"""Lane C tests: Sarvam is mocked everywhere. No network."""
import sys, types
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import directions, sarvam, volunteer  # noqa: E402


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("STATE_FILE", str(tmp_path / "s.json"))
    monkeypatch.setenv("INCIDENT_TOKEN", "tok")
    monkeypatch.setenv("SARVAM_API_KEY", "")
    monkeypatch.setenv("NUDGEBEE_APPROVE_WEBHOOK", "")
    volunteer.reset()
    app = FastAPI()
    app.include_router(directions.router)
    app.include_router(volunteer.router)
    return TestClient(app)


def fake_modules(monkeypatch, booked=None):
    qs = types.ModuleType("queue_sim")
    qs.snapshot = lambda: {"gates": [{"id": "g1", "name": "Main Gate", "wait_min": 20, "load": .5},
                                         {"id": "g2", "name": "River Crossing", "wait_min": 55, "load": .9}]}
    qs.reported = []
    qs.report_crowd = lambda g, n: qs.reported.append((g, n)) or True
    sl = types.ModuleType("slots")
    sl.book = lambda uid, gate, when=None, mode="open", walk_in=False: (
        booked.append((uid, gate, when)) if booked is not None else None) or ({"label": "09:30 to 09:45"}, False)
    fl = types.ModuleType("flags")
    fl.traits = []
    fl.set_traits = lambda uid, t: fl.traits.append((uid, t))
    fl.invalidate_cache = lambda: None
    fl.map_mode = lambda: "lite"
    fl.slot_mode = lambda: "open"
    for n, m in (("queue_sim", qs), ("slots", sl), ("flags", fl)):
        monkeypatch.setitem(sys.modules, n, m)
    return qs, sl, fl


# ---- intents in six languages
@pytest.mark.parametrize("text,intent", [
    ("book a slot tomorrow morning", "book"), ("how long is the wait at the river crossing", "wait"),
    ("I am with my mother, she is 70", "age"), ("is this booking site real", "verify"),
    ("स्लॉट बुक करो", "book"), ("नदी पर इंतज़ार कितना है", "wait"),
    ("ബുക്ക് ചെയ്യണം", "book"), ("എത്ര സമയം കാത്തിരിക്കണം", "wait"),
    ("பதிவு செய்ய வேண்டும்", "book"), ("எவ்வளவு நேரம் காத்திருப்பு", "wait"),
    ("స్లాట్ బుక్ చేయండి", "book"), ("ఎంత సమయం వేచి ఉండాలి", "wait"),
    ("ಸ್ಲಾಟ್ ಬುಕ್ ಮಾಡಿ", "book"), ("ಎಷ್ಟು ಸಮಯ ಕಾಯಬೇಕು", "wait"),
    ("walk-in pilgrim, no phone, 2 people", "walkin"), ("blah", "unknown"),
])
def test_keyword_intent(text, intent):
    assert directions.keyword_intent(text)["intent"] == intent


def test_age_and_when():
    i = directions.keyword_intent("I am with my mother, she is 70")
    assert i["age"] == 70
    assert directions.keyword_intent("book tomorrow morning")["when"] == "tomorrow morning"


def test_stub_when_lane_b_missing(env, monkeypatch):
    for n in ("queue_sim", "slots"):
        monkeypatch.setitem(sys.modules, n, None)
    j = env.post("/api/directions", data={"text": "book a slot", "lang": "en", "uid": "u"}).json()
    assert "not connected" in j["reply_text"] and j["audio_base64"] is None and "latency" in j


def test_book_wait_age(env, monkeypatch):
    booked = []
    qs, sl, fl = fake_modules(monkeypatch, booked)
    j = env.post("/api/directions", data={"text": "book a slot tomorrow morning", "lang": "hi", "uid": "u1"}).json()
    assert "09:30" in j["reply_text"] and booked[0][1] == "g1"
    j = env.post("/api/directions", data={"text": "how long is the wait at the river crossing", "lang": "en"}).json()
    assert "55" in j["reply_text"] and "River Crossing" in j["reply_text"]
    j = env.post("/api/directions", data={"text": "I am with my mother, she is 70", "lang": "en", "uid": "u2"}).json()
    assert j["age_set"] and fl.traits[0][0] == "u2" and fl.traits[0][1]["age_65_plus"]


