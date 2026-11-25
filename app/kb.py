"""Venue knowledge base: loads a swappable JSON pack and finds the entries that answer a spoken or typed question.

No external services, no embeddings. The scorer works on English, Indian-script text and romanised speech-recogniser
output: exact word, word-ending (prefix), consonant-skeleton and fuzzy character matches, weighted by how rare a word
is across the pack (rare words say more than 'help').

    kb.facts_for(text, lang, position_stop_id=None) -> str | None     # block for the chat model, None = unknown
    kb.search(text, lang, k=5) -> [{"id", "topic", "score", "answer", "where"}]
    kb.topics(lang="en") -> ["Opening hours and daily schedule", ...]
Pack: env VENUE_PACK = name in app/knowledge (default venue_demo) or an absolute path.
"""
import difflib
import json
import math
import os
import re
import threading
import unicodedata
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"
THRESHOLD = 1.8          # minimum score of the best entry; below it we say "I do not know"
_lock = threading.Lock()
_state = {"key": None, "pack": None, "index": None}

STOP = set("""a an the is are am was were be to of in on at for and or but with without from by as it its this that these those
i me my we our you your he she they them do does did can could should would will shall may might please tell show give want need
know get got have has had how what when where which who whom why there here any some very much many about also so then than
if not no yes ok okay hello hi sir madam kindly just let us one two like see go going come""".split())
STOP |= set("""में है हैं का की के को से पर और कि क्या कहाँ कहां कैसे कब कौन मुझे मैं हम आप यह वह एक भी तो ही
ఎక్కడ ఏమిటి ఎలా ఏంటి ఉంది ఉన్నాయి నాకు మీరు ఇది అది
எங்கே என்ன எப்படி உள்ளது இருக்கிறது எனக்கு நீங்கள் இது அது
എവിടെ എന്ത് എങ്ങനെ ഉണ്ട് എനിക്ക് നിങ്ങൾ ഇത് അത്
ಎಲ್ಲಿ ಏನು ಹೇಗೆ ಇದೆ ನನಗೆ ನೀವು ಇದು ಅದು
kahan kya kya kaise hai hain mujhe kidhar ekkada enti ela undi enga enna epdi irukku evide enthu engane undu ellide enu hege ide""".split())
_ZW = dict.fromkeys([0x200B, 0x200C, 0x200D, 0xFEFF], None)
_INDIC = re.compile(r"[ऀ-෿]")
_VOW = re.compile(r"[aeiouy]")


def _norm_text(s):
    s = unicodedata.normalize("NFC", str(s or "")).translate(_ZW).lower()
    s = "".join(" " if unicodedata.category(c)[0] in "PSZC" else c for c in s)
    return s


def _tokens(s):
    return [t for t in _norm_text(s).split() if t and t not in STOP]


def _skeleton(t):
    """Romanised word -> consonant skeleton so neeru / neellu / niru land close together."""
    if _INDIC.search(t) or not t.isascii():
        return ""
    t = t.replace("aa", "a").replace("ee", "i").replace("oo", "u").replace("th", "t").replace("dh", "d").replace("kh", "k").replace("ph", "p").replace("sh", "s").replace("ch", "c")
    t = t[:1] + _VOW.sub("", t[1:])
    return re.sub(r"(.)\1+", r"\1", t)


def _grams(t):
    t = f"#{t}#"
    return {t[i:i + 3] for i in range(len(t) - 2)}


def _strength(q, v):
    """How well query token q matches vocabulary token v: 0 = not at all, up to 1.0 exact."""
    if q == v:
        return 1.0
    indic = bool(_INDIC.search(q)) or bool(_INDIC.search(v))
    if bool(_INDIC.search(q)) != bool(_INDIC.search(v)):
        return 0.0
    short, long_ = (q, v) if len(q) <= len(v) else (v, q)
    if len(short) >= (3 if indic else 4) and long_.startswith(short) and len(long_) - len(short) <= (4 if indic else 4):
        return 0.8
    if indic:
        if len(q) >= 3 and len(v) >= 3:
            a, b = _grams(q), _grams(v)
            j = len(a & b) / len(a | b)
            if j >= 0.6:
                return 0.55 + 0.2 * j
        return 0.0
    if abs(len(q) - len(v)) > 3 or len(q) < 4 or len(v) < 4:
        return 0.0
    sq, sv = _skeleton(q), _skeleton(v)
    if len(sq) >= 2 and sq == sv:
        return 0.7
    if q[0] != v[0]:
        return 0.0
    r = difflib.SequenceMatcher(None, q, v).ratio()
    return 0.6 if r >= 0.78 else 0.0


def _pack_path():
    name = os.environ.get("VENUE_PACK", "venue_demo").strip() or "venue_demo"
    p = Path(name)
    if not p.is_absolute():
        p = KNOWLEDGE_DIR / (name if name.endswith(".json") else name + ".json")
    return p


