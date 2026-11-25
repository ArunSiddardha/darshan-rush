"""Find which gate (stop) a pilgrim names, in any of six scripts, romanised or garbled by speech to text.

find_gates(text) -> [(gate_id, score, pos)] in order of mention. Score: 3 full name, 2 key word, 1 weak word.
Indic aliases are matched as stems on the space-free text, so inflections ("...ക്യാമ്പിൽ", "...ల్లో") still match.
Latin words are also matched fuzzily (difflib) because speech engines spell 'crossing' as kraasing, krosing, etc.
"""
import difflib
import re

_ZW = dict.fromkeys([0x200B, 0x200C, 0x200D, 0x00AD, 0x200E, 0x200F], None)

# (alias, score). Latin aliases are lower case; Indic ones are stems.
ALIASES = {
    "g1": [("basecamp", 3), ("बेसकैंप", 3), ("बेसकैम्प", 3), ("ബേസ്ക്യാമ്പ്", 3), ("ബേസ്ക്യാംപ്", 3), ("பேஸ்கேம்ப்", 3),
           ("బేస్క్యాంప్", 3), ("ಬೇಸ್ಕ್ಯಾಂಪ್", 3), ("బేస్‌క్యాంప్", 3),
           ("camp", 2), ("kyamp", 2), ("kaemp", 2), ("kamp", 2), ("कैंप", 2), ("कैम्प", 2), ("ക്യാമ്പ്", 2), ("ക്യാംപ്", 2), ("கேம்ப்", 2),
           ("క్యాంప్", 2), ("ಕ್ಯಾಂಪ್", 2), ("base", 1), ("bais", 1), ("beys", 1), ("बेस", 1), ("ബേസ്", 1), ("பேஸ்", 1), ("బేస్", 1), ("ಬೇಸ್", 1)],
    "g2": [("rivercrossing", 3), ("rivarcrossing", 3), ("रिवरक्रॉसिंग", 3), ("റിവർക്രോസിംഗ്", 3), ("റിവർക്രോസിങ്", 3), ("ரிவர்கிராசிங்", 3),
           ("రివర్క్రాసింగ్", 3), ("ರಿವರ್ಕ್ರಾಸಿಂಗ್", 3),
           ("crossing", 2), ("crosing", 2), ("krosing", 2), ("kraasing", 2), ("krasing", 2), ("crasing", 2), ("kraising", 2), ("kraassing", 2),
           ("क्रॉसिंग", 2), ("क्रासिंग", 2), ("ക്രോസിംഗ്", 2), ("ക്രോസിങ്", 2), ("ക്രോസ്സിംഗ്", 2), ("கிராசிங்", 2), ("க்ராசிங்", 2),
           ("క్రాసింగ్", 2), ("ಕ್ರಾಸಿಂಗ್", 2), ("ಕ್ರಾಸಿಂಗ್", 2), ("river", 2), ("rivar", 2), ("रिवर", 2), ("റിവർ", 2), ("ரிவர்", 2), ("రివర్", 2), ("ರಿವರ್", 2),
           ("nadi", 1), ("nathi", 1), ("puzha", 1), ("नदी", 1), ("പുഴ", 1), ("നദി", 1), ("நதி", 1), ("ஆறு", 1), ("నది", 1), ("ನದಿ", 1)],
    "g3": [("forestpath", 3), ("फॉरेस्टपाथ", 3), ("ഫോറസ്റ്റ്പാത്ത്", 3), ("பாரஸ்ட்பாத்", 3), ("ఫారెస్ట్పాత్", 3), ("ಫಾರೆಸ್ಟ್ಪಾತ್", 3),
           ("forest", 2), ("forrest", 2), ("foresttu", 2), ("farest", 2), ("फॉरेस्ट", 2), ("फारेस्ट", 2), ("ഫോറസ്റ്റ്", 2), ("ഫോറെസ്റ്റ്", 2),
           ("பாரஸ்ட்", 2), ("ஃபாரஸ்ட்", 2), ("ஃபாரெஸ்ட்", 2), ("ఫారెస్ట్", 2), ("ఫారెస్టు", 2), ("ಫಾರೆಸ್ಟ್", 2),
           ("adavi", 2), ("kaadu", 1), ("kaatu", 1), ("vanam", 1), ("जंगल", 1), ("കാട്", 1), ("വനം", 1), ("காடு", 1), ("అడవి", 2), ("ಕಾಡು", 1),
           ("path", 1), ("paath", 1), ("पाथ", 1), ("പാത്ത്", 1), ("பாத்", 1), ("పాత్", 1), ("ಪಾತ್", 1)],
    "g4": [("queuecomplex", 3), ("kyoocomplex", 3), ("cuecomplex", 3), ("qcomplex", 3), ("क्यूकॉम्प्लेक्स", 3), ("ക്യൂകോംപ്ലക്സ്", 3),
           ("க்யூகாம்ப்ளக்ஸ்", 3), ("క్యూకాంప్లెక్స్", 3), ("ಕ್ಯೂಕಾಂಪ್ಲೆಕ್ಸ್", 3),
           ("complex", 2), ("compleks", 2), ("complax", 2), ("kompleks", 2), ("kaamplex", 2), ("कॉम्प्लेक्स", 2), ("कॉम्पलेक्स", 2), ("कांप्लेक्स", 2),
           ("കോംപ്ലക്സ്", 2), ("കോമ്പ്ലക്സ്", 2), ("காம்ப்ளக்ஸ்", 2), ("காம்ப்ளெக்ஸ்", 2), ("కాంప్లెక్స్", 2), ("కాంప్లెక్సు", 2), ("ಕಾಂಪ್ಲೆಕ್ಸ್", 2)],
    "g5": [("mainsteps", 3), ("mainstep", 3), ("mensteps", 3), ("मेनस्टेप", 3), ("मुख्यसीढ़", 3), ("മെയിൻസ്റ്റെപ്", 3), ("மெயின்ஸ்டெப்", 3), ("మెయిన్స్టెప్", 3),
           ("ಮೇನ್ಸ್ಟೆಪ್", 3), ("steps", 2), ("stepsu", 2), ("स्टेप", 2), ("सीढ़ी", 2), ("सीढ़ियां", 2), ("സ്റ്റെപ്", 2), ("ஸ்டெப்", 2), ("స్టెప్", 2),
           ("ಸ್ಟೆಪ್", 2), ("mettu", 2), ("mettlu", 2), ("metlu", 2), ("padikal", 2), ("మెట్ల", 2), ("మెట్టు", 2), ("படிகள்", 2), ("പടികൾ", 2),
           ("ಮೆಟ್ಟಿಲು", 2), ("மெயின்", 1), ("മെയിൻ", 1), ("మెయిన్", 1), ("ಮೇನ್", 1), ("मेन", 1), ("padi", 1), ("പടി", 1), ("படி", 1)],
}
_LATIN = {gid: [(a, s) for a, s in al if re.fullmatch(r"[a-z]+", a)] for gid, al in ALIASES.items()}
_VIRAMA = "\u094d\u0bcd\u0c4d\u0ccd\u0d4d"   # inflected endings (-ിൽ, -లో) replace the final virama, so match the stem without it
_INDIC = {gid: [(a.rstrip(_VIRAMA) if len(a.rstrip(_VIRAMA)) >= 3 else a, s) for a, s in al if not re.fullmatch(r"[a-z]+", a)] for gid, al in ALIASES.items()}

