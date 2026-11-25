# Darshan Rush: the film, 1:50 cut (hard maximum 1:58)

The form says the video must be under 2 minutes. This cut runs 1:50 and leaves 8 s of slack for app replies that run long. If the edit passes 1:58, cut in this order: shorten the honesty card to 4 s, trim the end card to 4 s, trim the knees reply to its first clause.

Same rules as `VIDEO_SCRIPT.md`: English subtitles under every Telugu and Malayalam line; fictional-person caption the first time each person appears; no event, temple, deity, police or crowd imagery; subtitles for app replies come from the real recorded reply; numbers from `metrics/rehearsal1.md` (change narration and the numbers card together if the final take differs). Music: none for the hook, soft bed from 0:08, out at 0:30, back at 1:04.

The **SPONSOR label** column is the small on-screen tag (bottom left, same style as the full film). Totals at the end.

---

## Second by second

| Time | PICTURE | SOUND | SPONSOR label |
|---|---|---|---|
| **0:00 to 0:04** | Black. White text: **"8 January 2025. Tirupati. Six people died in a crush for a darshan token."** | Silence. | none |
| **0:04 to 0:08** | New line: **"They were not waiting for God. They were waiting for a number."** | Silence. | none |
| **0:08 to 0:13** | Card: **"Lakshmamma, 68. A village near Nellore. Speaks only Telugu. Has never booked anything online."** Small grey line: *A fictional pilgrim, voiced by our team.* | **Narration P1 (shortened):** "This is Lakshmamma. / Sixty-eight. / Only Telugu." | none |
| **0:13 to 0:17** | Phone left (pilgrim page, Telugu, live mode), one tap, her words appear on screen. Caption right: **"One tap. Then she just talks."** | **Lakshmamma (Telugu):** ఈ రోజు దర్శనానికి ఒక టైమ్ కావాలి, నాయనా. Subtitle: **"I need a time for darshan today, dear."** | **Sarvam: speech to text, language detected** |
| **0:17 to 0:23** | Slot pass slides in (time window, gate, SIMULATED tag). App speaks. | **App (Telugu), real reply,** trimmed to the time and gate. Under its end, **Narration P2b (kept):** "No form. / No English." | **Sarvam: text to speech** |
| **0:23 to 0:30** | Same phone, no second tap. Map opens, "You are here" slides to River Crossing and pulses, rest icon lights. Caption: **"She asks what anyone would ask."** | **Lakshmamma (Telugu):** నేను రివర్ క్రాసింగ్ దగ్గర ఉన్నాను. మోకాళ్ళు నొప్పిగా ఉన్నాయి. కూర్చోడానికి చోటు ఉందా? Subtitle: **"I am at River Crossing. My knees hurt. Is there somewhere to sit?"** Then the first sentence of the real reply. No narration. | **Sarvam** |
| **0:30 to 0:34** | Hard cut. Card on indigo: **"Later. Everyone arrives at once."** *Simulated crowd.* Then the graph, p95 climbing. | Music out. **Narration P4a (shortened):** "Then everyone arrives at once." | none (Kubernetes) |
| **0:34 to 0:39** | Terminal, large: **OOMKilled**, RESTARTS 0 to **1** (boxes on both). Caption: **"Real Kubernetes. Real crash."** | **Narration P4b (kept):** "Then Kubernetes kills it. / This crash is real." | none (Kubernetes) |
| **0:39 to 0:48** | NudgeBee execution view: the event, then zoom into its own root-cause text (exit code 137, memory limit reached). Caption: **"NudgeBee finds the cause, in its own words."** | **Narration P5 (shortened):** "Nobody is watching a dashboard. / NudgeBee is. // It finds the cause, / in plain words." | **NudgeBee: investigation** |
| **0:48 to 0:52** | Volunteer page on the phone: the Malayalam question, English line under it, "What NudgeBee found" open. Top caption: **"Meera, 20, volunteer at the spot counter."** *A fictional volunteer, voiced by our team.* The question is spoken. | **App (Malayalam), real question** (subtitle = the English line on the page). Over its first second, **Narration P6 (shortened):** "So the app asks Meera, in Malayalam." | **Sarvam: text to speech** |
| **0:52 to 0:55** | Meera taps the mic. The page shows what it heard, then "Waiting for the duty officer to confirm in NudgeBee". | **Meera (Malayalam):** ശരി, ചെയ്യൂ. Subtitle: **"Okay. Do it."** | **Sarvam: speech to text** |
| **0:55 to 0:59** | Split. Left: NudgeBee approval card, cursor clicks **Approve**. Right: Flagsmith, `map_mode` full, `slot_mode` open. | **Narration P7a (kept):** "A duty officer confirms in NudgeBee." | **NudgeBee: approval** |
| **0:59 to 1:04** | Left: NudgeBee HTTP tasks marked done. Right: Flagsmith flips `map_mode` to **lite**, `slot_mode` to **staggered** (highlight each). Caption: **"No redeploy. Two flags."** | **Narration P7b (kept):** "Two Flagsmith flags flip. / A light map. / Staggered slots. / No redeploy." | **NudgeBee flips Flagsmith** |
| **1:04 to 1:12** | Graph drops to the floor, then the numbers card: **Before: slowest 3.1 s, crashed after 19 s. After: slowest 15 ms, 0 crashes, 1,100 requests a second.** *Local cluster, simulated crowd.* Small tag top right: `map_mode=lite` `slot_mode=staggered`. | Music back, soft. **Narration P8a (kept):** "Before, / the slowest booking took three seconds, / and the service died in nineteen. // After, / fifteen milliseconds. / No crash." | **Flagsmith: lite map, staggered slots** |
| **1:12 to 1:15** | Lakshmamma's phone: light map, her pass unchanged at the top. Caption: **"Her slot is still hers."** | **Narration P8b (kept):** "And Lakshmamma's slot / is still hers." | **Flagsmith: lite map** |
| **1:15 to 1:21** | Phone left: she speaks. Cut to the staff page: the care request with her words in English and the volunteer it went to, exactly as the screen shows. (If routing is not live: the calm reply and the help note, caption "One sentence leaves a note for the volunteers", narration P9a-alt.) | **Lakshmamma (Telugu):** నా మనవడు కనిపించడం లేదు. Subtitle: **"I can't find my grandson."** **Narration P9a (kept):** "When Ravi wanders off, / one sentence reaches the nearest volunteer." | **Sarvam** |
| **1:21 to 1:27** | Phone: she asks; the reply text appears, the map shows the route ahead. Caption: **"Ask anything."** | **Lakshmamma (Telugu):** ఇక్కడి నుండి దర్శనం వరకు ఎన్ని మెట్లు? *Ikkadi nundi darshanam varaku enni metlu?* Subtitle: **"How many steps from here to darshan?"** Then the real reply, first sentence only (expected meaning from `app/route_facts.py`: about 440 steps from River Crossing; subtitle from the real audio). No narration. | **Sarvam** |
| **1:27 to 1:34** | Money card, three lines one by one: **"The shrine pays about Rs 10 a voice booking."** / **"It costs us about Rs 3.5."** / **"Pilgrims pay nothing. Ever."** | **Narration P10 (shortened):** "The shrine pays about ten rupees a voice booking. / It costs us three and a half. / Pilgrims never pay." | none |
| **1:34 to 1:39** | Plain card: **"The crowd is simulated. The crash and the fix are real. No shrine uses this yet."** | **Narration P11 (kept):** "The crowd is simulated. / The crash and the fix are real. / No shrine uses this yet." | none |
| **1:39 to 1:44** | Black. White text: **"This time, nobody stood in a crush for a number."** | **Narration P12b (kept):** "This time, / nobody stood in a crush / for a number." | none |
| **1:44 to 1:50** | End card: **Darshan Rush**, then **Sarvam AI · NudgeBee · Flagsmith**, team names, footer *Simulated crowd. Not affiliated with any temple. Not for operational use.* | **Narration P12c (kept):** "Darshan Rush." Music resolves. | all three names |

