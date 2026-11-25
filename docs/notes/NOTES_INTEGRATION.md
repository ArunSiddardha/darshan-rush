# Integration pass 1 (25 Nov 2026)

## Changed
- main.py: volunteer and directions routers mounted (`/healthz` shows both ok). Added `GET /api/config` (public_url from env PUBLIC_URL, set by deploy.sh from metrics/public_url.txt), `POST /api/event` (reached_gate, goes to the Flagsmith track_event path), `phones` in `/api/metrics-lite` (unique uids on /api/queue in 30 s, sim workers included), rush start/stop accept `X-Rush-Token` or `X-Incident-Token`, `mark_rush_detected()` called on rush start, favicon 204, `slots.load()` at startup.
- Lane C adapters rewritten to Lane B's real API: `queue_sim.snapshot()`, `slots.book(uid, gate, time, mode, walk_in)` (returns tuple), `flags.set_traits` (new, stored per uid and sent with the Flagsmith identity), `queue_sim.report_crowd` (new). Directions with `readback=1` speaks the text as is (it used to be parsed as a new booking), and returns `slot` for the page.
- Bookings persist to `/data/bookings.json` (next to STATE_FILE, own file so volunteer state is untouched). Verified: after an OOM restart the booking count survived (22 -> 22).
- flip.sh now makes one POST per flag (publish_immediately), reads only FLAGSMITH_ADMIN_KEY. nudgebee README and workflow YAML use exactly two HTTP tasks of that form. owner.html moved to `_old/`.
- Frontend: Sarvam-credits notice shown when `notice` comes back with 200, slot label shown as a window, exposure sent once, volunteer page no longer says "applying the fix" when the webhook is not configured, graph label overlap, link colour.

## Tuned numbers (documented in k8s/deployment.yaml and config.py)
HEAVY_MB=12, HEAVY_HOLD_S=1.5 (hold grows 15% per concurrent render, so latency climbs first), RUSH_WORKERS=16, RUSH_RAMP_S=3 (one new worker every 3 s). Full map: p95 climbs from about 0.2 s to 3 s and the pod is OOMKilled about 28 s after the rush starts (20 s and 28 s in two runs). Lite map: 0 restarts, 0 errors, p95 about 15 ms at 1000 requests/s. Numbers: metrics/rehearsal1.md (script: `scripts/rehearsal.sh`, about 3 minutes, resets the demo first).

## Verified (how)
- Flagsmith live in the cluster: `flip.sh lite staggered` then GET /api/flags showed lite/staggered within 1.5 s; flip back worked (curl loop).
- Booking open and staggered (3 uids landed in 3 different windows when staggered), walk-in, typed directions in en hi ml ta te kn (all HTTP 200 with the credits notice), through localhost:8088. Through the public tunnel: /healthz, a booking and a Malayalam directions call.
- POST /api/incident with token -> volunteer page "asking" (Malayalam question). A typed yes in Malayalam (also via the Yes button in the browser) -> decision yes, page says the webhook is not configured and nothing changed; /api/flags stayed full/open.
- reset_demo.sh restores full/open, clears state, restarts pod (checked after the rehearsal).
- Real browser (Chrome for Testing via Playwright, own profile): /, /volunteer, /judge?t=, /graph at 390x844 and 1440x900, no console errors, no horizontal overflow, all six language labels render, book + typed question + "I reached the gate" worked. Screenshots in metrics/shots/ (gitignored).
- Tests: 81 pass (`cd app && ../.venv/bin/python -m pytest -q tests`).

## Not verified / still broken
- Sarvam: still no credits, so no audio in or out was tested; TTS model/speaker (bulbul, shubh for ml-IN) unverified. Browser mic recording untested.
- NudgeBee: agent, workflow import, the webhook and the OOM event firing were never exercised. YAML format is best effort.
- QR on /judge: page shows the public URL text and builds the QR from the same value (Lane D decoded the encoder earlier); I did not re-decode my screenshot.
- The quick-tunnel URL changes if the tunnel restarts; then rewrite public_url.txt, run deploy.sh, and update the NudgeBee workflow URL.
- `POST /api/volunteer/reply` and `/api/volunteer/crowd-report` take no token (anyone who finds the page can type yes). The real gate is the NudgeBee in-app approval; add a token if that matters.
- metrics-lite `restarts` is null (app cannot see it); judge page "pod restarts" shows "-" and the before/after table restarts come only from kubectl in rehearsal.md. The rehearsal "full map" request count is tiny because the load generator dies with the pod.
- Flagsmith A/B: exposure and reached_gate reach the SDK; I did not confirm they show on Flagsmith's results page. voice_directions variant depends on the identity/segment setup the lead made.
- Slow Flagsmith edge: app keeps the last good value; not tested under outage.
- Pilgrim page in the map variant leaves a large empty band above the mic; acceptable but could be tightened.

