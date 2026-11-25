"""Flagsmith add-ons router: why each flag has its value, remote UI copy, staged rollout status.

Mount: `from addons_flags import router as addons_flags_router; app.include_router(addons_flags_router)`
Env: FLAGSMITH_CLIENT_KEY (or FLAGSMITH_ENV_KEY), optional FLAGSMITH_ADMIN_KEY (rollout percentage),
     FLAGSMITH_API_URL (edge base), ROLLOUT_LOG (default repo/metrics/rollout.log).
Never raises on Flagsmith trouble: it reports source "defaults" and says so.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

from fastapi import APIRouter, Query

router = APIRouter()

EDGE = lambda: os.environ.get("FLAGSMITH_EDGE_URL", "https://edge.api.flagsmith.com/api/v1").rstrip("/")
ADMIN = "https://api.flagsmith.com/api/v1"
PROJECT = lambda: os.environ.get("FLAGSMITH_PROJECT_ID", "55985")
ROLLOUT_SEGMENT = "rollout_voice_agent_v2"
LANGS = ("en", "ml", "ta", "te", "kn", "hi")
TTL = 2.0
ROLLOUT_LOG = lambda: os.environ.get(
    "ROLLOUT_LOG", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "metrics", "rollout.log"))

FLAGS = ["map_mode", "slot_mode", "voice_directions", "voice_first", "voice_agent_v2", "ui_copy"]
# which segment can override which flag (the name we show in the WHY column)
SEGMENT_FOR = {"voice_first": "elders_65_plus", "voice_agent_v2": ROLLOUT_SEGMENT}

DEFAULT_COPY = {
    "slot_window_min": 15,
    "slot_cap": 30,
    "banner": {
        "en": "Book your darshan slot by speaking. Press the mic and say your name.",
        "ml": "സംസാരിച്ചുകൊണ്ട് ദർശന സ്ലോട്ട് ബുക്ക് ചെയ്യൂ. മൈക്ക് അമർത്തി നിങ്ങളുടെ പേര് പറയൂ.",
        "ta": "பேசியே தரிசன நேரத்தை பதிவு செய்யுங்கள். மைக்கை அழுத்தி உங்கள் பெயரைச் சொல்லுங்கள்.",
        "te": "మాట్లాడి దర్శన స్లాట్ బుక్ చేయండి. మైక్ నొక్కి మీ పేరు చెప్పండి.",
        "kn": "ಮಾತನಾಡಿ ದರ್ಶನ ಸ್ಲಾಟ್ ಬುಕ್ ಮಾಡಿ. ಮೈಕ್ ಒತ್ತಿ ನಿಮ್ಮ ಹೆಸರು ಹೇಳಿ.",
        "hi": "बोलकर दर्शन स्लॉट बुक करें। माइक दबाएं और अपना नाम बताएं।",
    },
    "examples": {
        "en": ["My name is Ravi, two people", "Book the morning slot", "Which gate is least crowded?"],
        "ml": ["എന്റെ പേര് രവി, രണ്ടു പേർ", "രാവിലത്തെ സ്ലോട്ട് വേണം", "ഏത് ഗേറ്റിലാണ് തിരക്ക് കുറവ്?"],
        "ta": ["என் பெயர் ரவி, இரண்டு பேர்", "காலை நேரம் வேண்டும்", "எந்த வாசலில் கூட்டம் குறைவு?"],
        "te": ["నా పేరు రవి, ఇద్దరు", "ఉదయం స్లాట్ కావాలి", "ఏ గేటు తక్కువ రద్దీ?"],
        "kn": ["ನನ್ನ ಹೆಸರು ರವಿ, ಇಬ್ಬರು", "ಬೆಳಿಗ್ಗೆ ಸ್ಲಾಟ್ ಬೇಕು", "ಯಾವ ಗೇಟ್ ಕಡಿಮೆ ರದ್ದಿ?"],
        "hi": ["मेरा नाम रवि है, दो लोग", "सुबह का स्लॉट चाहिए", "कौन सा गेट कम भीड़ वाला है?"],
    },
    "simulated_note": "Simulated crowd. Not affiliated with any temple. Not for operational use.",
}
DEFAULT_FLAGS = {"map_mode": ("full", True), "slot_mode": ("open", True), "voice_directions": (None, True),
                 "voice_first": (None, False), "voice_agent_v2": (None, False), "ui_copy": (None, True)}

_cache = {}  # key -> (t, data)


def _key():
    return (os.environ.get("FLAGSMITH_CLIENT_KEY") or os.environ.get("FLAGSMITH_ENV_KEY") or "").strip()


def _http(method, url, headers, body=None, timeout=4):
    req = urllib.request.Request(url, method=method, headers=dict(headers, **{"Content-Type": "application/json"}),
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def _parse(resp):
    return {f["feature"]["name"]: (f.get("feature_state_value"), bool(f.get("enabled"))) for f in resp}


def _environment_flags():
    """Environment defaults (no identity): what a visitor with no segment sees."""
    hit = _cache.get("env")
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    data = _parse(_http("GET", EDGE() + "/flags/", {"X-Environment-Key": _key()}))
    _cache["env"] = (time.time(), data)
    return data


def _identity_flags(uid, traits):
    ck = ("id", uid, json.dumps(traits, sort_keys=True))
    hit = _cache.get(ck)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    body = {"identifier": uid, "traits": [{"trait_key": k, "trait_value": v} for k, v in traits.items()]}
    data = _parse(_http("POST", EDGE() + "/identities/", {"X-Environment-Key": _key()}, body).get("flags", []))
    if len(_cache) > 500:
        _cache.clear()
    _cache[ck] = (time.time(), data)
    return data


def _reason(name, ident, env, traits):
    """Why does this visitor have this value? Compared with the environment default."""
    iv, ie = ident
    ev, ee = env if env else (None, None)
    if name == "voice_directions":
        return {"kind": "variant", "why": f"A/B variant '{iv}' (50/50 split, sticky per visitor)"}
    if (iv, ie) != (ev, ee):
        seg = SEGMENT_FOR.get(name)
        if seg == ROLLOUT_SEGMENT:
            return {"kind": "segment", "segment": seg, "why": f"in the staged rollout segment ({seg})"}
        if seg:
            return {"kind": "segment", "segment": seg, "why": f"segment {seg} (trait age_65_plus = true)"}
        return {"kind": "segment", "segment": None, "why": "segment override"}
    return {"kind": "default", "why": "environment default (no segment matched)"}


def _short(v):
    if isinstance(v, str) and len(v) > 60:
        return v[:57] + "..."
    return v


@router.get("/api/flags/decisions")
def decisions(uid: str = Query("anon"), lang: str = Query("en"), age65: bool = Query(False)):
    """Every flag value for this visitor, with the reason."""
    lang = lang if lang in LANGS else "en"
    traits = {"language": lang, "age_65_plus": bool(age65)}
    out = {"uid": uid, "traits": traits, "source": "flagsmith", "flags": []}
    if not _key():
        out["source"] = "unavailable"
        out["message"] = "Flagsmith key not set; showing safe defaults."
    else:
        try:
            ident = _identity_flags(uid, traits)
            env = _environment_flags()
        except Exception as e:
            out["source"] = "unavailable"
            out["message"] = f"Flagsmith unreachable ({type(e).__name__}); showing safe defaults."
            ident = env = None
    if out["source"] == "flagsmith":
        for n in FLAGS:
            if n in ident:
                r = _reason(n, ident[n], env.get(n), traits)
                out["flags"].append({"flag": n, "enabled": ident[n][1], "value": _short(ident[n][0]), **r})
    else:
        for n in FLAGS:
            v, e = DEFAULT_FLAGS[n]
            out["flags"].append({"flag": n, "enabled": e, "value": v, "kind": "default",
                                 "why": "safe default (Flagsmith not reachable)"})
    return out


def _merge_copy(remote):
    out = json.loads(json.dumps(DEFAULT_COPY))
    if isinstance(remote, dict):
        for k, v in remote.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k].update(v)
            else:
                out[k] = v
    return out


_copy_cache = [0.0, None]


def remote_number(name):
    """slot_cap / slot_window_min from the Flagsmith remote config 'ui_copy', cached 30 s. None if unavailable,
    so the caller falls back to its env default."""
    now = time.time()
    if now - _copy_cache[0] > 30:
        val = None
        if _key():
            try:
                raw = _environment_flags().get("ui_copy", (None, False))
                val = json.loads(raw[0]) if isinstance(raw[0], str) and raw[0].strip() else None
            except Exception:
                val = None
        _copy_cache[0], _copy_cache[1] = now, val
    try:
        v = int((_copy_cache[1] or {}).get(name))
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


@router.get("/api/ui-copy")
def ui_copy(lang: str = Query("en")):
    lang = lang if lang in LANGS else "en"
    source, remote, msg = "defaults", None, None
    if _key():
        try:
            raw = _environment_flags().get("ui_copy", (None, False))
            remote = json.loads(raw[0]) if isinstance(raw[0], str) and raw[0].strip() else None
            source = "flagsmith" if remote else "defaults"
        except Exception as e:
            msg = f"Flagsmith unreachable ({type(e).__name__}); using built-in copy."
    else:
        msg = "Flagsmith key not set; using built-in copy."
    c = _merge_copy(remote)
    res = {"lang": lang, "source": source, "banner": c["banner"].get(lang) or c["banner"]["en"],
           "examples": c["examples"].get(lang) or c["examples"]["en"],
           "slot_window_min": c["slot_window_min"], "slot_cap": c["slot_cap"],
           "simulated_note": c["simulated_note"]}
    if msg:
        res["message"] = msg
    return res


# ---------------- rollout ----------------
def _rollout_pct():
    """Percentage of the PERCENTAGE_SPLIT rule on the rollout segment (admin API), else None."""
    k = os.environ.get("FLAGSMITH_ADMIN_KEY", "").strip()
    if not k:
        return None
    hit = _cache.get("pct")
    if hit and time.time() - hit[0] < 3:
        return hit[1]
    try:
        d = _http("GET", f"{ADMIN}/projects/{PROJECT()}/segments/?page_size=100&q={ROLLOUT_SEGMENT}",
                  {"Authorization": "Api-Key " + k})
        pct = None
        for s in d.get("results", []):
            if s["name"] == ROLLOUT_SEGMENT:
                for r in s["rules"]:
                    for rr in r.get("rules", []):
                        for c in rr.get("conditions", []):
                            if c.get("operator") == "PERCENTAGE_SPLIT":
                                pct = int(float(c["value"]))
    except Exception:
        return None
    _cache["pct"] = (time.time(), pct)
    return pct


def _log_tail(n=12):
    try:
        with open(ROLLOUT_LOG(), "r", encoding="utf-8") as f:
            return [l.rstrip("\n") for l in f.readlines()[-n:]]
    except OSError:
        return []


@router.get("/api/rollout")
def rollout():
    lines = _log_tail()
    pct = _rollout_pct()
    source = "flagsmith"
    if pct is None:
        source = "log"
        for l in reversed(lines):
            m = re.search(r"\bpct=(\d+)", l)
            if m:
                pct = int(m.group(1))
                break
    return {"flag": "voice_agent_v2", "percent": pct, "source": source if pct is not None else "unknown",
            "steps": [10, 50, 100], "last_step": lines[-1] if lines else None, "log": lines,
            "rule": "Pause and roll back one step if 5xx errors exceed 2% of requests."}
