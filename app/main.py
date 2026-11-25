"""Darshan Rush: a prototype crowd and slot service. Simulated crowd. Not affiliated with any temple.
Not for operational use."""
import hmac
import importlib
import logging
import threading
import time
from collections import deque
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import crash
import flags
import queue_sim
import slots

log = logging.getLogger("darshan")
STATIC = Path(__file__).parent / "static"
app = FastAPI(title="Darshan Rush")
STARTED = time.time()
MOUNTED = {}  # router name -> "ok" or reason it is missing

_samples = deque(maxlen=20000)  # (t, ms, ok)
_phones = {}                    # uid -> last time seen on /api/queue (for the judge "phones" counter)
_heavy_in_flight = 0
_heavy_lock = threading.Lock()


# ---------- metrics middleware ----------
_UNTRACKED = ("/api/metrics-lite", "/api/rush", "/healthz", "/static", "/api/dev")


@app.middleware("http")
async def _track(request: Request, call_next):
    path = request.url.path
    t0 = time.time()
    try:
        resp = await call_next(request)
        ok = resp.status_code < 500
    except Exception as e:  # unexpected crash in a handler
        log.exception("unhandled: %s", e)
        resp, ok = JSONResponse({"error": "internal error", "detail": str(e)[:200]}, status_code=500), False
    if path.startswith("/api/") and not path.startswith(_UNTRACKED):
        _samples.append((t0, (time.time() - t0) * 1000.0, ok))
    return resp


def metrics_window(window_s=10.0, now=None):
    now = now or time.time()
    rows = [s for s in list(_samples) if now - s[0] <= window_s]
    lat = sorted(s[1] for s in rows)
    p95 = lat[min(len(lat) - 1, int(0.95 * len(lat)))] if lat else 0.0
    return {"rps": round(len(rows) / window_s, 2), "errors": sum(1 for s in rows if not s[2]),
            "p95_ms": round(p95, 1)}


