"""Sponsors addon tests. No network, no Sarvam: sarvam._post is mocked, Flagsmith HTTP is mocked."""
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import FastAPI
from fastapi.testclient import TestClient

import addons_sponsors as sp


@pytest.fixture(autouse=True)
def clean(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_FILE", str(tmp_path / "state.json"))
    for k in ("FLAGSMITH_ENV_KEY", "FLAGSMITH_CLIENT_KEY", "FLAGSMITH_ADMIN_KEY"):
        monkeypatch.delenv(k, raising=False)
    sp._calls.clear()
    sp._cache.clear()
    import flags  # never let a test build a real Flagsmith SDK client inside flags.py
    monkeypatch.setattr(flags, "experiment", lambda: {"variants": {}, "source": "local", "recent_events": []})
    yield


class FakeResp:
    def __init__(self, status=200, body=None):
        self.status_code, self._b = status, body or {}

    def json(self):
        return self._b


def fake_module(post):
    m = types.SimpleNamespace()
    m._post = post
    return m


def test_wrapper_records_and_returns_same_result():
    resp = FakeResp(200, {"transcript": "namaskaram", "language_code": "ml-IN"})
    m = fake_module(lambda path, what, **kw: (resp, 321))
    assert sp.install_recorder(m) is True
    r, ms = m._post("/speech-to-text", "speech-to-text", data={"mode": "codemix"})
    assert r is resp and ms == 321
    c = sp._calls[-1]
    assert (c["type"], c["status"], c["ms"], c["lang"], c["text"]) == ("stt", 200, 321, "ml", "namaskaram")


def test_wrapper_idempotent():
    m = fake_module(lambda *a, **k: (FakeResp(), 1))
    assert sp.install_recorder(m) is True
    first = m._post
    assert sp.install_recorder(m) is False
    assert m._post is first
    m._post("/text-to-speech", "text-to-speech", json={"text": "x"})
    assert len(sp._calls) == 1  # not double counted


def test_wrapper_reraises_original_error_and_records_status():
    class SarvamNoCredits(Exception):
        pass

    def boom(path, what, **kw):
        raise SarvamNoCredits("nope")

    m = fake_module(boom)
    sp.install_recorder(m)
    with pytest.raises(SarvamNoCredits):
        m._post("/translate", "translate", json={"input": "hi", "target_language_code": "ml-IN"})
    c = sp._calls[-1]
    assert c["status"] == 402 and c["type"] == "translate" and c["error"] == "no credits"


def test_wrapper_never_raises_when_recording_breaks(monkeypatch):
    m = fake_module(lambda *a, **k: (FakeResp(), 5))
    sp.install_recorder(m)
    monkeypatch.setattr(sp, "_record", lambda *a, **k: 1 / 0)
    r, ms = m._post("/text-to-speech", "text-to-speech", json={})
    assert ms == 5


def test_error_status_mapping():
    class E(Exception):
        pass
    assert sp._err_status(E("Sarvam translate: rate limited (429), try again")) == (429, "http 429")
    assert sp._err_status(E("Sarvam stt timed out after 8 s")) == (0, "timeout")
    assert sp._err_status(E("Sarvam stt network error: ConnectError")) == (0, "network")


def test_calls_persist_and_reload():
    sp._store({"t": 1.0, "type": "tts", "status": 200, "ms": 10, "lang": "ml", "text": "a", "out": "", "error": None})
    sp._calls.clear()
    sp._load_calls()
    assert sp._calls and sp._calls[0]["type"] == "tts"


def _seed():
    now = 1000.0
    for typ, st, ms, lg, tx in [("stt", 200, 800, "ml", "ശരി"), ("stt", 200, 600, "en", "yes please"),
                                ("tts", 200, 1200, "ml", "വലിയ തിരക്ക്"), ("tts", 200, 1000, "hi", "namaste")]:
        sp._calls.append({"t": now, "type": typ, "status": st, "ms": ms, "lang": lg, "text": tx, "out": "", "error": None})
        now += 1


def test_sarvam_block_stats(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "x")
    _seed()
    b = sp.sarvam_block({})
    assert b["calls"] == {"stt": 2, "tts": 2} and b["median_ms"]["stt"] == 700
    assert b["languages_heard"] == ["en", "ml"]
    assert b["last_heard"]["text"] == "yes please" and b["last_said"]["lang"] == "hi"
    assert b["state"] == "working" and "available" in b["credits"]
    assert "x" not in json.dumps(b.get("key_slot"))  # slot numbers only


def test_sarvam_credits_problem_and_empty(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "x")
    assert sp.sarvam_block({})["state"] == "waiting"
    sp._calls.append({"t": 1, "type": "stt", "status": 402, "ms": 5, "lang": None, "text": "", "out": "", "error": "no credits"})
    b = sp.sarvam_block({})
    assert b["state"] == "problem" and "402" in b["credits"]


def test_sarvam_falls_back_to_volunteer_state(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "x")
    b = sp.sarvam_block({"transcript": "ശരി", "question_en": "Heavy rush."})
    assert b["last_heard"]["text"] == "ശരി" and b["last_said"]["text"] == "Heavy rush."


TL = lambda *steps: {"timeline": [{"step": s, "t": 100.0 + i * 10} for i, s in enumerate(steps)]}


def test_nudgebee_block_durations_and_steps():
    v = {**TL("Rush detected", "Crash reported to NudgeBee", "Cause found by NudgeBee", "Asked the volunteer",
              "Volunteer said yes", "NudgeBee approved", "Flags flipped", "Booking recovered"),
         "event_id": "abcdef123456", "root_cause": "### Title\n**OOM** killed", "summary": "Pod ran out of memory",
         "status": "recovered"}
    b = sp.nudgebee_block(v)
    assert b["state"] == "working"
    assert b["crash_to_cause_s"] == 10.0 and b["yes_to_recovery_s"] == 30.0
    assert [a["done"] for a in b["approval"]] == [True] * 5
    assert "#" not in b["root_cause_short"] and b["automations"][0] == "darshan-crash-report"


def test_nudgebee_block_empty_is_waiting_not_error():
    b = sp.nudgebee_block({})
    assert b["last_crash"] is None and b["root_cause"] is None and b["state"] in ("waiting", "problem")


def test_flagsmith_without_key_is_a_clear_problem_not_a_crash():
    b = sp.flagsmith_block({})
    assert b["state"] == "problem" and all(f["available"] is False for f in b["flags"])
    assert len(b["flags"]) == 6


def test_flagsmith_values_reasons_and_proof(monkeypatch):
    monkeypatch.setenv("FLAGSMITH_ENV_KEY", "edge")
    monkeypatch.setenv("FLAGSMITH_ADMIN_KEY", "adm")
    std = {"map_mode": ("lite", True), "slot_mode": ("staggered", True), "voice_directions": ("voice", True),
           "voice_first": (None, False), "ui_copy": (json.dumps({"banner": {"en": "a", "ml": "b"}}), True),
           "voice_agent_v2": (None, False)}
    eld = dict(std, voice_first=(None, True))
    monkeypatch.setattr(sp, "_edge_flags", lambda traits: eld if traits.get("age_65_plus") else std)
    monkeypatch.setattr(sp, "_rollout_pct", lambda: 50)
    monkeypatch.setattr(sp, "_last_change", lambda n: {"t": 125.0, "count": 4, "by": "Admin API key (x)"})
    monkeypatch.setattr(sp, "_audit", lambda: {"count": 0, "rows": []})
    b = sp.flagsmith_block(TL("Rush detected", "Volunteer said yes", "Flags flipped"))
    by = {f["flag"]: f for f in b["flags"]}
    assert b["state"] == "working"
    assert by["map_mode"]["value"] == "lite" and "changed from the default" in by["map_mode"]["reason"]
    assert "NudgeBee" in by["map_mode"]["proof"]
    assert "segment elders_65_plus" in by["voice_first"]["reason"]
    assert by["voice_agent_v2"]["value"] == "50% rollout"
    assert by["ui_copy"]["value"].startswith("remote text for 2")
    assert "adm" not in json.dumps(b)


def test_flagsmith_edge_down(monkeypatch):
    monkeypatch.setenv("FLAGSMITH_ENV_KEY", "edge")
    monkeypatch.setattr(sp, "_edge_flags", lambda t: (_ for _ in ()).throw(OSError("down")))
    b = sp.flagsmith_block({})
    assert b["state"] == "problem" and "not reachable" in b["note"]


def test_endpoint_and_page_never_error(monkeypatch):
    app = FastAPI()
    app.include_router(sp.router)
    c = TestClient(app)
    r = c.get("/api/sponsors/status")
    assert r.status_code == 200
    d = r.json()
    for k in ("sarvam", "flagsmith", "nudgebee", "chain", "simulated_note"):
        assert k in d
    monkeypatch.setattr(sp, "status_payload", lambda: 1 / 0)
    r = c.get("/api/sponsors/status")
    assert r.status_code == 200 and r.json()["error"] == "not available"
    for p, t in (("/sponsors", "text/html"), ("/sponsors/sponsors.js", "javascript"), ("/sponsors/sponsors.css", "text/css")):
        r = c.get(p)
        assert r.status_code == 200 and t in r.headers["content-type"]


def test_chain_lights_from_timeline():
    ch = sp.chain_block(TL("Rush detected", "Crash reported to NudgeBee"), "full")
    assert [n["on"] for n in ch] == [True, True] + [False] * 5
    assert ch[2]["next"] is True
    ch = sp.chain_block(TL("Rush detected"), "lite")
    assert ch[5]["on"] is True  # flags lite lights the flags step like the judge page
