# Lane D notes (Frontend)

## Done
- app/static/index.html, style.css, map.js, app.js (pilgrim, 390 px first, six languages, SVG map, lite list, SIMULATED badge, footer, sponsor lines).
- judge.html (inline QR encoder, /api/config, rush button, live counters, before/after table), graph.html (SVG recovery chart, flip marker).
- README.md and .gitignore rewritten. Old cake-shop files moved to repo/_old/ (cake_index.html, cake_style.css, cake_shop.js). `_old/` is now gitignored.

## Verified
- QR encoder: decoded with macOS CIDetector for 4 URLs (27 to 130 chars, versions 2-8). Correct.
- Pilgrim page, booking, 402 message, graph, with a mock server on 127.0.0.1:8765 (not in repo). Screenshot at 500 px wide (browser minimum), no horizontal overflow.
- Flip marker on graph: data contained full->lite transitions; marker drawn from that, not visually inspected.

## Unverified (needs real backend)
- Real field shapes. Code is tolerant: /api/flags may be flat, {value} objects, or {flags:{}}; /api/queue gates {id,name,wait_min,load 0..1 or 0..100}.
- Browser mic recording and Sarvam audio playback.
- Lite banner is shown in the pilgrim's language but not spoken (no audio endpoint in contract).
- judge.html on a real phone via tunnel.

## Needs from other lanes (guesses I coded against)
- B: POST /api/event {uid,event:"reached_gate",gate} -> record via Flagsmith track_event. Not in the contract; please add (page ignores failure).
- B: POST /api/slots/book accepts {uid,gate,lang}; returns {slot:{gate,time}|string, mode}.
- B: GET /api/config -> {public_url}. GET /api/metrics-lite should add `phones` (unique uids seen in last ~30 s, from /api/queue?uid=). Judge counter shows "-" otherwise.
- B: /api/flags should include map_mode, slot_mode, voice_directions (variant 'voice' or 'map'; 'map' puts the map above the mic).
- B: rush start token header: page sends both X-Rush-Token and X-Incident-Token, token from ?t= on judge.html (stored in localStorage).
- C: POST /api/directions multipart form: audio or text, uid, lang (+readback=1 for slot readback); expects {transcript, reply_text, audio_base64, optional slot}. Return HTTP 402 for Sarvam credits.
- Old app/static/owner.html still links /static/style.css (restyled); lane C replaces it with volunteer.html.
- Lead: fill README demo link, sponsor feedback column, team names.
