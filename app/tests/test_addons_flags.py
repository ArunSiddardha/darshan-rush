"""Tests for addons_flags with Flagsmith mocked (no network)."""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import addons_flags as af


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("FLAGSMITH_CLIENT_KEY", "test")
    monkeypatch.delenv("FLAGSMITH_ADMIN_KEY", raising=False)
    monkeypatch.setenv("ROLLOUT_LOG", str(tmp_path / "rollout.log"))
    af._cache.clear()
    app = FastAPI()
    app.include_router(af.router)
    return TestClient(app)


def _flag(name, value=None, enabled=False):
    return {"feature": {"name": name}, "feature_state_value": value, "enabled": enabled}


ENV = [_flag("map_mode", "full", True), _flag("slot_mode", "open", True), _flag("voice_directions", "map", True),
       _flag("voice_first", None, False), _flag("voice_agent_v2", None, False),
       _flag("ui_copy", json.dumps({"slot_cap": 44, "banner": {"ml": "REMOTE-ML"}}), True)]


def fake_http(identity_overrides):
    def f(method, url, headers, body=None, timeout=4):
        if url.endswith("/flags/"):
            return ENV
        flags = [dict(x) for x in ENV]
        traits = {t["trait_key"]: t["trait_value"] for t in body["traits"]}
        for x in flags:
            if x["feature"]["name"] == "voice_first" and traits.get("age_65_plus"):
                x["enabled"] = True
            if x["feature"]["name"] == "voice_directions":
                x["feature_state_value"] = "voice"
        return {"flags": flags}
    return f


def test_decisions_segment_and_default(client, monkeypatch):
    monkeypatch.setattr(af, "_http", fake_http(None))
    d = client.get("/api/flags/decisions", params={"uid": "a", "lang": "ml", "age65": "true"}).json()
    by = {f["flag"]: f for f in d["flags"]}
    assert d["source"] == "flagsmith"
    assert by["voice_first"]["enabled"] is True and by["voice_first"]["segment"] == "elders_65_plus"
    assert by["voice_directions"]["kind"] == "variant" and by["voice_directions"]["value"] == "voice"
    assert by["map_mode"]["kind"] == "default"
    d2 = client.get("/api/flags/decisions", params={"uid": "b", "lang": "en"}).json()
    assert {f["flag"]: f for f in d2["flags"]}["voice_first"]["enabled"] is False


def test_decisions_unreachable_gives_defaults(client, monkeypatch):
    def boom(*a, **k):
        raise OSError("down")
    monkeypatch.setattr(af, "_http", boom)
    d = client.get("/api/flags/decisions?uid=x").json()
    assert d["source"] == "unavailable" and "unreachable" in d["message"]
    assert {f["flag"]: f for f in d["flags"]}["map_mode"]["value"] == "full"


def test_ui_copy_remote_merge_and_fallback(client, monkeypatch):
    monkeypatch.setattr(af, "_http", fake_http(None))
    c = client.get("/api/ui-copy?lang=ml").json()
    assert c["source"] == "flagsmith" and c["banner"] == "REMOTE-ML" and c["slot_cap"] == 44
    assert c["examples"] and c["slot_window_min"] == 15  # default kept for keys not overridden
    monkeypatch.setattr(af, "_http", lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    af._cache.clear()
    c = client.get("/api/ui-copy?lang=te").json()
    assert c["source"] == "defaults" and c["banner"] and "message" in c
    assert client.get("/api/ui-copy?lang=zz").json()["lang"] == "en"


def test_no_key_uses_defaults(monkeypatch):
    monkeypatch.delenv("FLAGSMITH_CLIENT_KEY", raising=False)
    monkeypatch.delenv("FLAGSMITH_ENV_KEY", raising=False)
    af._cache.clear()
    app = FastAPI(); app.include_router(af.router)
    c = TestClient(app).get("/api/ui-copy?lang=hi").json()
    assert c["source"] == "defaults"


def test_rollout_reads_log(client, tmp_path):
    (tmp_path / "rollout.log").write_text("t STEP pct=10 action=set\nt OK pct=10 held\nt STEP pct=50 action=set\n")
    r = client.get("/api/rollout").json()
    assert r["percent"] == 50 and r["source"] == "log" and r["last_step"].endswith("action=set")
    assert r["steps"] == [10, 50, 100]


def test_rollout_no_log(client):
    r = client.get("/api/rollout").json()
    assert r["percent"] is None and r["source"] == "unknown" and r["log"] == []
