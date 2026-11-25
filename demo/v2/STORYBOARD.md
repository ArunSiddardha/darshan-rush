# Storyboard: Darshan Rush film (16 frames, 1920x1080)

Frame times match VIDEO_SCRIPT.md. Design rules for every frame:
- One idea per frame. If a frame needs two captions, it is two frames.
- Nothing stays on screen permanently except a small sponsor label (top right, 28 px, white text on a 60% indigo pill: "Sarvam AI", "NudgeBee", "Flagsmith"), only while that tool is doing the work.
- Captions are at least 54 px (title cards 72 to 96 px) so they read on a laptop at normal distance. Subtitles 46 px, white with a dark 70% band, bottom centre, two lines at most.
- Title cards use the app's own look (the saffron and indigo theme block in `app/static/style.css`, line 162 onwards): Anek font (`app/static/fonts.css`), background `#FBFAF7`, ink `#1B1B26`, secondary ink `#4E4E60`, saffron `#F26B1D` for one rule or one word, indigo `#2B2E8C` for urgency and money cards (white text on it). In the frames below, "off-white" means `#FBFAF7`, "indigo" means `#2B2E8C`, and "saffron" means `#F26B1D`.
- No stock footage, no clip art, no crowd photos, no temple, deity or police images. Only the real app, the real terminal, the real dashboards, and plain text.
- Phone frames: the real page at 390x844, scaled to 960 px tall with a thin dark bezel (assemble.sh `phone-left-with-caption`), left third; the caption sits in the right two thirds, left aligned, vertically centred.

---

### F1. 0:00 to 0:06. The date
- **Composition:** full black. One line of white text, centred, Anek Regular 64 px, max width 1400 px, fades in over 0.8 s.
- **Text:** "8 January 2025. Tirupati. Six people died in a crush for a darshan token."
- **Eye:** straight to the centre. Nothing else exists.

### F2. 0:06 to 0:12. The number
- **Composition:** same black, F1 text fades out, this fades in at the same spot. Hold 1 s of black after.
- **Text:** "They were not waiting for God. They were waiting for a number."
- **Eye:** the last word. Optional: "a number." in saffron.

### F3. 0:12 to 0:20. Lakshmamma
- **Composition:** off-white card. A short saffron rule above the name. Name 96 px, the three facts 54 px below, one per line. A small 30 px grey line at the bottom.
- **Text:** "Lakshmamma, 68" / "A village near Nellore." / "Speaks only Telugu." / "Has never booked anything online." Bottom: "A fictional pilgrim, voiced by our team."
- **Eye:** the name, then down the three lines in order as the narration reads them.

### F4. 0:20 to 0:34. She just talks
- **Composition:** phone left (pilgrim page, Telugu, live mode). Right: caption. Bottom: subtitle band for her line, then for the app's reply. Sponsor label "Sarvam AI".
- **Caption:** "One tap. Then she just talks."
- **Eye:** the phone screen as her words appear, then the slot card sliding in.

### F5. 0:34 to 0:50. An ordinary question
- **Composition:** same layout. The map opens on the phone; the "You are here" marker moves to River Crossing and pulses. Optional 1.3x push in on the phone over 2 s.
- **Caption:** "She asks what anyone would ask."
- **Subtitles:** her line, then the app's real reply.
- **Eye:** the pulsing marker.

### F6. 0:50 to 0:54. The pass
- **Composition:** full screen, the slot card only (cropped from the phone recording, scaled up, centred on off-white). Soft shadow.
- **Caption (under it):** "Her time is set. 3:00 pm."
- **Eye:** the time on the pass.

### F7. 0:54 to 1:04. Everyone arrives
- **Composition:** 1.5 s indigo card, white 80 px text, small 30 px line under it. Hard cut to the graph page full screen; the p95 line climbing is the only motion.
- **Text:** "Later. Everyone arrives at once." / small: "Simulated crowd."
- **Caption on the graph:** "Booking slows down."
- **Eye:** the climbing line, top right of the plot.

### F8. 1:04 to 1:09. The crash
- **Composition:** full screen terminal (dark), font 28 px or larger. A saffron outline box appears on "OOMKilled" and on the RESTARTS count changing to 1.
- **Caption:** "Real Kubernetes. Real crash."
- **Eye:** the boxed word.

