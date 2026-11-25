import re

import pytest

import assistant
import route_facts as rf


@pytest.fixture(autouse=True)
def _clean():
    assistant.reset()
    yield
    assistant.reset()


def test_totals_add_up():
    t = rf.totals()
    assert (t["distance_m"], t["steps"], t["climb_m"], t["minutes"]) == (2400, 480, 180, 90)
    assert t["hardest"]["from"] == "g3" and t["hardest"]["steps"] == 200


def test_stretch_and_remaining():
    assert rf.stretch("g1", "g2")["minutes"] == 10 and rf.stretch("g2", "g1")["minutes"] == 10
    s = rf.stretch("g1", "g4")
    assert s["steps"] == 300 and s["difficulty"] == "hard" and s["wheelchair"] is False
    r = rf.remaining_from("g2")
    assert (r["steps"], r["distance_m"], r["minutes"]) == (440, 1900, 80)
    assert rf.remaining_from(None)["known_position"] is False and rf.remaining_from(None)["steps"] == 480
    assert rf.remaining_from("g1", "g3")["to_gate"]["steps"] == 100
    assert rf.remaining_from("g5")["steps"] == 60


def test_assistant_walk_matches_route_facts():
    assert assistant.walk_between("g1", "g2") == 10 and assistant.WALK[("g3", "g4")] == 30


def ask(text, lang, pos=None, uid="rf"):
    if pos:
        assistant.set_position(uid, pos)
    r = assistant.answer(text, lang, uid, use_model=False)
    assert not re.search(r"\bg[1-5]\b", r["reply"])
    return r


@pytest.mark.parametrize("text,lang", [
    ("how many steps do I have to climb", "en"), ("ఎన్ని మెట్లు ఎక్కాలి?", "te"), ("எத்தனை படிகள் ஏற வேண்டும்", "ta"),
    ("എത്ര പടികൾ കയറണം", "ml"), ("ಎಷ್ಟು ಮೆಟ್ಟಿಲು ಹತ್ತಬೇಕು", "kn"), ("कितनी सीढ़ियाँ चढ़नी हैं", "hi")])
def test_effort_from_base_camp(text, lang):
    r = ask(text, lang)
    assert r["intent"] == "effort" and "480" in r["reply"] and "2.4" in r["reply"] and r["via"] == "rules"
    assert assistant.get_position("rf") is None      # the question does not move the pilgrim


@pytest.mark.parametrize("text,lang", [
    ("I am at River Crossing. How many steps are left to the shrine?", "en"), ("how many steps left", "en"),
    ("ఎన్ని మెట్లు మిగిలాయి", "te"), ("எத்தனை படிகள் மீதம்", "ta"), ("എത്ര പടികൾ ബാക്കി", "ml")])
def test_effort_from_river_crossing(text, lang):
    r = ask(text, lang, pos="g2")
    assert r["intent"] == "effort" and "440" in r["reply"] and "480" not in r["reply"]
    assert r["position_gate_id"] == "g2"


def test_position_in_the_same_sentence():
    r = ask("I am at River Crossing. How many steps are left to the shrine?", "en", uid="rf2")
    assert "From River Crossing" in r["reply"] and "440 steps" in r["reply"] and r["position_gate_id"] == "g2"


def test_mettlu_is_not_the_stop_main_steps():
    r = ask("enni mettlu ekkali", "te")
    assert r["intent"] == "effort" and r["gate_id"] is None and "480" in r["reply"]
    assert ask("ఎన్ని మెట్లు ఎక్కాలి?", "te")["intent"] == "effort"
    # naming the stop still works
    assert ask("how long is the wait at Main Steps", "en")["intent"] == "wait_gate"
    assert ask("I am at Main Steps, how many steps are left", "en", uid="rf3")["position_gate_id"] == "g5"


def test_other_effort_questions():
    for t in ["how far is it", "is it steep", "how long to walk", "how much climbing is there", "can my mother manage the climb"]:
        r = ask(t, "en")
        assert r["intent"] == "effort", t
    assert "wheelchair route" in ask("is there a ramp", "en")["reply"]
    assert "Forest Path" in ask("is there a wheelchair route", "en", pos="g2")["reply"]
    assert ask("how far is River Crossing", "en")["intent"] == "distance"
    assert ask("where is the toilet, how far", "en")["intent"] == "facility"


def test_strip_ids_everywhere():
    assert assistant.strip_ids("Base Camp (g1), then g2 River Crossing (g2).") == "Base Camp, then River Crossing."
    r = ask("tell me about the route stops", "en")
    assert not re.search(r"\bg[1-5]\b", r["reply"])


def test_map_data_new_fields():
    j = assistant.map_data("rf", "en")
    p = j["paths"][2]
    assert (p["from"], p["steps"], p["walk_min"], p["distance_m"], p["difficulty"], p["wheelchair"]) == ("g3", 200, 30, 700, "hard", False)
    assert j["totals"]["steps"] == 480 and j["remaining"]["steps"] == 480
    assistant.set_position("rf", "g3")
    assert assistant.map_data("rf", "en")["remaining"]["steps"] == 380 and j["stops"][0]["walk_to_next_min"] == 10


def test_facts_block_has_route_numbers_and_no_ids_needed():
    f = assistant.facts("rf", "en")
    assert "480 steps" in f and "Forest Path to Queue Complex: 30 min, 700 m, 200 steps" in f
