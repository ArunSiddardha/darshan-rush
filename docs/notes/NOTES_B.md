# NOTES_B (Lane B, Backend core)

## Done and how it was verified
- Cake files moved: `_old/products.py`, `_old/test_app_cake.py`.
- `app/queue_sim.py`: 5 gates (Base Camp, River Crossing, Forest Path, Queue Complex, Main Steps), background thread tick 1 s, `set_rush()` surge. Every payload has `simulated:true`.
- `app/slots.py`: book/list/cancel/get, open = first window, staggered = least-loaded window in blocks of 8, cap `SLOT_CAP` (default 30) per `SLOT_WINDOW_MIN` (15) window, always returns a slot, one booking per uid (repeat returns the same slot with `already_booked:true`), walk-in by volunteer (`walk_in:true`, uid `walkin-N`). Times are IST.
- `app/flags.py`: Flagsmith server SDK, identity + traits `language`, `age_65_plus`, 2 s cache, `default_flag_handler`, last-good value if Flagsmith fails, local store + `POST /api/dev/flag` when no key (disabled when a key is set).
- `app/main.py`: all contract endpoints. Full map mode: `/api/queue` and `/api/slots/book` run `build_live_render` (HEAVY_MB, touched, held HEAVY_HOLD_S). Lite skips it.
- `app/tests/test_core.py`: 31 tests, all pass (`cd app && ../.venv/bin/python -m pytest -q tests`). All mocked, no network.
- Smoke on port 8081 (stopped by exact PID): queue, book open and staggered, rush start (6 workers, 11 rps, heavy_in_flight 6, 0 errors), metrics, rush stop. Flagsmith live was NOT exercised (smoke ran in local flag mode).

## Endpoints (beyond the contract)
- `POST /api/slots/book {uid,gate,time?,walk_in?}`; `POST /api/slots/walkin {gate,uid?}`; `POST /api/slots/cancel {uid}`; `GET /api/slots?uid=`.
- `GET /api/flags?uid&lang&age65&expose=1` (variant + map_mode + slot_mode). Frontend should call it once per pilgrim to record exposure.
- `POST /api/experiment {uid,lang?,age65?}` records `reached_gate` (call when the pilgrim taps "I reached the gate"); `GET /api/experiment` per-variant counts.
- `POST /api/rush/start[?workers=N]`, `/api/rush/stop` need header **`X-Rush-Token`** = env `RUSH_TOKEN` (503 if unset). `GET /api/rush/status`.
- `GET /api/metrics-lite` returns rps (10 s), errors (5xx, 10 s), p95_ms, restarts (always null: not knowable in-process, Lane A reads kubectl), map_mode, slot_mode, bookings.
- Pages `/`, `/volunteer`, `/judge`, `/graph`, `/map` serve from `static/`, 404 with a message if the file is missing. `/healthz` lists which routers mounted.
- `/api/incident` is defined in main only if `volunteer.router` does not already have it; it calls `volunteer.start_incident(summary, root_cause, proposed_fix, event_id)`.

## Assumptions the lead and other lanes must know
- Flag values are read as strings: `map_mode` "full"|"lite", `slot_mode` "open"|"staggered", `voice_directions` "voice"|"map" (JSON like {"mode":"lite"} also accepted). The enabled/disabled state is ignored. So the NudgeBee HTTP task must PATCH the feature state **value** (not just `enabled`). If the lead made them boolean flags, tell me.
- Env added: `RUSH_TOKEN`, `PORT` (rush workers call `http://127.0.0.1:$PORT`, must match the container port, default 8080), `SLOT_CAP`, `SLOT_WINDOW_MIN`, `RUSH_WORKERS` (24). `STATE_FILE` default is now /tmp/darshan-state.json.
- Rush load runs inside the pod, so it dies when the pod is OOM-killed (that is the proof). Lane A's `rush.sh` is external load and still needs its URL list changed to `/api/queue` + `/api/slots/book` (body `{uid,gate}`).
- Bookings are in memory: an OOM restart empties them (the `bookings` metric resets). Sim uids are `sim-<worker>-<0..49>`.
- With HEAVY_MB=40 and 24 workers the pod needs ~1 GB, so it will OOM at the 160Mi limit quickly; lower RUSH_WORKERS or HEAVY_MB if it dies before NudgeBee sees a stable pattern.

## Unverified
- Live Flagsmith (identities, traits, `get_experiment_flag`, `track_event` names must match the metric `reached_gate` exactly).
- OOM inside kind (needs Lane A's image build).
- volunteer module: not present at smoke time; main reports `missing` and `/api/incident` returns 503 until it exists. `directions` mounted fine.
