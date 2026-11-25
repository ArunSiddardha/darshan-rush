"""The pilgrim assistant brain: answer(text, lang, uid, session) -> dict.

Fast rules answer almost everything from the live (simulated) state, in six languages, without the model.
Only text the rules cannot classify goes to the Sarvam chat model with a facts block; its JSON is validated
against the facts (gate ids must exist, numbers must come from the facts). When the model is unavailable or
slow the rules answer, and the pilgrim is never answered about the wrong stop.
"""
import json
import re
import threading
import time
import unicodedata

import directions
import gatematch
import queue_sim
import route_facts
import sarvam

LANGS = directions.LANGS
ORDER = [g["id"] for g in queue_sim.GATES]
WALK = {(a, b): route_facts.minutes(a, b) for a, b in zip(route_facts.STOPS[:4], route_facts.STOPS[1:5])}   # simulated minutes between stops (route_facts is the source)
XY = {"g1": (12, 86), "g2": (30, 66), "g3": (52, 74), "g4": (70, 48), "g5": (86, 18)}
FACILITIES = {"g1": ["water", "toilet", "cloak", "info", "lost_found", "wheelchair"], "g2": ["water", "toilet", "rest"],
              "g3": ["rest", "medical", "water"], "g4": ["toilet", "info", "wheelchair", "lost_found", "medical"],
              "g5": ["water", "medical", "rest", "info"]}
FAC_LABEL = {
    "water": {"en": "Drinking water", "hi": "पीने का पानी", "ml": "കുടിവെള്ളം", "ta": "குடிநீர்", "te": "తాగునీరు", "kn": "ಕುಡಿಯುವ ನೀರು"},
    "toilet": {"en": "Toilets", "hi": "शौचालय", "ml": "ടോയ്‌ലറ്റ്", "ta": "கழிப்பறை", "te": "టాయిలెట్లు", "kn": "ಶೌಚಾಲಯ"},
    "medical": {"en": "The medical post", "hi": "मेडिकल पोस्ट", "ml": "മെഡിക്കൽ പോസ്റ്റ്", "ta": "மருத்துவ மையம்", "te": "మెడికల్ పోస్ట్", "kn": "ವೈದ್ಯಕೀಯ ಕೇಂದ್ರ"},
    "rest": {"en": "The rest area", "hi": "विश्राम स्थल", "ml": "വിശ്രമ സ്ഥലം", "ta": "ஓய்வு இடம்", "te": "విశ్రాంతి స్థలం", "kn": "ವಿಶ್ರಾಂತಿ ಸ್ಥಳ"},
    "wheelchair": {"en": "Wheelchair help", "hi": "व्हीलचेयर सहायता", "ml": "വീൽചെയർ സഹായം", "ta": "சக்கர நாற்காலி உதவி", "te": "వీల్‌చైర్ సహాయం", "kn": "ವೀಲ್‌ಚೇರ್ ಸಹಾಯ"},
    "cloak": {"en": "The cloak room", "hi": "क्लोक रूम", "ml": "ക്ലോക്ക് റൂം", "ta": "கிளாக் ரூம்", "te": "క్లోక్ రూమ్", "kn": "ಕ್ಲೋಕ್ ರೂಮ್"},
    "lost_found": {"en": "Lost and found", "hi": "खोया पाया केंद्र", "ml": "നഷ്ടപ്പെട്ടവ കണ്ടെത്തൽ കേന്ദ്രം", "ta": "தொலைந்தவை மையம்", "te": "తప్పిపోయినవి కేంద్రం", "kn": "ಕಳೆದುಹೋದ ವಸ್ತು ಕೇಂದ್ರ"},
    "info": {"en": "The information counter", "hi": "सूचना काउंटर", "ml": "ഇൻഫർമേഷൻ കൗണ്ടർ", "ta": "தகவல் கவுண்டர்", "te": "సమాచార కౌంటర్", "kn": "ಮಾಹಿತಿ ಕೌಂಟರ್"},
}
UNIT = {"en": "minutes", "hi": "मिनट", "ml": "മിനിറ്റ്", "ta": "நிமிடம்", "te": "నిమిషాలు", "kn": "ನಿಮಿಷ"}

