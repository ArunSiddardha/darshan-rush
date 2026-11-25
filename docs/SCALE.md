# Scale: what breaks and what we would do

Written to be critical of our own prototype. Numbers come from `metrics/rehearsal1.md` and the code as of 25 Nov 2026.

## What the demo proves and what it does not

It proves graceful degradation: when the heavy map overloads a small pod, a flag change brings the service back without a redeploy. It does not prove capacity. The rush is 16 worker threads inside the same pod, talking to itself over localhost, so the 1,107 requests per second peak measures the pod loading itself, competing with real requests for the same 160Mi and CPU. The "before" figure is 5 completed requests because the load generator dies with the pod.

## What breaks first at 10,000 pilgrims in a minute

About 170 requests a second, each pilgrim doing a queue read, speech calls and a booking.

| # | Limit | Where it shows in the code | Fix |
|---|---|---|---|
| 1 | **Sarvam** is the first wall, not our pod. Each voice booking is several paid speech calls with 2 to 6 s latency; nothing queues or throttles them | `app/sarvam.py` (batch calls, 8 s timeout, one retry on the other key) | A queue in front of speech calls with per-key limits and back-pressure; keep caching fixed lines; degrade to typed and tap flows (lite mode already avoids paid calls); ask Sarvam about production rate limits |
| 2 | **One replica** with in-process locks. A second replica would hold its own slot counts and double-book a window | `app/slots.py` (`threading.Lock`, `_counts` in memory), `k8s/deployment.yaml` (`replicas: 1`) | Postgres with a unique constraint on (window, pilgrim) and an atomic increment; at least three replicas behind an ingress, a horizontal autoscaler and a pod disruption budget |
| 3 | **`emptyDir` for `/data`**: bookings, volunteer state, care requests and the speech cache are lost when the pod is rescheduled or the node is lost. They only survive a container restart | `k8s/deployment.yaml` (`volumes: emptyDir`), `app/config.py` (`BOOKINGS_FILE`) | A database for state, or at minimum a persistent volume claim (single writer only) |
| 4 | **State in memory** that should be shared: pilgrim position, traits, A/B counts, help requests, the assistant health window | `app/assistant.py`, `app/flags.py`, `app/addons_staff.py`, `app/addons_state.py` | Redis or Postgres |
| 5 | **The load generator inside the pod** | `app/main.py` (`_rush_worker`) | k6 or hey from outside the cluster, against the ingress, with the numbers reported beside the in-pod ones |
| 6 | **Quick tunnel**: free, no SLA, the address changes on every restart, which also breaks the NudgeBee webhook URL | `scripts/tunnel.sh` | A stable domain, TLS and a real ingress controller |
| 7 | **Flagsmith on every cache miss**: a 2 s cache per process, no local evaluation, no webhook | `app/flags.py` (`TTL = 2.0`) | Local evaluation mode in the SDK so an outage costs nothing and calls do not grow with replicas |
| 8 | **One uvicorn worker**; sync endpoints run in the thread pool, and full map mode holds memory for seconds | `app/Dockerfile`, `app/main.py` | Several workers or pods once state is shared; remove the deliberate memory hunger from production builds |
| 9 | **The recorders and metrics are per process**: `/sponsors` call log and metrics samples would each show one replica | `app/addons_sponsors.py`, `app/main.py` (`_samples`) | Prometheus metrics and a shared log |
| 10 | **No rate limits or abuse control** on any public endpoint; volunteer reply and crowd report take no token | `app/volunteer.py` | Per-client rate limits at the ingress, tokens or logins for staff endpoints, a bot filter on public booking |

## Voice data and privacy at scale

- Pilgrims' speech goes to a third party (Sarvam). Real use needs a lawful basis, a consent screen and a clear notice in the pilgrim's language, under India's data protection law.
- We do not store pilgrim audio for booking. We do store the audio of care requests on `/data` (`care_audio/`), with no retention limit and no deletion tool. That needs a retention period (days, not forever), encryption at rest, access control for staff and a delete-on-request path.
- Logs must not contain transcripts or identifiers. The Sarvam recorder keeps an 80-character preview of each call and the key slot number (never the key); that preview should be removed or hashed for production.
- Elders and people in distress use this: a failure must fail safe (show the information counter and a human), which the assistant does for unknown questions and emergencies, but this is untested with real users.

## Order we would do it in

1. Postgres for bookings with the unique constraint; three replicas; ingress; stable domain.
2. A speech queue with rate limits and a typed fallback that never needs Sarvam.
3. An external load test (k6) and a published capacity number for the booking path alone, then with speech.
4. Local Flagsmith evaluation, Prometheus metrics, alerts that NudgeBee consumes.
5. Privacy work: consent, retention, deletion, native-speaker review, accessibility testing with elders.
6. A pilot with one real venue, with their staff, before any claim about real crowds.
