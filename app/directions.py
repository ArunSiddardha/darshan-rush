"""Pilgrim voice/text assistant: POST /api/directions.

Understands: book a slot, wait time at a gate, "I am with my mother, she is 70" (age trait),
a walk-in booking spoken by a volunteer, and "is this booking site real" (touts / fake sites).
Lane B modules (slots, queue_sim, flags) are imported lazily; if missing we answer with a clear stub.
Keyword intent works in all six languages without any LLM.
"""
import base64
import re
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import sarvam

router = APIRouter()
LANGS = ("ml", "ta", "te", "kn", "hi", "en")
DIGITS = str.maketrans("०१२३४५६७८९೦೧೨೩೪೫೬೭೮೯൦൧൨൩൪൫൬൭൮൯౦౧౨౩౪౫౬౭౮౯௦௧௨௩௪௫௬௭௮௯", "0123456789" * 5)

# ---------------------------------------------------------------- keywords
KW = {
    "verify": ["real", "fake", "genuine", "tout", "scam", "official", "legit", "website", "site", "http", "www.", ".com",
               "असली", "नकली", "फर्जी", "धोखा", "वेबसाइट", "साइट", "दलाल",
               "ശരിയായ", "വ്യാജ", "തട്ടിപ്പ്", "വെബ്സൈറ്റ്", "സൈറ്റ്", "ഇടനിലക്കാർ",
               "உண்மை", "போலி", "மோசடி", "இணையதளம்", "தளம்", "தரகர்",
               "నిజమైన", "నకిలీ", "మోసం", "వెబ్‌సైట్", "వెబ్సైట్", "సైట్", "దళారి",
               "ನಿಜವಾದ", "ನಕಲಿ", "ಮೋಸ", "ವೆಬ್‌ಸೈಟ್", "ವೆಬ್ಸೈಟ್", "ಸೈಟ್", "ದಲ್ಲಾಳಿ"],
    "walkin": ["walk-in", "walk in", "walkin", "no phone", "without phone", "without a phone", "doesn't have a phone",
               "does not have a phone", "for the pilgrim", "वॉक-इन", "वॉक इन", "फोन नहीं", "बिना फोन",
               "വാക്ക് ഇൻ", "വാക്ക്-ഇൻ", "ഫോൺ ഇല്ല", "ഫോണില്ല",
               "வாக் இன்", "போன் இல்லை", "தொலைபேசி இல்லை",
               "వాక్ ఇన్", "ఫోన్ లేదు", "ఫోన్ లేని",
               "ವಾಕ್ ಇನ್", "ಫೋನ್ ಇಲ್ಲ", "ಫೋನ್ ಇಲ್ಲದ"],
    "wait": ["wait", "how long", "queue", "crowd", "line", "rush", "busy", "इंतज़ार", "इंतजार", "कितना समय", "कितनी देर",
             "भीड़", "लाइन", "कतार", "എത്ര സമയം", "കാത്തിരിപ്പ്", "കാത്തിരി", "തിരക്ക്", "ക്യൂ", "എത്ര നേരം",
             "எவ்வளவு நேரம்", "காத்திருப்பு", "காத்திரு", "கூட்டம்", "வரிசை", "ఎంత సమయం", "వేచి", "రద్దీ", "క్యూ",
             "ఎంత సేపు", "ಎಷ್ಟು ಸಮಯ", "ಕಾಯ", "ಜನಸಂದಣಿ", "ಸರತಿ", "ಎಷ್ಟು ಹೊತ್ತು"],
    "book": ["book", "slot", "ticket", "reserve", "darshan", "बुक", "स्लॉट", "दर्शन", "आरक्षण", "ബുക്ക്", "സ്ലോട്ട്",
             "ദർശനം", "ടിക്കറ്റ്", "பதிவு", "புக்", "ஸ்லாட்", "தரிசனம்", "டிக்கெட்", "బుక్", "స్లాట్", "దర్శనం",
             "టికెట్", "ಬುಕ್", "ಸ್ಲಾಟ್", "ದರ್ಶನ", "ಟಿಕೆಟ್"],
}
RELATIVES = ["mother", "father", "mom", "dad", "grandmother", "grandfather", "grandma", "grandpa", "parent", "elder",
             "old", "aged", "माँ", "मां", "माता", "पिता", "पिताजी", "दादी", "दादा", "बुजुर्ग",
             "അമ്മ", "അച്ഛൻ", "അച്ഛന്", "അമ്മൂമ്മ", "മുത്തശ്ശി", "അപ്പൂപ്പൻ", "അമ്മയ",
             "அம்மா", "அப்பா", "பாட்டி", "தாத்தா", "అమ్మ", "నాన్న", "అమ్మమ్మ", "తాత", "ಅಮ್ಮ", "ಅಪ್ಪ", "ಅಜ್ಜಿ", "ತಾತ", "ಅಜ್ಜ"]
AGE_MARK = ["years", "year old", "age", "aged", "उम्र", "साल", "वर्ष", "வயசு", "வயது", "వయసు", "వయస్సు", "വയസ്സ്", "വയസ്", "വയസ്സായി", "ವಯಸ್ಸು"]
AGE_WORDS = [  # longest first
    ("अस्सी", 80), ("पचहत्तर", 75), ("बहत्तर", 72), ("सत्तर", 70), ("पैंसठ", 65), ("साठ", 60),
    ("எழுபத்தைந்து", 75), ("எழுபது", 70), ("அறுபத்தைந்து", 65), ("அறுபது", 60), ("எண்பது", 80),
    ("డెబ్బై ఐదు", 75), ("డెబ్భై ఐదు", 75), ("డెబ్భై", 70), ("డెబ్బై", 70), ("అరవై ఐదు", 65), ("అరవై", 60), ("ఎనభై", 80),
    ("എഴുപത്തഞ്ച്", 75), ("എഴുപത്", 70), ("അറുപത്തഞ്ച്", 65), ("അറുപത്", 60), ("എൺപത്", 80),
    ("ಎಪ್ಪತ್ತೈದು", 75), ("ಎಪ್ಪತ್ತು", 70), ("ಅರವತ್ತೈದು", 65), ("ಅರವತ್ತು", 60), ("ಎಂಭತ್ತು", 80),
    ("eighty", 80), ("seventy five", 75), ("seventy-five", 75), ("seventy", 70), ("sixty five", 65), ("sixty-five", 65), ("sixty", 60)]
