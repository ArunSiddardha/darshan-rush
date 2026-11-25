"""Temple volunteer incident flow: NudgeBee finds the cause, we ask the volunteer by voice in Malayalam,
a spoken yes triggers the NudgeBee approval webhook, we watch Flagsmith until map_mode is lite.

Routes: POST /api/incident, GET /api/volunteer/state, GET /api/volunteer/audio,
POST /api/volunteer/reply, POST /api/volunteer/crowd-report, POST /api/volunteer/reset.
State is persisted to STATE_FILE.
"""
import base64
import hmac
import json
import re
import threading
import time

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response

import config
import sarvam

router = APIRouter()

STEPS = ["Rush detected", "Cause found by NudgeBee", "Asked the volunteer", "Volunteer said yes",
         "NudgeBee approved", "Flags flipped", "Booking recovered"]
QUESTION_EN = "Heavy rush. Shall I switch to staggered slots? Every pilgrim still gets a slot."
QUESTION_ML = "വലിയ തിരക്ക്. സ്ലോട്ടുകൾ ഇടവിട്ട രീതിയിലേക്ക് മാറ്റട്ടെ? എല്ലാ തീർത്ഥാടകർക്കും സ്ലോട്ട് ലഭിക്കും."
CONFIRM_EN = "Done. Slots are staggered and the map is light. Every pilgrim can still book."
CONFIRM_ML = "ശരി. സ്ലോട്ടുകൾ ഇടവിട്ട രീതിയിലായി, മാപ്പ് ലഘുവായി. എല്ലാ തീർത്ഥാടകർക്കും ഇപ്പോഴും ബുക്ക് ചെയ്യാം."
NO_WEBHOOK_NOTE = "NudgeBee webhook not configured"
APPROVED_BY = "Temple volunteer (voice)"

YES = {"ml": ["ശരി", "ഉവ്വ്", "അതെ", "ആയിക്കോട്ടെ", "സമ്മതം", "ചെയ്യൂ", "ചെയ്തോളൂ", "sari", "shari", "athe", "uvve"],
       "ta": ["ஆம்", "ஆமா", "சரி", "செய்", "aam", "aama", "seri"],
       "te": ["అవును", "ఔను", "సరే", "చేయండి", "avunu", "sare"],
       "kn": ["ಹೌದು", "ಸರಿ", "ಆಯ್ತು", "ಮಾಡಿ", "haudu", "houdu", "aytu"],
       "hi": ["हाँ", "हां", "हाँजी", "जी", "ठीक", "ओके", "कर", "haan", "han", "theek", "thik", "ji"],
       "en": ["yes", "yeah", "yep", "ok", "okay", "sure", "go", "do", "please", "approve", "approved"]}
NO = {"ml": ["വേണ്ട", "ഇല്ല", "വേണ്ടാ", "venda", "illa"],
      "ta": ["இல்லை", "வேண்டாம்", "வேணாம்", "illai", "vendam"],
      "te": ["వద్దు", "లేదు", "కాదు", "vaddu", "ledu", "kadu"],
      "kn": ["ಬೇಡ", "ಇಲ್ಲ", "beda"],
      "hi": ["नहीं", "नही", "ना", "मत", "nahi", "nahin", "mat"],
      "en": ["no", "nope", "don't", "dont", "stop", "cancel", "not"]}
_YES_ALL = {w for ws in YES.values() for w in ws}
_NO_ALL = {w for ws in NO.values() for w in ws}

_lock = threading.RLock()


def _blank():
    return {"status": "idle", "event_id": None, "summary": None, "root_cause": None, "proposed_fix": None,
            "question_text": None, "question_en": None, "audio": None, "confirm_text": None, "confirm_audio": None,
            "transcript": None, "decision": None, "webhook_ok": None, "webhook_error": None, "timeline": [],
            "notes": [], "latency": {}, "crowd_reports": []}


STATE = _blank()
_AUDIO_KEYS = ("audio", "confirm_audio")


# ---------------------------------------------------------------- persistence / timeline
def _save():
    try:
        with open(config.STATE_FILE(), "w") as f:
            json.dump({k: (base64.b64encode(v).decode() if k in _AUDIO_KEYS and v else v) for k, v in STATE.items()}, f)
    except Exception:
        pass


