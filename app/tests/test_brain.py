"""The assistant brain: gate matching in six scripts, intents, position memory, model validation. The model is always mocked."""
import pytest

import assistant
import gatematch
import queue_sim
import slots


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    assistant.reset()
    monkeypatch.setattr(assistant, "_model", lambda *a, **k: None)   # no real Sarvam calls in tests
    yield


def ask(text, lang="en", uid="u1", **kw):
    return assistant.answer(text, lang, uid, None, **kw)


GATE_CASES = [
    ("I reached River Crossing", "g2"), ("river kraasing", "g2"), ("what is the wait at Forest Path", "g3"), ("foresttu paath lo entha sepu", "g3"),
    ("queue complex lo entha sepu", "g4"), ("kyoo kompleks", "g4"), ("how far is the main steps from here", "g5"), ("base camp", "g1"),
    ("నేను రివర్ క్రాసింగ్ కి వచ్చాను", "g2"), ("ఫారెస్ట్ పాత్ లో ఎంత సేపు", "g3"), ("క్యూ కాంప్లెక్స్ లో ఎంత సేపు", "g4"), ("మెయిన్ స్టెప్స్ ఎంత దూరం", "g5"),
    ("ഞാൻ റിവർ ക്രോസിങ്ങിൽ എത്തി", "g2"), ("ഫോറസ്റ്റ് പാത്തിൽ എത്ര നേരം", "g3"), ("ബേസ് ക്യാമ്പിൽ കാത്തിരിപ്പ്", "g1"), ("ക്യൂ കോംപ്ലക്സിൽ", "g4"),
    ("நான் ரிவர் கிராசிங் வந்துவிட்டேன்", "g2"), ("மெயின் ஸ்டெப்ஸ் எவ்வளவு தூரம்", "g5"), ("ಫಾರೆಸ್ಟ್ ಪಾತ್ ನಲ್ಲಿ ಎಷ್ಟು ಸಮಯ", "g3"),
    ("ನಾನು ರಿವರ್ ಕ್ರಾಸಿಂಗ್ ತಲುಪಿದೆ", "g2"), ("मैं रिवर क्रॉसिंग पहुँच गया", "g2"), ("मेन स्टेप्स पर कितना इंतज़ार", "g5"), ("main river crossing pe hoon", "g2"),
]


@pytest.mark.parametrize("text,gid", GATE_CASES)
def test_gate_matching(text, gid):
    assert gatematch.best_gate(text) == gid


def test_no_gate_in_general_question():
    assert gatematch.best_gate("which gate has the shortest wait") is None


POSITION = [("I reached River Crossing", "en"), ("నేను రివర్ క్రాసింగ్ కి వచ్చాను", "te"), ("ഞാൻ റിവർ ക്രോസിങ്ങിൽ എത്തി", "ml"),
            ("நான் ரிவர் கிராசிங் வந்துவிட்டேன்", "ta"), ("ನಾನು ರಿವರ್ ಕ್ರಾಸಿಂಗ್ ತಲುಪಿದೆ", "kn"), ("मैं रिवर क्रॉसिंग पहुँच गया", "hi"),
            ("I am at the river crossing now, how long from here", "en"), ("nenu river krosing vachanu", "te")]


@pytest.mark.parametrize("text,lang", POSITION)
def test_position_sets_and_answers_next(text, lang):
    r = ask(text, lang)
    assert r["intent"] == "position" and r["position_gate_id"] == "g2" and r["action"] == "set_position" and r["show"] == "map"
    assert [p["state"] for p in r["progress"]] == ["done", "here", "next", "todo", "todo"]
    assert str(queue_sim.gate_wait("g3")) in r["reply"] and "20" in r["reply"]   # next stop wait and walk (route_facts), from the facts
    assert assistant.get_position("u1") == "g2"


