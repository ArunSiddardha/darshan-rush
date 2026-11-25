import threading
import time
from types import SimpleNamespace
from unittest import mock

import pytest
from fastapi.testclient import TestClient

import config
import flags
import main
import queue_sim
import slots

client = TestClient(main.app)
FIXED = 1_800_000_000.0  # fixed clock for slot tests


# ---------- queue_sim ----------
def test_snapshot_shape_and_simulated():
    s = queue_sim.snapshot()
    assert s["simulated"] is True
    assert [g["name"] for g in s["gates"]] == ["Base Camp", "River Crossing", "Forest Path",
                                                "Queue Complex", "Main Steps"]
    for g in s["gates"]:
        assert set(g) == {"id", "name", "load", "wait_min"} and 0 <= g["load"] <= 1


def test_rush_surge_raises_waits():
    before = sum(g["wait_min"] for g in queue_sim.snapshot()["gates"])
    queue_sim.set_rush(True)
    for _ in range(30):
        queue_sim.step()
    after = sum(g["wait_min"] for g in queue_sim.snapshot()["gates"])
    assert after > before * 1.5
    queue_sim.set_rush(False)
    for _ in range(40):
        queue_sim.step()
    assert sum(g["wait_min"] for g in queue_sim.snapshot()["gates"]) < after


def test_resolve_gate():
    assert queue_sim.resolve_gate("3") == "g3"
    assert queue_sim.resolve_gate("Main Steps") == "g5"
    assert queue_sim.resolve_gate("g1") == "g1"
    assert queue_sim.resolve_gate("zzz") is None


# ---------- slots ----------
def test_open_mode_first_come_same_window():
    slots.NOW = lambda: FIXED
    a, _ = slots.book("u1", "g1", mode="open")
    b, _ = slots.book("u2", "g2", mode="open")
    assert a["window"] == b["window"]


def test_one_booking_per_uid():
    slots.NOW = lambda: FIXED
    a, again1 = slots.book("u1", "g1")
    b, again2 = slots.book("u1", "g3")
    assert (again1, again2) == (False, True) and a["window"] == b["window"]
    assert slots.total() == 1


def test_staggered_never_exceeds_cap_and_always_returns(monkeypatch):
    monkeypatch.setenv("SLOT_CAP", "5")
    slots.NOW = lambda: FIXED
    for i in range(300):  # far more than 8 windows * 5
        s, _ = slots.book(f"u{i}", "g4", mode="staggered")
        assert s["start"]
    assert max(slots._counts.values()) <= 5
    assert len(slots._counts) >= 60


def test_staggered_spreads_across_windows():
    slots.NOW = lambda: FIXED
    for i in range(16):
        slots.book(f"u{i}", "g4", mode="staggered")
    assert len(slots._counts) == 8 and set(slots._counts.values()) == {2}


def test_cancel_and_rebook():
    slots.NOW = lambda: FIXED
    slots.book("u1", "g1")
    assert slots.cancel("u1") is True and slots.cancel("u1") is False
    assert slots.get("u1") is None and slots.total() == 0


def test_time_preference_honoured_in_open_mode():
    slots.NOW = lambda: FIXED
    s0, _ = slots.book("a", "g1")
    later = slots.listing()["windows"][4]["start"]
    s, _ = slots.book("b", "g1", time_pref=later)
    assert s["start"] == later and s["window"] > s0["window"]


def test_walk_in_by_volunteer():
    slots.NOW = lambda: FIXED
    s, _ = slots.book_walk_in("Queue Complex")
    assert s["walk_in"] is True and s["uid"].startswith("walkin-") and s["gate"] == "g4"
    s2, _ = slots.book_walk_in("g1")
    assert s2["uid"] != s["uid"]


# ---------- flags ----------
def test_local_flags_and_dev_set():
    assert flags.map_mode() == "full" and flags.slot_mode() == "open"
    flags.dev_set("map_mode", "lite")
    assert flags.lite_mode() is True
    with pytest.raises(ValueError):
        flags.dev_set("map_mode", "bogus")
    with pytest.raises(KeyError):
        flags.dev_set("nope", "x")


def test_flag_cache_two_seconds():
    sdk = mock.Mock()
    sdk.get_environment_flags.return_value.get_feature_value.return_value = "lite"
    with mock.patch.object(flags, "_sdk", return_value=sdk):
        assert flags.map_mode() == "lite"
        assert flags.map_mode() == "lite"
        assert sdk.get_environment_flags.call_count == 1
        flags._cache["map_mode"] = (time.time() - 3, "lite")
        flags.map_mode()
        assert sdk.get_environment_flags.call_count == 2


