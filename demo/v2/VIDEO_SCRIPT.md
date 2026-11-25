# Darshan Rush: the film (2:45, hard maximum 3:00)

No stage demo. This video is the whole submission. Judges watch it once, on a laptop, fast.
Goal: feel something by 0:10, understand the product by 0:30, see Sarvam, NudgeBee and Flagsmith do real work, believe it is real, remember one person.

**Rules for the whole film**
- English subtitles under every Telugu and Malayalam line, always, large (see STORYBOARD.md).
- Lakshmamma and Meera are fictional people, voiced by our team. A small caption says so the first time each appears.
- No footage of any event, no temple, deity, police or crowd images. The app, the terminal, the dashboards and plain text cards only.
- Every subtitle for the app's spoken reply is transcribed from the real recorded reply, not from this script. The "expected meaning" below is only a guide.
- Numbers from `metrics/rehearsal1.md` (25 Nov 2026 14:07). If the final recorded take gives different numbers, use the take's numbers and change the narration to match.
- Pause marks in narration: `/` short breath, `//` a full beat (about one second).
- Music: none for the hook. A soft bed from 0:12 only if a licence-clean file exists (RECORDING_PLAN.md e). Always ducked under voice, out completely at 0:54 (rush starts) and back at 1:44 (recovery).

---

## The characters

- **Lakshmamma**, 68, from a village near Nellore. Speaks only Telugu. Has never booked anything online. Travelling with her grandson **Ravi**, 9.
- **Meera**, 20, a college student volunteering at the spot counter. Malayalam speaker. Not an engineer.
- **The duty officer**: off screen. Only his click in NudgeBee is seen.

---

## Second by second