TPL = {
 "en": {
  "pos_next": "You are at {pos}. Next is {nxt}, {walk} on foot. The wait there is {wait}.{slot}",
  "pos_last": "You are at {pos}, the last stop. The wait here is {wait}.{slot}",
  "wait_gate": "The wait at {gate} is {wait}.{frm}", "frm": " From {pos} it is {walk} on foot.",
  "wait_best": "{gate} has the shortest wait, {wait}.", "wait_all": "Waits now: {list}.",
  "crowd": "The longest wait is {g1}, {w1}. The shortest is {g2}, {w2}.{rush}", "rush": " It is busy, so slots are staggered.",
  "next_nopos": "Tell me which stop you are at, for example: I reached {first}. The route starts at {first}, then {second}.",
  "distance": "{gate} is {walk} on foot from {pos}.",
  "distance_nopos": "Tell me which stop you are at. From {first} it is {walk} on foot to {gate}.",
  "slot_info": "Your slot is {time} at {gate}.{state}", "st_soon": " It starts in {m}.", "st_now": " It is open now, please go to the gate.",
  "st_past": " That time has passed.", "slot_none": "You have no slot yet. Say: book a slot, and I will help.",
  "late_soon": "You are not late. Your slot is {time} at {gate}, it starts in {m}.",
  "late_now": "Your slot window is open now. Please go to {gate} soon.",
  "late_past": "Your slot time has passed. Say: book a slot, and I will find a new one.",
  "fac": "{fac}: {stops}.{near}", "near": " Nearest to you: {stop}.", "ask_pos": " Tell me which stop you have reached and I will name the nearest one.",
  "where_unk": "I do not know where you are yet. Which stop have you reached: {stops}? Say it, or tap it on the map.",
  "elder": "For elders, wheelchair help is at {w} and rest areas are at {r}. A volunteer at the counter can help too.",
  "distress": "Please stay calm. Go to the nearest volunteer or the information counter at {info}. I have left a help note on the volunteer screen.",
  "fee": "There is no fee. Booking is free and no payment is ever asked. Slots are booked only here or at the spot counter. Do not pay anyone.",
  "carry": "Carry drinking water, light clothes and any medicine you need. Keep bags small. The cloak room is at {c}.",
  "about": "I am a prototype assistant for a crowded shrine. I tell you waiting times, the route and your slot, and I can book one. The data is simulated.",
  "unknown": "I do not have that information, please ask the volunteer at the counter.",
  "goodbye": "You are welcome. Take care.", "ask_new_time": "Tell me the new time, for example tomorrow morning.",
  "cancelled": "Done. Your booking is cancelled.", "cancel_none": "You have no booking to cancel."},
 "hi": {
  "pos_next": "आप {pos} पर हैं। अगला पड़ाव {nxt} है, पैदल {walk}। वहाँ इंतज़ार {wait} है।{slot}",
  "pos_last": "आप {pos} पर हैं, यह आख़िरी पड़ाव है। यहाँ इंतज़ार {wait} है।{slot}",
  "wait_gate": "{gate} पर इंतज़ार {wait} है।{frm}", "frm": " {pos} से पैदल {walk} लगते हैं।",
  "wait_best": "{gate} पर सबसे कम इंतज़ार है, {wait}।", "wait_all": "अभी इंतज़ार: {list}।",
  "crowd": "सबसे ज़्यादा इंतज़ार {g1} पर है, {w1}। सबसे कम {g2} पर, {w2}।{rush}", "rush": " भीड़ है, इसलिए स्लॉट अलग-अलग समय पर दिए जा रहे हैं।",
  "next_nopos": "बताइए आप किस पड़ाव पर हैं, जैसे: मैं {first} पहुँच गया। रास्ता {first} से शुरू होकर {second} जाता है।",
  "distance": "{gate}, {pos} से पैदल {walk} दूर है।",
  "distance_nopos": "बताइए आप किस पड़ाव पर हैं। {first} से {gate} तक पैदल {walk} लगते हैं।",
  "slot_info": "आपका स्लॉट {time} है, {gate} पर।{state}", "st_soon": " यह {m} में शुरू होगा।", "st_now": " अभी खुला है, कृपया गेट पर जाइए।",
  "st_past": " वह समय निकल चुका है।", "slot_none": "अभी आपका कोई स्लॉट नहीं है। कहिए: स्लॉट बुक करो।",
  "late_soon": "आप लेट नहीं हैं। आपका स्लॉट {time} है, {gate} पर, यह {m} में शुरू होगा।",
  "late_now": "आपका स्लॉट अभी खुला है। कृपया जल्दी {gate} जाइए।",
  "late_past": "आपका स्लॉट का समय निकल गया है। कहिए: स्लॉट बुक करो, मैं नया स्लॉट देखता हूँ।",
  "fac": "{fac}: {stops}।{near}", "near": " आपके सबसे पास: {stop}।", "ask_pos": " बताइए आप किस पड़ाव पर पहुँचे हैं, मैं सबसे पास वाला बता दूँगा।",
  "where_unk": "मुझे अभी नहीं पता आप कहाँ हैं। आप किस पड़ाव पर पहुँचे हैं: {stops}? बोलिए या नक्शे पर छुइए।",
  "elder": "बुज़ुर्गों के लिए व्हीलचेयर सहायता {w} पर है और विश्राम स्थल {r} पर हैं। काउंटर पर स्वयंसेवक भी मदद करेंगे।",
  "distress": "शांत रहिए। सबसे पास के स्वयंसेवक या {info} के सूचना काउंटर पर जाइए। मैंने स्वयंसेवक की स्क्रीन पर मदद का नोट छोड़ दिया है।",
  "fee": "कोई शुल्क नहीं है। बुकिंग मुफ़्त है और कभी पैसे नहीं माँगे जाते। स्लॉट सिर्फ़ यहाँ या स्पॉट काउंटर पर मिलते हैं। किसी को पैसे न दें।",
  "carry": "पीने का पानी, हल्के कपड़े और ज़रूरी दवा साथ रखिए। बैग छोटे रखिए। क्लोक रूम {c} पर है।",
  "about": "मैं भीड़ वाले तीर्थ के लिए एक प्रोटोटाइप सहायक हूँ। मैं इंतज़ार, रास्ता और आपका स्लॉट बताता हूँ और स्लॉट बुक कर सकता हूँ। डेटा नकली, सिमुलेटेड है।",
  "unknown": "मेरे पास यह जानकारी नहीं है, कृपया काउंटर पर स्वयंसेवक से पूछिए।",
  "goodbye": "आपका स्वागत है। ध्यान रखिए।", "ask_new_time": "नया समय बताइए, जैसे कल सुबह।",
  "cancelled": "ठीक है। आपकी बुकिंग रद्द हो गई।", "cancel_none": "आपकी कोई बुकिंग नहीं है।"},
 "ml": {
  "pos_next": "നിങ്ങൾ {pos} ൽ ആണ്. അടുത്തത് {nxt}, നടക്കാൻ {walk}. അവിടെ കാത്തിരിപ്പ് {wait}.{slot}",
  "pos_last": "നിങ്ങൾ {pos} ൽ ആണ്, ഇത് അവസാന സ്ഥലമാണ്. ഇവിടെ കാത്തിരിപ്പ് {wait}.{slot}",
  "wait_gate": "{gate} ൽ കാത്തിരിപ്പ് {wait} ആണ്.{frm}", "frm": " {pos} ൽ നിന്ന് നടക്കാൻ {walk}.",
  "wait_best": "{gate} ൽ ആണ് ഏറ്റവും കുറവ് കാത്തിരിപ്പ്, {wait}.", "wait_all": "ഇപ്പോഴത്തെ കാത്തിരിപ്പ്: {list}.",
  "crowd": "ഏറ്റവും കൂടുതൽ കാത്തിരിപ്പ് {g1} ൽ, {w1}. ഏറ്റവും കുറവ് {g2} ൽ, {w2}.{rush}", "rush": " തിരക്കുണ്ട്, അതിനാൽ സ്ലോട്ടുകൾ ഇടവിട്ടാണ്.",
  "next_nopos": "നിങ്ങൾ ഏത് സ്ഥലത്താണെന്ന് പറയൂ, ഉദാഹരണത്തിന്: ഞാൻ {first} ൽ എത്തി. വഴി {first} ൽ തുടങ്ങി {second} ലേക്ക് പോകുന്നു.",
  "distance": "{pos} ൽ നിന്ന് {gate} ലേക്ക് നടക്കാൻ {walk}.",
  "distance_nopos": "നിങ്ങൾ ഏത് സ്ഥലത്താണെന്ന് പറയൂ. {first} ൽ നിന്ന് {gate} ലേക്ക് നടക്കാൻ {walk}.",
  "slot_info": "നിങ്ങളുടെ സ്ലോട്ട് {time}, {gate} ൽ.{state}", "st_soon": " ഇത് {m} കഴിഞ്ഞ് തുടങ്ങും.", "st_now": " ഇപ്പോൾ തുറന്നിട്ടുണ്ട്, ഗേറ്റിലേക്ക് പോകൂ.",
  "st_past": " ആ സമയം കഴിഞ്ഞു.", "slot_none": "നിങ്ങൾക്ക് ഇതുവരെ സ്ലോട്ട് ഇല്ല. സ്ലോട്ട് ബുക്ക് ചെയ്യൂ എന്ന് പറയൂ.",
  "late_soon": "നിങ്ങൾ വൈകിയിട്ടില്ല. സ്ലോട്ട് {time}, {gate} ൽ, {m} കഴിഞ്ഞ് തുടങ്ങും.",
  "late_now": "നിങ്ങളുടെ സ്ലോട്ട് ഇപ്പോൾ തുറന്നിട്ടുണ്ട്. വേഗം {gate} ലേക്ക് പോകൂ.",
  "late_past": "നിങ്ങളുടെ സ്ലോട്ട് സമയം കഴിഞ്ഞു. സ്ലോട്ട് ബുക്ക് ചെയ്യൂ എന്ന് പറയൂ, പുതിയത് നോക്കാം.",
  "fac": "{fac}: {stops}.{near}", "near": " നിങ്ങൾക്ക് ഏറ്റവും അടുത്തത്: {stop}.", "ask_pos": " നിങ്ങൾ ഏത് സ്ഥലത്ത് എത്തി എന്ന് പറയൂ, ഏറ്റവും അടുത്തത് ഞാൻ പറയാം.",
  "where_unk": "നിങ്ങൾ എവിടെയാണെന്ന് എനിക്ക് ഇതുവരെ അറിയില്ല. ഏത് സ്ഥലത്താണ് എത്തിയത്: {stops}? പറയൂ, അല്ലെങ്കിൽ മാപ്പിൽ തൊടൂ.",
  "elder": "മുതിർന്നവർക്ക് വീൽചെയർ സഹായം {w} ൽ ഉണ്ട്, വിശ്രമ സ്ഥലങ്ങൾ {r} ൽ. കൗണ്ടറിലെ വോളന്റിയറും സഹായിക്കും.",
  "distress": "ശാന്തമായിരിക്കൂ. അടുത്തുള്ള വോളന്റിയറുടെ അടുത്തോ {info} ലെ ഇൻഫർമേഷൻ കൗണ്ടറിലോ പോകൂ. വോളന്റിയർ സ്ക്രീനിൽ ഞാൻ സഹായ കുറിപ്പ് ഇട്ടിട്ടുണ്ട്.",
  "fee": "ഫീസ് ഇല്ല. ബുക്കിംഗ് സൗജന്യമാണ്, പണം ഒരിക്കലും ചോദിക്കില്ല. സ്ലോട്ട് ഇവിടെയോ സ്പോട്ട് കൗണ്ടറിലോ മാത്രം. ആർക്കും പണം നൽകരുത്.",
  "carry": "കുടിവെള്ളം, ഭാരം കുറഞ്ഞ വസ്ത്രം, ആവശ്യമായ മരുന്ന് എന്നിവ കരുതൂ. ബാഗ് ചെറുതാക്കൂ. ക്ലോക്ക് റൂം {c} ൽ ആണ്.",
  "about": "തിരക്കുള്ള തീർത്ഥാടന കേന്ദ്രത്തിനുള്ള ഒരു പ്രോട്ടോടൈപ്പ് സഹായിയാണ് ഞാൻ. കാത്തിരിപ്പ്, വഴി, സ്ലോട്ട് എന്നിവ പറയും, സ്ലോട്ട് ബുക്ക് ചെയ്യാനും കഴിയും. ഡാറ്റ സിമുലേറ്റഡ് ആണ്.",
  "unknown": "എനിക്ക് ആ വിവരം ഇല്ല, ദയവായി കൗണ്ടറിലെ വോളന്റിയറോട് ചോദിക്കൂ.",
  "goodbye": "സന്തോഷം. ശ്രദ്ധിക്കൂ.", "ask_new_time": "പുതിയ സമയം പറയൂ, ഉദാഹരണത്തിന് നാളെ രാവിലെ.",
  "cancelled": "ശരി. നിങ്ങളുടെ ബുക്കിംഗ് റദ്ദാക്കി.", "cancel_none": "റദ്ദാക്കാൻ ബുക്കിംഗ് ഇല്ല."},
 "ta": {
  "pos_next": "நீங்கள் {pos} இல் இருக்கிறீர்கள். அடுத்தது {nxt}, நடந்து {walk}. அங்கே காத்திருப்பு {wait}.{slot}",
  "pos_last": "நீங்கள் {pos} இல் இருக்கிறீர்கள், இது கடைசி இடம். இங்கே காத்திருப்பு {wait}.{slot}",
  "wait_gate": "{gate} இல் காத்திருப்பு {wait}.{frm}", "frm": " {pos} இலிருந்து நடந்து {walk}.",
  "wait_best": "{gate} இல் தான் குறைந்த காத்திருப்பு, {wait}.", "wait_all": "இப்போதைய காத்திருப்பு: {list}.",
  "crowd": "அதிக காத்திருப்பு {g1} இல், {w1}. குறைவு {g2} இல், {w2}.{rush}", "rush": " கூட்டம் அதிகம், அதனால் ஸ்லாட்டுகள் பிரித்து வழங்கப்படுகின்றன.",
  "next_nopos": "நீங்கள் எந்த இடத்தில் இருக்கிறீர்கள் என்று சொல்லுங்கள், உதாரணம்: நான் {first} வந்துவிட்டேன். வழி {first} இல் தொடங்கி {second} செல்கிறது.",
  "distance": "{pos} இலிருந்து {gate} நடந்து {walk}.",
  "distance_nopos": "நீங்கள் எந்த இடத்தில் இருக்கிறீர்கள் என்று சொல்லுங்கள். {first} இலிருந்து {gate} நடந்து {walk}.",
  "slot_info": "உங்கள் ஸ்லாட் {time}, {gate} இல்.{state}", "st_soon": " இது {m} இல் தொடங்கும்.", "st_now": " இப்போது திறந்துள்ளது, கேட்டுக்கு செல்லுங்கள்.",
  "st_past": " அந்த நேரம் கடந்துவிட்டது.", "slot_none": "உங்களுக்கு இன்னும் ஸ்லாட் இல்லை. ஸ்லாட் புக் செய் என்று சொல்லுங்கள்.",
  "late_soon": "நீங்கள் தாமதம் இல்லை. ஸ்லாட் {time}, {gate} இல், {m} இல் தொடங்கும்.",
  "late_now": "உங்கள் ஸ்லாட் இப்போது திறந்துள்ளது. சீக்கிரம் {gate} செல்லுங்கள்.",
  "late_past": "உங்கள் ஸ்லாட் நேரம் கடந்துவிட்டது. ஸ்லாட் புக் செய் என்று சொல்லுங்கள், புதியது பார்க்கிறேன்.",
  "fac": "{fac}: {stops}.{near}", "near": " உங்களுக்கு அருகில்: {stop}.", "ask_pos": " நீங்கள் எந்த இடத்தை அடைந்தீர்கள் என்று சொல்லுங்கள், அருகில் உள்ளதைச் சொல்கிறேன்.",
  "where_unk": "நீங்கள் எங்கே இருக்கிறீர்கள் என்று இன்னும் தெரியாது. எந்த இடத்தை அடைந்தீர்கள்: {stops}? சொல்லுங்கள், அல்லது வரைபடத்தில் தொடுங்கள்.",
  "elder": "முதியவர்களுக்கு சக்கர நாற்காலி உதவி {w} இல் உள்ளது, ஓய்வு இடங்கள் {r} இல். கவுண்டரில் தன்னார்வலரும் உதவுவார்.",
  "distress": "அமைதியாக இருங்கள். அருகிலுள்ள தன்னார்வலரிடம் அல்லது {info} தகவல் கவுண்டருக்கு செல்லுங்கள். தன்னார்வலர் திரையில் உதவி குறிப்பு வைத்துள்ளேன்.",
  "fee": "கட்டணம் இல்லை. பதிவு இலவசம், பணம் ஒருபோதும் கேட்கப்படாது. ஸ்லாட் இங்கே அல்லது ஸ்பாட் கவுண்டரில் மட்டுமே. யாருக்கும் பணம் கொடுக்காதீர்கள்.",
  "carry": "குடிநீர், இலகுவான உடை, தேவையான மருந்து எடுத்துச் செல்லுங்கள். பை சிறியதாக இருக்கட்டும். கிளாக் ரூம் {c} இல் உள்ளது.",
  "about": "நெரிசலான புனிதத் தலத்துக்கான முன்மாதிரி உதவியாளர் நான். காத்திருப்பு, வழி, உங்கள் ஸ்லாட் சொல்வேன், ஸ்லாட் புக் செய்வேன். தரவு போலியானது, சிமுலேட்டட்.",
  "unknown": "என்னிடம் அந்தத் தகவல் இல்லை, கவுண்டரில் உள்ள தன்னார்வலரிடம் கேளுங்கள்.",
  "goodbye": "நன்றி. கவனமாக இருங்கள்.", "ask_new_time": "புதிய நேரம் சொல்லுங்கள், உதாரணம் நாளை காலை.",
  "cancelled": "சரி. உங்கள் பதிவு ரத்து செய்யப்பட்டது.", "cancel_none": "ரத்து செய்ய பதிவு இல்லை."},
 "te": {
  "pos_next": "మీరు {pos} దగ్గర ఉన్నారు. తర్వాత {nxt}, నడవడానికి {walk}. అక్కడ వేచి ఉండే సమయం {wait}.{slot}",
  "pos_last": "మీరు {pos} దగ్గర ఉన్నారు, ఇది చివరి చోటు. ఇక్కడ వేచి ఉండే సమయం {wait}.{slot}",
  "wait_gate": "{gate} దగ్గర వేచి ఉండే సమయం {wait}.{frm}", "frm": " {pos} నుండి నడవడానికి {walk}.",
  "wait_best": "{gate} దగ్గర తక్కువ సమయం, {wait}.", "wait_all": "ఇప్పటి వేచి ఉండే సమయాలు: {list}.",
  "crowd": "ఎక్కువ సమయం {g1} దగ్గర, {w1}. తక్కువ {g2} దగ్గర, {w2}.{rush}", "rush": " రద్దీగా ఉంది, అందుకే స్లాట్లు విడివిడిగా ఇస్తున్నారు.",
  "next_nopos": "మీరు ఏ చోట ఉన్నారో చెప్పండి, ఉదాహరణకు: నేను {first} చేరుకున్నాను. దారి {first} నుండి మొదలై {second} వెళ్తుంది.",
  "distance": "{pos} నుండి {gate} కి నడవడానికి {walk}.",
  "distance_nopos": "మీరు ఏ చోట ఉన్నారో చెప్పండి. {first} నుండి {gate} కి నడవడానికి {walk}.",
  "slot_info": "మీ స్లాట్ {time}, {gate} దగ్గర.{state}", "st_soon": " ఇది {m} లో మొదలవుతుంది.", "st_now": " ఇప్పుడు తెరిచి ఉంది, గేటు దగ్గరకు వెళ్ళండి.",
  "st_past": " ఆ సమయం దాటిపోయింది.", "slot_none": "మీకు ఇంకా స్లాట్ లేదు. స్లాట్ బుక్ చేయి అని చెప్పండి.",
  "late_soon": "మీరు ఆలస్యం కాలేదు. స్లాట్ {time}, {gate} దగ్గర, {m} లో మొదలవుతుంది.",
  "late_now": "మీ స్లాట్ ఇప్పుడు తెరిచి ఉంది. త్వరగా {gate} కి వెళ్ళండి.",
  "late_past": "మీ స్లాట్ సమయం దాటిపోయింది. స్లాట్ బుక్ చేయి అని చెప్పండి, కొత్తది చూస్తాను.",
  "fac": "{fac}: {stops}.{near}", "near": " మీకు దగ్గరలో: {stop}.", "ask_pos": " మీరు ఏ చోటుకు చేరారో చెప్పండి, దగ్గరలో ఉన్నది చెబుతాను.",
  "where_unk": "మీరు ఎక్కడ ఉన్నారో నాకు ఇంకా తెలియదు. ఏ చోటుకు చేరారు: {stops}? చెప్పండి, లేదా మ్యాప్‌లో తాకండి.",
  "elder": "పెద్దవారికి వీల్‌చైర్ సహాయం {w} దగ్గర ఉంది, విశ్రాంతి స్థలాలు {r} దగ్గర. కౌంటర్ వద్ద వాలంటీర్ కూడా సహాయం చేస్తారు.",
  "distress": "ప్రశాంతంగా ఉండండి. దగ్గరలోని వాలంటీర్ దగ్గరకు లేదా {info} లోని సమాచార కౌంటర్ కి వెళ్ళండి. వాలంటీర్ స్క్రీన్ మీద సహాయ నోట్ ఉంచాను.",
  "fee": "ఫీజు లేదు. బుకింగ్ ఉచితం, డబ్బు ఎప్పుడూ అడగరు. స్లాట్లు ఇక్కడ లేదా స్పాట్ కౌంటర్ వద్ద మాత్రమే. ఎవరికీ డబ్బు ఇవ్వకండి.",
  "carry": "తాగునీరు, తేలికపాటి బట్టలు, అవసరమైన మందులు తీసుకెళ్ళండి. బ్యాగ్ చిన్నదిగా ఉంచండి. క్లోక్ రూమ్ {c} దగ్గర ఉంది.",
  "about": "రద్దీగా ఉండే పుణ్యక్షేత్రం కోసం ప్రోటోటైప్ సహాయకుడిని. వేచి ఉండే సమయం, దారి, మీ స్లాట్ చెబుతాను, స్లాట్ బుక్ చేయగలను. డేటా నకిలీ, సిమ్యులేటెడ్.",
  "unknown": "నా దగ్గర ఆ సమాచారం లేదు, దయచేసి కౌంటర్ వద్ద వాలంటీర్ ని అడగండి.",
  "goodbye": "సరే, జాగ్రత్తగా ఉండండి.", "ask_new_time": "కొత్త సమయం చెప్పండి, ఉదాహరణకు రేపు ఉదయం.",
  "cancelled": "సరే. మీ బుకింగ్ రద్దయింది.", "cancel_none": "రద్దు చేయడానికి బుకింగ్ లేదు."},
 "kn": {
  "pos_next": "ನೀವು {pos} ನಲ್ಲಿ ಇದ್ದೀರಿ. ಮುಂದೆ {nxt}, ನಡೆಯಲು {walk}. ಅಲ್ಲಿ ಕಾಯುವ ಸಮಯ {wait}.{slot}",
  "pos_last": "ನೀವು {pos} ನಲ್ಲಿ ಇದ್ದೀರಿ, ಇದು ಕೊನೆಯ ಸ್ಥಳ. ಇಲ್ಲಿ ಕಾಯುವ ಸಮಯ {wait}.{slot}",
  "wait_gate": "{gate} ನಲ್ಲಿ ಕಾಯುವ ಸಮಯ {wait}.{frm}", "frm": " {pos} ನಿಂದ ನಡೆಯಲು {walk}.",
  "wait_best": "{gate} ನಲ್ಲಿ ಕಡಿಮೆ ಸಮಯ, {wait}.", "wait_all": "ಈಗಿನ ಕಾಯುವ ಸಮಯ: {list}.",
  "crowd": "ಹೆಚ್ಚು ಸಮಯ {g1} ನಲ್ಲಿ, {w1}. ಕಡಿಮೆ {g2} ನಲ್ಲಿ, {w2}.{rush}", "rush": " ಜನಸಂದಣಿ ಇದೆ, ಆದ್ದರಿಂದ ಸ್ಲಾಟ್‌ಗಳನ್ನು ಹಂಚಲಾಗುತ್ತಿದೆ.",
  "next_nopos": "ನೀವು ಯಾವ ಸ್ಥಳದಲ್ಲಿ ಇದ್ದೀರಿ ಹೇಳಿ, ಉದಾಹರಣೆಗೆ: ನಾನು {first} ತಲುಪಿದೆ. ದಾರಿ {first} ನಿಂದ ಶುರುವಾಗಿ {second} ಕ್ಕೆ ಹೋಗುತ್ತದೆ.",
  "distance": "{pos} ನಿಂದ {gate} ಗೆ ನಡೆಯಲು {walk}.",
  "distance_nopos": "ನೀವು ಯಾವ ಸ್ಥಳದಲ್ಲಿ ಇದ್ದೀರಿ ಹೇಳಿ. {first} ನಿಂದ {gate} ಗೆ ನಡೆಯಲು {walk}.",
  "slot_info": "ನಿಮ್ಮ ಸ್ಲಾಟ್ {time}, {gate} ನಲ್ಲಿ.{state}", "st_soon": " ಇದು {m} ನಲ್ಲಿ ಶುರುವಾಗುತ್ತದೆ.", "st_now": " ಈಗ ತೆರೆದಿದೆ, ಗೇಟ್‌ಗೆ ಹೋಗಿ.",
  "st_past": " ಆ ಸಮಯ ಮುಗಿದಿದೆ.", "slot_none": "ನಿಮಗೆ ಇನ್ನೂ ಸ್ಲಾಟ್ ಇಲ್ಲ. ಸ್ಲಾಟ್ ಬುಕ್ ಮಾಡಿ ಎಂದು ಹೇಳಿ.",
  "late_soon": "ನೀವು ತಡವಾಗಿಲ್ಲ. ಸ್ಲಾಟ್ {time}, {gate} ನಲ್ಲಿ, {m} ನಲ್ಲಿ ಶುರು.",
  "late_now": "ನಿಮ್ಮ ಸ್ಲಾಟ್ ಈಗ ತೆರೆದಿದೆ. ಬೇಗ {gate} ಗೆ ಹೋಗಿ.",
  "late_past": "ನಿಮ್ಮ ಸ್ಲಾಟ್ ಸಮಯ ಮುಗಿದಿದೆ. ಸ್ಲಾಟ್ ಬುಕ್ ಮಾಡಿ ಎಂದು ಹೇಳಿ, ಹೊಸದನ್ನು ನೋಡುತ್ತೇನೆ.",
  "fac": "{fac}: {stops}.{near}", "near": " ನಿಮಗೆ ಹತ್ತಿರ: {stop}.", "ask_pos": " ನೀವು ಯಾವ ಸ್ಥಳ ತಲುಪಿದ್ದೀರಿ ಎಂದು ಹೇಳಿ, ಹತ್ತಿರದದ್ದನ್ನು ಹೇಳುತ್ತೇನೆ.",
  "where_unk": "ನೀವು ಎಲ್ಲಿದ್ದೀರಿ ಎಂದು ನನಗೆ ಇನ್ನೂ ಗೊತ್ತಿಲ್ಲ. ಯಾವ ಸ್ಥಳ ತಲುಪಿದ್ದೀರಿ: {stops}? ಹೇಳಿ, ಅಥವಾ ನಕ್ಷೆಯಲ್ಲಿ ತಟ್ಟಿ.",
  "elder": "ಹಿರಿಯರಿಗೆ ವೀಲ್‌ಚೇರ್ ಸಹಾಯ {w} ನಲ್ಲಿ ಇದೆ, ವಿಶ್ರಾಂತಿ ಸ್ಥಳಗಳು {r} ನಲ್ಲಿ. ಕೌಂಟರ್‌ನ ಸ್ವಯಂಸೇವಕರೂ ಸಹಾಯ ಮಾಡುತ್ತಾರೆ.",
  "distress": "ಶಾಂತವಾಗಿರಿ. ಹತ್ತಿರದ ಸ್ವಯಂಸೇವಕರ ಬಳಿ ಅಥವಾ {info} ನ ಮಾಹಿತಿ ಕೌಂಟರ್‌ಗೆ ಹೋಗಿ. ಸ್ವಯಂಸೇವಕರ ಪರದೆಯಲ್ಲಿ ಸಹಾಯ ಟಿಪ್ಪಣಿ ಇಟ್ಟಿದ್ದೇನೆ.",
  "fee": "ಶುಲ್ಕ ಇಲ್ಲ. ಬುಕಿಂಗ್ ಉಚಿತ, ಹಣ ಎಂದಿಗೂ ಕೇಳುವುದಿಲ್ಲ. ಸ್ಲಾಟ್ ಇಲ್ಲಿ ಅಥವಾ ಸ್ಪಾಟ್ ಕೌಂಟರ್‌ನಲ್ಲಿ ಮಾತ್ರ. ಯಾರಿಗೂ ಹಣ ಕೊಡಬೇಡಿ.",
  "carry": "ಕುಡಿಯುವ ನೀರು, ಹಗುರ ಬಟ್ಟೆ, ಬೇಕಾದ ಔಷಧಿ ಒಯ್ಯಿರಿ. ಚೀಲ ಚಿಕ್ಕದಿರಲಿ. ಕ್ಲೋಕ್ ರೂಮ್ {c} ನಲ್ಲಿ ಇದೆ.",
  "about": "ಜನಸಂದಣಿಯ ಪುಣ್ಯಕ್ಷೇತ್ರಕ್ಕಾಗಿ ಮಾದರಿ ಸಹಾಯಕ ನಾನು. ಕಾಯುವ ಸಮಯ, ದಾರಿ, ನಿಮ್ಮ ಸ್ಲಾಟ್ ಹೇಳುತ್ತೇನೆ, ಸ್ಲಾಟ್ ಬುಕ್ ಮಾಡಬಲ್ಲೆ. ಡೇಟಾ ನಕಲಿ, ಸಿಮ್ಯುಲೇಟೆಡ್.",
  "unknown": "ನನ್ನ ಬಳಿ ಆ ಮಾಹಿತಿ ಇಲ್ಲ, ದಯವಿಟ್ಟು ಕೌಂಟರ್‌ನ ಸ್ವಯಂಸೇವಕರನ್ನು ಕೇಳಿ.",
  "goodbye": "ಸರಿ, ಜಾಗ್ರತೆ.", "ask_new_time": "ಹೊಸ ಸಮಯ ಹೇಳಿ, ಉದಾಹರಣೆಗೆ ನಾಳೆ ಬೆಳಿಗ್ಗೆ.",
  "cancelled": "ಸರಿ. ನಿಮ್ಮ ಬುಕಿಂಗ್ ರದ್ದಾಗಿದೆ.", "cancel_none": "ರದ್ದು ಮಾಡಲು ಬುಕಿಂಗ್ ಇಲ್ಲ."},
}


