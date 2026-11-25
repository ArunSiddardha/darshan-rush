# Darshan Rush

**What:** a prototype that lets a pilgrim book a darshan slot by speaking in Malayalam, Tamil, Telugu, Kannada, Hindi or English, and keeps working when a whole crowd arrives at once.
**Who:** pilgrims at any crowded shrine (Sabarimala is the worked example), the volunteers at the spot counter who book for walk-ins without a phone, and the volunteer on duty who approves fixes by voice.
**How:** when a rush overloads the booking service, NudgeBee finds the cause, the app asks the volunteer by voice in Malayalam, and the volunteer's spoken yes flips Flagsmith flags so the service recovers.

Demo video: TODO add link

## Architecture

```mermaid
flowchart LR
  P[Pilgrim phone, voice or text] --> A[Darshan app, FastAPI on kind]
  J[Judges scan QR, rush] --> A
  A -->|speech to text, text to speech| SV[Sarvam AI]
  A -->|flags, traits, experiment events| FS[Flagsmith]
  A -. OOMKilled .-> K[Kubernetes]
  K --> NB[NudgeBee agent and workflows]
  NB -->|root cause: POST /api/incident| A
  A -->|Malayalam voice question| V[Volunteer screen]
  V -->|spoken yes| A
  A -->|approval webhook| NB
  NB -->|Admin API: map_mode lite, slot_mode staggered| FS
  FS -->|flags| A
```

Pages: `/` pilgrim (one talk button, language detected from speech), `/volunteer` duty staff (one screen at a time), `/judge` QR and rush button, `/graph` recovery chart.

## Sponsors

| Sponsor | What it does here | Where in the code | Our feedback |
|---|---|---|---|
| Flagsmith | Flags `map_mode` (full or lite) and `slot_mode` (open or staggered), flipped after approval. A/B test `voice_directions` (voice vs map directions, metric `reached_gate`). Segment `elders_65_plus` (trait `age_65_plus`) switches on `voice_first`, which opens the large voice-first layout. Remote config `ui_copy` (banner, examples, `slot_cap`, `slot_window_min`) is read by the app, so copy and caps change without a deploy. Percentage rollout of `voice_agent_v2` with `scripts/rollout.sh` (10, 50, 100 percent, pauses and rolls back if errors pass 2 percent). | `app/flags.py`, `app/addons_flags.py` (decisions, ui-copy, rollout), `app/slots.py` (`slot_cap`, `slot_window_min` from `ui_copy`), `scripts/flagsmith_setup.py`, `scripts/rollout.sh`, `app/static/app.js`, `app/static/judge.html` ("Flagsmith decides", A/B card, rollout percent), `nudgebee/*.yaml` | TODO fill in after the build |
| NudgeBee | Sees the OOMKilled booking pod, runs the root cause analysis, and runs an approval-gated workflow whose HTTP task flips the flags. | `nudgebee/`, `scripts/nudgebee_agent.sh`, `k8s/` | TODO fill in |
| Sarvam AI | Speech to text with automatic language detection (the pilgrim never picks a language), text to speech for readback, the volunteer question and live conversation, translation and text recognition for "Read this for me" (Sarvam Vision document intelligence), a chat model for the "Is this booking site real?" check. Two API keys rotate on 402 or 429. | `app/sarvam.py`, `app/sarvam_keys.py`, `app/directions.py`, `app/volunteer.py`, `app/addons_live.py`, `app/addons_read.py`, `app/addons_scam.py` | TODO fill in |

### Flagsmith experiment results (plain statement)

We keep our own honest counts per variant at `GET /api/experiment` (exposed, reached, rate), per visitor id, and show them on the judge page labelled "test traffic". Flagsmith's own Experimentation results are **not available on this plan**: the identity call answers "Events must be enabled to use experiment flags", so we did not rely on them. We still send the `reached_gate` event name so it can be switched on later.

## Setup (ten commands or fewer)

