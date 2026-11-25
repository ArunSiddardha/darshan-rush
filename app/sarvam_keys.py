"""Tiny Sarvam key pool. Reads SARVAM_API_KEY and SARVAM_API_KEY_2 from the environment (never logged).

current()          -> the key to use now (the first one that is not cooling down)
on_status(code)    -> call after every Sarvam response; HTTP 402 or 429 makes the current key
                      cool down (402: 10 min, 429: 30 s) so current() returns the other key
request(...)       -> convenience: httpx call that retries ONCE on the other key after 402/429

Integrator change to app/sarvam.py (two lines):
  1. in _headers():  k = config.SARVAM_API_KEY()   ->   k = sarvam_keys.current()
     (and in chat(): "Bearer " + config.SARVAM_API_KEY()  ->  "Bearer " + sarvam_keys.current())
  2. in _post(), right after `ms = int(...)`:  sarvam_keys.on_status(r.status_code)
  plus `import sarvam_keys` at the top. 402 handling stays as is; the next call then uses key 2.
"""
import os
import threading
import time

import httpx

BASE = "https://api.sarvam.ai"
COOLDOWN = {402: 600.0, 429: 30.0}
_lock = threading.Lock()
_cool = {}      # key index -> time until which it is skipped
_last = [0]     # index of the key returned by the last current()


def _keys():
    out = []
    for name in ("SARVAM_API_KEY", "SARVAM_API_KEY_2"):
        v = os.environ.get(name, "").strip()
        if v and v not in out:
            out.append(v)
    return out


def available():
    return bool(_keys())


def current():
    """Current key, or '' if none is set. If every key is cooling down, the one that recovers first."""
    ks = _keys()
    if not ks:
        return ""
    now = time.time()
    with _lock:
        for i in range(len(ks)):
            if _cool.get(i, 0) <= now:
                _last[0] = i
                return ks[i]
        i = min(range(len(ks)), key=lambda j: _cool.get(j, 0))
        _last[0] = i
        return ks[i]


def on_status(code):
    """Report an HTTP status. Returns True if the key was rotated (caller may retry once)."""
    if code not in COOLDOWN or len(_keys()) < 2:
        return False
    with _lock:
        _cool[_last[0]] = time.time() + COOLDOWN[code]
    return True


def reset():
    with _lock:
        _cool.clear()
        _last[0] = 0


def request(method, path, timeout=10.0, **kw):
    """httpx request to Sarvam with the pool key; one retry on the other key after 402/429.
    kw may include headers (the api-subscription-key header is added), json, data, files, params."""
    for attempt in (0, 1):
        k = current()
        if not k:
            raise RuntimeError("SARVAM_API_KEY is not set")
        h = dict(kw.pop("headers", None) or {})
        h["api-subscription-key"] = k
        r = httpx.request(method, BASE + path, headers=h, timeout=timeout, **kw)
        if attempt == 0 and on_status(r.status_code):
            # file handles must be rewound for the retry
            f = kw.get("files")
            if f:
                for v in (f.values() if isinstance(f, dict) else f):
                    fo = v[1] if isinstance(v, tuple) and len(v) > 1 else None
                    if hasattr(fo, "seek"):
                        fo.seek(0)
            continue
        return r
    return r
