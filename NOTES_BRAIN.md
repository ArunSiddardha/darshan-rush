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

## STATUS
(sections below are filled in at the end)