def test_walkin_and_verify(env, monkeypatch):
    booked = []
    fake_modules(monkeypatch, booked)
    j = env.post("/api/directions", data={"text": "walk-in for 3 people, tomorrow evening", "lang": "ml", "walkin": "1"}).json()
    assert j["intent"] == "walkin" and booked[0][0].startswith("walkin-") and "3" in j["reply_text"]
    j = env.post("/api/directions", json={"text": "is darshan-booking-fast.com real?", "lang": "en"}).json()
    assert "fake" in j["reply_text"].lower() and ".gov.in" in j["reply_text"]
    j = env.post("/api/directions", data={"text": "is this booking site real", "lang": "te"}).json()
    assert j["intent"] == "verify" and "gov.in" in j["reply_text"]


def test_tts_402_notice(env, monkeypatch):
    fake_modules(monkeypatch)
    monkeypatch.setenv("SARVAM_API_KEY", "x")
    def boom(*a, **k): raise sarvam.SarvamNoCredits("x")
    monkeypatch.setattr(sarvam, "tts", boom)
    j = env.post("/api/directions", data={"text": "wait at main gate", "lang": "en"}).json()
    assert j["notice"] == sarvam.NO_CREDITS_MSG and j["audio_base64"] is None and j["reply_text"]


def test_audio_path_mocked(env, monkeypatch):
    fake_modules(monkeypatch)
    monkeypatch.setenv("SARVAM_API_KEY", "x")
    monkeypatch.setattr(sarvam, "stt", lambda *a: sarvam.STTResult("ಎಷ್ಟು ಸಮಯ ಕಾಯಬೇಕು", "kn", 120))
    monkeypatch.setattr(sarvam, "tts", lambda t, l: sarvam.AudioResult(b"RIFFwav", 90))
    j = env.post("/api/directions", files={"audio": ("a.webm", b"zz", "audio/webm")}, data={"uid": "u"}).json()
    assert j["lang"] == "kn" and j["audio_base64"] and j["latency"]["stt_ms"] == 120 and j["latency"]["tts_ms"] == 90


# ---- sarvam client
def test_402_raises(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "x")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(402, text='{"error":"No credits available."}'))
    for f in (lambda: sarvam.translate("hi", "ml"), lambda: sarvam.tts("hi", "ml"), lambda: sarvam.chat("s", "u"),
              lambda: sarvam.stt(b"x")):
        with pytest.raises(sarvam.SarvamNoCredits):
            f()


def test_timeout_and_nokey(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "x")
    def to(*a, **k): raise httpx.ReadTimeout("t")
    monkeypatch.setattr(httpx, "post", to)
    with pytest.raises(sarvam.SarvamError, match="timed out"):
        sarvam.translate("hi", "ml")
    monkeypatch.setenv("SARVAM_API_KEY", "")
    with pytest.raises(sarvam.NoKey):
        sarvam.tts("hi", "ml")


def test_request_shapes(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "x")
    seen = {}
    def post(url, **k):
        seen[url.rsplit("/", 1)[-1]] = k
        return httpx.Response(200, json={"transcript": "hi", "language_code": "ml-IN", "translated_text": "t",
                                         "audios": ["UklGRg=="], "choices": [{"message": {"content": "<think>x</think>ok"}}]},
                              request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "post", post)
    r = sarvam.stt(b"x"); assert r.language == "ml" and seen["speech-to-text"]["data"]["mode"] == "codemix"
    assert seen["speech-to-text"]["timeout"] == 8
    sarvam.translate("hi", "ml"); assert seen["translate"]["json"]["target_language_code"] == "ml-IN"
    assert sarvam.tts("hi", "ta").wav == b"RIFF" and seen["text-to-speech"]["json"]["target_language_code"] == "ta-IN"
    assert sarvam.chat("s", "u").text == "ok"


# ---- volunteer flow
@pytest.mark.parametrize("text,d", [("ശരി", "yes"), ("ശരി, ചെയ്യൂ.", "yes"), ("വേണ്ട", "no"), ("ஆம்", "yes"),
    ("இல்லை", "no"), ("అవును", "yes"), ("వద్దు", "no"), ("ಹೌದು", "yes"), ("ಬೇಡ", "no"), ("हाँ", "yes"),
    ("नहीं", "no"), ("yes please", "yes"), ("no", "no"), ("hmm", "unclear"), ("ശരി വേണ്ട", "unclear")])
