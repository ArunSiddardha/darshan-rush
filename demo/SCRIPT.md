# Darshan Rush: 3-minute demo script (record by 16:00 IST, submit by 17:00)

Rules for the take: plain spoken voice, no reading speed-talk. Every number on screen is labelled SIMULATED where it is. Nothing says or shows a temple logo, a deity or police. Do not claim a booking app ever crashed in real life: say "the crowd is simulated, the failure and the fix are real".
Before each take run `scripts/reset_demo.sh` (full map, open slots, state idle). Do one complete rehearsal first (`scripts/rehearsal.sh`, about 3 minutes).

What past first places did, and where it shows below: a named person and the stakes in the first 15 s (Suraksha, Beacon), the demo first and the architecture last and short (Suraksha, DealDesk), the sponsor named all the way through (DealDesk), an honest limits line (Suraksha, WristHeat).

Narration is what Arun says in English. Total narration: 399 words (counted), about 3 minutes at a relaxed pace; the app speaking fills the gaps.

---

## Beat 1. Hook (0:00 to 0:15) · 61 words · sponsor: none yet
**On screen:** title card "Darshan Rush" for 3 s, then a calm full-screen text card (Anek font, plain): "8 January 2025. Tirupati. Six people died in a crush at a token counter." then the pilgrim phone page on its own.
**Narration:**
"On the eighth of January 2025, at Tirupati, six people died in a crush at a token counter. They were queuing for a number. Nobody should have to stand in a crush for a number. And Sabarimala season is open right now, about eighty thousand people a day. This is Darshan Rush. Meet a grandmother with one phone, and one language."

## Beat 2. The pilgrim talks (0:15 to 0:40) · 36 words · sponsor: **Sarvam**
**On screen:** phone-left-with-caption layout, the pilgrim page at the public URL on Arun's iPhone (language set to Telugu). Mic tapped, her words appear, slot card appears with the time and gate, the slot is read aloud. Caption: "Sarvam: she speaks Telugu, she hears her slot in Telugu".
**Spoken to the app (Telugu), 1st phrase, say it slowly like a grandmother:**
- Telugu: **అమ్మా, రేపు పొద్దున్నే దర్శనానికి ఒక టైమ్ ఇవ్వండి**
- Roman: *Ammaa, repu poddunne darshananiki oka time ivvandi.*
- Meaning: "Please give me a time for darshan early tomorrow morning."
**Narration (over the slot read-back, quietly, while the app voice is playing, then on top of the pause):**
"She just talks. In Telugu. Sarvam turns her speech into text, the app finds her a slot for tomorrow morning, and reads it back to her, out loud, in her own language. No form. No English."
**Then she says (2nd phrase):**
- Telugu: **మా అమ్మకి డెబ్బై ఏళ్లు**
- Roman: *Maa ammaki debbai ellu.*
- Meaning: "My mother is seventy."
(Do this only if it works in the rehearsal. If the app does not react to age, cut this phrase and keep beat 2 at one phrase.)

## Beat 3. The judges cause the rush (0:40 to 1:00) · 47 words · sponsor: none (Kubernetes)
**On screen:** side-by-side: the judge page (QR large, phones counter climbing) and the recovery graph. Cut to Arun's hand pointing at the room. Caption: "Judges: scan the QR, book a slot, now".
**Narration:**
"Now the real test. Judges, scan this code and book a slot, all at once. This is what a festival looks like at the booking server. Every phone that joins makes the heavy full map work harder. We run it on real Kubernetes, with a memory limit."

## Beat 4. It slows, the pod is killed (1:00 to 1:20) · 37 words · sponsor: none (real Kubernetes)
**On screen:** recovery graph: p95 line climbs from about 0.2 s to 3 s. Terminal full screen: `kubectl --context kind-nb -n darshan get pods -w` showing OOMKilled and RESTARTS going to 1. Caption: "Real pod, real OOM kill. Crowd is simulated."
**Narration:**
"Watch the line. Booking gets slower and slower, then the pod runs out of memory and Kubernetes kills it. Here is the restart. The pilgrim is staring at a spinner. That is the moment people start pushing."

## Beat 5. NudgeBee finds the cause (1:20 to 1:40) · 40 words · sponsor: **NudgeBee**
**On screen:** NudgeBee execution view (app.nudgebee.com): the OOMKilled event, the investigation result. Zoom on its words about the memory limit and the heavy map. Caption: "NudgeBee: root cause, in its own words".
**Narration:**
"Nobody is watching a dashboard at this hour. NudgeBee is. It sees the killed pod, investigates, and writes the cause in plain words, here: the heavy map is eating the memory limit. Then it sends that cause to our app."

## Beat 6. The volunteer is asked in Malayalam (1:40 to 2:00) · 35 words · sponsor: **Sarvam**
**On screen:** Arun's phone, volunteer page: the Malayalam question appears with the English line under it, "What NudgeBee found" expanded for a moment. Arun taps the mic and speaks. The page shows what it heard, then "Waiting for the duty officer to confirm in NudgeBee". Caption: "Sarvam: the volunteer answers in Malayalam".
**Spoken to the app (Malayalam), a natural yes:**
- Malayalam: **ശരി, ചെയ്യൂ**
- Roman: *Sari, cheyyu.*
- Meaning: "Okay, do it."
**Narration (over the question appearing, before he speaks):**
"The volunteer on duty is not an engineer. So the app asks in Malayalam, out loud: should we switch to the light version? One spoken yes. Sarvam hears it, and the decision goes to NudgeBee."

