"""Care requests: persistent store and the (simulated) volunteer roster.

Lives on the data volume next to STATE_FILE: <dir of STATE_FILE>/care.json (audio of the pilgrim's words in care_audio/).
Every call checks the path, so a different STATE_FILE (tests, restart) loads that folder's file.
Volunteers in SEED are SIMULATED; a staff member who checks in becomes a real (simulated=False) volunteer.
"""
import json
import os
import re
import tempfile
import threading
import time

import config

NOW = time.time          # tests replace this

CATEGORIES = ["medical", "lost_person", "lost_item", "safety_crowd", "harassment_theft", "tout_payment", "accessibility",
              "water_toilet_clean", "slot_booking", "staff_behaviour", "suggestion", "other"]
URGENCIES = ["emergency", "urgent", "normal"]
STATUSES = ["open", "assigned", "on_the_way", "resolved", "could_not_resolve"]
ACTIVE = ("open", "assigned", "on_the_way")

SEED = [  # SIMULATED volunteers, one or two per stop
    {"id": "v-meera", "name": "Meera", "stop": "g3", "langs": ["ml", "en"]},
    {"id": "v-ravi", "name": "Ravi", "stop": "g1", "langs": ["te", "hi", "en"]},
    {"id": "v-lakshmi", "name": "Lakshmi", "stop": "g2", "langs": ["ta", "en"]},
    {"id": "v-karthik", "name": "Karthik", "stop": "g2", "langs": ["te", "ta", "en"]},
    {"id": "v-suresh", "name": "Suresh", "stop": "g4", "langs": ["kn", "en"]},
    {"id": "v-anita", "name": "Anita", "stop": "g5", "langs": ["hi", "en"]},
    {"id": "v-joseph", "name": "Joseph", "stop": "g3", "langs": ["ml", "ta", "en"]},
]
DUTY_OFFICER = {"id": "duty", "name": "Duty officer", "stop": "g1", "langs": ["en", "hi", "te", "ta", "ml", "kn"], "role": "duty_officer"}

_lock = threading.RLock()
_db = None
_path = None


def folder():
    return os.path.dirname(config.STATE_FILE()) or "."


def path():
    return os.path.join(folder(), "care.json")


def audio_dir():
    return os.path.join(folder(), "care_audio")


def _seed():
    vols = {}
    for v in SEED:
        vols[v["id"]] = {**v, "on_duty": True, "simulated": True, "role": "volunteer", "checked_in_at": None}
    return {"counter": 0, "requests": [], "volunteers": vols}


def _load():
    global _db, _path
    p = path()
    with _lock:
        if _db is not None and _path == p:
            return _db
        db = None
        try:
            with open(p) as f:
                db = json.load(f)
            if not isinstance(db, dict) or "requests" not in db or "volunteers" not in db:
                db = None
        except (OSError, ValueError):
            db = None
        _db = db or _seed()
        _path = p
        return _db


def reload():
    """Forget memory and read the file again (what a restart does)."""
    global _db, _path
    with _lock:
        _db = None
        _path = None
        return _load()


def reset():
    """Tests: start from the seeded roster and no requests (does not delete files)."""
    global _db, _path
    with _lock:
        _db = _seed()
        _path = path()
        _save()


def _save():
    with _lock:
        if _db is None:
            return
        p = path()
        try:
            os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p) or ".", prefix=".care", suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(_db, f)
            os.replace(tmp, p)
        except OSError:
            pass   # the in-memory copy still works; persistence is best effort


def save():
    _save()


# ------------------------------------------------------------------ requests
def new_request(**kw):
    """Create and persist a request. kw: uid, language, transcript, summary_en, category, urgency, urgency_reason, stop_id, stop_name."""
    with _lock:
        db = _load()
        db["counter"] += 1
        t = NOW()
        r = {"id": f"C-{db['counter']}", "uid": kw.get("uid") or "anon", "language": kw.get("language") or "en",
             "transcript": kw.get("transcript") or "", "summary_en": kw.get("summary_en") or "",
             "category": kw.get("category") if kw.get("category") in CATEGORIES else "other",
             "urgency": kw.get("urgency") if kw.get("urgency") in URGENCIES else "normal",
             "urgency_reason": kw.get("urgency_reason") or "", "stop_id": kw.get("stop_id"), "stop_name": kw.get("stop_name"),
             "status": "open", "assigned_to": None, "tried": [], "escalated": False, "created_at": t, "assigned_at": None,
             "acknowledged_at": None, "resolved_at": None, "resolution_note": "", "has_audio": False, "via": kw.get("via", "rules"),
             "duty_officer_notified": False, "timeline": [{"t": t, "event": "created", "by": "pilgrim", "note": ""}]}
        db["requests"].append(r)
        _save()
        return r


def get(rid):
    with _lock:
        rid = (rid or "").strip().upper()
        for r in _load()["requests"]:
            if r["id"].upper() == rid:
                return r
    return None


def all_requests():
    with _lock:
        return list(_load()["requests"])


def log(r, event, by="system", note=""):
    with _lock:
        r["timeline"].append({"t": NOW(), "event": event, "by": by, "note": note})


def save_audio(rid, data, content_type):
    if not data or len(data) > 600_000:
        return False
    with _lock:
        try:
            os.makedirs(audio_dir(), exist_ok=True)
            with open(os.path.join(audio_dir(), re.sub(r"[^A-Za-z0-9-]", "", rid) + ".bin"), "wb") as f:
                f.write(data)
            r = get(rid)
            if r:
                r["has_audio"] = True
                r["audio_type"] = (content_type or "audio/webm").split(";")[0]
                _save()
            return True
        except OSError:
            return False


def load_audio(rid):
    try:
        with open(os.path.join(audio_dir(), re.sub(r"[^A-Za-z0-9-]", "", rid) + ".bin"), "rb") as f:
            return f.read()
    except OSError:
        return None


# ------------------------------------------------------------------ volunteers
def volunteers(on_duty_only=False):
    with _lock:
        vs = [dict(v) for v in _load()["volunteers"].values()]
    return [v for v in vs if v["on_duty"]] if on_duty_only else vs


def volunteer(vid):
    with _lock:
        v = _load()["volunteers"].get(vid)
        if v:
            return dict(v)
        for x in _load()["volunteers"].values():       # also accept the name
            if x["name"].lower() == str(vid).lower():
                return dict(x)
    return None


def checkin(name, stop, langs=None, on_duty=True):
    """A staff member checks in at a stop: becomes a real (not simulated) volunteer. Returns the volunteer."""
    name = (name or "").strip()[:40] or "Volunteer"
    vid = "v-" + (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "x")
    langs = [l for l in (langs or []) if l in ("en", "hi", "te", "ta", "ml", "kn")] or ["en"]
    with _lock:
        db = _load()
        v = db["volunteers"].get(vid)
        if v is None:
            v = {"id": vid, "name": name, "role": "volunteer"}
            db["volunteers"][vid] = v
        v.update({"stop": stop, "langs": langs, "on_duty": bool(on_duty), "simulated": False, "checked_in_at": NOW()})
        _save()
        return dict(v)
