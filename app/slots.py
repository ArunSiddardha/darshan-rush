"""Darshan slot booking. SIMULATED. open mode = first come, staggered mode = spread across windows."""
import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import config
import queue_sim

IST = timezone(timedelta(hours=5, minutes=30))
LOOKAHEAD = 8  # windows examined per block in staggered mode

_lock = threading.Lock()
_by_uid = {}      # uid -> booking
_counts = {}      # window start (epoch s) -> count
_walkin_seq = 0
NOW = time.time   # tests replace this


def _save():
    """Write bookings to the /data volume so an OOM restart does not lose any pilgrim's slot."""
    try:
        path = config.BOOKINGS_FILE()
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"bookings": list(_by_uid.values()), "walkin_seq": _walkin_seq}, f)
        os.replace(tmp, path)
    except Exception:
        pass


def load():
    global _walkin_seq
    try:
        with open(config.BOOKINGS_FILE()) as f:
            d = json.load(f)
    except Exception:
        return 0
    with _lock:
        _by_uid.clear()
        _counts.clear()
        for b in d.get("bookings", []):
            _by_uid[b["uid"]] = b
            _counts[b["window"]] = _counts.get(b["window"], 0) + 1
        _walkin_seq = int(d.get("walkin_seq", 0))
        return len(_by_uid)


def _remote(name):
    """Caps and window from the Flagsmith remote config (ui_copy), so they change without a deploy."""
    try:
        import os
        if os.environ.get("UI_COPY_LIVE", "1") == "0":
            return None
        import addons_flags
        return addons_flags.remote_number(name)
    except Exception:
        return None


def _cap():
    return _remote("slot_cap") or config.SLOT_CAP()


def _window_s():
    return (_remote("slot_window_min") or config.SLOT_WINDOW_MIN()) * 60


def _first_window():
    """Start (epoch s) of the next window that has not begun yet."""
    w = _window_s()
    return (int(NOW()) // w + 1) * w


def _fmt(ts):
    return datetime.fromtimestamp(ts, IST).strftime("%H:%M")


def _slot(ts, booking):
    w = _window_s()
    return {"start": _fmt(ts), "end": _fmt(ts + w), "label": f"{_fmt(ts)} to {_fmt(ts + w)}",
            "window": ts, "gate": booking["gate"], "gate_name": queue_sim.BY_ID[booking["gate"]]["name"],
            "uid": booking["uid"], "walk_in": booking["walk_in"]}


def _parse_time(t):
    """'HH:MM' (IST) -> epoch of the next occurrence, or None. An int or float is already an epoch."""
    if isinstance(t, (int, float)):
        return int(t)
    try:
        hh, mm = str(t).split(":")[:2]
        now = datetime.fromtimestamp(NOW(), IST)
        want = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if want <= now:
            want += timedelta(days=1)
        return int(want.timestamp())
    except Exception:
        return None


def _choose_staggered(start):
    """Spread arrivals: in each block of LOOKAHEAD windows take the least loaded one.
    If the whole block is at cap, move on to the next block. Always terminates with a slot."""
    w, cap, block = _window_s(), _cap(), 0
    while True:
        base = start + block * LOOKAHEAD * w
        cands = [(_counts.get(base + i * w, 0), i) for i in range(LOOKAHEAD)]
        count, i = min(cands)
        if count < cap:
            return base + i * w
        block += 1


def book(uid, gate, time_pref=None, mode="open", walk_in=False):
    """Returns (slot dict, already_booked). One booking per uid."""
    gate = queue_sim.resolve_gate(gate) or "g4"
    with _lock:
        if uid in _by_uid:
            return _slot(_by_uid[uid]["window"], _by_uid[uid]), True
        start = _first_window()
        pref = _parse_time(time_pref) if time_pref else None
        if pref and pref >= start:
            start = (pref // _window_s()) * _window_s()
        ts = _choose_staggered(start) if mode == "staggered" else start
        b = {"uid": uid, "gate": gate, "window": ts, "walk_in": bool(walk_in), "mode": mode}
        _by_uid[uid] = b
        _counts[ts] = _counts.get(ts, 0) + 1
        _save()
        return _slot(ts, b), False


def book_walk_in(gate, mode="open", uid=None):
    """Volunteer books on behalf of a pilgrim without a phone."""
    global _walkin_seq
    with _lock:
        _walkin_seq += 1
        n = _walkin_seq
    return book(uid or f"walkin-{n}", gate, None, mode, walk_in=True)


def cancel(uid):
    with _lock:
        b = _by_uid.pop(uid, None)
        if not b:
            return False
        _counts[b["window"]] = max(0, _counts.get(b["window"], 1) - 1)
        if not _counts[b["window"]]:
            _counts.pop(b["window"], None)
        _save()
        return True


def get(uid):
    with _lock:
        b = _by_uid.get(uid)
        return _slot(b["window"], b) if b else None


def listing(uid=None, n=8):
    """Next n windows with counts, plus this pilgrim's slot."""
    start, w, cap = _first_window(), _window_s(), _cap()
    with _lock:
        wins = [{"start": _fmt(start + i * w), "count": _counts.get(start + i * w, 0), "cap": cap}
                for i in range(n)]
        mine = _slot(_by_uid[uid]["window"], _by_uid[uid]) if uid in _by_uid else None
        total = len(_by_uid)
        peak = max(_counts.values()) if _counts else 0
    return {"windows": wins, "mine": mine, "total": total, "peak_window": peak, "cap": cap,
            "simulated": True}


def total():
    return len(_by_uid)


def reset():
    global _walkin_seq
    with _lock:
        _by_uid.clear()
        _counts.clear()
        _walkin_seq = 0
        _save()