## Beat 7. Duty officer confirms; the flags flip (2:00 to 2:15) · 30 words · sponsors: **NudgeBee, Flagsmith**
**On screen:** NudgeBee approval card, a hand clicks Approve (record this on the Mac, see SHOTLIST). Then the Flagsmith dashboard: map_mode changes full to lite, slot_mode open to staggered. Caption: "A person approves. NudgeBee flips the Flagsmith flags".
**Narration:**
"A human still confirms. The duty officer clicks approve in NudgeBee. NudgeBee then changes two Flagsmith flags: map mode to lite, slot mode to staggered. No redeploy. No code change."

## Beat 8. Recovery, numbers before and after (2:15 to 2:35) · 36 words · sponsor: **Flagsmith**
**On screen:** the recovery graph with the drop, then a clean two-column card (from `metrics/rehearsal1.md`, recheck the numbers from the actual take): Before: full map, open slots, p95 up to about 3,100 ms, pod OOM killed after 28 s. After: lite map, staggered slots, p95 about 16 ms, 0 restarts. Caption: "Numbers from our local cluster, simulated crowd".
**Narration:**
"And it recovers. Before: slowest requests over three seconds, and a dead pod after twenty-eight seconds. After: sixteen milliseconds, no restarts. Slots are now staggered across the morning, so nobody is pushed into one crowded window."

## Beat 9. Elders get voice first; the A/B test (2:35 to 2:48) · 34 words · sponsor: **Flagsmith**
**On screen:** the Flagsmith segments view (language trait, age 65 and over) then the A/B card: voice directions vs map directions, metric "reached the gate". Caption: "Flagsmith segment: voice first for 65+. A/B: voice vs map".
**Narration:**
"Flagsmith also decides who sees what. Pilgrims over sixty-five get the voice-first screen. And an A/B test asks a real question: do voice directions get people to the gate more often than a map?"

## Beat 10. Honest limits, and how this differs (2:48 to 3:00) · 43 words · sponsors: all three named in the end card
**On screen:** one end card, three lines (what is simulated / what is real / how it differs), then the end card "Sarvam · NudgeBee · Flagsmith" with the repo URL.
**Narration:**
"What is simulated: the crowd and the gate times. What is real: the Kubernetes failure, NudgeBee's finding, the approval, the flags. Virtual-Q books a slot, the Swami chatbot answers questions. We keep it working, fairly, in your language, when everyone arrives. Thank you."

---

## Word count
Counted per beat: 61, 36, 47, 37, 40, 35, 30, 36, 34, 43 = 399. If you run long in the take, drop the last sentence of beats 3 and 8.

## Spoken phrases at a glance
| Where | Language | Script | Roman | Meaning |
|---|---|---|---|---|
| Pilgrim, request | Telugu | అమ్మా, రేపు పొద్దున్నే దర్శనానికి ఒక టైమ్ ఇవ్వండి | Ammaa, repu poddunne darshananiki oka time ivvandi | Please give me a time for darshan early tomorrow morning |
| Pilgrim, 2nd | Telugu | మా అమ్మకి డెబ్బై ఏళ్లు | Maa ammaki debbai ellu | My mother is seventy |
| Volunteer, yes | Malayalam | ശരി, ചെയ്യൂ | Sari, cheyyu | Okay, do it |
| Volunteer, backup yes | Malayalam | ശരി | Sari | Okay |
(Have a Telugu speaker listen to the two Telugu lines and say them once. If a line is off, ask any Telugu-speaking person at the venue for a more natural wording; the meaning is what matters.)

---

## 90-second cut (if time is short)
Keep: hook, pilgrim, rush and kill, NudgeBee cause, volunteer yes, flags flip with numbers, limits. Cut: elders A/B card (say it in one line), the second Telugu phrase, the side-by-side beat.

| Time | Beat | Narration (about 190 words in all) |
|---|---|---|
| 0:00 to 0:10 | Hook | "On the eighth of January 2025, at Tirupati, six people died in a crush for a token. Nobody should stand in a crush for a number. Sabarimala season is open now. Meet a grandmother with one phone." |
| 0:10 to 0:25 | Pilgrim (Sarvam), phrase 1 only | "She talks in Telugu. Sarvam turns it into text, finds a slot for tomorrow morning, and reads it back in Telugu." |
| 0:25 to 0:42 | Judges scan, graph climbs, pod killed | "Judges, scan and book, all at once. Booking slows, the pod runs out of memory and Kubernetes kills it." |
| 0:42 to 0:55 | NudgeBee cause | "NudgeBee sees it, finds the cause in plain words, and sends it to our app." |
| 0:55 to 1:08 | Volunteer yes (Sarvam) | "The volunteer is asked in Malayalam. One spoken yes. The duty officer confirms in NudgeBee." |
| 1:08 to 1:22 | Flags flip, numbers | "NudgeBee flips two Flagsmith flags: lite map, staggered slots. Slowest requests: three seconds before, sixteen milliseconds after. No restarts." |
| 1:22 to 1:30 | Limits and close | "Crowd simulated. Failure and fix real. Voice-first for elders is a Flagsmith segment, with an A/B test running. Thank you." |

Use the same clips; in EDIT.txt use shorter in/out times and drop the side-by-side line.