WAIT = [("what is the wait at Forest Path", "en", "g3"), ("ఫారెస్ట్ పాత్ లో ఎంత సేపు", "te", "g3"), ("ഫോറസ്റ്റ് പാത്തിൽ എത്ര നേരം കാത്തിരിക്കണം", "ml", "g3"),
        ("queue complex lo entha sepu", "te", "g4"), ("மெயின் ஸ்டெப்ஸ் எவ்வளவு நேரம் காத்திருக்க", "ta", "g5"), ("ಬೇಸ್ ಕ್ಯಾಂಪ್ ನಲ್ಲಿ ಎಷ್ಟು ಸಮಯ ಕಾಯಬೇಕು", "kn", "g1"),
        ("बेस कैंप पर कितना इंतज़ार", "hi", "g1")]


@pytest.mark.parametrize("text,lang,gid", WAIT)
def test_wait_is_about_the_named_gate_even_after_position(text, lang, gid):
    ask("I reached River Crossing")                      # the old bug: it kept answering about the first gate
    r = ask(text, lang)
    assert r["intent"] == "wait_gate" and r["gate_id"] == gid
    assert str(queue_sim.gate_wait(gid)) in r["reply"]
    assert r["position_gate_id"] == "g2"


def test_best_gate_and_crowd_and_next():
    queue_sim.report_crowd("g3", 100)
    r = ask("which gate has the shortest wait")
    assert r["intent"] == "wait_best" and r["gate_id"] == min(queue_sim.snapshot()["gates"], key=lambda g: g["wait_min"])["id"]
    assert ask("is it crowded now")["intent"] == "crowd"
    r = ask("where do I go next")
    assert r["intent"] == "next" and r["gate_id"] == "g1" and r["show"] == "map"          # no position yet: starts at the first stop
    ask("I reached Forest Path")
    r = ask("where do I go next")
    assert r["gate_id"] == "g4"


def test_distance_from_here():
    ask("I reached River Crossing")
    r = ask("how far is the main steps from here")
    assert r["intent"] == "distance" and r["gate_id"] == "g5" and "70" in r["reply"]


def test_slot_questions_and_booking_actions():
    assert ask("where is my slot / what time is my slot")["intent"] == "slot_info"
    assert ask("I am late for my slot")["intent"] == "slot_late"
    s, _ = slots.book("u1", "g3", None, "open")
    r = ask("what time is my slot")
    assert r["intent"] == "slot_info" and s["start"] in r["reply"] or r["gate_id"] == "g3"
    assert r["gate_id"] == "g3" and r["show"] == "slot"
    assert ask("I am late for my slot")["intent"] == "slot_late"
    assert ask("can I change my slot to evening")["action"] == "change"
    assert ask("cancel my booking")["action"] == "cancel"
    assert ask("I want a slot for tomorrow morning")["action"] == "book"


FACILITY = [("where is drinking water", "water"), ("where is the toilet", "toilet"), ("I need medical help, a doctor", "medical"), ("where is the cloak room", "cloak"),
            ("నీళ్ళు ఎక్కడ దొరుకుతాయి", "water"), ("కుడినీళ్ళు", None), ("കുടിവെള്ളം എവിടെ", "water"), ("ടോയ്‌ലറ്റ് എവിടെ", "toilet")]


@pytest.mark.parametrize("text,fac", [f for f in FACILITY if f[1]])
def test_facilities(text, fac):
    r = ask(text, "ml" if "ം" in text or "്" in text else "en")
    assert r["intent"] == "facility" and r["facility"] == fac and r["show"] == "map"


def test_elder_fee_carry_about_bye():
    assert ask("my mother cannot walk much, is there help")["intent"] == "help_elder"
    assert "no payment" in ask("is there a fee / who do I pay")["reply"]
    assert ask("what should I carry")["intent"] == "carry"
    assert ask("what is this app")["intent"] == "about"
    assert ask("thank you")["intent"] == "goodbye"


@pytest.mark.parametrize("text,lang", [("I lost my son", "en"), ("నా కొడుకు తప్పిపోయాడు", "te"), ("എന്റെ മകനെ കാണാനില്ല", "ml"), ("मेरा बेटा खो गया", "hi")])
def test_distress_calm_and_flag(text, lang):
    import volunteer
    volunteer.STATE["notes"].clear()
    r = ask(text, lang)
    assert r["intent"] == "distress" and r["action"] == "call_volunteer"
    assert "police" not in r["reply"].lower()
    assert any("needs help" in n for n in volunteer.STATE["notes"])


