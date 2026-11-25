"""Reply language follows the script of what the pilgrim said or typed."""
import directions


def test_script_lang():
    assert directions.script_lang("నేను ఎక్కడ ఉన్నాను") == "te"
    assert directions.script_lang("நான் எங்கே இருக்கிறேன்") == "ta"
    assert directions.script_lang("ഞാൻ എവിടെയാണ്") == "ml"
    assert directions.script_lang("ನಾನು ಎಲ್ಲಿದ್ದೇನೆ") == "kn"
    assert directions.script_lang("मैं कहाँ हूँ") == "hi"
    assert directions.script_lang("where am I") is None
    assert directions.script_lang("slot booking కావాలి please") == "te"
    assert directions.script_lang("") is None