| Time | PICTURE | SOUND | SPONSOR label |
|---|---|---|---|
| **0:00 to 0:06** | Black. One line of white text fades in, centred, Anek, large: **"8 January 2025. Tirupati. Six people died in a crush for a darshan token."** | Silence. Room tone only. | none |
| **0:06 to 0:11** | Text fades out. New line, same place: **"They were not waiting for God. They were waiting for a number."** | Silence. | none |
| **0:11 to 0:12** | Black. | Silence, then the first breath of the music bed (if any). | none |
| **0:12 to 0:20** | Title card, warm off-white, saffron rule: **"Lakshmamma, 68. A village near Nellore. Speaks only Telugu. Has never booked anything online."** Small grey line under it: *A fictional pilgrim, voiced by our team.* | **Narration P1 (quiet):** "This is Lakshmamma. / She is sixty-eight. / She speaks only Telugu. / She has never booked anything online." | none |
| **0:20 to 0:24** | Phone on the left (pilgrim page, Telugu, live mode). A finger taps "Tap once to start talking". Right side caption: **"One tap. Then she just talks."** | **Narration P2a (warm):** "She taps once. / And she just talks." | Sarvam |
| **0:24 to 0:28** | Her words appear on the phone as she speaks. Subtitle bottom. | **Lakshmamma (Telugu):** ఈ రోజు దర్శనానికి ఒక టైమ్ కావాలి, నాయనా. *Ee roju darshananiki oka time kaavaali, naayanaa.* Subtitle: **"I need a time for darshan today, dear."** | Sarvam: speech to text |
| **0:28 to 0:34** | The slot card slides in like a pass (time window, gate name, SIMULATED tag). The app speaks. | **App (Telugu), real reply.** Expected meaning, subtitle from the real audio: **"Your darshan time is 3:00 to 3:10 in the afternoon, at Forest Path."** Under the end of it, **Narration P2b (warm):** "No form. / No English." | Sarvam: text to speech |
| **0:34 to 0:42** | Same phone, still listening (no second tap). | **Lakshmamma (Telugu):** నేను రివర్ క్రాసింగ్ దగ్గర ఉన్నాను. మోకాళ్ళు నొప్పిగా ఉన్నాయి. కూర్చోడానికి చోటు ఉందా? *Nenu river crossing daggara unnaanu. Mokaallu noppigaa unnaayi. Koorchodaaniki chotu undaa?* Subtitle: **"I am at River Crossing. My knees hurt. Is there somewhere to sit?"** | Sarvam |
| **0:42 to 0:50** | The site map opens on the phone. The "You are here" marker slides to River Crossing and pulses; the rest icon near it lights. Caption right: **"She asks what anyone would ask."** | **App (Telugu), real reply.** Expected meaning: **"There is a rest place with water at River Crossing. Your gate is 12 minutes' walk from there."** Then **Narration P3 (warm):** "The map shows her where she is. / And where to sit." | Sarvam (voice), venue knowledge pack |
| **0:50 to 0:54** | Full screen: just the slot pass, big. Caption: **"Her time is set. 3:00 pm."** | **Narration P3b (warm):** "Her time is set. / She can rest until then." | none |
| **0:54 to 1:04** | Hard cut. Card on indigo: **"Later. Everyone arrives at once."** small line *Simulated crowd.* Then the live graph: the p95 line climbing from 0.2 s to 3 s, phones counter rising. | Music out. A low steady tick (room tone). **Narration P4a (urgent):** "Then / everyone arrives at once. // The booking service slows." | none (Kubernetes) |
| **1:04 to 1:09** | Full-screen terminal, large font: `kubectl get pods -w` line with **OOMKilled** and RESTARTS going from 0 to **1** (highlight box on those two words). Caption: **"Real Kubernetes. Real crash."** | **Narration P4b (urgent):** "Then Kubernetes kills it. / This crash is real." | none (Kubernetes) |
| **1:09 to 1:20** | The real NudgeBee execution view: OOMKilled event, then zoom into its own root-cause text (memory limit, heavy map render). Caption: **"NudgeBee finds the cause, in its own words."** | **Narration P5 (urgent, slower):** "Nobody is watching a dashboard. / NudgeBee is. // It finds the cause, / in plain words. / The heavy map ate the memory." | **NudgeBee** |
| **1:20 to 1:26** | Card: **"Meera, 20. Volunteer at the spot counter. Speaks Malayalam."** small grey line *A fictional volunteer, voiced by our team.* | **Narration P6 (steady):** "Meera runs the spot counter. / She is a student, / not an engineer. / So the app asks her, in Malayalam." | none |
| **1:26 to 1:31** | Phone on the left: the volunteer page, the Malayalam question on screen, English line under it, "What NudgeBee found" open. The question is spoken. | **App (Malayalam), real question.** Subtitle = the English line the volunteer page shows under it (expected: **"Bookings are failing. Shall we switch to the light map and staggered slots?"**) | Sarvam: text to speech |
| **1:31 to 1:34** | Meera taps the mic and answers. The page shows what it heard, then "Waiting for the duty officer to confirm in NudgeBee". | **Meera (Malayalam):** ശരി, ചെയ്യൂ. *Sari, cheyyu.* Subtitle: **"Okay. Do it."** | Sarvam: speech to text |
| **1:34 to 1:39** | Split screen. Left: NudgeBee approval card; the cursor clicks **Approve**. Right: Flagsmith dashboard, flags as they were (`map_mode` full, `slot_mode` open). | **Narration P7a (steady):** "A duty officer confirms in NudgeBee." | **NudgeBee** |
| **1:39 to 1:44** | Right side: Flagsmith flips, `map_mode` full to **lite**, `slot_mode` open to **staggered** (highlight each change). Caption: **"No redeploy. Two flags."** | **Narration P7b (steady):** "Two Flagsmith flags flip. / A light map. / Staggered slots. / No redeploy." | **Flagsmith** (flipped by NudgeBee) |
| **1:44 to 1:52** | The graph: the line drops to the floor and stays there. Then the before and after card, two columns, saffron left, indigo right: **Before: slowest 3.1 s, crashed after 19 s.** **After: slowest 15 ms, 0 crashes, 1,100 requests a second.** Small line: *Local cluster, simulated crowd.* | Music back, soft. **Narration P8a (relieved):** "Before, / the slowest booking took three seconds, / and the service died in nineteen. // After, / fifteen milliseconds. / No crash." | **Flagsmith** |
| **1:52 to 1:56** | Lakshmamma's phone again: light map (plain list), her slot pass unchanged at the top. Caption: **"Her slot is still hers."** | **Narration P8b (relieved, warm):** "And Lakshmamma's slot / is still hers." | Flagsmith (lite map) |
| **1:56 to 2:04** | Phone left (pilgrim). She speaks. Then cut to the staff page: a care alert at the nearest stop with her words in English and the volunteer it went to, exactly as the screen shows it. **Check first:** nearest-volunteer routing needs `addons_care` live (RECORDING_PLAN.md B5). If it is not live, show the real calm reply and the help note, use caption "One sentence leaves a note for the volunteers" and narration P9a-alt. | **Lakshmamma (Telugu):** నా మనవడు కనిపించడం లేదు. *Naa manavadu kanipinchadam ledu.* Subtitle: **"I can't find my grandson."** **Narration P9a (brisk):** "When Ravi wanders off, / one sentence reaches the nearest volunteer." | Sarvam |
| **2:04 to 2:09** | Split: two phones side by side. Left: a 65+ visitor gets the voice-first screen (one big talk button). Right: a younger visitor gets the standard screen. Caption: **"65 and over: voice first. Decided by Flagsmith."** | **Narration P9b (brisk):** "Everyone over sixty-five gets voice first. / Flagsmith decides that." | **Flagsmith** (segment) |
| **2:09 to 2:14** | The /sponsors page, full screen: Sarvam calls, Flagsmith flags with change times, NudgeBee chain lit. Slow push in. Caption: **"All three, live."** | **Narration P9c (proud):** "All three tools, / live, / on one page." | Sarvam · NudgeBee · Flagsmith |
| **2:14 to 2:26** | Money card, white on indigo, three lines appear one by one: **"The shrine pays about Rs 10 a voice booking."** / **"It costs us about Rs 3.5."** / **"Pilgrims pay nothing. Ever."** | **Narration P10 (plain, proud):** "Who pays? / The shrine. / About ten rupees for a voice booking. / It costs us three and a half. // Pilgrims never pay. / No ads. / No selling data." | none |
| **2:26 to 2:32** | Plain card, three short lines: **"The crowd is simulated. The crash and the fix are real. No shrine uses this yet."** | **Narration P11 (honest, even):** "The crowd is simulated. / The crash and the fix are real. / No shrine uses this yet." | none |
| **2:32 to 2:38** | Lakshmamma's phone: the map with "You are here" at the last stop, the pass glowing "Your time: now". Caption: **"3:04 pm. Lakshmamma reached the steps."** | **Narration P12a (quiet):** "At three o'clock, / Lakshmamma reached the steps." | none |
| **2:38 to 2:42** | Black. White text, same font as the opening: **"This time, nobody stood in a crush for a number."** | **Narration P12b (quiet, slow):** "This time, / nobody stood in a crush / for a number." | none |
| **2:42 to 2:45** | End card: **Darshan Rush**. Under it: **Sarvam AI · NudgeBee · Flagsmith**. Under that: team names. Footer: *Simulated crowd. Not affiliated with any temple. Not for operational use.* | **Narration P12c:** "Darshan Rush." Music resolves and ends. | all three names |

