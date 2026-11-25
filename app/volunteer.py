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
import os
import sarvam

router = APIRouter()

STEPS = ["Rush detected", "Crash reported to NudgeBee", "Cause found by NudgeBee", "Asked the volunteer", "Volunteer said yes",
         "NudgeBee approved", "Flags flipped", "Booking recovered"]
QUESTION_EN = "Heavy rush. Shall I switch to staggered slots? Every pilgrim still gets a slot."
QUESTION_ML = "വലിയ തിരക്ക്. സ്ലോട്ടുകൾ ഇടവിട്ട രീതിയിലേക്ക് മാറ്റട്ടെ? എല്ലാ തീർത്ഥാടകർക്കും സ്ലോട്ട് ലഭിക്കും."
CONFIRM_EN = "Done. Slots are staggered and the map is light. Every pilgrim can still book."
CONFIRM_ML = "ശരി. സ്ലോട്ടുകൾ ഇടവിട്ട രീതിയിലായി, മാപ്പ് ലഘുവായി. എല്ലാ തീർത്ഥാടകർക്കും ഇപ്പോഴും ബുക്ക് ചെയ്യാം."
UNCLEAR_EN = "Sorry, please say yes or no."
UNCLEAR_ML = "ക്ഷമിക്കണം, ശരി എന്നോ വേണ്ട എന്നോ പറയൂ."
NO_WEBHOOK_NOTE = "NudgeBee webhook not configured"
APPROVED_BY = "Temple volunteer (voice)"

# Strong yes words say yes on their own. Weak ones are verbs ("do it", "kar do") and lose against any no word.
YES = {"ml": ["ശരി", "സരി", "ശെരി", "സെരി", "ഷെറി", "ഷെരി", "ചെയ്യാം", "ഉവ്വ്", "അതെ", "ആം", "ആണ്", "ആയിക്കോട്ടെ", "സമ്മതം", "sari", "shari", "sheri", "sedi", "seri", "athe", "aam", "uvve", "ok", "okay"],
       "ta": ["ஆம்", "ஆமா", "ஆமாம்", "சரி", "aam", "aama", "aamaam", "sari", "seri"],
       "te": ["అవును", "ఔను", "సరే", "అలాగే", "avunu", "sare", "sarey"],
       "kn": ["ಹೌದು", "ಸರಿ", "ಆಯ್ತು", "ಓಕೆ", "haudu", "houdu", "aytu", "aythu", "sari"],
       "hi": ["हाँ", "हां", "हाँजी", "जी", "ठीक", "ओके", "सही", "haan", "han", "haa", "theek", "thik", "ji", "sahi"],
       "en": ["yes", "yeah", "yep", "yup", "ok", "okay", "sure", "approve", "approved", "alright", "fine", "right"]}
YES_WEAK = {"ml": ["ചെയ്യൂ", "ചെയ്യു", "ചെയ്തോളൂ", "ചെയ്തോ", "മാറ്റിക്കോ", "മാറ്റിക്കോളൂ", "മാറ്റൂ", "മാറ്റ്", "cheyyu", "maattikko", "mattikko"],
            "ta": ["செய்", "பண்ணு", "பண்ணுங்க", "பண்ணுங்கள்", "செய்யுங்க", "செய்யுங்கள்", "மாத்து", "மாத்துங்க", "pannunga", "panni", "seiyungal"],
            "te": ["చేయండి", "చెయ్యండి", "చేయి", "చెయ్యి", "చేయు", "మార్చండి", "cheyyandi", "cheyandi"],
            "kn": ["ಮಾಡಿ", "ಮಾಡು", "ಬದಲಿಸಿ", "maadi", "madi"],
            "hi": ["कर", "करो", "करिए", "कीजिए", "कीजिये", "बदल", "kar", "karo", "kijiye"],
            "en": ["go", "please", "proceed", "switch", "change", "ahead"]}
NO = {"ml": ["വേണ്ട", "വേണ്ടാ", "വേണ്ടേ", "ഇല്ല", "venda", "vendaa", "illa"],
      "ta": ["இல்லை", "இல்ல", "வேண்டாம்", "வேணாம்", "வேண்டாங்க", "illai", "illa", "vendam", "venam", "vendaam"],
      "te": ["వద్దు", "వద్దండి", "లేదు", "కాదు", "vaddu", "ledu", "kadu"],
      "kn": ["ಬೇಡ", "ಬೇಡಾ", "ಇಲ್ಲ", "beda", "illa"],
      "hi": ["नहीं", "नही", "मत", "रहने", "nahi", "nahin", "nahee", "mat"],
      "en": ["no", "nope", "don't", "dont", "stop", "cancel", "not", "never"]}
