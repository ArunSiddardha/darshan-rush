"""Care requests: a pilgrim says a complaint or a need for help in any of six languages; it becomes a tracked request,
goes to the nearest on-duty volunteer, and the pilgrim is kept informed until it is closed.

Router `router` (mount with app.include_router(addons_care.router)):
  POST /api/care                 audio (multipart: audio, uid, lang, stop, choice) or JSON {text, uid, lang, stop, choice}
  POST /api/care/{id}/stop       {stop}  the pilgrim names the stop afterwards (re-routes)
  GET  /api/care/mine?uid=       the pilgrim's requests with live status text in their language
  GET  /api/care/open            staff: active requests (?volunteer= adds distance from that volunteer)
  GET  /api/care/assigned?volunteer=
  POST /api/care/{id}/ack | /onway | /resolve {volunteer, note} | /cannot {volunteer, reason}
  GET  /api/care/{id}/audio      the pilgrim's own words
  POST /api/care/checkin         {volunteer, stop, languages, on_duty}
  GET  /api/care/stats
Python: from_assistant(text, uid, lang, position), get_policy(), set_policy_source(fn), set_hooks(on_emergency=, on_unacknowledged=),
check_escalations(), start_watcher().

Understanding: keyword rules in six scripts plus romanised forms first (0 ms, no model). The Sarvam chat model is asked only when
the rules find nothing specific, and its JSON is validated. Emergencies never wait for the model. Everything about volunteers is
SIMULATED unless a staff member checked in. The reply never claims that police or an ambulance were called.
"""
import base64
import json
import math
import re
import statistics
import threading
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

import care_store as store
import gatematch
import queue_sim

router = APIRouter()
LANGS = ("en", "hi", "te", "ta", "ml", "kn")
ORDER = [g["id"] for g in queue_sim.GATES]
STOP_NAME = {g["id"]: g["name"] for g in queue_sim.GATES}
WALK = {("g1", "g2"): 6, ("g2", "g3"): 9, ("g3", "g4"): 8, ("g4", "g5"): 12}   # simulated minutes; same as assistant.py
URG_RANK = {"emergency": 0, "urgent": 1, "normal": 2}

# ------------------------------------------------------------------ policy (Flagsmith remote config 'care_policy')
DEFAULT_POLICY = {
    "ack_minutes": {"emergency": 2, "urgent": 5, "normal": 15},
    "language_slack_stops": 1,            # prefer a volunteer who speaks the pilgrim's language if at most this many stops further
    "emergency_language_slack_stops": 0,  # emergencies: pure nearest first
    "max_reroutes": 4,
    "duty_officer_on_emergency": True,
    "use_model": True,
    "model_timeout_s": 8,
}
_policy_source = None


def set_policy_source(fn):
    """fn() returns a dict or a JSON string (e.g. the Flagsmith value of the flag 'care_policy'), or None for the defaults."""
    global _policy_source
    _policy_source = fn


def get_policy():
    p = json.loads(json.dumps(DEFAULT_POLICY))
    if _policy_source is None:
        return p
    try:
        v = _policy_source()
        if isinstance(v, (str, bytes)):
            v = json.loads(v) if v.strip() else None
        if not isinstance(v, dict):
            return p
    except Exception:
        return p
    am = v.get("ack_minutes")
    if isinstance(am, dict):
        for k in URG_RANK:
            x = am.get(k)
            if isinstance(x, (int, float)) and not isinstance(x, bool) and 0 < x <= 240:
                p["ack_minutes"][k] = x
    for k in ("language_slack_stops", "emergency_language_slack_stops", "max_reroutes"):
        x = v.get(k)
        if isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= 10:
            p[k] = x
    for k in ("duty_officer_on_emergency", "use_model"):
        if isinstance(v.get(k), bool):
            p[k] = v[k]
    x = v.get("model_timeout_s")
    if isinstance(x, (int, float)) and not isinstance(x, bool) and 1 <= x <= 8:
        p["model_timeout_s"] = x
    return p


# ------------------------------------------------------------------ escalation hooks (NudgeBee webhook, wired by the integrator)
HOOKS = {"on_emergency": None, "on_unacknowledged": None}


def set_hooks(on_emergency=None, on_unacknowledged=None):
    HOOKS["on_emergency"] = on_emergency
    HOOKS["on_unacknowledged"] = on_unacknowledged


def _fire(name, req):
    fn = HOOKS.get(name)
    if not callable(fn):
        return
    snap = json.loads(json.dumps(req))

    def run():
        try:
            fn(snap)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


# ------------------------------------------------------------------ rules: six languages and romanised forms
def _compile(words):
    """Latin words match at a word start (so 'faint' matches 'fainted'); other scripts match anywhere."""
    lat = [w for w in words if w.isascii()]
    ind = [w for w in words if not w.isascii()]
    rx = re.compile(r"\b(?:" + "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in lat) + ")") if lat else None
    return rx, ind


def _hit(comp, text):
    rx, ind = comp
    return bool((rx and rx.search(text)) or any(w in text for w in ind))


W = {}
W["emerg_med"] = [
    "faint", "unconscious", "collapsed", "collapse", "passed out", "pass out", "not breathing", "cannot breathe", "can't breathe", "cant breathe",
    "breathless", "chest pain", "heart attack", "bleeding", "blood", "seizure", "fits", "not responding", "not waking", "stroke", "fell down and",
    "spruha", "murcha", "moorcha", "mayakam", "kallu tirigi", "kallu tirigi", "chaati noppi", "gunde noppi", "gundenoppi", "ooputiradu", "oopiri",
    "mayakkam", "mayangi", "nenju vali", "moochu", "bodham", "bodhamilla", "nenju vedana", "shwasam", "swasam", "behosh", "chakkar", "seene mein dard",
    "khoon", "saans", "dil ka daura", "tale sutthu", "ede novu", "usiru", "prajne",
    "స్పృహ", "కళ్లు తిరిగ", "కళ్ళు తిరిగ", "ఛాతీ నొప్పి", "గుండె నొప్పి", "రక్తం", "ఊపిరి", "మూర్ఛ",
    "மயக்கம்", "மயங்கி", "நெஞ்சு வலி", "இரத்தம்", "ரத்தம்", "மூச்சு", "வலிப்பு",
    "ബോധം", "ബോധക്ഷയ", "തളർന്നു വീണു", "നെഞ്ചുവേദന", "നെഞ്ച് വേദന", "രക്തം", "ശ്വാസം", "ശ്വാസ", "അപസ്മാര",
    "ಪ್ರಜ್ಞೆ", "ತಲೆ ಸುತ್ತ", "ಎದೆ ನೋವು", "ರಕ್ತ", "ಉಸಿರ", "ಮೂರ್ಛೆ",
    "बेहोश", "चक्कर", "सीने में दर्द", "सीने मे दर्द", "खून", "सांस", "साँस", "दौरा", "दिल का दौरा"]
W["med"] = ["sick", "unwell", "dizzy", "vomit", "fever", "injured", "injury", "hurt", "pain", "fell", "fall", "i am ill", "is ill", "medicine", "doctor", "headache",
            "swollen", "sprain", "twisted", "tired and weak", "weak", "nenu baaledu", "baaledu", "noppi", "jwaram", "vaanthi", "kaichal", "vali", "bukhar", "dard", "ulti", "tabiyat", "tabiyat kharab", "dawakhana", "doctor kavali", "vedana", "novu", "jvara",
            "జ్వరం", "నొప్పి", "వాంతి", "అనారోగ్య", "డాక్టర్", "காய்ச்சல்", "வலி", "வாந்தி", "உடம்பு சரியில்ல", "ഛർദ്ദി", "പനി", "വേദന", "ഡോക്ടർ",
            "ಜ್ವರ", "ನೋವು", "ವಾಂತಿ", "ವೈದ್ಯ", "बुखार", "दर्द", "उल्टी", "बीमार", "डॉक्टर", "चोट"]
W["crush_emerg"] = ["stampede", "crushed", "crushing", "suffocat", "cannot move", "can't move", "cant move", "trapped", "getting crushed", "bhagdad", "thokkisalata",
                    "తొక్కిసలాట", "ఊపిరాడ", "நெரிசலில் சிக்கி", "மூச்சு திணறல்", "തിക്കിലും തിരക്കിലും", "ശ്വാസം മുട്ട", "ನೂಕುನುಗ್ಗಲು", "ಉಸಿರುಗಟ್ಟ", "भगदड़", "दम घुट", "कुचल"]
W["crush"] = ["pushing", "shoving", "too crowded", "too many people", "overcrowd", "no space", "very crowded", "crowd is pushing", "dhakka", "dhakka mukki", "thallu", "thalluthunnaru",
              "nerisal", "thallugirargal", "thallunnu", "thikku", "thirakku", "nooku", "nugguthidaare", "bheed", "धक्का", "भीड़", "తోసుకుం", "తోస్తున్నారు", "తోపులాట", "நெரிசல்", "தள்ளுகிறார்கள்", "തിക്കും", "തിരക്ക്", "തള്ളുന്നു",
              "ನೂಕು", "ತುಂಬ ಜನ"]
W["lost"] = ["lost", "missing", "cannot find", "can't find", "cant find", "not able to find", "got separated", "separated", "went missing", "gone missing", "misplaced",
             "kanipinchatledu", "kanipinchadam ledu", "kanipinchatle", "kanabadatledu", "kanabadadam ledu", "kaanaledu", "kanapadatledu", "dorakatledu", "podigottukunna", "pogottukunna", "tappipoyaru", "tappipoyadu", "tappipoyindi",
             "kaanavillai", "kanavillai", "kaanom", "kanom", "tholainthu", "tholaithu", "kaanunnilla", "kanunnilla", "kaananilla", "nashtappettu", "kaananillaa", "kanpadtilla", "kaanisthilla", "kaanuttilla", "kaanalla", "kaledu", "kalachihogide", "kalediddene",
             "nahi mil raha", "nahin mil raha", "nahi mil rahi", "nahi mila", "gum ho", "gum gaya", "gum gayi", "kho gaya", "kho gayi", "kho diya", "bichad",
             "కనిపించడం లేదు", "కనిపించట్లేదు", "కనబడటం లేదు", "కనబడట్లేదు", "తప్పిపోయ", "పోగొట్టుకున్న", "దొరకడం లేదు",
             "காணவில்லை", "காணோம்", "தொலைந்து", "தொலைத்து", "കാണുന്നില്ല", "കാണാനില്ല", "കാണാതായി", "നഷ്ടപ്പെട്ടു", "നഷ്ടമായി", "കളഞ്ഞു", "വേർപിരിഞ്ഞ",
             "ಕಾಣುತ್ತಿಲ್ಲ", "ಕಾಣಿಸುತ್ತಿಲ್ಲ", "ಕಳೆದುಹೋ", "ಕಳೆದು ಹೋ", "ಕಳೆದುಕೊಂಡ", "खो गया", "खो गयी", "खो गई", "गुम", "नहीं मिल", "बिछड़", "कहीं नहीं दिख"]
