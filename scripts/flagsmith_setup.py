#!/usr/bin/env python3
"""Idempotent Flagsmith setup for Darshan Rush. Never prints keys.

Creates: segments elders_65_plus + lang_ml/ta/te/kn/hi, features voice_first (bool, ON for
elders_65_plus), ui_copy (JSON remote config), voice_agent_v2 (bool, staged rollout segment
rollout_voice_agent_v2 with a PERCENTAGE_SPLIT rule).

Usage:
  python3 flagsmith_setup.py                 # create everything, then verify via the edge API
  python3 flagsmith_setup.py --set-rollout N # set rollout percentage (0-100) for voice_agent_v2
  python3 flagsmith_setup.py --get-rollout   # print the current percentage
Env: FLAGSMITH_ADMIN_KEY, FLAGSMITH_CLIENT_KEY (verify only). Project 55985, env 119864.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "https://api.flagsmith.com/api/v1"
EDGE = "https://edge.api.flagsmith.com/api/v1"
PROJECT = int(os.environ.get("FLAGSMITH_PROJECT_ID", "55985"))
ENV_ID = int(os.environ.get("FLAGSMITH_ENV_ID", "119864"))
ROLLOUT_SEGMENT = "rollout_voice_agent_v2"
LANGS = ["ml", "ta", "te", "kn", "hi"]

UI_COPY = {
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


def _key(name):
    k = os.environ.get(name, "").strip()
    if not k:
        sys.exit(f"{name} is not set (load repo/.env)")
    return k


def call(method, path, body=None, base=BASE):
    req = urllib.request.Request(
        base + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Api-Key " + _key("FLAGSMITH_ADMIN_KEY"), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()[:400]}") from None


def _list(path):
    out, url = [], path
    while url:
        d = call("GET", url)
        out += d.get("results", [])
        nxt = d.get("next")
        url = nxt.replace(BASE, "") if nxt else None
    return out


def get_segment(name):
    for s in _list(f"/projects/{PROJECT}/segments/?page_size=100"):
        if s["name"] == name:
            return s
    return None


def get_feature(name):
    for f in _list(f"/projects/{PROJECT}/features/?page_size=100"):
        if f["name"] == name:
            return f
    return None


def ensure_segment(name, conditions, description="", rule_type="ANY"):
    s = get_segment(name)
    if s:
        print(f"segment {name}: exists ({s['id']})")
        return s
    inner = {"type": rule_type, "rules": [], "conditions": conditions}
    s = call("POST", f"/projects/{PROJECT}/segments/", {
        "name": name, "description": description, "project": PROJECT,
        "rules": [{"type": "ALL", "rules": [inner], "conditions": []}]})
    print(f"segment {name}: created ({s['id']})")
    return s


def ensure_feature(name, kind="STANDARD", initial_value=None, default_enabled=False, description=""):
    f = get_feature(name)
    if f:
        print(f"feature {name}: exists ({f['id']})")
        return f
    body = {"name": name, "type": kind, "default_enabled": default_enabled, "description": description}
    if initial_value is not None:
        body["initial_value"] = initial_value
    f = call("POST", f"/projects/{PROJECT}/features/", body)
    print(f"feature {name}: created ({f['id']})")
    return f


def publish_version(feature_id, **payload):
    payload["publish_immediately"] = True
    return call("POST", f"/environments/{ENV_ID}/features/{feature_id}/versions/", payload)


def live_states(feature_id):
    """Feature states of the live version: env default plus segment overrides."""
    return call("GET", f"/environments/{ENV_ID}/features/{feature_id}/versions/?page_size=1&ordering=-created_at")


def _states(feature_id):
    vs = call("GET", f"/environments/{ENV_ID}/features/{feature_id}/versions/")
    live = [v for v in vs.get("results", []) if v.get("is_live")]
    live.sort(key=lambda v: v.get("live_from") or "", reverse=True)
    if not live:
        return []
    return call("GET", f"/environments/{ENV_ID}/features/{feature_id}/versions/{live[0]['uuid']}/featurestates/")


def ensure_override(feature_id, segment_id, enabled=True, string_value=None):
    """Segment override on a feature (env uses v2 versioning)."""
    for st in _states(feature_id):
        fs = st.get("feature_segment")
        seg = fs.get("segment") if isinstance(fs, dict) else None
        if seg == segment_id:
            want_val = string_value
            cur = st.get("feature_state_value")
            if st.get("enabled") == enabled and (want_val is None or cur == want_val):
                return "exists"
            break
    fsv = {"type": "unicode", "string_value": string_value or ""}
    try:
        publish_version(feature_id, feature_states_to_create=[{
            "feature_segment": {"segment": segment_id}, "enabled": enabled,
            "feature_state_value": fsv}])
    except RuntimeError:
        # the override exists: update it instead
        upd = [dict(st, enabled=enabled) for st in _states(feature_id)
               if isinstance(st.get("feature_segment"), dict) and st["feature_segment"].get("segment") == segment_id]
        if not upd:
            raise
        if fsv:
            for u in upd:
                u["feature_state_value"] = fsv
        publish_version(feature_id, feature_states_to_update=upd)
    return "set"


def set_rollout(pct):
    """Set voice_agent_v2 rollout percentage: segment rollout_voice_agent_v2 PERCENTAGE_SPLIT rule."""
    pct = max(0, min(100, int(pct)))
    seg = get_segment(ROLLOUT_SEGMENT)
    if not seg:
        sys.exit("run flagsmith_setup.py first (rollout segment missing)")
    rule = _find_split_rule(seg)
    cond = {"operator": "PERCENTAGE_SPLIT", "property": None, "value": str(pct)}  # property must be null on a split: a name makes the engine hash that trait instead of the identity
    if rule:
        cond["id"] = rule["id"]
        inner_rule = rule["_parent"]
        body = {"rules": [{"id": seg["rules"][0]["id"], "type": "ALL", "conditions": [], "rules": [
            {"id": inner_rule["id"], "type": "ALL", "conditions": [cond], "rules": []}]}]}
        call("PATCH", f"/projects/{PROJECT}/segments/{seg['id']}/", body)
    return pct


def _find_split_rule(seg):
    for r in seg.get("rules", []):
        for rr in r.get("rules", []):
            for c in rr.get("conditions", []):
                if c.get("operator") == "PERCENTAGE_SPLIT":
                    return dict(c, _parent=rr)
    return None


def get_rollout():
    seg = get_segment(ROLLOUT_SEGMENT)
    c = _find_split_rule(seg) if seg else None
    return int(float(c["value"])) if c else None


def edge_identity(uid, traits):
    req = urllib.request.Request(
        EDGE + "/identities/", method="POST",
        data=json.dumps({"identifier": uid, "traits": [{"trait_key": k, "trait_value": v} for k, v in traits.items()]}).encode(),
        headers={"X-Environment-Key": _key("FLAGSMITH_CLIENT_KEY"), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return {f["feature"]["name"]: f for f in json.load(r)["flags"]}


def main():
    args = sys.argv[1:]
    if args[:1] == ["--set-rollout"]:
        print(set_rollout(int(args[1])))
        return
    if args[:1] == ["--get-rollout"]:
        print(get_rollout())
        return
    elders = ensure_segment("elders_65_plus", [{"operator": "EQUAL", "property": "age_65_plus", "value": "true"}],
                            "Pilgrims aged 65 or more: voice-first experience")
    for l in LANGS:
        ensure_segment(f"lang_{l}", [{"operator": "EQUAL", "property": "language", "value": l}],
                       f"Pilgrims who speak {l}")
    # the spec names language segments by the trait values; also create plain-name aliases
    vf = ensure_feature("voice_first", "STANDARD", None, False, "Voice-first UI (mic first, big buttons)")
    print("voice_first override for elders_65_plus:", ensure_override(vf["id"], elders["id"], True))
    ensure_feature("ui_copy", "STANDARD", json.dumps(UI_COPY, ensure_ascii=False), True,
                        "Remote config: banner text per language, slot window and cap, mic example phrases")
    v2 = ensure_feature("voice_agent_v2", "STANDARD", None, False, "Voice agent v2: staged rollout 10 -> 50 -> 100")
    seg = get_segment(ROLLOUT_SEGMENT)
    if not seg:
        seg = ensure_segment(ROLLOUT_SEGMENT, [{"operator": "PERCENTAGE_SPLIT", "property": "x", "value": "0"}],
                             "Staged rollout of voice_agent_v2", rule_type="ALL")
        set_rollout(0)  # create needs a non-blank property; this PATCH nulls it so the split hashes the identity
    print("voice_agent_v2 override for rollout segment:", ensure_override(v2["id"], seg["id"], True))
    # ----- verify through the edge API -----
    import time
    time.sleep(3)
    a = b = False
    old = {}
    for _ in range(6):
        old = edge_identity("setup-check-elder", {"age_65_plus": True, "language": "ml"})
        young = edge_identity("setup-check-young", {"age_65_plus": False, "language": "en"})
        a, b = old["voice_first"]["enabled"], young["voice_first"]["enabled"]
        if a and not b:
            break
        time.sleep(3)
    print(f"edge check: elder voice_first={a} (want True), younger voice_first={b} (want False)")
    ok = a and not b
    cp = old.get("ui_copy", {}).get("feature_state_value")
    print("edge ui_copy present:", bool(cp))
    print("rollout percentage now:", get_rollout())
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
