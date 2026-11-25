# Submission form: ready-to-paste answers

Paste each block under the matching form label. Replace VIDEO_URL and LIVE_URL. Facts checked against the code in `app/` and the notes on 25 Nov 2026. Numbers: `metrics/rehearsal1.md` (25 Nov 2026 14:07) unless stated.

---

## Before you press submit

- [ ] Repository https://github.com/ArunSiddardha/darshan-rush is public (open it in a private window, logged out).
- [ ] Video is under 2 minutes (target 1:50, see `VIDEO_SCRIPT_110s.md`), uploaded as unlisted or public, and plays in a private window.
- [ ] LIVE_URL opens in a private window on a phone. If the tunnel is down, say so in the Live demo field rather than leaving a dead link.
- [ ] README has the real video link and live link (no VIDEO_URL, LIVE_URL, NUDGEBEE_RUN_PROOF_LINK or TEAM_MEMBER placeholders left).
- [ ] Team members are listed in the README and on the form.
- [ ] Every number in answer 5 matches the number on screen in the final video (if the final take differs from 19 s / 3.1 s / 15 ms, change both).
- [ ] Submit well before 15:30, when judges are assigned. Late edits may not be reviewed.

---

## Project title

**Darshan Rush: a voice-first darshan assistant that stays fair when everyone arrives at once**

Alternatives:
1. Darshan Rush: speak in your language, get a fair slot, even in a rush
2. Darshan Rush: a pilgrim's voice assistant that keeps working when the crowd arrives
3. Darshan Rush: voice booking for shrines, with a volunteer who approves the fix by voice

---

## Repository

https://github.com/ArunSiddardha/darshan-rush

---

## Demo video

VIDEO_URL

---

## Live demo

LIVE_URL

Note: this is a temporary Cloudflare quick tunnel to our local kind cluster, so the address can change if the tunnel restarts and it may be offline after the event. The film shows everything the live link does. Open it on a phone, tap once and talk.

---

## What did you build and how does it work?

On 8 January 2025, six people died in a crush at a darshan token counter in Tirupati. The Sabarimala season is open now, with about 80,000 pilgrims a day. Booking systems fail on the day everyone arrives at once.

Darshan Rush serves one person: an elderly pilgrim like Lakshmamma, 68, who speaks only Telugu and has never booked anything online. She taps once and talks, hands-free, in any of six Indian languages, detected from her speech. She books a darshan slot and hears it read back. She can ask anything: the wait at each stop, the way, how many steps are left, where to find water, help for an elder. A simulated site map shows "You are here", the waits and the facilities. If her grandson goes missing, one sentence becomes a tracked help request that goes to the nearest on-duty volunteer.

Temple staff get a volunteer page: walk-in booking for pilgrims without a phone, voice crowd reports, "Ask anything" about waits and open requests, and care requests to close.