def load():
    try:
        with open(config.STATE_FILE()) as f:
            d = json.load(f)
        for k in _AUDIO_KEYS:
            d[k] = base64.b64decode(d[k]) if d.get(k) else None
        with _lock:
            STATE.update({k: v for k, v in d.items() if k in STATE})
    except Exception:
        pass


def reset():
    with _lock:
        STATE.clear()
        STATE.update(_blank())
        _save()


def mark(step):
    with _lock:
        if not any(t["step"] == step for t in STATE["timeline"]):
            STATE["timeline"].append({"step": step, "t": time.time()})
        _save()


def note(msg):
    with _lock:
        if msg not in STATE["notes"]:
            STATE["notes"].append(msg)
        _save()


def public():
    with _lock:
        d = {k: v for k, v in STATE.items() if k not in _AUDIO_KEYS}
        d["has_audio"] = bool(STATE["audio"])
        d["has_confirm_audio"] = bool(STATE["confirm_audio"])
        d["steps"] = STEPS
        d["voice_available"] = sarvam.available()
        return d


# ---------------------------------------------------------------- speaking
def _speak(text, lang="ml"):
    """Returns (wav or None, ms, note or None)."""
    if not sarvam.available():
        return None, 0, "Voice unavailable (no Sarvam key). Type instead."
    try:
        a = sarvam.tts(text, lang)
        return a.wav, a.ms, None
    except sarvam.SarvamNoCredits:
        return None, 0, sarvam.NO_CREDITS_MSG
    except sarvam.SarvamError as e:
        return None, 0, f"Voice unavailable ({e}). Type instead."


def mark_rush_detected():
    mark("Rush detected")


def start_incident(summary, root_cause, proposed_fix, event_id):
    """Called when NudgeBee reports a cause. Builds the Malayalam question (text now, audio right after)."""
    with _lock:
        if STATE["event_id"] == event_id and STATE["status"] != "idle":
            return  # NudgeBee may post the same event twice
        t_rush = next((t["t"] for t in STATE["timeline"] if t["step"] == "Rush detected"), None)
        reset()
        STATE.update(event_id=event_id, summary=summary, root_cause=root_cause, proposed_fix=proposed_fix,
                     question_text=QUESTION_ML, question_en=QUESTION_EN, status="asking")
        if t_rush:
            STATE["timeline"].append({"step": "Rush detected", "t": t_rush})
        mark("Rush detected")
        mark("Cause found by NudgeBee")
        mark("Asked the volunteer")
    wav, ms, n = _speak(QUESTION_ML)
    with _lock:
        STATE["audio"] = wav
        STATE["latency"]["question_tts_ms"] = ms
        if n:
            STATE["notes"].append(n)
        _save()


# ---------------------------------------------------------------- yes / no
def _tokens(text):
    return [t for t in re.split(r"[\s,.;:!?।\"'()\[\]\-]+", (text or "").lower().replace("‌", "")) if t]


def _match(tok, words):
    for w in words:
        if tok == w or (len(w) >= 3 and not w.isascii() and tok.startswith(w)):
            return True
    return False


def keyword_decision(text):
    toks = _tokens(text)
    y = any(_match(t, _YES_ALL) for t in toks)
    n = any(_match(t, _NO_ALL) for t in toks)
    if y == n:
        return "unclear"
    return "yes" if y else "no"


def classify(text):
    """Keywords first (six languages); LLM only when keywords cannot tell. Returns (decision, llm_ms)."""
    d = keyword_decision(text)
    if d != "unclear" or not text.strip() or not sarvam.available():
        return d, 0
    try:
        j, ms = sarvam.chat_json(
            "A temple volunteer was asked in Malayalam whether to switch to staggered slots. Classify the spoken answer "
            "(Malayalam, Tamil, Telugu, Kannada, Hindi or English). Return ONLY JSON "
            '{"decision": "yes"|"no"|"unclear"}.', text)
        v = str(j.get("decision", "unclear")).lower()
        return (v if v in ("yes", "no") else "unclear"), ms
    except Exception:
        return "unclear", 0


# ---------------------------------------------------------------- flags / webhook
def map_is_lite():
    import flags
    try:
        flags.invalidate_cache()
    except Exception:
        pass
    f = getattr(flags, "map_mode", None)
    if callable(f):
        return str(f()).lower() == "lite"
    return bool(flags.lite_mode())