def T(lang, key, **kw):
    return (TPL.get(lang) or TPL["en"]).get(key, TPL["en"][key]).format(**kw)


# ------------------------------------------------------------------ keywords
def _w(low, words):
    """Latin words match on word starts, other scripts as substrings."""
    for w in words:
        if w.isascii():
            if re.search(r"(?<![a-z])" + re.escape(w), low):
                return True
        elif w in low:
            return True
    return False


K = {
 "distress": ["lost my", "lost our", "lost her", "lost him", "i am lost", "i'm lost", "missing", "can't find my", "cannot find my", "emergency", "ambulance",
              "fainted", "collapsed", "heart attack", "bleeding", "accident", "help me", "tappipoy", "kaanavillai", "kanavillai", "kaananilla", "kaanaanilla",
              "kaanathaay", "kho gaya", "kho gayi", "kho gaye", "khoo gaya", "kanapadatam", "खो गया", "खो गई", "खो गए", "गुम", "बेहोश", "आपातकाल", "मदद करो",
              "తప్పిపోయ", "కనపడ", "స్పృహ", "ప్రమాదం", "காணவில்லை", "தொலைந்", "மயக்கம்", "அவசர", "விபத்து", "കാണാനില്ല", "കാണാതായി", "നഷ്ടപ്പെട്ടു",
              "ബോധം", "അടിയന്തര", "അപകടം", "ಕಾಣೆಯಾ", "ಕಳೆದು", "ಪ್ರಜ್ಞೆ", "ತುರ್ತು", "ಅಪಘಾತ",
              "കാണുന്നില്ല", "കുട്ടിയെ കാണ", "காணவில்லை", "కనిపించడం", "కనబడ", "ಕಾಣುತ್ತಿಲ್ಲ", "ಕಾಣ್ತಿಲ್ಲ", "नहीं मिल रहा", "नहीं मिल रही", "दिख नहीं रहा", "दिख नहीं रही",
              "nahi mil raha", "nahi mil rahi", "kanapadatledu", "kanapadatla", "kaanunnilla", "kaanunilla", "kaanala", "kaanapadala", "kanpadala", "kaanuttilla", "bacha kho", "baccha kho"],
 "water": ["water", "drinking", "thirst", "paani", "pani ", "neellu", "neeru", "vellam", "thanneer", "tanni", "kudineer", "पानी", "पीने", "വെള്ളം", "കുടിവെള്ളം",
           "தண்ணீர்", "குடிநீர்", "నీళ్", "నీరు", "తాగునీరు", "ನೀರು"],
 "toilet": ["toilet", "restroom", "washroom", "bathroom", "latrine", "शौचालय", "टॉयलेट", "ടോയ്‌ലറ്റ്", "ടോയ്ലറ്റ്", "ടോയിലറ്റ്", "கழிப்பறை", "டாய்லெட்", "టాయిలెట్",
            "మరుగుదొడ్డి", "ಶೌಚಾಲಯ", "ಟಾಯ್ಲೆಟ್"],
 "medical": ["medical", "doctor", "first aid", "clinic", "hospital", "medicine", "डॉक्टर", "चिकित्सा", "मेडिकल", "ഡോക്ടർ", "മെഡിക്കൽ", "ചികിത്സ", "மருத்துவ", "டாக்டர்",
             "వైద్య", "డాక్టర్", "మెడికల్", "ವೈದ್ಯ", "ಡಾಕ್ಟರ್", "ಮೆಡಿಕಲ್"],
 "rest": ["rest area", "resting", "bench", "sit down", "विश्राम", "വിശ്രമ", "ஓய்வு", "విశ్రాంతి", "ವಿಶ್ರಾಂತಿ"],
 "wheelchair": ["wheelchair", "wheel chair", "व्हीलचेयर", "വീൽചെയർ", "വീൽ ചെയർ", "வீல்சேர்", "வீல் சேர்", "వీల్ చైర్", "వీల్‌చైర్", "ವೀಲ್ ಚೇರ್", "ವೀಲ್‌ಚೇರ್"],
 "cloak": ["cloak", "luggage", "locker", "baggage", "bag deposit", "क्लोक", "सामान", "ക്ലോക്ക്", "ലഗേജ്", "கிளாக்", "லக்கேஜ்", "క్లోక్", "లగేజ్", "ಕ್ಲೋಕ್", "ಲಗೇಜ್"],
 "lost_found": ["lost and found", "lost & found", "खोया पाया"],
 "info": ["information", "info counter", "help desk", "helpdesk", "counter", "सूचना", "काउंटर", "ഇൻഫർമേഷൻ", "കൗണ്ടർ", "தகவல்", "கவுண்டர்", "సమాచార", "కౌంటర్", "ಮಾಹಿತಿ", "ಕೌಂಟರ್"],
 "fee": ["fee", "pay ", "payment", "charge", "cost", "price", "money", "free of", "is it free", "paise", "पैसे", "शुल्क", "फीस", "भुगतान", "പണം", "ഫീസ്", "ചാർജ്",
         "கட்டணம்", "பணம்", "ఫీజు", "డబ్బు", "ఛార్జి", "ಶುಲ್ಕ", "ಹಣ", "ಫೀಸ್"],
 "carry": ["carry", "bring", "pack", "what to take", "should i take", "ले जाना", "साथ में", "കൊണ്ടുപോ", "കരുതേ", "கொண்டு", "எடுத்து", "తీసుకు", "ತೆಗೆದುಕೊಂಡು", "ಒಯ್ಯ"],
 "about": ["what is this", "who are you", "what can you do", "what do you do", "this app", "यह क्या", "यह ऐप", "ഇത് എന്താണ്", "ഈ ആപ്പ്", "ഇതെന്താണ്", "இது என்ன", "ఇది ఏమిటి",
           "ఈ యాప్", "ಇದು ಏನು", "ಈ ಆಪ್"],
 "crowd": ["crowd", "busy", "rush", "भीड़", "തിരക്ക്", "கூட்டம்", "రద్దీ", "ಜನಸಂದಣಿ"],
 "best": ["shortest", "least", "lowest", "minimum", "fastest", "quickest", "best gate", "which gate", "less crowded", "sabse kam", "सबसे कम", "ഏറ്റവും കുറവ്", "കുറവ്",
          "குறைவு", "குறைந்த", "తక్కువ", "ಕಡಿಮೆ"],
 "next": ["next", "where do i go", "where should i go", "what now", "go next", "आगे", "अगला", "ഇനി", "അടുത്ത", "அடுத்த", "తర్వాత", "తరువాత", "ಮುಂದೆ", "ಮುಂದಿನ",
          "kahan jaun", "enga poga", "ekkada vell", "evide pok", "elli hog", "कहाँ जाऊ", "कहां जाऊ", "कहाँ जाना", "कहां जाना", "എവിടെ പോകണം", "எங்கே போக", "ఎక్కడికి వెళ్ళ"],
 "distance": ["how far", "distance", "walk to", "far from", "कितनी दूर", "दूर", "ദൂരം", "தூரம்", "దూరం", "ದೂರ", "dooram", "dhooram", "duram"],
 "wait": ["wait", "how long", "queue", "line", "delay", "sepu", "sepa", "neram", "nerm", "kathirippu", "kaathirippu", "kitna time", "kitni der", "इंतज़ार", "इंतजार",
          "कितना समय", "कितनी देर", "എത്ര സമയം", "കാത്തിരിപ്പ്", "കാത്തിരി", "എത്ര നേരം", "எவ்வளவு நேரம்", "காத்திருப்பு", "காத்திரு", "வரிசை", "ఎంత సమయం", "వేచి",
          "క్యూ", "ఎంత సేపు", "ಎಷ್ಟು ಸಮಯ", "ಕಾಯ", "ಸರತಿ", "ಎಷ್ಟು ಹೊತ್ತು"],
 "slot": ["slot", "booking", "my ticket", "स्लॉट", "बुकिंग", "സ്ലോട്ട്", "ബുക്കിംഗ്", "ஸ்லாட்", "பதிவு", "స్లాట్", "బుకింగ్", "ಸ್ಲಾಟ್", "ಬುಕ್ಕಿಂಗ್", "ಬುಕಿಂಗ್"],
 "late": ["late", "delay", "miss my", "missed", "देर", "लेट", "വൈകി", "താമസ", "தாமத", "லேட்", "ఆలస్యం", "లేట్", "ತಡ", "ಲೇಟ್"],
 "change": ["change", "reschedule", "different time", "another time", "बदल", "മാറ്റ", "மாற்ற", "మార్చ", "ಬದಲ"],
 "cancel": ["cancel", "रद्द", "कैंसल", "റദ്ദ", "ക്യാൻസൽ", "ரத்து", "கேன்சல்", "రద్దు", "క్యాన్సల్", "ರದ್ದು", "ಕ್ಯಾನ್ಸಲ್"],
 "bookverb": ["book a", "book me", "book my", "book it", "book slot", "i want a slot", "i need a slot", "get me a slot", "reserve", "बुक कर", "बुक करो", "ബുക്ക് ചെയ്യ", "புக் பண்ண",
              "புக் செய்", "பதிவு செய்", "బుక్ చేయ", "ಬುಕ್ ಮಾಡ"],
 "bye": ["thank", "bye", "goodbye", "that's all", "धन्यवाद", "शुक्रिया", "നന്ദി", "நன்றி", "ధన్యవాదాలు", "ಧನ್ಯವಾದ"],
 "want": ["want", "need", "get me", "chahiye", "chaahiye", "kavali", "venum", "venam", "beku", "चाहिए", "కావాలి", "வேண்டும்", "വേണം", "ಬೇಕು"],
 "walk": ["walk", "चल", "നടക്ക", "நடக்க", "నడవ", "ನಡೆ"],
 "elderw": ["senior", "grandmother", "grandfather", "ಹಿರಿಯ", "పెద్ద", "முதியோர்", "முதியவர்", "बड़े बुज़ुर्ग", "बड़े बुजुर्ग", "elder", "old", "cannot walk", "can't walk", "disabled", "tired", "weak", "बुज़ुर्ग", "बुजुर्ग", "മുതിർന്ന", "വയസ്സായ", "முதியவ", "வயதான", "పెద్దవార", "ವಯಸ್ಸಾದ"],
}
POS_LAT = re.compile(r"\b(i\s*(am|m|'m|’m)\s+(now\s+|just\s+)?(at|in|near|reaching|standing)|i\s*have\s+reached|reached|arrived|reaching|came to|now at|am at|"
                     r"i'?m at|im at|vachanu|vachaanu|vacchanu|vachhanu|vachesanu|vannu|vandhen|vanthen|vandhuten|vanthuten|vanduten|pahunch|pahuncha|aa gaya|aagaya|ethi|ethiyi|etthi|ettiyi|"
                     r"bandhe|bandhidde|talupide|unnanu|irukken|irukiren|ivide|here at)\b")
