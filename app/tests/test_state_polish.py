"""Shared state, assistant flags, knowledge-pack fallback, health guard and care hook (all mocked, no paid calls)."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

import addons_state
import assistant
import flags
import sarvam


def _client():
    app = FastAPI()
    app.include_router(addons_state.router)
    return TestClient(app)


def test_state_has_everything_for_each_role():
    c = _client()
    for role in ("pilgrim", "staff", "judge"):
        j = c.get(f"/api/state?uid=u-state&role={role}").json()
        for k in ("flags", "mode", "queue", "assistant", "map", "slot", "venue"):
            assert k in j
        assert set(j["flags"]) >= {"map_mode", "slot_mode", "assistant_llm", "venue_pack", "reply_style"}
    assert "help" in c.get("/api/state?role=staff").json()


def test_assistant_llm_off_means_no_model_call(monkeypatch):
    called = []
    monkeypatch.setattr(flags, "assistant_llm", lambda: "off")
    monkeypatch.setattr(sarvam, "available", lambda: True)
    monkeypatch.setattr(sarvam, "chat", lambda *a, **k: called.append(1))
    r = assistant.answer("purple elephant philosophy", "en", "u-off")
    assert not called and r["intent"] == "unknown"


def test_knowledge_pack_answers_without_model(monkeypatch):
    monkeypatch.setattr(sarvam, "available", lambda: False)
    r = assistant.answer("what time does darshan open", "en", "u-kb", use_model=False)
    assert r["via"] == "knowledge_pack" and "05:00" in r["reply"]


def test_reply_style_brief_in_lite(monkeypatch):
    monkeypatch.setattr(flags, "_env_value", lambda n: {"reply_style": "normal", "map_mode": "lite"}.get(n, "x"))
    assert flags.reply_style() == "brief"


def test_simulate_failure_needs_token_and_fires_once(monkeypatch):
    import config
    monkeypatch.setattr(config, "INCIDENT_TOKEN", lambda: "tok")
    posted = []
    monkeypatch.setattr(addons_state, "_post", lambda p: posted.append(p))
    addons_state._guard["last_post"] = 0
    c = _client()
    assert c.post("/api/assistant/simulate-failure?n=6").status_code == 401
    j = c.post("/api/assistant/simulate-failure?n=6", headers={"x-incident-token": "tok"}).json()
    assert j["health"]["failures_last_minute"] >= 5
    import time
    time.sleep(0.2)
    c.post("/api/assistant/simulate-failure?n=6", headers={"x-incident-token": "tok"})
    time.sleep(0.2)
    assert len(posted) == 1 and posted[0]["service"] == "voice assistant"


def test_water_question_is_not_a_care_request(monkeypatch):
    monkeypatch.setattr(sarvam, "available", lambda: False)
    assert assistant.answer("where is drinking water", "en", "u-w", use_model=False)["intent"] == "facility"


def test_pages_served():
    c = _client()
    assert "Rs 10" in c.get("/for-temples").text and "I am a pilgrim" in c.get("/start").text