def post_webhook(payload):
    url = config.NUDGEBEE_APPROVE_WEBHOOK()
    if not url:
        raise RuntimeError(NO_WEBHOOK_NOTE)
    try:
        r = httpx.post(url, json=payload, timeout=15)
    except httpx.HTTPError as e:
        raise RuntimeError(f"webhook network error: {e.__class__.__name__}")
    if r.status_code >= 400:
        raise RuntimeError(f"webhook {r.status_code}: {r.text[:150]}")


def handle_reply(transcript, watch=True):
    """Returns decision. Acts only while status == 'asking'."""
    with _lock:
        if STATE["status"] != "asking":
            return "ignored"
        STATE["transcript"] = transcript
    decision, ms = classify(transcript)
    with _lock:
        STATE["decision"] = decision
        STATE["latency"]["classify_ms"] = ms
        _save()
    if decision == "no":
        with _lock:
            STATE["status"] = "declined"
            _save()
    elif decision == "yes":
        mark("Volunteer said yes")
        with _lock:
            payload = {"event_id": STATE["event_id"], "approved_by": APPROVED_BY, "transcript": transcript}
        configured = bool(config.NUDGEBEE_APPROVE_WEBHOOK())
        try:
            post_webhook(payload)
            ok, err = True, None
        except Exception as e:
            ok, err = False, str(e)
        with _lock:
            STATE.update(status="approved", webhook_ok=ok, webhook_error=err)
            _save()
        if ok:
            mark("NudgeBee approved")
        elif not configured:
            note(NO_WEBHOOK_NOTE + ": nothing was changed. Approve in NudgeBee by hand.")
        else:
            note("Approval webhook failed: " + str(err))
        if watch and (ok or not configured):
            threading.Thread(target=watch_flags, daemon=True).start()
    return decision


def watch_flags(timeout=180, interval=2.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            lite = map_is_lite()
        except Exception as e:
            note(f"flag check failed: {e}")
            lite = False
        if lite:
            mark("Flags flipped")
            wav, ms, n = _speak(CONFIRM_ML)
            with _lock:
                STATE.update(confirm_text=CONFIRM_ML, confirm_audio=wav, status="recovered")
                STATE["latency"]["confirm_tts_ms"] = ms
                if n:
                    STATE["notes"].append(n)
            mark("Booking recovered")
            return True
        time.sleep(interval)
    note("Timed out waiting for map_mode to become lite")
    return False


# ---------------------------------------------------------------- crowd report
_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
              "ten": 10, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "hundred": 100, "thousand": 1000}
_DIG = str.maketrans("०१२३४५६७८९೦೧೨೩೪೫೬೭೮೯൦൧൨൩൪൫൬൭൮൯౦౧౨౩౪౫౬౭౮౯௦௧௨௩௪௫௬௭௮௯", "0123456789" * 5)


def parse_count(text):
    low = (text or "").lower().translate(_DIG).replace(",", "")
    m = re.search(r"\d+", low)
    if m:
        n = int(m.group(0))
        if re.search(r"\d\s*(?:k|thousand|हज़ार|हजार|ആയിരം|ஆயிரம்|వేల|ಸಾವಿರ)", low) and n < 1000:
            n *= 1000
        return n
    total, cur = 0, 0
    found = False
    for w in re.findall(r"[a-z]+", low):
        v = _NUM_WORDS.get(w)
        if v is None:
            continue
        found = True
        if v in (100, 1000):
            cur = max(cur, 1) * v
            if v == 1000:
                total, cur = total + cur, 0
        else:
            cur += v
    return total + cur if found else None