TOMORROW = ["tomorrow", "kal ", "naalai", "naale", "nale ", "repu", "naaley", "कल", "നാളെ", "நாளை", "రేపు", "ನಾಳೆ"]
PARTS = {"morning": ["morning", "subah", "subha", "kaalai", "kalai", "raavile", "ravile", "udayam", "beligge", "सुबह", "രാവിലെ", "காலை", "கலை", "ఉదయం", "ಬೆಳಿಗ್ಗೆ"],
         "afternoon": ["afternoon", "dopahar", "mathiyam", "uchcha", "madhyahna", "दोपहर", "ഉച്ച", "மதியம்", "మధ్యాహ్నం", "ಮಧ್ಯಾಹ್ನ"],
         "evening": ["evening", "shaam", "maalai", "vaikunneram", "saayantram", "sanje", "शाम", "വൈകുന്നേരം", "മാലൈ", "மாலை", "సాయంత్రం", "ಸಂಜೆ"]}
GATE_ALIASES = {"forest": ["forest", "path", "जंगल", "കാട്", "காடு", "అడవి", "ಕಾಡು"],
                "base": ["base", "camp", "बेस", "ബേസ്", "பேஸ்", "బేస్", "ಬೇಸ್"],
                "queue": ["queue complex", "complex", "कॉम्प्लेक्स", "കോംപ്ലക്സ്", "காம்ப்ளக்ஸ்"],
                "river": ["river", "crossing", "नदी", "പുഴ", "ആറ്", "നദി", "ஆறு", "நதி", "నది", "ನದಿ"],
                "main": ["main", "मुख्य", "പ്രധാന", "முதன்மை", "ప్రధాన", "ಮುಖ್ಯ"],
                "hill": ["hill", "steps", "climb", "पहाड़", "सीढ़", "മല", "படி", "మెట్లు", "ಮೆಟ್ಟಿಲು"]}

