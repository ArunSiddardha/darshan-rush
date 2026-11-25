"""Flagsmith wrapper. Server SDK with identities and traits, 2 s cache, default flag handler,
local in-memory fallback when no key (POST /api/dev/flag)."""
import hashlib
import json
import logging
import threading
import time

import config

log = logging.getLogger("flags")

DEFAULTS = {"map_mode": "full", "slot_mode": "open", "voice_directions": None,
            "assistant_llm": "on", "venue_pack": "venue_demo", "reply_style": "normal"}
ALLOWED = {"map_mode": ("full", "lite"), "slot_mode": ("open", "staggered"),
           "voice_directions": ("voice", "map"), "assistant_llm": ("on", "off"),
           "reply_style": ("normal", "brief"), "venue_pack": None}  # None: any safe pack name
LOCAL = dict(DEFAULTS)
TTL = 2.0

_lock = threading.Lock()
_client = None
_client_failed = False
_cache = {}  # name -> (t, value)

# Experiment counts kept locally too (Flagsmith results page is the source of truth when available)
EXPOSED = {"voice": set(), "map": set()}
REACHED = {"voice": set(), "map": set()}
EVENT_LOG = []


def using_flagsmith():
    return bool(config.FLAGSMITH_ENV_KEY())


def warn_if_local():
    if not using_flagsmith():
        print("WARNING: FLAGSMITH_ENV_KEY is not set. Using the LOCAL in-memory flag store "
              "(POST /api/dev/flag). This is not Flagsmith.", flush=True)


def _default_handler(name):
    from flagsmith.models import DefaultFlag
    return DefaultFlag(enabled=True, value=DEFAULTS.get(name))


def _sdk():
    global _client, _client_failed
    if _client or _client_failed or not using_flagsmith():
        return _client
    try:
        from flagsmith import Flagsmith
        _client = Flagsmith(environment_key=config.FLAGSMITH_ENV_KEY(),
                            api_url=config.FLAGSMITH_API_URL(), request_timeout_seconds=3,
                            default_flag_handler=_default_handler)
    except Exception as e:  # pragma: no cover
        log.error("Flagsmith SDK init failed: %s", e)
        _client_failed = True
    return _client


def _norm(name, v):
    """Value may be a plain string or JSON such as {"mode":"lite"}."""
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("{"):
            try:
                v = json.loads(s)
            except ValueError:
                pass
    if isinstance(v, dict):
        v = v.get("mode") or v.get("value")
    v = str(v or "").strip().lower().strip('"')
    if ALLOWED.get(name) is None:      # free-form name (venue_pack): letters, digits, _ and - only
        import re
        return v if re.fullmatch(r"[a-z0-9_\-]{1,60}", v) else None
    return v if v in ALLOWED[name] else None


def _hash_variant(uid):
    return "voice" if int(hashlib.sha256(uid.encode()).hexdigest(), 16) % 2 == 0 else "map"


def _env_value(name):
    """Environment-level value, cached 2 s. Falls back to the last good value, then the default."""
    now = time.time()
    hit = _cache.get(name)
    if hit and now - hit[0] < TTL:
        return hit[1]
    sdk = _sdk()
    if sdk:
        try:
            val = _norm(name, sdk.get_environment_flags().get_feature_value(name))
        except Exception as e:
            log.warning("%s fetch failed: %s", name, e)
            val = None
        val = val or (hit[1] if hit else DEFAULTS[name])
    else:
        val = _norm(name, LOCAL[name]) or DEFAULTS[name]
    _cache[name] = (now, val)
    return val


def map_mode():
    return _env_value("map_mode")


def slot_mode():
    return _env_value("slot_mode")


def assistant_llm():
    """'on': the assistant may call the Sarvam model (grounded in facts); 'off': rules and knowledge pack only."""
    return _env_value("assistant_llm")


def venue_pack():
    """Which knowledge pack (app/knowledge/<name>.json) the assistant and map use."""
    return _env_value("venue_pack")


def reply_style():
    """'brief' (or lite map mode, i.e. a rush): one short sentence per reply."""
    return "brief" if _env_value("reply_style") == "brief" or lite_mode() else "normal"


_raw_cache = {}


