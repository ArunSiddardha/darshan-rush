"""Live conversation mode: POST /api/live/turn and POST /api/live/prompt.

The browser (addons_ui/live.js) detects speech itself and posts one utterance per turn. This module keeps a
small dialogue state per session so a booking takes several natural turns:

  "I want a slot" -> "For when?" -> "tomorrow morning" -> "For how many people?" -> read back -> "yes" -> booked.

Reuses directions.py (keyword intent, understand() with the Sarvam chat fallback, parse_when, say_time, speak,
book_slot, set_age_trait, wait answers) and sarvam.py (stt, tts). Nothing in those files is edited.
Mount:  from addons_live import router as live_router ; app.include_router(live_router)
"""
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

import assistant
import directions
import sarvam

router = APIRouter()
LANGS = directions.LANGS
MAX_AUDIO = 4 * 1024 * 1024
SESSION_TTL = 3600
_pool = ThreadPoolExecutor(max_workers=4)

# ------------------------------------------------------------------ fixed prompts, six languages
P = {
    "en": {
        "greeting": "Namaste. I am listening. You can ask for a slot or the waiting time.",
        "nudge": "I am listening. You can ask for a slot or the waiting time.",
        "ask_when": "For when? Today, or tomorrow morning?",
        "ask_party": "For how many people?",
        "confirm": "{when}, at {gate}{party}. Shall I book it?",
        "cancelled": "Done. Your booking is cancelled.",
        "cancel_none": "You have no booking to cancel.",
        "cancel_pending": "Okay, I will not book it. Tell me when you want a slot.",
        "goodbye": "You are welcome. Take care.",
        "unclear_idle": "Sorry, I missed that. Would you like a slot, or the waiting time?",
        "unclear_when": "Sorry, I missed that. Today, or tomorrow morning?",
        "unclear_party": "Sorry, how many people?",
        "unclear_confirm": "Sorry. Shall I book it? Please say yes or no.",
        "party": ", for {n} people",
        "lang_switch": "Okay, I will speak English.",
        "no_booking_repeat": "I have nothing to repeat yet. You can ask for a slot or the waiting time.",
    },
    "hi": {
        "greeting": "नमस्ते। मैं सुन रहा हूँ। आप स्लॉट या इंतज़ार का समय पूछ सकते हैं।",
        "nudge": "मैं सुन रहा हूँ। आप स्लॉट या इंतज़ार का समय पूछ सकते हैं।",
        "ask_when": "किस समय के लिए? आज, या कल सुबह?",
        "ask_party": "कितने लोगों के लिए?",
        "confirm": "{when}, {gate} पर{party}। क्या मैं बुक कर दूँ?",
        "cancelled": "ठीक है, आपकी बुकिंग रद्द हो गई।",
        "cancel_none": "रद्द करने के लिए कोई बुकिंग नहीं है।",
        "cancel_pending": "ठीक है, मैं बुक नहीं करूँगा। जब स्लॉट चाहिए तब बताइए।",
        "goodbye": "आपका स्वागत है। ध्यान रखिए।",
        "unclear_idle": "माफ़ कीजिए, सुनाई नहीं दिया। स्लॉट चाहिए, या इंतज़ार का समय?",
        "unclear_when": "माफ़ कीजिए। आज, या कल सुबह?",
        "unclear_party": "माफ़ कीजिए, कितने लोग?",
        "unclear_confirm": "माफ़ कीजिए। क्या मैं बुक कर दूँ? हाँ या ना बोलिए।",
        "party": ", {n} लोगों के लिए",
        "lang_switch": "ठीक है, अब हिंदी में बोलूँगा।",
        "no_booking_repeat": "अभी दोहराने के लिए कुछ नहीं है। आप स्लॉट या इंतज़ार का समय पूछ सकते हैं।",
    },
    "ml": {
        "greeting": "നമസ്കാരം. ഞാൻ കേൾക്കുന്നുണ്ട്. സ്ലോട്ടോ കാത്തിരിപ്പ് സമയമോ ചോദിക്കാം.",
        "nudge": "ഞാൻ കേൾക്കുന്നുണ്ട്. സ്ലോട്ടോ കാത്തിരിപ്പ് സമയമോ ചോദിക്കാം.",
        "ask_when": "എപ്പോഴത്തേക്ക്? ഇന്നോ, നാളെ രാവിലെയോ?",
        "ask_party": "എത്ര പേർക്ക്?",
        "confirm": "{when}, {gate}{party}. ബുക്ക് ചെയ്യട്ടേ?",
        "cancelled": "ശരി, നിങ്ങളുടെ ബുക്കിംഗ് റദ്ദാക്കി.",
        "cancel_none": "റദ്ദാക്കാൻ ബുക്കിംഗ് ഒന്നുമില്ല.",
        "cancel_pending": "ശരി, ബുക്ക് ചെയ്യുന്നില്ല. സ്ലോട്ട് വേണമെങ്കിൽ പറയൂ.",
        "goodbye": "സ്വാഗതം. സൂക്ഷിച്ച് പോകൂ.",
        "unclear_idle": "ക്ഷമിക്കണം, കേട്ടില്ല. സ്ലോട്ട് വേണോ, കാത്തിരിപ്പ് സമയം വേണോ?",
        "unclear_when": "ക്ഷമിക്കണം. ഇന്നോ, നാളെ രാവിലെയോ?",
        "unclear_party": "ക്ഷമിക്കണം, എത്ര പേർ?",
        "unclear_confirm": "ക്ഷമിക്കണം. ബുക്ക് ചെയ്യട്ടേ? അതെ അല്ലെങ്കിൽ വേണ്ട എന്ന് പറയൂ.",
        "party": ", {n} പേർക്ക്",
        "lang_switch": "ശരി, ഇനി മലയാളത്തിൽ സംസാരിക്കാം.",
        "no_booking_repeat": "ആവർത്തിക്കാൻ ഇതുവരെ ഒന്നുമില്ല. സ്ലോട്ടോ കാത്തിരിപ്പ് സമയമോ ചോദിക്കാം.",
    },
    "ta": {
        "greeting": "வணக்கம். நான் கேட்டுக்கொண்டிருக்கிறேன். ஸ்லாட் அல்லது காத்திருப்பு நேரம் கேளுங்கள்.",
        "nudge": "நான் கேட்டுக்கொண்டிருக்கிறேன். ஸ்லாட் அல்லது காத்திருப்பு நேரம் கேளுங்கள்.",
        "ask_when": "எப்போதுக்கு? இன்றா, நாளை காலையா?",
        "ask_party": "எத்தனை பேருக்கு?",
        "confirm": "{when}, {gate}{party}. பதிவு செய்யட்டுமா?",
        "cancelled": "சரி, உங்கள் பதிவு ரத்து செய்யப்பட்டது.",
        "cancel_none": "ரத்து செய்ய பதிவு எதுவும் இல்லை.",
        "cancel_pending": "சரி, பதிவு செய்யவில்லை. ஸ்லாட் வேண்டும் என்றால் சொல்லுங்கள்.",
        "goodbye": "வரவேற்கிறேன். பத்திரமாக செல்லுங்கள்.",
        "unclear_idle": "மன்னிக்கவும், கேட்கவில்லை. ஸ்லாட் வேண்டுமா, காத்திருப்பு நேரம் வேண்டுமா?",
        "unclear_when": "மன்னிக்கவும். இன்றா, நாளை காலையா?",
        "unclear_party": "மன்னிக்கவும், எத்தனை பேர்?",
        "unclear_confirm": "மன்னிக்கவும். பதிவு செய்யட்டுமா? ஆம் அல்லது இல்லை என்று சொல்லுங்கள்.",
        "party": ", {n} பேருக்கு",
        "lang_switch": "சரி, இனி தமிழில் பேசுகிறேன்.",
        "no_booking_repeat": "திரும்பச் சொல்ல இன்னும் எதுவும் இல்லை. ஸ்லாட் அல்லது காத்திருப்பு நேரம் கேளுங்கள்.",
    },
    "te": {
        "greeting": "నమస్కారం. నేను వింటున్నాను. స్లాట్ లేదా వేచి ఉండే సమయం అడగండి.",
        "nudge": "నేను వింటున్నాను. స్లాట్ లేదా వేచి ఉండే సమయం అడగండి.",
        "ask_when": "ఎప్పటికి? ఈరోజా, రేపు ఉదయమా?",
        "ask_party": "ఎంత మందికి?",
        "confirm": "{when}, {gate} వద్ద{party}. బుక్ చేయమంటారా?",
        "cancelled": "సరే, మీ బుకింగ్ రద్దు చేశాను.",
        "cancel_none": "రద్దు చేయడానికి బుకింగ్ ఏదీ లేదు.",
        "cancel_pending": "సరే, బుక్ చేయను. స్లాట్ కావాలంటే చెప్పండి.",
        "goodbye": "మీకు స్వాగతం. జాగ్రత్తగా వెళ్ళండి.",
        "unclear_idle": "క్షమించండి, వినిపించలేదు. స్లాట్ కావాలా, వేచి ఉండే సమయం కావాలా?",
        "unclear_when": "క్షమించండి. ఈరోజా, రేపు ఉదయమా?",
        "unclear_party": "క్షమించండి, ఎంత మంది?",
        "unclear_confirm": "క్షమించండి. బుక్ చేయమంటారా? అవును లేదా వద్దు అని చెప్పండి.",
        "party": ", {n} మందికి",
        "lang_switch": "సరే, ఇక తెలుగులో మాట్లాడతాను.",
        "no_booking_repeat": "ఇంకా చెప్పడానికి ఏమీ లేదు. స్లాట్ లేదా వేచి ఉండే సమయం అడగండి.",
    },
    "kn": {
        "greeting": "ನಮಸ್ಕಾರ. ನಾನು ಕೇಳುತ್ತಿದ್ದೇನೆ. ಸ್ಲಾಟ್ ಅಥವಾ ಕಾಯುವ ಸಮಯ ಕೇಳಿ.",
        "nudge": "ನಾನು ಕೇಳುತ್ತಿದ್ದೇನೆ. ಸ್ಲಾಟ್ ಅಥವಾ ಕಾಯುವ ಸಮಯ ಕೇಳಿ.",
        "ask_when": "ಯಾವಾಗಕ್ಕೆ? ಇಂದೋ, ನಾಳೆ ಬೆಳಿಗ್ಗೆಯೋ?",
        "ask_party": "ಎಷ್ಟು ಜನರಿಗೆ?",
        "confirm": "{when}, {gate} ನಲ್ಲಿ{party}. ಬುಕ್ ಮಾಡಲೇ?",
        "cancelled": "ಸರಿ, ನಿಮ್ಮ ಬುಕಿಂಗ್ ರದ್ದಾಗಿದೆ.",
        "cancel_none": "ರದ್ದು ಮಾಡಲು ಬುಕಿಂಗ್ ಇಲ್ಲ.",
        "cancel_pending": "ಸರಿ, ಬುಕ್ ಮಾಡುವುದಿಲ್ಲ. ಸ್ಲಾಟ್ ಬೇಕಾದರೆ ಹೇಳಿ.",
        "goodbye": "ಸ್ವಾಗತ. ಜಾಗ್ರತೆಯಾಗಿ ಹೋಗಿ.",
        "unclear_idle": "ಕ್ಷಮಿಸಿ, ಕೇಳಿಸಲಿಲ್ಲ. ಸ್ಲಾಟ್ ಬೇಕೇ, ಕಾಯುವ ಸಮಯ ಬೇಕೇ?",
        "unclear_when": "ಕ್ಷಮಿಸಿ. ಇಂದೋ, ನಾಳೆ ಬೆಳಿಗ್ಗೆಯೋ?",
        "unclear_party": "ಕ್ಷಮಿಸಿ, ಎಷ್ಟು ಜನ?",
        "unclear_confirm": "ಕ್ಷಮಿಸಿ. ಬುಕ್ ಮಾಡಲೇ? ಹೌದು ಅಥವಾ ಬೇಡ ಎನ್ನಿ.",
        "party": ", {n} ಜನರಿಗೆ",
        "lang_switch": "ಸರಿ, ಇನ್ನು ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡುತ್ತೇನೆ.",
        "no_booking_repeat": "ಪುನಃ ಹೇಳಲು ಇನ್ನೂ ಏನೂ ಇಲ್ಲ. ಸ್ಲಾಟ್ ಅಥವಾ ಕಾಯುವ ಸಮಯ ಕೇಳಿ.",
    },
}


