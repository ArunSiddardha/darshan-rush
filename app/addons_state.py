"""One shared state for every screen (GET /api/state) and the assistant health guard (rolling window of model
calls -> one NudgeBee webhook POST with a 10 minute cool-down; POST /api/assistant/simulate-failure for the demo)."""
import hmac
import logging
import os
import statistics
import threading
import time
from collections import deque
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

log = logging.getLogger("state")
router = APIRouter()


def _wire_care():
    """Care routing policy comes from the Flagsmith remote-config flag care_policy (read on every routing decision)."""
    try:
        import addons_care
        import flags
        addons_care.set_policy_source(lambda: flags.raw_value("care_policy"))
    except Exception as e:
        log.info("care policy source not wired: %s", e)


_wire_care()

WINDOW_S, FAIL_N, SLOW_MS, COOLDOWN_S = 60, 5, 8000, 600
_calls = deque(maxlen=200)          # (t, ok, ms, err)
_guard = {"last_post": 0.0, "last_result": None, "posts": 0, "last_error": None}
_lock = threading.Lock()


def record(ok, ms, err=None):
    """Called after every Sarvam model call by the assistant."""
    with _lock:
        _calls.append((time.time(), bool(ok), int(ms or 0), err))
        if err:
            _guard["last_error"] = str(err)[:160]
    _maybe_alert()


def _recent():
    now = time.time()
    return [c for c in list(_calls) if now - c[0] <= WINDOW_S]


def health():
    rec = _recent()
    bad = [c for c in rec if not c[1] or c[2] > SLOW_MS]
    lat = [c[2] for c in rec if c[1]]
    llm = "on"
    try:
        import flags
        llm = flags.assistant_llm()
    except Exception:
        pass
    return {"calls_last_minute": len(rec), "failures_last_minute": len(bad),
            "median_latency_ms": int(statistics.median(lat)) if lat else None,
            "last_error": _guard["last_error"], "assistant_llm": llm,
            "fallback": llm == "off",
            "fallback_line": "Assistant on fallback (approved in NudgeBee)" if llm == "off" else None,
            "guard": {"threshold": f"{FAIL_N} failures or calls over {SLOW_MS // 1000} s within a minute",
                      "last_post": _guard["last_post"] or None, "last_result": _guard["last_result"],
                      "posts": _guard["posts"], "webhook_configured": bool(os.environ.get("NUDGEBEE_ASSISTANT_WEBHOOK"))}}


def _maybe_alert():
    rec = _recent()
    bad = [c for c in rec if not c[1] or c[2] > SLOW_MS]
    if len(bad) < FAIL_N or time.time() - _guard["last_post"] < COOLDOWN_S:
        return
    _guard["last_post"] = time.time()
    h = health()
    payload = {"service": "voice assistant", "failures_last_minute": h["failures_last_minute"],
               "last_error": h["last_error"], "median_latency_ms": h["median_latency_ms"]}
    threading.Thread(target=_post, args=(payload,), daemon=True).start()


def _post(payload):
    url = os.environ.get("NUDGEBEE_ASSISTANT_WEBHOOK", "").strip()
    if not url:
        _guard["last_result"] = "not sent: NUDGEBEE_ASSISTANT_WEBHOOK is not set"
        return
    try:
        import httpx
        r = httpx.post(url, json=payload, timeout=8)
        _guard["last_result"] = f"sent, HTTP {r.status_code}"
        _guard["posts"] += 1
    except Exception as e:
        _guard["last_result"] = f"send failed: {e.__class__.__name__}"
    log.info("assistant health webhook: %s", _guard["last_result"])


@router.post("/api/assistant/simulate-failure")
def simulate_failure(n: int = 6, x_incident_token: Optional[str] = Header(None), x_rush_token: Optional[str] = Header(None)):
    """Record n failed model calls (no Sarvam credits used) so the demo can trigger the NudgeBee guard."""
    import config
    want = [t for t in (config.INCIDENT_TOKEN(), config.RUSH_TOKEN()) if t]
    got = x_incident_token or x_rush_token or ""
    if not want or not any(hmac.compare_digest(w, got) for w in want):
        raise HTTPException(401, "token required")
    for _ in range(max(1, min(int(n), 20))):
        record(False, 0, "simulated failure (demo, no Sarvam call)")
    return {"ok": True, "health": health()}


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as e:
        log.debug("state part failed: %s", e)
        return default


@router.get("/api/state")
def api_state(uid: str = "anon", role: str = "pilgrim", lang: str = "en"):
    """Everything a page needs in one poll, so every open screen stays in sync."""
    import flags
    import queue_sim
    import slots
    lang = lang if lang in ("en", "hi", "ml", "ta", "te", "kn") else "en"
    mm, sm = _safe(flags.map_mode, "full"), _safe(flags.slot_mode, "open")
    out = {"now": time.time(), "role": role, "simulated": True,
           "flags": {"map_mode": mm, "slot_mode": sm, "assistant_llm": _safe(flags.assistant_llm, "on"),
                     "venue_pack": _safe(flags.venue_pack, "venue_demo"), "reply_style": _safe(flags.reply_style, "normal"),
                     "source": "flagsmith" if _safe(flags.using_flagsmith, False) else "local"},
           "mode": "rush" if (sm == "staggered" or _safe(queue_sim.rush_on, False)) else "calm",
           "queue": _safe(queue_sim.snapshot, {}),
           "assistant": health()}
    out["rush_line"] = "Rush mode: staggered slots" if sm == "staggered" else None
    if uid and uid != "anon":
        out["visitor_flags"] = _safe(lambda: flags.get_flags(uid, None, None, expose=False), {})
    import assistant
    out["map"] = _safe(lambda: assistant.map_data(uid, lang), {})
    out["position"] = _safe(lambda: assistant.get_position(uid))
    out["slot"] = _safe(lambda: slots.listing(uid).get("mine"))
    vol = _safe(lambda: __import__("volunteer").public(), {}) if role in ("staff", "judge") else None
    if vol is not None:
        out["volunteer"] = vol
    if role in ("staff", "judge"):
        out["help"] = _safe(lambda: [h for h in __import__("addons_staff").HELP if h.get("status") == "open"][-20:], [])
        care = _safe(lambda: __import__("addons_care").get_open()["requests"][:20], None)
        if care is not None:
            out["care"] = care
    if role == "judge":
        out["metrics"] = _safe(lambda: __import__("main").metrics_window(), {})
    try:
        import kb
        out["venue"] = kb.pack_info()
    except Exception:
        out["venue"] = None
    return out


def _page(name):
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).parent / "static" / name, media_type="text/html", headers={"Cache-Control": "no-cache"})


@router.get("/for-temples", include_in_schema=False)
def for_temples():
    return _page("for-temples.html")


@router.get("/start", include_in_schema=False)
def start():
    return _page("start.html")
