"""Staff assistant: volunteers and duty staff ask anything about operations, by voice or text, and hear a short answer.

POST /api/staff/ask   JSON {text, lang, staff_id, confirm?} or multipart (audio, lang, staff_id)  -> reply text + audio
GET  /api/staff/examples                                   example questions for the UI
POST /api/staff/help  {stop, text, uid}                    a pilgrim help request lands in the staff queue
GET  /api/staff/help                                       open and handled help requests

Rules answer the common questions straight from the live modules (no model call). Anything else goes to the Sarvam chat
model with a facts block and a JSON contract {intent, reply, action, needs_confirmation}; numbers in the reply must
appear in the facts or the question, else the reply is replaced by a safe "I do not have that". Actions (walk-in booking,
crowd report, help handled) always ask for a spoken yes first. Rush-mode switching is NOT possible here: it goes through
NudgeBee approval. Live modules are imported lazily and every lookup tolerates a missing module or function.
"""
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Request

router = APIRouter()
IST = timezone(timedelta(hours=5, minutes=30))
CONFIRM_TTL_S = 120
LANGS = ("en", "ml", "te", "ta", "kn", "hi")

_lock = threading.RLock()
HELP = []                 # {"id", "t", "stop", "text", "uid", "status": open|handled}
PENDING = {}              # staff_id -> {"action", "say_en", "expires"}
_RUSH = {"since": None}   # remembered when we first saw rush on (the sim has no timestamp)

EXAMPLES = ["Which stop is busiest?", "How many bookings in this hour?", "How many walk-ins today?", "Any pilgrim needing help?",
            "What did NudgeBee find?", "Are we in rush mode?", "When is the next free slot?", "How long is the wait at Forest Path?",
            "Is the system healthy?", "What do I tell a pilgrim who lost their child?", "Book a walk-in for two at River Crossing",
            "Report two thousand waiting at Queue Complex"]
EXAMPLES_ML = ["ഏത് സ്റ്റോപ്പിലാണ് കൂടുതൽ തിരക്ക്?", "ഈ മണിക്കൂറിൽ എത്ര ബുക്കിംഗ്?", "ആർക്കെങ്കിലും സഹായം വേണോ?", "നഡ്ജ്ബീ എന്താണ് കണ്ടെത്തിയത്?",
               "അടുത്ത സ്ലോട്ട് എപ്പോൾ?", "ഫോറസ്റ്റ് പാത്തിൽ എത്ര നേരം കാത്തിരിക്കണം?"]


# ------------------------------------------------------------------ lazy access to the live modules
def _mod(name):
    try:
        return __import__(name)
    except Exception:
        return None