## Lead, next
1. Get Sarvam credits, then test one real Malayalam take and a TTS readback (volunteer page and pilgrim page).
2. Create the NudgeBee workflows (nudgebee/README.md): workflow 1 posts to `{PUBLIC_URL}/api/incident` with `X-Incident-Token`; workflow 2 has the approval plus the two Flagsmith HTTP tasks. Put the automation webhook URL in `.env` as NUDGEBEE_APPROVE_WEBHOOK, then `scripts/secrets.sh` and `scripts/deploy.sh`.
3. Run `scripts/rehearsal.sh` once more before filming; run `scripts/reset_demo.sh` before each take.
4. Earlier slip (Lane A): FLAGSMITH_ENV_KEY was printed once in a session; rotate if that matters.

## Pass 2 (25 Nov 2026, after NudgeBee cloud went live)

### Changed
- Crash self-report (`app/crash.py`, wired in `main.py`): a marker `/data/rush_marker.json` is set when a rush starts and cleared on the stop button and on graceful shutdown (SIGTERM, so `rollout restart` and `reset_demo.sh` are not crashes). If the next start finds it still set, the app counts a restart, POSTs once to `NUDGEBEE_CRASH_WEBHOOK` (`namespace, pod, reason, what_happened, restarts_seen, map_mode, reported_at`) and marks "Crash reported to NudgeBee" on the volunteer timeline (new step 2 of 8). With no webhook set, the timeline shows "Rush detected" and a note says the crash was not reported. The rush stays stopped after the crash (the new process has no rush threads; nothing auto-starts one). `NUDGEBEE_CRASH_WEBHOOK` added to config.py, the deployment (optional secretKeyRef), `.env.example` and the README table. `reset_demo.sh` also removes the marker.
- `/api/incident` (in volunteer.py): tolerant parsing (JSON with raw newlines, then a regex cut between the four keys for unescaped quotes, text/plain, form bodies, JSON sent with a form content type); missing event_id is generated; root_cause trimmed to 1500 chars; while status is asking or approved a new incident returns `200 {"status":"duplicate"}` unless `?force=1`; no recognisable field returns 400.
- Volunteer page: English summary under the Malayalam question, "What NudgeBee found" expander (root cause), after yes "Waiting for the duty officer to confirm in NudgeBee" until the flags flip, then "Booking recovered".
- Judge page: chain line Rush > Crash > NudgeBee cause > Volunteer yes > NudgeBee approval > Flags flipped > Recovered, lit from `/api/volunteer/state` and `/api/metrics-lite`.
- Pilgrim page: smaller empty band above the mic in the map variant. The lite banner text already existed for all six languages (checked in app.js).

### Verified
- 93 tests pass (11 new in `app/tests/test_pass2.py`, webhook mocked).
- Live in the cluster: a rush OOM-killed the pod (restarts 1), the new process came up with the rush stopped, the timeline showed "Rush detected" plus the "not reported" note (webhook empty). A malformed incident (unescaped quotes, raw newline) was accepted and gave "asking".
- Built, deployed, `/healthz` ok, `reset_demo.sh` run at the end: full/open, state idle, pod healthy.

### Unverified
- The crash POST to a real NudgeBee webhook (none set yet; only mocked). Set `NUDGEBEE_CRASH_WEBHOOK` in `.env`, then `scripts/secrets.sh` and a pod restart (`deploy.sh` or reset_demo).
- Whether NudgeBee's real payload from its LLM summary parses as expected; the tolerant parser is tested with synthetic bodies only.
- The new volunteer, judge and pilgrim page layouts were syntax-checked (node) but not looked at in a browser this pass.
- The judge chain "Flags flipped" light depends on the page having seen the rush or timeline; a reload after recovery still lights it from the timeline.
- Deployment secretKeyRef `optional: true` with the key absent: pod started fine (this run), webhook empty.
