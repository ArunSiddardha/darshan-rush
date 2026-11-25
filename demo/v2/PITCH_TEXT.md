# Submission text v2 (Festive Hacks, Bengaluru)

Fill the [brackets]. Do not paste keys. Paste the live URL only if the tunnel is up at submission time.

## Name
Darshan Rush

## One-line pitch
A pilgrim talks to her phone in her own language and gets a fair darshan slot, and when ten thousand people arrive at once the system stays up, because a volunteer says yes and NudgeBee and Flagsmith switch it to a lighter mode.

## Problem
On 8 January 2025, six people died in a crush at a darshan token counter in Tirupati. They were queuing for a number. Booking systems exist (Sabarimala Virtual-Q books slots; the Swami chatbot answers questions in text), but none is built for the moment everyone arrives at once, or for the grandmother who speaks only Telugu and has never booked anything online.

## What it does
- **Live, hands-free conversation.** One tap, then the pilgrim just talks. The app detects the language (Telugu, Tamil, Malayalam, Kannada, Hindi, English), answers aloud in that language, and keeps listening until she says thank you.
- **Books a fair slot by voice** and shows it like a pass. A walk-in with no phone is served by the volunteer at the counter.
- **Answers any question about the venue** (water, toilets, a place to sit, medical post, what to carry, touts and fees) from the venue's own knowledge pack. Numbers in any model reply are checked against the facts, or the app says "I do not have that".
- **A site map with "You are here".** "I am at River Crossing" moves the marker; the map shows the nearest rest place, water and her gate. (Simulated venue.)
- **Help requests.** "I can't find my grandson" gets a calm reply and reaches the volunteers. [Keep "routed to the nearest volunteer" only if `addons_care` is live at submission.]
- **Staff "ask anything".** A volunteer asks by voice ("how many walk-ins at gate 3?") and hears the answer from live data; actions need a spoken yes.
- **The rush.** When thousands book at once, the booking pod on Kubernetes runs out of memory and is killed. NudgeBee finds the cause and asks our app; the app asks the volunteer in Malayalam; her spoken yes goes to NudgeBee; the duty officer approves; NudgeBee's workflow flips two Flagsmith flags (map full to lite, slots open to staggered). Booking recovers, and slots already booked survive the restart.
- **Voice first for elders.** A Flagsmith segment (age 65 and over) turns on a one-button voice screen; language segments choose copy.
- **A /sponsors page** showing all three tools live: recent Sarvam calls, Flagsmith values with change times, the NudgeBee chain.

## Results (local kind cluster, simulated crowd, 25 Nov 2026)
| | Before (full map, open slots) | After (lite map, staggered slots) |
|---|---|---|
| Slowest requests (p95, worst) | 3,081 ms | 15 ms |
| Pod restarts | 1 (OOMKilled after 19 s of rush) | 0 |
| Peak requests a second | 2.3 | 1,107 |
| Errors | 0, but in-flight work lost in the kill | 0 |
Bookings kept across the restart: 801. Source: `metrics/rehearsal1.md`.

## How each sponsor does real work
| Sponsor | Real work | Files |
|---|---|---|
| **Sarvam AI** | Speech to text and language detection for the pilgrim, the volunteer and staff; text to speech for every spoken reply and the volunteer's question; translation; chat for questions the rules cannot answer | `app/sarvam.py`, `app/sarvam_keys.py`, `app/addons_live.py`, `app/assistant.py`, `app/addons_staff.py`, `app/directions.py`, `app/volunteer.py` |
| **NudgeBee** | Watches the cluster, investigates the OOMKilled pod, posts the root cause to the app, runs the approval-gated workflow whose HTTP tasks flip the Flagsmith flags | `nudgebee/*.yaml`, `nudgebee/README.md`, `scripts/nudgebee_agent.sh`, `app/volunteer.py`, `app/crash.py`, `k8s/` |
| **Flagsmith** | Flags `map_mode`, `slot_mode`, `voice_directions`, `voice_first`, `ui_copy` (remote config); segments for age 65+ and language; percentage rollout with automatic rollback; flags flipped by NudgeBee through the Admin API | `app/flags.py`, `app/addons_flags.py`, `scripts/flagsmith_setup.py`, `scripts/flip.sh`, `scripts/rollout.sh` |

## Business model
The shrine pays, the pilgrim never does. About **Rs 10 per voice booking** (with a small minimum per season); it costs us about **Rs 3.5** (Sarvam's published per-use prices, 25 Nov 2026, three spoken turns per booking), so about 65% gross margin before fixed costs. No ads, no data sales. First step: a free pilot on one festival day at one shrine (about Rs 25,000 of our cost), then a season licence. Honest size: about Rs 30 crore a year if every large Indian shrine bought it, more with event venues, railway stations at festivals and hospital queues.

## What is simulated, what is real
Simulated: the crowd (a load generator), gate waits, the venue and its knowledge pack, the volunteer roster, and the people in the video (our team speaking). Real: the Kubernetes OOM kill, NudgeBee's investigation and approval, the Flagsmith flag changes and segments, and every Sarvam call. The full map is deliberately memory hungry so the failure can be reproduced. Not affiliated with any temple. Not for operational use. No shrine uses it yet.

## What you will see in the video (2:45)
- 0:00 Why it matters: Tirupati, 8 January 2025.
- 0:12 Lakshmamma, 68, speaks Telugu to her phone and gets her slot, read back in Telugu (Sarvam).
- 0:34 She asks where she can sit; the map shows where she is.
- 0:54 Everyone arrives at once; booking slows; Kubernetes kills the pod (real terminal).
- 1:09 NudgeBee finds the cause in its own words.
- 1:20 Meera, a volunteer, is asked in Malayalam and says yes.
- 1:34 The duty officer approves in NudgeBee; two Flagsmith flags flip on screen.
- 1:44 Before and after: 3.1 s and a crash, then 15 ms and none. Her slot is still hers.
- 1:56 A help request, voice first for elders (Flagsmith segment), all three tools live on one page.
- 2:14 Who pays: the shrine, Rs 10 a voice booking; cost Rs 3.5; pilgrims never pay.
- 2:26 What is simulated and what is real.

## AI assistance disclosure
Built with Claude Code agents directed by the team. The agents wrote most of the code, scripts and documents; the team chose the idea, reviewed and tested the work, and recorded the video. The voices in the video are our team.

## Team
[Name, role] · [Name, role] · [Name, role]

## Links
- Demo video: [YouTube or Drive URL]
- Public repository: [GitHub URL]
- Live app (only while the tunnel is up): [PUBLIC_URL] · sponsors page: [PUBLIC_URL]/sponsors
