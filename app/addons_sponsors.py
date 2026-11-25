"""Sponsors page: what Sarvam AI, Flagsmith and NudgeBee are doing in this product right now.

Mount: `from addons_sponsors import router as addons_sponsors_router; app.include_router(addons_sponsors_router)`
(or `_mount("addons_sponsors")`). Importing this module installs the Sarvam call recorder (idempotent), so
mount it early. Routes: GET /sponsors (page), GET /sponsors/sponsors.js, GET /sponsors/sponsors.css,
GET /api/sponsors/status (JSON).

Env (all optional, every missing source shows "not available" instead of failing):
  FLAGSMITH_ENV_KEY or FLAGSMITH_CLIENT_KEY  edge reads (values, reasons)
  FLAGSMITH_ADMIN_KEY                        audit log, change history, rollout percentage (never returned)
  FLAGSMITH_PROJECT_ID (55985), FLAGSMITH_ENV_ID (119864)
  STATE_FILE                                 recorder files live next to it (the /data volume)

Never calls Sarvam. The recorder only watches calls that other code makes.
"""
import json
import logging
import os
import re
import statistics
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

log = logging.getLogger("sponsors")
router = APIRouter()
UI = Path(__file__).parent / "addons_ui"

FLAG_NAMES = ["map_mode", "slot_mode", "voice_directions", "voice_first", "ui_copy", "voice_agent_v2"]
FLAG_DEFAULTS = {"map_mode": "full", "slot_mode": "open"}
AUTOMATIONS = ["darshan-crash-report", "darshan-rush-investigate", "darshan-staggered-approved"]
ADMIN = "https://api.flagsmith.com/api/v1"
EDGE = lambda: os.environ.get("FLAGSMITH_API_URL", "https://edge.api.flagsmith.com/api/v1/").rstrip("/")
PROJECT = lambda: os.environ.get("FLAGSMITH_PROJECT_ID", "55985")
ENV_ID = lambda: os.environ.get("FLAGSMITH_ENV_ID", "119864")
EDGE_KEY = lambda: (os.environ.get("FLAGSMITH_CLIENT_KEY") or os.environ.get("FLAGSMITH_ENV_KEY") or "").strip()
ADMIN_KEY = lambda: os.environ.get("FLAGSMITH_ADMIN_KEY", "").strip()
CACHE_S = 10.0


def _data_dir():
    return os.path.dirname(os.environ.get("STATE_FILE", "/tmp/darshan-state.json")) or "."


def _plain(md, n=220):
    """Markdown from NudgeBee -> one short plain line: no headings, links, emoji or asterisks."""
    t = re.sub(r"\[([^\]]*)\]\(#[^)]*\)", "", str(md or ""))
    t = re.sub(r"[#*`>|]+|[\U0001F000-\U0001FFFF\u2600-\u27BF]", "", t)
    t = re.sub(r"(?i)event summary|quick investigation", "", t)
    t = re.sub(r"\b(Title|Event Id|Resource|Time):[^\n]*\n?", "", t)
    t = re.sub(r"^\s*-\s*", "", t, flags=re.M)
    t = re.sub(r"(^|\s)-(?=\s)", " ", t)
    return _clip(t.strip(" -\n"), n)


def _clip(s, n=80):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


# =============================================================== Sarvam recorder
_calls = []
_calls_lock = threading.Lock()
MAX_CALLS = 400
TYPES = {"speech-to-text": "stt", "translate": "translate", "text-to-speech": "tts", "chat": "chat"}


def _calls_file():
    return os.path.join(_data_dir(), "sarvam_calls.jsonl")


def _load_calls():
    try:
        with open(_calls_file(), encoding="utf-8") as f:
            rows = [json.loads(l) for l in f if l.strip()]
        with _calls_lock:
            _calls[:] = [r for r in rows if isinstance(r, dict)][-MAX_CALLS:]
    except Exception:
        pass