# ---------------------------------------------------------------- replies (six languages)
T = {
    "en": {
        "book_ok": "Your slot is booked for {when} at {gate}. Please come fifteen minutes early.",
        "book_walkin": "Walk-in booked for {party} at {gate}, {when}. Please tell the pilgrim this time.",
        "wait": "The wait at {gate} is about {min} minutes. This is simulated.",
        "wait_all": "Waits now: {list}. This is simulated.",
        "age": "Noted. We will keep your route short and give you voice help. Take your time.",
        "verify": ("I cannot confirm any website is real. Book only on the official temple board website, and never pay a "
                   "person at the gate for a slot: slots are not sold by touts. Fake booking sites copy the real look, so "
                   "type the address yourself and check it ends in .gov.in."),
        "verify_bad": ("Careful: this address does not end in .gov.in, so treat it as possibly fake. Do not pay or enter "
                       "your ID there. Use only the official temple board site, and never pay touts."),
        "unknown": "Sorry, I did not catch that. You can say: book a slot, how long is the wait, or is this booking site real.",
        "stub_slots": "Slot booking is not connected yet (stub). Please try again shortly.",
        "stub_queue": "Queue times are not connected yet (stub). Please try again shortly.",
    },
    "hi": {
        "book_ok": "आपका स्लॉट बुक हो गया है, {when}, {gate} पर। कृपया पंद्रह मिनट पहले आइए।",
        "book_walkin": "{party} लोगों के लिए वॉक-इन बुक हो गया, {when}, {gate} पर। यह समय श्रद्धालु को बता दीजिए।",
        "wait": "{gate} पर इंतज़ार लगभग {min} मिनट है (सिमुलेटेड)।",
        "wait_all": "अभी इंतज़ार: {list} (सिमुलेटेड)।",
        "age": "ठीक है। हम आपका रास्ता छोटा रखेंगे और आवाज़ से मदद देंगे। आराम से चलिए।",
        "verify": ("मैं किसी वेबसाइट के असली होने की पुष्टि नहीं कर सकता। बुकिंग सिर्फ़ मंदिर बोर्ड की आधिकारिक वेबसाइट पर "
                   "करें, और गेट पर किसी को स्लॉट के पैसे न दें: दलाल स्लॉट नहीं बेचते। नकली साइटें असली जैसी दिखती हैं, "
                   "इसलिए पता खुद टाइप करें और देखें कि वह .gov.in पर ख़त्म हो।"),
        "verify_bad": ("सावधान: यह पता .gov.in पर ख़त्म नहीं होता, इसलिए इसे नकली मानें। वहाँ पैसे या पहचान पत्र न दें। "
                       "सिर्फ़ आधिकारिक बोर्ड की साइट इस्तेमाल करें, दलालों को पैसे न दें।"),
        "unknown": "माफ़ कीजिए, समझ नहीं आया। आप कह सकते हैं: स्लॉट बुक करो, इंतज़ार कितना है, या यह बुकिंग साइट असली है?",
        "stub_slots": "स्लॉट बुकिंग अभी जुड़ी नहीं है (स्टब)। कृपया थोड़ी देर बाद कोशिश करें।",
        "stub_queue": "कतार का समय अभी जुड़ा नहीं है (स्टब)। कृपया थोड़ी देर बाद कोशिश करें।",
    },
    "ml": {
        "book_ok": "നിങ്ങളുടെ സ്ലോട്ട് ബുക്ക് ചെയ്തു, {when}, {gate} ഗേറ്റിൽ. പതിനഞ്ച് മിനിറ്റ് മുൻപ് എത്തണം.",
        "book_walkin": "{party} പേർക്ക് വാക്ക്-ഇൻ ബുക്ക് ചെയ്തു, {when}, {gate}. ഈ സമയം തീർത്ഥാടകനോട് പറയണം.",
        "wait": "{gate} ൽ ഏകദേശം {min} മിനിറ്റ് കാത്തിരിക്കണം (സിമുലേറ്റഡ്).",
        "wait_all": "ഇപ്പോഴത്തെ കാത്തിരിപ്പ്: {list} (സിമുലേറ്റഡ്).",
        "age": "ശരി. ഞങ്ങൾ നിങ്ങളുടെ വഴി ചെറുതാക്കും, ശബ്ദത്തിൽ സഹായിക്കും. സാവധാനം പോകൂ.",
        "verify": ("ഒരു വെബ്സൈറ്റും ശരിയാണെന്ന് എനിക്ക് ഉറപ്പിക്കാനാവില്ല. ക്ഷേത്ര ബോർഡിന്റെ ഔദ്യോഗിക വെബ്സൈറ്റിൽ മാത്രം ബുക്ക് "
                   "ചെയ്യുക, ഗേറ്റിൽ ആർക്കും സ്ലോട്ടിനായി പണം നൽകരുത്: ഇടനിലക്കാർ സ്ലോട്ട് വിൽക്കുന്നില്ല. വ്യാജ സൈറ്റുകൾ "
                   "യഥാർത്ഥ സൈറ്റ് പോലെ തോന്നും, അതിനാൽ വിലാസം സ്വയം ടൈപ്പ് ചെയ്ത് .gov.in ൽ അവസാനിക്കുന്നെന്ന് നോക്കുക."),
        "verify_bad": ("ശ്രദ്ധിക്കുക: ഈ വിലാസം .gov.in ൽ അവസാനിക്കുന്നില്ല, അതിനാൽ വ്യാജമാകാം. അവിടെ പണമോ തിരിച്ചറിയൽ കാർഡോ "
                       "നൽകരുത്. ഔദ്യോഗിക ബോർഡ് സൈറ്റ് മാത്രം ഉപയോഗിക്കുക."),
        "unknown": "ക്ഷമിക്കണം, മനസ്സിലായില്ല. പറയാം: സ്ലോട്ട് ബുക്ക് ചെയ്യൂ, എത്ര സമയം കാത്തിരിക്കണം, ഈ ബുക്കിംഗ് സൈറ്റ് ശരിയാണോ.",
        "stub_slots": "സ്ലോട്ട് ബുക്കിംഗ് ഇതുവരെ ബന്ധിപ്പിച്ചിട്ടില്ല (സ്റ്റബ്). അല്പം കഴിഞ്ഞ് ശ്രമിക്കൂ.",
        "stub_queue": "ക്യൂ സമയം ഇതുവരെ ബന്ധിപ്പിച്ചിട്ടില്ല (സ്റ്റബ്). അല്പം കഴിഞ്ഞ് ശ്രമിക്കൂ.",
    },
    "ta": {
        "book_ok": "உங்கள் ஸ்லாட் பதிவாகிவிட்டது, {when}, {gate}. பதினைந்து நிமிடம் முன்பே வாருங்கள்.",
        "book_walkin": "{party} பேருக்கு வாக்-இன் பதிவாகிவிட்டது, {when}, {gate}. இந்த நேரத்தை பக்தரிடம் சொல்லுங்கள்.",
        "wait": "{gate} இல் காத்திருப்பு சுமார் {min} நிமிடம் (சிமுலேட்டட்).",
        "wait_all": "இப்போதைய காத்திருப்பு: {list} (சிமுலேட்டட்).",
        "age": "சரி. உங்கள் வழியை குறுகியதாக வைத்து குரல் உதவி தருவோம். மெதுவாக செல்லுங்கள்.",
        "verify": ("எந்த இணையதளமும் உண்மையானது என்று என்னால் உறுதி செய்ய முடியாது. கோயில் வாரியத்தின் அதிகாரப்பூர்வ "
                   "இணையதளத்தில் மட்டும் பதிவு செய்யுங்கள்; வாசலில் யாருக்கும் ஸ்லாட்டுக்கு பணம் தராதீர்கள்: தரகர்கள் "
                   "ஸ்லாட் விற்பதில்லை. போலி தளங்கள் உண்மையானது போலவே இருக்கும்; முகவரியை நீங்களே தட்டச்சு செய்து "
                   ".gov.in இல் முடிகிறதா என்று பாருங்கள்."),
        "verify_bad": ("கவனம்: இந்த முகவரி .gov.in இல் முடியவில்லை, எனவே போலியாக இருக்கலாம். அங்கே பணமோ அடையாள அட்டையோ "
                       "தராதீர்கள். அதிகாரப்பூர்வ வாரிய தளத்தை மட்டும் பயன்படுத்துங்கள்."),
        "unknown": "மன்னிக்கவும், புரியவில்லை. சொல்லலாம்: ஸ்லாட் பதிவு செய், எவ்வளவு நேரம் காத்திருக்க வேண்டும், இந்த தளம் உண்மையா.",
        "stub_slots": "ஸ்லாட் பதிவு இன்னும் இணைக்கப்படவில்லை (ஸ்டப்). சிறிது நேரம் கழித்து முயலுங்கள்.",
        "stub_queue": "வரிசை நேரம் இன்னும் இணைக்கப்படவில்லை (ஸ்டப்). சிறிது நேரம் கழித்து முயலுங்கள்.",
    },
    "te": {
        "book_ok": "మీ స్లాట్ బుక్ అయింది, {when}, {gate} వద్ద. పదిహేను నిమిషాల ముందు రండి.",
        "book_walkin": "{party} మందికి వాక్-ఇన్ బుక్ అయింది, {when}, {gate}. ఈ సమయం భక్తునికి చెప్పండి.",
        "wait": "{gate} వద్ద వేచి ఉండే సమయం సుమారు {min} నిమిషాలు (సిమ్యులేటెడ్).",
        "wait_all": "ఇప్పటి వేచి ఉండే సమయం: {list} (సిమ్యులేటెడ్).",
        "age": "సరే. మీ దారిని చిన్నగా ఉంచి, వాయిస్ సహాయం ఇస్తాం. నెమ్మదిగా వెళ్ళండి.",
        "verify": ("ఏ వెబ్‌సైట్ నిజమైనదో నేను నిర్ధారించలేను. ఆలయ బోర్డు అధికారిక వెబ్‌సైట్‌లోనే బుక్ చేయండి; గేట్ వద్ద "
                   "ఎవరికీ స్లాట్ కోసం డబ్బు ఇవ్వకండి: దళారులు స్లాట్లు అమ్మరు. నకిలీ సైట్లు నిజమైనవాటిలా కనిపిస్తాయి, "
                   "కాబట్టి చిరునామాను మీరే టైప్ చేసి .gov.in తో ముగుస్తుందో చూడండి."),
        "verify_bad": ("జాగ్రత్త: ఈ చిరునామా .gov.in తో ముగియదు, కాబట్టి నకిలీ కావచ్చు. అక్కడ డబ్బు లేదా ఐడి ఇవ్వకండి. "
                       "అధికారిక బోర్డు సైట్ మాత్రమే వాడండి."),
        "unknown": "క్షమించండి, అర్థం కాలేదు. చెప్పవచ్చు: స్లాట్ బుక్ చేయి, ఎంత సేపు వేచి ఉండాలి, ఈ సైట్ నిజమేనా.",
        "stub_slots": "స్లాట్ బుకింగ్ ఇంకా కనెక్ట్ కాలేదు (స్టబ్). కొంచెం సేపటి తర్వాత ప్రయత్నించండి.",
        "stub_queue": "క్యూ సమయం ఇంకా కనెక్ట్ కాలేదు (స్టబ్). కొంచెం సేపటి తర్వాత ప్రయత్నించండి.",
    },
    "kn": {
        "book_ok": "ನಿಮ್ಮ ಸ್ಲಾಟ್ ಬುಕ್ ಆಗಿದೆ, {when}, {gate} ನಲ್ಲಿ. ಹದಿನೈದು ನಿಮಿಷ ಮುಂಚೆ ಬನ್ನಿ.",
        "book_walkin": "{party} ಜನರಿಗೆ ವಾಕ್-ಇನ್ ಬುಕ್ ಆಗಿದೆ, {when}, {gate}. ಈ ಸಮಯವನ್ನು ಭಕ್ತರಿಗೆ ತಿಳಿಸಿ.",
        "wait": "{gate} ನಲ್ಲಿ ಕಾಯುವ ಸಮಯ ಸುಮಾರು {min} ನಿಮಿಷ (ಸಿಮ್ಯುಲೇಟೆಡ್).",
        "wait_all": "ಈಗಿನ ಕಾಯುವ ಸಮಯ: {list} (ಸಿಮ್ಯುಲೇಟೆಡ್).",
        "age": "ಸರಿ. ನಿಮ್ಮ ದಾರಿಯನ್ನು ಚಿಕ್ಕದಾಗಿಡುತ್ತೇವೆ ಮತ್ತು ಧ್ವನಿ ಸಹಾಯ ನೀಡುತ್ತೇವೆ. ನಿಧಾನವಾಗಿ ಹೋಗಿ.",
        "verify": ("ಯಾವ ವೆಬ್‌ಸೈಟ್ ನಿಜವೆಂದು ನಾನು ಖಚಿತಪಡಿಸಲಾರೆ. ದೇವಾಲಯ ಮಂಡಳಿಯ ಅಧಿಕೃತ ವೆಬ್‌ಸೈಟ್‌ನಲ್ಲೇ ಬುಕ್ ಮಾಡಿ; "
                   "ಗೇಟ್‌ನಲ್ಲಿ ಯಾರಿಗೂ ಸ್ಲಾಟ್‌ಗಾಗಿ ಹಣ ಕೊಡಬೇಡಿ: ದಲ್ಲಾಳಿಗಳು ಸ್ಲಾಟ್ ಮಾರುವುದಿಲ್ಲ. ನಕಲಿ ಸೈಟ್‌ಗಳು ನಿಜವಾದವುಗಳಂತೆ "
                   "ಕಾಣುತ್ತವೆ, ಆದ್ದರಿಂದ ವಿಳಾಸವನ್ನು ನೀವೇ ಟೈಪ್ ಮಾಡಿ .gov.in ನಲ್ಲಿ ಕೊನೆಗೊಳ್ಳುತ್ತದೆಯೇ ನೋಡಿ."),
        "verify_bad": ("ಎಚ್ಚರಿಕೆ: ಈ ವಿಳಾಸ .gov.in ನಲ್ಲಿ ಕೊನೆಗೊಳ್ಳುವುದಿಲ್ಲ, ಆದ್ದರಿಂದ ನಕಲಿ ಇರಬಹುದು. ಅಲ್ಲಿ ಹಣ ಅಥವಾ ಗುರುತಿನ "
                       "ಚೀಟಿ ಕೊಡಬೇಡಿ. ಅಧಿಕೃತ ಮಂಡಳಿ ಸೈಟ್ ಮಾತ್ರ ಬಳಸಿ."),
        "unknown": "ಕ್ಷಮಿಸಿ, ಅರ್ಥವಾಗಲಿಲ್ಲ. ಹೇಳಬಹುದು: ಸ್ಲಾಟ್ ಬುಕ್ ಮಾಡಿ, ಎಷ್ಟು ಹೊತ್ತು ಕಾಯಬೇಕು, ಈ ಸೈಟ್ ನಿಜವೇ.",
        "stub_slots": "ಸ್ಲಾಟ್ ಬುಕಿಂಗ್ ಇನ್ನೂ ಸಂಪರ್ಕವಾಗಿಲ್ಲ (ಸ್ಟಬ್). ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಪ್ರಯತ್ನಿಸಿ.",
        "stub_queue": "ಸರತಿ ಸಮಯ ಇನ್ನೂ ಸಂಪರ್ಕವಾಗಿಲ್ಲ (ಸ್ಟಬ್). ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಪ್ರಯತ್ನಿಸಿ.",
    },
}


