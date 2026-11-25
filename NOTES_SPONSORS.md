# NOTES_SPONSORS: the /sponsors page (Sarvam AI, Flagsmith, NudgeBee, live)

New files only: `app/addons_sponsors.py`, `app/tests/test_addons_sponsors.py`, `app/addons_ui/sponsors.html|js|css`. No existing file edited. static_v2 did not exist, so the page uses the current `/static/style.css` + `/static/fonts.css` tokens (Anek, warm neutrals).

## Built
- `GET /sponsors` (page), `/sponsors/sponsors.js`, `/sponsors/sponsors.css` (served by the router from `addons_ui/`, no static copy needed), `GET /api/sponsors/status` (JSON, never an error: every source degrades to "not available").
- Sarvam recorder: importing the module wraps `sarvam._post` (idempotent, never raises, re-raises the original error unchanged). Records type, status, ms, language, 80-char preview, key SLOT number (never the key) in memory and in `<dir of STATE_FILE>/sarvam_calls.jsonl`; reloaded at import. Covers stt, translate, tts, chat. Not covered: doc-ai (photo read) and any call that bypasses `sarvam._post`.
- Crash recorder: wraps `crash.check_after_start` to save pod/time/sent to `sponsors_crash.json` (pod name for the "last crash" fact).
- Flagsmith: values via the edge API (identities for a standard and a 65+ visitor, to show the segment reason), change time and author from each feature's version list (Admin API), audit log (10 s cache), rollout %, A/B from `flags.experiment()`.
- NudgeBee: from volunteer state/timeline, crash recorder, webhook-configured flags. Chain lit from the same timeline as /judge.

## Verified
- 16 tests pass (mocks only); full suite run too (see below).
- Live: throwaway app (`_tools/sponsors_app.py`, ports 18940/18941, stopped by PID) importing the real `main.app`, with the real cluster's `state.json` copied out of the pod and the REAL Flagsmith (env + admin keys). Sarvam key was set to a dummy so nothing could be spent. Real values seen: all six flags, last-change times, rollout 0%, real NudgeBee root cause and summary, "asking" state.
- Screenshots 1440x900 and 390x844 in `metrics/shots/sponsors/`: `desktop-*`/`mobile-*` = real data; `seeded-*` = clearly TEST-SEEDED state (made-up recovered timeline and six made-up Sarvam calls in `_tools/sponsors_data2`) only to check the populated layout. No horizontal overflow, no console errors.

## Findings worth knowing
- Flagsmith `/audit/?project=55985` returns HTTP 500; `/projects/55985/audit/` returns 200 but EMPTY (changes made with an Admin API key are not logged there). So "who changed it" comes from the version list: author is null = "Admin API key (script or NudgeBee task)". It cannot tell NudgeBee's task from `flip.sh`. Proof line: shown when the flag version time falls between the volunteer's yes and the flip; correlation, not a signature.
- "Duty officer confirmed in NudgeBee" is inferred (shown at the flip time, labelled so). The app has no direct signal for it.
- "Crash to cause" only shows when a crash was reported (otherwise rush and cause are marked together and it would read 0 s).
- NudgeBee agent pods are not visible from our pod; the card says so and shows what the app received.
- Sarvam "Last said" falls back to the volunteer question (cached render) until the recorder has seen a TTS call. Cached renders cost no call, so they are not counted.

## Integration (for the integrator)
1. `main.py`: `for _m in (..., "addons_sponsors"): _mount(_m)` (or import + `app.include_router(addons_sponsors.router)`). Mount EARLY (before requests/startup) so the recorders are installed before the first Sarvam call and before `crash.check_after_start` runs at startup.
2. Links: add `<a href="/sponsors">Sponsors</a>` to volunteer.html (staff dashboard) and judge.html. The page already links back to /volunteer and /judge.
3. Env in the pod: nothing required. `FLAGSMITH_ADMIN_KEY` (+ optional `FLAGSMITH_ENV_ID`, default 119864, `FLAGSMITH_PROJECT_ID`, default 55985) enables change history, audit and rollout %; without it those facts say "not available". The key is never returned.
4. `/data` must be writable (it is) for `sarvam_calls.jsonl`.

## Unverified
- Recorder against real Sarvam traffic (no credits spent; tested with mocks and a seeded file). Multi-worker setups would each keep their own memory (file is shared append-only; one uvicorn worker today).
- The page inside the real cluster pod (only the throwaway app).
- Design: the shared style.css currently has a coloured gradient top background; the page inherits it.
