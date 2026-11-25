# Live versus simulated

Honest status on 25 Nov 2026. "Real" means it runs against the real service or the real kernel. "Simulated" means the app generates it and labels it `SIMULATED`. "Planned" is not built.

## Real

| What | How we know |
|---|---|
| Kubernetes OOMKill of the booking pod | Kernel kill of a 160Mi pod, restart count and `OOMKilled` seen with kubectl (`metrics/rehearsal1.md`, `notes/NOTES_INTEGRATION.md`). The memory hunger is deliberate (`HEAVY_MB`), so the failure is real but injected |
| Latency and request numbers | Measured by the app's own middleware and the rehearsal script, on a local kind cluster |
| Booking logic and persistence | Slots, caps, staggered spreading, bookings that survive a restart (801 kept in the rehearsal) |
| Sarvam speech to text, text to speech, translation, chat, vision | Real calls with recorded latencies (`notes/NOTES_BRAIN.md`, `notes/NOTES_SARVAM.md`, `notes/NOTES_KB.md`); tests mock them |
| Flagsmith flags, traits, remote config, segments, flip, rollout | Real project 55985; the flip request verified with curl; rollout runs in `metrics/rollout.log`; flag list read from the edge API on 25 Nov 2026 |
| Crash self-report and incident receiver | Exercised in the live cluster; the outbound crash POST only against a mock |

## Simulated (and labelled)

| What | Detail |
|---|---|
| The crowd | All crowd sizes, waits per stop, the five-stop route, walking minutes and facilities (`app/queue_sim.py`, `app/assistant.py`) |
| The pilgrims in the rush | A thread pool of 16 workers inside the same pod, ramping one every 3 s |
| The knowledge pack | "Demo Hill Shrine": times, distances and counts are invented demo values |
| Care volunteers | The roster is seeded; only a staff member who checks in is real |
| A/B traffic | Counts from test traffic, labelled so; Flagsmith's own results are not on our plan |
| The rollout rollback demo | `rollout.sh --breach-at` pretends the error rate spikes, logged as SIMULATED |
| Every temple fact | No temple, police or deity logos or imagery; not affiliated with any temple |

## Real but not fully proven in the repository

| What | Status |
|---|---|
| NudgeBee agent, root cause and approval workflow | The workflow files are best effort ("import format UNVERIFIED"); a recorded end-to-end run must be linked: NUDGEBEE_RUN_PROOF_LINK |
| NudgeBee automations 3 (crash report) and 4 (assistant health guard) | The app sends the webhooks; delivery to a real NudgeBee workflow is unverified |
| "Duty officer confirmed in NudgeBee" on the sponsors page | Inferred from the flip time and labelled so; the app has no direct signal |
| Voice on a real iPhone, and a real microphone | Tested with recorded speech through the real recorder path in headless Chrome; not on an iPhone |
| Reading real photos | Verified on clean sample images only |
| Volunteer hands-free yes with real speech | Tested with mocks and text; the tap Yes and No buttons exist because one-word speech was unreliable |

## Planned, not built

- A phone line for pilgrims without a smartphone (a labelled placeholder card on the volunteer page, no number).
- A camera-based crowd count (skipped for time).
- A real queue or gate feed from a venue.
- A load generator outside the cluster, a database, several replicas, a stable domain ([SCALE.md](SCALE.md)).
- Flagsmith experiment results (needs a plan with events enabled).
- A native-speaker review of the five Indian-language interface strings.
