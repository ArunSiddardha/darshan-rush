# Darshan Rush v2 interface (lane: design)

New pages live in `app/static_v2/`. Nothing in `app/static/`, no `.py`, no k8s files were touched. Nothing is committed and nothing is swapped in.

## 1. References studied (390 x 844, `metrics/shots/v2/ref/`)

- **GOV.UK Design System** (button, task list): one bold 19 to 36 px sans, two weights only, short lines, a heavy left-aligned heading, solid full-width buttons with a hard bottom edge, no decoration. Took: plain sentence-case labels, one action per screen, large tap targets.
- **Zerodha Kite login**: almost empty first screen, one field, one orange button, small quiet footer. Took: the first screen holds one thing.
- **CRED landing**: one large confident headline, everything else small and quiet. Took: weight contrast (one big element, the rest small).
- **Airbnb**: pill chips in a sideways-scrolling row that never wraps, one accent colour, 24 px side margins. Took: the language switcher and the side margin.
- **BMRCL metro**: a counter-example. Kannada set too heavy and too tight, many colours, banners. Took: what to avoid for Indic text (give it line height, do not bold it all).
- **DigiYatra**: blocked ("Access denied") to headless browsers. **IRCTC**: HTTP/2 error. Not used.

What makes them clean, in short: one type family; at most two weights on a screen; five sizes or fewer; lines under 60 characters on a phone; a 4/8 px rhythm; one accent colour used only for the main action; the first screen shows one task; cards are flat white on a tinted ground with one soft shadow; buttons are solid, full width, 48 px or taller; labels are sentence case and never truncated.

## 2. Tokens (`static_v2/style.css`)

| Token | Value | Use |
|---|---|---|
| `--bg` | `#F3F1EC` | warm neutral page |
| `--surface` | `#FFFFFF` | cards |
| `--sunk` / `--line` | `#EAE7E0` / `#DEDAD1` | tracks, dividers |
| `--ink` / `--ink-2` / `--ink-3` | `#1A1917` / `#55514A` / `#77726A` | text (ink-2 is AA on bg and white) |
| `--accent` | `#0D5C63` deep teal | the one accent: mic, primary button, pass |
| `--ok` | `#2B7149` | success, Yes, recovered |
| `--warn` | `#8A5300` | SIMULATED tag, lite banner, voice paused |
| `--bad` | `#B42318` | only a failure happening now, No |

Type scale (five sizes): 13, 16, 20, 28, 56 px. Spacing: 4, 8, 12, 16, 24, 32, 48 px. One radius: 14 px (pills fully round). One elevation: `0 1px 0 rgba(26,25,23,.04), 0 10px 28px -14px rgba(26,25,23,.22)`.
Line height: Latin 1.45; Malayalam, Telugu, Kannada, Tamil 1.7; Devanagari 1.6 (set by `:lang()` on the html element, Latin islands reset with `lang="en"`). Checked in screenshots: no clipped marks in ml, te, kn.

Components: buttons (primary, secondary, quiet, yes, no), mic (with listening pulse), progress dots, card, flat card, chip, status pill (calm, ask, wait, ok, bad), message line (neutral, warn, bad, ok), field, inline form, expander, stepper, bottom sheet, footer. Icons: inline SVG symbols, 1.8 px round stroke, no emoji anywhere. Motion: mic pulse, card enter, sheet slide, chevron turn; all switched off under `prefers-reduced-motion`.

## 3. Fonts

**Anek** superfamily by Ek Type (Anek Latin, Malayalam, Tamil, Telugu, Kannada, Devanagari), SIL Open Font License 1.1, from Google Fonts. Self-hosted in `static_v2/fonts/` (2.5 MB, variable wght 400 to 700 and wdth 75 to 125, one woff2 per script). `static_v2/fonts.css` declares all seven files under ONE family name, `'Anek'`, split by `unicode-range`, so every script uses the same design and the browser downloads only the scripts on screen. `font-display: swap`, fallback stack Noto Sans (per script), system-ui.
Weights used: 420 body, 540 to 580 labels, 600 to 660 headings and numbers. Display: no second face. After looking, a serif next to six Indic scripts read as two products; instead the big numbers (slot time, judge numbers) use Anek Latin at width 112 to 118 and weight 640 to 660, which keeps one family. Unused files from the download are in `static_v2/fonts/_unused/` (safe to delete).

## 4. Pages and the API each one calls (same calls as v1)

