# NOTES_POLISH: final pass (25 Nov 2026, 14:28 to 14:55 IST)

Deployed to kind "nb" (healthz: all 10 routers ok, flags from Flagsmith), demo reset (map_mode full, slot_mode open, assistant_llm on, reply_style normal, venue_pack venue_demo, volunteer idle). Full pytest: 382 passed (7 new in `tests/test_state_polish.py`). Real Sarvam calls by me: about 6 (TTS on 3 care turns, 1 position turn, 2 /api/care posts); everything else used the rules path or mocks.

## What I changed
**Wiring (L, M, N)**
- `assistant.py`: knowledge pack in the model's facts (`kb.facts_for`); rules-only answer from the pack when the model is off or fails (`via: knowledge_pack`, translated to the pilgrim's language, stop ids stripped, at most 2 sentences, 1 in brief mode); `assistant_llm` off means no model call; `reply_style` brief (or lite map mode) means one sentence; every model call is recorded for the health guard; care hook: real complaints and distress (medical, lost person or item, crowd, harassment, tout, staff) open a tracked care request inside the normal conversation, ordinary questions ("where is water", "my slot") stay normal answers.
- `flags.py`: `assistant_llm()`, `venue_pack()`, `reply_style()`, `raw_value()` (remote config) with the same 2 s cache and safe defaults. `kb.py`: pack chosen by the `venue_pack` flag (falls back to `VENUE_PACK` env, then `venue_demo`).
- New `addons_state.py`: `GET /api/state?uid=&role=pilgrim|staff|judge` (flags, mode, rush line, queue, map, slot, position, volunteer state, help and care requests, metrics, assistant health, venue); assistant health guard (rolling 60 s window; 5 failures or calls over 8 s -> one POST to `NUDGEBEE_ASSISTANT_WEBHOOK`, 10 min cool-down); `POST /api/assistant/simulate-failure?n=6` (incident or rush token); `/for-temples` and `/start`; care policy read from Flagsmith `care_policy`.
- `main.py` mounts `addons_staff`, `addons_state`, `addons_care`. Flagsmith flag `care_policy` created (feature 303528, JSON remote config). `scripts/set_flag.sh <assistant_llm|venue_pack|reply_style|care_policy> <value>`. `reset_demo.sh` also resets the three assistant flags.
- Staff screen: third button "Ask anything" (staff assistant fragment), "Requests near you" card (care requests with id, stop, assigned volunteer, emergency dot; plus help notes), "Assistant on fallback (approved in NudgeBee)" and "Rush mode: staggered slots" lines, polls `/api/state` every 1.5 s.
- Pilgrim page (`static/sync.js`, `window.DR` handle from app.js): quiet cycling "You can ask about: ..." line in six languages, quiet "I need help" (opens a real care request and shows its spoken reply with request number and volunteer), rush line, `/api/state` poll every 1.5 s (flag flip, slot or position change refresh the page and move the map).
- Sponsors page: flags `assistant_llm`, `venue_pack`, `reply_style` with reasons; NudgeBee: four automations by name plus the assistant health guard and its last run.

**Listen at once (H)**: the first AudioContext costs about 540 ms to create (headless Chrome), so the pilgrim page now creates it suspended after load and the tap resumes it; Listening is set inside the tap. Measured with a stubbed mic playing 0.4 s silence then 4.78 s of speech: tap to Listening 7 ms (was 596 ms); upload 4.84 s of audio (speech captured in full). `greeting:false` kept; barge-in code unchanged.

**Presentation (B, D, J, F, O)**
- Staff header matched to the pilgrim header (same veil height and spacing). Judge page: "Presenter view" pills (Pilgrim, Staff, Sponsors, Graph, For temples) with keys 1 to 5; For temples link on judge and sponsors pages.
- `/for-temples`: who it is for, what a shrine gets, Rs 3.5 / Rs 10 (pilgrim Rs 0) / about Rs 30 crore (labelled our estimate), "Pilgrims never pay. No ads. No data sales.", cost to serve (estimate), swappable venue pack, "Start with one festival day, free". `/start`: wordmark, the sentence, three large choices, small links, disclaimer. Root `/` stays the pilgrim screen.
- Demo capture mode `?capture=1` (`static/capture.js`): hides cursor, caret, the A/B developer line and voice timings; `uid=` (a real uid booked through the API first), `lang=`, `state=booked|map|more|help` on `/`, `state=walk|crowd|qa|overview|requests` on `/volunteer`. It only scrolls or opens a real state; it never fakes data.
- README: "Ask anything, for pilgrims and staff", "Business model" (only the numbers in business/), "What we would do for real traffic". `k8s/deployment.yaml`: emptyDir labelled demo only.
- QA fixes: "next stop" no longer ends the session; pack answers no longer read "(g1)"; vibrate only after a tap.