W["person"] = ["son", "daughter", "child", "children", "kid", "baby", "boy", "girl", "father", "mother", "dad", "mom", "husband", "wife", "grandfather", "grandmother", "grandma", "grandpa",
               "brother", "sister", "uncle", "aunt", "parents", "friend", "group", "family", "elder", "old man", "old woman", "daddy", "mummy", "papa", "person", "people",
               "abbai", "ammayi", "koduku", "kuthuru", "bidda", "pilla", "pillavadu", "nanna", "amma", "tata", "naanamma", "magan", "magal", "kuzhandhai", "kulanthai", "appa", "paati", "thatha",
               "mon", "mol", "kutti", "kuttiye", "achan", "ammachi", "appooppan", "maga", "magalu", "magu", "tande", "taayi", "thaayi", "beta", "beti", "bacha", "bachcha", "bachche", "pitaji", "pitajee", "dada", "dadi", "nana", "nani",
               "కొడుకు", "కూతురు", "అబ్బాయి", "అమ్మాయి", "బిడ్డ", "పిల్ల", "నాన్న", "అమ్మ", "తాత", "అమ్మమ్మ", "భర్త", "భార్య",
               "மகன்", "மகள்", "குழந்தை", "அப்பா", "அம்மா", "பாட்டி", "தாத்தா", "கணவர்", "மனைவி",
               "മകൻ", "മകൾ", "മകനെ", "മകളെ", "മകന്", "കുട്ടി", "കുട്ടിയെ", "അച്ഛൻ", "അച്ഛനെ", "അമ്മയെ", "അമ്മ", "അപ്പൂപ്പൻ", "അമ്മൂമ്മ", "ഭർത്താവ്", "ഭാര്യ",
               "ಮಗ", "ಮಗಳು", "ಮಗು", "ತಂದೆ", "ತಾಯಿ", "ಅಪ್ಪ", "ಅಮ್ಮ", "ಅಜ್ಜ", "ಅಜ್ಜಿ", "ಗಂಡ", "ಹೆಂಡತಿ",
               "बेटा", "बेटी", "बच्चा", "बच्चे", "बच्ची", "पिता", "पापा", "माँ", "मां", "दादा", "दादी", "पति", "पत्नी", "भाई", "बहन", "परिवार"]
W["child"] = ["son", "daughter", "child", "children", "kid", "baby", "boy", "girl", "abbai", "ammayi", "koduku", "kuthuru", "bidda", "pilla", "pillavadu", "magan", "magal", "kuzhandhai", "kulanthai",
              "mon", "mol", "kutti", "maga", "magalu", "magu", "beta", "beti", "bacha", "bachcha", "bachche",
              "కొడుకు", "కూతురు", "అబ్బాయి", "అమ్మాయి", "బిడ్డ", "పిల్ల", "மகன்", "மகள்", "குழந்தை", "മകൻ", "മകൾ", "മകനെ", "മകളെ", "കുട്ടി", "കുട്ടിയെ", "ಮಗ", "ಮಗಳು", "ಮಗು", "बेटा", "बेटी", "बच्चा", "बच्चे", "बच्ची"]
W["item"] = ["phone", "mobile", "wallet", "purse", "bag", "luggage", "chain", "ring", "ticket", "qr", "spectacles", "glasses", "money", "cash", "watch", "camera", "keys", "key", "slippers", "chappals", "chappal", "shoes", "documents", "aadhaar", "aadhar", "id card",
             "phone", "mobail", "fon", "sanchi", "pursu", "chain", "gadiyaram", "cheppulu", "kannadi", "kaasu", "kasu", "panam", "paisa", "paise", "dabbu", "duddu",
             "ఫోన్", "మొబైల్", "పర్సు", "బ్యాగ్", "సంచి", "చెప్పులు", "డబ్బులు పోగొట్టుకున్న", "போன்", "மொபைல்", "பணப்பை", "பை", "செருப்பு", "ഫോൺ", "മൊബൈൽ", "പേഴ്സ്", "ബാഗ്", "ചെരുപ്പ്", "ಫೋನ್", "ಮೊಬೈಲ್", "ಪರ್ಸ್", "ಬ್ಯಾಗ್", "ಚಪ್ಪಲಿ",
             "फोन", "मोबाइल", "पर्स", "बटुआ", "बैग", "थैला", "चप्पल", "चश्मा", "घड़ी", "सामान"]
W["harass"] = ["harass", "molest", "touched me", "touching me", "touching her", "eve teas", "teasing", "stole", "stolen", "thief", "thieves", "pickpocket", "pick pocket", "snatch", "robbed", "robbery", "theft", "cheated", "attacked", "threaten", "threatening", "following me", "stalk",
               "donga", "dongalu", "dongilinchaadu", "thirudan", "thirudar", "thirudi", "kallan", "kallanmar", "kalla", "kalaru", "chor", "chori", "chedkhani", "chhed", "pareshan",
               "దొంగ", "దొంగిలి", "వేధిస్త", "వేధింపు", "திருடன்", "திருட", "திருடி", "தொல்லை", "കള്ളൻ", "മോഷ്ടി", "മോഷണം", "ശല്യ", "ಕಳ್ಳ", "ಕದ್ದ", "ಕಿರುಕುಳ", "चोर", "चोरी", "छेड़", "छेड़छाड़", "परेशान कर", "लूट"]
W["tout"] = ["rupees", "rupee", "rs.", "rs ", "bribe", "quick darshan", "fast darshan", "vip darshan", "special darshan", "express darshan", "skip the queue", "skip queue", "jump the queue", "line jump",
             "asking money", "asking for money", "demanding money", "ask for money", "extra money", "commission", "tout", "agent is", "broker", "black ticket", "pay to", "payment", "charging", "charge",
             "dabbulu adugutunnaru", "dabbu adugutunnaru", "dabbu adig", "duddu keltaidare", "panam kekkaranga", "panam ketkiraanga", "kaasu kekkaranga", "kaasu kekkiraanga", "kaasu ketkiraanga", "paisa maang", "paise maang", "paise maangte", "paise maang rahe", "rishwat", "lanchm", "lanchan", "lanch",
             "ఈ డబ్బు", "డబ్బులు అడ", "డబ్బు అడ", "లంచం", "ரூபாய்", "பணம் கேட", "காசு கேட", "லஞ்சம்", "ரூபா", "രൂപ", "പണം ചോദ", "കൈക്കൂലി", "ದುಡ್ಡು ಕೇಳ", "ಹಣ ಕೇಳ", "ಲಂಚ", "रुपये", "रुपए", "पैसे मांग", "पैसा मांग", "रिश्वत", "दलाल", "रुपया"]
W["ask"] = ["ask", "demand", "want", "charge", "pay", "give", "quick", "vip", "special", "agent", "adug", "kekk", "ketk", "keltaid", "maang", "మరి", "అడ", "கேட", "ചോദ", "ಕೇಳ", "मांग", "माँग"]
W["access"] = ["wheelchair", "wheel chair", "elderly", "old person", "old woman", "old man", "cannot walk", "can't walk", "cant walk", "unable to walk", "stairs", "steps are too", "disabled", "handicap", "pregnant", "walking stick", "stretcher", "senior citizen", "blind", "cannot climb", "can't climb", "tired old", "carry my",
               "vheelchair", "veelchair", "kursi kavali", "nadavaleru", "nadavaleka", "nadakka mudiyala", "nadakka mudiyathu", "nadakkan vayya", "nadakkan pattilla", "nadeyalu agalla", "chal nahi sakte", "chal nahi sakti", "chal nahin", "bujurg", "vruddha", "vriddha", "periyavar", "vayasayavar", "vayassaya", "hiriya",
               "వీల్‌చైర్", "వీల్ చైర్", "వీల్చైర్", "వృద్ధ", "నడవలేక", "నడవలేరు", "నడవలేను", "சக்கர நாற்காலி", "வீல்சேர்", "வீல் சேர்", "வீல்சேர", "நடக்க முடியவில்லை", "நடக்க முடியாது", "முதியவர்", "വീൽചെയർ", "വീൽ ചെയർ", "നടക്കാൻ വയ്യ", "നടക്കാൻ പറ്റില്ല", "വൃദ്ധ", "പ്രായമായ",
               "ವೀಲ್ಚೇರ್", "ವೀಲ್ ಚೇರ್", "ನಡೆಯಲು ಆಗ", "ನಡೆಯಲಾಗ", "ವೃದ್ಧ", "ಹಿರಿಯ", "व्हीलचेयर", "व्हील चेयर", "व्हीलचेअर", "चल नहीं सक", "चल नही सक", "बुजुर्ग", "बूढ़े", "बुज़ुर्ग", "विकलांग"]
