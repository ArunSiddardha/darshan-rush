"""Phones side by side: a transcript that repeats a reply the app just spoke is ignored, real questions are not."""
import addons_live as L


def test_echo_is_ignored_and_questions_pass():
    L._spoken.clear()
    L.note_spoken("You are at River Crossing. Next is Forest Path, 20 minutes on foot. The wait there is 36 minutes.")
    assert L.is_echo("you are at river crossing next is forest path 20 minutes on foot")
    assert L.is_echo("Next is Forest Path, twenty minutes on foot. The wait there is 36 minutes") 
    assert not L.is_echo("where is the nearest water")
    assert not L.is_echo("I reached the forest path")
    assert not L.is_echo("yes")
    L._spoken.clear()
    assert not L.is_echo("you are at river crossing next is forest path")


def test_indian_script_question_is_not_an_echo_of_an_earlier_reply():
    L._spoken.clear()
    L.note_spoken("നിങ്ങളുടെ സ്ലോട്ട് ബുക്ക് ചെയ്തു, നാളെ രാവിലെ 6 മണിക്ക്, Base Camp ഗേറ്റിൽ. പതിനഞ്ച് മിനിറ്റ് മുൻപ് എത്തണം.")
    L.note_spoken("ഒരു വെബ്സൈറ്റും ശരിയാണെന്ന് എനിക്ക് ഉറപ്പിക്കാനാവില്ല. ക്ഷേത്ര ബോർഡിന്റെ ഔദ്യോഗിക വെബ്സൈറ്റിൽ മാത്രം ബുക്ക് ചെയ്യൂ.")
    assert not L.is_echo("ചേച്ചി, മെയിൻ സ്റ്റെപ്സ് ഗേറ്റിൽ എത്ര നേരം കാത്തിരിക്കണം?")
    assert L.is_echo("നിങ്ങളുടെ സ്ലോട്ട് ബുക്ക് ചെയ്തു നാളെ രാവിലെ 6 മണിക്ക് Base Camp ഗേറ്റിൽ")
    L._spoken.clear()
