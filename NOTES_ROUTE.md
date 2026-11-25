# Route facts (simulated)

One source of truth: `app/route_facts.py`. All numbers are invented for the prototype.

| Stretch | min | m | steps | climb m | difficulty | wheelchair | shelters |
|---|---|---|---|---|---|---|---|
| Base Camp to River Crossing | 10 | 500 | 40 | 10 | easy | yes | 0 |
| River Crossing to Forest Path | 20 | 600 | 60 | 40 | moderate | yes | 1 |
| Forest Path to Queue Complex | 30 | 700 | 200 | 70 | hard | no (carrying help) | 2 |
| Queue Complex to Main Steps | 20 | 400 | 120 | 40 | moderate | yes | 1 |
| Main Steps to shrine | 10 | 200 | 60 | 20 | moderate | no | 0 |
| Total | 90 | 2400 | 480 | 180 | | | |

Helpers: `totals()`, `remaining_from(stop, booked_gate)`, `stretch(a, b)`, `describe()`, `facts_lines()`.

## Changes
- `assistant.py`: WALK now derives from route_facts (fixes 6 vs 12 min). New rule intent `effort` (steps, distance, time, climb, steepness, "can my mother manage", ramp / wheelchair route) in six languages plus romanised forms; uses the pilgrim's position, else Base Camp and says so. Step words are stripped before stop matching, so "mettlu" / "మెట్లు" is never Main Steps (typing "Main Steps" still works). `strip_ids()` removes g1..g5 and "(g2)" from every reply (one place, in `answer()`). Route facts are in the model facts block.
- `GET /api/map`: paths gain `steps, distance_m, climb_m, difficulty, wheelchair, surface, shelters`; top level gains `totals` and `remaining` (from the uid's position, with `to_gate` for the booked gate).
- Knowledge pack `venue_demo.json`: route numbers only (minutes, steps, shelters, no ids).
- `static/map.js` / `map.css`: summary strip (distance, steps, walking time; "From here" when position known), quiet label per stretch (steps, min, "steep" on the hardest), plain text lines in lite mode.
- `tests/test_route_facts.py` new; two numbers in `tests/test_brain.py` updated (walk 9 to 20, 29 to 70) because they hard-coded the old minutes.

## Verified
- Full suite: 382 passed. Deployed to kind; on localhost:8088 the three test questions answer 480 steps / 2.4 km / 90 min from Base Camp (English and Telugu) and 440 steps / 1.9 km / 80 min from River Crossing; /api/map carries the new fields.
- Screenshot at 390 px (Chrome for Testing, temp profile) viewed: no collisions between stretch labels and stop cards.
- No Sarvam calls used; all answers are rules-only.

## Not verified
- "From here" strip state and lite mode were not screenshotted (logic exercised only via /api/map and code reading).
- Translations of the new strings are mine, not checked by a native speaker.
- "Steps left to Main Steps" counts to the shrine, not to that stop.