_YES_ALL = {w for ws in YES.values() for w in ws}
_YES_WEAK_ALL = {w for ws in YES_WEAK.values() for w in ws}
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
def _cache_path(text, lang):
    import hashlib
    d = os.path.join(os.path.dirname(config.STATE_FILE()) or ".", "voice_cache")
    return os.path.join(d, hashlib.sha1(f"{lang}|{text}".encode()).hexdigest()[:16] + ".wav")


def _speak(text, lang="ml"):
    """Returns (wav or None, ms, note or None). The fixed demo sentences are cached on disk, so the volunteer
    question and the confirmation play at once (ms is 0 on a cache hit)."""
    path = _cache_path(text, lang)
    # the volume cache first, then the copy shipped in the image (app/voice_seed): audio rendered by real Sarvam bulbul
    for p in (path, os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_seed", os.path.basename(path))):
        try:
            with open(p, "rb") as f:
                w = f.read()
            if len(w) > 1000:
                return w, 0, None
        except OSError:
            pass
    if not sarvam.available():
        return None, 0, "Voice unavailable (no Sarvam key). Type instead."
    try:
        a = sarvam.tts(text, lang)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(a.wav)
        except OSError:
            pass
        return a.wav, a.ms, None
    except sarvam.SarvamNoCredits:
        return None, 0, sarvam.NO_CREDITS_MSG
    except sarvam.SarvamError as e:
        return None, 0, f"Voice unavailable ({e}). Type instead."


def warm_cache():
    """Pre-render the fixed Malayalam sentences (question, confirmation, please-say-yes-or-no)."""
    for t in (QUESTION_ML, CONFIRM_ML, UNCLEAR_ML):
        _speak(t, "ml")


def mark_rush_detected():
    mark("Rush detected")


def mark_crash_reported():
    mark("Crash reported to NudgeBee")


def mark_crash_seen(sent):
    """The app restarted during a rush. Shown on the timeline even when the webhook is not set."""
    mark("Rush detected")
    if sent:
        mark_crash_reported()
    else:
        note("Crash seen, but not reported to NudgeBee (webhook missing or failed)")


ROOT_CAUSE_MAX = 1500


def start_incident(summary, root_cause, proposed_fix, event_id):
    """Called when NudgeBee reports a cause. Builds the Malayalam question (text now, audio right after)."""
    summary = _clean(summary)
    root_cause = _clean(root_cause)[:ROOT_CAUSE_MAX]
    with _lock:
        if STATE["event_id"] == event_id and STATE["status"] != "idle":
            return  # NudgeBee may post the same event twice
        keep = {t["step"]: t["t"] for t in STATE["timeline"]
                if t["step"] in ("Rush detected", "Crash reported to NudgeBee")}
        reset()
        STATE.update(event_id=event_id, summary=summary, root_cause=root_cause, proposed_fix=proposed_fix,
                     question_text=QUESTION_ML, question_en=QUESTION_EN, status="asking")
        for step, tt in keep.items():
            STATE["timeline"].append({"step": step, "t": tt})
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


def _clean(x):
    return "" if x is None else str(x).strip()


def is_busy():
    with _lock:
        return STATE["status"] in ("asking", "approved")


# ---------------------------------------------------------------- yes / no
def _tokens(text):
    return [t for t in re.split(r"[\s,.;:!?।\"()\[\]\-]+", (text or "").lower().replace("‌", "")) if t]


def _match(tok, words):
    for w in words:
        if tok == w or (len(w) >= 3 and not w.isascii() and tok.startswith(w)):
            return True
    return False


def keyword_decision(text):
    toks = _tokens(text)
    strong = any(_match(t, _YES_ALL) for t in toks)
    weak = any(_match(t, _YES_WEAK_ALL) for t in toks)
    n = any(_match(t, _NO_ALL) for t in toks)
    if n:
        contradiction = strong or any(t in ("go", "ahead", "proceed") for t in toks)
        return "unclear" if contradiction else "no"   # "no" with a strong yes is contradictory: never approve
    return "yes" if (strong or weak) else "unclear"


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


async def _text_or_audio(request: Request, reply=False):
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
        fn, ctype = up.filename or "reply.webm", up.content_type or "audio/webm"
        r = await run_in_threadpool(sarvam.stt, data, fn, ctype)
        text, ms = r.transcript.strip(), r.ms
        if reply and text and keyword_decision(text) == "unclear" and len(text.split()) <= 4:
            # A short answer that auto-detect could not read: listen again as Malayalam (the question language),
            # then as English. First reading that gives a clear yes or no wins.
            for lang in ("ml", "en"):
                try:
                    r2 = await run_in_threadpool(sarvam.stt, data, fn, ctype, lang, "transcribe")
                except sarvam.SarvamError:
                    break
                ms += r2.ms
                if keyword_decision(r2.transcript) != "unclear":
                    text = text + " | " + r2.transcript.strip()
                    break
        return text, None, ms
    except sarvam.SarvamNoCredits:
        return "", {"transcript": "", "decision": "unavailable", "notice": sarvam.NO_CREDITS_MSG}, 0
    except sarvam.SarvamError as e:
        return "", {"transcript": "", "decision": "unavailable", "notice": f"Voice unavailable ({e}). Type instead."}, 0


_FIELDS = ("event_id", "summary", "root_cause", "proposed_fix")


def tolerant_parse(raw):
    """Parse an incident body that may be slightly broken JSON (raw newlines, unescaped quotes, markdown).
    Falls back to cutting the text between the four known keys. Returns a dict (possibly empty)."""
    raw = (raw or "").strip()
    try:
        d = json.loads(raw, strict=False)
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    keys = "|".join(_FIELDS)
    marks = [(m.start(), m.end(), m.group(1)) for m in
             re.finditer(r'["\']?\b(' + keys + r')\b["\']?\s*[:=]\s*', raw)]
    out = {}
    for i, (_, end, name) in enumerate(marks):
        chunk = raw[end: marks[i + 1][0] if i + 1 < len(marks) else len(raw)]
        chunk = chunk.strip()
        if i + 1 < len(marks):
            chunk = re.sub(r'[,&\s]+$', '', chunk)
        else:
            chunk = re.sub(r'[\s}]+$', '', chunk)
        chunk = chunk.rstrip(",").strip()
        if len(chunk) >= 2 and chunk[0] in "\"'" and chunk[-1] == chunk[0]:
            chunk = chunk[1:-1]
        elif chunk[:1] in "\"'":
            chunk = chunk[1:]
        out[name] = chunk.replace('\\n', "\n").replace('\\"', '"')
    return out


async def read_incident_body(request):
    ct = request.headers.get("content-type", "").lower()
    raw = (await request.body()).decode("utf-8", "replace")
    if "form" in ct and not raw.lstrip().startswith("{"):  # curl -d sends JSON as a form type
        from urllib.parse import parse_qsl
        try:
            return dict(parse_qsl(raw, keep_blank_values=True))
        except Exception:
            pass
    return tolerant_parse(raw)


@router.post("/api/incident")
async def api_incident(request: Request, x_incident_token: str = Header(None), force: int = 0):
    from starlette.concurrency import run_in_threadpool
    _check_token(x_incident_token)
    b = await read_incident_body(request)
    if not any(b.get(k) for k in ("summary", "root_cause", "proposed_fix")):
        raise HTTPException(400, "no summary or root_cause found in the body")
    if not force and is_busy():
        return {"ok": True, "status": "duplicate"}
    eid = str(b.get("event_id") or "").strip() or f"evt-{int(time.time() * 1000)}"
    await run_in_threadpool(start_incident, b.get("summary"), b.get("root_cause"), b.get("proposed_fix"), eid)
    return {"ok": True, "status": STATE["status"], "event_id": eid}


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
    text, err, stt_ms = await _text_or_audio(request, reply=True)
    if err:
        return err
    if not text:
        return {"transcript": "", "decision": "unclear", "notice": "Nothing heard. Tap Yes or No.", "message": UNCLEAR_EN, "message_ml": UNCLEAR_ML}
    decision = await run_in_threadpool(handle_reply, text)
    with _lock:
        STATE["latency"]["stt_ms"] = stt_ms
        _save()
    out = {}
    if decision == "unclear":
        out = {"message": UNCLEAR_EN, "message_ml": UNCLEAR_ML}
    return {**out, "transcript": text, "decision": decision, "latency": {"stt_ms": stt_ms, **STATE["latency"]}}


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
try:
    threading.Thread(target=warm_cache, daemon=True).start()
except Exception:
    pass
