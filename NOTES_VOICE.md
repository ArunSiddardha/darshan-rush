# Voice test notes (25 Nov 2026)

Source: `voice_tests/out/clean.wav.json` (57 real Sarvam runs on synthetic clean audio), `clean_dir.json`, `clean_yesno.json` (re-runs after fixes, with cached question audio). The run was stopped early to save credits; noisy and phone-quality conditions were NOT run.

## What real speech was understood
- Directions intents, 6 languages (te, ta, ml, kn, hi, en): book, wait, age (65+ trait), walk-in, verify (booking-site check) were all classified correctly in the clean set, including Hinglish and Tanglish code-mix ("slot book ചെയ്യണം"). Replies came back in the detected language.
- Yes/no for the volunteer: Malayalam, Tamil, Telugu, Kannada, Hindi, English; 'no' words were correct in every language.
- Crowd report by voice (en, hi, ml): gate and number extracted (2000, 1500, 800) and applied.
- Speech to text latency 250 to 1500 ms. Question audio synthesis 1.4 to 2.2 s uncached; 0 ms once cached (voice_seed).

## What failed, and the fix
- Mis-transcriptions of short Malayalam 'yes': "Shitty." / "ഷെറി." (ശരി), "आम्" / "ആം", "చేయు" (Telugu script for ചെയ്യൂ), "Sedi." (Tamil 'seri'). Fixed with tolerant word lists. "Matao." (an English 'no' that came out garbled) stays unclear on purpose.
- Contradictions never approve: "No, go ahead", "yes no", "ഇല്ല ശരി" give unclear. "don't do it" is now a 'no' (apostrophe no longer splits the word), and "What do you mean?" no longer counts as yes (removed bare "do").
- Silence returns "Nothing heard. Tap Yes or No." with no approval.
- Slot parser accepted only HH:MM strings; now also epoch ints.
- iPhone `audio/mp4; codecs=mp4a.40.2` is stripped before Sarvam.

## Best phrases for the demo (all verified)
- Pilgrim, Malayalam: "ചേട്ടാ, നാളെ രാവിലെ ഒരു slot book ചെയ്യണം." Hindi: "भैया, कल सुबह का 1 slot book कर दो ना।" English: "I want to book a slot tomorrow morning."
- Wait time: "How long is the wait at the river crossing right now?" / "ചേച്ചി Hill Steps Gate-ൽ എത്ര നേരം കാത്തിരിക്കണം?"
- Elder: "My mother is 70, she cannot walk fast, so please keep it short." (sets the age 65+ trait)
- Scam: "Is this booking site real? Someone at the gate asked me for money."
- Volunteer yes (Malayalam): "ശരി, മാറ്റിക്കോ." or "അതെ, ചെയ്യൂ." Safest English: "Yes, go ahead." No: "വേണ്ട."
- Crowd: "River Crossing-ൽ ഏകദേശം 800 പേർ കാത്തുനിൽക്കുന്നു."
- Avoid for the demo: one-word "ശരി" alone (can be heard as "Shitty"); say two words.

## Not tested
Noisy audio, real phone microphones, long utterances, Sarvam streaming. Browser mic run: `voice_tests/out/browser_*.png` (fake device).