def _p(lang, key, **kw):
    s = P.get(lang, P["en"]).get(key) or P["en"][key]
    return s.format(**kw) if kw else s


# ------------------------------------------------------------------ word lists
def _words(t):
    return re.findall(r"[a-z']+", t)


YES_LAT = {"yes", "yeah", "yep", "yup", "ok", "okay", "sure", "correct", "confirm", "haan", "han", "haa",
           "avunu", "aam", "aama", "amam", "athe", "ade", "sari", "sheri", "seri", "houdu", "hauda", "theek", "thik"}
YES_IND = ["हाँ", "हां", "ठीक", "जी हाँ", "बुक कर", "ശരി", "അതെ", "ആവാം", "ഓക്കെ", "ബുക്ക് ചെയ്", "ஆமா", "ஆம்", "சரி", "ஓகே",
           "అవును", "సరే", "ఓకే", "ಹೌದು", "ಸರಿ", "ಓಕೆ"]
NO_LAT = {"no", "nope", "nah", "nahi", "illa", "illai", "vendam", "venda", "vaddu", "bedaa", "beda", "cancel"}
NO_IND = ["नहीं", "ना ", "नही", "ഇല്ല", "വേണ്ട", "வேண்டாம்", "இல்லை", "వద్దు", "లేదు", "ಬೇಡ", "ಇಲ್ಲ"]
BYE_LAT = ["thank", "thanks", "bye", "goodbye", "that's all", "that is all", "no more", "dhanyavad", "shukriya",
           "nandri", "nandi", "dhanyavadalu", "dhanyavada", "nanni", "that will be all", "i am done", "i'm done"]
