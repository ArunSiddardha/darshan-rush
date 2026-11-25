# Lane C (Voice) notes

## Files
- `app/sarvam.py` (rewritten), `app/directions.py`, `app/volunteer.py`, `app/static/volunteer.html` (inline JS, no volunteer.js, no dependency on style.css), `app/tests/test_lane_c.py`.
- `owner.py` and `voice.py` moved to `_old/`. **`app/main.py` still imports `owner` and `voice`** (Lane B owns it): it must now `import volunteer, directions`, call `app.include_router(volunteer.router)` and `app.include_router(directions.router)`, serve `static/volunteer.html` at `/volunteer`, and drop the old `/api/voice`, `/api/owner/*` routes. `volunteer.load()` also runs at import.

## Sarvam smoke calls (25 Nov 2026, one call each, no retries)
- translate, text-to-speech, chat (sarvam-105b): HTTP 402 `{"error":{"message":"No credits available.","code":"insufficient_quota_error","request_id":"..."}}`.
- speech-to-text (saaras:v4, mode=codemix) with an empty wav: HTTP 400 `Audio duration is 0, please check the audio.` This confirms the endpoint, model name, `mode` field and header are accepted (not 402 on this route, yet a real clip may still 402 once billed). Not verified with real speech.
- Request shapes: STT multipart `file`, `model`, `mode`; translate JSON `input, source_language_code, target_language_code`; TTS JSON `text, target_language_code, model (bulbul:v3), speaker (shubh)`; chat OpenAI style at `/v1/chat/completions` with both `api-subscription-key` and Bearer headers. These match the earlier working cake-shop client. I did not re-read docs.sarvam.ai pages (no web tool in this run); the shapes follow `sarvam.md` plus the live responses above. TTS model/speaker are env-overridable (`SARVAM_TTS_MODEL`, `SARVAM_TTS_SPEAKER`, `SARVAM_STT_MODEL`, `SARVAM_CHAT_MODEL`). The research note suggests `bulbul:v4-flash`; untested because of the 402. Whether `shubh` has a ml-IN voice is unverified.
- 402 raises `SarvamNoCredits`; UI text is "Voice unavailable (Sarvam credits). Type instead." Every call returns its latency in ms (`STTResult/TextResult/AudioResult.ms`), shown in the API reply (`latency`) and on the volunteer page.

## What works (verified by 47 mocked tests, `pytest app/tests/test_lane_c.py`)
- Intents (book, wait, age, walk-in, verify) by keyword in en/hi/ml/ta/te/kn; LLM only when keywords find nothing.
- `POST /api/directions` (multipart `audio|text, lang, uid, walkin` or JSON): reply in the pilgrim's language, `audio_base64` when Sarvam works, else `notice`; `transcript`, `latency{stt_ms,llm_ms,tts_ms,total_ms}`, `intent`. Never returns 5xx on Sarvam failure.
- Site check never claims a site is real; warns about touts; flags any address not ending `.gov.in`.
- Volunteer flow: token check (401 on bad, 503 if INCIDENT_TOKEN unset), Malayalam question text, yes/no in six languages, webhook payload `{event_id, approved_by:'Temple volunteer (voice)', transcript}`, empty webhook records "NudgeBee webhook not configured" and flips nothing, flag watcher, confirmation, 7-step timeline, persistence to STATE_FILE, duplicate event ids ignored, crowd report parsing ("two thousand", "2,000", Indic digits).
- Not run live against a real server or browser: only the JS was syntax-checked with node. The page has not been seen in a browser.

## Assumed Lane B interfaces (all imported lazily; stubs shown if absent)
- `queue_sim.get_queue(uid, lang)` (or `snapshot/current`) returning `{gates:[{id,name,wait_min,load}]}`.
- `queue_sim.report_crowd(gate_id, count)` (or `crowd_report/set_crowd/report/update_crowd`) for volunteer crowd reports.
- `slots.book(uid, gate_id, when_text)` returning `{slot, mode}` (`book_slot` also tried; walk-ins use uid `walkin-<ts>`).
- `flags.set_traits(uid, {"age": n, "age_65_plus": bool})` (or `set_trait`), `flags.map_mode()` returning "full"/"lite" (falls back to `flags.lite_mode()`), `flags.invalidate_cache()`.
- Config: `config.STATE_FILE()`, `INCIDENT_TOKEN()`, `NUDGEBEE_APPROVE_WEBHOOK()`, `SARVAM_API_KEY()` (existing).
- If names differ, tell Lane C or adapt in the adapter helpers at the top of `directions.py` ("Lane B adapters").

## Other lanes / lead must
- Lane A: NudgeBee workflow 1 posts `POST /api/incident` with `X-Incident-Token`, JSON `{summary, root_cause, proposed_fix, event_id}`; workflow 2 is triggered by the approval webhook URL which the lead puts in `NUDGEBEE_APPROVE_WEBHOOK`.
- Lane B: call `volunteer.mark_rush_detected()` when the rush starts (so "Rush detected" has the true time; otherwise it equals the incident time). `POST /api/volunteer/reset` (token) clears state between rehearsals.
- Lead: Sarvam credits, then one real Malayalam take; confirm webhook env var is set before the demo.
- Lane D: volunteer page at `/static/volunteer.html`, routes `/api/volunteer/{state,audio,reply,crowd-report}`.
- "Booking recovered" is marked right after the flags flip and confirmation, not from a measured metric.