POS_IND = ["చేరుకున్న", "వచ్చాను", "వచ్చేశాను", "వచ్చాం", "ఉన్నాను", "వచ్చా", "வந்துவிட்டேன்", "வந்துட்டேன்", "வந்தேன்", "இருக்கிறேன்", "இருக்கேன்", "வந்து சேர்ந்",
           "എത്തി", "ഇവിടെയാണ്", "ഇവിടെ ആണ്", "ತಲುಪಿ", "ಬಂದಿದ್ದೇನೆ", "ಬಂದೆ", "ಇದ್ದೇನೆ", "पहुँच", "पहुंच", "आ गया", "आ गई", "आ गए", "पर हूँ", "पे हूँ", "में हूँ", "यहाँ हूँ", "यहां हूं"]
FROM_HERE = ["from here", "इधर से", "यहाँ से", "यहां से", "ഇവിടെ നിന്ന്", "ഇവിടുന്ന്", "இங்கிருந்து", "ఇక్కడి నుండి", "ఇక్కడ నుండి", "ಇಲ್ಲಿಂದ"]


# ------------------------------------------------------------------ state
_state_lock = threading.Lock()
_pos = {}      # uid -> gate id
_hist = {}     # uid -> [(role, text)]
_cache = {}    # (lang, text, digest) -> (ts, result fields)
CACHE_S = 20