W["clean"] = ["toilet", "toilets", "restroom", "washroom", "latrine", "dirty", "unclean", "filthy", "smell", "stink", "garbage", "litter", "dustbin", "drinking water", "no water", "water is", "water tap", "tap", "drain", "sewage", "hygiene", "clean",
              "neellu", "neeru", "neru", "thanni", "thaneer", "kudineer", "vellam", "vellamilla", "paani", "pani nahi", "ganda", "gandagi", "gandi", "mosam", "ashuddham", "kashmalam", "kalmasham", "mugulu", "shuchi",
              "టాయిలెట్", "మరుగుదొడ్డి", "నీళ్లు", "నీళ్ళు", "నీరు", "మురికి", "చెత్త", "கழிப்பறை", "டாய்லெட்", "தண்ணீர்", "குடிநீர்", "அழுக்கு", "குப்பை", "ടോയ്‌ലറ്റ്", "ടോയ്ലറ്റ്", "ശുചിമുറി", "ശൗചാലയ", "വെള്ളം", "വൃത്തികേട്", "മാലിന്യ",
              "ಶೌಚಾಲಯ", "ಟಾಯ್ಲೆಟ್", "ನೀರು", "ಕೊಳಕು", "ಕಸ", "शौचालय", "टॉयलेट", "पानी", "गंदा", "गंदगी", "कचरा", "बदबू"]
W["slot"] = ["slot", "booking", "booked", "reservation", "token", "time slot", "late for", "slot time", "cancelled", "not confirmed", "qr code", "qr not", "confirmation", "my turn", "not working", "queue number",
             "slotu", "bookingu", "slot kavali", "slot maara", "ticketu", "స్లాట్", "బుకింగ్", "ஸ்லாட்", "முன்பதிவு", "புக்கிங்", "സ്ലോട്ട്", "ബുക്കിംഗ്", "ബുക്കിങ്", "ಸ್ಲಾಟ್", "ಬುಕಿಂಗ್", "स्लॉट", "बुकिंग", "टोकन"]
W["staff"] = ["rude", "misbehav", "shouted at", "shouting at", "scolded", "yelled", "not helping", "ignoring", "ignored me", "abused", "insulted", "arrogant", "volunteer is", "staff is", "behaving badly", "refused to help", "refuse to help", "humiliat",
              "arichadu", "arichaaru", "tittadu", "tittaru", "tittinar", "tittinaar", "kathinar", "dheshyappettu", "dheshyam", "kaduthu", "kooguttaare", "badtameez", "badtamiz", "chilla", "chillaya", "daanta", "dantaa",
              "అరిచ", "తిట్ట", "మర్యాద లేక", "సహాయం చేయ", "திட்டின", "கத்தின", "மரியாதை இல்ல", "உதவ மறு", "ദേഷ്യപ്പെട്ടു", "ശകാരി", "മര്യാദ", "സഹായിക്കുന്നില്ല", "ಕೂಗಾಡ", "ಬೈದ", "ಅಗೌರವ", "ಸಹಾಯ ಮಾಡ", "बदतमीज़", "बदतमीज", "चिल्ला", "डांट", "दुर्व्यवहार", "मदद नहीं"]
W["suggest"] = ["suggest", "suggestion", "should have", "would be better", "please add", "feedback", "recommend", "it would help", "i think you should", "idea", "improve", "sujhav", "sujhaav", "salahe", "salaha", "alochana", "nirdesham", "soochana",
                "సూచన", "సలహా", "ஆலோசனை", "பரிந்துரை", "നിർദ്ദേശം", "നിര്ദ്ദേശം", "ಸಲಹೆ", "ಸೂಚನೆ", "सुझाव", "सलाह"]
# 25 Nov: words found missing when every category was tried in all six languages
W["med"] += ["పడిపోయ", "కింద పడ", "गिर गई", "गिर गया", "गिर गए", "गिर पड़", "விழுந்து", "விழுந்த", "വീണു", "വീണ്", "ಬಿದ್ದರು", "ಬಿದ್ದು", "ಬಿದ್ದ"]
W["lost"] += ["காணாமல்", "காணவில்லை", "காணோம்", "ಕಾಣೆಯಾಗ", "ಕಾಣುತ್ತಿಲ್ಲ", "ಕಾಣೆ"]
W["child"] += ["குழந்தை", "பிள்ளை", "மகன்", "மகள்", "ಮಗು", "ಮಗಳು"]
W["person"] += ["குழந்தை", "பிள்ளை", "மகன்", "மகள்", "ಮಗು", "ಮಗಳು"]
W["tout"] += ["पैसे माँग", "पैसे मांग", "पैसा माँग", "पैसा मांग", "रुपये माँग", "रुपये मांग", "रुपए माँग", "रुपए मांग"]
W["ask"] += ["माँग", "मांग"]
W["crush"] += ["ತಳ್ಳು", "ತಳ್ಳುತ್ತ", "ನೂಕು"]
C = {k: _compile(v) for k, v in W.items()}


def _norm(text):
    return re.sub(r"\s+", " ", gatematch.norm(text)).strip()


def classify_rules(text):
    """-> (category, urgency, reason, confident). Pure rules, no model, no network."""
    t = _norm(text)
    if not t:
        return "other", "normal", "nothing was understood", False
    lost, person, item, child = (_hit(C[k], t) for k in ("lost", "person", "item", "child"))
    if _hit(C["emerg_med"], t):
        who = "a person" if person else "someone"
        return "medical", "emergency", f"{who} may be unconscious, bleeding, in chest pain or unable to breathe", True
    if _hit(C["crush_emerg"], t):
        return "safety_crowd", "emergency", "crowd crush or suffocation risk", True
    if lost:
        if person and not (item and not _hit(C["child"], t) and not re.search(r"\b(father|mother|husband|wife|friend|group|family|parents|grand\w*|dad|mom|papa|brother|sister)\b", t)):
            if child:
                return "lost_person", "emergency", "a lost child is the highest priority", True
            return "lost_person", "urgent", "an adult or elder is separated from the pilgrim", True
        if item:
            return "lost_item", "normal", "a lost belonging", True
        return "lost_person", "urgent", "someone cannot be found (details unclear)", True
    if _hit(C["crush"], t):
        return "safety_crowd", "urgent", "pushing or very dense crowd", True
    if _hit(C["harass"], t):
        return "harassment_theft", "urgent", "harassment or theft reported", True
    if _hit(C["tout"], t) and (_hit(C["ask"], t) or re.search(r"\d{2,}", t)):
        return "tout_payment", "urgent", "someone is asking for money; no payment is ever needed", True
    if _hit(C["access"], t):
        return "accessibility", "urgent", "wheelchair or elder help needed", True
    if _hit(C["med"], t):
        return "medical", "urgent", "someone is unwell or hurt", True
    if _hit(C["staff"], t):
        return "staff_behaviour", "normal", "complaint about staff behaviour", True
    if _hit(C["clean"], t):
        return "water_toilet_clean", "normal", "water, toilet or cleanliness problem", True
    if _hit(C["slot"], t):
        return "slot_booking", "normal", "slot or booking problem", True
    if _hit(C["tout"], t):
        return "tout_payment", "urgent", "a payment is mentioned; no payment is ever needed", True
    if _hit(C["suggest"], t):
        return "suggestion", "normal", "a suggestion", True
    return "other", "normal", "not clear from the words", False


def looks_like_care(text):
    """True when the words are a complaint or request for help (rules only)."""
    cat, _u, _r, conf = classify_rules(text)
    return bool(conf and cat != "suggestion")


# ------------------------------------------------------------------ reply language
LABEL = {
    "en": {"medical": "a medical problem", "lost_person": "a person who is lost", "lost_item": "a lost item", "safety_crowd": "a crowd safety problem",
           "harassment_theft": "harassment or theft", "tout_payment": "someone asking for money", "accessibility": "a need for wheelchair or elder help",
           "water_toilet_clean": "a water, toilet or cleanliness problem", "slot_booking": "a slot or booking problem", "staff_behaviour": "a complaint about staff",
           "suggestion": "your suggestion", "other": "your request"},
    "hi": {"medical": "स्वास्थ्य की समस्या", "lost_person": "एक खोया हुआ व्यक्ति", "lost_item": "खोया हुआ सामान", "safety_crowd": "भीड़ से सुरक्षा की समस्या",
           "harassment_theft": "परेशान करना या चोरी", "tout_payment": "किसी का पैसे मांगना", "accessibility": "व्हीलचेयर या बुज़ुर्ग की मदद",
           "water_toilet_clean": "पानी, शौचालय या सफ़ाई की समस्या", "slot_booking": "स्लॉट या बुकिंग की समस्या", "staff_behaviour": "स्टाफ़ के व्यवहार की शिकायत",
           "suggestion": "आपका सुझाव", "other": "आपका अनुरोध"},
    "te": {"medical": "ఆరోగ్య సమస్య", "lost_person": "తప్పిపోయిన వ్యక్తి", "lost_item": "పోగొట్టుకున్న వస్తువు", "safety_crowd": "రద్దీ వల్ల భద్రత సమస్య",
           "harassment_theft": "వేధింపు లేదా దొంగతనం", "tout_payment": "ఎవరో డబ్బు అడగడం", "accessibility": "వీల్‌చైర్ లేదా పెద్దవారికి సహాయం",
           "water_toilet_clean": "నీరు, టాయిలెట్ లేదా శుభ్రత సమస్య", "slot_booking": "స్లాట్ లేదా బుకింగ్ సమస్య", "staff_behaviour": "సిబ్బంది ప్రవర్తనపై ఫిర్యాదు",
           "suggestion": "మీ సూచన", "other": "మీ అభ్యర్థన"},
    "ta": {"medical": "உடல்நலப் பிரச்சினை", "lost_person": "காணாமல் போன ஒருவர்", "lost_item": "தொலைந்த பொருள்", "safety_crowd": "கூட்ட நெரிசல் பாதுகாப்புப் பிரச்சினை",
           "harassment_theft": "தொந்தரவு அல்லது திருட்டு", "tout_payment": "யாரோ பணம் கேட்பது", "accessibility": "சக்கர நாற்காலி அல்லது முதியவர் உதவி",
           "water_toilet_clean": "தண்ணீர், கழிப்பறை அல்லது தூய்மைப் பிரச்சினை", "slot_booking": "ஸ்லாட் அல்லது முன்பதிவுப் பிரச்சினை", "staff_behaviour": "பணியாளர் நடத்தை பற்றிய புகார்",
           "suggestion": "உங்கள் ஆலோசனை", "other": "உங்கள் கோரிக்கை"},
    "ml": {"medical": "ആരോഗ്യ പ്രശ്നം", "lost_person": "കാണാതായ ഒരാൾ", "lost_item": "നഷ്ടപ്പെട്ട സാധനം", "safety_crowd": "തിരക്ക് മൂലമുള്ള സുരക്ഷാ പ്രശ്നം",
           "harassment_theft": "ശല്യമോ മോഷണമോ", "tout_payment": "ആരോ പണം ചോദിക്കുന്നത്", "accessibility": "വീൽചെയർ അല്ലെങ്കിൽ പ്രായമായവർക്കുള്ള സഹായം",
           "water_toilet_clean": "വെള്ളം, ടോയ്‌ലറ്റ് അല്ലെങ്കിൽ ശുചിത്വ പ്രശ്നം", "slot_booking": "സ്ലോട്ട് അല്ലെങ്കിൽ ബുക്കിംഗ് പ്രശ്നം", "staff_behaviour": "ജീവനക്കാരുടെ പെരുമാറ്റത്തെക്കുറിച്ചുള്ള പരാതി",
           "suggestion": "നിങ്ങളുടെ നിർദ്ദേശം", "other": "നിങ്ങളുടെ അഭ്യർത്ഥന"},
    "kn": {"medical": "ಆರೋಗ್ಯ ಸಮಸ್ಯೆ", "lost_person": "ಕಳೆದುಹೋದ ವ್ಯಕ್ತಿ", "lost_item": "ಕಳೆದುಹೋದ ವಸ್ತು", "safety_crowd": "ಜನಸಂದಣಿಯ ಸುರಕ್ಷತೆಯ ಸಮಸ್ಯೆ",
           "harassment_theft": "ಕಿರುಕುಳ ಅಥವಾ ಕಳ್ಳತನ", "tout_payment": "ಯಾರೋ ಹಣ ಕೇಳುತ್ತಿರುವುದು", "accessibility": "ವೀಲ್‌ಚೇರ್ ಅಥವಾ ಹಿರಿಯರಿಗೆ ಸಹಾಯ",
           "water_toilet_clean": "ನೀರು, ಶೌಚಾಲಯ ಅಥವಾ ಸ್ವಚ್ಛತೆಯ ಸಮಸ್ಯೆ", "slot_booking": "ಸ್ಲಾಟ್ ಅಥವಾ ಬುಕಿಂಗ್ ಸಮಸ್ಯೆ", "staff_behaviour": "ಸಿಬ್ಬಂದಿ ವರ್ತನೆಯ ದೂರು",
           "suggestion": "ನಿಮ್ಮ ಸಲಹೆ", "other": "ನಿಮ್ಮ ವಿನಂತಿ"},
}
# guidance group per category
GROUP = {"medical": "g_med", "lost_person": "g_lostp", "lost_item": "g_item", "safety_crowd": "g_crowd", "harassment_theft": "g_harass", "tout_payment": "g_tout",
         "accessibility": "g_access", "water_toilet_clean": "g_clean", "slot_booking": "g_slot", "staff_behaviour": "g_staff", "suggestion": "g_sugg", "other": "g_other"}
