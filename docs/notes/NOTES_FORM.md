# NOTES_FORM: submission form, social posts, 1:50 film cut

New files only (no existing file edited, no Sarvam calls):
- `demo/v2/SUBMISSION_FORM.md`: ready-to-paste answers under each form label, plus a "Before you press submit" checklist at the top.
- `demo/v2/SOCIAL_POSTS.md`: one LinkedIn post and one X post (274 characters with tags as plain names) for Arun's own account.
- `demo/v2/VIDEO_SCRIPT_110s.md`: the film cut to 1:50 (same columns and paragraph labels as VIDEO_SCRIPT.md), sponsor screen time (Sarvam 36 s, NudgeBee 18 s, Flagsmith 16 s), narration kept / shortened / dropped, and an edit list mapped to `demo/v2/cards/clips/` (durations checked with ffprobe) and the RECORDING_PLAN capture names.

## Checked against the code
- Flags present in code: `map_mode`, `slot_mode`, `voice_directions`, `voice_first`, `ui_copy`, `voice_agent_v2` (`app/addons_flags.py`), `assistant_llm`, `venue_pack`, `reply_style`, `care_policy` (`app/addons_state.py`).
- Sarvam: `saaras:v4` with `mode="codemix"` default, `bulbul:v3`, `sarvam-105b` with `reasoning_effort: None`, codec stripping of `audio/mp4; codecs=...` (`app/sarvam.py`).
- Steps: `app/route_facts.py` (River Crossing to the shrine = 60+200+120+60 = 440 steps); "enni metlu" is caught by `app/assistant.py` rules.
- Sarvam latency numbers in the feedback answer: NOTES_VOICE.md (STT 250 to 1500 ms) and NOTES_LIVE.md (first audio 2.1 to 3.4 s fresh, 0.32 to 0.38 s cached).

## Taken from the lead's brief (not re-verified by me)
- The four NudgeBee automations, the 2.8 minute crash investigation with "exit code 137, memory limit reached", the Flagsmith key as a NudgeBee secret, darshan-assistant-degraded not yet test-run.
- "About 23 seconds" to OOMKill today. The rehearsal file and the numbers card say 19 s, so answer 5 gives both; the film keeps 19 s to match the card. If the final take differs, change card, narration and answer 5 together.
- NudgeBee feedback items (event grouping, approvals only in app/Slack/email, secrets UI, org approval wait) and Flagsmith "free plan allows one project".

## Open items for Arun / the lead
1. Replace VIDEO_URL, LIVE_URL, SOCIAL_POST_LINKS; README still has VIDEO_URL, LIVE_URL, NUDGEBEE_RUN_PROOF_LINK, NUDGEBEE_AUTOMATION_3/4_NAME, TEAM_MEMBER and licence placeholders (docs/README_NEW.md). The README says automations 3 and 4 are unverified; the lead now says automation 3 (darshan-crash-report) ran for real, so the README should be updated by whoever owns it.
2. New phone take `P5_steps_q.mov` for the "ask anything" beat (details in the script). Fallback: existing P4_steps take.
3. New narration takes (about 20 s): shortened P1, P6 and P10.
4. Care beat: only say "nearest volunteer" if the routed request shows on the staff page (addons_care live); otherwise use P9a-alt.
5. Answer 5 is about 460 words counting the numbered steps and code names; trim the "How it differs" line if the form has a hard limit.