def reset():
    with _state_lock:
        _pos.clear(); _hist.clear(); _cache.clear()


def get_position(uid):
    return _pos.get(uid)


def set_position(uid, gid):
    if gid in ORDER:
        _pos[uid] = gid


def _mins(n, lang):
    return f"{n} {UNIT.get(lang, UNIT['en'])}"


def walk_between(a, b):
    """Simulated walking minutes along the route between two stops."""
    i, j = ORDER.index(a), ORDER.index(b)
    lo, hi = sorted((i, j))
    return sum(WALK[(ORDER[k], ORDER[k + 1])] for k in range(lo, hi))


def _gates():
    return {g["id"]: g for g in queue_sim.snapshot()["gates"]}


def progress(pos):
    out = []
    pi = ORDER.index(pos) if pos in ORDER else -1
    for i, gid in enumerate(ORDER):
        st = "here" if i == pi else "done" if i < pi else "next" if i == pi + 1 else "todo"
        out.append({"id": gid, "name": queue_sim.BY_ID[gid]["name"], "state": st})
    return out


def _slot(uid):
    try:
        import slots
        return slots.get(uid), slots
    except Exception:
        return None, None


def _slot_state(slot, slots_mod):
    """'soon' (minutes), 'now' or 'past' for the pilgrim's window."""
    try:
        now = slots_mod.NOW()
        start, w = slot["window"], slots_mod._window_s()
        if now < start:
            return "soon", max(1, int(round((start - now) / 60)))
        if now < start + w:
            return "now", 0
        return "past", 0
    except Exception:
        return "soon", 0


def _slot_sentence(uid, lang):
    slot, sm = _slot(uid)
    if not slot:
        return ""
    return " " + T(lang, "slot_info", time=directions.say_time(lang, slot["window"]), gate=gatematch.display(slot["gate"], lang), state="").strip()


def facts(uid, lang="en"):
    """Compact facts block for the model (and a record of every legal number)."""
    gs = _gates()
    pos = _pos.get(uid)
    lines = ["SIMULATED data for a prototype crowded-shrine assistant. Not real. Route order and live waits:"]
    for i, gid in enumerate(ORDER):
        g = gs[gid]
        nxt = f", walk to next stop {WALK[(gid, ORDER[i + 1])]} min" if i < len(ORDER) - 1 else ", last stop"
        lines.append(f"{i + 1}. {gid} {g['name']}: wait {g['wait_min']} min, load {int(g['load'] * 100)} percent{nxt}; "
                     f"facilities: {', '.join(FACILITIES[gid])}")
    lines += route_facts.facts_lines()
    if pos:
        rem = route_facts.remaining_from(pos, (_slot(uid)[0] or {}).get("gate"))
        lines.append(f"Still ahead from {queue_sim.BY_ID[pos]['name']}: {rem['steps']} steps, {rem['distance_m']} m, {rem['minutes']} min, {rem['climb_m']} m climb.")
    lines.append("Facility types: water, toilet, medical post, rest area, wheelchair help, cloak room, lost_found, info counter (information counter).")
    mode = "rush, slots are staggered" if _rush() else "normal"
    lines.append(f"Mode: {mode}.")
    lines.append(f"Pilgrim position: {pos + ' ' + queue_sim.BY_ID[pos]['name'] if pos else 'unknown'}.")
    slot, sm = _slot(uid)
    if slot:
        st, n = _slot_state(slot, sm)
        lines.append(f"Pilgrim slot: {slot['label']} at {slot['gate']} {slot['gate_name']} ({st}{', ' + str(n) + ' min' if n else ''}).")
    else:
        lines.append("Pilgrim slot: none.")
    lines.append("Rules: everything is free, no payment is ever asked; slots are booked only in this app or at the spot counter; data is simulated; "
                 "no temple is named; never promise police or ambulance.")
    return "\n".join(lines)


def _rush():
    try:
        import flags
        return flags.slot_mode() == "staggered" or queue_sim.rush_on()
    except Exception:
        return queue_sim.rush_on()


def _allowed_numbers(uid):
    nums = set()
    for n in re.findall(r"\d+", facts(uid)):
        nums.add(n)
    nums.update({"1", "2", "3", "4", "5"})
    return nums


# ------------------------------------------------------------------ rules
def _stops_with(ftype, lang):
    return ", ".join(gatematch.display(g, lang) for g in ORDER if ftype in FACILITIES[g])


def _nearest(ftype, pos):
    c = [g for g in ORDER if ftype in FACILITIES[g]]
    return min(c, key=lambda g: walk_between(pos, g)) if c and pos else None


def _res(intent, reply, lang, uid, gate_id=None, action="none", show="none", via="rules", **more):
    pos = _pos.get(uid)
    return {"intent": intent, "reply": reply, "gate_id": gate_id, "position_gate_id": pos, "progress": progress(pos), "show": show,
            "action": action, "via": via, "lang": lang, "llm_ms": 0, **more}


WHERE_AM_I = re.compile(r"\b(where am i|where i am|which (step|stop|stage|place|point) (am i|i am)|what (step|stop) am i|my (location|position))\b", re.I)


def ask_position(uid, lang):
    """Position unknown (there is no GPS): ask which stop the pilgrim has reached instead of a dead-end answer."""
    return _res("position", T(lang, "where_unk", stops=", ".join(gatematch.display(g, lang) for g in ORDER)), lang, uid, show="map")


def _pos_reply(uid, lang):
    gs, pos = _gates(), _pos[uid]
    i = ORDER.index(pos)
    sl = _slot_sentence(uid, lang)
    if i == len(ORDER) - 1:
        return T(lang, "pos_last", pos=gatematch.display(pos, lang), wait=_mins(gs[pos]["wait_min"], lang), slot=sl), None
    nx = ORDER[i + 1]
    return T(lang, "pos_next", pos=gatematch.display(pos, lang), nxt=gatematch.display(nx, lang), walk=_mins(WALK[(pos, nx)], lang),
             wait=_mins(gs[nx]["wait_min"], lang), slot=sl), nx


# ------------------------------------------------------------------ effort questions (steps, distance, climb, ramp)
_EFF_TPL = {
 "en": {"ramp_no": "There is no wheelchair route from {pos} to {b}; volunteers offer carrying help.", "from": "From {pos} to the shrine: about {steps} steps, {dist}, and {mins} of walking.",
        "unk": "I do not know where you are, so counting from {pos}: about {steps} steps, {dist}, and {mins} of walking to the shrine.",
        "hard": " The steepest part is between {a} and {b}: {hs} steps. Rest shelters: {rest}.", "flat": " There is no steep part ahead.",
        "ramp_all": "Yes, a wheelchair route exists from {pos} all the way to the shrine.",
        "ramp_part": "A wheelchair route exists from {pos} up to {a}, but not between {a} and {b}, where volunteers offer carrying help.",
        "km": "km", "m": "metres", "shrine": "the shrine"},
 "hi": {"ramp_no": "{pos} से {b} तक व्हीलचेयर का रास्ता नहीं है; स्वयंसेवक उठाकर ले जाने में मदद करते हैं।", "from": "{pos} से दर्शन स्थल तक लगभग {steps} सीढ़ियाँ, {dist} और {mins} पैदल चलना है।",
        "unk": "मुझे नहीं पता आप कहाँ हैं, इसलिए {pos} से गिनती: लगभग {steps} सीढ़ियाँ, {dist} और {mins} पैदल।",
        "hard": " सबसे खड़ी चढ़ाई {a} और {b} के बीच है: {hs} सीढ़ियाँ। विश्राम स्थल: {rest}।", "flat": " आगे कोई खड़ी चढ़ाई नहीं है।",
        "ramp_all": "हाँ, {pos} से दर्शन स्थल तक व्हीलचेयर का रास्ता है।",
        "ramp_part": "{pos} से {a} तक व्हीलचेयर का रास्ता है, पर {a} और {b} के बीच नहीं; वहाँ स्वयंसेवक उठाकर ले जाने में मदद करते हैं।",
        "km": "किमी", "m": "मीटर", "shrine": "दर्शन स्थल"},
 "ml": {"ramp_no": "{pos} മുതൽ {b} വരെ വീൽചെയർ വഴിയില്ല; സന്നദ്ധപ്രവർത്തകർ ചുമന്ന് സഹായിക്കും.", "from": "{pos} മുതൽ ദർശന സ്ഥലം വരെ ഏകദേശം {steps} പടികൾ, {dist}, {mins} നടക്കണം.",
        "unk": "നിങ്ങൾ എവിടെയാണെന്ന് അറിയില്ല, അതിനാൽ {pos} മുതൽ കണക്കാക്കുന്നു: ഏകദേശം {steps} പടികൾ, {dist}, {mins} നടത്തം.",
        "hard": " ഏറ്റവും കുത്തനെയുള്ളത് {a}നും {b}നും ഇടയിലാണ്: {hs} പടികൾ. വിശ്രമ സ്ഥലങ്ങൾ: {rest}.", "flat": " മുന്നിൽ കുത്തനെയുള്ള ഭാഗമില്ല.",
        "ramp_all": "ഉണ്ട്, {pos} മുതൽ ദർശന സ്ഥലം വരെ വീൽചെയർ വഴിയുണ്ട്.",
        "ramp_part": "{pos} മുതൽ {a} വരെ വീൽചെയർ വഴിയുണ്ട്, {a}നും {b}നും ഇടയിൽ ഇല്ല; അവിടെ സന്നദ്ധപ്രവർത്തകർ ചുമന്ന് സഹായിക്കും.",
        "km": "കിലോമീറ്റർ", "m": "മീറ്റർ", "shrine": "ദർശന സ്ഥലം"},
 "ta": {"ramp_no": "{pos} இலிருந்து {b} வரை சக்கர நாற்காலி பாதை இல்லை; தன்னார்வலர்கள் தூக்கிச் செல்ல உதவுவார்கள்.", "from": "{pos} இலிருந்து தரிசன இடம் வரை சுமார் {steps} படிகள், {dist}, {mins} நடக்க வேண்டும்.",
        "unk": "நீங்கள் எங்கே இருக்கிறீர்கள் என்று தெரியாது, அதனால் {pos} இலிருந்து கணக்கிடுகிறேன்: சுமார் {steps} படிகள், {dist}, {mins} நடை.",
        "hard": " மிகச் செங்குத்தானது {a} மற்றும் {b} இடையே: {hs} படிகள். ஓய்வு இடங்கள்: {rest}.", "flat": " முன்னால் செங்குத்தான பகுதி இல்லை.",
        "ramp_all": "ஆம், {pos} இலிருந்து தரிசன இடம் வரை சக்கர நாற்காலி பாதை உள்ளது.",
        "ramp_part": "{pos} முதல் {a} வரை சக்கர நாற்காலி பாதை உள்ளது, {a} மற்றும் {b} இடையே இல்லை; அங்கு தன்னார்வலர்கள் தூக்கிச் செல்ல உதவுவார்கள்.",
        "km": "கிலோமீட்டர்", "m": "மீட்டர்", "shrine": "தரிசன இடம்"},
 "te": {"ramp_no": "{pos} నుండి {b} వరకు వీల్‌చైర్ దారి లేదు; వాలంటీర్లు మోసుకెళ్ళి సహాయం చేస్తారు.", "from": "{pos} నుండి దర్శన స్థలం వరకు సుమారు {steps} మెట్లు, {dist}, {mins} నడక.",
        "unk": "మీరు ఎక్కడ ఉన్నారో తెలియదు, అందుకే {pos} నుండి లెక్కిస్తున్నాను: సుమారు {steps} మెట్లు, {dist}, {mins} నడక.",
        "hard": " అత్యంత నిటారుగా ఉండేది {a}, {b} మధ్య: {hs} మెట్లు. విశ్రాంతి స్థలాలు: {rest}.", "flat": " ముందు నిటారు భాగం లేదు.",
        "ramp_all": "అవును, {pos} నుండి దర్శన స్థలం వరకు వీల్‌చైర్ దారి ఉంది.",
        "ramp_part": "{pos} నుండి {a} వరకు వీల్‌చైర్ దారి ఉంది, {a}, {b} మధ్య లేదు; అక్కడ వాలంటీర్లు మోసుకెళ్ళి సహాయం చేస్తారు.",
        "km": "కిలోమీటర్లు", "m": "మీటర్లు", "shrine": "దర్శన స్థలం"},
 "kn": {"ramp_no": "{pos} ನಿಂದ {b} ವರೆಗೆ ಗಾಲಿಕುರ್ಚಿ ದಾರಿ ಇಲ್ಲ; ಸ್ವಯಂಸೇವಕರು ಹೊತ್ತುಕೊಂಡು ಸಹಾಯ ಮಾಡುತ್ತಾರೆ.", "from": "{pos} ನಿಂದ ದರ್ಶನ ಸ್ಥಳದವರೆಗೆ ಸುಮಾರು {steps} ಮೆಟ್ಟಿಲುಗಳು, {dist}, {mins} ನಡಿಗೆ.",
        "unk": "ನೀವು ಎಲ್ಲಿದ್ದೀರಿ ಎಂದು ಗೊತ್ತಿಲ್ಲ, ಆದ್ದರಿಂದ {pos} ನಿಂದ ಎಣಿಸುತ್ತೇನೆ: ಸುಮಾರು {steps} ಮೆಟ್ಟಿಲುಗಳು, {dist}, {mins} ನಡಿಗೆ.",
        "hard": " ಅತಿ ಕಡಿದಾದದ್ದು {a} ಮತ್ತು {b} ನಡುವೆ: {hs} ಮೆಟ್ಟಿಲುಗಳು. ವಿಶ್ರಾಂತಿ ಸ್ಥಳಗಳು: {rest}.", "flat": " ಮುಂದೆ ಕಡಿದಾದ ಭಾಗವಿಲ್ಲ.",
        "ramp_all": "ಹೌದು, {pos} ನಿಂದ ದರ್ಶನ ಸ್ಥಳದವರೆಗೆ ಗಾಲಿಕುರ್ಚಿ ದಾರಿ ಇದೆ.",
        "ramp_part": "{pos} ನಿಂದ {a} ವರೆಗೆ ಗಾಲಿಕುರ್ಚಿ ದಾರಿ ಇದೆ, {a} ಮತ್ತು {b} ನಡುವೆ ಇಲ್ಲ; ಅಲ್ಲಿ ಸ್ವಯಂಸೇವಕರು ಹೊತ್ತುಕೊಂಡು ಸಹಾಯ ಮಾಡುತ್ತಾರೆ.",
        "km": "ಕಿಲೋಮೀಟರ್", "m": "ಮೀಟರ್", "shrine": "ದರ್ಶನ ಸ್ಥಳ"},
}