TPL = {
    "en": {"intro": "I understood: {label}. Your request number is {id}.", "coming": "Volunteer {name} from {stop} is coming, about {m} minutes.",
           "none": "No volunteer is free right now. I keep trying, and the duty officer can see your request.", "ask_stop": "Which stop are you at? Please tell me or tap it.",
           "g_med": "Please stay with them. The volunteer will find you.", "g_lostp": "Please stay where you are and keep your phone with you. Do not go looking far.",
           "g_item": "Please check the last place you were. If it is found, it is kept at the lost and found counter.", "g_crowd": "Move to the side or an open space if you safely can, and stay calm.",
           "g_harass": "Please move near other people or the nearest volunteer. Keep your things close.", "g_tout": "There is no payment for darshan or slots. Please do not pay anyone.",
           "g_access": "Please wait where you are, in a shaded place if possible. The volunteer will bring help.", "g_clean": "Thank you for telling us. The team will be informed.",
           "g_slot": "Please keep your booking number with you. The volunteer will check it.", "g_staff": "Thank you for telling us. This will be reviewed.",
           "g_sugg": "Thank you. Your suggestion is noted.", "g_other": "Please stay where you are. The volunteer will ask what you need.",
           "st_open": "Your request {id} is noted. We are finding a volunteer.", "st_assigned": "Volunteer {name} is coming from {stop}, about {m} minutes.",
           "st_onway": "Volunteer {name} is on the way to you, about {m} minutes.", "st_resolved": "Request {id} is closed. {note}",
           "st_cannot": "The volunteer could not resolve request {id}. Please go to the help counter at {info}.", "st_wait": "Your request {id} is noted."},
    "hi": {"intro": "मैं समझ गया: {label}। आपका अनुरोध नंबर {id} है।", "coming": "स्वयंसेवक {name}, {stop} से आ रहे हैं, लगभग {m} मिनट में।",
           "none": "अभी कोई स्वयंसेवक खाली नहीं है। मैं कोशिश करता रहूँगा, और ड्यूटी अधिकारी आपका अनुरोध देख सकते हैं।", "ask_stop": "आप किस पड़ाव पर हैं? कृपया बताइए या चुनिए।",
           "g_med": "कृपया उनके साथ रहिए। स्वयंसेवक आपको ढूँढ लेंगे।", "g_lostp": "कृपया वहीं रुकिए और फ़ोन साथ रखिए। दूर तक ढूँढने मत जाइए।",
           "g_item": "कृपया आख़िरी जगह देख लीजिए। मिलने पर सामान खोया-पाया काउंटर पर रखा जाता है।", "g_crowd": "अगर सुरक्षित हो तो किनारे या खुली जगह पर जाइए, और शांत रहिए।",
           "g_harass": "कृपया दूसरे लोगों या नज़दीकी स्वयंसेवक के पास जाइए। अपना सामान पास रखिए।", "g_tout": "दर्शन या स्लॉट के लिए कोई पैसा नहीं लगता। कृपया किसी को पैसे न दें।",
           "g_access": "कृपया वहीं रुकिए, हो सके तो छाया में। स्वयंसेवक मदद लेकर आएँगे।", "g_clean": "बताने के लिए धन्यवाद। टीम को सूचित किया जाएगा।",
           "g_slot": "कृपया अपना बुकिंग नंबर साथ रखिए। स्वयंसेवक उसे देखेंगे।", "g_staff": "बताने के लिए धन्यवाद। इसकी समीक्षा होगी।",
           "g_sugg": "धन्यवाद। आपका सुझाव दर्ज हो गया।", "g_other": "कृपया वहीं रुकिए। स्वयंसेवक पूछेंगे कि आपको क्या चाहिए।",
           "st_open": "आपका अनुरोध {id} दर्ज है। स्वयंसेवक ढूँढ रहे हैं।", "st_assigned": "स्वयंसेवक {name}, {stop} से आ रहे हैं, लगभग {m} मिनट में।",
           "st_onway": "स्वयंसेवक {name} आपके पास आ रहे हैं, लगभग {m} मिनट में।", "st_resolved": "अनुरोध {id} बंद हो गया। {note}",
           "st_cannot": "स्वयंसेवक अनुरोध {id} हल नहीं कर सके। कृपया {info} के सहायता काउंटर पर जाइए।", "st_wait": "आपका अनुरोध {id} दर्ज है।"},
    "te": {"intro": "నాకు అర్థమైంది: {label}. మీ అభ్యర్థన నంబర్ {id}.", "coming": "వాలంటీర్ {name}, {stop} నుండి వస్తున్నారు, సుమారు {m} నిమిషాల్లో.",
           "none": "ఇప్పుడు ఏ వాలంటీర్ ఖాళీగా లేరు. నేను ప్రయత్నిస్తూనే ఉంటాను, డ్యూటీ అధికారి మీ అభ్యర్థనను చూడగలరు.", "ask_stop": "మీరు ఏ స్టాప్‌లో ఉన్నారు? దయచేసి చెప్పండి లేదా నొక్కండి.",
           "g_med": "దయచేసి వారితోనే ఉండండి. వాలంటీర్ మిమ్మల్ని కనుగొంటారు.", "g_lostp": "దయచేసి ఉన్న చోటే ఉండండి, ఫోన్ మీ దగ్గరే ఉంచండి. దూరం వెతుక్కుంటూ వెళ్లకండి.",
           "g_item": "దయచేసి చివరగా ఉన్న చోట చూడండి. దొరికితే లాస్ట్ అండ్ ఫౌండ్ కౌంటర్‌లో ఉంచుతారు.", "g_crowd": "సురక్షితంగా వీలైతే పక్కకు లేదా ఖాళీ స్థలానికి వెళ్లండి, ప్రశాంతంగా ఉండండి.",
           "g_harass": "దయచేసి ఇతర వ్యక్తుల దగ్గరకు లేదా దగ్గరి వాలంటీర్ దగ్గరకు వెళ్లండి. మీ వస్తువులు దగ్గర ఉంచుకోండి.", "g_tout": "దర్శనానికి లేదా స్లాట్‌కు ఎలాంటి డబ్బు లేదు. దయచేసి ఎవరికీ డబ్బు ఇవ్వకండి.",
           "g_access": "దయచేసి ఉన్న చోటే వేచి ఉండండి, వీలైతే నీడలో. వాలంటీర్ సహాయం తీసుకువస్తారు.", "g_clean": "చెప్పినందుకు ధన్యవాదాలు. బృందానికి తెలియజేస్తాం.",
           "g_slot": "దయచేసి మీ బుకింగ్ నంబర్ దగ్గర ఉంచుకోండి. వాలంటీర్ చూస్తారు.", "g_staff": "చెప్పినందుకు ధన్యవాదాలు. దీనిని పరిశీలిస్తాం.",
           "g_sugg": "ధన్యవాదాలు. మీ సూచన నమోదైంది.", "g_other": "దయచేసి ఉన్న చోటే ఉండండి. మీకు ఏమి కావాలో వాలంటీర్ అడుగుతారు.",
           "st_open": "మీ అభ్యర్థన {id} నమోదైంది. వాలంటీర్‌ను వెతుకుతున్నాం.", "st_assigned": "వాలంటీర్ {name}, {stop} నుండి వస్తున్నారు, సుమారు {m} నిమిషాల్లో.",
           "st_onway": "వాలంటీర్ {name} మీ వైపు వస్తున్నారు, సుమారు {m} నిమిషాల్లో.", "st_resolved": "అభ్యర్థన {id} ముగిసింది. {note}",
           "st_cannot": "వాలంటీర్ అభ్యర్థన {id} పరిష్కరించలేకపోయారు. దయచేసి {info} లోని సహాయ కౌంటర్‌కు వెళ్లండి.", "st_wait": "మీ అభ్యర్థన {id} నమోదైంది."},
    "ta": {"intro": "புரிந்துகொண்டேன்: {label}. உங்கள் கோரிக்கை எண் {id}.", "coming": "தன்னார்வலர் {name}, {stop} இடத்திலிருந்து வருகிறார், சுமார் {m} நிமிடங்களில்.",
           "none": "இப்போது எந்தத் தன்னார்வலரும் இல்லை. தொடர்ந்து முயல்கிறேன், கடமை அதிகாரி உங்கள் கோரிக்கையைப் பார்க்க முடியும்.", "ask_stop": "நீங்கள் எந்த நிறுத்தத்தில் இருக்கிறீர்கள்? சொல்லுங்கள் அல்லது தொடுங்கள்.",
           "g_med": "தயவுசெய்து அவருடனேயே இருங்கள். தன்னார்வலர் உங்களைக் கண்டுபிடிப்பார்.", "g_lostp": "தயவுசெய்து இருக்கும் இடத்திலேயே இருங்கள், போனை கையில் வைத்திருங்கள். தூரம் தேடிச் செல்ல வேண்டாம்.",
           "g_item": "தயவுசெய்து கடைசியாக இருந்த இடத்தைப் பாருங்கள். கிடைத்தால் தொலைந்தவை கவுண்டரில் வைக்கப்படும்.", "g_crowd": "பாதுகாப்பாக முடிந்தால் ஓரமாகவோ திறந்த இடத்திற்கோ செல்லுங்கள், அமைதியாக இருங்கள்.",
           "g_harass": "தயவுசெய்து மற்றவர்கள் அருகில் அல்லது அருகிலுள்ள தன்னார்வலரிடம் செல்லுங்கள். உடைமைகளை அருகில் வைத்திருங்கள்.", "g_tout": "தரிசனத்துக்கோ ஸ்லாட்டுக்கோ பணம் இல்லை. தயவுசெய்து யாருக்கும் பணம் கொடுக்காதீர்கள்.",
           "g_access": "தயவுசெய்து இருக்கும் இடத்திலேயே காத்திருங்கள், முடிந்தால் நிழலில். தன்னார்வலர் உதவியுடன் வருவார்.", "g_clean": "சொன்னதற்கு நன்றி. குழுவுக்குத் தெரிவிக்கப்படும்.",
           "g_slot": "தயவுசெய்து உங்கள் முன்பதிவு எண்ணை வைத்திருங்கள். தன்னார்வலர் பார்ப்பார்.", "g_staff": "சொன்னதற்கு நன்றி. இது பரிசீலிக்கப்படும்.",
           "g_sugg": "நன்றி. உங்கள் ஆலோசனை பதிவாகிவிட்டது.", "g_other": "தயவுசெய்து இருக்கும் இடத்திலேயே இருங்கள். உங்களுக்கு என்ன வேண்டும் என்று தன்னார்வலர் கேட்பார்.",
           "st_open": "உங்கள் கோரிக்கை {id} பதிவாகிவிட்டது. தன்னார்வலரைத் தேடுகிறோம்.", "st_assigned": "தன்னார்வலர் {name}, {stop} இடத்திலிருந்து வருகிறார், சுமார் {m} நிமிடங்களில்.",
           "st_onway": "தன்னார்வலர் {name} உங்களை நோக்கி வருகிறார், சுமார் {m} நிமிடங்களில்.", "st_resolved": "கோரிக்கை {id} முடிந்தது. {note}",
           "st_cannot": "தன்னார்வலரால் கோரிக்கை {id} ஐத் தீர்க்க முடியவில்லை. தயவுசெய்து {info} உதவி கவுண்டருக்குச் செல்லுங்கள்.", "st_wait": "உங்கள் கோரிக்கை {id} பதிவாகிவிட்டது."},
    "ml": {"intro": "മനസ്സിലായി: {label}. നിങ്ങളുടെ അപേക്ഷാ നമ്പർ {id}.", "coming": "വോളന്റിയർ {name}, {stop} എന്ന സ്ഥലത്തുനിന്ന് വരുന്നു, ഏകദേശം {m} മിനിറ്റിൽ.",
           "none": "ഇപ്പോൾ ഒരു വോളന്റിയറും ഒഴിവില്ല. ഞാൻ ശ്രമിച്ചുകൊണ്ടിരിക്കും, ഡ്യൂട്ടി ഓഫീസർക്ക് നിങ്ങളുടെ അപേക്ഷ കാണാം.", "ask_stop": "നിങ്ങൾ ഏത് സ്റ്റോപ്പിലാണ്? ദയവായി പറയൂ അല്ലെങ്കിൽ തൊടൂ.",
           "g_med": "ദയവായി അവരോടൊപ്പം നിൽക്കൂ. വോളന്റിയർ നിങ്ങളെ കണ്ടെത്തും.", "g_lostp": "ദയവായി നിൽക്കുന്നിടത്ത് തന്നെ നിൽക്കൂ, ഫോൺ കൂടെ വയ്ക്കൂ. ദൂരേക്ക് തിരയാൻ പോകരുത്.",
           "g_item": "ദയവായി അവസാനം ഉണ്ടായിരുന്ന സ്ഥലം നോക്കൂ. കിട്ടിയാൽ ലോസ്റ്റ് ആൻഡ് ഫൗണ്ട് കൗണ്ടറിൽ സൂക്ഷിക്കും.", "g_crowd": "സുരക്ഷിതമായി പറ്റുമെങ്കിൽ വശത്തേക്കോ തുറന്ന സ്ഥലത്തേക്കോ മാറൂ, ശാന്തമായിരിക്കൂ.",
           "g_harass": "ദയവായി മറ്റുള്ളവരുടെ അടുത്തേക്കോ അടുത്തുള്ള വോളന്റിയറുടെ അടുത്തേക്കോ പോകൂ. സാധനങ്ങൾ അടുത്ത് വയ്ക്കൂ.", "g_tout": "ദർശനത്തിനോ സ്ലോട്ടിനോ പണം ആവശ്യമില്ല. ദയവായി ആർക്കും പണം നൽകരുത്.",
           "g_access": "ദയവായി നിൽക്കുന്നിടത്ത് കാത്തിരിക്കൂ, പറ്റുമെങ്കിൽ തണലിൽ. വോളന്റിയർ സഹായവുമായി വരും.", "g_clean": "പറഞ്ഞതിന് നന്ദി. ടീമിനെ അറിയിക്കും.",
           "g_slot": "ദയവായി നിങ്ങളുടെ ബുക്കിംഗ് നമ്പർ കൈയിൽ വയ്ക്കൂ. വോളന്റിയർ പരിശോധിക്കും.", "g_staff": "പറഞ്ഞതിന് നന്ദി. ഇത് പരിശോധിക്കും.",
           "g_sugg": "നന്ദി. നിങ്ങളുടെ നിർദ്ദേശം രേഖപ്പെടുത്തി.", "g_other": "ദയവായി നിൽക്കുന്നിടത്ത് തന്നെ നിൽക്കൂ. എന്താണ് വേണ്ടതെന്ന് വോളന്റിയർ ചോദിക്കും.",
           "st_open": "നിങ്ങളുടെ അപേക്ഷ {id} രേഖപ്പെടുത്തി. വോളന്റിയറെ തിരയുന്നു.", "st_assigned": "വോളന്റിയർ {name}, {stop} എന്ന സ്ഥലത്തുനിന്ന് വരുന്നു, ഏകദേശം {m} മിനിറ്റിൽ.",
           "st_onway": "വോളന്റിയർ {name} നിങ്ങളുടെ അടുത്തേക്ക് വരുന്നു, ഏകദേശം {m} മിനിറ്റിൽ.", "st_resolved": "അപേക്ഷ {id} അവസാനിച്ചു. {note}",
           "st_cannot": "അപേക്ഷ {id} പരിഹരിക്കാൻ വോളന്റിയർക്ക് കഴിഞ്ഞില്ല. ദയവായി {info} എന്ന സ്ഥലത്തെ സഹായ കൗണ്ടറിൽ പോകൂ.", "st_wait": "നിങ്ങളുടെ അപേക്ഷ {id} രേഖപ്പെടുത്തി."},
    "kn": {"intro": "ಅರ್ಥವಾಯಿತು: {label}. ನಿಮ್ಮ ವಿನಂತಿ ಸಂಖ್ಯೆ {id}.", "coming": "ಸ್ವಯಂಸೇವಕ {name}, {stop} ನಿಂದ ಬರುತ್ತಿದ್ದಾರೆ, ಸುಮಾರು {m} ನಿಮಿಷಗಳಲ್ಲಿ.",
           "none": "ಈಗ ಯಾವ ಸ್ವಯಂಸೇವಕರೂ ಖಾಲಿ ಇಲ್ಲ. ನಾನು ಪ್ರಯತ್ನಿಸುತ್ತಲೇ ಇರುತ್ತೇನೆ, ಕರ್ತವ್ಯ ಅಧಿಕಾರಿ ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ನೋಡಬಹುದು.", "ask_stop": "ನೀವು ಯಾವ ನಿಲ್ದಾಣದಲ್ಲಿ ಇದ್ದೀರಿ? ದಯವಿಟ್ಟು ಹೇಳಿ ಅಥವಾ ಒತ್ತಿ.",
           "g_med": "ದಯವಿಟ್ಟು ಅವರ ಜೊತೆಗೇ ಇರಿ. ಸ್ವಯಂಸೇವಕರು ನಿಮ್ಮನ್ನು ಹುಡುಕಿ ಬರುತ್ತಾರೆ.", "g_lostp": "ದಯವಿಟ್ಟು ಇದ್ದಲ್ಲೇ ಇರಿ, ಫೋನ್ ಜೊತೆಗೆ ಇಟ್ಟುಕೊಳ್ಳಿ. ದೂರ ಹುಡುಕಲು ಹೋಗಬೇಡಿ.",
           "g_item": "ದಯವಿಟ್ಟು ಕೊನೆಯ ಸ್ಥಳವನ್ನು ನೋಡಿ. ಸಿಕ್ಕರೆ ಕಳೆದುಹೋದ ವಸ್ತುಗಳ ಕೌಂಟರ್‌ನಲ್ಲಿ ಇಡುತ್ತಾರೆ.", "g_crowd": "ಸುರಕ್ಷಿತವಾಗಿ ಸಾಧ್ಯವಾದರೆ ಬದಿಗೆ ಅಥವಾ ಖಾಲಿ ಜಾಗಕ್ಕೆ ಹೋಗಿ, ಶಾಂತವಾಗಿರಿ.",
           "g_harass": "ದಯವಿಟ್ಟು ಇತರರ ಬಳಿ ಅಥವಾ ಹತ್ತಿರದ ಸ್ವಯಂಸೇವಕರ ಬಳಿ ಹೋಗಿ. ನಿಮ್ಮ ವಸ್ತುಗಳನ್ನು ಹತ್ತಿರ ಇಟ್ಟುಕೊಳ್ಳಿ.", "g_tout": "ದರ್ಶನಕ್ಕೆ ಅಥವಾ ಸ್ಲಾಟ್‌ಗೆ ಹಣ ಇಲ್ಲ. ದಯವಿಟ್ಟು ಯಾರಿಗೂ ಹಣ ಕೊಡಬೇಡಿ.",
           "g_access": "ದಯವಿಟ್ಟು ಇದ್ದಲ್ಲೇ ಕಾಯಿರಿ, ಸಾಧ್ಯವಾದರೆ ನೆರಳಿನಲ್ಲಿ. ಸ್ವಯಂಸೇವಕರು ಸಹಾಯ ತರುತ್ತಾರೆ.", "g_clean": "ಹೇಳಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದಗಳು. ತಂಡಕ್ಕೆ ತಿಳಿಸಲಾಗುವುದು.",
           "g_slot": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಬುಕಿಂಗ್ ಸಂಖ್ಯೆ ಜೊತೆಗೆ ಇಟ್ಟುಕೊಳ್ಳಿ. ಸ್ವಯಂಸೇವಕರು ಪರಿಶೀಲಿಸುತ್ತಾರೆ.", "g_staff": "ಹೇಳಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದಗಳು. ಇದನ್ನು ಪರಿಶೀಲಿಸಲಾಗುವುದು.",
           "g_sugg": "ಧನ್ಯವಾದಗಳು. ನಿಮ್ಮ ಸಲಹೆ ದಾಖಲಾಗಿದೆ.", "g_other": "ದಯವಿಟ್ಟು ಇದ್ದಲ್ಲೇ ಇರಿ. ನಿಮಗೆ ಏನು ಬೇಕು ಎಂದು ಸ್ವಯಂಸೇವಕರು ಕೇಳುತ್ತಾರೆ.",
           "st_open": "ನಿಮ್ಮ ವಿನಂತಿ {id} ದಾಖಲಾಗಿದೆ. ಸ್ವಯಂಸೇವಕರನ್ನು ಹುಡುಕುತ್ತಿದ್ದೇವೆ.", "st_assigned": "ಸ್ವಯಂಸೇವಕ {name}, {stop} ನಿಂದ ಬರುತ್ತಿದ್ದಾರೆ, ಸುಮಾರು {m} ನಿಮಿಷಗಳಲ್ಲಿ.",
           "st_onway": "ಸ್ವಯಂಸೇವಕ {name} ನಿಮ್ಮ ಕಡೆ ಬರುತ್ತಿದ್ದಾರೆ, ಸುಮಾರು {m} ನಿಮಿಷಗಳಲ್ಲಿ.", "st_resolved": "ವಿನಂತಿ {id} ಮುಗಿದಿದೆ. {note}",
           "st_cannot": "ಸ್ವಯಂಸೇವಕರಿಗೆ ವಿನಂತಿ {id} ಪರಿಹರಿಸಲಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು {info} ನಲ್ಲಿರುವ ಸಹಾಯ ಕೌಂಟರ್‌ಗೆ ಹೋಗಿ.", "st_wait": "ನಿಮ್ಮ ವಿನಂತಿ {id} ದಾಖಲಾಗಿದೆ."},
}
INFO_STOP = "g1"


