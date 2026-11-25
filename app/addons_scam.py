"""POST /api/site-check: calm warning about a pasted web address or a described offer ('pay 500 for a quick pass').

Keyword rules run first; the Sarvam chat model is asked only when the rules find nothing, and it can only
raise the verdict to caution or high_risk. We NEVER say a site is genuine. Only a host that ends in .gov.in is
described as 'looks like a government address, still check on the official notice board'.
Mount:  from addons_scam import router as scam_router ; app.include_router(scam_router)
"""
import base64
import json
import os
import re
import time
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

import sarvam_keys
from addons_read import LANG_CODES, NO_CREDITS, ReadError, speak, translate

router = APIRouter()

SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "cutt.ly", "rb.gy", "is.gd", "shorturl.at", "wa.me", "ow.ly", "tiny.cc"}
LOOKALIKE_WORDS = ("darshan", "sabarimala", "ayyappa", "temple", "devasom", "devaswom", "tirupati", "ttd", "pass", "vip", "booking", "ticket", "seva")
OFFICIAL_LOOK = ("gov", "govt", "official", "devasthanam", "devaswom")
MONEY = re.compile(r"(₹|\brs\.?\s*\d|\brupees?\b|\binr\b|\bpay(ing|ment)?\b|\d+\s*(rs|rupees)\b|\bupi\b|\bgpay\b|\bphonepe\b|\bpaytm\b|\bcash\b|\badvance\b|\bdeposit\b|\bfee\b|\bcharge\b|पैसे|रुपये|रुपए|రూపాయ|ఫీజు|രൂപ|പണം)", re.I)
URGENT = re.compile(r"(\burgent\b|\bhurry\b|\bonly today\b|\blast (chance|few)\b|\bquick(ly)?\b|\bfast\b|\bimmediately\b|\bnow only\b|\bwithin \d+ ?(min|hour)|\blimited\b|जल्दी|తొందర|വേഗ)", re.I)
VIP = re.compile(r"(\bvip\b|\bspecial (darshan|pass|entry)\b|\bskip (the )?(queue|line)\b|\bno queue\b|\bdirect entry\b|\bback ?door\b|\bquick darshan\b|\bfast ?track\b|\bexpress (entry|darshan)\b|\bguaranteed\b|\bconfirmed slot\b)", re.I)
PERSON = re.compile(r"(\bsend (me )?(otp|aadhaar|aadhar|id)\b|\botp\b|\baadhaar\b|\baadhar\b|\bcard number\b|\bcvv\b|\bpin\b)", re.I)
TOUT = re.compile(r"(\bagent\b|\bbroker\b|\btout\b|\barrange\b|\bget you in\b|\bnear the front\b|\bahead of (the )?(queue|line|others)\b|\bwhatsapp (me|us)\b)", re.I)
URL_RE = re.compile(r"(https?://[^\s]+|www\.[^\s]+|\b[a-z0-9-]+(\.[a-z0-9-]+)+(/[^\s]*)?)", re.I)

REPLIES = {
    "high_risk": "Please be careful. This has several signs of a scam: {why}. Do not pay anything and do not share OTP, Aadhaar or card details. "
                 "Darshan slots are booked only on the official notice board or at the official counter. Ask a volunteer or an official in uniform.",
    "caution": "Please be careful. {why}. Do not pay yet. Check the details on the official notice board or at the official counter before you pay or share anything.",
    "unknown": "I cannot check this for you. Do not pay or share personal details yet. Check on the official notice board or ask an official at the counter.",
    "gov": "This looks like a government address, still check on the official notice board before you pay or share anything.",
}
WHY = {
    "payment": "it asks for payment", "urgency": "it pushes you to hurry", "vip": "it offers a special pass or a way to skip the queue",
    "short_link": "it uses a shortened link that hides the real site", "lookalike": "the address imitates an official name but is not a government address",
    "nongov_booking": "it is a website that is not a government address and it asks for a booking", "tout": "someone is offering to get you ahead of the queue", "personal": "it asks for personal or payment details", "odd_tld": "the address ending is unusual for an official service",
    "model": "it looks like a known scam pattern",
}