def test_flagsmith_down_uses_last_good_then_default():
    sdk = mock.Mock()
    sdk.get_environment_flags.side_effect = RuntimeError("down")
    with mock.patch.object(flags, "_sdk", return_value=sdk):
        assert flags.map_mode() == "full"  # default
        flags._cache["map_mode"] = (time.time() - 3, "lite")
        assert flags.map_mode() == "lite"  # last good value


def test_json_remote_config_value():
    sdk = mock.Mock()
    sdk.get_environment_flags.return_value.get_feature_value.return_value = '{"mode": "lite"}'
    with mock.patch.object(flags, "_sdk", return_value=sdk):
        assert flags.map_mode() == "lite"


def test_identity_traits_sent_to_sdk():
    sdk = mock.Mock(spec=["get_identity_flags"])
    sdk.get_identity_flags.return_value.get_feature_value.return_value = "voice"
    with mock.patch.object(flags, "_sdk", return_value=sdk):
        r = flags.voice_directions("u1", lang="ml", age_65_plus=True)
    assert r["voice_directions"] == "voice" and r["source"] == "flagsmith"
    assert sdk.get_identity_flags.call_args.kwargs["traits"] == {"language": "ml", "age_65_plus": True}


def test_default_flag_handler():
    d = flags._default_handler("slot_mode")
    assert d.value == "open" and d.enabled is True


def test_variant_hash_is_stable_without_flagsmith():
    assert flags.voice_directions("abc")["voice_directions"] == flags.voice_directions("abc")["voice_directions"]
    flags.dev_set("voice_directions", "map")
    assert flags.voice_directions("abc")["voice_directions"] == "map"


# ---------- API ----------
def test_api_queue_full_runs_heavy_lite_skips():
    with mock.patch.object(main, "build_live_render") as heavy:
        r = client.get("/api/queue?uid=u&lang=ml").json()
        assert heavy.call_count == 1 and r["map_mode"] == "full" and r["simulated"] is True
        flags.dev_set("map_mode", "lite")
        r = client.get("/api/queue?uid=u").json()
        assert heavy.call_count == 1 and r["map_mode"] == "lite"


def test_heavy_really_allocates(monkeypatch):
    monkeypatch.setenv("HEAVY_MB", "8")
    sizes = []
    real = bytearray
    with mock.patch.object(main, "bytearray", lambda n: (sizes.append(n), real(n))[1], create=True):
        main.build_live_render("x")
    assert sizes == [8 * 1024 * 1024] and main._heavy_in_flight == 0


def test_book_open_then_staggered_via_api():
    r = client.post("/api/slots/book", json={"uid": "p1", "gate": "g2"}).json()
    assert r["mode"] == "open" and r["slot"]["gate"] == "g2" and r["simulated"] is True
    flags.dev_set("slot_mode", "staggered")
    r = client.post("/api/slots/book", json={"uid": "p2", "gate": "g2"}).json()
    assert r["mode"] == "staggered"
    again = client.post("/api/slots/book", json={"uid": "p2", "gate": "g2"}).json()
    assert again["already_booked"] is True
    mine = client.get("/api/slots?uid=p2").json()
    assert mine["mine"]["uid"] == "p2" and mine["total"] == 2
    assert client.post("/api/slots/cancel", json={"uid": "p2"}).json() == {"cancelled": True}


def test_book_requires_uid_and_walkin_does_not():
    assert client.post("/api/slots/book", json={"gate": "g1"}).status_code == 400
    r = client.post("/api/slots/walkin", json={"gate": "g3"}).json()
    assert r["slot"]["walk_in"] is True


def test_dev_flag_endpoint():
    assert client.post("/api/dev/flag", json={"name": "slot_mode", "value": "staggered"}).status_code == 200
    assert client.get("/api/flags?uid=a&lang=ml").json()["slot_mode"] == "staggered"
    assert client.post("/api/dev/flag", json={"name": "x", "value": 1}).status_code == 400
    assert client.post("/api/dev/flag", json={"name": "map_mode", "value": "zz"}).status_code == 400


def test_experiment_counts_and_event():
    flags.dev_set("voice_directions", "voice")
    client.get("/api/flags?uid=u1&lang=ml&expose=1")
    client.get("/api/flags?uid=u2&lang=ml&expose=1")
    assert client.post("/api/experiment", json={"uid": "u1"}).json()["variant"] == "voice"
    ex = client.get("/api/experiment").json()
    assert ex["metric"] == "reached_gate"
    assert ex["variants"]["voice"] == {"exposed": 2, "reached_gate": 1, "rate": 0.5}
    assert client.post("/api/experiment", json={"uid": "u1", "event": "other"}).status_code == 400