def T(lang, key, **kw):
    t = TPL.get(lang) or TPL["en"]
    return (t.get(key) or TPL["en"][key]).format(**kw)


def spoken_id(rid):
    return rid.replace("-", " ")


# ------------------------------------------------------------------ routing
def stop_dist(a, b):
    """Distance in stops along the route (0 = same stop); None when unknown."""
    if a in ORDER and b in ORDER:
        return abs(ORDER.index(a) - ORDER.index(b))
    return None


def walk_min(a, b):
    if a not in ORDER or b not in ORDER:
        return 3
    i, j = sorted((ORDER.index(a), ORDER.index(b)))
    return sum(WALK[(ORDER[k], ORDER[k + 1])] for k in range(i, j))


def pick_volunteer(req, exclude=(), policy=None):
    """Nearest on-duty volunteer: same stop first, then adjacent stops (by route distance); one who speaks the pilgrim's
    language wins when at most `language_slack_stops` further (0 for emergencies). Returns a volunteer dict or None."""
    p = policy or get_policy()
    lang = req.get("language")
    here = req.get("stop_id")
    slack = p["emergency_language_slack_stops"] if req.get("urgency") == "emergency" else p["language_slack_stops"]
    cands = []
    for v in store.volunteers(on_duty_only=True):
        if v["id"] in exclude or v.get("role") == "duty_officer":
            continue
        d = stop_dist(v["stop"], here)
        if d is None:                       # pilgrim stop unknown: language match, then load balance
            d = 0
        load = sum(1 for r in store.all_requests() if r["status"] in store.ACTIVE and r.get("assigned_to") and r["assigned_to"]["id"] == v["id"])
        cands.append((d, load, 0 if lang in v["langs"] else 1, v))
    if not cands:
        return None
    best_d = min(c[0] for c in cands)
    near = [c for c in cands if c[0] <= best_d + (slack if lang else 0)]
    near.sort(key=lambda c: (c[2], c[0], c[1], walk_min(c[3]["stop"], here), c[3]["name"]))
    # same stop beats a language match that is further away only inside the slack
    return near[0][3]