def _t(lang, key):
    return T.get(lang, T["en"]).get(key) or T["en"][key]


# ---------------------------------------------------------------- understanding
def _has(text, words):
    return any(w in text for w in words)


def _urls(text):
    return re.findall(r"(?:https?://|www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:/\S*)?", text.lower())


def keyword_intent(text):
    """Returns {intent, age, party, when, gate_hint}. Works offline in all six languages."""
    low = (text or "").lower().translate(DIGITS)
    out = {"intent": "unknown", "age": None, "party": None, "when": None, "gate_hint": None}
    nums = [int(n) for n in re.findall(r"\d{1,3}", low)]
    if _has(low, RELATIVES) or _has(low, AGE_MARK):
        ages = [n for n in nums if 40 <= n <= 110] or [n for n in nums if 10 <= n <= 110]
        if ages:
            out["age"] = ages[0]
        else:
            for w, v in AGE_WORDS:
                if w in low:
                    out["age"] = v
                    break
    p = re.search(r"(\d{1,2})\s*(?:people|persons|pilgrims|members|log|जन|പേർ|പേര|பேர்|మంది|ಜನ)", low)
    if p:
        out["party"] = int(p.group(1))
    else:
        pw = re.search(r"\b(two|three|four|five)\s+(?:people|persons|pilgrims|members)|(दो|तीन|चार|पाँच)\s+(?:लोग|जन|श्रद्धालु)|(രണ്ടു|രണ്ട്|മൂന്ന്|നാല്)\s*(?:പേർ|പേര)", low)
        if pw:
            w = next(g for g in pw.groups() if g)
            out["party"] = {"two": 2, "three": 3, "four": 4, "five": 5, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "രണ്ടു": 2, "രണ്ട്": 2, "മൂന്ന്": 3, "നാല്": 4}[w]
    if _has(low, TOMORROW):
        out["when"] = "tomorrow"
    for part, ws in PARTS.items():
        if _has(low, ws):
            out["when"] = (out["when"] + " " if out["when"] else "") + part
    for g, ws in GATE_ALIASES.items():
        if _has(low, ws):
            out["gate_hint"] = g
            break
    has_domain = bool(re.search(r"[a-z0-9-]+\.(?:com|in|org|net|co|info|xyz|online|site|app)\b", low))
    verify_words = [w for w in KW["verify"] if w not in ("site", "website")]
    if _has(low, verify_words) or has_domain or (_has(low, ["site", "website"]) and _has(low, ["book", "real", "fake"])):
        out["intent"] = "verify"
    elif _has(low, KW["walkin"]):
        out["intent"] = "walkin"
    elif _has(low, KW["wait"]):
        out["intent"] = "wait"
    elif _has(low, KW["book"]):
        out["intent"] = "book"
    elif out["age"]:
        out["intent"] = "age"
    return out


