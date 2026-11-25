# NOTES_MAP: simulated site map (front end)

## Built
- `app/static/map.js` + `map.css` (new): one module `SiteMap.create(el, opts)` used by the pilgrim page and the staff page. Inline SVG hill route (river, trees, hill as quiet shapes), five numbered stops plus an end flag, load ring (arc length + colour) with a text label and a distinct glyph (Calm / Busy / Very busy), facility line icons per stop (water, toilet, medical, rest, wheelchair, cloak, lost and found, info) with a legend, "You are here" marker with pulse, ticket pill "Your gate", walked path solid and path ahead dashed, a "Next: X, n min walk, n min wait" line, SIMULATED tag. Stop sheet: wait, walk to next, facilities, "Take me here", "I am here". Names and strings in en, ml, ta, te, kn, hi.
- Pilgrim `index.html` / `app.js`: map section `#siteMap` below the fold, quiet "Site map" link under the talk button. A reply from `/api/directions` or a live turn (live.js now passes the raw response as `m.raw`) with position_gate_id, gate_id or show:'map' moves the marker (1.1 s animation along the path), highlights and scrolls to the stop. Rush mode (map_mode lite): same data as a light list, no animation, existing lite banner.
- "I am here" and "Take me here" send a sentence to `/api/directions` (JSON text, e.g. "I reached River Crossing"); the reply is shown in the reply card and moves the marker.
- Staff `volunteer.html`: "Site overview" collapsed in the calm view with the compact map; tap a stop -> "Report crowd here" posts text "<stop>, many people waiting" to `/api/volunteer/crowd-report`.
- Screenshots: `metrics/shots/map/` (390 px: en, te, ml at g1/g3/g4/g5, rush lists en, ml, stop sheet, staff overview, 1440 px map; real `/api/map` data in api-en-m.png). Screenshot-only params: `?pos=g3`, `?demo=lite`, `/volunteer?ov=1`.
- Deployed (build_load.sh, deploy.sh); `/static/map.js` and `map.css` are served on the public URL.

## Backend gaps
- `/api/map` position is only set if the assistant stores it; the page also remembers the last position in localStorage when the API says null. A dedicated "set position" endpoint would be cleaner than sending a sentence.
- Per-stop "needs help" counts for staff: the page reads `help` or `needs_help` on a stop (not in the contract yet). `SM.setHelp({g3:2})` is the hook.
- Crowd-report text has no count, so the backend may answer "not understood"; the sheet says "Report sent" regardless of the server verdict.
- Stop names come from the page's own translations (API gives English only); the API x,y are ignored (fixed layout so labels never collide).

## Unverified
- Translations written by me, not a native speaker. Ta, kn, hi were not screenshotted.
- Real phone, bright light, touch targets (headless only). Live-turn map move (needs a real mic session) and the 1.1 s animation were not captured; only static frames.
- Not shot at all five stops in every language: te g1, ml g5, en g3/g4/g2 verified; others use the same code path.
- Staff "Report crowd" end to end.