def _assign(req, vol, by="system", note=""):
    with store._lock:
        t = store.NOW()
        d = stop_dist(vol["stop"], req.get("stop_id"))
        req["assigned_to"] = {"id": vol["id"], "name": vol["name"], "stop": vol["stop"], "stop_name": STOP_NAME.get(vol["stop"]),
                              "distance_stops": d, "eta_min": max(2, walk_min(vol["stop"], req.get("stop_id"))), "simulated": bool(vol.get("simulated"))}
        req["tried"] = list(dict.fromkeys(req.get("tried", []) + [vol["id"]]))
        req["status"] = "assigned"
        req["assigned_at"] = t
        req["acknowledged_at"] = None
        store.log(req, "assigned", by, f"{vol['name']} at {STOP_NAME.get(vol['stop'], vol['stop'])}" + (f" ({note})" if note else ""))


def route(req, policy=None, exclude=None):
    """Assign (or re-assign) the request; emergencies also notify the duty officer (once)."""
    p = policy or get_policy()
    with store._lock:
        vol = pick_volunteer(req, exclude=exclude if exclude is not None else (), policy=p)
        if vol:
            _assign(req, vol)
        else:
            req["assigned_to"] = None
            if req["status"] == "assigned":
                req["status"] = "open"
        if req["urgency"] == "emergency" and p["duty_officer_on_emergency"] and not req["duty_officer_notified"]:
            req["duty_officer_notified"] = True
            store.log(req, "duty_officer_notified", "system", "emergency")
            _fire("on_emergency", req)
        store.save()
    return req


def _ack_limit_s(req, p):
    return float(p["ack_minutes"].get(req["urgency"], 15)) * 60.0


def check_escalations(now=None):
    """Re-route requests nobody acknowledged in time (next nearest, marked escalated); also retry unassigned ones.
    Returns the list of request ids that changed."""
    p = get_policy()
    now = now if now is not None else store.NOW()
    changed = []
    with store._lock:
        for r in store.all_requests():
            if r["status"] == "open":
                if r.get("stop_id") or r["urgency"] != "normal" or True:
                    route(r, p)
                    if r["status"] == "assigned":
                        changed.append(r["id"])
            elif r["status"] == "assigned" and r.get("acknowledged_at") is None and r.get("assigned_at"):
                if now - r["assigned_at"] >= _ack_limit_s(r, p):
                    old = r["assigned_to"]
                    r["escalated"] = True
                    store.log(r, "not_acknowledged", "system", f"{old['name'] if old else '?'} did not respond in time")
                    _fire("on_unacknowledged", r)
                    if len(r["tried"]) <= p["max_reroutes"]:
                        vol = pick_volunteer(r, exclude=r["tried"], policy=p)
                        if vol is None:                  # everyone was tried: start over with the closest
                            vol = pick_volunteer(r, exclude=(), policy=p)
                        if vol:
                            _assign(r, vol, note="escalated")
                            r["assigned_at"] = now
                    else:
                        r["assigned_at"] = now           # stop re-routing, keep watching via the duty officer
                    changed.append(r["id"])
        if changed:
            store.save()
    return changed


_watcher = {"t": None, "stop": threading.Event()}


def start_watcher(interval=15.0):
    """Optional background loop that runs check_escalations(). The API also calls it on every request."""
    if _watcher["t"] and _watcher["t"].is_alive():
        return

    def loop():
        while not _watcher["stop"].wait(interval):
            try:
                check_escalations()
            except Exception:
                pass
    _watcher["stop"].clear()
    _watcher["t"] = threading.Thread(target=loop, name="care-watch", daemon=True)
    _watcher["t"].start()


