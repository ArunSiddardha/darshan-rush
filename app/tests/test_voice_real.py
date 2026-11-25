"""Logic tests built from REAL Sarvam transcripts (25 Nov 2026). No network."""
import directions as d
import volunteer as v
import pytest

YES = ["ശരി.", "ഷെറി.", "അതെ, ചെയ്യൂ.", "ആം.", "ശരി, മാറ്റിക്കോ.", "ചെയ്യാം.", "ചെയ്യൂ.", "చేయు.", "Sari.", "సరే.", "అవును, చేయండి.",
       "ஆமாம், பண்ணுங்க.", "ಹೌದು, ಮಾಡಿ.", "हाँ।", "हाँ, ठीक है।", "कर दो।", "Yes, go ahead.", "Okay, do it.", "Yes.", "yes please do it"]
NO = ["വേണ്ട.", "ഇപ്പോ വേണ്ട.", "Vendaam.", "வேண்டாம்.", "వద్దు.", "Beda.", "ಬೇಡ.", "नहीं।", "मत करो।", "No.", "Not now.", "don't do it", "no, stop"]
UNCLEAR = ["What?", "one minute.", "", "The river crossing is very busy today. I can see so many people.", "എന്താ പറഞ്ഞത്?",
           "What do you mean?", "Shitty.", "Matao.", "yes no", "No, go ahead", "ഇല്ല ശരി"]


@pytest.mark.parametrize("t", YES)
def test_yes(t):
    assert v.keyword_decision(t) == "yes"


@pytest.mark.parametrize("t", NO)
def test_no(t):
    assert v.keyword_decision(t) == "no"


@pytest.mark.parametrize("t", UNCLEAR)
def test_unclear_never_approves(t):
    assert v.keyword_decision(t) == "unclear"


def test_when():
    ts, lbl = d.parse_when("tomorrow morning")
    assert lbl == "tomorrow 06:00"
    assert d.parse_when("naalaikku kaalai slot")[1] == "tomorrow 06:00"
    assert d.parse_when("repu udayam slot kavali")[1] == "tomorrow 06:00"
    assert d.parse_when("slot at ten thirty tomorrow")[1] == "tomorrow 10:30"
    assert d.parse_when("tomorrow evening 6 pm")[1] == "tomorrow 18:00"
    assert d.parse_when("2 people please")[1] is None
    assert d.parse_when("book a slot")[0] is None


def test_say_time():
    from datetime import datetime
    ts, _ = d.parse_when("tomorrow morning")
    assert d.say_time("en", ts) == "tomorrow at six o'clock in the morning"
    assert d.say_time("hi", ts).startswith("कल सुबह 6")


def test_age_and_party_words():
    assert d.keyword_intent("मेरी माँ सत्तर साल की हैं")["age"] == 70
    assert d.keyword_intent("எங்க அம்மாவுக்கு எழுபது வயசு")["age"] == 70
    assert d.keyword_intent("my mother is seventy")["age"] == 70
    assert d.keyword_intent("ഇവർക്ക് phone ഇല്ല. walk-in ആണ്. 2 പേരുണ്ട്")["party"] == 2


def test_gate_in_text():
    g = [{"id": "g2", "name": "River Crossing"}, {"id": "g5", "name": "Main Steps"}]
    assert d.gate_in_text(g, "wait at the river crossing")["id"] == "g2"
    assert d.gate_in_text(g, "main steps gate")["id"] == "g5"
    assert d.gate_in_text(g, "hello") is None


def test_spoken_has_no_symbols():
    t = d.spoken("Wait is 5 minutes (simulated).", "en")
    assert "(" not in t and ")" not in t