```bash
brew install kind kubectl helm cloudflared        # 1 (and start Docker or colima)
cp .env.example .env                              # 2 then fill the values below
python3 -m venv .venv && .venv/bin/pip install -r app/requirements.txt   # 3
scripts/cluster_up.sh                             # 4
scripts/build_load.sh && scripts/secrets.sh       # 5
scripts/deploy.sh                                 # 6  app at http://localhost:8088
scripts/tunnel.sh                                 # 7  prints the public URL, put it in PUBLIC_URL
scripts/nudgebee_agent.sh <agent-key>             # 8  then create the workflows per nudgebee/README.md
open http://localhost:8088/static/judge.html      # 9  QR and "Cause the rush"
open http://localhost:8088/static/graph.html      # 10 recovery chart
```

| Variable | Purpose |
|---|---|
| `SARVAM_API_KEY` | Sarvam speech and translation. Without credits the app shows "Voice unavailable (Sarvam credits). Type instead." |
| `SARVAM_API_KEY_2` | Optional second key. On HTTP 402 or 429 the app falls over to it for a while (`app/sarvam_keys.py`) |
| `FLAGSMITH_CLIENT_KEY` | Optional client key for the decisions and ui-copy endpoints (falls back to `FLAGSMITH_ENV_KEY`) |
| `FLAGSMITH_ENV_KEY` | Server-side environment key for reading flags and sending events |
| `FLAGSMITH_ADMIN_KEY` | Used by the NudgeBee workflow to flip flags |
| `NUDGEBEE_APPROVE_WEBHOOK` | Approval workflow URL called after the volunteer says yes |
| `NUDGEBEE_CRASH_WEBHOOK` | Optional. NudgeBee crash-report webhook. After a restart during a rush the app posts once: namespace, pod, reason, restart count, map mode |
| `INCIDENT_TOKEN` | Shared secret for `POST /api/incident` and the rush button |
| `HEAVY_MB` | Memory the full map mode allocates per request (what makes the pod run out of memory) |
| `STATE_FILE` | Where the volunteer state is kept |
| `PUBLIC_URL` | Address encoded in the judge QR code |

## What is simulated

- All crowd sizes, gate waiting times and slots are generated by the app (`SIMULATED` badge on every page). No real temple, booking system or camera feed is used.
- The "rush" is a load script against a local kind cluster. Before and after numbers come from that cluster, not from production.
- The A/B test traffic, the rollout percentages and the 'breach' demo of the rollout rollback (`rollout.sh --breach-at`) are test traffic or simulated, and are labelled so.
- The phone line for pilgrims without a smartphone is a placeholder card on the volunteer page. It is not built and no number is shown.
- The booking pod is deliberately memory hungry in full map mode so that the failure is reproducible.

## How this differs from existing systems

Virtual-Q books a slot. The Swami chatbot answers questions. Darshan Rush does neither as its main job: it keeps working fairly, in your language, when everyone arrives at once. Slots turn staggered under load, the heavy map becomes a light list, and the people on duty approve the fix by voice instead of reading a dashboard.

## AI assistance disclosure

Built with Claude Code agents directed by the team. The agents wrote the code, scripts and this document; the team chose the idea, reviewed the results and ran the demo.

## Known limits

- Not affiliated with any temple and not for operational use.
- Voice depends on Sarvam credits. If they run out, typed input still works and the page says so.
- The slot readback falls back to the device voice if Sarvam audio is missing, and the page labels that.
- The map is a simple SVG diagram, not a real floor plan or tile map.
- Phones-connected count and the before/after table on the judge page are computed from `/api/metrics-lite` and need that endpoint to expose a phones count.
- Tested in a recent Chrome (and WebKit emulation); the live conversation mode needs a microphone and https. It falls back to tap to talk when it cannot start.
- Reading a photo works well on clean images; a distant or glary sign may read poorly. The site check gives a warning only, never a guarantee that a site is genuine.
- Sarvam credits are limited; fixed spoken lines are cached on disk and shipped as audio in the image so the demo does not pay for them twice.
- The Malayalam, Tamil, Telugu, Kannada and Hindi interface strings were written by the build agents, not reviewed by a native speaker.

## Team

TODO: names and roles.

## License

See `LICENSE`.