def apply_crowd_report(text, uid="volunteer"):
    """Parse 'River Crossing, about two thousand waiting' and update queue_sim if present."""
    import directions
    count = parse_count(text)
    gate_id, gate_name = None, None
    gates = directions.get_gates(uid) or []
    g = directions.pick_gate(gates, directions.keyword_intent(text)["gate_hint"]) if gates else None
    if g:
        gate_id, gate_name = g.get("id"), g.get("name")
    rec = {"text": text, "count": count, "gate": gate_name or gate_id, "t": time.time(), "applied": False}
    if count is None:
        rec["error"] = "No number heard. Say for example: River Crossing, about two thousand waiting."
        return rec
    try:
        import queue_sim
        f = next((getattr(queue_sim, n) for n in ("report_crowd", "crowd_report", "set_crowd", "report", "update_crowd")
                  if callable(getattr(queue_sim, n, None))), None)
        if f and (gate_id or gate_name):
            f(gate_id or gate_name, count)
            rec["applied"] = True
        elif not f:
            rec["note"] = "queue_sim has no crowd-report function yet; saved only"
        else:
            rec["note"] = "Gate not recognised; saved only"
    except ImportError:
        rec["note"] = "queue_sim not available yet; saved only"
    except Exception as e:
        rec["note"] = f"queue_sim error: {e}"
    return rec


# ---------------------------------------------------------------- routes
def _check_token(tok):
    expected = config.INCIDENT_TOKEN()
    if not expected:
        raise HTTPException(503, "INCIDENT_TOKEN is not configured on the server")
    if not tok or not hmac.compare_digest(tok, expected):
        raise HTTPException(401, "bad incident token")


async def _text_or_audio(request: Request):
    """Returns (text, error_json or None, stt_ms). Accepts multipart (audio/text) or JSON."""
    from starlette.concurrency import run_in_threadpool
    ct = request.headers.get("content-type", "")
    if "json" in ct:
        return str((await request.json()).get("text") or "").strip(), None, 0
    form = await request.form()
    text = str(form.get("text") or "").strip()
    up = form.get("audio")
    if text or not up or not hasattr(up, "read"):
        return text, None, 0
    data = await up.read()
    try:
        r = await run_in_threadpool(sarvam.stt, data, up.filename or "reply.webm", up.content_type or "audio/webm")
        return r.transcript.strip(), None, r.ms
    except sarvam.SarvamNoCredits:
        return "", {"transcript": "", "decision": "unavailable", "notice": sarvam.NO_CREDITS_MSG}, 0
    except sarvam.SarvamError as e:
        return "", {"transcript": "", "decision": "unavailable", "notice": f"Voice unavailable ({e}). Type instead."}, 0


@router.post("/api/incident")
async def api_incident(request: Request, x_incident_token: str = Header(None)):
    from starlette.concurrency import run_in_threadpool
    _check_token(x_incident_token)
    try:
        b = await request.json()
    except Exception:
        raise HTTPException(400, "JSON body required")
    await run_in_threadpool(start_incident, b.get("summary"), b.get("root_cause"), b.get("proposed_fix"),
                            str(b.get("event_id") or f"evt-{int(time.time())}"))
    return {"ok": True, "status": STATE["status"]}


@router.post("/api/volunteer/reset")
def api_reset(x_incident_token: str = Header(None)):
    _check_token(x_incident_token)
    reset()
    return {"ok": True}


@router.get("/api/volunteer/state")
def api_state():
    return public()


@router.get("/api/volunteer/audio")
def api_audio(kind: str = "question"):
    with _lock:
        wav = STATE["confirm_audio"] if kind == "confirm" else STATE["audio"]
    if not wav:
        raise HTTPException(404, "no audio")
    return Response(wav, media_type="audio/wav", headers={"Cache-Control": "no-store"})


@router.post("/api/volunteer/reply")
async def api_reply(request: Request):
    from starlette.concurrency import run_in_threadpool
    text, err, stt_ms = await _text_or_audio(request)
    if err:
        return err
    if not text:
        return {"transcript": "", "decision": "unclear", "notice": "Nothing heard. Tap Yes or No."}
    decision = await run_in_threadpool(handle_reply, text)
    with _lock:
        STATE["latency"]["stt_ms"] = stt_ms
        _save()
    return {"transcript": text, "decision": decision, "latency": {"stt_ms": stt_ms, **STATE["latency"]}}


@router.post("/api/volunteer/crowd-report")
async def api_crowd(request: Request):
    from starlette.concurrency import run_in_threadpool
    text, err, stt_ms = await _text_or_audio(request)
    if err:
        return err
    rec = await run_in_threadpool(apply_crowd_report, text)
    with _lock:
        STATE["crowd_reports"] = (STATE["crowd_reports"] + [rec])[-10:]
        _save()
    return {"transcript": text, "report": rec, "latency": {"stt_ms": stt_ms}}


try:
    load()
except Exception:
    pass