BYE_IND = ["धन्यवाद", "शुक्रिया", "बस", "अलविदा", "നന്ദി", "ബൈ", "നിർത്ത", "நன்றி", "போதும்", "ధన్యవాదాలు", "ధన్యవాదములు", "చాలు",
           "ಧನ್ಯವಾದ", "ಸಾಕು", "ಬೈ"]
REPEAT = ["say that again", "say again", "again", "repeat", "once more", "pardon", "what did you say", "come again",
          "फिर से", "दोबारा", "दोहरा", "ഒന്നുകൂടി", "വീണ്ടും", "ആവർത്തി", "மீண்டும்", "திரும்ப", "మళ్ళీ", "మరోసారి", "ಮತ್ತೆ", "ಇನ್ನೊಮ್ಮೆ",
          "marubadi", "marupadi", "thirumba", "veendum", "phir se", "dobara"]
CANCEL = ["cancel", "रद्द", "कैंसल", "റദ്ദ", "ക്യാൻസൽ", "ரத்து", "கேன்சல்", "రద్దు", "క్యాన్సల్", "ರದ್ದು", "ಕ್ಯಾನ್ಸಲ್"]
CHANGE = ["change", "different", "another time", "instead", "reschedule", "modify", "बदल", "दूसरा", "മാറ്റ", "വേറെ", "மாற்ற",
          "வேறு", "మార్చ", "వేరే", "ಬದಲಿ", "ಬೇರೆ"]