## Before / after
| Before | After |
|---|---|
| Tap to Listening 596 ms | 7 ms |
| sync.js could not see app.js variables (QA blocker 0) | `window.DR`; booking shown on the pass 1.1 s, help request on the staff screen 1.1 s, position moves the map |
| Pack questions without the model: "I do not have that" | grounded pack answer in the pilgrim's language |
| "my mother is 80 and cannot climb steps" -> cloak room | help for elders (pack triggers added) |
| Staff header taller than the pilgrim header, overlapping the title | same height and spacing |
| No staff Q&A, no requests list | Ask anything + Requests near you |
| Judge page: 2 links | presenter pills, keys 1 to 5 |

## Verified
- Flag switch without a deploy: `venue_pack` -> `venue_stadium_demo` made "where can I get food" answer "Food stalls are on every concourse..." (Demo Arena) instead of the Base Camp meal hall; switched back (Flagsmith edge needs about 5 to 10 s).
- Health guard: 6 simulated failures -> one POST to the darshan-assistant-degraded webhook, "sent, HTTP 200" (local app; NudgeBee then waits for its in-app approval; reset_demo sets assistant_llm back on).
- Right stop: "I reached River Crossing" -> position g2 and "what is the wait at Forest Path" -> g3 in English, Telugu and Malayalam (rules).
- Care, three requests end to end: Telugu fainting -> medical emergency, Karthik from River Crossing, about 2 min; Malayalam tout -> tout_payment urgent, Joseph; English lost phone -> lost_item, Meera from Forest Path. All three on the staff state with id, stop and volunteer.
- 10 pilgrim questions (timings, toilet, carry, elder, lost companion, phone, bus, water near a stop, food, footwear) and 6 staff questions (busiest, bookings, help, medical post, walk-in, rush switch refused) through the real code with typed text; fixes above.

## Tap counts (counted in the browser)
- Pilgrim books by voice: 1 tap to start live mode, then speech; confirm by voice (0 taps) or Yes (1 tap). Replay the slot: 1 tap ("Hear again" on the pass). Pass survives reload (localStorage + GET /api/slots).
- Staff answers the rush question: 1 tap (Yes) or a spoken yes; "Waiting for the duty officer in NudgeBee" shows next.
- Staff walk-in: 1 tap "Book for a pilgrim" + speech (+1 tap "Hear again" if needed): at most 3.

## Page weight
Pilgrim page HTML + JS + CSS about 157 KB uncompressed (no fonts), all self-hosted, no outside hosts; fonts preloaded (Latin) and split by unicode-range.

## Final state (14:53 IST)
Deployed image with all changes; `reset_demo.sh` run; volunteer state cleared with POST /api/volunteer/reset; public URL: every page 200, /api/state shows map_mode full, slot_mode open, assistant_llm on, venue_pack venue_demo, mode calm, volunteer idle, no care or help requests.
Note for the lead: every pod restart (deploy or reset_demo) is seen by NudgeBee, which posts a real incident about 1 to 2 minutes later and the staff screen switches to "Heavy rush. Shall I switch...". Before recording a calm frame, POST /api/volunteer/reset with the incident token (no pod restart).

## Still imperfect
- Staff "Ask anything" sometimes answers an unrelated FAQ for off-topic questions without the model (QA #9); the weather question still matches opening hours in rules-only mode (QA #6; the model answers it correctly).
- The first screen cycles examples in six scripts, so all six Anek fonts load (about 2.5 MB on a cold cache); fonts use unicode-range and font-display swap, self-hosted.
- Care markers on the staff site-overview map are not drawn (the list is shown above the map). NudgeBee hooks for care emergencies (`addons_care.set_hooks`) are planned, not wired, so the crash automation is not triggered by a care request.
- The `/api/state` poll adds one light request per open screen every 1.5 s; during the staged rush that is part of the load.
- Other agents edited `assistant.py`, `route_facts.py`, `map.js` while I worked; the suite was green at 14:49.
- README "Demo video" link and "Team" are still TODO for Arun. The trycloudflare URL changes on each tunnel restart.

## Five screens that look best for the video (metrics/shots/final/)
1. `pilgrim-03-booked-pass-m.png`: Lakshmamma's Telugu pass, big time, River Crossing, Hear again.
2. `pilgrim-01-first-telugu-m.png`: one talk button, Telugu prompt, "You can ask about" line.
3. `staff-01-calm-requests-m.png`: All calm, three actions, "Requests near you" with C-1 and C-2.
4. `sponsors-d.png`: the chain plus three live sponsor cards.
5. `for-temples-d.png`: the money story in three numbers.

Recording a booked frame: book first through the API (`POST /api/slots/book {"uid":"Lakshmamma","gate":"g2","lang":"te"}`), then open `/?capture=1&uid=Lakshmamma&lang=te&state=booked`. Run `scripts/reset_demo.sh` afterwards.
