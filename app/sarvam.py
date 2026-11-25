"""Small Sarvam REST client (httpx): speech to text, translate, text to speech, chat.

No fake results. Every call has an 8 second timeout, raises a clear error, and returns
its own latency in milliseconds so the UI can show it. HTTP 402 raises SarvamNoCredits.
"""
import base64
import json
import os
import re
import time
from typing import NamedTuple, Optional

import httpx

import config

BASE = "https://api.sarvam.ai"
TIMEOUT = 8.0

# Short language code used in the app -> Sarvam BCP-47 code.
LANG_CODES = {"ml": "ml-IN", "ta": "ta-IN", "te": "te-IN", "kn": "kn-IN", "hi": "hi-IN", "en": "en-IN"}
CODE_TO_LANG = {v: k for k, v in LANG_CODES.items()}

NO_CREDITS_MSG = "Voice unavailable (Sarvam credits). Type instead."


class SarvamError(Exception):
    pass


class NoKey(SarvamError):
    pass


class SarvamNoCredits(SarvamError):
    """HTTP 402: the Sarvam account has no credits."""

    def __init__(self, detail=""):
        super().__init__(NO_CREDITS_MSG)
        self.detail = detail


class STTResult(NamedTuple):
    transcript: str
    language: Optional[str]   # short code (ml, ta, ...) or None
    ms: int


class TextResult(NamedTuple):
    text: str
    ms: int


class AudioResult(NamedTuple):
    wav: bytes
    ms: int


def short_lang(code):
    if not code:
        return None
    return CODE_TO_LANG.get(code) or (code.split("-")[0].lower() if code.split("-")[0].lower() in LANG_CODES else None)


def available():
    return bool(config.SARVAM_API_KEY())


def _headers():
    k = config.SARVAM_API_KEY()
    if not k:
        raise NoKey("SARVAM_API_KEY is not set. Voice is unavailable; type instead.")
    return {"api-subscription-key": k}


def _post(path, what, **kw):
    """One POST. Returns (response, ms). Raises SarvamNoCredits / SarvamError."""
    t0 = time.perf_counter()
    try:
        r = httpx.post(BASE + path, timeout=TIMEOUT, **kw)
    except httpx.TimeoutException:
        raise SarvamError(f"Sarvam {what} timed out after {int(TIMEOUT)} s")
    except httpx.HTTPError as e:
        raise SarvamError(f"Sarvam {what} network error: {e.__class__.__name__}")
    ms = int((time.perf_counter() - t0) * 1000)
    if r.status_code == 402:
        raise SarvamNoCredits(r.text[:200])
    if r.status_code == 429:
        raise SarvamError(f"Sarvam {what}: rate limited (429), try again in a moment")
    if r.status_code >= 400:
        raise SarvamError(f"Sarvam {what} {r.status_code}: {r.text[:200]}")
    return r, ms


def stt(audio: bytes, filename="audio.webm", content_type="audio/webm") -> STTResult:
    """Speech to text with saaras, codemix mode, language auto-detected."""
    r, ms = _post("/speech-to-text", "speech-to-text", headers=_headers(),
                  files={"file": (filename, audio, content_type)},
                  data={"model": os.environ.get("SARVAM_STT_MODEL", "saaras:v4"), "mode": "codemix"})
    j = r.json()
    return STTResult(j.get("transcript", "") or "", short_lang(j.get("language_code")), ms)


def translate(text: str, target: str, source="auto") -> TextResult:
    """Translate. target and source are short codes (ml) or full codes (ml-IN)."""
    tgt = LANG_CODES.get(target, target)
    src = "auto" if source == "auto" else LANG_CODES.get(source, source)
    r, ms = _post("/translate", "translate", headers=_headers(), json={
        "input": text[:1000], "source_language_code": src, "target_language_code": tgt})
    return TextResult(r.json()["translated_text"], ms)


def tts(text: str, lang: str) -> AudioResult:
    """Text to speech with bulbul. Returns wav bytes."""
    r, ms = _post("/text-to-speech", "text-to-speech", headers=_headers(), json={
        "text": text[:1500], "target_language_code": LANG_CODES.get(lang, lang),
        "model": os.environ.get("SARVAM_TTS_MODEL", "bulbul:v3"),
        "speaker": os.environ.get("SARVAM_TTS_SPEAKER", "shubh")})
    return AudioResult(base64.b64decode(r.json()["audios"][0]), ms)


def chat(system: str, user: str, max_tokens=400) -> TextResult:
    """Chat with sarvam-105b. <think> blocks are stripped."""
    h = _headers()
    h["Authorization"] = "Bearer " + config.SARVAM_API_KEY()
    r, ms = _post("/v1/chat/completions", "chat", headers=h, json={
        "model": os.environ.get("SARVAM_CHAT_MODEL", "sarvam-105b"), "temperature": 0.1, "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    txt = r.json()["choices"][0]["message"]["content"] or ""
    return TextResult(re.sub(r"<think>.*?</think>", "", txt, flags=re.S).strip(), ms)


def chat_json(system: str, user: str):
    """Chat that must return a JSON object. Returns (dict, ms)."""
    res = chat(system, user)
    m = re.search(r"\{.*\}", res.text, flags=re.S)
    if not m:
        raise SarvamError("no JSON in chat reply")
    try:
        return json.loads(m.group(0)), res.ms
    except ValueError:
        raise SarvamError("bad JSON in chat reply")