def stop_watcher():
    _watcher["stop"].set()


# ------------------------------------------------------------------ model understanding (validated)
SYS = ("You triage help requests from pilgrims at a crowded shrine. Return ONLY JSON: "
       '{"category":"medical|lost_person|lost_item|safety_crowd|harassment_theft|tout_payment|accessibility|water_toilet_clean|slot_booking|staff_behaviour|suggestion|other",'
       '"urgency":"emergency|urgent|normal","stop_id":"g1..g5 or null","summary_en":"one English sentence","question":"one short question in the pilgrim language only if the place is unknown, else empty"}. '
       'Example: {"category":"lost_item","urgency":"normal","stop_id":null,"summary_en":"Pilgrim lost a phone.","question":"Which stop are you at?"} '
       "Keep the JSON valid, keys exactly as shown. Stops: g1 Base Camp, g2 River Crossing, g3 Forest Path, g4 Queue Complex, g5 Main Steps. Never invent a place.")


def model_understand(text, lang, known_stop, policy):
    """Sarvam chat JSON, validated. Returns dict or None (any failure -> None, rules decide)."""
    if not policy.get("use_model"):
        return None
    try:
        import sarvam
        j, ms = sarvam.chat_json(SYS, f"Pilgrim language: {lang}. Known stop: {known_stop or 'unknown'}.\nPilgrim said: {text[:400]}")
    except Exception:
        return None
    return validate_model(j)


def validate_model(j):
    if not isinstance(j, dict):
        return None
    cat, urg = j.get("category"), j.get("urgency")
    if cat not in store.CATEGORIES or urg not in store.URGENCIES:
        return None
    floor = {"medical": "urgent", "lost_person": "urgent", "safety_crowd": "urgent", "harassment_theft": "urgent", "tout_payment": "urgent", "accessibility": "urgent"}
    if cat in floor and URG_RANK[urg] > URG_RANK[floor[cat]]:
        urg = floor[cat]                                  # never let the model play down a safety category
    sid = j.get("stop_id")
    sid = sid if sid in ORDER else None
    summ = j.get("summary_en")
    summ = re.sub(r"\s+", " ", summ).strip()[:240] if isinstance(summ, str) else ""
    q = j.get("question")
    q = q.strip()[:160] if isinstance(q, str) else ""
    return {"category": cat, "urgency": urg, "stop_id": sid, "summary_en": summ, "question": q}


def _rule_summary(cat, text, lang, stop_name):
    label = LABEL["en"][cat]
    where = f" at {stop_name}" if stop_name else ""
    if lang == "en" and text:
        return f"Pilgrim says: \"{text[:160]}\" ({label}{where})"
    return f"Pilgrim ({lang}) reports {label}{where}. Original words kept."


# ------------------------------------------------------------------ core: understand + open + route + reply
def _public(r, volunteer_stop=None, lang=None):
    now = store.NOW()
    out = {k: r.get(k) for k in ("id", "uid", "language", "transcript", "summary_en", "category", "urgency", "urgency_reason", "stop_id", "stop_name", "status",
                                 "assigned_to", "escalated", "created_at", "acknowledged_at", "resolved_at", "resolution_note", "has_audio", "via", "timeline",
                                 "duty_officer_notified")}
    end = r.get("resolved_at") or now
    out["waiting_s"] = int(max(0, end - r["created_at"]))
    out["audio_url"] = f"/api/care/{r['id']}/audio" if r.get("has_audio") else None
    out["status_text"] = status_text(r, r.get("language"))
    if volunteer_stop:
        d = stop_dist(volunteer_stop, r.get("stop_id"))
        out["distance_stops"] = d
        out["walk_min"] = walk_min(volunteer_stop, r.get("stop_id")) if d is not None else None
    return out


def _stop_label(gid, lang):
    """The stop's name as spoken in the pilgrim's language (falls back to English)."""
    try:
        return gatematch.display(gid, lang) if gid in ORDER else ""
    except Exception:
        return STOP_NAME.get(gid, "")


def status_text(r, lang):
    lang = lang if lang in LANGS else "en"
    a = r.get("assigned_to") or {}
    stop = _stop_label(a.get("stop"), lang) or a.get("stop_name") or ""
    m = a.get("eta_min", 3)
    if r["status"] == "resolved":
        return T(lang, "st_resolved", id=spoken_id(r["id"]), note=r.get("resolution_note") or "").strip()
    if r["status"] == "could_not_resolve":
        return T(lang, "st_cannot", id=spoken_id(r["id"]), info=STOP_NAME[INFO_STOP])
    if r["status"] == "on_the_way" and a:
        return T(lang, "st_onway", name=a["name"], m=m)
    if r["status"] == "assigned" and a:
        return T(lang, "st_assigned", name=a["name"], stop=stop, m=m)
    return T(lang, "st_open", id=spoken_id(r["id"]))


def build_reply(r, asked_stop=False, question=""):
    lang = r["language"] if r["language"] in LANGS else "en"
    parts = [T(lang, "intro", label=LABEL.get(lang, LABEL["en"])[r["category"]], id=spoken_id(r["id"]))]
    a = r.get("assigned_to")
    if a:
        parts.append(T(lang, "coming", name=a["name"], stop=_stop_label(a.get("stop"), lang) or a.get("stop_name") or "", m=a["eta_min"]))
    else:
        parts.append(T(lang, "none"))
    parts.append(T(lang, GROUP[r["category"]]))
    if asked_stop:
        parts.append(question if (question and _script_ok(question, lang)) else T(lang, "ask_stop"))
    return " ".join(parts)


def _script_ok(s, lang):
    """A model-written sentence must be in the pilgrim's script (English for en)."""
    non_latin = sum(1 for ch in s if ord(ch) > 0x2FF)
    letters = sum(1 for ch in s if ch.isalpha()) or 1
    return (non_latin / letters < 0.2) if lang == "en" else (non_latin / letters > 0.5)


CHOICE = {"medical": ("medical", "emergency", "pilgrim pressed the medical help button"),
          "lost_person": ("lost_person", "urgent", "pilgrim pressed the lost person button"),
          "tout_payment": ("tout_payment", "urgent", "pilgrim pressed the someone-is-asking-for-money button"),
          "other": ("other", "normal", "pilgrim pressed the other help button")}
CHOICE_TEXT = {"medical": "I need medical help", "lost_person": "Someone from my group is lost",
               "tout_payment": "Someone is asking me for money", "other": "I need help"}


def open_request(text, uid, lang, stop_id=None, choice=None, position=None, audio=None, audio_type=None, allow_model=True, policy=None):
    """Understand, open, route. Sync. Returns (request, asked_stop, question, notice)."""
    p = policy or get_policy()
    lang = lang if lang in LANGS else "en"
    text = (text or "").strip()
    stop = stop_id if stop_id in ORDER else None
    notice = None
    named = gatematch.best_gate(text) if text else None
    from_pos = position if position in ORDER else None
    if choice in CHOICE:
        cat, urg, why = CHOICE[choice]
        conf = True
        text = text or CHOICE_TEXT[choice]
        via = "button"
    else:
        cat, urg, why, conf = classify_rules(text)
        via = "rules"
    model = None
    if not conf and allow_model and text:     # emergencies are always 'conf' by rules, so they never wait for the model
        model = model_understand(text, lang, stop or named or from_pos, p)
        if model:
            cat, urg, why, via = model["category"], model["urgency"], "model classified", "model"
            if model["stop_id"] and not (stop or named):
                named = model["stop_id"]
        else:
            via = "rules_fallback"
    final_stop = stop or named or from_pos
    asked = final_stop is None
    summ = (model or {}).get("summary_en") or _rule_summary(cat, text, lang, STOP_NAME.get(final_stop))
    # one quick duplicate guard: the same pilgrim, same category, in the last 3 minutes, still open
    for old in reversed(store.all_requests()):
        if old["uid"] == (uid or "anon") and old["category"] == cat and old["status"] in store.ACTIVE and store.NOW() - old["created_at"] < 180:
            store.log(old, "repeated", "pilgrim", text[:120])
            if final_stop and not old.get("stop_id"):
                old["stop_id"], old["stop_name"] = final_stop, STOP_NAME[final_stop]
            store.save()
            return old, False, "", "duplicate"
    r = store.new_request(uid=uid, language=lang, transcript=text, summary_en=summ, category=cat, urgency=urg, urgency_reason=why,
                          stop_id=final_stop, stop_name=STOP_NAME.get(final_stop), via=via)
    if audio:
        store.save_audio(r["id"], audio, audio_type)
    route(r, p)
    return r, asked, (model or {}).get("question", ""), notice


def _payload(r, asked, question, audio_b64=None, notice=None, text_reply=None):
    reply = text_reply or build_reply(r, asked, question)
    a = r.get("assigned_to")
    return {"id": r["id"], "category": r["category"], "urgency": r["urgency"], "urgency_reason": r["urgency_reason"],
            "stop": {"id": r.get("stop_id"), "name": r.get("stop_name")} if r.get("stop_id") else None,
            "assigned_to": ({"name": a["name"], "stop": a["stop_name"], "stop_id": a["stop"], "distance_stops": a["distance_stops"], "eta_min": a["eta_min"],
                             "simulated": a["simulated"]} if a else None),
            "reply_text": reply, "audio_base64": audio_b64, "status": r["status"], "needs_stop": bool(asked), "summary_en": r["summary_en"],
            "transcript": r["transcript"], "lang": r["language"], "via": r["via"], "notice": notice}


def from_assistant(text, uid, lang, position=None):
    """For the pilgrim assistant: call when a normal conversation turn sounds like a complaint or distress.
    Returns the same dict as POST /api/care (without audio), or None when the words are not a care matter."""
    if not looks_like_care(text):
        return None
    r, asked, q, _n = open_request(text, uid, lang, position=position, allow_model=False)
    return _payload(r, asked, q)


def _speak(reply, lang):
    try:
        import sarvam
        res = sarvam.tts(reply, lang)
        return base64.b64encode(res.wav).decode(), None
    except Exception as e:
        msg = e.args[0] if e.__class__.__name__ == "SarvamNoCredits" and e.args else "Voice unavailable. The text above is the same."
        return None, msg