def _try(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _gates():
    qs = _mod("queue_sim")
    return (_try(lambda: qs.snapshot()["gates"], []) or []) if qs else []


def _stop_in(text):
    """Stop id named in the text (English or common spellings), else None."""
    low = (text or "").lower()
    qs = _mod("queue_sim")
    if not qs:
        return None
    for g in qs.GATES:
        if g["name"].lower() in low or re.search(r"\b%s\b" % g["id"], low):
            return g["id"]
    alias = {"g1": ["base camp", "basecamp", "base", "ബേസ്", "బేస్"], "g2": ["river", "crossing", "റിവർ", "നദി"], "g3": ["forest", "ഫോറസ്റ്റ്", "കാട്"],
             "g4": ["queue complex", "queue", "complex", "ക്യൂ"], "g5": ["main steps", "steps", "മെയിൻ", "പടി"]}
    for gid, words in alias.items():
        if any(w in low for w in words):
            return gid
    return None


def _stop_name(gid):
    qs = _mod("queue_sim")
    return qs.BY_ID[gid]["name"] if qs and gid in qs.BY_ID else str(gid)


def _fmt(ts):
    return datetime.fromtimestamp(ts, IST).strftime("%H:%M")


def add_help(stop=None, text="", uid="", kind="help"):
    """A pilgrim (or the assistant on a pilgrim's behalf) asks for a volunteer. Public so assistant.py can call it."""
    with _lock:
        rec = {"id": len(HELP) + 1, "t": time.time(), "stop": stop if stop in (getattr(_mod("queue_sim"), "BY_ID", {}) or {}) else None,
               "text": (text or "")[:200], "uid": str(uid or "")[:40], "kind": kind, "status": "open"}
        HELP.append(rec)
        return rec


def gather():
    """Live facts as a plain dict. Every part is optional."""
    qs, sl, fl, vol, cr = _mod("queue_sim"), _mod("slots"), _mod("flags"), _mod("volunteer"), _mod("crash")
    f = {"now": datetime.now(IST).strftime("%H:%M"), "stops": [], "rush": None}
    if qs:
        snap = _try(qs.snapshot, {}) or {}
        f["stops"] = snap.get("gates", [])
        f["rush"] = bool(snap.get("rush"))
        if f["rush"] and not _RUSH["since"]:
            _RUSH["since"] = time.time()
        if not f["rush"]:
            _RUSH["since"] = None
        marker = _try(lambda: cr._read(), {}) if cr else {}
        since = (marker or {}).get("started") if (marker or {}).get("running") else _RUSH["since"]
        f["rush_since"] = _fmt(since) if f["rush"] and since else None
    if sl:
        lst = _try(lambda: sl.listing(None, 8), {}) or {}
        f["slot_windows"], f["slot_cap"], f["bookings_total"] = lst.get("windows", []), lst.get("cap"), lst.get("total")
        books = list(_try(lambda: list(sl._by_uid.values()), []) or [])
        f["walkins_today"] = sum(1 for b in books if b.get("walk_in"))
        hr = datetime.now(IST).replace(minute=0, second=0, microsecond=0)
        h0, h1 = hr.timestamp(), (hr + timedelta(hours=1)).timestamp()
        f["bookings_this_hour"] = sum(1 for b in books if h0 <= b.get("window", 0) < h1)
        f["peak_window"] = lst.get("peak_window")
    if fl:
        f["map_mode"], f["slot_mode"] = _try(fl.map_mode), _try(fl.slot_mode)
        f["flags_source"] = "flagsmith" if _try(fl.using_flagsmith, False) else "local"
    if vol:
        pub = _try(vol.public, {}) or {}
        f["nudgebee"] = {"status": pub.get("status"), "summary": pub.get("summary"), "root_cause": pub.get("root_cause"),
                         "proposed_fix": pub.get("proposed_fix"), "steps_done": [t.get("step") for t in pub.get("timeline", [])]}
        f["voice_available"] = pub.get("voice_available")
    f["help_open"] = [h for h in HELP if h["status"] == "open"]
    cs = _mod("care_store")
    f["care_open"] = []
    if cs:
        for r in (_try(cs.all_requests, []) or []):
            if r.get("status") in getattr(cs, "ACTIVE", ("open", "assigned", "on_the_way")):
                a = r.get("assigned_to") or {}
                f["care_open"].append({"id": r.get("id"), "category": str(r.get("category") or "other").replace("_", " "), "urgency": r.get("urgency"),
                                       "stop": r.get("stop_name") or "unknown stop", "status": str(r.get("status")).replace("_", " "),
                                       "volunteer": a.get("name") if isinstance(a, dict) else None, "text": (r.get("summary_en") or r.get("transcript") or "")[:70]})
    f["webhooks"] = {"nudgebee_approve": bool(_try(lambda: __import__("config").NUDGEBEE_APPROVE_WEBHOOK(), "")),
                     "nudgebee_crash": bool(_try(lambda: __import__("config").NUDGEBEE_CRASH_WEBHOOK(), ""))}
    return f


def facts_text(f):
    """The facts block the model sees (and the numbers it may quote)."""
    L = [f"Time now {f.get('now')} IST. SIMULATED demo shrine."]
    for g in f.get("stops", []):
        L.append(f"Stop {g['id']} {g['name']}: wait {g['wait_min']} min, load {int(g['load'] * 100)} percent")
    L.append(f"Rush mode: {'ON' + (' since ' + f['rush_since'] if f.get('rush_since') else '') if f.get('rush') else 'off'}")
    if f.get("map_mode"):
        L.append(f"Flags: map_mode {f['map_mode']}, slot_mode {f['slot_mode']} (source {f.get('flags_source')})")
    if f.get("bookings_total") is not None:
        L.append(f"Bookings: {f['bookings_total']} total, {f.get('bookings_this_hour')} in this hour, {f.get('walkins_today')} walk-ins today, slot cap {f.get('slot_cap')} per window")
    nf = next((w for w in f.get("slot_windows", []) if w["count"] < w["cap"]), None)
    if nf:
        L.append(f"Next free slot window starts {nf['start']} ({nf['count']} of {nf['cap']} booked)")
    ho = f.get("help_open", [])
    L.append(f"Open help requests: {len(ho)}" + "".join(f"; #{h['id']} {_stop_name(h['stop']) if h['stop'] else 'unknown stop'}: {h['text'] or h['kind']}" for h in ho[:5]))
    co = f.get("care_open", [])
    L.append(f"Open complaints and care requests: {len(co)}" + "".join(
        f"; {c['id']} {c['category']} ({c['urgency']}) at {c['stop']}, {c['status']}" + (f", with {c['volunteer']}" if c['volunteer'] else "") for c in co[:6]))
    n = f.get("nudgebee") or {}
    if n:
        L.append(f"NudgeBee: status {n.get('status')}; cause: {n.get('root_cause') or 'none yet'}; fix: {n.get('proposed_fix') or 'none'}")
    L.append(f"Health: flags {f.get('flags_source', 'unknown')}, voice {'available' if f.get('voice_available') else 'unavailable'}, NudgeBee approve webhook {'set' if f['webhooks']['nudgebee_approve'] else 'not set'}")
    return "\n".join(L)


# ------------------------------------------------------------------ rules
_NUMW = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _has(low, words):
    return any(w in low for w in words)


def _party(low):
    m = re.search(r"\bfor\s+(\d+|%s)\b" % "|".join(_NUMW), low)
    if m:
        v = m.group(1)
        return int(v) if v.isdigit() else _NUMW[v]
    m = re.search(r"\b(\d+|%s)\s+(?:people|pilgrims|persons|walk-?ins?)\b" % "|".join(_NUMW), low)
    if m:
        v = m.group(1)
        return int(v) if v.isdigit() else _NUMW[v]
    return None


def _count(text):
    vol = _mod("volunteer")
    return _try(lambda: vol.parse_count(text)) if vol else None


def _parse_action(text, low):
    """Returns (kind, payload) for a requested change, else None."""
    if _has(low, ["walk-in", "walkin", "walk in", "വാക്ക് ഇൻ", "വാക്ക്-ഇൻ"]) and _has(low, ["book", "add", "register", "make", "create", "ബുക്ക്"]) \
            and not _has(low, ["how many", "എത്ര", "cancel"]):
        return "book_walkin", {"party": _party(low) or 1, "stop": _stop_in(text)}
    if _has(low, ["report", "reporting", "റിപ്പോർട്ട്"]) or (_has(low, ["waiting"]) and re.search(r"\d|thousand|hundred", low)):
        c = _count(text)
        if c is not None and _has(low, ["waiting", "people", "pilgrims", "crowd", "report", "റിപ്പോർട്ട്"]):
            return "report_crowd", {"count": c, "stop": _stop_in(text)}
    if _has(low, ["handled", "resolved", "mark", "done with", "close the help", "clear the help"]) and _has(low, ["help", "request", "സഹായ"]):
        return "help_handled", {}
    return None


def _wants_rush_switch(low):
    return _has(low, ["rush", "staggered", "lite mode", "slot mode", "map mode", "തിരക്ക് മോഡ്"]) and \
        bool(re.search(r"\b(switch|turn|set|enable|disable|activate|start|stop|change|flip|put)\b", low)) and \
        not re.search(r"\b(are we|is it|since when|status|are|is)\b", low)


def _rules_answer(text, low, f):
    """Returns (intent, reply_en) or None when the rules do not cover the question."""
    stops = f.get("stops", [])
    if _has(low, ["busiest", "most crowded", "most busy", "longest wait", "worst", "കൂടുതൽ തിരക്ക്", "ഏറ്റവും തിരക്ക്"]):
        if not stops:
            return "busiest", "I cannot see the stop loads right now."
        g = max(stops, key=lambda x: x["wait_min"])
        return "busiest", f"{g['name']} is busiest, with a wait of {g['wait_min']} minutes."
    if _has(low, ["how long", "wait at", "waiting time", "wait time", "wait for", "കാത്തിരി"]) and _stop_in(text) and not _has(low, ["help"]):
        gid = _stop_in(text)
        g = next((x for x in stops if x["id"] == gid), None)
        return "wait", (f"The wait at {g['name']} is about {g['wait_min']} minutes." if g else "I cannot see that stop right now.")
    if _has(low, ["walk-in", "walkin", "walk in", "വാക്ക്"]) and _has(low, ["how many", "count", "today", "എത്ര"]):
        n = f.get("walkins_today")
        return "walkins", ("I cannot read the booking list." if n is None else f"{n} walk-in booking{'s' if n != 1 else ''} today.")
    if _has(low, ["booking", "bookings", "booked", "ബുക്കിംഗ്", "ബുക്ക്"]) and _has(low, ["how many", "this hour", "count", "എത്ര"]):
        if f.get("bookings_total") is None:
            return "bookings", "I cannot read the booking list."
        return "bookings", f"{f['bookings_this_hour']} booking{'s' if f['bookings_this_hour'] != 1 else ''} in this hour, {f['bookings_total']} in total."
    if _has(low, ["complaint", "complaints", "care request", "care requests", "open request", "open requests", "pending request", "issues", "grievance", "പരാതി"]):
        co = f.get("care_open", [])
        if not co:
            return "complaints", "There are no open complaints right now."
        emer = [c for c in co if c["urgency"] == "emergency"]
        c = (emer or co)[0]
        who = f", {c['volunteer']} is on it" if c["volunteer"] else ", nobody has taken it yet"
        return "complaints", (f"{len(co)} open complaint{'s' if len(co) != 1 else ''}" + (f", {len(emer)} of them an emergency" if emer else "")
                              + f". The most urgent is {c['id']}: {c['category']} at {c['stop']}{who}.")
    if _has(low, ["help", "needing", "needs help", "assist", "സഹായം", "സഹായ"]) and _has(low, ["any", "pilgrim", "who", "anyone", "ആർക്ക", "ഏതെങ്കിലും", "needing"]) \
            and not _has(low, ["handled", "mark"]):
        ho = f.get("help_open", [])
        co = [c for c in f.get("care_open", []) if c["urgency"] in ("emergency", "urgent")]
        if not ho and co:
            c = co[0]
            return "help_open", (f"{len(co)} pilgrim{'s need' if len(co) != 1 else ' needs'} help. The most urgent is {c['id']}: {c['category']} at {c['stop']}"
                                 + (f", {c['volunteer']} is on it." if c["volunteer"] else ", nobody has taken it yet."))
        if not ho:
            return "help_open", "No pilgrim is waiting for help right now."
        h = ho[0]
        where = f" at {_stop_name(h['stop'])}" if h["stop"] else ""
        return "help_open", f"{len(ho)} pilgrim{'s need' if len(ho) != 1 else ' needs'} help. The oldest is request {h['id']}{where}: {h['text'] or h['kind']}."
    if _has(low, ["nudgebee", "nudge bee", "nudge", "നഡ്ജ്", "നഡ്ജ്ബീ", "ന്യൂജ്"]):
        n = f.get("nudgebee") or {}
        if n.get("root_cause"):
            return "nudgebee", f"NudgeBee found: {n['root_cause']}" + (f" Proposed fix: {n['proposed_fix']}" if n.get("proposed_fix") else "")
        return "nudgebee", "NudgeBee has not reported a cause. Everything is quiet."
    if _has(low, ["rush", "തിരക്ക് മോഡ്"]) and _has(low, ["are we", "is it", "is there", "any", "now", "right now", "since", "status", "mode", "on", "off", "ആണോ"]):
        if f.get("rush"):
            since = f" since {f['rush_since']}" if f.get("rush_since") else ""
            return "rush", f"Yes, rush mode is on{since}. Slots are {f.get('slot_mode') or 'staggered'} and the map is {f.get('map_mode') or 'light'}."
        return "rush", f"No, we are not in rush mode. Slots are {f.get('slot_mode') or 'open'}."
    if _has(low, ["next free", "next slot", "free slot", "next window", "അടുത്ത സ്ലോട്ട്", "ഫ്രീ സ്ലോട്ട്"]):
        w = next((x for x in f.get("slot_windows", []) if x["count"] < x["cap"]), None)
        return "next_slot", (f"The next free slot starts at {w['start']}, with {w['cap'] - w['count']} places left." if w else "No free slot in the next windows.")
    if _has(low, ["healthy", "health", "system ok", "everything ok", "all ok", "working", "status of the system", "ആരോഗ്യ", "സിസ്റ്റം"]):
        bad = []
        if f.get("rush"):
            bad.append("rush mode is on")
        if f.get("voice_available") is False:
            bad.append("voice is unavailable")
        if not f["webhooks"]["nudgebee_approve"]:
            bad.append("the NudgeBee approval link is not set")
        nf = (f.get("nudgebee") or {}).get("status")
        base = f"Flags come from {f.get('flags_source', 'an unknown source')}."
        return "health", ("Yes, the system looks healthy. " + base) if not bad else ("Mostly. " + base + " Note: " + ", ".join(bad) + ".")
    return None


def _kb_hint(text, lang):
    kb = _mod("kb")
    return _try(lambda: kb.facts_for(text, lang)) if kb else None


# ------------------------------------------------------------------ model path
SYSTEM = ("You are the operations assistant for temple volunteers at a simulated hill shrine. Answer ONLY from the FACTS. "
          "Never invent a number, a stop or a time. If the facts do not contain the answer, say you do not know and suggest the information counter. "
          "Reply in {lang}, at most two short spoken sentences. You cannot change rush mode: the rush switch is approved through NudgeBee. "
          "If the user asks to book a walk-in, report a crowd count, or mark a help request handled, set action and needs_confirmation true. "
          'Return ONLY JSON: {{"intent": "...", "reply": "...", "action": null or {{"type": "book_walkin|report_crowd|help_handled", "stop": "g1..g5", "count": 0, "party": 1}}, "needs_confirmation": false}}')
LANG_NAME = {"en": "English", "ml": "Malayalam", "te": "Telugu", "ta": "Tamil", "kn": "Kannada", "hi": "Hindi"}
_DIG = str.maketrans("०१२३४५६७८९೦೧೨೩೪೫೬೭೮೯൦൧൨൩൪൫൬൭൮൯౦౧౨౩౪౫౬౭౮౯௦௧௨௩௪௫௬௭௮௯", "0123456789" * 5)


def _numbers(s):
    return set(re.findall(r"\d+", (s or "").translate(_DIG)))


def numbers_ok(reply, allowed_text):
    """Every number the reply states must appear in the facts or the question."""
    return _numbers(reply) <= _numbers(allowed_text)


def _llm(text, lang, f, kbtxt):
    import sarvam
    facts = facts_text(f) + ("\n" + kbtxt if kbtxt else "")
    j, ms = sarvam.chat_json(SYSTEM.format(lang=LANG_NAME.get(lang, "English")), f"FACTS:\n{facts}\n\nQUESTION: {text}")
    return j, ms, facts


def _valid_action(a, f):
    """Validate an action dict (from the model) against live state. Returns clean dict or None."""
    if not isinstance(a, dict):
        return None
    t, qs = a.get("type"), _mod("queue_sim")
    stop = a.get("stop") if a.get("stop") in (getattr(qs, "BY_ID", {}) or {}) else None
    if t == "book_walkin" and stop:
        try:
            party = int(a.get("party") or 1)
        except (TypeError, ValueError):
            return None
        return {"type": t, "stop": stop, "party": max(1, min(party, 10))} if 1 <= party <= 10 else None
    if t == "report_crowd" and stop:
        try:
            c = int(a.get("count"))
        except (TypeError, ValueError):
            return None
        return {"type": t, "stop": stop, "count": c} if 0 < c <= 10000 else None
    if t == "help_handled" and f.get("help_open"):
        return {"type": t, "id": f["help_open"][0]["id"]}
    return None


def _confirm_text(a):
    if a["type"] == "book_walkin":
        return f"Book {a['party']} walk-in{'s' if a['party'] != 1 else ''} at {_stop_name(a['stop'])}? Say yes to confirm."
    if a["type"] == "report_crowd":
        return f"Report {a['count']} waiting at {_stop_name(a['stop'])}? Say yes to confirm."
    return f"Mark help request {a['id']} as handled? Say yes to confirm."


def execute(a):
    """Run a confirmed action. Returns the English result sentence."""
    if a["type"] == "book_walkin":
        sl, fl = _mod("slots"), _mod("flags")
        if not sl:
            return "Booking is not available right now."
        mode = _try(fl.slot_mode, "open") if fl else "open"
        got = [sl.book_walk_in(a["stop"], mode=mode or "open")[0] for _ in range(a["party"])]
        labels = sorted({s["label"] for s in got})
        return f"Done. {a['party']} walk-in{'s' if a['party'] != 1 else ''} booked at {_stop_name(a['stop'])}, slot {' and '.join(labels)}."
    if a["type"] == "report_crowd":
        qs = _mod("queue_sim")
        ok = bool(qs and qs.report_crowd(a["stop"], a["count"]))
        return f"Done. {a['count']} waiting at {_stop_name(a['stop'])} is recorded." if ok else "I could not record that count."
    if a["type"] == "help_handled":
        with _lock:
            h = next((x for x in HELP if x["id"] == a.get("id") and x["status"] == "open"), None)
            if not h:
                return "That help request is already handled."
            h["status"], h["handled_at"] = "handled", time.time()
        return f"Done. Help request {h['id']} is marked as handled."
    return "Nothing to do."


RUSH_MSG = "I cannot change rush mode here. The rush switch is approved through NudgeBee."
UNKNOWN_MSG = "I do not have that. Please ask at the information counter."


def _yesno(text):
    vol = _mod("volunteer")
    d = _try(lambda: vol.keyword_decision(text)) if vol else None
    if d in ("yes", "no"):
        return d
    low = (text or "").lower()
    if re.search(r"\b(yes|yeah|ok|okay|confirm|do it)\b|ശരി|അതെ", low):
        return "yes"
    if re.search(r"\b(no|cancel|stop|don't)\b|വേണ്ട|ഇല്ല", low):
        return "no"
    return None


def answer(text, lang="en", staff_id="staff", confirm=None, use_llm=True):
    """Core. Returns a dict with intent, reply_en (rules) or reply (final text in lang), action, needs_confirmation, via."""
    text = (text or "").strip()
    low = text.lower()
    f = gather()
    out = {"intent": "unknown", "action": None, "needs_confirmation": False, "via": "rules", "reply_lang": "en"}
    with _lock:
        pend = PENDING.get(staff_id)
        if pend and pend["expires"] < time.time():
            PENDING.pop(staff_id, None)
            pend = None
    if pend:
        d = confirm or _yesno(text)
        if d in ("yes", "no"):
            with _lock:
                PENDING.pop(staff_id, None)
            if d == "yes":
                return {**out, "intent": "confirmed", "reply": execute(pend["action"]), "action": pend["action"], "executed": True}
            return {**out, "intent": "cancelled", "reply": "Okay, I did not do it."}
        with _lock:
            PENDING.pop(staff_id, None)        # a new question replaces the pending action
    if not text:
        return {**out, "reply": "I did not hear anything. Please try again."}
    d_ = _mod("directions")
    if d_ and _try(lambda: d_.script_lang(text)) and use_llm:
        # asked in Telugu, Hindi, Tamil, Kannada or Malayalam: read it in English so every rule and action works, answer back in the staff language
        try:
            import sarvam
            en = sarvam.translate(text, "en").text.strip()
            if en:
                out["understood_en"] = en
                text, low = en, en.lower()
        except Exception:
            pass
    if _wants_rush_switch(low):
        return {**out, "intent": "rush_switch_refused", "reply": RUSH_MSG}
    act = _parse_action(text, low)
    if act:
        kind, p = act
        if kind in ("book_walkin", "report_crowd") and not p.get("stop"):
            return {**out, "intent": kind, "reply": "Which stop? Base Camp, River Crossing, Forest Path, Queue Complex or Main Steps."}
        if kind == "report_crowd" and not (0 < p["count"] <= 10000):
            return {**out, "intent": kind, "reply": "That number looks wrong. Please say it again."}
        if kind == "help_handled" and not f.get("help_open"):
            return {**out, "intent": kind, "reply": "There is no open help request to mark."}
        a = _valid_action({"type": kind, **p}, f)
        if not a:
            return {**out, "intent": kind, "reply": "I did not understand that request. Please say it again."}
        with _lock:
            PENDING[staff_id] = {"action": a, "expires": time.time() + CONFIRM_TTL_S}
        return {**out, "intent": kind, "reply": _confirm_text(a), "action": a, "needs_confirmation": True}
    r = _rules_answer(text, low, f)
    if r:
        return {**out, "intent": r[0], "reply": r[1]}
    kbtxt = _kb_hint(text, lang)
    if use_llm:
        try:
            j, ms, facts = _llm(text, lang, f, kbtxt)
            reply = str(j.get("reply") or "").strip()
            if not reply:
                raise ValueError("empty reply")
            if not numbers_ok(reply, facts + " " + text):
                return {**out, "intent": str(j.get("intent") or "unknown"), "reply": UNKNOWN_MSG, "via": "llm_rejected_numbers", "llm_ms": ms}
            a = _valid_action(j.get("action"), f)
            reply = re.sub(r"\s*[\(\[]?\b[gG][1-5]\b[\)\]]?\s*", " ", reply).strip()     # stop ids are internal
            res = {**out, "intent": str(j.get("intent") or "unknown")[:40], "reply": reply, "reply_lang": lang, "via": "llm", "llm_ms": ms}
            if a:
                with _lock:
                    PENDING[staff_id] = {"action": a, "expires": time.time() + CONFIRM_TTL_S}
                res.update(action=a, needs_confirmation=True, reply=_confirm_text(a), reply_lang="en")
            return res
        except Exception as e:
            out["note"] = f"model unavailable ({e.__class__.__name__})"
    if kbtxt:        # model unavailable: give the pack's own words
        top = kbtxt.splitlines()[-1].lstrip("- ")
        return {**out, "intent": "pack", "reply": top, "via": "pack"}
    return {**out, "reply": UNKNOWN_MSG}


# ------------------------------------------------------------------ speech
def _translate(text, lang):
    if lang == "en" or not text:
        return text, None
    try:
        import sarvam
        return sarvam.translate(text, lang, "en").text, None
    except Exception as e:
        return text, f"Could not translate ({e.__class__.__name__}); showing English."


def _speak(text, lang):
    d = _mod("directions")
    if not d:
        return None, 0, "Voice unavailable."
    return d.speak(text, lang)


async def _read(request: Request):
    """(text, lang, staff_id, confirm, audio_bytes, filename, content_type)"""
    ct = request.headers.get("content-type", "")
    if "json" in ct:
        j = await request.json()
        return str(j.get("text") or ""), str(j.get("lang") or "en"), str(j.get("staff_id") or "staff"), j.get("confirm"), None, "", ""
    form = await request.form()
    up = form.get("audio")
    data = await up.read() if up is not None and hasattr(up, "read") else None
    return (str(form.get("text") or ""), str(form.get("lang") or "en"), str(form.get("staff_id") or "staff"), form.get("confirm"),
            data, getattr(up, "filename", "") or "audio.webm", getattr(up, "content_type", "") or "audio/webm")


@router.post("/api/staff/ask")
async def staff_ask(request: Request):
    from starlette.concurrency import run_in_threadpool
    t0 = time.perf_counter()
    text, lang, staff_id, confirm, data, fn, ctype = await _read(request)
    lang = lang if lang in LANGS else "en"
    notice, stt_ms = None, 0
    if not text and data:
        try:
            import sarvam
            r = await run_in_threadpool(sarvam.stt, data, fn, ctype, lang if lang != "en" else None)
            text, stt_ms = r.transcript.strip(), r.ms
        except Exception as e:
            msg = getattr(e, "args", [""])[0] if e.__class__.__name__ == "SarvamNoCredits" else f"Voice unavailable ({e.__class__.__name__}). Type instead."
            return {"transcript": "", "reply_text": msg, "audio_base64": None, "intent": "unavailable", "action": None,
                    "needs_confirmation": False, "notice": msg, "lang": lang, "via": "none"}
    res = await run_in_threadpool(answer, text, lang, staff_id, str(confirm).lower() if confirm else None)
    reply = res["reply"]
    if lang == "en" and res.get("understood_en"):
        lang = (_mod("directions").script_lang(text) or lang)      # asked in Telugu on an English page: answer in Telugu
    if res.get("reply_lang") != lang:
        reply, notice = await run_in_threadpool(_translate, reply, lang)
    audio, tts_ms, n2 = await run_in_threadpool(_speak, reply, lang)
    return {"transcript": text, "reply_text": reply, "audio_base64": audio, "lang": lang, "intent": res["intent"], "action": res.get("action"),
            "needs_confirmation": res["needs_confirmation"], "executed": bool(res.get("executed")), "via": res["via"],
            "notice": notice or n2, "latency": {"stt_ms": stt_ms, "llm_ms": res.get("llm_ms", 0), "tts_ms": tts_ms,
                                                "total_ms": int((time.perf_counter() - t0) * 1000)}}


@router.get("/api/staff/examples")
def staff_examples(lang: str = "en"):
    return {"examples": EXAMPLES_ML if lang == "ml" else EXAMPLES, "simulated": True}


@router.post("/api/staff/help")
async def staff_help_add(request: Request):
    j = await request.json()
    return {"ok": True, "request": add_help(j.get("stop"), j.get("text", ""), j.get("uid", ""), j.get("kind", "help"))}


@router.get("/api/staff/help")
def staff_help_list():
    return {"requests": HELP[-50:], "open": sum(1 for h in HELP if h["status"] == "open")}