def test_unknown_without_model_is_safe_fallback():
    r = ask("purple elephant philosophy")
    assert r["intent"] == "unknown" and r["via"] == "rules_fallback" and "volunteer" in r["reply"]


def test_model_output_validated(monkeypatch):
    monkeypatch.setattr(assistant.sarvam, "available", lambda: True)
    good = {"intent": "unknown", "gate_id": "g9", "position_gate_id": None, "action": "none", "reply": "Parking is full."}
    monkeypatch.setattr(assistant, "_model", lambda *a, **k: good)
    r = ask("is parking available")
    assert r["via"] == "llm" and r["gate_id"] is None        # invalid gate id dropped
    bad = {"intent": "wait_gate", "gate_id": None, "action": "none", "reply": "The wait is 999 minutes."}
    monkeypatch.setattr(assistant, "_model", lambda *a, **k: bad)
    assistant.reset()
    r = ask("tell me a riddle about moonlight")
    assert r["via"] == "rules_fallback"                       # invented number: not trusted
    fix = {"intent": "wait_gate", "gate_id": "g3", "action": "none", "reply": "The wait at Forest Path is 999 minutes."}
    monkeypatch.setattr(assistant, "_model", lambda *a, **k: fix)
    assistant.reset()
    r = ask("hmm forest thing, tell me quickly please friend")
    assert str(queue_sim.gate_wait("g3")) in r["reply"] and "999" not in r["reply"]


def test_model_sets_position(monkeypatch):
    monkeypatch.setattr(assistant.sarvam, "available", lambda: True)
    monkeypatch.setattr(assistant, "_model", lambda *a, **k: {"intent": "position", "gate_id": "g4", "position_gate_id": "g4", "action": "set_position", "reply": "You are at Queue Complex."})
    r = ask("the thing with the many people has been reached by me")
    assert r["position_gate_id"] == "g4" and assistant.get_position("u1") == "g4"


def test_live_turn_flow_and_api(monkeypatch):
    import addons_live
    from fastapi.testclient import TestClient
    import main
    addons_live.reset_sessions()
    reply, extra, _ = addons_live.handle("I reached River Crossing", "u9", "s9", "en")
    assert "River Crossing" in reply and extra["brain"]["position_gate_id"] == "g2"
    reply, extra, _ = addons_live.handle("what is the wait at Forest Path", "u9", "s9", "en")
    assert "Forest Path" in reply
    c = TestClient(main.app)
    j = c.post("/api/directions", json={"text": "నేను రివర్ క్రాసింగ్ కి వచ్చాను", "lang": "te", "uid": "u7"}).json()
    assert j["intent"] == "position" and j["gate_id"] == "g2" and j["show"] == "map" and len(j["progress"]) == 5
    j = c.post("/api/directions", json={"text": "ഫോറസ്റ്റ് പാത്തിൽ എത്ര നേരം", "lang": "ml", "uid": "u7"}).json()
    assert j["intent"] == "wait_gate" and j["gate_id"] == "g3" and j["position_gate_id"] == "g2"
    m = c.get("/api/map?uid=u7").json()
    assert m["simulated"] is True and len(m["stops"]) == 5 and m["position"] == "g2" and m["stops"][1]["state"] == "here" and len(m["paths"]) == 4
    assert {f["type"] for f in m["facilities"]} == {"water", "toilet", "medical", "rest", "wheelchair", "cloak", "lost_found", "info"}


def test_live_booking_flow_still_works():
    import addons_live
    addons_live.reset_sessions()
    r, _, _ = addons_live.handle("book a slot", "u5", "s5", "en")
    assert "when" in r.lower() or "today" in r.lower()
    r, _, _ = addons_live.handle("I reached Forest Path", "u5", "s5", "en")      # mid booking: answered, then the question is repeated
    assert "Forest Path" in r and ("when" in r.lower() or "today" in r.lower())