def _nfd(s):
    return unicodedata.normalize("NFD", s)


_STEP_STEMS = [_nfd(x) for x in (
    "steps", "stairs", "staircase", "mettlu", "metlu", "mettu", "mettulu", "mettilu", "padi", "padikal", "padigal", "padikkal", "sidhi", "seedhi", "sidhiyan",
    "మెట్ల", "మెట్టు", "படி", "பட", "പടി", "ಮೆಟ್ಟಿಲ", "ಮೆಟ್ಟು", "सीढ़", "सीढ", "कदम")]
_QTY = [_nfd(x) for x in ("how many", "how much", "how far", "how long", "kitni", "kitne", "kitna", "enni", "ethra", "etra", "ethanai", "entha", "eshtu",
                         "कितन", "ఎన్ని", "ఎంత", "எத்தனை", "எவ்வளவு", "എത്ര", "ಎಷ್ಟು")]
_CLIMB = [_nfd(x) for x in ("climb", "uphill", "chadh", "ekka", "ērra", "yera", "kayara", "hatta", "चढ़", "चढ", "ఎక్క", "ஏற", "കയറ", "ಹತ್ತ", "ಏರ")]
_WALKW = [_nfd(x) for x in ("walk", "trek", "नडक", "पैदल", "चलना", "चलने", "నడ", "நட", "നട", "ನಡ")]
_DISTW = [_nfd(x) for x in ("distance", "dooram", "dhooram", "duram", "thooram", "door", "दूर", "దూరం", "தூரம்", "ദൂരം", "ದೂರ")]
_FARW = [_nfd(x) for x in ("how far", "kitni door", "कितनी दूर", "कितना दूर", "ఎంత దూరం", "எவ்வளவு தூரம்", "എത്ര ദൂരം", "ಎಷ್ಟು ದೂರ", "dooram", "duram")]
_EFF_RE = re.compile(
    r"how many (steps|stairs|km|kilometres|kilometers|metres|meters|minutes)|(steps|stairs) (are |do i )?(left|remain|remaining|to go|ahead|more|to climb|have)|"
    r"how much (climb|climbing|walking|walk|uphill|more)|how (long|many hours?|many minutes) .{0,25}(walk|climb|trek|reach|get to|take to)|walking time|"
    r"how (high|steep)|\bsteep\b|\bsteepness\b|is it (a )?(hard|tough|difficult|tiring|long|easy) (climb|walk|trek)|(hard|tough|difficult|tiring) (to )?(climb|walk)|"
    r"(can|will|could) (my|our|an|the|a) [a-z ]{0,25}(manage|climb|cope|walk|do it)|too much (climb|climbing|walking)|(steps|stairs) left|steps to climb|"
    r"\bsteps\b.{0,25}\b(climb|left|ahead|shrine|top)\b|\b(climb|walk)\b.{0,20}\bsteps\b|how far")
_RAMP_RE = re.compile(r"\bramp\b|wheelchair (route|path|access|way|possible|friendly)|wheel chair (route|path|access|way)|wheelchair.{0,25}(go up|reach|climb|manage|possible)")
_RAMP_L = [_nfd(x) for x in ("रैंप", "रेंप", "व्हीलचेयर का रास्ता", "व्हील चेयर का रास्ता", "റാമ്പ്", "വീൽചെയർ വഴി", "வீல்சேர் பாதை", "சாய்தளம்", "ரேம்ப்",
                             "சக்கர நாற்காலி பாதை", "ర్యాంప్", "వీల్‌చైర్ దారి", "వీల్ చైర్ దారి", "వీల్‌చైర్ మార్గం", "ರ್ಯಾಂಪ್", "ಗಾಲಿಕುರ್ಚಿ ದಾರಿ", "ವೀಲ್‌ಚೇರ್ ದಾರಿ")]
_STEEP_L = [_nfd(x) for x in ("खड़ी चढ़", "चढ़ाई", "నిటారు", "செங்குத்து", "കുത്തനെ", "കയറ്റം", "ಕಡಿದಾದ")]
_MAINSTEPS = re.compile(r"main\s*steps?|mainstep|mensteps|मेन\s*स्टेप|मुख्य\s*सीढ़|മെയിൻ\s*സ്റ്റെപ്|மெயின்\s*ஸ்டெப்|మెయిన్\s*స్టెప్|ಮೇನ್\s*ಸ್ಟೆಪ್")


def _has_any(e, words):
    return any(w in e for w in words)


def _effort_kind(low):
    """'ramp', 'far' (a bare distance question), 'main' or None. Works on the normalised text of any of the six languages."""
    low = _MAINSTEPS.sub(" mainstop ", low)      # the stop's own name is not a question about steps
    e = _nfd(low)
    if _RAMP_RE.search(low) or _has_any(e, _RAMP_L):
        return "ramp"
    if _EFF_RE.search(low):
        return "far" if "how far" in low and not re.search(r"steps|stairs|climb|walk|steep", low) else "main"
    q = _has_any(e, _QTY)
    if q and _has_any(e, _FARW) and not _has_any(e, _STEP_STEMS + _CLIMB):
        return "far"
    if q and _has_any(e, _STEP_STEMS + _CLIMB + _WALKW + _DISTW):
        return "main"
    if _has_any(e, _STEEP_L) or re.search(r"\b(ethra|etra|enni|kitni|kitne)\b.{0,12}\b(mettlu|metlu|mettu|padi|padikal|padigal|sidhi|seedhi|kadam)", low):
        return "main"
    return None


def _strip_steps(text):
    """Drop the word for 'steps' so it is never read as the stop called Main Steps (unless the stop name itself is said)."""
    if _MAINSTEPS.search(gatematch.norm(text)):
        return text
    stems = [x for x in _STEP_STEMS if x not in ("padi", "பட")] + ["steps", "stairs"]
    keep = [t for t in text.split() if not any(s in _nfd(t.lower()) for s in stems)]
    return " ".join(keep)


def _dist_say(m, lang):
    t = _EFF_TPL.get(lang) or _EFF_TPL["en"]
    return f"{m / 1000:.1f} {t['km']}" if m >= 1000 else f"{m} {t['m']}"


def _effort_reply(kind, lang, uid):
    import route_facts as rf
    t = _EFF_TPL.get(lang) or _EFF_TPL["en"]
    pos = _pos.get(uid)
    slot, _sm = _slot(uid)
    rem = rf.remaining_from(pos, slot["gate"] if slot else None)
    here = gatematch.display(rem["from"], lang)
    disp = lambda sid: gatematch.display(sid, lang) if sid in ORDER else t["shrine"]   # noqa: E731
    if kind == "ramp":
        i = rf.STOPS.index(rem["from"])
        blocked = next((s for s in rf.STRETCHES[i:] if not s["wheelchair"]), None)
        if not blocked:
            return t["ramp_all"].format(pos=here)
        if blocked["from"] == rem["from"]:
            return t["ramp_no"].format(pos=here, b=disp(blocked["to"]))
        return t["ramp_part"].format(pos=here, a=disp(blocked["from"]), b=disp(blocked["to"]))
    out = (t["from"] if rem["known_position"] else t["unk"]).format(pos=here, steps=rem["steps"], dist=_dist_say(rem["distance_m"], lang), mins=_mins(rem["minutes"], lang))
    h = rem["hardest"]
    if h and h["difficulty"] == "hard":
        rest = ", ".join(gatematch.display(g, lang) for g in rem["shelter_stops"]) or "-"
        out += t["hard"].format(a=disp(h["from"]), b=disp(h["to"]), hs=h["steps"], rest=rest)
    else:
        out += t["flat"]
    return out


_AFTER_W = ["after", "comes after", "के बाद", "बाद में", "കഴിഞ്ഞാൽ", "കഴിഞ്ഞ്", "ശേഷം", "பிறகு", "பின்", "తర్వాత", "తరువాత", "ನಂತರ", "ಆಮೇಲೆ", "ಬಳಿಕ",
            "kazhinjal", "kazhinju", "ke baad", "baad", "piragu", "pirahu", "tarvata", "tharuvata", "nantara", "aamele"]