def test_reached_gate_sent_to_sdk():
    sdk = mock.Mock()
    sdk.get_identity_flags.return_value.get_feature_value.return_value = "map"
    with mock.patch.object(flags, "_sdk", return_value=sdk):
        client.post("/api/experiment", json={"uid": "u9"})
    sdk.track_event.assert_called_once_with("reached_gate", identifier="u9")


def test_rush_token_protection():
    assert client.post("/api/rush/start").status_code == 401
    assert client.post("/api/rush/start", headers={"X-Rush-Token": "no"}).status_code == 401
    assert client.post("/api/rush/stop").status_code == 401


def test_rush_start_stop_spawns_and_stops_threads():
    started = []

    def fake(i, stop_evt):
        started.append(i)
        stop_evt.wait(5)

    with mock.patch.object(main, "_rush_worker", fake):
        r = client.post("/api/rush/start?workers=3", headers={"X-Rush-Token": "rt"}).json()
        assert r["running"] is True and r["workers"] == 3
        time.sleep(0.2)
        assert len(started) == 3 and queue_sim.rush_on() and main.rush_running()
        assert client.post("/api/rush/start", headers={"X-Rush-Token": "rt"}).json()["note"] == "already running"
        client.post("/api/rush/stop", headers={"X-Rush-Token": "rt"})
        time.sleep(0.2)
        assert not main.rush_running() and not queue_sim.rush_on()


def test_rush_worker_hits_endpoints():
    calls = []

    class FakeClient:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def get(self, url, **k):
            calls.append(url); return SimpleNamespace(status_code=200)
        def post(self, url, **k):
            calls.append(url); stop.set(); return SimpleNamespace(status_code=200)

    stop = threading.Event()
    with mock.patch.object(main.httpx, "Client", FakeClient):
        main._rush_worker(1, stop)
    assert calls[0].endswith("/api/queue") and calls[1].endswith("/api/slots/book")


def test_metrics_lite_fields():
    client.get("/api/queue?uid=m")
    m = client.get("/api/metrics-lite").json()
    for k in ("rps", "errors", "p95_ms", "restarts", "map_mode", "slot_mode", "bookings"):
        assert k in m
    assert m["rps"] > 0


def test_metrics_count_errors():
    with mock.patch.object(main, "build_live_render", side_effect=RuntimeError("boom")):
        r = TestClient(main.app, raise_server_exceptions=False).get("/api/queue")
    assert r.status_code == 500
    assert main.metrics_window()["errors"] >= 1


def test_incident_token_and_missing_volunteer():
    assert client.post("/api/incident", json={}).status_code == 401
    r = client.post("/api/incident", json={"summary": "s"}, headers={"X-Incident-Token": "it"})
    assert r.status_code in (200, 503)


def test_healthz_reports_routers_and_pages_404_gracefully():
    h = client.get("/healthz").json()
    assert "volunteer" in h["routers"] and "directions" in h["routers"]
    assert client.get("/judge").status_code in (200, 404)


# ---- integration additions
def test_bookings_persist_across_restart(tmp_path, monkeypatch):
    import slots
    monkeypatch.setenv("STATE_FILE", str(tmp_path / "state.json"))
    slots.reset()
    a, _ = slots.book("p1", "g1", None, "open")
    b, _ = slots.book("p2", "g2", None, "staggered")
    slots._by_uid.clear(); slots._counts.clear()   # simulate the process dying
    assert slots.load() == 2
    again, flag = slots.book("p1", "g1", None, "open")
    assert flag and again["label"] == a["label"] and slots.get("p2")["label"] == b["label"]
    slots.reset()


def test_config_event_phones(monkeypatch):
    from fastapi.testclient import TestClient
    import main
    monkeypatch.setenv("PUBLIC_URL", "https://example.test/")
    c = TestClient(main.app)
    assert c.get("/api/config").json()["public_url"] == "https://example.test"
    main._phones.clear()
    c.get("/api/queue?uid=a1"); c.get("/api/queue?uid=a2"); c.get("/api/queue?uid=a1")
    assert c.get("/api/metrics-lite").json()["phones"] == 2
    r = c.post("/api/event", json={"uid": "a1", "event": "reached_gate", "gate": "g1"}).json()
    assert r["ok"] and r["variant"] in ("voice", "map")
    fl = c.get("/api/flags?uid=a1").json()
    assert {"map_mode", "slot_mode", "voice_directions"} <= set(fl)


def test_rush_accepts_either_token_header(monkeypatch):
    from fastapi.testclient import TestClient
    import main
    monkeypatch.setenv("RUSH_TOKEN", "secret")
    c = TestClient(main.app)
    assert c.post("/api/rush/stop").status_code == 401
    assert c.post("/api/rush/stop", headers={"X-Incident-Token": "secret"}).status_code == 200
    assert c.post("/api/rush/stop", headers={"X-Rush-Token": "secret"}).status_code == 200
