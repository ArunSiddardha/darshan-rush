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
