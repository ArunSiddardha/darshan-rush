# Submission text (Festive Hacks, Bengaluru)

Fill the placeholders in [brackets]. Do not put keys or the live tunnel URL in public text unless it is up at submission time.

## One-line pitch
A darshan slot you book by speaking in your own language that stays fair when ten thousand people arrive at once, and a volunteer who approves the fix by voice.

## Problem
On 8 January 2025 six people died in a crush at a token counter in Tirupati while queuing for darshan tokens. The Sabarimala season opened on 16 November 2026 with about 80,000 pilgrims a day. Booking systems exist (Sabarimala Virtual-Q books a slot, the Swami chatbot answers questions in text), but none of them is built for the moment everyone arrives at once, in your language, and for the elderly pilgrim who only speaks one.

## What it does
- A pilgrim books a darshan slot by voice in Telugu, Tamil, Malayalam, Kannada, Hindi or English and hears the slot read back. A walk-in with no phone is served by the volunteer at the counter, who speaks for them.
- When a rush hits (judges scan a QR and all book at once) the booking pod on Kubernetes runs out of memory. NudgeBee finds the cause. The app asks the temple volunteer in Malayalam. The spoken yes starts an approval workflow in NudgeBee; its HTTP tasks flip two Flagsmith flags (`map_mode` full to lite, `slot_mode` open to staggered). Booking recovers; before and after numbers are shown.
- Flagsmith segments choose a voice-first experience for pilgrims 65 and over and by language, and run an A/B test (voice directions vs map directions, metric `reached_gate`).

## How each sponsor is used
| Sponsor | Real work | Files |
|---|---|---|
| Flagsmith | Flags `map_mode`, `slot_mode`, `voice_directions`; traits language and age 65+; A/B experiment events; flags flipped by a NudgeBee workflow through the Admin API | `app/flags.py`, `app/static/app.js`, `app/addons_flags.py`, `scripts/flagsmith_setup.py`, `scripts/flip.sh`, `scripts/rollout.sh`, `nudgebee/darshan-staggered-approved.yaml` |
| NudgeBee | Sees the OOMKilled pod, investigates, posts the root cause to the app, runs an approval-gated workflow whose HTTP tasks flip the flags | `nudgebee/darshan-rush-investigate.yaml`, `nudgebee/darshan-staggered-approved.yaml`, `nudgebee/README.md`, `scripts/nudgebee_agent.sh`, `app/volunteer.py` (incident and approval endpoints), `app/crash.py` (crash self-report), `k8s/` |
| Sarvam AI | Speech to text for the pilgrim and the volunteer's yes or no, text to speech for the slot readback and the volunteer's Malayalam question | `app/sarvam.py`, `app/sarvam_keys.py`, `app/directions.py`, `app/volunteer.py` |

## What is simulated
All crowd sizes, gate waits and slots come from the app and are labelled SIMULATED on every page. The rush is a load script against a local kind cluster; the before and after numbers come from that cluster, not production. The pod is deliberately memory hungry in full map mode so the failure is reproducible. The Kubernetes failure, NudgeBee's finding and approval, the Flagsmith flag changes and the Sarvam calls are real. Not affiliated with any temple, not for operational use.

## AI assistance disclosure
Built with Claude Code agents directed by the team. The agents wrote the code, scripts and documents; the team chose the idea, reviewed the results and ran the demo.

## Team
[Name, role] · [Name, role] · [Name, role]

## Links
- Public repository: [GitHub URL]
- Demo video (about 3 minutes): [YouTube or Drive URL]
- Live app (only while the tunnel is up): [PUBLIC_URL]
- Judge page: [PUBLIC_URL]/judge

---

## README block: "Judge this in 90 seconds" (paste near the top of README.md)

> ### Judge this in 90 seconds
> 1. **0:00** Open the live app on your phone: [PUBLIC_URL]. Pick a language, tap the microphone (or type) and ask for tomorrow morning's slot. You hear it read back.
> 2. **0:20** On a laptop open [PUBLIC_URL]/judge. Scan the QR with your phone and book, as many of you as you like. Press "Cause the rush".
> 3. **0:35** Watch [PUBLIC_URL]/graph: the slowest requests climb to about 3 seconds and the pod is killed for memory (a real Kubernetes OOM kill on a local kind cluster).
> 4. **0:50** In NudgeBee: the investigation names the cause. Open [PUBLIC_URL]/volunteer: it asks in Malayalam; say or tap yes.
> 5. **1:10** In NudgeBee approve the step. Two Flagsmith flags change (`map_mode` lite, `slot_mode` staggered); the graph drops to about 16 ms and the pod stays up.
> 6. **1:25** The crowd is simulated and labelled. Everything else is real. No account is needed for steps 1 to 3; steps 4 and 5 need the NudgeBee and Flagsmith dashboards, shown in the video if you cannot open them.