LLM_SYSTEM = ("You route requests of temple pilgrims (any Indian language or mixed). Return ONLY JSON: "
              '{"intent":"book|wait|age|walkin|verify|unknown","age":integer or null,"party":integer or null,'
              '"when":"tomorrow morning" style text or null,"gate":"gate name mentioned or null"}.')


def understand(text, use_llm=True):
    """Keywords first; ask the Sarvam chat model only when keywords find nothing. Returns (intent_dict, via, llm_ms)."""
    kw = keyword_intent(text)
    if kw["intent"] != "unknown" or not use_llm or not sarvam.available():
        return kw, "keywords", 0
    try:
        j, ms = sarvam.chat_json(LLM_SYSTEM, text)
        i = str(j.get("intent", "unknown")).lower()
        if i in ("book", "wait", "age", "walkin", "verify"):
            kw["intent"] = i
            kw["age"] = kw["age"] or (int(j["age"]) if str(j.get("age") or "").isdigit() else None)
            kw["party"] = kw["party"] or (int(j["party"]) if str(j.get("party") or "").isdigit() else None)
            kw["when"] = kw["when"] or j.get("when")
            kw["gate_hint"] = kw["gate_hint"] or j.get("gate")
            return kw, "llm", ms
        return kw, "llm", ms
    except Exception:
        return kw, "keywords", 0


# ---------------------------------------------------------------- time of day
IST = timezone(timedelta(hours=5, minutes=30))
PART_HOUR = {"morning": 6, "afternoon": 13, "evening": 17}
EN_HOURS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12}
EN_MINS = {"fifteen": 15, "thirty": 30, "forty five": 45, "forty-five": 45, "quarter": 15, "half": 30}
CLOCK_MARK = r"(?:am|pm|a\.m\.?|p\.m\.?|o'?clock|बजे|மணி|గంట|മണി|ಗಂಟೆ|baje|mani\b)"