TODAY = ["today", "now", "right away", "asap", "earliest", "soonest", "any time", "anytime", "whenever", "next slot",
         "आज", "अभी", "जल्दी", "ഇന്ന്", "ഇപ്പോൾ", "ഏതും", "இன்று", "இப்போது", "ఈరోజు", "ఈ రోజు", "ఇప్పుడు", "ಇಂದು", "ಈಗ", "indru", "inniku", "ippo", "eeroju", "ivattu", "aaj"]
LANG_NAMES = {
    "en": ["english", "इंग्लिश", "अंग्रेजी", "अंग्रेज़ी", "ഇംഗ്ലീഷ്", "ஆங்கிலம்", "இங்கிலீஷ்", "ఇంగ్లీష్", "ಇಂಗ್ಲಿಷ್"],
    "hi": ["hindi", "हिंदी", "हिन्दी", "ഹിന്ദി", "இந்தி", "హిందీ", "ಹಿಂದಿ"],
    "ml": ["malayalam", "മലയാളം", "मलयालम", "மலையாளம்", "మలయాళం", "ಮಲಯಾಳಂ"],
    "ta": ["tamil", "தமிழ்", "तमिल", "തമിഴ്", "తమిళం", "ತಮಿಳು"],
    "te": ["telugu", "తెలుగు", "तेलुगू", "तेलुगु", "തെലുങ്ക്", "தெலுங்கு", "ತೆಲುಗು"],
    "kn": ["kannada", "ಕನ್ನಡ", "कन्नड़", "कन्नड", "കന്നഡ", "கன்னடம்", "కన్నడ"],
}
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                "just me": 1, "alone": 1, "only me": 1, "myself": 1, "couple": 2,
                "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "पांच": 5, "छह": 6,
                "ഒരാൾ": 1, "ഒന്ന്": 1, "രണ്ട്": 2, "രണ്ടു": 2, "മൂന്ന്": 3, "നാല്": 4, "അഞ്ച്": 5,
                "ஒருவர்": 1, "ஒன்று": 1, "இரண்டு": 2, "மூன்று": 3, "நான்கு": 4, "ஐந்து": 5,
                "ఒకరు": 1, "ఒకటి": 1, "ఇద్దర": 2, "రెండు": 2, "ముగ్గుర": 3, "మూడు": 3, "నలుగుర": 4, "నాలుగు": 4, "ఐదు": 5,
                "ಒಬ್ಬ": 1, "ಒಂದು": 1, "ಇಬ್ಬರು": 2, "ಎರಡು": 2, "ಮೂರು": 3, "ನಾಲ್ಕು": 4, "ಐದು": 5}


def _any(low, words):
    return any(w in low for w in words)


def is_yes(low):
    return bool(set(_words(low)) & YES_LAT) or _any(low, YES_IND)


def is_no(low):
    return bool(set(_words(low)) & NO_LAT) or _any(low + " ", NO_IND)


def is_bye(low):
    low = (low or "").strip()
    if "?" in low or re.search(r"\b(next|what|which|where|how|after|before)\b", low) or re.search(r"अगला|अगली|क्या|कहाँ|അടുത്ത|ഏത്|എവിടെ|அடுத்த|எது|எங்கே|తర్వాత|ఏది|ఎక్కడ|ಮುಂದಿನ|ಯಾವುದು|ಎಲ್ಲಿ", low):
        return False            # a question is never goodbye
    try:
        import gatematch
        if gatematch.find_gates(low):
            return False        # a stop name in the sentence means a route question
    except Exception:
        pass
    if re.fullmatch(r"\W*stop\W*", low) or re.search(r"stop (listening|talking)", low):
        return True
    if re.search(r"\b(next|bus|last|which|what|where|how)\b[^.?!]*\bstop\b|\bstop\b\s*(name|number|after|before|is)", low):
        return False            # "next stop", "which stop", "stop after forest path" are questions, not goodbye
    return _any(low, BYE_LAT) or _any(low, BYE_IND)


def lang_in(low):
    for code, names in LANG_NAMES.items():
        if _any(low, names):
            return code
    return None


def party_in(text, info):
    if info.get("party"):
        return info["party"]
    low = text.lower().translate(directions.DIGITS)
    m = re.search(r"\b(\d{1,2})\b", low)
    if m and 1 <= int(m.group(1)) <= 40 and not info.get("age"):
        return int(m.group(1))
    for w, v in sorted(NUMBER_WORDS.items(), key=lambda x: -len(x[0])):
        if w in low:
            return v
    return None


# ------------------------------------------------------------------ audio cache and warming
_audio_cache = {}   # (lang, text) -> (b64, ms)
_cache_lock = threading.Lock()
_warm_done = set()


