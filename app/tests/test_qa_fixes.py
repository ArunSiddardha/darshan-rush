import addons_live as L
import assistant as A
import addons_staff as S


def test_next_stop_is_not_goodbye():
    for t in ["next stop", "what is the next stop", "next stop please", "अगला स्टॉप", "अगला स्टॉप क्या है", "അടുത്ത സ്റ്റോപ്പ്",
              "அடுத்த நிறுத்தம்", "తర్వాత స్టాప్ ఏది", "ಮುಂದಿನ ಸ್ಟಾಪ್", "stop at forest path"]:
        assert not L.is_bye(t.lower()), t
    for t in ["thank you", "that is all", "bye", "stop", "stop listening"]:
        assert L.is_bye(t), t


def test_next_after_named_stop():
    for t in ["what is next after forest path", "what comes after Forest Path", "क्यू कॉम्प्लेक्स के बाद क्या है", "ക്യൂ കോംപ്ലക്സ് കഴിഞ്ഞാൽ അടുത്തത് എന്ത്"]:
        r = A.rules(t, "en", "qa_after")
        assert r and r["intent"] == "next" and "comes" in r["reply"], (t, r)
    assert "Queue Complex" in A.rules("what comes after Forest Path", "en", "qa_after")["reply"]


def test_noise_ignored():
    for t in ["uh", "um", "hmm", "ah", "k", "xq", "uh um", "hm."]:
        assert L._noise(t), t
    assert not L._noise("yes") and not L._noise("next stop")


def test_kb_off_topic_unknown_and_short_no_ids():
    for t in ["who is the prime minister", "is it going to rain tomorrow at the shrine"]:
        r = A.answer(t, "en", "qa_kb", None, use_model=False)
        assert r["via"] != "knowledge_pack", (t, r["reply"])
    r = A.answer("is there an entry fee", "en", "qa_kb2", None, use_model=False)
    assert len(r["reply"]) <= 220 and "(g" not in r["reply"]


def test_distress_and_elder_rules():
    assert A.rules("എന്റെ കുട്ടിയെ കാണുന്നില്ല", "ml", "qa_d")["intent"] == "distress"
    assert A.rules("mera bachcha nahi mil raha", "hi", "qa_d")["intent"] == "distress"
    assert A.rules("ಹಿರಿಯರಿಗೆ ಸಹಾಯ ಬೇಕು", "kn", "qa_d")["intent"] == "help_elder"
    assert A.rules("മുതിർന്നവർക്ക് സഹായം", "ml", "qa_d")["intent"] == "help_elder"


def test_staff_rush_question():
    f = {"rush": False, "slot_mode": "open", "stops": []}
    for t in ["is there a rush now", "are we in rush mode"]:
        r = S._rules_answer(t, t.lower(), f)
        assert r and r[0] == "rush", t
