# NOTES_DEMO2: the v2 film plan (video-only submission)

Context: Arun, 14:30 IST: no stage demo; the uploaded video is the whole submission, judged by 17:45. Built for emotional impact.

## Written (new files only, all in `demo/v2/`)
- `VIDEO_SCRIPT.md` (written first): a 2:45 film, second by second, with PICTURE / SOUND / SPONSOR columns. Story of Lakshmamma (68, Telugu only, near Nellore, grandson Ravi) and Meera (20, volunteer, Malayalam). Hook on black text (Tirupati, 8 Jan 2025). Narration about 280 words in 21 labelled pieces (P1 to P12c), with pause marks and the emotion for each. Telugu and Malayalam lines in native script, read-aloud romanisation, English subtitles. A 90-second cut and a 60-second cut are included.
- `STORYBOARD.md`: 16 frames. The palette was checked against `app/static/style.css` (saffron #F26B1D, indigo #2B2E8C, background #FBFAF7, ink #1B1B26, Anek font).
- `RECORDING_PLAN.md`: take order, Mac captures with named states, Arun's phone takes with exact words, narration list, fallbacks with on-screen labels, music, edit list (adds up to 165 s) and pre-upload checks.
- `JUDGE_QA.md`: 12 questions with honest two-sentence answers.
- `PITCH_TEXT.md`: submission text v2 with the money model, the rehearsal numbers, the sponsor table and "what you will see".
- `ARUN_RECORD_NOW.md` in the same folder was written by the lead from my script. I did not edit it. I changed my RECORDING_PLAN so it matches its "no AirDrop" instruction.

## Checked against the code (read only, no Sarvam calls, nothing run)
- Numbers come from `metrics/rehearsal1.md`: p95 3,081 ms then 15 ms; the pod was killed after 19 s (NOTES_INTEGRATION has 20 to 28 s in other runs); peak 1,107 requests a second; 801 bookings kept.
- `scripts/reset_demo.sh` deletes bookings. So in the take order, Lakshmamma books after the reset and before the rush; otherwise "her slot is still hers" would be false.
- Voice first for elders: `app.js` calls `/api/flags/decisions` with `age65=true` when `localStorage.age65 = '1'`. That uses the real Flagsmith segment. `?demo=elder` forces the screen without Flagsmith, so the plan says not to use it.
- Malayalam yes words (`ശരി`, `ചെയ്യൂ`) are in `volunteer.py` YES / YES_WEAK.
- Music: CC0 tracks in `/Users/arun/video-studio/assets/music/`, logged in `assets/LICENCES.md` (HoliznaCC0, CC0 1.0). First choice `music_calm_currents.wav`. Nobody has listened to it: it is lo-fi and may have drums, in which case use no music.

## Risks the lead must act on
1. **Care routing to the nearest volunteer is not built yet.** `main.py` tries to mount `addons_care`, but that file did not exist at about 14:35. `care_store.py` (the roster) exists. Today a distress sentence gets a calm reply and "I left a help note on the volunteer screen". The script and plan include an honest alternative caption and narration line (P9a-alt). Check this before Arun records P3.
2. **assemble.sh strips clip audio (`-an`) and lays one narration file over the whole video.** The v2 film needs the phone clips' own sound (her voice, the app's reply), narration placed per piece, subtitles and ducked music. It also needs new layouts: `black` and the saffron and indigo `card`. RECORDING_PLAN F1 describes `assemble_v2.sh` and `make_cards_v2.cjs` as copies in `demo/v2/`. I have not written them.
3. The app's spoken replies (the Telugu slot read-back and map answer, the Malayalam question) are not scripted. Their subtitles must be transcribed from the real take. The script gives only the expected meanings.
4. The Telugu lines are mine. Have a Telugu speaker check them once. The P4 line "Nenu chivari mettu daggara unnaanu" is untested against the brain's stop matching. The fallback is tapping "I am here" on the map.
5. If nobody can say the Malayalam yes, the plan switches the volunteer page to Telugu and changes P6. Never dub a voice.
6. "They were not waiting for God" in the hook is the brief's wording. Some viewers may find it sharp. An alternative is "They were not waiting for darshan. They were waiting for a number." It is Arun's call.

## Not verified
- None of the captures, the takes or the edit have been run. No video was built.
- The NudgeBee and Flagsmith dashboard captures depend on the logged-in browser helpers in `_tools/` working at take time.
- Whether `/sponsors` lays out well at 1920x1080 (it was checked at 1440 and 390).