# ---------- heavy work ----------
def build_live_render(seed=""):
    """Deliberately memory hungry 'live map render'. Allocates HEAVY_MB, touches every page and
    holds it for HEAVY_HOLD_S. Skipped in lite map mode. Under a rush this is what OOM-kills the pod."""
    global _heavy_in_flight
    # The full render only happens for rush traffic (the in-pod rush, or the external load script's
    # 'rush*' / 'sim-*' uids). A few real visitors polling the page must never be able to kill the pod.
    if not (rush_running() or str(seed).startswith(("rush", "sim-", "load-"))):
        return
    with _heavy_lock:
        _heavy_in_flight += 1
    try:
        buf = bytearray(config.HEAVY_MB() * 1024 * 1024)
        for i in range(0, len(buf), 4096):
            buf[i] = (i // 4096) % 251
        # renders contend for the same tile cache, so each extra concurrent render makes all of them slower
        time.sleep(config.HEAVY_HOLD_S() * (1 + 0.15 * _heavy_in_flight))
        checksum = sum(buf[::1024 * 64]) + len(seed)
        del buf
        return checksum
    finally:
        with _heavy_lock:
            _heavy_in_flight -= 1


# ---------- pages ----------
def _page(name):
    p = STATIC / name
    if p.exists():
        return FileResponse(p)
    raise HTTPException(404, f"{name} has not been delivered yet")


@app.get("/")
def index():
    return _page("index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(STATIC / "favicon.svg", media_type="image/svg+xml")


@app.get("/volunteer")
def volunteer_page():
    return _page("volunteer.html")


@app.get("/judge")
def judge_page():
    return _page("judge.html")


@app.get("/graph")
def graph_page():
    return _page("graph.html")


@app.get("/map")
def map_page():
    return _page("map.html") if (STATIC / "map.html").exists() else _page("index.html")


@app.get("/api/map")
def api_map(uid: str = "anon", lang: str = "en"):
    import assistant
    return assistant.map_data(uid, lang if lang in ("en", "hi", "ml", "ta", "te", "kn") else "en")


@app.get("/healthz")
def healthz():
    return {"ok": True, "uptime_s": round(time.time() - STARTED, 1), "routers": MOUNTED,
            "flags_source": "flagsmith" if flags.using_flagsmith() else "local"}


# ---------- queue and flags ----------
@app.get("/api/queue")
def api_queue(uid: str = "anon", lang: str = "en"):
    now = time.time()
    _phones[uid] = now
    if len(_phones) > 5000:
        for k in [k for k, t in _phones.items() if now - t > 30]:
            _phones.pop(k, None)
    mode = flags.map_mode()
    if mode == "full":
        build_live_render(uid)
    out = queue_sim.snapshot()
    out.update({"map_mode": mode, "slot_mode": flags.slot_mode(), "lang": lang, "label": "SIMULATED"})
    return out


@app.get("/api/flags")
def api_flags(uid: str = "anon", lang: Optional[str] = None, age65: Optional[bool] = None,
              expose: int = 1):
    return flags.get_flags(uid, lang, age65, expose=bool(expose))


@app.get("/api/config")
def api_config():
    return {"public_url": config.PUBLIC_URL(), "app": "Darshan Rush", "simulated": True}


class EventIn(BaseModel):
    uid: str
    event: str = "reached_gate"
    gate: Optional[str] = None
    lang: Optional[str] = None
    age65: Optional[bool] = None


@app.post("/api/event")
def api_event(body: EventIn):
    """Frontend 'I reached the gate' tap. Recorded as the Flagsmith A/B metric reached_gate."""
    return api_experiment_event(ReachedIn(uid=body.uid, lang=body.lang, age65=body.age65, event=body.event))


@app.post("/api/dev/flag")
async def dev_flag(request: Request):
    body = await request.json()
    try:
        flags.dev_set(body["name"], body["value"])
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except KeyError:
        raise HTTPException(400, "unknown flag; use map_mode, slot_mode or voice_directions")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "flags": flags.LOCAL}


# ---------- slots ----------
class BookIn(BaseModel):
    uid: Optional[str] = None
    gate: str = "g4"
    time: Optional[str] = None
    walk_in: bool = False
    lang: Optional[str] = None


class UidIn(BaseModel):
    uid: str


@app.post("/api/slots/book")
def api_book(body: BookIn):
    mode = flags.slot_mode()
    if flags.map_mode() == "full":
        build_live_render(body.uid or "walkin")
    if body.walk_in:
        slot, again = slots.book_walk_in(body.gate, mode, body.uid)
    else:
        if not body.uid:
            raise HTTPException(400, "uid is required")
        slot, again = slots.book(body.uid, body.gate, body.time, mode)
    return {"slot": slot, "mode": mode, "already_booked": again, "simulated": True,
            "map_mode": flags.map_mode()}


@app.post("/api/slots/walkin")
def api_walkin(body: BookIn):
    """Volunteer books on behalf of a pilgrim without a phone."""
    body.walk_in = True
    return api_book(body)


@app.get("/api/slots")
def api_slots(uid: Optional[str] = None):
    out = slots.listing(uid)
    out["mode"] = flags.slot_mode()
    return out


@app.post("/api/slots/cancel")
def api_cancel(body: UidIn):
    return {"cancelled": slots.cancel(body.uid)}


# ---------- experiment ----------
class ReachedIn(BaseModel):
    uid: str
    lang: Optional[str] = None
    age65: Optional[bool] = None
    event: str = "reached_gate"


@app.get("/api/experiment")
def api_experiment():
    return flags.experiment()


@app.post("/api/experiment")
def api_experiment_event(body: ReachedIn):
    if body.event != "reached_gate":
        raise HTTPException(400, "only the reached_gate event is accepted")
    variant = flags.voice_directions(body.uid, body.lang, body.age65)["voice_directions"]
    sent = flags.track_event("reached_gate", body.uid, variant)
    return {"ok": True, "variant": variant, "sent_to_flagsmith": sent}


# ---------- rush (synthetic in-cluster load of simulated pilgrims) ----------
RUSH = {"stop": threading.Event(), "threads": [], "sent": 0, "failed": 0, "started": None}
_rush_lock = threading.Lock()


def _check_rush_token(tok, alt=None):
    tok = tok or alt
    want = config.RUSH_TOKEN()
    if not want:
        raise HTTPException(503, "RUSH_TOKEN is not set on the server")
    if not tok or not hmac.compare_digest(want, tok):
        raise HTTPException(401, "bad or missing X-Rush-Token")


def _rush_worker(i, stop_evt):
    base = f"http://127.0.0.1:{config.PORT()}"
    n = 0
    if stop_evt.wait(i * config.RUSH_RAMP_S()):  # pilgrims arrive one after another, not all in the same instant
        return
    with httpx.Client(timeout=15) as c:
        while not stop_evt.is_set():
            uid = f"sim-{i}-{n % 50}"
            n += 1
            try:
                r1 = c.get(f"{base}/api/queue", params={"uid": uid, "lang": "en"})
                r2 = c.post(f"{base}/api/slots/book", json={"uid": uid, "gate": f"g{1 + n % 5}"})
                ok = r1.status_code < 500 and r2.status_code < 500
            except Exception:
                ok = False
            with _rush_lock:
                RUSH["sent" if ok else "failed"] += 1
            if not ok:
                stop_evt.wait(0.5)


def rush_running():
    return any(t.is_alive() for t in RUSH["threads"])


@app.post("/api/rush/start")
def rush_start(x_rush_token: Optional[str] = Header(None), x_incident_token: Optional[str] = Header(None),
               workers: Optional[int] = None):
    _check_rush_token(x_rush_token, x_incident_token)
    with _rush_lock:
        if rush_running():
            return {"ok": True, "running": True, "note": "already running", "simulated": True}
        RUSH["stop"] = threading.Event()
        n = max(1, min(workers or config.RUSH_WORKERS(), 200))
        RUSH["threads"] = [threading.Thread(target=_rush_worker, args=(i, RUSH["stop"]), daemon=True)
                           for i in range(n)]
        RUSH.update(sent=0, failed=0, started=time.time())
    queue_sim.set_rush(True)
    crash.rush_started()
    if hasattr(volunteer, "mark_rush_detected"):
        try:
            volunteer.mark_rush_detected()
        except Exception as e:
            log.error("mark_rush_detected failed: %s", e)
    for t in RUSH["threads"]:
        t.start()
    return {"ok": True, "running": True, "workers": n, "simulated": True}


@app.post("/api/rush/stop")
def rush_stop(x_rush_token: Optional[str] = Header(None), x_incident_token: Optional[str] = Header(None)):
    _check_rush_token(x_rush_token, x_incident_token)
    RUSH["stop"].set()
    queue_sim.set_rush(False)
    crash.rush_stopped()
    return {"ok": True, "running": False, "sent": RUSH["sent"], "failed": RUSH["failed"]}


@app.get("/api/rush/status")
def rush_status():
    return {"running": rush_running(), "sent": RUSH["sent"], "failed": RUSH["failed"],
            "simulated": True}


# ---------- metrics ----------
@app.get("/api/metrics-lite")
def metrics_lite():
    m = metrics_window()
    now = time.time()
    m.update({"phones": sum(1 for t in list(_phones.values()) if now - t <= 30),
              "restarts": None,  # not knowable in-process; scripts read it from kubectl
              "map_mode": flags.map_mode(), "slot_mode": flags.slot_mode(),
              "bookings": slots.total(), "rush": rush_running(), "heavy_in_flight": _heavy_in_flight,
              "uptime_s": round(time.time() - STARTED, 1), "simulated": True})
    return m


# ---------- routers from other lanes (try-import so the app runs before they exist) ----------
def _mount(modname):
    try:
        mod = importlib.import_module(modname)
        app.include_router(mod.router)
        MOUNTED[modname] = "ok"
        return mod
    except ModuleNotFoundError as e:
        if e.name != modname:  # a dependency inside the module is missing: say so
            log.error("%s failed to import: %s", modname, e)
        MOUNTED[modname] = f"missing: {e}"
    except Exception as e:
        log.error("%s failed to mount: %s", modname, e)
        MOUNTED[modname] = f"error: {e}"
    return None


volunteer = _mount("volunteer")
directions = _mount("directions")
for _m in ("addons_sponsors", "addons_flags", "addons_read", "addons_scam", "addons_live", "addons_staff", "addons_state", "addons_care"):
    _mount(_m)


def _has_route(path):
    return any(getattr(r, "path", None) == path for r in app.routes)


if not _has_route("/api/incident"):
    @app.post("/api/incident")
    def incident(payload: dict, x_incident_token: Optional[str] = Header(None)):
        tok = config.INCIDENT_TOKEN()
        if not tok or not x_incident_token or not hmac.compare_digest(tok, x_incident_token):
            raise HTTPException(401, "bad or missing X-Incident-Token")
        if volunteer is None or not hasattr(volunteer, "start_incident"):
            raise HTTPException(503, "volunteer module is not available yet")
        volunteer.start_incident(payload.get("summary", ""), payload.get("root_cause", ""),
                                 payload.get("proposed_fix", ""), payload.get("event_id", ""))
        return {"ok": True}


@app.on_event("startup")
def _startup():
    flags.warn_if_local()
    slots.load()
    queue_sim.start()
    if hasattr(volunteer, "load"):
        try:
            volunteer.load()
        except Exception as e:
            log.error("volunteer.load failed: %s", e)
    try:
        rec = crash.check_after_start(flags.map_mode())
        if rec:
            log.warning("previous process died during a rush; crash report sent=%s", rec.get("sent"))
            if hasattr(volunteer, "mark_crash_seen"):
                volunteer.mark_crash_seen(rec.get("sent"))
    except Exception as e:
        log.error("crash check failed: %s", e)


@app.on_event("shutdown")
def _shutdown():
    RUSH["stop"].set()
    crash.rush_stopped()  # graceful stop is not a crash


STATIC.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