Total: 2:45. Room to breathe up to 3:00 if the app replies run long: let the replies play in full rather than cut a word.

---

## Narration only (what Arun reads), with emotion

Read slowly. Smile on P2 and P8. Drop your voice on P1 and P12. Do not rush the numbers.

- **P1, quiet.** This is Lakshmamma. / She is sixty-eight. / She speaks only Telugu. / She has never booked anything online.
- **P2a, warm.** She taps once. / And she just talks.
- **P2b, warm.** No form. / No English.
- **P3, warm.** The map shows her where she is. / And where to sit.
- **P3b, warm.** Her time is set. / She can rest until then.
- **P4a, urgent.** Then / everyone arrives at once. // The booking service slows.
- **P4b, urgent.** Then Kubernetes kills it. / This crash is real.
- **P5, urgent but slower.** Nobody is watching a dashboard. / NudgeBee is. // It finds the cause, / in plain words. / The heavy map ate the memory.
- **P6, steady.** Meera runs the spot counter. / She is a student, / not an engineer. / So the app asks her, in Malayalam.
- **P7a, steady.** A duty officer confirms in NudgeBee.
- **P7b, steady.** Two Flagsmith flags flip. / A light map. / Staggered slots. / No redeploy.
- **P8a, relieved.** Before, / the slowest booking took three seconds, / and the service died in nineteen. // After, / fifteen milliseconds. / No crash.
- **P8b, relieved, warm.** And Lakshmamma's slot / is still hers.
- **P9a, brisk.** When Ravi wanders off, / one sentence reaches the nearest volunteer.
- **P9b, brisk.** Everyone over sixty-five gets voice first. / Flagsmith decides that.
- **P9c, proud.** All three tools, / live, / on one page.
- **P10, plain, proud.** Who pays? / The shrine. / About ten rupees for a voice booking. / It costs us three and a half. // Pilgrims never pay. / No ads. / No selling data.
- **P11, honest, even.** The crowd is simulated. / The crash and the fix are real. / No shrine uses this yet.
- **P12a, quiet.** At three o'clock, / Lakshmamma reached the steps.
- **P12b, quiet, slow.** This time, / nobody stood in a crush / for a number.
- **P12c.** Darshan Rush.

About 280 words. At a calm pace (about 135 words a minute) that is about 2:05 of voice, leaving the rest for her lines, the app's replies and silence.

---

## Spoken lines in Telugu and Malayalam

Say them slowly, like the person would. If a native speaker at the venue offers a more natural wording, use theirs and change the subtitle to match its meaning.

