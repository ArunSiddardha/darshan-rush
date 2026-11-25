"""No GPS: when the stop is unknown the assistant asks for it; once told, answers are per pilgrim."""
import assistant


def test_unknown_position_asks_and_users_do_not_mix():
    assistant.reset()
    a = assistant.answer("which step am I in", "en", "wa-1", use_model=False)
    assert a["intent"] == "position" and "Which stop have you reached" in a["reply"]
    w = assistant.answer("where is the nearest water", "en", "wa-1", use_model=False)
    assert "Tell me which stop" in w["reply"]
    assistant.set_position("wa-1", "g2")
    assistant.set_position("wa-2", "g3")
    r1 = assistant.answer("which step am I in", "en", "wa-1", use_model=False)["reply"]
    r2 = assistant.answer("where am I", "en", "wa-2", use_model=False)["reply"]
    assert "River Crossing" in r1 and "Forest Path" in r2
    n1 = assistant.answer("where is the nearest water", "en", "wa-1", use_model=False)["reply"]
    assert "Nearest to you: River Crossing" in n1
    assert assistant.answer("where am I", "en", "wa-3", use_model=False)["position_gate_id"] is None
