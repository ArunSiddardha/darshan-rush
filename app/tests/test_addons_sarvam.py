"""Offline tests for addons_read, addons_scam, sarvam_keys. No network: Sarvam calls are monkeypatched."""
import base64
import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import addons_read
import addons_scam
import sarvam_keys

app = FastAPI()
app.include_router(addons_read.router)
app.include_router(addons_scam.router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def keys(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "k1")
    monkeypatch.setenv("SARVAM_API_KEY_2", "k2")
    sarvam_keys.reset()


def test_key_rotation_on_402_and_429():
    assert sarvam_keys.current() == "k1"
    assert sarvam_keys.on_status(200) is False and sarvam_keys.current() == "k1"
    assert sarvam_keys.on_status(402) is True and sarvam_keys.current() == "k2"
    assert sarvam_keys.on_status(429) is True      # both cooling: the one that recovers first (k2 after 429: 30 s)
    assert sarvam_keys.current() == "k2"


def test_single_key_never_rotates(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY_2")
    sarvam_keys.reset()
    assert sarvam_keys.on_status(402) is False and sarvam_keys.current() == "k1"


def test_no_key(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY"); monkeypatch.delenv("SARVAM_API_KEY_2")
    assert sarvam_keys.current() == "" and not sarvam_keys.available()
    r = client.post("/api/read-photo", files={"image": ("a.png", b"x", "image/png")}, data={"lang": "ml"})
    assert r.status_code == 503 and "Sarvam key" in r.json()["notice"]


def test_read_photo_happy(monkeypatch):
    monkeypatch.setattr(addons_read, "ocr", lambda *a: "Token 4812\nGate: River Crossing")
    monkeypatch.setattr(addons_read, "translate", lambda t, l: "ടോക്കൺ 4812")
    monkeypatch.setattr(addons_read, "speak", lambda t, l: base64.b64encode(b"RIFF").decode())
    r = client.post("/api/read-photo", files={"image": ("a.png", b"x", "image/png")}, data={"lang": "ml", "uid": "u"})
    j = r.json()
    assert r.status_code == 200 and j["text"].startswith("Token 4812") and j["translated_text"] == "ടോക്കൺ 4812"
    assert j["audio_base64"] and j["lang"] == "ml" and "total_ms" in j["latency"] and j["notice"] == ""


def test_read_photo_no_credits(monkeypatch):
    def boom(*a):
        raise addons_read.ReadError(addons_read.NO_CREDITS, 402)
    monkeypatch.setattr(addons_read, "ocr", boom)
    r = client.post("/api/read-photo", files={"image": ("a.png", b"x", "image/png")}, data={"lang": "te"})
    assert r.status_code == 402 and r.json()["notice"] == addons_read.NO_CREDITS


def test_read_photo_bad_type():
    r = client.post("/api/read-photo", files={"image": ("a.gif", b"x", "image/gif")}, data={"lang": "hi"})
    assert r.status_code == 415


def test_scam_rules():
    v, reasons, host, gov = addons_scam.rules("pay 500 for a quick darshan pass")
    assert v == "high_risk" and {"payment", "vip"} <= set(reasons)
    assert addons_scam.rules("bit.ly/abc")[0] == "caution"
    assert addons_scam.rules("https://sabarimala-darshan.xyz pay now")[0] == "high_risk"


def test_gov_in_only_on_real_suffix():
    assert addons_scam.rules("https://dept.example.gov.in/x")[3] is True
    assert addons_scam.rules("https://gov.in.evil.com/x")[3] is False
    assert addons_scam.rules("https://dept.gov.in@evil.com/x")[3] is False
    assert addons_scam.rules("https://evilgov.in/x")[3] is False


def _patch_voice(monkeypatch):
    monkeypatch.setattr(addons_scam, "translate", lambda t, l: "[" + l + "] " + t)
    monkeypatch.setattr(addons_scam, "speak", lambda t, l: "QVVESU8=")
    monkeypatch.setattr(addons_scam, "chat_classify", lambda t: "unknown")


def test_site_check_endpoint(monkeypatch):
    _patch_voice(monkeypatch)
    j = client.post("/api/site-check", json={"text": "pay 500 for a quick darshan pass", "lang": "ml", "uid": "u"}).json()
    assert j["verdict"] == "high_risk" and j["reply_text"].startswith("[ml]") and j["audio_base64"] and j["reasons"]


def test_never_says_genuine(monkeypatch):
    _patch_voice(monkeypatch)
    for t in ["https://dept.example.gov.in/darshan", "https://example.com", "hello", "pay 500 for vip pass"]:
        j = client.post("/api/site-check", json={"text": t, "lang": "en"}).json()
        low = j["reply_text"].lower()
        assert "genuine" not in low and "is safe" not in low and "legitimate" not in low and "authentic" not in low
        assert j["verdict"] in ("caution", "high_risk", "unknown")
    j = client.post("/api/site-check", json={"text": "https://dept.example.gov.in/darshan", "lang": "en"}).json()
    assert "looks like a government address, still check on the official notice board" in j["reply_text"]


def test_model_can_only_raise(monkeypatch):
    _patch_voice(monkeypatch)
    monkeypatch.setattr(addons_scam, "chat_classify", lambda t: "caution")
    j = client.post("/api/site-check", json={"text": "some portal asks my details", "lang": "en"}).json()
    assert j["verdict"] == "caution"


def test_site_check_empty():
    assert client.post("/api/site-check", json={"text": "", "lang": "en"}).status_code == 400