### F9. 1:09 to 1:20. NudgeBee finds why
- **Composition:** full screen NudgeBee execution view. 0 to 4 s: the whole view (the event). 4 to 11 s: slow push in on its own root-cause sentence, with a soft highlight band. Sponsor label "NudgeBee".
- **Caption:** "NudgeBee finds the cause, in its own words."
- **Eye:** the root-cause sentence. Its words must be readable: zoom until the text is at least 40 px on the final frame.

### F10. 1:20 to 1:26. Meera
- **Composition:** same card style as F3.
- **Text:** "Meera, 20" / "Volunteer at the spot counter." / "Speaks Malayalam." / bottom grey: "A fictional volunteer, voiced by our team."
- **Eye:** the name.

### F11. 1:26 to 1:34. One spoken yes
- **Composition:** phone left (volunteer page): the Malayalam question, the English line, "What NudgeBee found" open. Then the mic, what it heard, "Waiting for the duty officer". Sponsor label "Sarvam AI".
- **Caption:** "Asked in Malayalam. She says yes."
- **Subtitles:** the app's question, then "Okay. Do it."
- **Eye:** the question text, then the heard words.

### F12. 1:34 to 1:44. Approve, flip
- **Composition:** split screen, two equal panels with a 16 px gap. Left: NudgeBee approval card; the cursor clicks Approve (show a small ring on the click). Right: Flagsmith feature list; at 1:39 `map_mode` changes full to lite and `slot_mode` open to staggered, each with a saffron flash on the changed value. Labels: "NudgeBee" over the left panel, "Flagsmith" over the right.
- **Caption:** "A person approves. Two flags flip. No redeploy."
- **Eye:** left click, then right values. Never show a key, token or email in either panel (crop or blur the account menu).

### F13. 1:44 to 1:56. It holds
- **Composition:** 0 to 4 s: the graph full screen, line falling to the floor. 4 to 8 s: the before and after card, two columns (saffron "Before", indigo "After"), big numbers 110 px, labels 40 px, small 30 px line at the bottom. 8 to 12 s: Lakshmamma's phone, light map, her pass at the top.
- **Card text:** Before: "3.1 s slowest booking" / "crashed after 19 s". After: "15 ms" / "0 crashes, 1,100 requests a second". Small: "Local cluster, simulated crowd."
- **Caption on the phone part:** "Her slot is still hers."
- **Eye:** 3.1 s, then 15 ms, then her pass.

### F14. 1:56 to 2:14. Three quick truths
- **Composition:** three 5 to 8 s sub-frames, hard cuts, same caption position.
  - a) phone (her care request) then the staff page alert. Caption: "One sentence reaches the nearest volunteer."
  - b) two phones side by side, elder (voice-first) and standard. Caption: "65 and over: voice first. Decided by Flagsmith." Label "Flagsmith".
  - c) the /sponsors page full screen, slow push. Caption: "All three, live." Labels: all three.
- **Eye:** a) the alert card, b) the big talk button on the left phone, c) the three columns of live data.

### F15. 2:14 to 2:32. Money, then honesty
- **Composition:** indigo card, white text 72 px, three lines appearing one per narration sentence. Then an off-white card, three lines 60 px, ink colour.
- **Money text:** "The shrine pays about Rs 10 a voice booking." / "It costs us about Rs 3.5." / "Pilgrims pay nothing. Ever."
- **Honesty text:** "The crowd is simulated." / "The crash and the fix are real." / "No shrine uses this yet."
- **Eye:** each line as it appears. "Pilgrims pay nothing" in saffron.

### F16. 2:32 to 2:45. She reached the steps
- **Composition:** 2:32 to 2:38 phone left: the map with "You are here" at the last stop and the pass showing it is her time; caption right. 2:38 to 2:42 black, white text exactly like F1 and F2 (the film closes the loop). 2:42 to 2:45 the end card on off-white: "Darshan Rush" 120 px, "Sarvam AI · NudgeBee · Flagsmith" 48 px, team names 36 px, footer 26 px.
- **Caption:** "3:04 pm. Lakshmamma reached the steps."
- **Black card text:** "This time, nobody stood in a crush for a number."
- **End card footer:** "Simulated crowd. Not affiliated with any temple. Not for operational use."
- **Eye:** the closing line; it should feel like the answer to F2.