# ------------------------------------------------------------------ API
async def _read(request: Request):
    ct = request.headers.get("content-type", "")
    if "json" in ct:
        j = await request.json()
        return {"text": str(j.get("text") or ""), "uid": str(j.get("uid") or "anon"), "lang": str(j.get("lang") or "en"), "stop": j.get("stop"),
                "choice": j.get("choice"), "position": j.get("position"), "audio": None, "fn": "", "ctype": ""}
    form = await request.form()
    up = form.get("audio")
    data = await up.read() if up is not None and hasattr(up, "read") else None
    return {"text": str(form.get("text") or ""), "uid": str(form.get("uid") or "anon"), "lang": str(form.get("lang") or "en"), "stop": form.get("stop") or None,
            "choice": form.get("choice") or None, "position": form.get("position") or None, "audio": data,
            "fn": getattr(up, "filename", "") or "audio.webm", "ctype": getattr(up, "content_type", "") or "audio/webm"}


@router.post("/api/care")
async def post_care(request: Request):
    from starlette.concurrency import run_in_threadpool
    a = await _read(request)
    lang = a["lang"] if a["lang"] in LANGS else "en"
    text, notice = a["text"].strip(), None
    if not text and a["audio"] and a["choice"] not in CHOICE:
        try:
            import sarvam
            r = await run_in_threadpool(sarvam.stt, a["audio"], a["fn"], a["ctype"], lang if lang != "en" else None)
            text = r.transcript.strip()
        except Exception as e:
            notice = e.args[0] if e.__class__.__name__ == "SarvamNoCredits" and e.args else "Voice unavailable. Please type or use a button."
            return {"id": None, "status": "not_created", "reply_text": notice, "audio_base64": None, "notice": notice, "transcript": ""}
    if not text and a["choice"] not in CHOICE:
        return {"id": None, "status": "not_created", "reply_text": "I did not catch that. Please try again or use a button.", "audio_base64": None,
                "notice": "empty", "transcript": ""}
    await run_in_threadpool(check_escalations)
    pos = a["position"]
    if not pos:
        try:
            import assistant
            pos = assistant.get_position(a["uid"])
        except Exception:
            pos = None
    r, asked, q, n2 = await run_in_threadpool(lambda: open_request(
        text, a["uid"], lang, stop_id=a["stop"], choice=a["choice"], position=pos, audio=a["audio"], audio_type=a["ctype"]))
    reply = build_reply(r, asked, q)
    audio, n3 = await run_in_threadpool(_speak, reply, r["language"] if r["language"] in LANGS else lang)
    return _payload(r, asked, q, audio, "duplicate" if n2 == "duplicate" else (notice or n3), reply)


def _need(rid):
    r = store.get(rid)
    if not r:
        raise HTTPException(404, "no such request")
    return r


@router.post("/api/care/{rid}/stop")
async def post_stop(rid: str, request: Request):
    r = _need(rid)
    j = await request.json()
    s = j.get("stop")
    if s not in ORDER:
        raise HTTPException(400, "unknown stop")
    with store._lock:
        r["stop_id"], r["stop_name"] = s, STOP_NAME[s]
        store.log(r, "stop_set", "pilgrim", STOP_NAME[s])
        if r["status"] in ("open", "assigned") and r.get("acknowledged_at") is None:
            route(r, exclude=())
        store.save()
    return _public(r)


@router.get("/api/care/mine")
def get_mine(uid: str, lang: Optional[str] = None):
    check_escalations()
    rs = [r for r in store.all_requests() if r["uid"] == uid]
    return {"requests": [_public(r, lang=lang) for r in reversed(rs)]}


@router.get("/api/care/open")
def get_open(volunteer: Optional[str] = None, stop: Optional[str] = None, include_closed: bool = False):
    check_escalations()
    v = store.volunteer(volunteer) if volunteer else None
    vstop = stop if stop in ORDER else (v["stop"] if v else None)
    rs = [r for r in store.all_requests() if include_closed or r["status"] in store.ACTIVE]
    out = [_public(r, vstop) for r in rs]
    out.sort(key=lambda x: (URG_RANK[x["urgency"]], x.get("distance_stops") if x.get("distance_stops") is not None else 99, -x["waiting_s"]))
    return {"requests": out, "stats": stats(), "volunteer": v, "volunteer_stop": vstop}


@router.get("/api/care/assigned")
def get_assigned(volunteer: str):
    check_escalations()
    v = store.volunteer(volunteer)
    vid = v["id"] if v else volunteer
    rs = [r for r in store.all_requests() if r["status"] in ("assigned", "on_the_way") and (r.get("assigned_to") or {}).get("id") == vid]
    out = [_public(r, v["stop"] if v else None) for r in rs]
    out.sort(key=lambda x: (URG_RANK[x["urgency"]], -x["waiting_s"]))
    return {"requests": out, "volunteer": v}


async def _body(request):
    try:
        j = await request.json()
        return j if isinstance(j, dict) else {}
    except Exception:
        return {}


def _who(j, r):
    return str(j.get("volunteer") or (r.get("assigned_to") or {}).get("name") or "volunteer")[:40]


@router.post("/api/care/{rid}/ack")
async def post_ack(rid: str, request: Request):
    r, j = _need(rid), await _body(request)
    with store._lock:
        if r["status"] in store.ACTIVE and r.get("acknowledged_at") is None:
            r["acknowledged_at"] = store.NOW()
            store.log(r, "acknowledged", _who(j, r))
            store.save()
    return _public(r)


@router.post("/api/care/{rid}/onway")
async def post_onway(rid: str, request: Request):
    r, j = _need(rid), await _body(request)
    with store._lock:
        if r["status"] not in store.ACTIVE:
            raise HTTPException(409, "request is closed")
        vol = store.volunteer(j.get("volunteer")) if j.get("volunteer") else None
        if vol and (r.get("assigned_to") or {}).get("id") != vol["id"]:      # someone else steps in: they take it
            _assign(r, vol, by=vol["name"], note="took it")
        if r.get("acknowledged_at") is None:
            r["acknowledged_at"] = store.NOW()
            store.log(r, "acknowledged", _who(j, r))
        r["status"] = "on_the_way"
        store.log(r, "on_the_way", _who(j, r))
        store.save()
    return _public(r)


@router.post("/api/care/{rid}/resolve")
async def post_resolve(rid: str, request: Request):
    r, j = _need(rid), await _body(request)
    with store._lock:
        if r["status"] not in store.ACTIVE:
            raise HTTPException(409, "request is closed")
        if r.get("acknowledged_at") is None:
            r["acknowledged_at"] = store.NOW()
        r["status"], r["resolved_at"] = "resolved", store.NOW()
        r["resolution_note"] = str(j.get("note") or "")[:300]
        store.log(r, "resolved", _who(j, r), r["resolution_note"])
        store.save()
    return _public(r)


@router.post("/api/care/{rid}/cannot")
async def post_cannot(rid: str, request: Request):
    """The volunteer cannot help: the request goes to the next nearest. Only when nobody else is left does it close as 'could not resolve'."""
    r, j = _need(rid), await _body(request)
    with store._lock:
        if r["status"] not in store.ACTIVE:
            raise HTTPException(409, "request is closed")
        reason = str(j.get("reason") or "")[:300]
        store.log(r, "cannot", _who(j, r), reason)
        p = get_policy()
        r["escalated"] = True
        vol = pick_volunteer(r, exclude=r["tried"], policy=p) if len(r["tried"]) <= p["max_reroutes"] else None
        if vol:
            _assign(r, vol, note="re-routed: " + (reason or "previous volunteer could not help"))
        else:
            r["status"], r["resolved_at"], r["resolution_note"] = "could_not_resolve", store.NOW(), reason
            r["assigned_to"] = None
            store.log(r, "could_not_resolve", "system", "no other volunteer available")
        store.save()
    return _public(r)


@router.get("/api/care/{rid}/audio")
def get_audio(rid: str):
    r = _need(rid)
    data = store.load_audio(r["id"])
    if not data:
        raise HTTPException(404, "no audio")
    return Response(content=data, media_type=r.get("audio_type") or "audio/webm")


@router.post("/api/care/checkin")
async def post_checkin(request: Request):
    j = await _body(request)
    stop = j.get("stop")
    if stop not in ORDER:
        raise HTTPException(400, "stop must be one of " + ", ".join(ORDER))
    langs = j.get("languages") or j.get("langs") or []
    v = store.checkin(j.get("volunteer") or j.get("name"), stop, langs if isinstance(langs, list) else [langs], j.get("on_duty", True))
    check_escalations()
    return {"volunteer": v, "roster": store.volunteers()}


@router.get("/api/care/roster")
def get_roster():
    return {"volunteers": store.volunteers(), "note": "Volunteers with simulated=true are SIMULATED demo staff."}


def _median(xs):
    return round(statistics.median(xs), 1) if xs else None


def stats():
    rs = store.all_requests()
    by_cat, by_urg, by_stop, by_status = {}, {}, {}, {}
    for r in rs:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
        by_urg[r["urgency"]] = by_urg.get(r["urgency"], 0) + 1
        k = r.get("stop_name") or "unknown"
        by_stop[k] = by_stop.get(k, 0) + 1
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    ack = [r["acknowledged_at"] - r["created_at"] for r in rs if r.get("acknowledged_at")]
    res = [r["resolved_at"] - r["created_at"] for r in rs if r["status"] == "resolved" and r.get("resolved_at")]
    return {"total": len(rs), "open": sum(1 for r in rs if r["status"] in store.ACTIVE),
            "open_emergencies": sum(1 for r in rs if r["urgency"] == "emergency" and r["status"] in store.ACTIVE),
            "by_category": by_cat, "by_urgency": by_urg, "by_stop": by_stop, "by_status": by_status,
            "median_ack_s": _median(ack), "median_resolve_s": _median(res), "escalated": sum(1 for r in rs if r.get("escalated")),
            "volunteers_on_duty": len(store.volunteers(True)), "simulated_roster": any(v.get("simulated") for v in store.volunteers(True))}


@router.get("/api/care/stats")
def get_stats():
    check_escalations()
    return stats()