def host_of(text):
    """First address-like thing in the text -> lowercase hostname, or ''."""
    m = URL_RE.search(text or "")
    if not m:
        return ""
    u = m.group(0).rstrip(".,;)")
    if "://" not in u:
        u = "http://" + u
    try:
        h = (urlparse(u).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""
    return h if "." in h else ""


def is_gov(host):
    return bool(host) and host.endswith(".gov.in")


def rules(text):
    """-> (verdict, reason keys, host, gov_flag)"""
    t = text or ""
    host = host_of(t)
    r = []
    gov = is_gov(host)
    if MONEY.search(t):
        r.append("payment")
    if URGENT.search(t):
        r.append("urgency")
    if VIP.search(t):
        r.append("vip")
    if PERSON.search(t):
        r.append("personal")
    if TOUT.search(t):
        r.append("tout")
    if host and not gov:
        if host in SHORTENERS or any(host.endswith("." + s) for s in SHORTENERS):
            r.append("short_link")
        low = host.replace("-", "")
        if any(w in low for w in LOOKALIKE_WORDS) or any(w in low for w in OFFICIAL_LOOK):
            r.append("lookalike")
        if host.rsplit(".", 1)[-1] in {"xyz", "top", "click", "online", "site", "shop", "live", "icu", "buzz", "cc", "tk", "ml", "ga", "cf"}:
            r.append("odd_tld")
    if host and not gov and re.search(r"(book|slot|pass|ticket|darshan|seva|donat|register)", t, re.I):
        r.append("nongov_booking")
    n = len(r)
    if "payment" in r and ({"vip", "urgency", "personal", "tout"} & set(r)) or n >= 3 or ("lookalike" in r and "payment" in r):
        v = "high_risk"
    elif n:
        v = "caution"
    else:
        v = "unknown"
    return v, r, host, gov


CLASSIFY_SYS = ("You help pilgrims avoid scams at crowded shrines. Given a pasted address or a description of what someone offered, "
                'reply ONLY with JSON {"risk":"caution|high_risk|unknown","reason":"short english phrase"}. '
                "Use high_risk when money, a special pass, skipping queues or urgency are involved; caution when a non-government website asks for booking or payment; "
                "unknown otherwise. Never say anything is genuine or safe.")


def chat_classify(text):
    k = sarvam_keys.current()
    r = sarvam_keys.request("POST", "/v1/chat/completions", timeout=12, headers={"Authorization": "Bearer " + k}, json={
        "model": os.environ.get("SARVAM_CHAT_MODEL", "sarvam-105b"), "temperature": 0.1, "max_tokens": 300,
        "messages": [{"role": "system", "content": CLASSIFY_SYS}, {"role": "user", "content": text[:800]}]})
    if r.status_code >= 400:
        raise ReadError(f"chat {r.status_code}", r.status_code)
    txt = re.sub(r"<think>.*?</think>", "", r.json()["choices"][0]["message"]["content"] or "", flags=re.S)
    m = re.search(r"\{.*\}", txt, flags=re.S)
    j = json.loads(m.group(0)) if m else {}
    return (j.get("risk") if j.get("risk") in ("caution", "high_risk") else "unknown")


def english_reply(verdict, reasons, gov):
    if gov and verdict == "unknown":
        return REPLIES["gov"]
    why = "; ".join(WHY[x] for x in reasons[:3])
    if gov:
        return REPLIES["gov"] + " " + (why[:1].upper() + why[1:] + "." if why else "")
    return REPLIES[verdict].format(why=(why[:1].upper() + why[1:]) if why else "")


def check(text, lang):
    """Pure-ish core: returns (dict, latency dict). Raises ReadError on Sarvam failures only for translate."""
    lat = {}
    verdict, reasons, host, gov = rules(text)
    if verdict == "unknown" and not gov and sarvam_keys.available():
        t = time.time()
        try:
            risk = chat_classify(text)
            if risk != "unknown":
                verdict, reasons = risk, ["model"]
        except (httpx.HTTPError, ReadError, ValueError, KeyError, IndexError):
            pass
        lat["classify_ms"] = int((time.time() - t) * 1000)
    en = english_reply(verdict, reasons, gov)
    return verdict, reasons, en, lat


@router.post("/api/site-check")
async def site_check(request: Request):
    t0 = time.time()
    try:
        body = await request.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    text = str(body.get("text") or body.get("url") or "").strip()[:800]
    lang = body.get("lang") if body.get("lang") in LANG_CODES else "en"
    if not text:
        return JSONResponse({"verdict": "unknown", "reply_text": "", "audio_base64": "", "reasons": [], "lang": lang,
                             "notice": "Paste a web address or say what the person offered."}, status_code=400)
    verdict, reasons, en, lat = await run_in_threadpool(check, text, lang)
    reply, audio, notice = en, "", ""
    if sarvam_keys.available():
        try:
            if lang != "en":
                t = time.time()
                reply = await run_in_threadpool(translate, en, lang)
                lat["translate_ms"] = int((time.time() - t) * 1000)
            t = time.time()
            audio = await run_in_threadpool(speak, reply, lang)
            lat["tts_ms"] = int((time.time() - t) * 1000)
        except ReadError as e:
            notice = e.notice + (" Showing the warning in English." if lang != "en" and reply == en else "")
    else:
        notice = "Voice unavailable: Sarvam key is not set. Showing the warning in English."
    lat["total_ms"] = int((time.time() - t0) * 1000)
    return {"verdict": verdict, "reply_text": reply, "audio_base64": audio, "reasons": [WHY[x] for x in reasons],
            "reason_codes": reasons, "lang": lang, "latency": lat, "notice": notice}