def validate(pack):
    """Light schema check (no jsonschema dependency). Returns a list of problems, empty when fine."""
    bad = []
    if not isinstance(pack, dict) or not pack.get("venue"):
        bad.append("missing venue")
    ents = pack.get("entries") if isinstance(pack, dict) else None
    if not isinstance(ents, list) or not ents:
        return bad + ["entries must be a non-empty list"]
    seen = set()
    for i, e in enumerate(ents):
        for k in ("id", "topic", "triggers", "answer"):
            if not e.get(k):
                bad.append(f"entry {i} missing {k}")
        if e.get("id") in seen:
            bad.append(f"duplicate id {e.get('id')}")
        seen.add(e.get("id"))
    return bad


def _build(pack):
    ents = pack["entries"]
    vocab = {}                       # token -> {entry idx: multiplier}; words in the topic title count more
    for i, e in enumerate(ents):
        toks = set(_tokens(" ".join(e.get("triggers", []))))
        toks |= set(_tokens(" ".join(e.get("tags", [])))) | set(_tokens(" ".join(e.get("example_questions", []))))
        for t in toks:
            vocab.setdefault(t, {})[i] = 1.0
        for t in _tokens(e.get("topic", "")):
            vocab.setdefault(t, {})[i] = 1.6
    n = len(ents)
    idf = {t: math.log((n + 1) / (len(s) + 0.5)) for t, s in vocab.items()}
    for st in pack.get("stops", []):          # place names appear in many entries and are rarely the topic itself
        for t in _tokens(st.get("name", "")):
            if t in idf:
                idf[t] *= 0.5
    return {"ents": ents, "vocab": vocab, "idf": idf, "cache": {}, "stops": {s["id"]: s["name"] for s in pack.get("stops", [])}}


def load(force=False):
    """Load (once per pack name) and return the index. Raises ValueError for an unusable pack."""
    path = _pack_path()
    key = (str(path), path.stat().st_mtime if path.exists() else 0)
    with _lock:
        if not force and _state["key"] == key and _state["index"]:
            return _state["index"]
        try:
            with open(path, encoding="utf-8") as f:
                pack = json.load(f)
        except (OSError, ValueError) as e:
            raise ValueError(f"venue pack {path.name} unreadable: {e}")
        bad = validate(pack)
        if bad:
            raise ValueError(f"venue pack {path.name} invalid: {'; '.join(bad[:3])}")
        _state.update(key=key, pack=pack, index=_build(pack))
        return _state["index"]


def pack_info():
    idx = load()
    p = _state["pack"]
    return {"venue": p.get("venue"), "id": p.get("id"), "entries": len(idx["ents"]), "simulated": bool(p.get("simulated")), "file": _pack_path().name}


def venue_name():
    load()
    return _state["pack"].get("venue", "")


def _matches(idx, q):
    """[(vocab token, strength)] for one query token, cached."""
    c = idx["cache"]
    if q not in c:
        hits = []
        for v in idx["vocab"]:
            s = _strength(q, v)
            if s:
                hits.append((v, s))
        if len(c) > 2000:
            c.clear()
        c[q] = hits
    return c[q]


def search(text, lang="en", k=5, position_stop_id=None):
    """Top-k entries for the question, best first. Empty list when nothing matches."""
    try:
        idx = load()
    except ValueError:
        return []
    qs = list(dict.fromkeys(_tokens(text)))
    if not qs:
        return []
    scores = {}
    for q in qs:
        best = {}                                 # entry idx -> best weight for this query token
        for v, s in _matches(idx, q):
            for i, mult in idx["vocab"][v].items():
                w = idx["idf"][v] * s * mult
                if w > best.get(i, 0):
                    best[i] = w
        for i, w in best.items():
            scores[i] = scores.get(i, 0) + w
    out = []
    for i, sc in scores.items():
        e = idx["ents"][i]
        if position_stop_id and e.get("where") == position_stop_id:
            sc *= 1.15
        out.append((sc, i))
    out.sort(key=lambda x: (-x[0], x[1]))
    return [{"id": idx["ents"][i]["id"], "topic": idx["ents"][i]["topic"], "score": round(sc, 2),
             "answer": idx["ents"][i]["answer"], "where": idx["ents"][i].get("where", "all")} for sc, i in out[:k]]


def facts_for(text, lang="en", position_stop_id=None, k=3):
    """Compact fact block for the chat model, or None when the pack has nothing relevant (say 'I do not know')."""
    hits = search(text, lang, k=max(k, 5), position_stop_id=position_stop_id)
    if not hits or hits[0]["score"] < THRESHOLD:
        return None
    top = hits[0]["score"]
    keep = [h for h in hits if h["score"] >= max(THRESHOLD * 0.8, top * 0.5)][:k]
    idx = load()
    lines = [f"VENUE FACTS ({venue_name()}, simulated):"]
    if position_stop_id:
        lines.append(f"The pilgrim is now at: {idx['stops'].get(position_stop_id, position_stop_id)}.")
    for h in keep:
        where = "" if h["where"] in ("all", None) else f" [applies at {idx['stops'].get(h['where'], h['where'])}]"
        lines.append(f"- {h['topic']}{where}: {h['answer']}")
    return "\n".join(lines)


def topics(lang="en"):
    """Short list of things a pilgrim can ask about (entry topics, in pack order)."""
    return [e["topic"] for e in load()["ents"]]