**index.html + app.js + pilgrim.css (pilgrim)**
- `GET /api/flags?uid&lang[&age65=true][&expose=0]` every 5 s (map_mode, slot_mode, voice_directions, traits)
- `GET /api/queue?uid&lang` every 3 s (gates, map_mode, slot_mode)
- `POST /api/slots/book` JSON `{uid, gate, lang}` (Book the shortest queue)
- `GET /api/slots?uid` once on load, to restore my pass after a reload (new; read-only, already exists)
- `POST /api/directions` form: `audio` or `text`, `uid`, `lang`; `readback=1` for Play again and for elder spoken help; text `is this booking site real <url>` for the add-on (uses the existing verify intent)
- `POST /api/event` JSON `{uid, event:'reached_gate', gate, lang}`
- States: first screen (wordmark, SIMULATED, language row, prompt, mic, Type instead), listening, thinking, reply card, booked pass, elder voice-first (`localStorage.elder`, the More help toggle, or a Flagsmith trait `age_65_plus`), lite (from map_mode). Screenshot-only states: `?demo=listening|thinking|reply|lite|elder|error`, `?lang=xx`.
- Messages by real cause: Sarvam 402 or "credit" text, 429 rate limit, mic blocked (NotAllowedError), no mic, network lost (only after 9 s without a queue answer), booking busy (5xx). Non-failure messages fade after 9 s.
- Add-on entry points for the other agent: `<details id="addonRead" data-addon="read-this">` with body `#addonReadBody` (currently says "Not available yet in this prototype"), and `<details id="addonReal" data-addon="is-it-real">` (already working through /api/directions).

**volunteer.html**
- `GET /api/volunteer/state` every 2 s; `GET /api/volunteer/audio?kind=question|confirm`; `POST /api/volunteer/reply` (text yes/no or audio); `POST /api/volunteer/crowd-report`; `POST /api/directions` with `walkin=1` for walk-in booking.
- Status card: All calm / A question for you / Waiting for the duty officer in NudgeBee / Not sent to NudgeBee (webhook_ok false) / You said no / Booking recovered.

**judge.html + qr.js**
- `GET /api/config`, `/api/volunteer/state`, `/api/metrics-lite` (2 s), `/api/flags?uid=judge-screen&expose=0` (4 s), `/api/experiment` (4 s); `POST /api/rush/start`, `/api/rush/stop` with `X-Rush-Token` from `?t=`. QR encoder copied unchanged from v1.

**graph.html**
- `GET /api/metrics-lite` every 2 s; three aligned lanes (p95, errors, requests per second) and a dark marker where map_mode went full to lite.

## 5. What the pages expect from the backend that is missing or weak

- `metrics-lite.restarts` is always `null`, so "pod restarts" shows "-" (v1 same).
- Elder mode reads `F.traits.age_65_plus` (or `age65`) from `/api/flags`; today traits come back empty unless `age65=true` is sent. If Flagsmith should switch elders on by itself, the flags response needs a clear field such as `voice_first: true`.
- Volunteer notes text from the backend says "Type instead" on a page that has buttons; the page rewrites any "credit" note to "Voice is paused: Sarvam has no credits left. Use Yes or No."
- "Read this for me" has no endpoint yet.
- Gate names come only in English from `/api/queue`; they are tagged `lang="en"` so they render correctly inside other scripts.

## 6. Verification

Served with my own stdlib proxy `/Users/arun/hackathon/festive/_tools/design_serve.py` on **port 8766** (8765 was already held by another process, PID 62248, which I did not touch), proxying `/api/*` to the real backend on 8088. Stopped by exact PID when done. Screenshots in `metrics/shots/v2/` (script: `_tools/design_shots.cjs`): pilgrim home en/ml/te, booked en/ml/te (real bookings against the backend), reply ml, listening te, thinking en, lite te, elder ml, about sheet, volunteer asking (phone and desktop), judge (phone and desktop), graph (phone and desktop). Three review rounds; fixed: closed sheet showing in full-page shots, Latin line height inside Indic pages, book button leaking onto the first screen, the "now" step on the stepper, the volunteer question size, judge chain label size, graph height at 900 px. No JS page errors in any shot.
Not verified: real microphone recording (headless has no mic), Sarvam audio playback (credits), the lite state from a real flag flip (shown via `?demo=lite`), Kannada/Tamil/Hindi screenshots (strings written, not shot).

## 7. Swap-in steps (for the lead; not done)

1. `mv app/static app/_old_static_v1` (or into `_old/`), then `mv app/static_v2 app/static`. Optionally delete `app/static/fonts/_unused/`.
2. All asset paths are absolute `/static/...`, matching how `main.py` mounts the folder and serves `/`, `/volunteer`, `/judge`, `/graph` as files from it. `map.js` and the old `style.css` are no longer used. `/map` falls back to `index.html` when there is no `map.html`, so it keeps working.
3. The Dockerfile copies `app/` so fonts ship with the image; the image grows about 2.5 MB.
4. Hard-reload phones once (the old `style.css` may be cached).
5. Translations of the new strings (ml, ta, te, kn, hi) were written by me, not by a native speaker: worth a quick check by a speaker before the demo.
