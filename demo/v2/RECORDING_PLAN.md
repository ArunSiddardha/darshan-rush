# Recording plan for the v2 film

Who: **the lead** = the Claude session on the Mac at home (runs the app, the cluster, the headless browser). **Arun** = at the venue with his iPhone.
Deadline: judged by 17:45 IST, upload well before. Target: all raw files on the Mac by 16:00, first full cut 16:20, upload by 16:45.
No Sarvam calls from the Mac for capture. The only Sarvam use is Arun's real phone takes (STT and TTS), which is the product working.

## 0. Order of the whole take (this order matters)

`scripts/reset_demo.sh` deletes all bookings. Lakshmamma's slot must be booked **after** the reset and **before** the rush, so the "her slot is still hers" beat is true.

| Step | Who | What | Approx. time |
|---|---|---|---|
| 1 | lead | `scripts/reset_demo.sh`, wait 60 s; confirm `GET /api/flags` says full/open; send Arun the current public URL (`metrics/public_url.txt`) | 2 min |
| 2 | Arun | Take P1: Lakshmamma books and asks about her knees (section B2) | 3 min |
| 3 | lead | Start the Mac captures (A1), then start the rush | 1 min |
| 4 | lead | Pod OOMKilled, NudgeBee investigates, the volunteer question appears; tell Arun "ready" | 1 to 2 min |
| 5 | Arun | Take M1: Meera's yes (B3) | 1 min |
| 6 | lead | Approve in NudgeBee on camera, Flagsmith flips on camera, graph recovers (A2, A3) | 2 min |
| 7 | Arun | Take P2: reopen the pilgrim page on the same phone, light map, the slot still there (B4) | 1 min |
| 8 | Arun | Take P3 (care request) and P4 (the last stop, "it is your time") | 2 min |
| 9 | lead | Captures that do not depend on timing: elder vs standard, /sponsors, Flagsmith segments (A4) | 5 min |
| 10 | Arun | Narration in a quiet corner (C) | 10 min |

If step 5 misses the moment, the lead can re-run the incident (reset, P1 again, rush) once. Never stage a second "yes" over the first incident.

---

## A. The lead, on the Mac (headless, deterministic, real backend)

