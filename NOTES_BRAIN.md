# NOTES_BRAIN: the assistant brain (backend lane)

## API CONTRACT (written first, for the front-end agent)

### Response of POST /api/live/turn and POST /api/directions (new fields, always present when text was understood)
```
{
  "transcript": "...", "reply_text": "...", "audio_base64": "...|null", "lang": "te",
  "intent": "position|wait_gate|wait_best|crowd|next|distance|slot_info|slot_late|facility|help_elder|distress|fee|carry|about|goodbye|book|change|cancel|unknown",
  "gate_id": "g2" | null,              // the stop the question is about (always the one the pilgrim named)
  "position_gate_id": "g2" | null,     // where the pilgrim is (last known, stored per session/uid)
  "progress": [ {"id":"g1","name":"Base Camp","state":"done|here|next|todo"}, ... 5 stops in route order ],
  "show": "map" | "slot" | "none",     // open the map (centred on gate_id / position_gate_id) or the slot card
  "action": "none|book|change|cancel|set_position|call_volunteer",
  "via": "rules|llm|rules_fallback",
  "latency": {"stt_ms":0,"llm_ms":0,"tts_ms":0,"total_ms":0}
}
```
/api/directions also accepts JSON `{"text":..., "lang":"te", "uid":"u1"}` (or multipart with audio) and returns the same fields.
"I reached River Crossing" -> intent position, gate_id g2, position_gate_id g2, show map, progress g1 done / g2 here / g3 next.

### GET /api/map?uid=U&lang=en
```
{ "simulated": true, "rush": false, "canvas": {"w":100,"h":100},
  "stops": [ {"id":"g1","name":"Base Camp","x":..,"y":..,"wait_min":9,"load":0.3,"facilities":["water","toilet",...],
              "walk_to_next_min": 6 | null, "state":"done|here|next|todo", "is_slot_gate": false} ... ],
  "paths": [ {"from":"g1","to":"g2","walk_min":6} ... ],
  "facilities": [ {"type":"water","stop":"g1","x":..,"y":..,"label":"Drinking water"} ... ],
  "position": "g2" | null, "slot": {"label":"15:00 to 15:10","gate":"g3","gate_name":"Forest Path"} | null,
  "label": "SIMULATED" }
```
Facility types: water, toilet, medical, rest, wheelchair, cloak, lost_found, info.

## What was wrong
- Gate matching (directions.gate_in_text) only looked for Latin words of 4+ letters from the gate name, so any Indian-script or romanised-speech name ("రివర్ క్రాసింగ్", "kraasing", "queue complex lo") was missed. The fallback then picked the first gate (Base Camp) or the shortest wait, so the answer was about the wrong stop.
- "I reached River Crossing" had no intent at all: nothing remembered where the pilgrim was, and a statement of position was treated as unclear.
- Sarvam chat (sarvam-105b) returned an EMPTY reply: the hidden reasoning used the whole token budget. Fixed by sending `"reasoning_effort": null` in sarvam.chat (about 0.3 to 1 s per call now). This also fixes the older llm_fill and understand fallbacks.

## What changed
- app/gatematch.py: aliases for all five stops in six scripts plus romanisations, stem matching on the space-free text (inflections like -ിൽ, -లో work), difflib fuzzy matching for garbled Latin. The stop actually named always wins. directions.gate_in_text now uses it.
- app/assistant.py: answer(text, lang, uid, session). Rules first (about 20 intents, six languages, no model, 0 ms), then the Sarvam chat model with a facts block for anything else, validated (gate ids must exist, ids stripped from speech, numbers must be in the facts, English answers to a non-English pilgrim replaced by the safe line), then a safe fallback ("I do not have that information, please ask the volunteer at the counter."). Position is stored per uid. Distress ("I lost my son") gives a calm reply and posts "Pilgrim needs help ..." into volunteer notes. Never claims to call police.
- Wired into addons_live.handle (idle, booked, and also mid-booking: a position or facility question is answered and the open booking question is repeated), into /api/directions (directions.respond_brain) and GET /api/map in main.py. Booking, change, cancel keep the existing flow.
- Simulated site plan: stops g1..g5, walking minutes 6, 9, 8, 12, facilities per stop, all labelled simulated.

## Verified
- Tests: 248 pass (app/tests/test_brain.py, model mocked): gate matching in six scripts, position in six languages, waits about the named gate after a position, best gate, next, distance, slot, facilities, elder, fee, carry, about, goodbye, distress and the volunteer note, validation of model output, live flow, /api/directions, /api/map.
- Deployed image, via /api/live/turn text field: "I reached River Crossing", "what is the wait at Forest Path" in English, Telugu and Malayalam answer about the right stop (g2 position, g3 wait), with audio.
- REAL Sarvam (about 22 calls in total): chat JSON contract and tone checked on free-form questions in English, Telugu, Malayalam (shoes and cloak room, less crowded stop, tired). TTS for the six deployed checks.
## Only with mocks
- Hindi, Tamil, Kannada reply texts and the Indic distress phrases (written by me, not reviewed by a native speaker). Speech-to-text spelling variants are guessed, not tested with real audio.
## Known limits
- Model answers are sometimes thin (it said "I do not have that information" for a question about the stop with fewer people when position was unknown) and one Telugu answer mixed a cloak-room guess with a rest suggestion. Facts only cover what is in the block.
- "Late" or "change my slot" on /api/directions without a time asks for the new time; in live mode the existing booking flow asks.
- Walking minutes and facilities are simulated constants, not a real plan. Position is in memory per uid (lost on pod restart).
- Old English "a ... walk" phrasing now reads "9 minutes on foot".