def parse_when(text, now=None):
    """Spoken time wish -> (epoch seconds in the future or None, label). Handles '10:30', '10 am', 'ten thirty',
    'tomorrow morning', 'naalaikku kaalai', 'repu udayam', 'kal subah'. No time words at all -> (None, None)."""
    low = (text or "").lower().translate(DIGITS)
    now = now or datetime.now(IST)
    tomorrow = _has(low, TOMORROW)
    part = next((p for p, ws in PARTS.items() if _has(low, ws)), None)
    hh = mm = None
    m = re.search(r"(?<![\d:])(\d{1,2})[:.](\d{2})(?!\d)\s*(am|pm|p\.m|a\.m)?", low)
    if m and int(m.group(1)) <= 24 and int(m.group(2)) < 60:
        hh, mm = int(m.group(1)), int(m.group(2))
        if m.group(3) and m.group(3).startswith("p") and hh < 12:
            hh += 12
        elif m.group(3) and m.group(3).startswith("a") and hh == 12:
            hh = 0
    else:
        m = re.search(r"(?<![\d:])(\d{1,2})\s*" + CLOCK_MARK, low) or re.search(r"\bat\s+(\d{1,2})\b(?!\s*(?:people|persons))", low)
        if m and 1 <= int(m.group(1)) <= 24:
            hh, mm = int(m.group(1)), 0
            tail = low[m.end() - len(m.group(0)):m.end() + 4]
            if "pm" in tail or "p.m" in tail:
                hh += 12 if hh < 12 else 0
            elif ("am" in tail or "a.m" in tail) and hh == 12:
                hh = 0
        else:
            wm = re.search(r"\b(" + "|".join(EN_HOURS) + r")(?:\s+(" + "|".join(sorted(EN_MINS, key=len, reverse=True)) + r"))?(?=\W|$)", low)
            if wm and (re.search(r"\bat\s+" + wm.group(1), low) or wm.group(2) or re.search(wm.group(1) + r"\s*(?:o'?clock|am|pm)", low)):
                hh, mm = EN_HOURS[wm.group(1)], EN_MINS.get(wm.group(2) or "", 0)
    if hh is not None:
        if part in ("afternoon", "evening") and hh < 12:
            hh += 12
        elif part == "morning" and hh == 12:
            hh = 0
        elif part is None and not re.search(r"am|a\.m|24", low) and 1 <= hh <= 5:
            hh += 12     # nobody books darshan at 3 in the night
    elif part:
        hh, mm = PART_HOUR[part], 0
    elif tomorrow:
        hh, mm = PART_HOUR["morning"], 0
    else:
        return None, None
    if hh > 23:
        hh = 0
    want = now.replace(hour=hh, minute=mm, second=0, microsecond=0) + timedelta(days=1 if tomorrow else 0)
    if want <= now:
        want += timedelta(days=1)
    return int(want.timestamp()), f"{'tomorrow ' if tomorrow else ''}{hh:02d}:{mm:02d}"