def test_keyword_decision(text, d):
    assert volunteer.keyword_decision(text) == d


def incident(c, ev="e1"):
    return c.post("/api/incident", headers={"X-Incident-Token": "tok"},
                  json={"summary": "OOMKilled", "root_cause": "map tiles", "proposed_fix": "lite", "event_id": ev})


def test_incident_auth(env):
    assert env.post("/api/incident", json={}).status_code == 401
    assert env.post("/api/incident", json={}, headers={"X-Incident-Token": "bad"}).status_code == 401


def test_full_flow_with_webhook(env, monkeypatch):
    fake_modules(monkeypatch)
    monkeypatch.setenv("NUDGEBEE_APPROVE_WEBHOOK", "http://nb/hook")
    hook = []
    monkeypatch.setattr(httpx, "post", lambda url, **k: hook.append((url, k["json"])) or httpx.Response(200))
    monkeypatch.setattr(volunteer, "watch_flags", lambda *a, **k: volunteer.watch_flags.__wrapped__() if False else None)
    assert incident(env).json()["ok"]
    s = env.get("/api/volunteer/state").json()
    assert s["status"] == "asking" and "തിരക്ക്" in s["question_text"] and s["question_en"].startswith("Heavy rush")
    assert [t["step"] for t in s["timeline"]] == STEPS3
    assert env.post("/api/volunteer/reply", data={"text": "ശരി"}).json()["decision"] == "yes"
    assert hook[0][1]["approved_by"] == "Temple volunteer (voice)" and hook[0][1]["event_id"] == "e1"
    s = env.get("/api/volunteer/state").json()
    assert s["status"] == "approved" and s["webhook_ok"]
    assert env.post("/api/volunteer/reply", data={"text": "ശരി"}).json()["decision"] == "ignored"


STEPS3 = ["Rush detected", "Cause found by NudgeBee", "Asked the volunteer"]


def test_no_webhook_configured(env, monkeypatch):
    fake_modules(monkeypatch)
    monkeypatch.setattr(volunteer, "watch_flags", lambda *a, **k: None)
    monkeypatch.setattr(httpx, "post", lambda *a, **k: pytest.fail("no webhook call expected"))
    incident(env)
    env.post("/api/volunteer/reply", json={"text": "yes"})
    s = env.get("/api/volunteer/state").json()
    assert s["webhook_ok"] is False and any("NudgeBee webhook not configured" in n for n in s["notes"])
    assert "NudgeBee approved" not in [t["step"] for t in s["timeline"]]


def test_declined(env, monkeypatch):
    fake_modules(monkeypatch)
    incident(env)
    assert env.post("/api/volunteer/reply", data={"text": "no"}).json()["decision"] == "no"
    assert env.get("/api/volunteer/state").json()["status"] == "declined"


def test_watch_flags_completes(env, monkeypatch):
    fake_modules(monkeypatch)
    incident(env)
    volunteer.watch_flags(timeout=3, interval=0.1)
    s = env.get("/api/volunteer/state").json()
    steps = [t["step"] for t in s["timeline"]]
    assert "Flags flipped" in steps and steps[-1] == "Booking recovered" and s["status"] == "recovered"


def test_persistence(env, monkeypatch):
    fake_modules(monkeypatch)
    incident(env)
    volunteer.STATE["event_id"] = None
    volunteer.load()
    assert volunteer.STATE["event_id"] == "e1"


def test_crowd_report(env, monkeypatch):
    qs, _, _ = fake_modules(monkeypatch)
    j = env.post("/api/volunteer/crowd-report", data={"text": "River Crossing, about two thousand waiting"}).json()
    assert j["report"]["count"] == 2000 and j["report"]["applied"] and qs.reported == [("g2", 2000)]
    assert volunteer.parse_count("about 1,500 people") == 1500
    j = env.post("/api/volunteer/crowd-report", data={"text": "many people"}).json()
    assert "error" in j["report"]
