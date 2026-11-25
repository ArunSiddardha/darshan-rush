"""POST /api/read-photo: read the text in a photo of a ticket, token slip or signboard.

Sarvam Vision (Document AI) is an async job API: POST /doc-ai/v1/job/parse (multipart file), poll
GET /doc-ai/v1/job/{id}/status, then GET /doc-ai/v1/job/{id}/results (JSON blocks). We then translate
with /translate and speak with /text-to-speech (same request shapes as sarvam.py).
Mount:  from addons_read import router as read_router ; app.include_router(read_router)
"""
import base64
import os
import time

import httpx
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

import sarvam_keys

router = APIRouter()

LANG_CODES = {"ml": "ml-IN", "ta": "ta-IN", "te": "te-IN", "kn": "kn-IN", "hi": "hi-IN", "en": "en-IN"}
NO_CREDITS = "Voice unavailable (Sarvam credits). Type instead."
MAX_BYTES = 8 * 1024 * 1024
POLL_TIMEOUT = float(os.environ.get("READ_POLL_TIMEOUT_S", "25"))
TERMINAL = {"completed", "partially_completed", "failed", "rejected"}
OK_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg", "image/tiff": "tiff", "application/pdf": "pdf"}


class ReadError(Exception):
    def __init__(self, notice, status=502):
        super().__init__(notice)
        self.notice, self.status = notice, status


def _check(r, what):
    if r.status_code in (402, 403):
        raise ReadError(NO_CREDITS, 402)
    if r.status_code == 429:
        raise ReadError("Sarvam is busy (rate limit). Try again in a moment.", 429)
    if r.status_code >= 400:
        raise ReadError(f"Sarvam {what} failed ({r.status_code}).", 502)
    return r


def ocr(data: bytes, filename: str, ctype: str, hint_lang: str):
    """Sarvam Vision parse job on one image. Returns the page text (blocks joined by newlines)."""
    try:
        r = _check(sarvam_keys.request("POST", "/doc-ai/v1/job/parse", timeout=20,
                   files={"file": (filename, data, ctype)},
                   data={"language": LANG_CODES.get(hint_lang, hint_lang), "output_format": "md"}), "photo upload")
        jid = r.json()["job_id"]
        t0 = time.time()
        while True:
            st = _check(sarvam_keys.request("GET", f"/doc-ai/v1/job/{jid}/status", timeout=10), "status").json()
            s = (st.get("status") or "").lower()
            if s in TERMINAL:
                break
            if time.time() - t0 > POLL_TIMEOUT:
                raise ReadError("Reading the photo took too long. Try again with a clearer photo.", 504)
            time.sleep(0.6)
        if s not in ("completed", "partially_completed"):
            raise ReadError("Could not read this photo. Try again in better light.", 422)
        res = _check(sarvam_keys.request("GET", f"/doc-ai/v1/job/{jid}/results", timeout=15), "results").json()
    except httpx.HTTPError as e:
        raise ReadError(f"Network problem reaching Sarvam ({e.__class__.__name__}).", 502)
    parts = []
    for doc in res.get("documents", []):
        for page in doc.get("pages", []):
            for b in sorted(page.get("blocks", []), key=lambda b: b.get("reading_order", 0)):
                if b.get("text"):
                    parts.append(b["text"].strip())
    return "\n".join(parts)


def translate(text: str, lang: str) -> str:
    try:
        r = _check(sarvam_keys.request("POST", "/translate", timeout=10, json={
            "input": text[:1000], "source_language_code": "auto", "target_language_code": LANG_CODES.get(lang, lang)}), "translate")
    except httpx.HTTPError as e:
        raise ReadError(f"Network problem reaching Sarvam ({e.__class__.__name__}).", 502)
    return r.json()["translated_text"]


def speak(text: str, lang: str) -> str:
    """base64 WAV from bulbul, same request shape as sarvam.tts."""
    try:
        r = _check(sarvam_keys.request("POST", "/text-to-speech", timeout=12, json={
            "text": text[:1500], "target_language_code": LANG_CODES.get(lang, lang),
            "model": os.environ.get("SARVAM_TTS_MODEL", "bulbul:v3"),
            "speaker": os.environ.get("SARVAM_TTS_SPEAKER", "shubh")}), "text-to-speech")
    except httpx.HTTPError as e:
        raise ReadError(f"Network problem reaching Sarvam ({e.__class__.__name__}).", 502)
    return r.json()["audios"][0]


def _has_indic(t):
    return any("\u0900" <= c <= "\u0d7f" for c in t)


def _fail(notice, status, lang, t0, text=""):
    return JSONResponse({"text": text, "translated_text": "", "audio_base64": "", "lang": lang,
                         "latency": {"total_ms": int((time.time() - t0) * 1000)}, "notice": notice}, status_code=status)


@router.post("/api/read-photo")
async def read_photo(image: UploadFile = File(...), lang: str = Form("en"), uid: str = Form(""), source_lang: str = Form("")):
    t0 = time.time()
    lang = lang if lang in LANG_CODES else "en"
    # OCR language hint. Verified: an en-IN hint makes Sarvam Vision hallucinate on Malayalam lines of a mixed board,
    # while an Indic hint reads English and Malayalam both correctly. So default to an Indic hint, not 'en'.
    source_lang = source_lang if source_lang in LANG_CODES else os.environ.get("READ_OCR_HINT", "hi")
    if not sarvam_keys.available():
        return _fail("Photo reading unavailable: Sarvam key is not set. Type instead.", 503, lang, t0)
    ctype = (image.content_type or "").split(";")[0].lower()
    data = await image.read()
    if ctype not in OK_TYPES:
        return _fail("Please send a PNG or JPEG photo.", 415, lang, t0)
    if not data or len(data) > MAX_BYTES:
        return _fail("The photo is empty or larger than 8 MB.", 413, lang, t0)
    lat = {}
    text = ""
    try:
        t = time.time()
        text = await run_in_threadpool(ocr, data, image.filename or "photo." + OK_TYPES[ctype], ctype, source_lang)
        lat["read_ms"] = int((time.time() - t) * 1000)
        if not text.strip():
            return _fail("No text found in this photo. Hold the phone steady and try again.", 200, lang, t0)
        translated = text
        if lang != "en" or _has_indic(text):
            t = time.time()
            translated = await run_in_threadpool(translate, text, lang)
            lat["translate_ms"] = int((time.time() - t) * 1000)
        audio = ""
        try:
            t = time.time()
            audio = await run_in_threadpool(speak, translated, lang)
            lat["tts_ms"] = int((time.time() - t) * 1000)
        except ReadError as e:       # text is still useful without voice
            lat["tts_error"] = e.notice
    except ReadError as e:
        return _fail(e.notice, e.status, lang, t0, text)
    lat["total_ms"] = int((time.time() - t0) * 1000)
    notice = lat.pop("tts_error", "")
    return {"text": text, "translated_text": translated, "audio_base64": audio, "lang": lang, "latency": lat, "notice": notice}