def raw_value(name):
    """Raw remote-config value (e.g. JSON for care_policy), cached 2 s; None when unavailable."""
    now = time.time()
    hit = _raw_cache.get(name)
    if hit and now - hit[0] < TTL:
        return hit[1]
    val = hit[1] if hit else None
    sdk = _sdk()
    if sdk:
        try:
            val = sdk.get_environment_flags().get_feature_value(name)
        except Exception as e:
            log.warning("%s fetch failed: %s", name, e)
    _raw_cache[name] = (now, val)
    return val


def lite_mode():
    return map_mode() == "lite"


def invalidate_cache():
    _cache.clear()


TRAITS = {}  # uid -> traits learned from conversation (e.g. age 65+ said to the voice assistant)


def set_traits(uid, traits):
    """Remember traits for this pilgrim; they are sent to Flagsmith with the identity on the next call."""
    with _lock:
        TRAITS.setdefault(uid, {}).update({k: v for k, v in traits.items() if k != "age"})
    sdk = _sdk()
    if sdk:
        try:
            sdk.get_identity_flags(uid, traits=dict(TRAITS[uid]))
        except Exception as e:
            log.warning("set_traits failed: %s", e)


def traits_for(lang=None, age_65_plus=None, uid=None):
    t = dict(TRAITS.get(uid, {})) if uid else {}
    if lang:
        t["language"] = lang
    if age_65_plus is not None:
        t["age_65_plus"] = bool(age_65_plus)
    return t


def voice_directions(uid, lang=None, age_65_plus=None, expose=False):
    """Variant for this pilgrim: 'voice' or 'map'. Identity + traits, so segments (language,
    age 65+) can override. expose=True records the exposure for the A/B test."""
    sdk = _sdk()
    variant = None
    source = "local"
    if sdk:
        source = "flagsmith"
        traits = traits_for(lang, age_65_plus, uid)
        try:
            if expose and hasattr(sdk, "get_experiment_flag"):
                variant = _norm("voice_directions", getattr(
                    sdk.get_experiment_flag("voice_directions", identifier=uid), "value", None))
            if variant is None:
                fl = sdk.get_identity_flags(uid, traits=traits or None)
                variant = _norm("voice_directions", fl.get_feature_value("voice_directions"))
        except Exception as e:
            log.warning("identity flags failed: %s", e)
    else:
        variant = _norm("voice_directions", LOCAL["voice_directions"])
    variant = variant or _hash_variant(uid)
    if expose:
        with _lock:
            EXPOSED[variant].add(uid)
    return {"voice_directions": variant, "source": source}


def get_flags(uid, lang=None, age_65_plus=None, expose=False):
    out = voice_directions(uid, lang, age_65_plus, expose)
    out.update({"map_mode": map_mode(), "slot_mode": slot_mode(),
                "traits": traits_for(lang, age_65_plus)})
    return out


def track_event(name, uid, variant, value=None):
    """The single place where conversion events leave the app (metric: reached_gate)."""
    with _lock:
        if name == "reached_gate" and variant in REACHED:
            REACHED[variant].add(uid)
        EVENT_LOG.append({"event": name, "uid": uid[:8], "variant": variant, "t": time.time()})
        del EVENT_LOG[:-20]
    sdk = _sdk()
    if sdk and hasattr(sdk, "track_event"):
        try:
            kw = {"identifier": uid}
            if value is not None:
                kw["value"] = value
            sdk.track_event(name, **kw)
            return True
        except Exception as e:
            log.warning("track_event failed: %s", e)
    return False


def experiment():
    with _lock:
        res = {}
        for v in ("voice", "map"):
            exp, hit = len(EXPOSED[v]), len(REACHED[v])
            res[v] = {"exposed": exp, "reached_gate": hit, "rate": round(hit / exp, 3) if exp else None}
        return {"flag": "voice_directions", "metric": "reached_gate", "variants": res,
                "source": "flagsmith" if _sdk() else "local", "recent_events": list(EVENT_LOG)}


def dev_set(name, value):
    if using_flagsmith():
        raise PermissionError("dev flag endpoint is disabled when Flagsmith is configured")
    if name not in LOCAL:
        raise KeyError(name)
    if value is not None and _norm(name, value) is None:
        raise ValueError(f"{name} must be one of {ALLOWED[name]}")
    with _lock:
        LOCAL[name] = value
    invalidate_cache()
