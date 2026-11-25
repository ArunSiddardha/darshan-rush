"""Whole conversations in all six languages, as a pilgrim would have them (regression for 25 Nov findings):
book -> party -> a question while confirming (never taken as yes) -> yes -> where am I -> reached a stop -> nearest water."""
import pytest
import addons_live as L
import assistant
import directions

B = {"en": ["I want to book a slot tomorrow morning", "two people", "Is this booking site real? Someone asked me for money.", "yes", "where am I", "I reached the river crossing", "where is the nearest water"],
     "te": ["అన్నా, రేపు ఉదయం ఒక స్లాట్ కావాలి. బుకింగ్ చేస్తారా?", "ఇద్దరు", "ఈ booking site నిజమేనా? ఎవరో డబ్బులు అడుగుతున్నారు.", "సరే", "నేను ఎక్కడ ఉన్నాను", "నేను రివర్ క్రాసింగ్ చేరుకున్నాను", "దగ్గరలో నీళ్ళు ఎక్కడ ఉన్నాయి"],
     "ta": ["சாமி, நாளைக்கு கலை ஒரு ஸ்லாட் புக்கிங் பண்ணனும்.", "இரண்டு பேர்", "இந்த புக்கிங் வெப்சைட் உண்மையானதா? ஒரு தரகர் பணம் கேக்குறார்.", "சரி", "நான் எங்கே இருக்கிறேன்", "நான் ரிவர் கிராசிங் வந்துவிட்டேன்", "அருகில் தண்ணீர் எங்கே"],
     "ml": ["ചേട്ടാ, നാളെ രാവിലെ ഒരു സ്ലോട്ട് ബുക്ക് ചെയ്യണം.", "രണ്ടു പേർ", "ഈ booking വെബ്സൈറ്റ് ശരിയാണോ? ഇടനിലക്കാരൻ പൈസ ചോദിക്കുന്നു.", "ശരി", "ഞാൻ എവിടെയാണ്", "ഞാൻ റിവർ ക്രോസിംഗിൽ എത്തി", "അടുത്ത് വെള്ളം എവിടെ"],
     "kn": ["ಅಣ್ಣ, ನಾಳೆ ಬೆಳಿಗ್ಗೆ ಒಂದು ಸ್ಲಾಟ್ ಬುಕಿಂಗ್ ಮಾಡಿ.", "ಇಬ್ಬರು", "ಈ ಬುಕ್ಕಿಂಗ್ ಸೈಟ್ ನಿಜವಾದದ್ದಾ? ಯಾರೋ ದುಡ್ಡು ಕೇಳ್ತಿದ್ದಾರೆ.", "ಸರಿ", "ನಾನು ಎಲ್ಲಿದ್ದೇನೆ", "ನಾನು ರಿವರ್ ಕ್ರಾಸಿಂಗ್ ತಲುಪಿದೆ", "ಹತ್ತಿರ ನೀರು ಎಲ್ಲಿದೆ"],
     "hi": ["भैया कल सुबह का एक स्लॉट बुक कर दो ना।", "दो लोग", "ये booking site असली है क्या? कोई पैसे माँग रहा है।", "हाँ", "मैं कहाँ हूँ", "मैं रिवर क्रॉसिंग पहुँच गया", "पास में पानी कहाँ है"]}
NO = {"en": "no", "te": "వద్దు", "ta": "வேண்டாம்", "ml": "വേണ്ട", "kn": "ಬೇಡ", "hi": "नहीं"}


def _turn(sid, lang, text):
    sl = directions.script_lang(text) or lang
    s = L.session(sid, sl)
    reply, extra, _ = L.handle(text, sid, sid, sl, s)
    return s, reply, extra


@pytest.mark.parametrize("lang", list(B))
def test_full_conversation(lang):
    sid = "conv6-" + lang
    assistant.reset()
    states, intents = [], []
    for t in B[lang]:
        s, reply, extra = _turn(sid, lang, t)
        assert reply, (lang, t)
        states.append(s["state"]); intents.append(extra.get("intent"))
        if lang != "en":
            assert directions.script_lang(reply) == lang, (lang, t, reply)     # answered in the pilgrim's language
    assert states[:4] == ["ask_party", "confirm", "confirm", "booked"], (lang, states)   # the question did not book the slot
    assert intents[4] == "position" and intents[5] == "position" and intents[6] == "facility", (lang, intents)
    assert assistant.get_position(sid) == "g2"


@pytest.mark.parametrize("lang", list(B))
def test_no_during_booking_stops_it(lang):
    sid = "conv6no-" + lang
    _turn(sid, lang, B[lang][0])
    s, reply, extra = _turn(sid, lang, NO[lang])
    assert s["state"] == "idle" and extra.get("intent") == "cancel" and reply
