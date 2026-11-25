"""Simulated crowd on a pilgrim route. Everything here is SIMULATED, never real data."""
import random
import threading
import time

GATES = [
    {"id": "g1", "name": "Base Camp", "base": 0.25},
    {"id": "g2", "name": "River Crossing", "base": 0.35},
    {"id": "g3", "name": "Forest Path", "base": 0.45},
    {"id": "g4", "name": "Queue Complex", "base": 0.60},
    {"id": "g5", "name": "Main Steps", "base": 0.50},
]
BY_ID = {g["id"]: g for g in GATES}
MAX_WAIT_MIN = 180

_lock = threading.Lock()
_load = {g["id"]: g["base"] for g in GATES}
_surge = 0.0       # 0..1 extra pressure, ramps up while a rush runs
_rush_on = False
_thread = None
_stop = threading.Event()
_rng = random.Random(7)


def wait_from_load(load, gate_idx=0):
    """Minutes of waiting grow faster than load (queues are nonlinear). Later gates are slower."""
    load = max(0.0, min(1.0, load))
    return int(round(4 + (MAX_WAIT_MIN - 4) * (load ** 2) * (0.55 + 0.1 * gate_idx)))


def step(dt=1.0):
    """Advance the simulation one tick. Public so tests can drive it without the thread."""
    global _surge
    with _lock:
        target = 0.6 if _rush_on else 0.0
        _surge += (target - _surge) * min(1.0, 0.25 * dt)
        for g in GATES:
            cur = _load[g["id"]]
            goal = min(1.0, g["base"] + _surge)
            cur += (goal - cur) * 0.2 + _rng.uniform(-0.03, 0.03)
            _load[g["id"]] = max(0.02, min(1.0, cur))


def _run():
    while not _stop.wait(1.0):
        step(1.0)


def start():
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_run, name="queue-sim", daemon=True)
    _thread.start()


def stop():
    _stop.set()


def set_rush(on):
    global _rush_on
    with _lock:
        _rush_on = bool(on)


def rush_on():
    return _rush_on


def report_crowd(gate, count):
    """A volunteer reports a head count at a gate; the simulated load follows (2500 people = full)."""
    gid = resolve_gate(gate)
    if not gid:
        return False
    with _lock:
        _load[gid] = max(0.02, min(1.0, float(count) / 2500.0))
    return True


def reset():
    global _surge, _rush_on
    with _lock:
        _surge = 0.0
        _rush_on = False
        for g in GATES:
            _load[g["id"]] = g["base"]


def snapshot():
    """Payload for /api/queue. Always labelled simulated."""
    with _lock:
        gates = [{"id": g["id"], "name": g["name"], "load": round(_load[g["id"]], 2),
                  "wait_min": wait_from_load(_load[g["id"]], i)} for i, g in enumerate(GATES)]
    return {"gates": gates, "simulated": True, "rush": _rush_on}


def gate_wait(gate_id):
    for g in snapshot()["gates"]:
        if g["id"] == gate_id:
            return g["wait_min"]
    return None


def resolve_gate(value):
    """Accept an id (g3), a 1-5 number or a name; return the gate id or None."""
    v = str(value or "").strip().lower()
    if v in BY_ID:
        return v
    if v.isdigit() and 1 <= int(v) <= len(GATES):
        return GATES[int(v) - 1]["id"]
    for g in GATES:
        if g["name"].lower() == v:
            return g["id"]
    return None