| Who | When | Native script | Read aloud like this | English subtitle |
|---|---|---|---|---|
| Lakshmamma | 0:24 | ఈ రోజు దర్శనానికి ఒక టైమ్ కావాలి, నాయనా. | Ee ROH-ju dar-sha-NAA-ni-ki oka time KAA-vaa-li, NAA-ya-naa. | I need a time for darshan today, dear. |
| Lakshmamma | 0:34 | నేను రివర్ క్రాసింగ్ దగ్గర ఉన్నాను. మోకాళ్ళు నొప్పిగా ఉన్నాయి. కూర్చోడానికి చోటు ఉందా? | NAY-nu river crossing DAG-ga-ra un-NAA-nu. MO-kaal-lu NOP-pi-gaa un-NAA-yi. KOOR-cho-DAA-ni-ki CHO-tu un-DAA? | I am at River Crossing. My knees hurt. Is there somewhere to sit? |
| Lakshmamma (spare) | if needed | తాగడానికి నీళ్ళు ఎక్కడ ఉన్నాయి? | TAA-ga-DAA-ni-ki NEEL-lu EK-ka-da un-NAA-yi? | Where is drinking water? |
| Lakshmamma | 1:56 | నా మనవడు కనిపించడం లేదు. | Naa MA-na-va-du ka-ni-PIN-cha-dam LAY-du. | I can't find my grandson. |
| Meera | 1:31 | ശരി, ചെയ്യൂ. | SHA-ri, CHEY-yoo. | Okay. Do it. |
| Meera (backup) | 1:31 | ശരി. | SHA-ri. | Okay. |
| Meera (if nobody speaks Malayalam) | 1:31 | సరే, చేయండి. (Telugu) | SA-ray, CHAY-yan-di. | Okay. Do it. |

If Meera's line is said in Telugu, change P6 to "So the app asks her, in her own language." and her card to "Meera, 20. Volunteer at the spot counter." The volunteer page must then be set to Telugu so the question and the answer match. Do not dub a Malayalam yes over a Telugu speaker.

App replies (Telugu slot readback, Telugu map answer, Malayalam question): use the real audio from the recording and transcribe the subtitle from what the app actually said (the reply text is on the phone screen; translate that).

---

## 90-second cut

Same clips, shorter. Narration about 170 words.

| Time | Beat | Keep / change |
|---|---|---|
| 0:00 to 0:09 | Hook | Both text lines, 4.5 s each. No narration. |
| 0:09 to 0:14 | Lakshmamma card | P1 shortened: "This is Lakshmamma. / Sixty-eight. / Only Telugu." |
| 0:14 to 0:26 | Booking line, slot pass appears, app reply (trim to the time and gate) | P2b "No form. / No English." |
| 0:26 to 0:34 | Knees line, map marker moves | Cut the app reply to its first sentence. No narration. |
| 0:34 to 0:42 | Graph climbs, terminal OOMKilled | P4a + P4b joined: "Then everyone arrives at once. / Kubernetes kills the service. / This crash is real." |
| 0:42 to 0:50 | NudgeBee root cause | "NudgeBee finds the cause, / in plain words." |
| 0:50 to 0:58 | Meera: question plus "Sari, cheyyu" | "Meera, a volunteer, says yes in Malayalam." (over the question, before her line) |
| 0:58 to 1:06 | Approve click, flags flip (split) | P7a + P7b shortened: "The duty officer confirms. / Two Flagsmith flags flip. / No redeploy." |
| 1:06 to 1:12 | Before and after card | "Three seconds before. / Fifteen milliseconds after. / No crash." |
| 1:12 to 1:20 | Money card | "The shrine pays about ten rupees a booking. / It costs us three and a half. / Pilgrims never pay." |
| 1:20 to 1:24 | Honesty card | P11 as is. |
| 1:24 to 1:30 | Closing line + end card | P12b, then the end card with the three sponsor names. |

Cut entirely: the care request, the elders split, the sponsors page, "her slot is still hers" (keep it as a 1-second caption on the numbers card if it fits).

## 60-second cut

| Time | Beat | Narration |
|---|---|---|
| 0:00 to 0:07 | Hook, both lines, 3.5 s each | none |
| 0:07 to 0:18 | Booking line in Telugu, slot pass, first sentence of the reply | "Lakshmamma speaks only Telugu. / She just talks." |
| 0:18 to 0:26 | Graph climbs, OOMKilled in the terminal | "Then everyone arrives. / Kubernetes kills the service. / Really." |
| 0:26 to 0:32 | NudgeBee root cause | "NudgeBee finds why." |
| 0:32 to 0:38 | Meera: "Sari, cheyyu" | none (subtitle only) |
| 0:38 to 0:45 | Approve, flags flip, graph drops | "One yes. / Two Flagsmith flags. / Three seconds becomes fifteen milliseconds." |
| 0:45 to 0:52 | Money card | "Shrines pay ten rupees a booking. / Pilgrims never pay." |
| 0:52 to 1:00 | Honesty line as small text, closing line, end card | "This time, / nobody stood in a crush for a number." |
