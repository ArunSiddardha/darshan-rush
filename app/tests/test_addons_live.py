"""Tests for addons_live. Sarvam is mocked: no network, no credits."""
import base64
import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import addons_live as L
import sarvam


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    L.reset_sessions()
    L._audio_cache.clear()
    L._warm_done.clear()
    monkeypatch.setattr(L.sarvam, "available", lambda: False)   # no warming, no TTS calls
    monkeypatch.setattr(L.directions, "speak", lambda t, lang: (base64.b64encode(b"RIFFfake").decode(), 12, None))
    monkeypatch.setattr(L.directions, "understand", lambda t, use_llm=True: (L.directions.keyword_intent(t), "keywords", 0))
    yield


def turn(sid, text, lang="en", uid="u1"):
    r, extra, end = L.handle(text, uid, sid, lang)
    return r, end


def test_full_booking_conversation():
    r, _ = turn("a", "I want a slot")
    assert "For when" in r
    r, _ = turn("a", "tomorrow morning")
    assert "how many" in r.lower()
    r, _ = turn("a", "two people")
    assert "Shall I book it" in r and "tomorrow" in r.lower()
    r, end = turn("a", "yes")
    assert "booked" in r.lower() and not end
    import slots
    assert slots.get("u1") is not None
    s = L.session("a", "en")
    assert s["state"] == "booked" and s["slot"]["label"]


def test_party_already_said_is_skipped():
    turn("b", "book a slot")
    r, _ = turn("b", "tomorrow morning for 3 people")
    assert "Shall I book it" in r


def test_unclear_never_books():
    import slots
    r, _ = turn("c", "hmm blah blah")
    assert "slot" in r.lower()
    turn("c", "book a slot")
    r, _ = turn("c", "purple elephant")
    assert "Sorry" in r and slots.total() == 0
    r, _ = turn("c", "tomorrow morning")
    r, _ = turn("c", "zzz")
    r, _ = turn("c", "qqq")           # second miss on the people question assumes one person and reads back
    assert "Shall I book it" in r
    r, _ = turn("c", "banana")
    assert "yes or no" in r and slots.total() == 0


def test_no_changes_time_and_cancel():
    import slots
    turn("d", "book a slot tomorrow morning for 2 people")
    r, _ = turn("d", "no")
    assert "For when" in r
    turn("d", "tomorrow evening")
    turn("d", "yes")
    assert slots.total() == 1
    r, _ = turn("d", "change the time")
    assert "For when" in r
    r, _ = turn("d", "cancel")
    assert "cancel" in r.lower() and slots.total() == 0
    r, _ = turn("d", "cancel")
    assert "no booking" in r.lower()


def test_repeat_wait_age_and_goodbye():
    turn("e", "book a slot")
    first = L.session("e", "en")["last_reply"]
    r, _ = turn("e", "say that again")
    assert r == first
    r, _ = turn("e", "how long is the wait at river crossing")
    assert "minutes" in r and "For when" in r        # answered, then the open question again
    r, _ = turn("e", "my mother is 70")
    assert L.session("e", "en")["state"] == "ask_when"
    r, end = turn("e", "thank you")
    assert end


def test_age_trait_is_set(monkeypatch):
    got = {}
    monkeypatch.setattr(L.directions, "set_age_trait", lambda uid, age: got.update(uid=uid, age=age) or True)
    turn("f", "my mother is 70")
    assert got == {"uid": "u1", "age": 70}


def test_language_switch_keeps_the_question():
    turn("g", "book a slot")
    r, extra, _ = L.handle("Tamil la sollunga", "u1", "g", "en")
    assert extra["lang_switched"] == "ta" and "தமிழில்" in r and "எப்போது" in r
    r, extra, _ = L.handle("நாளை காலை", "u1", "g", "en")      # session language sticks even if the client says en
    assert L.session("g", "en")["lang"] == "ta"


def test_telugu_and_malayalam_words():
    turn("h", "స్లాట్ బుక్ చేయి", "te")
    r, _ = turn("h", "రేపు ఉదయం", "te")
    assert L.session("h", "te")["state"] == "ask_party"
    r, _ = turn("h", "ఇద్దరు", "te")
    assert L.session("h", "te")["state"] == "confirm"
    r, _ = turn("h", "అవును", "te")
    assert L.session("h", "te")["state"] == "booked"
    r, end = turn("h", "ధన్యవాదాలు", "te")
    assert end


# ------------------------------------------------------------------ HTTP
def client(monkeypatch, stt_text):
    app = FastAPI()
    app.include_router(L.router)
    monkeypatch.setattr(L.sarvam, "stt", lambda *a, **k: sarvam.STTResult(stt_text[0], "en", 123))
    return TestClient(app)


def post(c, text, sid="s1"):
    return c.post("/api/live/turn", files={"audio": ("a.wav", io.BytesIO(b"RIFF" + b"\0" * 100), "audio/wav")},
                  data={"uid": "u9", "lang": "en", "session_id": sid}).json()


def test_http_turn_shape_and_noise(monkeypatch):
    box = [""]
    c = client(monkeypatch, box)
    j = post(c, "")
    assert j["ignored"] and j["audio_base64"] is None and j["reply_text"] == ""
    box[0] = "."
    assert post(c, "")["ignored"]
    box[0] = "I want a slot"
    j = post(c, "")
    for k in ("transcript", "reply_text", "audio_base64", "lang", "state", "end_session", "slot", "latency"):
        assert k in j
    assert j["state"] == "ask_when" and j["audio_base64"] and j["latency"]["stt_ms"] == 123
    box[0] = "thanks"
    assert post(c, "")["end_session"] is True


def test_http_prompt_and_cache(monkeypatch):
    c = client(monkeypatch, [""])
    j = c.post("/api/live/prompt", data={"kind": "nudge", "lang": "en"}).json()
    assert "I am listening" in j["reply_text"] and j["latency"]["tts_cached"] is False
    j = c.post("/api/live/prompt", data={"kind": "nudge", "lang": "en"}).json()
    assert j["latency"]["tts_cached"] is True
    assert c.post("/api/live/prompt", data={"kind": "x"}).status_code == 400


def test_credits_message(monkeypatch):
    app = FastAPI(); app.include_router(L.router)
    def boom(*a, **k): raise sarvam.SarvamNoCredits()
    monkeypatch.setattr(L.sarvam, "stt", boom)
    j = TestClient(app).post("/api/live/turn", files={"audio": ("a.wav", io.BytesIO(b"x" * 50), "audio/wav")}, data={"session_id": "z"}).json()
    assert j["error"] and "credits" in j["reply_text"]


def test_llm_fallback_when_stt_garbles(monkeypatch):
    monkeypatch.setattr(L.sarvam, "available", lambda: True)
    monkeypatch.setattr(L.sarvam, "chat_json", lambda s, u: ({"day": "tomorrow", "part": "morning", "party": None, "answer": None}, 5))
    turn("l", "book a slot")
    r, _ = turn("l", "రే పోదయం")
    assert "how many" in r.lower()
    monkeypatch.setattr(L.sarvam, "chat_json", lambda s, u: ({"day": None, "part": None, "party": 2, "answer": None}, 5))
    r, _ = turn("l", "ఎందరూ")
    assert "Shall I book it" in r
    monkeypatch.setattr(L.sarvam, "chat_json", lambda s, u: ({"answer": "yes"}, 5))
    r, _ = turn("l", "ఓహో అలాగే")
    assert "booked" in r.lower()