Total: 1:50.

### Sponsor screen time (labelled seconds)
- **Sarvam:** 0:13 to 0:30 (17 s) + 0:48 to 0:55 (7 s) + 1:15 to 1:27 (12 s) = **36 s**.
- **NudgeBee:** 0:39 to 0:48 (9 s) + 0:55 to 0:59 (4 s) + 0:59 to 1:04 (5 s) = **18 s**.
- **Flagsmith:** 0:59 to 1:04 (5 s) + 1:04 to 1:12 (8 s) + 1:12 to 1:15 (3 s) = **16 s** (plus the before state on screen 0:55 to 0:59).
Each is above 15 s. Do not trim 0:59 to 1:15 without checking these totals again.

---

## Narration: what is reused

Arun's recorded paragraphs (`RECORDING_PLAN.md` section C) are reused where marked "kept". Shortened lines can be cut from the recorded take where the words exist; where they do not, record the new words below (one quiet take, same mic, about 20 s in total).

**Kept as recorded:** P2b, P4b, P7a, P7b, P8a, P8b, P9a (or P9a-alt), P11, P12b, P12c.

**Shortened (new words):**
- **P1** to: "This is Lakshmamma. / Sixty-eight. / Only Telugu." (new take; the recorded P1 is too long for 5 s)
- **P4a** to: "Then everyone arrives at once." (cut from the recorded P4a: drop "The booking service slows.")
- **P5** to: "Nobody is watching a dashboard. / NudgeBee is. // It finds the cause, / in plain words." (cut from the recorded P5: drop "The heavy map ate the memory.")
- **P6** to: "So the app asks Meera, in Malayalam." (new take; if Meera's yes is in Telugu: "So the app asks Meera, in her own language.")
- **P10** to: "The shrine pays about ten rupees a voice booking. / It costs us three and a half. / Pilgrims never pay." (new take, or use the money line from N90 and the end of P10)

**Dropped:** P2a, P3, P3b, P9b, P9c, P12a.

---

## Edit list

Timeline 1920x1080, 30 fps. Cards are in `demo/v2/cards/clips/` (all 1920x1080). Captures named as in `RECORDING_PLAN.md`: lead captures in `demo/v2/raw/`, phone takes in `demo/v2/raw/phone/`. "Phone left" layout = `example_split.mp4` (phone on the left, caption on the right); "full" = full frame.

| # | Timeline | Clip | In | Out | Layout | Caption / label |
|---|---|---|---|---|---|---|
| 1 | 0:00 to 0:04 | `cards/clips/01_hook1.mp4` (6 s) | 0:01 | 0:05 | full | none |
| 2 | 0:04 to 0:08 | `cards/clips/02_hook2.mp4` (6 s) | 0:01 | 0:05 | full | none |
| 3 | 0:08 to 0:13 | `cards/clips/03_lakshmamma.mp4` (8 s) | 0:00 | 0:05 | full | (on card) |
| 4 | 0:13 to 0:30 | `raw/phone/P1_lakshmamma.mov`, best take | her first word minus 0.5 s | first sentence of the knees reply done | phone left | "One tap. Then she just talks." / "She asks what anyone would ask."; labels Sarvam; Telugu subtitles. Cut the confirm exchange ("Avunu") if it appears; jump-cut on the pass. |
| 5 | 0:30 to 0:32.5 | `cards/clips/04_later.mp4` (2.5 s) | 0:00 | 0:02.5 | full | (on card) |
| 6 | 0:32.5 to 0:34 | `raw/graph-1280x720.webm`, state G2 | G2 start | +1.5 s | full, scaled | none |
| 7 | 0:34 to 0:39 | `raw/kube-1280x720.webm`, K2 to K3 | 1 s before K2 | +5 s | full, zoom so text is 28 px or more | "Real Kubernetes. Real crash." |
| 8 | 0:39 to 0:48 | NudgeBee capture, N1 then N2 | N1 (2 s), then N2 hold | 9 s total | full, slow zoom into the root-cause text | "NudgeBee finds the cause, in its own words."; label NudgeBee |
| 9 | 0:48 to 0:55 | `raw/phone/M1_meera.mov` | question starts | "Waiting for the duty officer" shown | phone left | top line from `cards/clips/05_meera_ml.mp4` text (or `05_meera_neutral.mp4` if the yes is Telugu) as an overlay; subtitles; label Sarvam |
| 10 | 0:55 to 1:04 | Left: NudgeBee capture N3 to N5. Right: Flagsmith capture F1 to F2 | N3 / F1 | N5 / F2 | split 50/50 | "No redeploy. Two flags." at 0:59; labels NudgeBee, then "NudgeBee flips Flagsmith" |
| 11 | 1:04 to 1:05 | `raw/graph-1280x720.webm`, G3 to G4 | G4 start minus 0.5 s | +1 s | full | none |
| 12 | 1:05 to 1:12 | `cards/clips/06_numbers.mp4` (7 s) | 0:00 | 0:07 | full | overlay tag `map_mode=lite slot_mode=staggered`; label Flagsmith |
| 13 | 1:12 to 1:15 | `raw/phone/P2_after.mov` (spare: `raw/` L1) | 0:02 | 0:05 | phone left | "Her slot is still hers."; label Flagsmith |
| 14 | 1:15 to 1:21 | `raw/phone/P3_care.mov` (3 s), then `raw/` C1 (3 s) | her first word | +6 s | phone left, then staff page phone left | as shown on screen only; label Sarvam |
| 15 | 1:21 to 1:27 | `raw/phone/P5_steps_q.mov` (NEW take, see below) | her first word | first sentence of the reply | phone left | "Ask anything."; label Sarvam |
| 16 | 1:27 to 1:34 | `cards/clips/07_money.mp4` (12 s) | 0:00 | 0:07 | full | (on card). Check that all three lines are in by 0:07; if not, speed the clip to 170 percent rather than cut a line. |
| 17 | 1:34 to 1:39 | `cards/clips/08_honesty.mp4` (6 s) | 0:00 | 0:05 | full | (on card) |
| 18 | 1:39 to 1:44 | `cards/clips/09_closing.mp4` (4 s) | 0:00 | 0:04, then hold the last frame 1 s | full | (on card) |
| 19 | 1:44 to 1:50 | `cards/clips/10_end.mp4` (4 s) | 0:00 | 0:04, then hold the last frame 2 s | full | (on card) |

**New phone take P5_steps_q (about 15 s):** same Lakshmamma tab, after P3. Say **"Ikkadi nundi darshanam varaku enni metlu?"** (ఇక్కడి నుండి దర్శనం వరకు ఎన్ని మెట్లు? "How many steps from here to darshan?"). The assistant's rules catch "enni metlu" (`app/assistant.py`), so it answers from `app/route_facts.py` without a model call. Let the reply play, wait 2 s, stop. If it is not understood, use the existing `P4_steps.mov` and change the caption to "Ask anything: where am I?".

**Final checks:** `ffprobe` the export (under 1:58), watch it once at full screen with sound, check every subtitle against the real reply, and check no frame shows an email, workspace id, key or notification.
