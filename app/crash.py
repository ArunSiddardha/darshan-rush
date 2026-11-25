"""Crash self-report. A marker file on /data says a rush is running. If the next process start finds it still
set, the previous process died mid-rush (OOMKilled is a SIGKILL, so nothing could clear it): report once to the
NudgeBee crash webhook, count the restart, and leave the rush stopped."""
import json
import logging
import os
import time
from datetime import datetime, timezone

import httpx

import config

log = logging.getLogger("darshan")


def marker_path():
    return os.path.join(os.path.dirname(config.STATE_FILE()) or ".", "rush_marker.json")


def _read():
    try:
        with open(marker_path()) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _write(d):
    try:
        tmp = marker_path() + ".tmp"
        with open(tmp, "w") as f:
            json.dump(d, f)
        os.replace(tmp, marker_path())
    except Exception as e:
        log.error("rush marker not written: %s", e)


def rush_started():
    d = _read()
    d.update(running=True, started=time.time())
    d.setdefault("restarts", 0)
    _write(d)


def rush_stopped():
    """Clean stop (stop button, graceful shutdown). The restart count is kept."""
    d = _read()
    if d.get("running") or d:
        d["running"] = False
        _write(d)


def check_after_start(map_mode="full"):
    """Call once at startup. Returns the report record, or None when the last run ended cleanly."""
    d = _read()
    if not d.get("running"):
        return None
    d.update(running=False, restarts=int(d.get("restarts", 0)) + 1)
    _write(d)  # rush stays stopped: the new process has no rush threads and nothing restarts them
    rec = {"namespace": "darshan", "pod": os.environ.get("HOSTNAME", "unknown"),
           "reason": "OOMKilled (suspected)", "what_happened": "booking service restarted during a rush",
           "restarts_seen": d["restarts"], "map_mode": map_mode,
           "reported_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    url = config.NUDGEBEE_CRASH_WEBHOOK()
    if not url:
        rec["sent"] = False
        return rec
    try:
        r = httpx.post(url, json=rec, timeout=10)
        rec["sent"] = r.status_code < 400
        rec["status"] = r.status_code
    except Exception as e:
        rec["sent"] = False
        rec["error"] = e.__class__.__name__
        log.error("crash report failed: %s", e)
    return rec