All browser captures use `demo/record_pages.cjs` (Chrome for Testing, its own temp profile, never Arun's Chrome). Base URL `http://127.0.0.1:8088` (the kind cluster through NodePort). Output in `demo/raw/`. For v2, write the files to `demo/v2/raw/` (move them there after each run, or copy the script to `demo/v2/record_v2.cjs` with `OUT` changed; do not edit the original).

### A1. Rush captures (start them together just before the rush; 150 s)
```
cd /Users/arun/hackathon/festive/repo/demo && node record_pages.cjs 150 graph kube
```
- `graph-1280x720.webm`: the p95 line climbing to about 3 s, then falling to the floor after the flip. Named states: **G1 calm**, **G2 climbing**, **G3 crash gap**, **G4 recovered**.
- `kube-1280x720.webm`: the terminal look-alike page that runs the real `kubectl --context kind-nb -n darshan get pods` every second. Named states: **K1 Running 0 restarts**, **K2 OOMKilled**, **K3 Running 1 restart**. The page header says it is a live refresh; keep that visible. Font is 22 px: crop/zoom in the edit so it reads at least 28 px on the final frame.
- Start the rush the usual way (`scripts/rush.sh`, or `PRESS=1 node record_pages.cjs 150 judge` in a second terminal). Note the wall-clock time of the start, the OOMKilled line and the flip; write them in `demo/v2/raw/TIMES.txt` so the edit can find the moments.

### A2. NudgeBee (real execution view, approval)
- Attach to the logged-in NudgeBee browser through `_tools/hb.cjs` and open the running execution with `_tools/nb_exec.cjs` (as in SHOTLIST A3). Record the tab with Playwright `recordVideo` at 1280x720, or take a screenshot every second if recording is not possible.
- Named states: **N1** the OOMKilled event in the execution list; **N2** the investigation result with NudgeBee's own root-cause words (wait until the full text is rendered, hold 8 s); **N3** the approval card before the click; **N4** the click on Approve (use `_tools/nb_approve.cjs` with a visible cursor, or a person clicks; keep the cursor visible); **N5** the workflow's HTTP tasks marked done.
- Crop out the account menu, email, workspace id and any token field. Check every frame of N1 to N5 before use.

### A3. Flagsmith dashboard, before and after
- Open the project 55985 feature list in the same logged-in browser approach (`_tools/fs_api.cjs` / `fs_login.cjs` helpers exist). Record at 1280x720 from just before N4 until 10 s after.
- Named states: **F1** `map_mode` = full, `slot_mode` = open; **F2** after the NudgeBee HTTP tasks, `map_mode` = lite, `slot_mode` = staggered. If the list does not refresh by itself, reload once after the approval (the reload is visible and honest).
- Never show the Admin API key page, environment keys, or the SDK key panel.
- Also capture **F3** the segments page (`elders_65_plus`, language segments) as a still, 5 s.

### A4. Timing-free captures (after the rush)
- **E1 elder vs standard** (Flagsmith segment, real): two 390x844 headless pages side by side. Elder: before load set `localStorage.age65 = '1'` (the page then asks `/api/flags/decisions?...&age65=true`, and Flagsmith's `elders_65_plus` segment turns `voice_first` on). Standard: a fresh uid without it. 10 s each. Do NOT use `?demo=elder` for this shot, because that forces the screen without Flagsmith.
- **S1 sponsors page**: `http://127.0.0.1:8088/sponsors` at 1280x720 (and 1920x1080 if it lays out well), 12 s, after the run so the Sarvam calls from Arun's takes, the flag change times and the NudgeBee chain are all filled with real data.
- **C1 care alert on the staff page** (only if the care feature is live, see the warning in B5): the volunteer page at 390x844 showing the help note from Lakshmamma's request.
- **L1 light map on the pilgrim page at 1280 width** as a spare, in case Arun's P2 take fails.
- Check every capture: `ffprobe` for duration, extract one frame per second into a contact sheet, look at each frame for keys, tokens, emails or personal notifications.

---

## B. Arun, on his iPhone at the venue

Same phone setup as `demo/SHOTLIST.md` B1 and B2 (Do Not Disturb on, Screen Recording with **Microphone On**, Safari, volume about 70%). Use the public URL the lead sends. Use the **same phone and the same Safari tab** for P1, P2, P3 and P4, so it is the same pilgrim (same uid and slot).

### How to hold the phone and get a clean take in a noisy hall
- Find the quietest place you can reach in 1 minute: a corridor, a stairwell, outside the hall door, or sit in a car. Face a wall or a curtain, not the open room. Soft surfaces absorb echo.
- Phone upright in your left hand, elbow resting on a table or your knee, screen at chest height. Speak toward the bottom edge (the microphone) from about 15 to 20 cm, not straight into it.
- Keep the speaker uncovered so the app's reply is loud and clear on the recording.
- Start recording, wait 2 s silent, do the line, wait for the full reply, wait 2 s, stop. Never stop in the middle of the app's reply.
- Do every take twice. Keep both. Name them in your message ("P1 take 2 is better").
- If someone walks past talking, stop and redo. A clean take beats a fast one.
- Read the line slowly and warmly. Lakshmamma is 68 and tired; Meera is calm and busy.

### B2. Take P1: Lakshmamma books, then asks about her knees (file `P1_lakshmamma.mov`, about 50 s)
1. Open the public URL in Safari. Choose **తెలుగు (Telugu)**. Make sure live mode is on ("Tap once to start talking").
2. Start the screen recording with the microphone. Wait 2 s.
3. Tap once. Say: **"Ee roju darshananiki oka time kaavaali, naayanaa."** (ఈ రోజు దర్శనానికి ఒక టైమ్ కావాలి, నాయనా. "I need a time for darshan today, dear.")
4. Let the slot card appear and the whole Telugu reply play. If the app asks to confirm, say **"Avunu."** (అవును, "Yes.").
5. Without tapping again, say: **"Nenu river crossing daggara unnaanu. Mokaallu noppigaa unnaayi. Koorchodaaniki chotu undaa?"** (నేను రివర్ క్రాసింగ్ దగ్గర ఉన్నాను. మోకాళ్ళు నొప్పిగా ఉన్నాయి. కూర్చోడానికి చోటు ఉందా? "I am at River Crossing. My knees hurt. Is there somewhere to sit?")
6. Let the reply play and the map move to River Crossing. Scroll gently to the map if it does not show by itself. Wait 2 s. Stop.
7. Spare line if the knees line is not understood: **"Taagadaaniki neellu ekkada unnaayi?"** (తాగడానికి నీళ్ళు ఎక్కడ ఉన్నాయి? "Where is drinking water?")

### B3. Take M1: Meera says yes (file `M1_meera.mov`, about 25 s)
1. Wait for the lead's "ready" (the question is live). Open `<public URL>/volunteer` in a **new** tab (Meera is a different person).
2. Start the screen recording with the microphone when the Malayalam question shows. Let the question play fully.
3. Tap the microphone. Say calmly: **"Sari, cheyyu."** (ശരി, ചെയ്യൂ. "Okay. Do it.") If it is not understood, say **"Sari."** (ശരി).
4. Wait for what it heard and "Waiting for the duty officer to confirm in NudgeBee". Wait 2 s. Stop.
- **If nobody can say the Malayalam line naturally:** before the take, ask the lead to switch the volunteer page language to Telugu, and say **"Saray, chayyandi."** (సరే, చేయండి. "Okay. Do it.") Then the script changes (VIDEO_SCRIPT.md, the note under the lines table): Meera is "a volunteer", the question is shown in Telugu. Do not dub a Malayalam voice over it.
- If the microphone fails, tap the Yes button. That clip gets the on-screen label "Typed input" (section D).

### B4. Take P2: her slot is still hers (file `P2_after.mov`, 10 s)
After the lead says "recovered": go back to the Lakshmamma tab, pull down to reload. The page should show the light map (the plain list) and the slot pass at the top. Record 8 s, no speech needed.

### B5. Takes P3 and P4: the care request and the steps (files `P3_care.mov`, `P4_steps.mov`)
- **Warning:** care requests routed to the **nearest volunteer** come from `addons_care`, which was not in the repo at 15:00 (main.py tries to mount it; `care_store.py` with the volunteer roster exists). Today the assistant answers a distress sentence with "go to the nearest volunteer; I have left a help note on the volunteer screen". Ask the lead before this take whether the care routing is live. If it is not, the film shows only what is real: the calm reply and the help note, and the caption becomes "One sentence leaves a note for the volunteers." Never caption "nearest volunteer: Meera" unless the screen really says it.
- P3: in the Lakshmamma tab say **"Naa manavadu kanipinchadam ledu."** (నా మనవడు కనిపించడం లేదు. "I can't find my grandson.") Let the reply play.
- P4: say **"Nenu chivari mettu daggara unnaanu."** (నేను చివరి మెట్టు దగ్గర ఉన్నాను. "I am at the last steps.") or tap the last stop on the map and "I am here". The marker moves to the last stop with the pass at the top. Record 8 s. If the app does not understand the spoken stop name, use the map's "I am here" button: that is a tap, not typed text, so no label is needed.

### B6. Sending the files back
AirDrop does not work (Arun is at the venue, the Mac is at home). Upload to Google Drive or send by email as `ARUN_RECORD_NOW.md` says. In Photos choose "Actual size" or share the original file, so the video is not shrunk. Send a message with the file names and which take is better. The lead downloads them into `demo/v2/raw/phone/`.

---

## C. Narration (Arun, Voice Memos, quiet corner)

- Same quiet place as above, or sit in a car with the windows closed. Phone 20 cm from your mouth, slightly to the side (avoids pops on "p" and "b").
- Read **one sentence group at a time**, from the list below. Say the label first ("P one"), pause 1 s, read it, pause 2 s. If you stumble, say the label again and redo just that one. The lead cuts each one out and places it on the timeline.
- Read slowly (slower than feels natural). Smile on P2 and P8. Lower and softer on P1 and P12.
- One file: `narration.m4a`. Send the same way as the videos.

| Label | Emotion | Read exactly |
|---|---|---|
| P1 | quiet | This is Lakshmamma. She is sixty-eight. She speaks only Telugu. She has never booked anything online. |
| P2a | warm | She taps once. And she just talks. |
| P2b | warm | No form. No English. |
| P3 | warm | The map shows her where she is. And where to sit. |
| P3b | warm | Her time is set. She can rest until then. |
| P4a | urgent | Then, everyone arrives at once. The booking service slows. |
| P4b | urgent | Then Kubernetes kills it. This crash is real. |
| P5 | urgent, slower | Nobody is watching a dashboard. NudgeBee is. It finds the cause, in plain words. The heavy map ate the memory. |
| P6 | steady | Meera runs the spot counter. She is a student, not an engineer. So the app asks her, in Malayalam. |
| P6-alt | steady | (only if the yes is in Telugu) So the app asks her, in her own language. |
| P7a | steady | A duty officer confirms in NudgeBee. |
| P7b | steady | Two Flagsmith flags flip. A light map. Staggered slots. No redeploy. |
| P8a | relieved | Before, the slowest booking took three seconds, and the service died in nineteen. After, fifteen milliseconds. No crash. |
| P8b | relieved, warm | And Lakshmamma's slot is still hers. |
| P9a | brisk | When Ravi wanders off, one sentence reaches the nearest volunteer. |
| P9a-alt | brisk | (if care routing is not live) When Ravi wanders off, one sentence leaves a note for the volunteers. |
| P9b | brisk | Everyone over sixty-five gets voice first. Flagsmith decides that. |
| P9c | proud | All three tools, live, on one page. |
| P10 | plain, proud | Who pays? The shrine. About ten rupees for a voice booking. It costs us three and a half. Pilgrims never pay. No ads. No selling data. |
| P11 | honest, even | The crowd is simulated. The crash and the fix are real. No shrine uses this yet. |
| P12a | quiet | At three o'clock, Lakshmamma reached the steps. |
| P12b | quiet, slow | This time, nobody stood in a crush for a number. |
| P12c | quiet | Darshan Rush. |
| N90 | for the cuts | Meera, a volunteer, says yes in Malayalam. / Three seconds before. Fifteen milliseconds after. No crash. / The shrine pays about ten rupees a booking. It costs us three and a half. Pilgrims never pay. |

If the final rush take gives other numbers (for example the pod died after 28 s), the lead tells Arun before he records P8a, and he reads the take's numbers.

---

## D. Fallbacks (nothing faked)

| If this fails | Do this | On-screen label |
|---|---|---|
| Arun cannot record his voice takes | The lead records the pilgrim and volunteer pages on the Mac with the typed box (Playwright `fill` + `click`), same lines in Telugu/Malayalam script | **"Typed input"** (top left, 36 px, for the whole clip) and narration line "Here we typed the words instead of speaking them." |
| The app's spoken reply is not audible on the phone take | Use the take anyway; the reply text is on screen; add the subtitle from that text | none (the reply is real, just quiet) |
| Meera's spoken yes not understood | Tap the Yes button on the volunteer page | **"Typed input"** on that clip |
| NudgeBee approval cannot be recorded live | Use screenshots of the real execution and approval (stills, 1 s each) taken during the real run | **"Screenshots from the real run"** |
| Flagsmith dashboard did not refresh on camera | Reload once on camera; if still not possible, show `GET /api/flags` JSON in the terminal page before and after | none (it is the real value) |
| The rush does not OOM-kill the pod in the take | Use the rehearsal (metrics/rehearsal1.md) numbers on the card and say "in rehearsal" | **"From our rehearsal run, 25 Nov 14:07"** |
| Care routing not live | Show the real distress reply and help note only | caption changes, see B5 |
| No narration recorded | Captions carry the story (each narration line becomes a caption card); no synthetic voice pretending to be Arun | none |

---

## E. Music

A licence-clean library exists: `/Users/arun/video-studio/assets/music/`, logged in `/Users/arun/video-studio/assets/LICENCES.md` (section 2: Free Music Archive, HoliznaCC0, **CC0 1.0**, commercial use, no attribution required; checked 2026-11-13).
- First choice: `/Users/arun/video-studio/assets/music/music_calm_currents.wav` ("Calm Currents (Lofi, Relax, Calm)", HoliznaCC0, CC0 1.0, source in LICENCES.md line 337).
- Second choice: `/Users/arun/video-studio/assets/music/music_into_the_mist.wav` (CC0 1.0, line 339).
- These are lo-fi tracks and may have a drum beat. The film opens on six deaths; a beat there would be wrong. Rules: listen first; use only a section without drums if one exists; otherwise **no music**. Never under the hook (0:00 to 0:12), out from 0:54 to 1:44, back softly for the recovery and the close.
- Level: music bed at about -30 LUFS under voice, ducked a further 8 dB when anyone speaks (ffmpeg `sidechaincompress` with the voice as the key). Fade in 2 s, fade out 3 s at the end card.
- Caveat from LICENCES.md: CC0 tracks can still get a third-party Content ID claim on YouTube; if one appears, dispute with the CC0 page.

---

## F. Edit list and checks

### F1. What assemble.sh can and cannot do today
`demo/assemble.sh` builds the picture from an edit list and lays **one** narration file over the whole video. It strips all clip audio (`-an`), and its cards use the old teal palette. For v2 we need the phone clips' own audio (her voice and the app's reply), timed narration pieces, subtitles and an optional music bed. Do not edit the original. Make copies in `demo/v2/`:
- `assemble_v2.sh`: same layouts plus `black` (white text on black, for the hook and the closing line) and `card` (saffron/indigo palette, multi-line); keep audio from clips marked `audio=keep`; place each narration piece at its start time (`adelay`), mix with `amix`, music under it with `sidechaincompress`; then `loudnorm=I=-16:TP=-1.5:LRA=11` on the final mix.
- `make_cards_v2.cjs`: the palette from STORYBOARD.md, plus subtitle PNGs (transparent, bottom band) overlaid on their clips. ffmpeg here has no drawtext, so all text is rendered by headless Chrome, as in the original.

### F2. Edit list (`demo/v2/EDIT_v2.txt`)
Format: `file | in | out | layout | caption | audio | narration piece`. In/out times are seconds inside each source clip and are filled in after the takes (marked `?`).

```
-                         | 0 | 6  | black | 8 January 2025. Tirupati. Six people died in a crush for a darshan token. | - | -
-                         | 0 | 6  | black | They were not waiting for God. They were waiting for a number. | - | -
-                         | 0 | 8  | card  | Lakshmamma, 68 // A village near Nellore. // Speaks only Telugu. // Has never booked anything online. | - | P1
raw/phone/P1_lakshmamma.mov | ? | ?+14 | phone-left-with-caption | One tap. Then she just talks. | keep | P2a, P2b
raw/phone/P1_lakshmamma.mov | ? | ?+16 | phone-left-with-caption | She asks what anyone would ask. | keep | P3
raw/phone/P1_lakshmamma.mov | ? | ?+4  | full (crop to the slot card) | Her time is set. 3:00 pm. | - | P3b
-                         | 0 | 2  | card-indigo | Later. Everyone arrives at once. // Simulated crowd. | - | P4a
raw/graph-1280x720.webm   | ? | ?+8  | full | Booking slows down. | - | (P4a cont.)
raw/kube-1280x720.webm    | ? | ?+5  | full | Real Kubernetes. Real crash. | - | P4b
raw/nudgebee-1280x720.webm| ? | ?+11 | full | NudgeBee finds the cause, in its own words. | - | P5
-                         | 0 | 6  | card  | Meera, 20 // Volunteer at the spot counter. // Speaks Malayalam. | - | P6
raw/phone/M1_meera.mov    | ? | ?+8  | phone-left-with-caption | Asked in Malayalam. She says yes. | keep | -
raw/nudgebee-1280x720.webm+raw/flagsmith-1280x720.webm | ? | ?+10 | side-by-side | A person approves. Two flags flip. No redeploy. | - | P7a, P7b
raw/graph-1280x720.webm   | ? | ?+4  | full | (no caption) | - | P8a
-                         | 0 | 4  | card-numbers | Before: 3.1 s, crashed after 19 s // After: 15 ms, 0 crashes, 1,100 requests a second // Local cluster, simulated crowd. | - | (P8a cont.)
raw/phone/P2_after.mov    | ? | ?+4  | phone-left-with-caption | Her slot is still hers. | - | P8b
raw/phone/P3_care.mov     | ? | ?+8  | phone-left-with-caption | One sentence reaches the nearest volunteer. | keep | P9a
raw/elder-390x844.webm+raw/standard-390x844.webm | ? | ?+5 | side-by-side | 65 and over: voice first. Decided by Flagsmith. | - | P9b
raw/sponsors-1280x720.webm| ? | ?+5  | full | All three, live. | - | P9c
-                         | 0 | 12 | card-indigo | The shrine pays about Rs 10 a voice booking. // It costs us about Rs 3.5. // Pilgrims pay nothing. Ever. | - | P10
-                         | 0 | 6  | card  | The crowd is simulated. // The crash and the fix are real. // No shrine uses this yet. | - | P11
raw/phone/P4_steps.mov    | ? | ?+6  | phone-left-with-caption | 3:04 pm. Lakshmamma reached the steps. | - | P12a
-                         | 0 | 4  | black | This time, nobody stood in a crush for a number. | - | P12b
-                         | 0 | 3  | end   | Darshan Rush // Sarvam AI · NudgeBee · Flagsmith // [team names] | - | P12c
```
Sum of durations: 6+6+8+14+16+4+2+8+5+11+6+8+10+4+4+4+8+5+5+12+6+6+4+3 = 165 s = **2:45**.
Subtitle overlays (from VIDEO_SCRIPT.md, the English line for every Telugu and Malayalam line, and the app replies transcribed from the take) go on the `keep` clips at the moment each line is spoken.

### F3. Checks before upload (all must pass)
1. **Length**: `ffprobe` duration under 3:00 (target 2:45).
2. **Subtitles**: every non-English line has an English subtitle, on screen at least 1.5 s and long enough to read (about 15 characters a second). Look at the contact sheet and at each subtitle at 50% screen size.
3. **Loudness**: integrated about **-16 LUFS**, true peak below -1.5 dBTP (`ffmpeg -i out.mp4 -af loudnorm=print_format=summary -f null -`, or the `audio-analyzer` tool). Voice clearly above music; phone clips not quieter than narration by more than 3 dB.
4. **No word cut off**: listen to every cut point, with headphones, once. Each narration piece has at least 0.2 s of air before and after.
5. **No secrets**: step through a frame every 0.5 s of the NudgeBee, Flagsmith, terminal and sponsors segments; no key, token, email, workspace id, tunnel token or notification visible. The tunnel URL may show only if it is still up at submission time.
6. **Honesty labels**: "Simulated crowd" visible on the rush card and the numbers card; "Typed input" on any typed clip; footer on the end card.
7. **Phone playback**: put the final mp4 on the same Drive, open it on Arun's phone and play it once with the sound on and once muted (subtitles and captions alone must tell the story).
8. **Format**: H.264 + AAC, 1920x1080, 30 fps, `+faststart`, under 200 MB.
9. **A cold watch**: one person who has not seen the project watches once and says in one sentence what it does. If they cannot, fix the first 30 s.