def _store(rec):
    with _calls_lock:
        _calls.append(rec)
        over = len(_calls) > MAX_CALLS * 2
        if over:
            del _calls[:-MAX_CALLS]
        try:
            os.makedirs(_data_dir(), exist_ok=True)
            if over:
                with open(_calls_file(), "w", encoding="utf-8") as f:
                    f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in _calls)
            else:
                with open(_calls_file(), "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass


def _err_status(e):
    """Map a sarvam exception to (http status or 0, short label)."""
    name = e.__class__.__name__
    if name == "SarvamNoCredits":
        return 402, "no credits"
    if name == "NoKey":
        return 0, "no key"
    msg = str(e)
    m = re.search(r"\b([45]\d\d)\b", msg)
    if m:
        return int(m.group(1)), "http " + m.group(1)
    if "timed out" in msg:
        return 0, "timeout"
    return 0, "network"


def _record(what, kw, ms, status, resp, error=None):
    """Build and store one record. Called inside try/except by the wrapper."""
    typ = TYPES.get(what, what)
    j = kw.get("json") or {}
    data = kw.get("data") or {}
    body = None
    if resp is not None:
        try:
            body = resp.json()
        except Exception:
            body = None
    lang, text, out = None, "", ""
    if typ == "stt":
        lang = (body or {}).get("language_code") or data.get("language_code")
        text = (body or {}).get("transcript", "")
    elif typ == "translate":
        lang = j.get("target_language_code")
        text, out = j.get("input", ""), (body or {}).get("translated_text", "")
    elif typ == "tts":
        lang, text = j.get("target_language_code"), j.get("text", "")
    elif typ == "chat":
        msgs = j.get("messages") or [{}]
        text = (msgs[-1] or {}).get("content", "")
    short = (lang or "").split("-")[0].lower() or None
    try:
        import sarvam_keys
        slot, nkeys = sarvam_keys._last[0] + 1, len(sarvam_keys._keys())
    except Exception:
        slot, nkeys = None, None
    _store({"t": time.time(), "type": typ, "status": status, "ms": int(ms), "lang": short,
            "text": _clip(text), "out": _clip(out), "error": error, "slot": slot, "keys": nkeys})


def install_recorder(mod=None):
    """Wrap sarvam._post with a recorder. Idempotent, never changes behaviour, never raises."""
    try:
        if mod is None:
            import sarvam as mod
        orig = mod._post
        if getattr(orig, "_sponsors_wrapped", False):
            return False

        def _post(path, what, **kw):
            t0 = time.perf_counter()
            try:
                r, ms = orig(path, what, **kw)
            except BaseException as e:
                try:
                    st, label = _err_status(e)
                    _record(what, kw, (time.perf_counter() - t0) * 1000, st, None, label)
                except Exception:
                    pass
                raise
            try:
                _record(what, kw, ms, getattr(r, "status_code", 200), r)
            except Exception:
                pass
            return r, ms

        _post._sponsors_wrapped = True
        _post.__wrapped__ = orig
        mod._post = _post
        return True
    except Exception as e:  # pragma: no cover
        log.warning("sarvam recorder not installed: %s", e)
        return False


# ---- crash report recorder (what we sent to NudgeBee, and when)
def _crash_file():
    return os.path.join(_data_dir(), "sponsors_crash.json")


def install_crash_recorder(mod=None):
    try:
        if mod is None:
            import crash as mod
        orig = mod.check_after_start
        if getattr(orig, "_sponsors_wrapped", False):
            return False

        def check_after_start(*a, **kw):
            rec = orig(*a, **kw)
            try:
                if rec:
                    with open(_crash_file(), "w", encoding="utf-8") as f:
                        json.dump({"t": time.time(), **{k: rec.get(k) for k in (
                            "pod", "reason", "sent", "status", "restarts_seen", "reported_at", "error")}}, f)
            except Exception:
                pass
            return rec

        check_after_start._sponsors_wrapped = True
        mod.check_after_start = check_after_start
        return True
    except Exception as e:  # pragma: no cover
        log.warning("crash recorder not installed: %s", e)
        return False


# =============================================================== helpers
def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception as e:
        log.warning("%s failed: %s", getattr(fn, "__name__", "fn"), e)
        return {"available": False, "note": "not available"}


def _http(url, headers=None, body=None, timeout=4):
    h = dict(headers or {})
    if body is not None:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, headers=h, data=json.dumps(body).encode() if body is not None else None,
                                 method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def _iso(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


_cache = {}
_cache_lock = threading.Lock()


def _cached(key, fn, ttl=CACHE_S):
    with _cache_lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
    val = fn()
    with _cache_lock:
        _cache[key] = (time.time(), val)
    return val


def _volunteer():
    try:
        import volunteer
        return volunteer.public()
    except Exception:
        return {}


def _timeline(v):
    return {t["step"]: t["t"] for t in (v.get("timeline") or []) if isinstance(t, dict) and "step" in t}


# =============================================================== Sarvam block
def sarvam_block(v):
    with _calls_lock:
        calls = list(_calls)
    try:
        import sarvam
        have_key = bool(sarvam.available())
    except Exception:
        have_key = False
    by_type, lat = {}, {}
    for c in calls:
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1
        if c.get("status") == 200:
            lat.setdefault(c["type"], []).append(c["ms"])
    median = {k: int(statistics.median(x)) for k, x in lat.items() if x}
    heard = [c for c in calls if c["type"] == "stt" and c.get("status") == 200 and c.get("text")]
    said = [c for c in calls if c["type"] == "tts" and c.get("status") == 200 and c.get("text")]
    langs = sorted({c["lang"] for c in calls if c["type"] == "stt" and c.get("status") == 200 and c.get("lang")})
    last = calls[-1] if calls else None
    last_heard = ({"text": heard[-1]["text"], "lang": heard[-1]["lang"], "t": heard[-1]["t"]} if heard else None)
    # when the recorder has not seen a take yet, the volunteer state still holds what was really heard
    vt = v.get("transcript")
    if not last_heard and vt:
        last_heard = {"text": _clip(vt), "lang": None, "t": None, "from": "volunteer state"}
    last_said = ({"text": said[-1]["text"], "lang": said[-1]["lang"], "t": said[-1]["t"]} if said else None)
    if not last_said and v.get("question_en"):
        last_said = {"text": _clip(v["question_en"]), "lang": "ml", "t": None, "from": "volunteer question (cached render)"}
    slot = None
    try:
        import sarvam_keys
        ks = sarvam_keys._keys()
        if ks:
            cool = [sarvam_keys._cool.get(i, 0) > time.time() for i in range(len(ks))]
            slot = {"in_use": sarvam_keys._last[0] + 1, "of": len(ks), "cooling": [i + 1 for i, c in enumerate(cool) if c]}
    except Exception:
        pass
    if not have_key:
        credits, state = "no key set", "problem"
    elif not last:
        credits, state = "no calls yet this session", "waiting"
    elif last.get("status") == 200:
        credits, state = "available (last call answered 200)", "working"
    elif last.get("status") == 402:
        credits, state = "no credits (last call answered 402)", "problem"
    elif last.get("status") == 429:
        credits, state = "rate limited (last call answered 429)", "problem"
    else:
        credits, state = "last call failed: " + str(last.get("error") or last.get("status")), "problem"
    return {
        "state": state, "available": True,
        "calls": by_type, "calls_total": len(calls), "languages_heard": langs,
        "last_heard": last_heard, "last_said": last_said, "median_ms": median,
        "key_slot": slot, "credits": credits, "last_status": last.get("status") if last else None,
        "volunteer_latency_ms": v.get("latency") or {},
        "recorder": "counts calls made by this app process since the recorder started, kept on the data volume",
    }


# =============================================================== Flagsmith block
def _edge_flags(traits):
    body = {"identifier": "sponsors-page", "traits": [{"trait_key": k, "trait_value": x} for k, x in traits.items()]}
    d = _http(EDGE() + "/identities/", {"X-Environment-Key": EDGE_KEY()}, body)
    return {f["feature"]["name"]: (f.get("feature_state_value"), bool(f.get("enabled"))) for f in d.get("flags", [])}


def _env_flags():
    d = _http(EDGE() + "/flags/", {"X-Environment-Key": EDGE_KEY()})
    return {f["feature"]["name"]: (f.get("feature_state_value"), bool(f.get("enabled"))) for f in d}


def _admin(path):
    return _http(ADMIN + path, {"Authorization": "Api-Key " + ADMIN_KEY()})


def _feature_ids():
    def go():
        d = _admin(f"/projects/{PROJECT()}/features/?page_size=100")
        return {f["name"]: f["id"] for f in d.get("results", [])}
    return _cached("fids", go, 300)


def _last_change(name):
    fid = _feature_ids().get(name)
    if not fid:
        return None
    d = _admin(f"/environments/{ENV_ID()}/features/{fid}/versions/?page_size=1")
    r = (d.get("results") or [None])[0]
    if not r:
        return None
    who = r.get("published_by") or r.get("created_by")
    return {"t": _iso(r.get("live_from") or r.get("created_at")), "count": d.get("count"),
            "by": "a person in the dashboard" if who else "Admin API key (script or NudgeBee task)"}


def _audit():
    d = _admin(f"/projects/{PROJECT()}/audit/?page_size=40")
    rows = []
    for r in d.get("results", []):
        a = r.get("author") or {}
        who = (a.get("first_name") or "").strip() or ("a person" if a else "Admin API key")
        rows.append({"t": _iso(r.get("created_date")), "log": _clip(r.get("log"), 120), "by": who})
    return {"count": d.get("count", len(rows)), "rows": rows[:6]}


def _rollout_pct():
    d = _admin(f"/projects/{PROJECT()}/segments/?page_size=100&q=rollout_voice_agent_v2")
    for s in d.get("results", []):
        if s.get("name") == "rollout_voice_agent_v2":
            for r in s.get("rules", []):
                for rr in r.get("rules", []):
                    for c in rr.get("conditions", []):
                        if c.get("operator") == "PERCENTAGE_SPLIT":
                            return int(float(c["value"]))
    return None


def _fmt(name, val, on):
    if name == "ui_copy":
        try:
            j = json.loads(val)
            return "remote text for %d languages" % len(j.get("banner", {})) if on else "off"
        except Exception:
            return "on" if on else "off"
    if name in ("voice_first", "voice_agent_v2"):
        return "on" if on else "off"
    s = str(val if val is not None else "").strip()
    if s.startswith("{"):
        try:
            j = json.loads(s)
            s = str(j.get("mode") or j.get("value") or s)
        except Exception:
            pass
    return s or ("on" if on else "off")


def _flag_change(name):
    return _safe(_last_change, name) if ADMIN_KEY() else None


def flagsmith_block(v):
    out = {"available": True, "state": "waiting", "flags": [], "audit": None, "experiment": None, "rollout": None}
    tl = _timeline(v)
    std = eld = {}
    if not EDGE_KEY():
        out.update(state="problem", note="Flagsmith key is not set in this app")
    else:
        try:
            std = _cached("fs_std", lambda: _edge_flags({"language": "en", "age_65_plus": False}))
            eld = _cached("fs_eld", lambda: _edge_flags({"language": "ml", "age_65_plus": True}))
            out["state"] = "working"
        except Exception as e:
            out.update(state="problem", note="Flagsmith edge not reachable (%s)" % e.__class__.__name__)
            std = eld = {}
    pct = None
    changes = {}
    if ADMIN_KEY():
        pct = _safe(lambda: _cached("fs_pct", _rollout_pct))
        pct = pct if isinstance(pct, int) else None
        with ThreadPoolExecutor(max_workers=6) as ex:
            res = list(ex.map(lambda n: _cached("fs_ch_" + n, lambda: _flag_change(n)), FLAG_NAMES))
        changes = {n: r for n, r in zip(FLAG_NAMES, res) if isinstance(r, dict) and "t" in r}
        a = _safe(lambda: _cached("fs_audit", _audit))
        out["audit"] = a if isinstance(a, dict) and "rows" in a else {"available": False, "note": "not available"}
    else:
        out["admin_note"] = "FLAGSMITH_ADMIN_KEY is not set in this app: change history not available"
    yes_t, flip_t = tl.get("Volunteer said yes"), tl.get("Flags flipped")
    for n in FLAG_NAMES:
        if n not in std:
            out["flags"].append({"flag": n, "available": False, "value": "not available", "reason": "not available"})
            continue
        sv, son = std[n]
        ev, eon = eld.get(n, (None, None))
        row = {"flag": n, "available": True, "value": _fmt(n, sv, son), "enabled": son}
        if n == "voice_directions":
            row["reason"] = "A/B variant, 50/50 split, sticky per visitor"
            row["value"] = "voice or map (test visitor gets %s)" % _fmt(n, sv, son)
        elif n == "voice_agent_v2":
            row["reason"] = "percentage rollout" + (": %d%% of pilgrims" % pct if pct is not None else "")
            row["value"] = ("%d%% rollout" % pct) if pct is not None else _fmt(n, sv, son)
        elif eon is not None and (eon, ev) != (son, sv):
            row["reason"] = "segment elders_65_plus (age 65+ trait): on for them, off for others"
            row["value"] = "off for others, on for 65+"
        elif n in FLAG_DEFAULTS and _fmt(n, sv, son) != FLAG_DEFAULTS[n]:
            row["reason"] = "changed from the default (%s)" % FLAG_DEFAULTS[n]
        else:
            row["reason"] = "default for this environment" + (" (no segment matched)" if n != "ui_copy" else ", remote config")
        ch = changes.get(n)
        if ch:
            row["changed_at"], row["changed_by"], row["versions"] = ch["t"], ch["by"], ch["count"]
            if yes_t and ch["t"] and yes_t <= ch["t"] <= (flip_t or ch["t"]) + 120 and n in ("map_mode", "slot_mode"):
                row["proof"] = "written %d s after the volunteer's yes, through the Admin API: the NudgeBee HTTP task" % max(0, int(ch["t"] - yes_t))
        out["flags"].append(row)
    try:
        import flags
        out["experiment"] = flags.experiment()
        out["experiment"].pop("recent_events", None)
    except Exception:
        out["experiment"] = {"available": False, "note": "not available"}
    out["rollout"] = {"percent": pct, "flag": "voice_agent_v2"} if pct is not None else {"available": False, "note": "not available"}
    return out


# =============================================================== NudgeBee block
def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def nudgebee_block(v):
    tl = _timeline(v)
    crash_rec = _read_json(_crash_file())
    marker = None
    try:
        import crash
        marker = crash._read()
    except Exception:
        pass
    crash_t = tl.get("Crash reported to NudgeBee") or (crash_rec or {}).get("t")
    cause_t, ask_t, yes_t = tl.get("Cause found by NudgeBee"), tl.get("Asked the volunteer"), tl.get("Volunteer said yes")
    sent_t, flip_t, rec_t = tl.get("NudgeBee approved"), tl.get("Flags flipped"), tl.get("Booking recovered")
    root = v.get("root_cause") or ""
    try:
        import config
        crash_hook, appr_hook = bool(config.NUDGEBEE_CRASH_WEBHOOK()), bool(config.NUDGEBEE_APPROVE_WEBHOOK())
    except Exception:
        crash_hook = appr_hook = None
    got_event = bool(v.get("event_id"))
    status = v.get("status")
    if got_event:
        state, agent = "working", "connected: NudgeBee sent us a cause for this cluster"
    elif crash_t:
        state, agent = "waiting", "crash was reported; waiting for the cause to come back"
    elif crash_hook is False and appr_hook is False:
        state, agent = "problem", "webhooks are not set in this app"
    else:
        state, agent = "waiting", "nothing reported yet (the agent pods are not visible from inside our pod)"
    approval = [
        {"step": "Asked the volunteer", "t": ask_t, "done": bool(ask_t)},
        {"step": "Volunteer said yes", "t": yes_t, "done": bool(yes_t)},
        {"step": "Approval sent to NudgeBee", "t": sent_t, "done": bool(sent_t)},
        {"step": "Duty officer confirmed in NudgeBee", "t": flip_t, "done": bool(flip_t), "inferred": True},
        {"step": "Flags flipped", "t": flip_t, "done": bool(flip_t)},
    ]
    start_t = crash_t  # only a reported crash starts this clock (rush and cause are marked together)
    return {
        "state": state, "available": True, "agent": agent, "status": status,
        "last_crash": ({"t": crash_t, "pod": (crash_rec or {}).get("pod") or "not recorded",
                        "sent": (crash_rec or {}).get("sent"), "restarts": (marker or {}).get("restarts")}
                       if crash_t else None),
        "summary": v.get("summary") or None,
        "root_cause": root or None, "root_cause_short": _plain(root, 220) if root else None,
        "proposed_fix": v.get("proposed_fix"),
        "approval": approval, "webhook_ok": v.get("webhook_ok"), "webhook_error": v.get("webhook_error"),
        "crash_to_cause_s": round(cause_t - start_t, 1) if cause_t and start_t and cause_t >= start_t else None,
        "yes_to_recovery_s": round(rec_t - yes_t, 1) if rec_t and yes_t and rec_t >= yes_t else None,
        "automations": AUTOMATIONS, "webhooks": {"crash": crash_hook, "approval": appr_hook},
        "event_id": (v.get("event_id") or "")[:8] or None,
    }


# =============================================================== chain + status
CHAIN = [("Rush", "Rush detected", "app"), ("Crash", "Crash reported to NudgeBee", "app"),
         ("NudgeBee cause", "Cause found by NudgeBee", "NudgeBee"), ("Volunteer yes", "Volunteer said yes", "Sarvam"),
         ("NudgeBee approval", "NudgeBee approved", "NudgeBee"), ("Flagsmith flags", "Flags flipped", "Flagsmith"),
         ("Recovered", "Booking recovered", "app")]


def chain_block(v, map_mode):
    tl = _timeline(v)
    seen = "Rush detected" in tl or bool(tl)
    on = []
    for label, step, who in CHAIN:
        o = (step in tl) or (step == "Flags flipped" and seen and map_mode == "lite")
        on.append(o)
    last = max([i for i, o in enumerate(on) if o], default=-1)
    return [{"label": l, "owner": w, "on": on[i], "next": (i == last + 1 and seen), "t": tl.get(s)}
            for i, (l, s, w) in enumerate(CHAIN)]


def status_payload():
    v = _volunteer()
    s = _safe(sarvam_block, v)
    f = _safe(flagsmith_block, v)
    n = _safe(nudgebee_block, v)
    mm = None
    if isinstance(f, dict):
        mm = next((x.get("value") for x in f.get("flags", []) if x["flag"] == "map_mode"), None)
    return {"now": time.time(), "sarvam": s, "flagsmith": f, "nudgebee": n,
            "chain": _safe(chain_block, v, mm) if v else [], "simulated": True,
            "simulated_note": "Simulated: the crowd, the rush load and the pilgrims. Real: every Sarvam call, Flagsmith value and NudgeBee event shown here."}


@router.get("/api/sponsors/status")
def api_status():
    try:
        return status_payload()
    except Exception as e:  # never an error page
        return JSONResponse({"now": time.time(), "error": "not available", "detail": e.__class__.__name__,
                             "sarvam": {"available": False}, "flagsmith": {"available": False},
                             "nudgebee": {"available": False}, "chain": []})


def _file(name, media):
    p = UI / name
    if not p.exists():
        return JSONResponse({"error": name + " is missing"}, status_code=404)
    return FileResponse(p, media_type=media, headers={"Cache-Control": "no-cache"})


@router.get("/sponsors")
def page():
    return _file("sponsors.html", "text/html")


@router.get("/sponsors/sponsors.js")
def page_js():
    return _file("sponsors.js", "application/javascript")


@router.get("/sponsors/sponsors.css")
def page_css():
    return _file("sponsors.css", "text/css")


install_recorder()
install_crash_recorder()
_load_calls()