def tts_cached(text, lang):
    """Returns (b64 or None, ms, notice, hit). Only fixed prompts repeat, so every reply is cached by its text."""
    key = (lang, text)
    with _cache_lock:
        if key in _audio_cache:
            return _audio_cache[key][0], 0, None, True
    # disk: the session volume first, then the copy shipped in the image (app/voice_seed). Credits are limited.
    import base64
    import os
    import volunteer
    path = volunteer._cache_path(text, lang)
    for p in ((path, os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_seed", os.path.basename(path)))
              if os.environ.get("TTS_CACHE", "1") != "0" else ()):
        try:
            with open(p, "rb") as f:
                w = f.read()
            if len(w) > 1000:
                b64 = base64.b64encode(w).decode()
                with _cache_lock:
                    _audio_cache[key] = (b64, 0)
                return b64, 0, None, True
        except OSError:
            pass
    b64, ms, notice = directions.speak(text, lang)
    if b64:
        with _cache_lock:
            if len(_audio_cache) > 400:
                _audio_cache.clear()
            _audio_cache[key] = (b64, ms)
        if os.environ.get("TTS_CACHE", "1") != "0":
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as f:
                    f.write(base64.b64decode(b64))
            except OSError:
                pass
    return b64, ms, notice, False


def warm(lang):
    """Fetch audio for the fixed prompts of one language in the background (once per process per language)."""
    if os.environ.get("LIVE_WARM", "0") != "1" or lang in _warm_done or not sarvam.available():
        return   # off by default: every warmed line costs a Sarvam call
    _warm_done.add(lang)
    for k in ("nudge", "ask_when", "ask_party", "goodbye", "cancelled", "unclear_idle", "unclear_when",
              "unclear_party", "unclear_confirm"):
        _pool.submit(tts_cached, _p(lang, k), lang)


# ------------------------------------------------------------------ session state
_sessions = {}
_slock = threading.Lock()


def session(sid, lang):
    now = time.time()
    with _slock:
        for k in [k for k, v in _sessions.items() if now - v["touched"] > SESSION_TTL]:
            _sessions.pop(k, None)
        s = _sessions.get(sid)
        if not s:
            s = {"state": "idle", "lang": lang, "when_ts": None, "when_label": None, "party": None, "gate": None, "gate_name": None,
                 "last_reply": None, "unclear": 0, "slot": None, "turns": 0, "touched": now}
            _sessions[sid] = s
        s["touched"] = now
        return s


def reset_sessions():
    with _slock:
        _sessions.clear()


# ------------------------------------------------------------------ booking helpers
def _slots():
    return directions._mod("slots")


def _gates():
    return directions.get_gates() or []


def _pick_gate(text, hint):
    g = _gates()
    if not g:
        return None, None
    best = directions.gate_in_text(g, text) or directions.pick_gate(g, hint)
    if not best:
        best = min(g, key=lambda x: x.get("wait_min", 0))
    return best.get("id"), best.get("name")


def _window_for(ts):
    """Start of the window we would use, mirroring slots.book in open mode. None ts means the next window."""
    sl = _slots()
    if not sl:
        return ts
    w, first = sl._window_s(), sl._first_window()
    if ts and ts >= first:
        return (ts // w) * w
    return first


def _readback(s, lang):
    sl = _slots()
    ts = _window_for(s["when_ts"])
    s["when_ts"] = ts
    when = directions.say_time(lang, ts) if ts else ""
    party = _p(lang, "party", n=s["party"]) if s["party"] and s["party"] > 1 else ""
    return _p(lang, "confirm", when=when, gate=s["gate_name"] or "", party=party)


def _do_book(s, uid, lang):
    """Book through slots (via directions.book_slot, which honours the Flagsmith slot_mode). Returns (reply, slot, extra)."""
    sl = _slots()
    if sl and sl.get(uid):
        sl.cancel(uid)          # a changed time replaces the old booking
    res = directions.book_slot(uid, s["gate"], s["when_ts"])
    if res is None:
        return _p(lang, "unclear_idle"), None, {"stub": True}
    sd = res["slot"] if isinstance(res.get("slot"), dict) else {}
    when = directions.say_time(lang, sd["window"]) if sd.get("window") else directions._slot_text(res)
    gname = sd.get("gate_name") or s["gate_name"] or ""
    reply = directions._t(lang, "book_ok").format(when=when, gate=gname)
    slot = {"label": sd.get("label"), "gate": sd.get("gate"), "gate_name": gname, "when": when, "mode": res.get("mode")}
    return reply, slot, {"booking": res}


def _question_for(s, lang):
    return {"ask_when": _p(lang, "ask_when"), "ask_party": _p(lang, "ask_party")}.get(s["state"], "")


def _advance(s, uid, lang):
    """After collecting a field: ask the next missing one, or read the booking back."""
    if not s["when_ts"] and not s.get("when_set"):
        s["state"] = "ask_when"
        return _p(lang, "ask_when")
    if not s["party"] and not s.get("party_skipped"):
        s["state"] = "ask_party"
        return _p(lang, "ask_party")
    s["state"] = "confirm"
    return _readback(s, lang)


# ------------------------------------------------------------------ the dialogue
def handle(text, uid, sid, lang_req, s=None):
    """Pure text turn. Returns (reply_text, extra dict, end_session)."""
    lang = lang_req if lang_req in LANGS else "en"
    s = s or session(sid, lang)
    if s["turns"] and s.get("lang_locked"):
        lang = s["lang"]
    s["lang"] = lang
    s["turns"] += 1
    low = (text or "").lower().translate(directions.DIGITS).strip()
    extra = {"intent": "unknown", "via": "keywords", "llm_ms": 0}
    info = directions.keyword_intent(text)
    if info.get("age"):
        extra["age_set"] = directions.set_age_trait(uid, info["age"])
        extra["age"] = info["age"]
    st = s["state"]

    def say(reply, intent):
        extra["intent"] = intent
        s["unclear"] = 0
        s["last_reply"] = reply
        return reply, extra, False

    # goodbye: not when the word is part of "yes thank you" inside a pending confirmation
    if is_bye(low) and not (st == "confirm" and is_yes(low)):
        s["state"] = "ended"
        extra["intent"] = "goodbye"
        s["last_reply"] = _p(lang, "goodbye")
        return s["last_reply"], extra, True
    # language switch
    nl = lang_in(low)
    if nl and nl != lang and len(low.split()) <= 7 and info["intent"] in ("unknown", "book", "age"):
        s["lang"], s["lang_locked"] = nl, True
        extra["lang_switched"] = nl
        q = _question_for(s, nl) if st in ("ask_when", "ask_party") else (_readback(s, nl) if st == "confirm" else "")
        return say((_p(nl, "lang_switch") + " " + q).strip(), "lang")
    # repeat
    if _any(low, REPEAT) and not is_yes(low):
        return say(s["last_reply"] or _p(lang, "no_booking_repeat"), "repeat")
    # cancel
    if _any(low, CANCEL) and not (st == "confirm" and is_no(low) and "cancel" not in low):
        sl = _slots()
        if st == "confirm" or (st in ("ask_when", "ask_party") and not (sl and sl.get(uid))):
            s.update(state="idle", when_ts=None, party=None, when_set=False, party_skipped=False)
            return say(_p(lang, "cancel_pending"), "cancel")
        if sl and sl.get(uid):
            sl.cancel(uid)
            s.update(state="idle", slot=None, when_ts=None, party=None, when_set=False, party_skipped=False)
            return say(_p(lang, "cancelled"), "cancel")
        return say(_p(lang, "cancel_none"), "cancel")
    # change the time
    if _any(low, CHANGE) and st in ("confirm", "booked", "ask_party"):
        s.update(state="ask_when", when_ts=None, when_set=False)
        return say(_p(lang, "ask_when"), "change")

    # ---- the brain: questions about the route, waits, facilities, help are answered from the live state in every state
    BRAIN_IN_FLOW = ("distress", "position", "facility", "help_elder", "fee", "carry", "about", "wait_best", "distance", "crowd")
    if st in ("confirm", "ask_when", "ask_party"):
        br = assistant.rules(text, lang, uid, s)
        if br and br["intent"] in BRAIN_IN_FLOW:
            if br["action"] == "call_volunteer":
                assistant._raise_flag(uid, text, lang)
            extra["brain"] = br
            q = _readback(s, lang) if st == "confirm" else _question_for(s, lang)
            return say((br["reply"] + " " + q).strip(), br["intent"])
    elif st in ("idle", "booked"):
        br = assistant.answer(text, lang, uid, s, defer_unknown=info["intent"] in ("book", "walkin", "verify", "age"))
        if br and br["action"] not in ("book", "change", "cancel"):
            extra["brain"] = br
            extra["via"], extra["llm_ms"] = br["via"], br.get("llm_ms", 0)
            return say(br["reply"], br["intent"])

    # ---- state specific
    if st == "confirm":
        if is_yes(low) and not is_no(low):
            reply, slot, ex = _do_book(s, uid, lang)
            extra.update(ex)
            s["state"] = "booked" if slot else "idle"
            s["slot"] = slot
            extra["slot"] = slot
            return say(reply, "book")
        if is_no(low):
            s.update(state="ask_when", when_ts=None, when_set=False)
            return say(_p(lang, "ask_when"), "change")
        if info["intent"] in ("wait", "verify", "age") and not is_yes(low):
            reply, ex = directions.respond(text, lang, uid)      # answer the question, then ask for the yes or no again
            extra["llm_ms"] = ex.pop("llm_ms", 0)
            return say((reply + " " + _readback(s, lang)).strip(), ex.get("intent", "wait"))
        w, lbl = directions.parse_when(text)   # a new time instead of yes or no changes the booking being offered
        if w:
            s["when_ts"], s["when_set"] = w, True
            return say(_readback(s, lang), "change")
        j = llm_fill(text, "confirm", extra)
        ans = str((j or {}).get("answer") or "").lower()
        if ans == "yes":
            reply, slot, ex = _do_book(s, uid, lang)
            extra.update(ex)
            s["state"] = "booked" if slot else "idle"
            s["slot"] = slot
            extra["slot"] = slot
            return say(reply, "book")
        if ans == "no":
            s.update(state="ask_when", when_ts=None, when_set=False)
            return say(_p(lang, "ask_when"), "change")
        return _unclear(s, lang, extra)

    if st in ("ask_when", "ask_party"):
        if info["gate_hint"] or directions.gate_in_text(_gates(), text):
            s["gate"], s["gate_name"] = _pick_gate(text, info["gate_hint"])
        if st == "ask_when" or info["intent"] == "book":
            w, lbl = directions.parse_when(text)
            if not w and _any(low, TODAY):
                w, lbl = None, "soonest"
                s["when_set"] = True
            elif w:
                s["when_ts"], s["when_set"] = w, True
            party = party_in(text, info) if (info["party"] or st == "ask_party" or re.search(r"\d|people|persons|members", low)) else None
            if party:
                s["party"] = party
            if s.get("when_set") or party:
                return say(_advance(s, uid, lang), "book")
            if info["intent"] == "wait":
                pass
            elif info["intent"] != "age":
                j = llm_fill(text, st, extra)
                lw = _llm_when(j)
                if lw:
                    if lw != "soonest":
                        s["when_ts"] = lw
                    s["when_set"] = True
                if j and str(j.get("party") or "").isdigit() and 1 <= int(j["party"]) <= 40:
                    s["party"] = int(j["party"])
                if lw or s["party"]:
                    return say(_advance(s, uid, lang), "book")
                return _unclear(s, lang, extra)
        else:   # ask_party
            party = party_in(text, info)
            if party:
                s["party"] = party
                return say(_advance(s, uid, lang), "book")
            if info["intent"] not in ("wait", "age", "verify"):
                j = llm_fill(text, st, extra)
                if j and str(j.get("party") or "").isdigit() and 1 <= int(j["party"]) <= 40:
                    s["party"] = int(j["party"])
                    return say(_advance(s, uid, lang), "book")
                return _unclear(s, lang, extra)
        # wait / age / verify while booking: answer, then repeat the open question
        reply, ex = directions.respond(text, lang, uid)
        extra["llm_ms"] = ex.pop("llm_ms", 0)
        return say((reply + " " + _question_for(s, lang)).strip(), ex.get("intent", "wait"))

    # ---- idle / booked: understand the request
    intent = info["intent"]
    if intent == "unknown" and low:
        i2, via, ms = directions.understand(text)
        extra["via"], extra["llm_ms"] = via, ms
        intent = i2["intent"]
        info = {**info, **{k: v for k, v in i2.items() if v and not info.get(k)}}
        if intent == "age" and i2.get("age"):
            extra["age_set"] = directions.set_age_trait(uid, i2["age"])
    if intent in ("book", "walkin"):
        s.update(when_ts=None, when_set=False, party=info.get("party"), party_skipped=False)
        gid, gname = _pick_gate(text, info["gate_hint"])
        s["gate"], s["gate_name"] = gid, gname
        w, _lbl = directions.parse_when(text)
        if w:
            s["when_ts"], s["when_set"] = w, True
        elif _any(low, TODAY):
            s["when_set"] = True
        return say(_advance(s, uid, lang), "book")
    if intent in ("wait", "verify", "age"):
        reply, ex = directions.respond(text, lang, uid)
        extra["llm_ms"] = extra["llm_ms"] or ex.pop("llm_ms", 0)
        if intent == "age":
            reply = reply + " " + _p(lang, "nudge")
        return say(reply, intent)
    return _unclear(s, lang, extra)


SLOT_SYSTEM = ("A pilgrim answers a temple slot booking assistant in any Indian language or mixed. The assistant just asked: {q}. "
               'Return ONLY JSON: {{"day":"today|tomorrow|null","part":"morning|afternoon|evening|null","party":integer or null,'
               '"answer":"yes|no|null"}}. Use null when the words do not say it.')


def llm_fill(text, state, extra):
    """Second chance when keyword rules found nothing (speech to text often splits or garbles words). Returns a dict or None."""
    if not sarvam.available():
        return None
    q = {"ask_when": "for when (today or tomorrow, morning/afternoon/evening)?", "ask_party": "for how many people?",
         "confirm": "shall I book it? (yes or no)"}.get(state, "what do you want?")
    try:
        j, ms = sarvam.chat_json(SLOT_SYSTEM.format(q=q), text)
    except Exception:
        return None
    extra["llm_ms"] = extra.get("llm_ms", 0) + ms
    extra["via"] = "llm"
    return j


def _llm_when(j):
    """dict from llm_fill -> epoch seconds or 'soonest' or None"""
    if not j:
        return None
    day, part = str(j.get("day") or "").lower(), str(j.get("part") or "").lower()
    if day not in ("today", "tomorrow") and part not in ("morning", "afternoon", "evening"):
        return None
    probe = ("tomorrow " if day == "tomorrow" else "") + (part if part in ("morning", "afternoon", "evening") else "")
    w, _ = directions.parse_when(probe)
    return w or "soonest"


def _unclear(s, lang, extra):
    """A short rephrased question. Never books. Two misses on the people question: assume one person."""
    st = s["state"]
    s["unclear"] += 1
    extra["intent"] = "unclear"
    if st == "ask_party" and s["unclear"] >= 2:
        s["party_skipped"], s["unclear"] = True, 0
        s["state"] = "confirm"
        reply = _readback(s, lang)
    else:
        key = {"ask_when": "unclear_when", "ask_party": "unclear_party", "confirm": "unclear_confirm"}.get(st, "unclear_idle")
        reply = _p(lang, key)
    s["last_reply"] = reply
    return reply, extra, False


# ------------------------------------------------------------------ HTTP
_FILLER = {"uh", "um", "umm", "uhh", "hmm", "hm", "hmmm", "mm", "mmm", "ah", "aah", "ahh", "er", "erm", "eh", "oh", "huh", "ha", "haa", "ho", "uf", "oo", "ooh",
           "आ", "अ", "हम्म", "ऊं", "हूं", "ഉം", "ഹും", "ആ", "ம்", "ஹ்ம்", "ஆ", "ఉమ్", "హ్మ్", "ఆ", "ಉಂ", "ಹ್ಮ್", "ಆ"}
_REAL_SHORT = {"yes", "no", "ok", "hi", "bye", "stop", "help", "haan", "han", "nahi", "illa", "sari", "seri", "aam", "avunu", "ade", "athe", "houdu", "beda", "vendam", "vaddu"}


def _noise(t):
    core = re.sub(r"[\W_]+", "", t or "", flags=re.U)
    if len(core) < 2:
        return True
    words = re.findall(r"\w+", (t or "").lower(), flags=re.U)
    if all(w in _FILLER for w in words):
        return True
    if len(words) == 1 and re.fullmatch(r"[a-z]+", words[0]) and len(words[0]) <= 3 and words[0] not in _REAL_SHORT \
            and not re.search(r"[aeiou]", words[0][:1] + words[0][1:2]) and words[0] not in ("who", "why", "wc", "atm"):
        return True              # a cough transcribed as a letter or two
    return False


@router.post("/api/live/turn")
async def live_turn(audio: UploadFile = File(None), uid: str = Form("anon"), lang: str = Form("en"),
                    session_id: str = Form(""), text: str = Form(""), auto: str = Form("")):
    t0 = time.perf_counter()
    lang = (lang or "en").lower()[:2]
    auto = str(auto).lower() in ("1", "true", "yes") or lang not in LANGS   # detect the language from the speech
    lang = lang if lang in LANGS else "en"
    sid = session_id or uid
    s = session(sid, lang)
    lat = {"stt_ms": 0, "llm_ms": 0, "tts_ms": 0}
    transcript, notice = (text or "").strip(), None
    if audio is not None and not transcript:
        data = await audio.read()
        if len(data) > MAX_AUDIO:
            return JSONResponse({"error": "audio too large", "ignored": True, "state": s["state"]}, status_code=413)
        use = s["lang"] if s.get("lang_locked") else lang
        detect = auto and not s.get("lang_locked")
        if detect and s.get("turns") and s.get("state") in ("confirm", "ask_when", "ask_party") and len(data) < 90000:
            detect = False   # a short answer to our own question ("yes"): keep the language of the conversation, detection mishears one word
        try:
            r = await run_in_threadpool(sarvam.stt, data, audio.filename or "audio.wav", audio.content_type or "audio/wav",
                                        None if detect else (use if use in LANGS else None), "transcribe" if detect else "codemix")
            transcript, lat["stt_ms"] = r.transcript.strip(), r.ms
            if detect and r.language in LANGS:
                # follow the person. A one or two word answer ("yes") is often mis-detected: keep the session language then.
                if s.get("turns") and len(transcript.split()) <= 2 and r.language != s["lang"]:
                    lang = s["lang"]
                else:
                    lang = r.language
        except sarvam.SarvamNoCredits:
            notice = sarvam.NO_CREDITS_MSG
        except sarvam.SarvamError as e:
            notice = f"Voice unavailable ({e}). Type instead."
    base = {"transcript": transcript, "lang": s["lang"] if s.get("lang_locked") else lang, "state": s["state"],
            "end_session": False, "slot": s.get("slot"), "notice": notice}
    if notice:
        lat["total_ms"] = int((time.perf_counter() - t0) * 1000)
        return {**base, "reply_text": notice, "audio_base64": None, "ignored": False, "error": True, "latency": lat}
    if _noise(transcript):
        # nothing intelligible: stay silent (the page does not speak when ignored is true)
        lat["total_ms"] = int((time.perf_counter() - t0) * 1000)
        return {**base, "reply_text": "", "audio_base64": None, "ignored": True, "latency": lat}
    reply, extra, end = await run_in_threadpool(handle, transcript, uid, sid, lang, s)
    lat["llm_ms"] = extra.get("llm_ms", 0)
    out_lang = s["lang"]
    b64, lat["tts_ms"], tnotice, hit = await run_in_threadpool(tts_cached, reply, out_lang)
    lat["tts_cached"] = hit
    lat["total_ms"] = int((time.perf_counter() - t0) * 1000)
    warm_lang = out_lang
    _pool.submit(warm, warm_lang)
    return {**base, "lang": out_lang, "reply_text": reply, "audio_base64": b64, "state": s["state"], "end_session": end,
            "slot": extra.get("slot") or s.get("slot"), "notice": tnotice, "ignored": False, "intent": extra.get("intent"),
            "via": extra.get("via"), "age_set": extra.get("age_set", False), "latency": lat, **assistant.brain_fields(uid, extra)}


@router.post("/api/live/prompt")
async def live_prompt(kind: str = Form("greeting"), lang: str = Form("en"), session_id: str = Form("")):
    """Fixed spoken prompts for the page: greeting (on the first tap), nudge (8 s of silence), goodbye."""
    lang = (lang or "en").lower()[:2]
    lang = lang if lang in LANGS else "en"
    if kind not in ("greeting", "nudge", "goodbye"):
        return JSONResponse({"error": "unknown kind"}, status_code=400)
    if kind == "greeting" and session_id:
        s = session(session_id, lang)
        s.update(state="idle", turns=0, unclear=0, lang=lang, lang_locked=False, when_ts=None, party=None, when_set=False,
                 party_skipped=False)
    text = _p(lang, kind)
    t0 = time.perf_counter()
    b64, ms, notice, hit = await run_in_threadpool(tts_cached, text, lang)
    _pool.submit(warm, lang)
    return {"reply_text": text, "audio_base64": b64, "lang": lang, "notice": notice,
            "latency": {"tts_ms": ms, "tts_cached": hit, "total_ms": int((time.perf_counter() - t0) * 1000)}}