_AFTER_T = {
 "en": "After {a} comes {b}, {walk} on foot. The wait there is {wait}.", "hi": "{a} के बाद {b} आता है, पैदल {walk}। वहाँ इंतज़ार {wait} है।",
 "ml": "{a} കഴിഞ്ഞാൽ {b} ആണ്, നടക്കാൻ {walk}. അവിടെ കാത്തിരിപ്പ് {wait}.", "ta": "{a} க்குப் பிறகு {b}, நடந்து {walk}. அங்கே காத்திருப்பு {wait}.",
 "te": "{a} తర్వాత {b}, నడవడానికి {walk}. అక్కడ వేచి ఉండే సమయం {wait}.", "kn": "{a} ನಂತರ {b}, ನಡೆಯಲು {walk}. ಅಲ್ಲಿ ಕಾಯುವ ಸಮಯ {wait}.",
}
_AFTER_LAST = {"en": "{a} is the last stop, the shrine itself.", "hi": "{a} आखिरी पड़ाव है।", "ml": "{a} അവസാനത്തെ സ്ഥലമാണ്.", "ta": "{a} கடைசி இடம்.",
               "te": "{a} చివరి చోటు.", "kn": "{a} ಕೊನೆಯ ಸ್ಥಳ."}


def _after_reply(low, found, lang, uid):
    """'what is next after <stop>': answered from the named stop, no position needed."""
    if not found or not _w(low, _AFTER_W):
        return None
    if _w(low, POS_IND) or POS_LAT.search(low):
        return None
    a = found[0][0]
    i = ORDER.index(a)
    if i == len(ORDER) - 1:
        return _res("next", _AFTER_LAST.get(lang, _AFTER_LAST["en"]).format(a=gatematch.display(a, lang)), lang, uid, gate_id=a, show="map")
    b = ORDER[i + 1]
    gs = _gates()
    return _res("next", _AFTER_T.get(lang, _AFTER_T["en"]).format(a=gatematch.display(a, lang), b=gatematch.display(b, lang),
                walk=_mins(WALK[(a, b)], lang), wait=_mins(gs[b]["wait_min"], lang)), lang, uid, gate_id=b, show="map", next_gate_id=b)


def rules(text, lang, uid, session=None):
    """Returns a result dict, or None when the rules cannot classify the text (then the model gets a chance)."""
    low = gatematch.norm(text).strip()
    eff = _effort_kind(low)
    if eff == "far" and any(_w(low, K[f]) for f in ("water", "toilet", "medical", "rest", "cloak", "lost_found", "info")):
        eff = None
    if eff:      # 'how many steps' must not become the stop called Main Steps
        text = _strip_steps(text)
        low = gatematch.norm(text).strip()
    found = gatematch.find_gates(text)
    gs = _gates()
    pos_before = _pos.get(uid)
    # ---- distress first, always
    if _w(low, K["distress"]):
        info_stop = "g1" if "info" in FACILITIES["g1"] else ORDER[0]
        near = _nearest("info", pos_before) or info_stop
        return _res("distress", T(lang, "distress", info=gatematch.display(near, lang)), lang, uid, action="call_volunteer", show="none")
    _ar = _after_reply(low, found, lang, uid)
    if _ar:
        return _ar
    # ---- where the pilgrim says they are
    say_pos = bool(found) and (POS_LAT.search(low) or _w(low, POS_IND))
    target = None
    if say_pos:
        _pos[uid] = found[0][0]
        target = found[1][0] if len(found) > 1 else None
    else:
        named = gatematch.best_gate(text)
        target = named
    pos = _pos.get(uid)
    from_here = _w(low, FROM_HERE)
    has = lambda k: _w(low, K[k])   # noqa: E731
    if eff and not (eff == "far" and target):       # steps, distance, climb, ramp: answered from route_facts
        return _res("effort", _effort_reply(eff, lang, uid), lang, uid, show="map")
    # ---- facilities (a stop name does not turn a facility question into a wait question)
    fac_order = ["lost_found", "wheelchair", "cloak", "medical", "toilet", "water", "rest", "info"]
    fac = next((f for f in fac_order if has(f)), None)
    if fac == "info" and has("fee"):
        fac = None
    if fac and not (has("elderw") and any(r in low for r in directions.RELATIVES)):
        stops = _stops_with(fac, lang)
        n = _nearest(fac, pos)
        near = T(lang, "near", stop=gatematch.display(n, lang)) if n else ("" if _pos.get(uid) else T(lang, "ask_pos"))
        return _res("facility", T(lang, "fac", fac=FAC_LABEL[fac].get(lang) or FAC_LABEL[fac]["en"], stops=stops, near=near), lang, uid,
                    gate_id=n, show="map", facility=fac)
    # ---- elders
    _helpw = ["help", "सहायता", "मदद", "സഹായ", "உதவி", "సహాయ", "సాయం", "ಸಹಾಯ", "madad", "sahayam", "udavi", "sahaya"]
    if (any(r in low for r in directions.RELATIVES) and (has("elderw") or has("walk") or "help" in low)) or (has("elderw") and (_w(low, _helpw) or has("want")) and not has("distress")):
        return _res("help_elder", T(lang, "elder", w=_stops_with("wheelchair", lang), r=_stops_with("rest", lang)), lang, uid, show="map", facility="wheelchair")
    # ---- slot talk
    if has("cancel"):
        return _res("cancel", "", lang, uid, action="cancel", show="slot")
    if has("slot") or has("bookverb"):
        wants = has("want") and not has("late") and not has("change")
        slot, sm = _slot(uid)
        if has("late") or has("change") or has("bookverb") or wants:
            if has("late") and slot and not has("bookverb") and not wants:
                st, n = _slot_state(slot, sm)
                g = gatematch.display(slot["gate"], lang)
                key = {"soon": "late_soon", "now": "late_now", "past": "late_past"}[st]
                return _res("slot_late", T(lang, key, time=directions.say_time(lang, slot["window"]), gate=g, m=_mins(n, lang)), lang, uid,
                            gate_id=slot["gate"], show="slot")
            if has("late") and not slot:
                return _res("slot_late", T(lang, "slot_none"), lang, uid, show="slot")
            if has("change") and not has("bookverb") and not wants:
                return _res("change", "", lang, uid, action="change", show="slot")
            return _res("book", "", lang, uid, action="book", show="slot", gate_id=target)
        if slot:
            st, n = _slot_state(slot, sm)
            state = {"soon": T(lang, "st_soon", m=_mins(n, lang)), "now": T(lang, "st_now"), "past": T(lang, "st_past")}[st]
            return _res("slot_info", T(lang, "slot_info", time=directions.say_time(lang, slot["window"]), gate=gatematch.display(slot["gate"], lang), state=state),
                        lang, uid, gate_id=slot["gate"], show="slot")
        return _res("slot_info", T(lang, "slot_none"), lang, uid, show="slot")
    # ---- policy
    if has("fee"):
        return _res("fee", T(lang, "fee"), lang, uid)
    if has("carry"):
        return _res("carry", T(lang, "carry", c=gatematch.display("g1", lang)), lang, uid)
    if has("about"):
        return _res("about", T(lang, "about"), lang, uid)
    # ---- route questions
    if say_pos and not (target and (has("wait") or has("distance"))):
        reply, nx = _pos_reply(uid, lang)
        return _res("position", reply, lang, uid, gate_id=pos, action="set_position", show="map", next_gate_id=nx)
    if has("best") and (has("wait") or has("crowd") or "gate" in low or "stop" in low or not target):
        best = min(gs.values(), key=lambda g: g["wait_min"])
        return _res("wait_best", T(lang, "wait_best", gate=gatematch.display(best["id"], lang), wait=_mins(best["wait_min"], lang)), lang, uid,
                    gate_id=best["id"], show="map")
    if has("distance") or (has("walk") and target):
        if target and pos:
            return _res("distance", T(lang, "distance", gate=gatematch.display(target, lang), pos=gatematch.display(pos, lang),
                                      walk=_mins(walk_between(pos, target), lang)) if target != pos else T(lang, "pos_last", pos=gatematch.display(pos, lang),
                        wait=_mins(gs[pos]["wait_min"], lang), slot=""), lang, uid, gate_id=target, show="map")
        if target:
            return _res("distance", T(lang, "distance_nopos", gate=gatematch.display(target, lang), first=gatematch.display(ORDER[0], lang),
                                      walk=_mins(walk_between(ORDER[0], target), lang)), lang, uid, gate_id=target, show="map")
    if has("wait") or has("crowd"):
        if target:
            frm = ""
            if pos and pos != target:
                frm = T(lang, "frm", pos=gatematch.display(pos, lang), walk=_mins(walk_between(pos, target), lang))
            return _res("wait_gate", T(lang, "wait_gate", gate=gatematch.display(target, lang), wait=_mins(gs[target]["wait_min"], lang), frm=frm), lang, uid,
                        gate_id=target, show="map")
        if pos and (from_here or has("wait")):
            reply, nx = _pos_reply(uid, lang)
            return _res("position", reply, lang, uid, gate_id=pos, show="map", next_gate_id=nx)
        if has("crowd"):
            hi, lo = max(gs.values(), key=lambda g: g["wait_min"]), min(gs.values(), key=lambda g: g["wait_min"])
            return _res("crowd", T(lang, "crowd", g1=gatematch.display(hi["id"], lang), w1=_mins(hi["wait_min"], lang), g2=gatematch.display(lo["id"], lang),
                                   w2=_mins(lo["wait_min"], lang), rush=T(lang, "rush") if _rush() else ""), lang, uid, show="map")
        lst = ", ".join(f"{gatematch.display(g, lang)} {_mins(gs[g]['wait_min'], lang)}" for g in ORDER)
        return _res("wait_all", T(lang, "wait_all", list=lst), lang, uid, show="map")
    if has("next") or (has("distance") and pos):
        if pos:
            reply, nx = _pos_reply(uid, lang)
            return _res("next", reply, lang, uid, gate_id=nx or pos, show="map", next_gate_id=nx)
        return _res("next", T(lang, "next_nopos", first=gatematch.display(ORDER[0], lang), second=gatematch.display(ORDER[1], lang)), lang, uid,
                    gate_id=ORDER[0], show="map")
    if has("bye"):
        return _res("goodbye", T(lang, "goodbye"), lang, uid)
    if target and not has("wait") and len(low.split()) <= 4:      # a bare stop name: tell its wait
        return _res("wait_gate", T(lang, "wait_gate", gate=gatematch.display(target, lang), wait=_mins(gs[target]["wait_min"], lang), frm=""), lang, uid,
                    gate_id=target, show="map")
    return None


# ------------------------------------------------------------------ model
SYSTEM = ("You are the voice assistant of a prototype crowded-shrine app. Use ONLY the FACTS. Reply in this language: {lang}, one or two short "
          "sentences, natural when spoken, no lists, no symbols. If the facts do not cover the question, reply exactly in that language with: "
          "'I do not have that information, please ask the volunteer at the counter.' Never say stop ids like g1, say the stop name. Never invent numbers, places or promises. If the pilgrim asks where they are or which stop or step they are at, use intent position (leave position_gate_id null unless they name the stop). "
          "Return ONLY JSON: {{\"intent\":\"position|wait_gate|wait_best|next|distance|slot_info|facility|book|change|cancel|distress|unknown\","
          "\"gate_id\":\"g1..g5 or null\",\"position_gate_id\":\"g1..g5 or null (only if the pilgrim says where they are)\",\"reply\":\"...\","
          "\"action\":\"none|book|change|cancel|set_position|call_volunteer\"}}\n\nFACTS:\n{facts}")


def _kb_block(text, lang, uid):
    try:
        import kb
        return kb.facts_for(text, lang, _pos.get(uid))
    except Exception:
        return None


