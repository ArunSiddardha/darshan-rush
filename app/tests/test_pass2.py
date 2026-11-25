"""Pass 2: crash self-report and /api/incident hardening. Webhook mocked, no network."""
import sys
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import crash, volunteer  # noqa: E402

H = {"X-Incident-Token": "tok"}


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("STATE_FILE", str(tmp_path / "s.json"))
    monkeypatch.setenv("INCIDENT_TOKEN", "tok")
    monkeypatch.setenv("SARVAM_API_KEY", "")
    monkeypatch.setenv("NUDGEBEE_CRASH_WEBHOOK", "")
    monkeypatch.setenv("HOSTNAME", "darshan-abc")
    volunteer.reset()
    app = FastAPI()
    app.include_router(volunteer.router)
    return TestClient(app)


# ---- crash report
def test_clean_start_reports_nothing(env, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: pytest.fail("no post expected"))
    assert crash.check_after_start("full") is None
    crash.rush_started(); crash.rush_stopped()
    assert crash.check_after_start("full") is None


def test_crash_reports_once_with_count(env, monkeypatch):
    monkeypatch.setenv("NUDGEBEE_CRASH_WEBHOOK", "http://nb/crash")
    posts = []
    monkeypatch.setattr(httpx, "post", lambda url, **k: posts.append((url, k["json"])) or httpx.Response(200))
    crash.rush_started()  # process dies here, marker stays
    rec = crash.check_after_start("full")
    assert rec["sent"] and len(posts) == 1
    body = posts[0][1]
    assert posts[0][0] == "http://nb/crash"
    assert body["namespace"] == "darshan" and body["pod"] == "darshan-abc"
    assert body["reason"] == "OOMKilled (suspected)" and body["restarts_seen"] == 1 and body["map_mode"] == "full"
    assert body["what_happened"] == "booking service restarted during a rush" and body["reported_at"]
    assert crash.check_after_start("full") is None  # once only: the next start finds the marker cleared
    crash.rush_started()
    assert crash.check_after_start("lite")["restarts_seen"] == 2  # count kept across crashes


def test_crash_without_webhook_or_failing_webhook(env, monkeypatch):
    crash.rush_started()
    assert crash.check_after_start("full")["sent"] is False
    monkeypatch.setenv("NUDGEBEE_CRASH_WEBHOOK", "http://nb/crash")

    def boom(*a, **k):
        raise httpx.ConnectError("x")
    monkeypatch.setattr(httpx, "post", boom)
    crash.rush_started()
    r = crash.check_after_start("full")
    assert r["sent"] is False and r["error"] == "ConnectError"


def test_crash_timeline_survives_incident(env):
    volunteer.mark_crash_seen(True)
    env.post("/api/incident", headers=H, json={"summary": "s", "root_cause": "r", "event_id": "e1"})
    steps = [t["step"] for t in env.get("/api/volunteer/state").json()["timeline"]]
    assert steps[:2] == ["Rush detected", "Crash reported to NudgeBee"] and "Cause found by NudgeBee" in steps


def test_main_wiring_marks_and_clears(monkeypatch, tmp_path):
    monkeypatch.setenv("STATE_FILE", str(tmp_path / "s.json"))
    import main
    c = TestClient(main.app)
    r = c.post("/api/rush/start?workers=1", headers={"X-Rush-Token": "rt"})
    assert r.status_code == 200
    assert crash._read()["running"] is True
    c.post("/api/rush/stop", headers={"X-Rush-Token": "rt"})
    assert crash._read()["running"] is False


# ---- incident hardening
def post(env, body, ct="application/json", q=""):
    return env.post("/api/incident" + q, headers={**H, "Content-Type": ct}, content=body)


def state(env):
    return env.get("/api/volunteer/state").json()


def test_raw_newlines_and_markdown(env):
    body = '{"event_id":"e1","summary":"**Pod OOM**\nline two","root_cause":"limit 160Mi\n- cause: tiles","proposed_fix":"lite"}'
    assert post(env, body).json()["ok"]
    s = state(env)
    assert s["status"] == "asking" and "line two" in s["summary"] and "limit 160Mi" in s["root_cause"]


def test_unescaped_quotes_regex_fallback(env):
    body = '{"event_id": "e2", "summary": "Pod said "killed" at 12:01", "root_cause": "memory "limit" hit\nagain", "proposed_fix": "lite"}'
    assert post(env, body).status_code == 200
    s = state(env)
    assert s["event_id"] == "e2" and s["summary"] == 'Pod said "killed" at 12:01'
    assert s["root_cause"] == 'memory "limit" hit\nagain' and s["proposed_fix"] == "lite"


def test_text_plain_and_form(env):
    assert post(env, 'summary: Pod died\nroot_cause: out of memory', "text/plain").status_code == 200
    assert state(env)["summary"].startswith("Pod died")
    volunteer.reset()
    r = env.post("/api/incident", headers=H, data={"summary": "form s", "root_cause": "form r", "event_id": "f1"})
    assert r.status_code == 200 and state(env)["event_id"] == "f1"


def test_root_cause_trimmed_and_event_id_generated(env):
    r = post(env, '{"summary":"s","root_cause":"%s"}' % ("x" * 4000))
    assert r.json()["event_id"].startswith("evt-")
    assert len(state(env)["root_cause"]) == 1500


def test_empty_body_400(env):
    assert post(env, "nothing useful").status_code == 400


def test_duplicate_while_asking_or_approved_and_force(env, monkeypatch):
    monkeypatch.setattr(volunteer, "watch_flags", lambda *a, **k: None)
    assert post(env, '{"summary":"a","event_id":"e1"}').json()["status"] == "asking"
    assert post(env, '{"summary":"b","event_id":"e9"}').json() == {"ok": True, "status": "duplicate"}
    assert state(env)["summary"] == "a"
    env.post("/api/volunteer/reply", json={"text": "yes"})
    assert state(env)["status"] == "approved"
    assert post(env, '{"summary":"c","event_id":"e10"}').json()["status"] == "duplicate"
    r = post(env, '{"summary":"d","event_id":"e11"}', q="?force=1")
    assert r.json()["status"] == "asking" and state(env)["summary"] == "d"
    volunteer.reset()
    assert post(env, '{"summary":"e"}').json()["status"] == "asking"  # idle again: accepted


def test_json_sent_as_form_type(env):
    assert post(env, '{"summary":"s","root_cause":"r"}', "application/x-www-form-urlencoded").status_code == 200