What happens in a rush:
1. Everyone books at once. The pod on our Kubernetes cluster runs out of memory and is OOMKilled (a real kernel kill, 19 s into the rush in the recorded rehearsal, about 23 s in today's runs).
2. NudgeBee's agent sees the event, investigates and posts the root cause to our app: exit code 137, memory limit reached.
3. The app asks the volunteer, Meera, by voice in Malayalam whether to switch to the light map and staggered slots. She says "Sari, cheyyu" ("Okay, do it").
4. Her yes starts a NudgeBee approval workflow. A duty officer clicks Approve in NudgeBee.
5. NudgeBee's HTTP tasks flip two Flagsmith flags: `map_mode` to `lite` and `slot_mode` to `staggered`. No redeploy.
6. The same rush runs with no restart. Slowest booking (p95): 3.1 s before, 15 ms after; 1,107 requests a second at peak; 801 bookings kept.

Each tool does a job the others cannot: Sarvam is the voice, NudgeBee finds the cause and holds the human approval, Flagsmith changes behaviour in seconds without a deploy.

What is simulated: the crowd, the waits, the route, the volunteer roster and the venue facts ("Demo Hill Shrine"). The rush load is a generator inside the pod with deliberate memory hunger. The crash, the NudgeBee investigation, the approval, the flag flip and the voice are real. No shrine uses this yet.

How it differs: booking portals book, chatbots answer text, command centres serve officials. This takes speech, answers aloud, books, shows the way, and lets a volunteer approve a fix by voice.

Business model: the shrine pays about Rs 10 per voice booking and it costs us about Rs 3.5 in Sarvam calls. Pilgrims never pay, with no ads and no data sales.

---

## How have you used Flagsmith and what problem does it solve?

Flagsmith is the switch that saves a rush. The flags `map_mode` (`full` or `lite`) and `slot_mode` (`open` or `staggered`) decide whether every request builds the heavy live map and whether bookings pile into the first free window. When the pod is dying, NudgeBee flips both through the Flagsmith Admin API, and the app picks up the change within 2 seconds. No redeploy, and Lakshmamma keeps her slot.

We use more than an on/off switch. `voice_directions` is a 50/50 A/B test of voice versus map directions, with the metric `reached_gate`. `voice_first` is turned on by the segment `elders_65_plus`, from a trait the app sets when a pilgrim says "my mother is 70", so elders get one big talk button. `ui_copy` is remote config for banners, example phrases and the slot cap. `voice_agent_v2` is a staged rollout (10, 50, 100 percent) that `scripts/rollout.sh` rolls back on errors. `assistant_llm` turns model calls off so the assistant answers from rules. `venue_pack`, `reply_style` and `care_policy` choose the knowledge pack, short replies and care escalation timings.

Code: `app/flags.py` (server SDK, identities, traits, 2 s cache, last good value), `app/addons_flags.py`, `app/addons_state.py`, `scripts/flagsmith_setup.py`, `scripts/flip.sh`. The problem it solves: the operator can change how the system behaves in seconds, safely, for exactly the right people.

---

## How have you used NudgeBee and what problem does it solve?

During a rush nobody at a shrine is watching a dashboard, and the volunteer at the counter is not an engineer. NudgeBee watches for us. Its agent is installed on our kind cluster, and four automations are active on NudgeBee cloud.

`darshan-crash-report`: our app posts to a webhook when it restarts after a rush (`app/crash.py`). NudgeBee runs `llm.nubi` to investigate, `llm.summary` to write it up, and an HTTP POST back to our app. In a real run it took 2.8 minutes and returned the true root cause: exit code 137, memory limit reached.

`darshan-rush-investigate`: an event trigger on OOMKilled or CrashLoopBackOff in namespace `darshan`, then `llm.event_investigate`, a summary and an HTTP POST to `/api/incident` (`app/volunteer.py`).

`darshan-staggered-approved`: the volunteer's spoken yes calls this webhook. A duty officer approves in NudgeBee, then two HTTP tasks set `map_mode=lite` and `slot_mode=staggered` in Flagsmith. Verified end to end. The Flagsmith key is a NudgeBee secret.

`darshan-assistant-degraded`: if the assistant's model calls keep failing (`app/addons_state.py`), NudgeBee summarises, asks for approval and sets `assistant_llm=off`. Built and active, not yet test-run.

The problem it solves: the cause is found in plain words, and a human approves the fix before anything changes.

---

## How have you used Sarvam and what problem does it solve?

Lakshmamma cannot read English and will not fill in a form. Sarvam lets her just talk, in Telugu, Tamil, Malayalam, Kannada, Hindi or English.

Speech to text uses `saaras:v4` in `codemix` mode with automatic language detection, so "slot book ചെയ്യണം" works and nobody picks a language from a menu. Text to speech uses `bulbul:v3` to read her slot back, answer her questions and ask the volunteer in Malayalam. The chat model `sarvam-105b` sits behind the assistant for questions our rules cannot classify. It gets a facts block from the venue knowledge pack and the live waits, and its JSON is validated (stop ids must exist, numbers must come from the facts) before anything is spoken. Translation powers "Read this for me" and the booking-site check.

All calls go through one client, `app/sarvam.py` (8 s timeout, two keys that rotate on HTTP 402 or 429, no fake results). It is used by `app/addons_live.py` (hands-free conversation), `app/assistant.py`, `app/volunteer.py` (the Malayalam question and the yes/no), `app/addons_care.py`, `app/addons_staff.py` and `app/addons_read.py`.

The problem it solves: a pilgrim who has never used an app, and a volunteer who is not an engineer, can both work the system by voice. That is what makes the fix in a rush possible at all.

---

## What did you like about Flagsmith, and what would you improve?

We liked how little code a flag needed to do real work: identities, traits and segments gave us the 65-plus voice-first screen with no extra logic, and a flag read cached for 2 seconds made the rush fix feel instant. Remote config (`ui_copy`) let us change copy and caps without a deploy.

To improve: with feature versioning on, changing a value needs the v2 versions API, which took us a while to find; one POST to `/versions/` with `publish_immediately: true` solved it, but the docs could lead with that. Experiment results were not available on our plan, so we count `reached_gate` ourselves. The free plan allows one project, so our earlier app's old flags still sit beside the new ones.

---

## What did you like about NudgeBee, and what would you improve?

"Generate with nubi" built working automations from plain English, and the included AI credits let us run real investigations on day one. The agent install on our kind cluster was one command, and the crash investigation returned the true cause (exit code 137, memory limit reached) in 2.8 minutes.

To improve: repeat events are grouped, so after the first OOMKilled our event trigger did not fire again on the next rush, which makes repeat testing hard. Approvals work only in the app, Slack or email; an API to approve would let us show the approval inside our own volunteer screen. The secrets and configs screens could be clearer, and the organisation approval wait at signup cost us part of a hackathon day.

---

## What did you like about Sarvam, and what would you improve?

Code-mixed speech with automatic language detection handled casual Telugu and Malayalam mixed with English words, which is how pilgrims really speak. It was fast: speech to text took 250 to 1,500 ms, and the full turn from the end of speech to the first audio was 2.1 to 3.4 s with fresh speech synthesis (0.3 s for lines we cache).

To improve: one-word answers were often misheard; a Malayalam "sari" (okay) came back as an unrelated English word, so we added tolerant word lists and Yes/No buttons. iPhone Safari sends `audio/mp4; codecs=mp4a.40.2`, which the API rejected until we stripped the codec part. Credits ran out quickly during testing; a balance or usage endpoint would let us warn before calls start failing with 402.

---

## Paste your social posts links here

SOCIAL_POST_LINKS (LinkedIn link, X link). Drafts are in `demo/v2/SOCIAL_POSTS.md`.