DAYPART_WORDS = {
    "en": {"morning": "in the morning", "afternoon": "in the afternoon", "evening": "in the evening", "night": "at night"},
    "hi": {"morning": "सुबह", "afternoon": "दोपहर", "evening": "शाम", "night": "रात"},
    "ml": {"morning": "രാവിലെ", "afternoon": "ഉച്ചയ്ക്ക്", "evening": "വൈകുന്നേരം", "night": "രാത്രി"},
    "ta": {"morning": "காலை", "afternoon": "மதியம்", "evening": "மாலை", "night": "இரவு"},
    "te": {"morning": "ఉదయం", "afternoon": "మధ్యాహ్నం", "evening": "సాయంత్రం", "night": "రాత్రి"},
    "kn": {"morning": "ಬೆಳಿಗ್ಗೆ", "afternoon": "ಮಧ್ಯಾಹ್ನ", "evening": "ಸಂಜೆ", "night": "ರಾತ್ರಿ"},
}
TOMORROW_WORD = {"en": "tomorrow", "hi": "कल", "ml": "നാളെ", "ta": "நாளை", "te": "రేపు", "kn": "ನಾಳೆ"}
TODAY_WORD = {"en": "today", "hi": "आज", "ml": "ഇന്ന്", "ta": "இன்று", "te": "ఈరోజు", "kn": "ಇಂದು"}
MIN_WORD = {"en": "minutes", "hi": "मिनट", "ml": "മിനിറ്റ്", "ta": "நிமிடம்", "te": "నిమిషాలు", "kn": "ನಿಮಿಷ"}
EN_NUM = ["twelve", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven"]


def say_time(lang, ts, now=None):
    """The way people say a slot start: 'tomorrow at quarter past six in the morning', 'कल सुबह 6:15 बजे'."""
    now = now or datetime.now(IST)
    t = datetime.fromtimestamp(ts, IST)
    day = TOMORROW_WORD[lang] if t.date() > now.date() else TODAY_WORD[lang]
    h12 = t.hour % 12 or 12
    part = "morning" if 4 <= t.hour < 12 else "afternoon" if t.hour < 16 else "evening" if t.hour < 20 else "night"
    pw = DAYPART_WORDS[lang][part]
    if lang == "en":
        mins = {0: f"{EN_NUM[h12 % 12]}" + " o'clock", 15: f"quarter past {EN_NUM[h12 % 12]}", 30: f"half past {EN_NUM[h12 % 12]}",
                45: f"quarter to {EN_NUM[(h12 + 1) % 12]}"}.get(t.minute, f"{h12}:{t.minute:02d}")
        return f"{day} at {mins} {pw}"
    clock = f"{h12}:{t.minute:02d}" if t.minute else f"{h12}"
    suffix = {"hi": "बजे", "ml": "മണിക്ക്", "ta": "மணிக்கு", "te": "గంటకు", "kn": "ಗಂಟೆಗೆ"}[lang]
    return f"{day} {pw} {clock} {suffix}"


def spoken(text, lang):
    """Make a reply sound natural when read aloud: no brackets, no symbols."""
    t = text.replace("(", ", ").replace(")", "").replace(" ,", ",").replace("..", ".")
    if lang == "en":
        t = t.replace(".gov.in", " dot gov dot in")
    return re.sub(r"\s+", " ", t).strip()


# ---------------------------------------------------------------- Lane B adapters (lazy)
def _mod(name):
    try:
        return __import__(name)
    except Exception:
        return None


def _first(mod, names):
    for n in names:
        f = getattr(mod, n, None)
        if callable(f):
            return f
    return None


def get_gates(uid="anon", lang="en"):
    """Gate dicts from the simulated queue, or None if queue_sim cannot be imported."""
    qs = _mod("queue_sim")
    try:
        return qs.snapshot()["gates"] if qs else None
    except Exception:
        return None


def gate_in_text(gates, text):
    """The stop the pilgrim names (six scripts, romanised, fuzzy; see gatematch). The gate actually mentioned always wins."""
    import gatematch
    gid = gatematch.best_gate(text)
    for g in gates or []:
        if g.get("id") == gid:
            return g
    return None


def pick_gate(gates, hint):
    if not gates:
        return None
    if hint:
        h = hint.lower()
        for g in gates:
            blob = f"{g.get('id', '')} {g.get('name', '')}".lower()
            if h in blob or any(a in blob for a in GATE_ALIASES.get(h, [])):
                return g
        for g in gates:
            if str(g.get("name", "")).lower() in h:
                return g
    return None


def book_slot(uid, gate, when, walk_in=False):
    """slots.book(uid, gate, time_pref, mode, walk_in) returns (slot, already_booked); we return {slot, mode}."""
    sl, fl = _mod("slots"), _mod("flags")
    if not sl:
        return None
    mode = fl.slot_mode() if fl else "open"
    try:
        slot, again = sl.book(uid, gate or "g4", when, mode, walk_in=walk_in)
    except Exception:
        return None
    return {"slot": slot, "mode": mode, "already_booked": again}


def set_age_trait(uid, age):
    fl = _mod("flags")
    try:
        fl.set_traits(uid, {"age": age, "age_65_plus": age >= 65})
        return True
    except Exception:
        return False


def _slot_text(res):
    if isinstance(res, dict):
        s = res.get("slot", res)
        if isinstance(s, dict):
            return str(s.get("label") or s.get("time") or s.get("slot") or s)
        return str(s)
    return str(res)


# ---------------------------------------------------------------- core
def respond(text, lang, uid="anon", walkin=False, gates=None):
    """Pure text logic. Returns (reply_text, intent, extra_dict)."""
    lang = lang if lang in LANGS else "en"
    info, via, llm_ms = understand(text)
    intent = info["intent"]
    if walkin and intent in ("unknown", "book", "age"):
        intent = "walkin"
    extra = {"intent": intent, "via": via, "llm_ms": llm_ms, "stub": False, "age_set": False}
    if info["age"]:
        extra["age_set"] = set_age_trait(uid, info["age"])
        extra["age"] = info["age"]

    if intent == "verify":
        bad = any(not re.search(r"\.gov\.in(?:/|$)", u.split("/")[0] + "/") for u in _urls(text)
                  if re.search(r"\.(?:com|in|org|net|co|info|xyz|online|site|app)\b", u))
        return _t(lang, "verify_bad" if bad else "verify"), extra
    if intent == "age":
        return _t(lang, "age"), extra
    if intent == "wait":
        g = get_gates(uid, lang) if gates is None else gates
        if not g:
            extra["stub"] = True
            return _t(lang, "stub_queue"), extra
        gate = gate_in_text(g, text) or pick_gate(g, info["gate_hint"])
        if gate:
            extra["gate"] = gate.get("id")
            return _t(lang, "wait").format(gate=gate.get("name"), min=gate.get("wait_min")), extra
        mw = MIN_WORD[lang]
        lst = ". ".join(f"{x.get('name')}, {x.get('wait_min')} {mw}" for x in g)
        return _t(lang, "wait_all").format(list=lst), extra
    if intent in ("book", "walkin"):
        g = get_gates(uid, lang) if gates is None else gates
        gate = gate_in_text(g, text) or pick_gate(g, info["gate_hint"]) or (g[0] if g else None)
        wid = f"walkin-{int(time.time())}" if intent == "walkin" else uid
        want, _lbl = parse_when(text)
        extra["wanted"] = _lbl
        res = book_slot(wid, gate.get("id") if gate else None, want, walk_in=(intent == "walkin"))
        if res is None:
            extra["stub"] = True
            return _t(lang, "stub_slots"), extra
        extra["booking"] = res
        sd = res["slot"] if isinstance(res.get("slot"), dict) else {}
        when = say_time(lang, sd["window"]) if sd.get("window") else _slot_text(res)
        gname = sd.get("gate_name") or (gate or {}).get("name") or ""
        if intent == "walkin":
            return _t(lang, "book_walkin").format(party=info["party"] or 1, when=when, gate=gname), extra
        return _t(lang, "book_ok").format(when=when, gate=gname), extra
    return _t(lang, "unknown"), extra


def respond_brain(text, lang, uid="anon", walkin=False):
    """Same brain as the live turn. Returns (reply, extra). Booking, verify and age questions keep the older exact flow."""
    lang = lang if lang in LANGS else "en"
    if walkin:
        return respond(text, lang, uid, walkin)
    kw = keyword_intent(text)
    try:
        import sys
        import assistant
        if assistant.queue_sim is not sys.modules.get("queue_sim"):
            raise RuntimeError("state module replaced")
        br = assistant.answer(text, lang, uid, None, defer_unknown=kw["intent"] in ("book", "walkin", "verify", "age"))
    except Exception:   # state modules missing or faked: the older exact flow still answers
        return respond(text, lang, uid)
    if br is None or br["action"] == "book":
        reply, extra = respond(text, lang, uid)
        if br is not None:
            extra["brain"] = br
        return reply, extra
    extra = {"intent": br["intent"], "via": br["via"], "llm_ms": br.get("llm_ms", 0), "stub": False, "age_set": False, "brain": br}
    if br["action"] == "cancel":
        sl = _mod("slots")
        ok = bool(sl and sl.cancel(uid))
        return assistant.T(lang, "cancelled" if ok else "cancel_none"), extra
    if br["action"] == "change":
        when, _lbl = parse_when(text)
        sl = _mod("slots")
        if when and sl and sl.get(uid):
            sl.cancel(uid)
            reply, ex2 = respond(text, lang, uid)
            ex2["brain"] = {**br, "show": "slot"}
            return reply, ex2
        return assistant.T(lang, "ask_new_time"), extra
    return br["reply"], extra


def speak(text, lang):
    """Returns (audio_b64 or None, tts_ms, notice or None)."""
    import os
    cache = os.environ.get("TTS_CACHE", "1") != "0"
    path = None
    if cache:   # same text and language again (Play again, repeated prompts): no new Sarvam call. Credits are limited.
        import volunteer
        path = volunteer._cache_path(text, lang)
        for p in (path, os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_seed", os.path.basename(path))):
            try:
                with open(p, "rb") as f:
                    w = f.read()
                if len(w) > 1000:
                    return base64.b64encode(w).decode(), 0, None
            except OSError:
                pass
    if not sarvam.available():
        return None, 0, "Voice unavailable (no Sarvam key). Type instead."
    try:
        a = sarvam.tts(spoken(text, lang), lang)
        if path:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as f:
                    f.write(a.wav)
            except OSError:
                pass
        return base64.b64encode(a.wav).decode(), a.ms, None
    except sarvam.SarvamNoCredits:
        return None, 0, sarvam.NO_CREDITS_MSG
    except sarvam.SarvamError as e:
        return None, 0, f"Voice unavailable ({e}). Type instead."


async def _read_request(request: Request):
    ct = request.headers.get("content-type", "")
    if "json" in ct:
        d = await request.json()
        return d.get("text"), None, None, d
    form = await request.form()
    up = form.get("audio")
    audio = (await up.read(), up.filename or "audio.webm", up.content_type or "audio/webm") if up and hasattr(up, "read") else None
    return form.get("text"), audio, None, dict(form)


_SCRIPTS = (("te", 0x0C00, 0x0C7F), ("ta", 0x0B80, 0x0BFF), ("ml", 0x0D00, 0x0D7F), ("kn", 0x0C80, 0x0CFF), ("hi", 0x0900, 0x097F))


def script_lang(text):
    """The language a text is written in, from its script (Telugu, Tamil, Malayalam, Kannada, Devanagari); None for Latin or mixed-unknown.
    A pilgrim who speaks or types Telugu is answered in Telugu even when the page or the detector says English."""
    n = {}
    for ch in text or "":
        o = ord(ch)
        for k, a, b in _SCRIPTS:
            if a <= o <= b:
                n[k] = n.get(k, 0) + 1
    if not n:
        return None
    k = max(n, key=n.get)
    return k if n[k] >= 3 else None


@router.post("/api/directions")
async def api_directions(request: Request):
    from starlette.concurrency import run_in_threadpool
    t0 = time.perf_counter()
    text, audio, _, d = await _read_request(request)
    uid = str(d.get("uid") or "anon")
    lang = str(d.get("lang") or "auto").lower()[:2]
    walkin = str(d.get("walkin", "")).lower() in ("1", "true", "yes", "on")
    lat = {"stt_ms": 0, "llm_ms": 0, "tts_ms": 0}
    notice = None
    transcript = (text or "").strip()
    if audio and not transcript:
        try:
            r = await run_in_threadpool(sarvam.stt, *audio)
            transcript = r.transcript.strip()
            lat["stt_ms"] = r.ms
            if lang not in LANGS and r.language:
                lang = r.language
        except sarvam.SarvamNoCredits:
            return JSONResponse({"transcript": "", "reply_text": sarvam.NO_CREDITS_MSG, "audio_base64": None,
                                 "notice": sarvam.NO_CREDITS_MSG, "latency": {**lat, "total_ms": 0}}, status_code=200)
        except sarvam.SarvamError as e:
            return JSONResponse({"transcript": "", "reply_text": f"Voice unavailable ({e}). Type instead.",
                                 "audio_base64": None, "notice": str(e), "latency": {**lat, "total_ms": 0}}, status_code=200)
    if str(d.get("readback", "")).lower() not in ("1", "true"):
        lang = script_lang(transcript) or lang
    if lang not in LANGS:
        lang = "en"
    if str(d.get("readback", "")).lower() in ("1", "true") and transcript:
        reply, extra = transcript, {"intent": "readback", "via": "none"}  # speak this text as is, no intent logic
    elif not transcript:
        reply, extra = _t(lang, "unknown"), {"intent": "unknown", "via": "none"}
    else:
        reply, extra = await run_in_threadpool(respond_brain, transcript, lang, uid, walkin)
        lat["llm_ms"] = extra.pop("llm_ms", 0)
    b64, lat["tts_ms"], notice = await run_in_threadpool(speak, reply, lang)
    lat["total_ms"] = int((time.perf_counter() - t0) * 1000)
    extra = dict(extra)
    try:
        import sys
        import assistant
        if assistant.queue_sim is not sys.modules.get("queue_sim"):
            raise RuntimeError("state module replaced")
        br_fields = assistant.brain_fields(uid, extra)
    except Exception:
        br_fields = {}
    extra.pop("brain", None)
    out = {"transcript": transcript, "reply_text": reply, "audio_base64": b64, "lang": lang,
           "notice": notice, "latency": lat, **extra, **br_fields}
    bk = extra.get("booking")
    if bk and isinstance(bk.get("slot"), dict):
        out["slot"] = {"gate": bk["slot"].get("gate"), "label": bk["slot"].get("label")}
        out["mode"] = bk.get("mode")
    return out