def _kb_answer(text, lang, uid):
    """Rules-only answer from the venue pack (no model call): the top entry's short answer, in the pilgrim's language when we can."""
    try:
        import kb
        hits = kb.search(text, lang, k=1, position_stop_id=_pos.get(uid))
    except Exception:
        return None
    if not hits or hits[0]["score"] < kb.THRESHOLD:
        return None
    if re.search(r"\b(rain|raining|forecast|minister|president|cricket|election|news|stock|movie|film|politic)", (text or "").lower()):
        return None              # off topic: the honest 'I do not have that' line
    ans = re.sub(r"\s*\(g[1-5]\)", "", hits[0]["answer"])          # never read stop ids aloud
    parts = re.split(r"(?<=[.!?])\s", ans)
    ans = parts[0]
    if len(parts) > 1 and not _brief() and len(ans) + len(parts[1]) < 160:   # at most two short sentences, about 160 characters
        ans = ans + " " + parts[1]
    if len(ans) > 200:
        ans = ans[:200].rsplit(" ", 1)[0].rstrip(",;:") + "."
    if lang != "en":
        tr = _translate(ans, lang)
        if not tr:
            return None              # never answer a pilgrim in English they may not read: the safe line instead
        ans = tr
    return ans


_tr_cache = {}


def _translate(text, lang):
    key = (text, lang)
    if key in _tr_cache:
        return _tr_cache[key]
    out = None
    try:
        if sarvam.available():
            out = sarvam.translate(text, lang) if hasattr(sarvam, "translate") else None
            out = getattr(out, "text", out)
    except Exception:
        out = None
    if out:
        _tr_cache[key] = out
    return out


CARE_STRONG = ("medical", "lost_person", "lost_item", "safety_crowd", "harassment_theft", "tout_payment", "staff_behaviour")
CARE_OVERRIDES = (None, "fee", "unknown", "distress", "position", "wait_gate", "goodbye")


def _care(text, lang, uid, r):
    """Open a tracked care request when the words are a real complaint or distress (rules only, no model call).
    Ordinary questions ('where is water', 'my slot') stay with the normal answers."""
    try:
        import addons_care
        cat, urg, _why, conf = addons_care.classify_rules(text)
    except Exception:
        return None
    intent = r["intent"] if r else None
    if not conf or cat not in CARE_STRONG or (urg != "emergency" and intent not in CARE_OVERRIDES):
        return None
    try:
        c = addons_care.from_assistant(text, uid, lang, _pos.get(uid))
    except Exception:
        return None
    if not c or not c.get("reply_text"):
        return None
    distress = intent == "distress" or urg == "emergency" or cat in ("lost_person", "medical", "safety_crowd")
    return _res("distress" if distress else "care", c["reply_text"], lang, uid, action="call_volunteer" if distress else "none",
                show="none", via="care", care_id=c.get("id"), care_urgency=c.get("urgency"), care_category=c.get("category"))


def _health(ok, ms, err=None):
    try:
        import addons_state
        addons_state.record(ok, ms, err)
    except Exception:
        pass


def _llm_on():
    try:
        import flags
        return flags.assistant_llm() != "off"
    except Exception:
        return True


def _brief():
    try:
        import flags
        return flags.reply_style() == "brief"
    except Exception:
        return False


def _model(text, lang, uid, hist):
    if not sarvam.available() or not _llm_on():
        return None
    hl = "\n".join(f"{r}: {t}" for r, t in hist[-6:])
    user = (hl + "\n" if hl else "") + "pilgrim: " + text
    t0 = time.perf_counter()
    try:
        fx = facts(uid, lang)
        kbf = _kb_block(text, lang, uid)
        if kbf:
            fx += "\n" + kbf
        sysmsg = SYSTEM.format(lang={"en": "English", "hi": "Hindi", "ml": "Malayalam", "ta": "Tamil", "te": "Telugu", "kn": "Kannada"}.get(lang, "English"), facts=fx)
        if _brief():
            sysmsg = "RUSH MODE: reply in ONE short sentence only.\n" + sysmsg
        res = sarvam.chat(sysmsg, user, max_tokens=400)
        _health(True, (time.perf_counter() - t0) * 1000)
    except Exception as e:
        _health(False, (time.perf_counter() - t0) * 1000, e.__class__.__name__)
        return None
    m = re.search(r"\{.*\}", res.text, flags=re.S)
    if not m:
        return None
    try:
        j = json.loads(m.group(0))
    except ValueError:
        return None
    j["_ms"] = int((time.perf_counter() - t0) * 1000)
    return j


def validate(j, uid, lang="en"):
    """Check the model's JSON against the facts. Returns a cleaned dict or None when it cannot be trusted."""
    if not isinstance(j, dict):
        return None
    reply = re.sub(r"\bg[1-5]\b\s*", "", str(j.get("reply") or "")).strip()
    if not reply:
        return None
    if lang != "en" and sum(c.isascii() and c.isalpha() for c in reply) > 0.6 * max(1, sum(c.isalpha() for c in reply)):
        reply = T(lang, "unknown")      # the model answered in English instead of the pilgrim's language: say the safe line in theirs
    gid, pid = j.get("gate_id"), j.get("position_gate_id")
    gid = gid if gid in ORDER else None
    pid = pid if pid in ORDER else None
    action = j.get("action") if j.get("action") in ("none", "book", "change", "cancel", "set_position", "call_volunteer") else "none"
    allowed = _allowed_numbers(uid)
    gs = _gates()
    for n in re.findall(r"\d+", reply.translate(directions.DIGITS)):
        if n not in allowed:
            # a stray number: when it is about a named stop use the real wait, else distrust the whole reply
            if gid and re.search(r"\d", reply) and len(re.findall(r"\d+", reply)) == 1:
                reply = re.sub(r"\d+", str(gs[gid]["wait_min"]), reply, count=1)
            else:
                return None
    return {"intent": str(j.get("intent") or "unknown"), "gate_id": gid, "position_gate_id": pid, "reply": reply, "action": action}


def _digest(uid):
    gs = _gates()
    return (tuple(g["wait_min"] // 2 for g in gs.values()), _pos.get(uid), _slot(uid)[0] and _slot(uid)[0]["window"])


# ------------------------------------------------------------------ public
def strip_ids(reply):
    """Internal stop ids (g1..g5, '(g2)') never reach a pilgrim: removed here for every reply (rules, knowledge pack, model)."""
    s = re.sub(r"\s*[\(\[]\s*g[1-5]\s*[\)\]]", "", str(reply or ""))
    s = re.sub(r"\bg[1-5]\b\s*", "", s)
    return re.sub(r"[ \t]{2,}", " ", s).strip()


def answer(text, lang, uid="anon", session=None, use_model=True, defer_unknown=False):
    """Understand text and answer from the live state. Always returns a dict with a non-empty reply unless the action is book/change/cancel
    (then reply is '' and the caller runs the existing booking flow)."""
    lang = lang if lang in LANGS else "en"
    hist = session.setdefault("hist", []) if isinstance(session, dict) else _hist.setdefault(uid, [])
    r = rules(text, lang, uid, session)
    c = _care(text, lang, uid, r)         # complaint or distress: a tracked care request routed to the nearest volunteer
    if c is not None:
        r = c
    if r is None and WHERE_AM_I.search(text or ""):
        if _pos.get(uid):
            _rep, _nx = _pos_reply(uid, lang)
            r = _res("position", _rep, lang, uid, gate_id=_pos.get(uid), show="map", next_gate_id=_nx)
        else:
            r = ask_position(uid, lang)
    if r is None and defer_unknown:
        return None
    if r is None:
        key = (lang, gatematch.norm(text).strip(), _digest(uid))
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < CACHE_S:
            r = dict(hit[1])
        else:
            _t0 = time.time()
            v = validate(_model(text, lang, uid, hist), uid, lang) if use_model else None
            _llm_ms = int((time.time() - _t0) * 1000) if use_model else 0
            if v:
                if v["position_gate_id"] and v["action"] == "set_position":
                    set_position(uid, v["position_gate_id"])
                if v["intent"] == "position" and not _pos.get(uid):
                    v["reply"] = ask_position(uid, lang)["reply"]
                if v["action"] == "call_volunteer" or v["intent"] == "distress":
                    v["action"] = "call_volunteer"
                    v["reply"] = T(lang, "distress", info=gatematch.display(_nearest("info", _pos.get(uid)) or "g1", lang))
                r = _res(v["intent"], v["reply"], lang, uid, gate_id=v["gate_id"], action=v["action"],
                         show="map" if v["intent"] in ("position", "wait_gate", "wait_best", "next", "distance", "facility") else "slot" if v["action"] in ("book", "change", "cancel") else "none",
                         via="llm", llm_ms=_llm_ms)
                _cache[key] = (time.time(), dict(r))
            else:
                kba = _kb_answer(text, lang, uid)
                if kba:
                    r = _res("info", kba, lang, uid, via="knowledge_pack")
                else:
                    r = _res("unknown", T(lang, "unknown"), lang, uid, via="rules_fallback")
    r["reply"] = strip_ids(r.get("reply"))
    if r["action"] == "call_volunteer":
        _raise_flag(uid, text, lang)
    hist.append(("pilgrim", text))
    if r["reply"]:
        hist.append(("assistant", r["reply"]))
    del hist[:-12]
    return r


def _raise_flag(uid, text, lang):
    try:
        import volunteer
        pos = _pos.get(uid)
        where = f", last stop {queue_sim.BY_ID[pos]['name']}" if pos else ""
        volunteer.note(f"Pilgrim needs help (uid {uid}{where}, {lang}): {text.strip()[:90]}")
    except Exception:
        pass


# ------------------------------------------------------------------ map data
FAC_OFFSET = [(-5, 5), (5, 5), (-5, -5), (5, -5), (0, 7), (0, -7)]


def map_data(uid="anon", lang="en"):
    gs = _gates()
    pos = _pos.get(uid)
    slot, _sm = _slot(uid)
    prog = {p["id"]: p["state"] for p in progress(pos)}
    stops, paths, facs = [], [], []
    for i, gid in enumerate(ORDER):
        x, y = XY[gid]
        nxt = ORDER[i + 1] if i < len(ORDER) - 1 else None
        stops.append({"id": gid, "name": gs[gid]["name"], "name_local": gatematch.display(gid, lang), "x": x, "y": y, "wait_min": gs[gid]["wait_min"],
                      "load": gs[gid]["load"], "facilities": FACILITIES[gid], "walk_to_next_min": WALK[(gid, nxt)] if nxt else None,
                      "state": prog[gid], "is_slot_gate": bool(slot and slot["gate"] == gid)})
        if nxt:
            sf = route_facts.BY_PAIR[(gid, nxt)]
            paths.append({"from": gid, "to": nxt, "walk_min": WALK[(gid, nxt)], "steps": sf["steps"], "distance_m": sf["distance_m"], "climb_m": sf["climb_m"],
                          "difficulty": sf["difficulty"], "wheelchair": sf["wheelchair"], "surface": sf["surface"], "shelters": sf["shelters"]})
        for k, ft in enumerate(FACILITIES[gid]):
            dx, dy = FAC_OFFSET[k % len(FAC_OFFSET)]
            facs.append({"type": ft, "stop": gid, "x": x + dx, "y": y + dy, "label": FAC_LABEL[ft].get(lang) or FAC_LABEL[ft]["en"]})
    return {"simulated": True, "label": "SIMULATED", "rush": _rush(), "canvas": {"w": 100, "h": 100}, "stops": stops, "paths": paths,
            "facilities": facs, "position": pos, "totals": route_facts.totals(),
            "remaining": route_facts.remaining_from(pos, slot["gate"] if slot else None),
            "slot": {"label": slot["label"], "gate": slot["gate"], "gate_name": slot["gate_name"]} if slot else None}


def brain_fields(uid, extra):
    """Contract fields for the HTTP responses, from a brain result in extra['brain'] or defaults."""
    br = extra.get("brain") or {}
    pos = _pos.get(uid)
    intent = br.get("intent") or extra.get("intent")
    show = br.get("show") or ("slot" if intent in ("book", "change", "cancel") else "none")
    return {"intent": intent, "gate_id": br.get("gate_id"), "position_gate_id": pos, "progress": progress(pos), "show": show,
            "action": br.get("action") or ("book" if intent == "book" else "cancel" if intent == "cancel" else "change" if intent == "change" else "none")}