DISPLAY = {  # how each stop is named when spoken, per language
    "g1": {"en": "Base Camp", "hi": "बेस कैंप", "ml": "ബേസ് ക്യാമ്പ്", "ta": "பேஸ் கேம்ப்", "te": "బేస్ క్యాంప్", "kn": "ಬೇಸ್ ಕ್ಯಾಂಪ್"},
    "g2": {"en": "River Crossing", "hi": "रिवर क्रॉसिंग", "ml": "റിവർ ക്രോസിംഗ്", "ta": "ரிவர் கிராசிங்", "te": "రివర్ క్రాసింగ్", "kn": "ರಿವರ್ ಕ್ರಾಸಿಂಗ್"},
    "g3": {"en": "Forest Path", "hi": "फॉरेस्ट पाथ", "ml": "ഫോറസ്റ്റ് പാത്ത്", "ta": "பாரஸ்ட் பாத்", "te": "ఫారెస్ట్ పాత్", "kn": "ಫಾರೆಸ್ಟ್ ಪಾತ್"},
    "g4": {"en": "Queue Complex", "hi": "क्यू कॉम्प्लेक्स", "ml": "ക്യൂ കോംപ്ലക്സ്", "ta": "க்யூ காம்ப்ளக்ஸ்", "te": "క్యూ కాంప్లెక్స్", "kn": "ಕ್ಯೂ ಕಾಂಪ್ಲೆಕ್ಸ್"},
    "g5": {"en": "Main Steps", "hi": "मेन स्टेप्स", "ml": "മെയിൻ സ്റ്റെപ്സ്", "ta": "மெயின் ஸ்டெப்ஸ்", "te": "మెయిన్ స్టెప్స్", "kn": "ಮೇನ್ ಸ್ಟೆಪ್ಸ್"},
}


def display(gid, lang):
    return DISPLAY.get(gid, {}).get(lang) or DISPLAY.get(gid, {}).get("en") or gid


def norm(text):
    return (text or "").lower().translate(_ZW)


def find_gates(text):
    low = norm(text)
    flat = re.sub(r"[\s\-_.,;:!?'\"]+", "", low)
    found = {}   # gid -> (score, pos)

    def put(gid, score, pos):
        old = found.get(gid)
        if not old or score > old[0] or (score == old[0] and pos < old[1]):
            found[gid] = (score, pos)

    for gid in ALIASES:
        for a, s in _INDIC[gid] + _LATIN[gid]:
            i = flat.find(a)
            if i >= 0 and (len(a) >= 4 or not a.isascii() or s >= 2):
                put(gid, s, i)
    # fuzzy: garbled Latin words ('kraasing', 'forrest', 'compleks')
    words = re.findall(r"[a-z]{4,}", low)
    for wi, w in enumerate(words):
        for gid, al in _LATIN.items():
            for a, s in al:
                if len(a) >= 5 and abs(len(a) - len(w)) <= 2 and difflib.SequenceMatcher(None, w, a).ratio() >= 0.82:
                    put(gid, s, low.find(w))
    return sorted(((g, sc, p) for g, (sc, p) in found.items()), key=lambda x: x[2])


def best_gate(text):
    """The gate the pilgrim names: highest score, earliest on a tie. None when no stop is named."""
    f = find_gates(text)
    if not f:
        return None
    return max(f, key=lambda x: (x[1], -x[2]))[0]
