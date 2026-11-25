# QA report (independent tester) - 2026-11-25

Method note: every typed reply on the live endpoint triggers a paid Sarvam TTS call, so the 40+ utterance run used a throwaway
local copy of the current repo (port 18950, Sarvam keys blank, rules brain only, no spend). Spot checks of the LLM path ran on
http://localhost:8088 (6 real Sarvam calls so far). Where the local rules brain answers "I do not have that information" the
deployed model sometimes rescues the question (see table), so those are marked.

## Bugs (ordered by damage to the demo video)

| # | Sev | Bug | Steps | Expected | Actual | File / fix |
|---|-----|-----|-------|----------|--------|-----------|
| 0 | **blocker** | Pilgrim "I need help" button never sends anything and always says "Could not reach the volunteers"; /api/state is never polled by the pilgrim page, so NO pilgrim-to-staff or staff-to-pilgrim sync from sync.js works (only app.js's own queue poll works) | Open `/` (local build and redeployed 8088, re-tested after redeploy), tap "I need help". In the page console `typeof uid` is "undefined". Server log shows no POST at all and zero `GET /api/state?role=pilgrim` | Request to /api/care/request or /api/staff/help, volunteer sees it in "Requests near you" within 2 s | Red text "Could not reach the volunteers...", no request sent; staff screen never shows it | app/static/sync.js uses `uid`, `lang`, `SM`, `F`, `loadFlags`, `restore` but app.js wraps everything in `(function(){...})()` so they are not globals; the ReferenceError is swallowed by the `catch(e){}` blocks. Fix: in app.js add `window.__pilgrim={get uid(){return uid},get lang(){return lang},...}` (or `window.uid=uid`) and use it in sync.js. Also `/api/care/request` does not exist (the router has POST /api/care), so even with the fix the first endpoint 404s then falls back to /api/staff/help (works). |
| 0b | major | Pilgrim booking and position change do not appear anywhere on the staff screen | Pilgrim taps "Book the shortest queue"; or "I reached River Crossing". Watch /volunteer 15 s | staff overview shows bookings / pilgrim positions (staff state has `slot`/`position` keys) | No DOM change in 15 s (staff screen shows only calm state, help requests, crowd). Related to the blocker: pilgrim position is never shared | app/static/volunteer.html `sync(G)` shows no booking count; render `G.map` stops / booked count in Site overview; share position via /api/state. |
| 9 | major | Staff assistant answers off-topic or unknown questions with an unrelated FAQ | POST /api/staff/ask "is there a rush now" -> the "How slots work" paragraph (intent pack); "who is the prime minister" -> "Is there any entry fee?..." (local, no model; may be rescued by the model with credits) | rush: "No rush now, the system is calm"; unknown: "I do not have that" | unrelated 250-char FAQ read aloud | app/addons_staff.py: add a rush rule ("rush", "busy now", "crowd now" read flags/queue_sim); route kb pack hits below a higher score to the model or to "I do not have that". |
| 10 | minor | Page is heavy on a slow phone network: 44 s to first content at 50 KB/s, 400 ms latency | Chrome throttle, load `/` | content within ~10 s | 2.5 MB of Anek woff2 (Devanagari 726 KB, Telugu 402 KB, Kannada 310 KB) loaded, plus ~95 KB JS/CSS | app/static/fonts.css: `font-display:swap` and load only the script of the chosen language (unicode-range), or subset the Devanagari font. |
| 11 | minor | Going offline mid-use shows no message on the pilgrim page | throttle offline for 6 s on `/` | "No connection" notice | nothing visible | app/static/app.js pollQueue catch; show `say('net','bad')`. |
| 12 | minor | Mobile `/`: ~200 px empty gap between the "Site map" link and the map heading; /volunteer on mobile has 4 elements 8 px wider than the 390 px viewport (no scroll bar, clipped by a rounded container) | screenshot `metrics/shots/qa/local-home-m.png` | tight layout | blank space; DIV/SPAN r=398 on /volunteer | app/static/pilgrim.css hero min-height; volunteer.html care-near / site overview width. |
| 13 | minor | /start and /for-temples return 404 (do not exist) | GET /start | n/a | 404 | Only a problem if the video or README mention them. |
| 14 | minor | Console: "Blocked call to navigator.vibrate" on /volunteer before first tap | load /volunteer | none | console error | volunteer.html: guard `navigator.vibrate` with `navigator.userActivation.hasBeenActive`. |
| 15 | info | At the start of testing, 8088 had a REAL NudgeBee incident in state "asking" (volunteer page shows "Heavy rush"), so judges would see it instead of calm | GET /api/volunteer/state | calm | status asking | Reset with POST /api/volunteer/reset before recording. I did not touch it; incident, walk-in, crowd and staff-assistant tests ran on a local copy. |
| 1 | major | "What is next" after a NAMED stop is not answered | POST /api/live/turn text="what is next after forest path" (fresh session, no position). Same for "what is next after queue complex", Malayalam "ക്യൂ കോംപ്ലക്സ് കഴിഞ്ഞാൽ അടുത്തത് എന്ത്", Hindi "क्यू कॉम्प्लेक्स के बाद क्या है" | "After Forest Path comes Queue Complex, 8 minutes on foot, wait N minutes" | EN: "Tell me which stop you are at... route starts at Base Camp" (gate_id g1, wrong stop). "after queue complex" gives the wait at Queue Complex. "what is after main steps" dumps the whole route text. Hindi: "I do not have that information" | app/assistant.py `next` intent: when a gate is named in the sentence use it as the origin (gate_id), not only the stored position; add "after/ke baad/kazhinjal/tarvata" patterns in 6 scripts. |
| 2 | major | "next stop" is understood as goodbye and ENDS the session | text="next stop" | next stop from position / ask position | "You are welcome. Take care." state=ended | app/directions.py keyword_intent goodbye matcher ("stop"): require "stop" only as a standalone command or "that's all"; check `next` before goodbye. |
| 3 | major | Knowledge-pack answers leak stop ids into speech and run long | text="what is after main steps" (local build) | short spoken sentence | "Base Camp (g1), River Crossing (g2) ... (g5)... about 90 minutes", 280+ chars, read aloud as "g one" | app/assistant.py `via=knowledge_pack` path skips the id stripping and the length cap the llm path has; strip `\(g\d\)` and cap at 2 sentences. |
| 4 | major | Distress / elder-help phrasings missed by rules in some scripts (only the LLM saves them, and only with credits) | ml "എന്റെ കുട്ടിയെ കാണുന്നില്ല" (rules: unknown; deployed LLM: distress OK). kn "ಹಿರಿಯರಿಗೆ ಸಹಾಯ ಬೇಕು" (rules: unknown; deployed LLM: classed `facility`, answer fine but asks "which gate are you at"). ml "മുതിർന്നവർക്ക് സഹായം" unknown. hi romanised "mujhe kya saath le jana chahiye" unknown | distress must NEVER depend on the model; note on volunteer screen | Without Sarvam credits a lost child in Malayalam gets "I do not have that information" and NO volunteer note | app/assistant.py distress/help_elder triggers: add Malayalam "കാണുന്നില്ല/കാണാനില്ല", Kannada "ಹಿರಿಯ", Malayalam "മുതിർന്ന", romanised hi "le jana/saath". |
| 5 | minor | Noise word "uh" is answered with the unknown line instead of being ignored | text="uh" | ignored:true, silent | "I do not have that information..." spoken | app/addons_live.py `_noise` only drops <2 chars; add filler words (uh, um, hmm, ah) and 1-token non-word input. |
| 6 | minor | Off-topic weather question answered with opening hours (local build, knowledge_pack) | text="is it going to rain tomorrow at the shrine" | "I do not know the weather, ask the volunteer" | 383-char opening-hours answer (deployed build answered correctly via LLM) | app/kb.py THRESHOLD: weather word "tomorrow/shrine" matches hours entry; raise threshold or require topical tag overlap. |
| 7 | minor | `latency.llm_ms` and `stt_ms` always 0 for text turns; llm_ms is 0 even when via=llm | any llm reply on :8088 | real ms | `llm_ms: 0` with via=llm | app/addons_live.py reads extra["llm_ms"], assistant.answer does not set it. |
| 8 | minor | Kannada elder question on the deployed model answered as intent `facility` and asks the pilgrim to say a gate | see #4 | help_elder reply | model asks for position | app/assistant.py: add Kannada elder trigger so rules answer. |


## Pass rate (typed text, 42 utterances, local rules brain; the deployed LLM rescues some failures)
First run, counting my own test mistakes: en 14/19, te 4/4, ta 3/4, ml 3/4, kn 3/4, hi 5/7 = 32/42. Of the 10 failures,
3 were my own test errors (the fifth stop is "Main Steps", I typed "Sanctum Gate" twice, and "Queen Complex" once), leaving 7 real
failures, all listed above (#1, #2 not in first run, #4, #5, #6) - see final numbers at the end.

### Final pass rate by language (42 typed utterances, local rules brain, no Sarvam)
After removing my 3 test mistakes (wrong stop name) and counting the extra checks in the second run:

| Lang | Pass | Notes |
|------|------|-------|
| English | 15/19 real | fails: "next after <stop>" x2, "uh" not ignored, weather question -> hours; plus "next stop" -> goodbye (#2) |
| Telugu | 4/4 | native, romanised and code-mixed all correct stop, correct script |
| Tamil | 3/3 | |
| Malayalam | 3/4 | child-missing phrase missed by rules (deployed LLM rescued it, intent distress, note posted) |
| Kannada | 3/4 | elder help missed by rules; deployed LLM answered but as facility |
| Hindi | 5/6 | romanised "kya saath le jana" unknown; "next after" unknown |
| Total | 33/40 real (82%) | all 5 stops answered about the RIGHT stop whenever named (g1..g5 checked, EN/TE/TA/ML/KN/HI). Replies 40-150 chars, easy to speak. |

Multi-turn: "book a slot" -> "today evening" -> "two" -> "yes" gave slot 17:00 Base Camp; "tomorrow morning for 3" -> 06:00; "what is my slot", "cancel it" worked and `slot` and `show` fields matched. "change it to evening" re-asks "Today, or tomorrow morning?" (okay) but a bare "yes" afterwards loops the same question (minor).

## What works well
- Position memory and map fields: "I reached River Crossing" -> position g2, progress g1 done / g2 here / g3 next, show=map, in 6 scripts including romanised ("river crossing lo unnanu", "pahunch gaya", misspelling "crosing").
- Wait questions name the right stop in all scripts; numbers match /api/queue and /api/map.
- Fee/tout, lost child (English, Hindi, Kannada, deployed Malayalam via model), carry, facilities, elders: calm, short, grounded; volunteer note posted for distress.
- Unknown and noise inputs never invent facts ("I do not have that information").
- No-key behaviour: text turns still answer (rules) with notice "Voice unavailable (no Sarvam key). Type instead."; audio turn returns error:true with a clear message, no crash.
- Staff: walk-in booking (slot 14:45 Queue Complex), crowd report with a number moves the pilgrim queue (Forest Path 38 -> 64 min), staff assistant busiest/bookings/wait/help-open answered from live data, walk-in action asks yes first and executes on yes, rush switching refused ("approved through NudgeBee"), reset endpoint works.
- Sync that works: staff crowd report -> pilgrim page in 0.16 s (8088) / 0.77 s (local).
- Voice, real Sarvam on 8088 with a stubbed mic: one tap shows "Listening. Just speak." within 0.5 s; spoken "Hey, I want to book a slot tomorrow morning" was transcribed and answered "For how many people?" in 0.99 s.
- No console errors or failed requests on /, /judge, /sponsors, /graph at 390 and 1440 widths; no horizontal scroll; Indian scripts render without clipping (see shots in metrics/shots/qa/).

## Not verified / limits
- Chrome's fake audio device (`--use-fake-device-for-media-stream`) hangs getUserMedia in this macOS session (reproduced), so the mic test used a stubbed getUserMedia playing the WAV. Only one spoken turn was run (credits), so the full hands-free booking to "booked" by voice was NOT re-verified.
- Real Sarvam calls: about 9 to 10 of 12 (3 text spot checks with TTS+chat, 1 voice turn). The 40 utterances ran on a local copy with the key blank, so LLM wording, TTS quality and audio were not judged except the spot checks.
- Staff incident test (?force=1 + reset) ran on the local copy, not on 8088/public, to avoid disturbing the live NudgeBee incident. Public URL checked only for HTTP 200 on / /volunteer /judge /sponsors /graph and /api/state.
- Two-tab and reload behaviour: a fresh browser context shows no slot, so the check was inconclusive; slot restore uses localStorage + GET /api/slots?uid (not retested after the sync.js fix is in).
- Retest: bug 0 re-tested after the 8088 redeploy (still failing at that time). Others reproduce on the repo code that the local copy ran.

## QA fixes (backend, 15:03)
Fixed, each with a test in app/tests/test_qa_fixes.py (suite: 388 passed):
- Row 2 (next stop = goodbye): `is_bye` now fires only on clear closing phrases; never on questions, "next/what/which/after", or a stop name; "stop" only alone or "stop listening". Checked in six scripts.
- Row 1 (next after a named stop): new `_after_reply` in assistant.py answers from the named stop in six languages without needing a position.
- Row 5 (noise): `_noise` ignores fillers (uh, um, hmm, ah, ...) and one-token non-words.
- Rows 3 and 6 (knowledge pack): ids stripped, answer capped at two sentences or about 160 chars, off-topic words (rain, minister, etc.) give the honest unknown line. Threshold moved 1.8 to 2.2 and generic words (tomorrow, shrine, now) removed from matching; a higher threshold broke legitimate water, steps and medical questions, so no "strong topic word" rule beyond that.
- Rows 4 and 8 (distress, elder): added Malayalam, Kannada, Tamil, Telugu, Hindi and romanised triggers; elder help in Kannada and Malayalam now routes to help_elder by rules.
- Row 9 (staff rush): "is there a rush now" answers from live state.
- Row 7 (llm_ms): set when the model path is used.
Not fixed: rows 0, 0b, 10 to 14 (front end, not in this lane). Staff unknown questions still depend on the kb threshold, not tested beyond the pilgrim path. No real Sarvam calls made.
