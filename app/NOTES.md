# Dukaan Duty app notes

## Works (tested, 9 pytest tests pass in `/Users/arun/hackathon/festive/repo/.venv`)
- `/`, `/owner`, `/healthz`, `/api/products`, `/api/flags`, `/api/order`, `/api/experiment`, `/api/metrics-lite` run locally with no keys.
- Heavy vs lite: full mode allocates and touches HEAVY_MB (default 40) for about 2 s per `/api/products` and `/api/order` call. Lite mode skips it, drops recommendations and big visuals.
- Without FLAGSMITH_ENV_KEY a clear warning is printed and a local flag store is used (`POST /api/dev/flag {"name":"lite_mode","value":true}`).
- Incident flow: bad or missing X-Incident-Token gives 401. Valid incident gives state `asking`; "haudu/yes" (or any yes word) POSTs `{event_id, approved_by, transcript}` to NUDGEBEE_APPROVE_WEBHOOK; "beda/no" gives `declined`. After a yes, a thread polls lite_mode and then marks "Flag flipped" and "Shop recovered" and prepares a Kannada confirmation.
- Owner state is saved to STATE_FILE (default /tmp/dukaan-state.json). It does not survive a container restart unless STATE_FILE is on a mounted volume (e.g. emptyDir at /data), and an OOM restart restarts the container.

## Needs keys
- SARVAM_API_KEY: voice, translate, TTS. Without it `/api/voice` returns 503 with a message. The incident still works, but without Kannada audio (built-in Kannada text is shown, a note appears on /owner).
- FLAGSMITH_ENV_KEY: real flags. Create flags `lite_mode` (boolean), `ordering_mode` (multivariate: voice/tap), `rush_message` (string remote config). Event name for the metric must be exactly `order_completed`.
- NUDGEBEE_APPROVE_WEBHOOK, INCIDENT_TOKEN.

## Unverified (never run against the real services)
- Sarvam REST shapes were written from docs and research notes: STT `POST /speech-to-text` (model saaras:v4 with fallback saaras:v3, mode codemix, browser webm upload), `POST /translate`, `POST /text-to-speech` (default bulbul:v3 speaker `shubh`, fallback bulbul:v2 `anushka`; override with SARVAM_TTS_MODEL / SARVAM_TTS_SPEAKER), chat `sarvam-105b` at `/v1/chat/completions`. Run one smoke call with a real key first.
- Flagsmith: `get_experiment_flag` and `track_event` need flagsmith >= 6.3.0 and the Experimentation beta on the plan; if locked, local per-variant counts at `/api/experiment` still work. Environment-level lite_mode is cached 2 s. `get_environment_flags` must be allowed for the server-side key.
- Memory limit behaviour (OOM at 160Mi) depends on the cluster; HEAVY_MB=40 x several concurrent requests should trip it, not tested here.
- Browser mic and audio playback were not tested in a real browser (only HTTP smoke on port 8081).
