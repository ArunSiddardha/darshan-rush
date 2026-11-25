# NOTES_ADDONS (integration pass, 25 Nov 2026)

## Built and verified
- **Design swap**: `static_v2` is now `app/static`; the old one is in `_old/static_v1`. All four pages use one system (Anek, tokens in `style.css`).
- **No language picker (pilgrim)**: language starts from the phone (`navigator.languages`), audio goes to Sarvam with automatic detection (`/api/directions` and `/api/live/turn` accept a missing or `auto` lang; live uses Sarvam `transcribe` mode for detection because `codemix` wrote romanised Hindi), the reply and the page follow the detected language, mid-conversation switches are followed. One or two word answers to our own question keep the conversation language (detection mishears single words). A quiet 'Language' item in More help is the manual override. Verified for real over the public https URL with an English phone and spoken Malayalam, Hindi, Telugu, Tamil, Kannada (all detected, replies in that language). English was tested with an English phone.
- **First screen**: wordmark, one large talk button, one line, cycling example phrases in the six scripts until the first words, then in the person's language. Nothing else above the fold.
- **Live mode is the default** (`addons_live.py` + `addons_ui/live.js`): one tap, then listen / answer aloud / listen; breathing level, captions, End. Tap-to-talk (single utterance, auto end after 1.5 s of silence, level meter, `isTypeSupported` recorder choice) is the fallback when live cannot start. Full hands-free booking verified over the public https URL with a fake microphone at 390 x 844 (see numbers below). A big Yes / No appears for the spoken "Shall I book it?" as a tap fallback, because a one-word answer can be misheard.
- **Volunteer screen**: one thing at a time (calm with 'Book for a pilgrim' and 'Report crowd', question, waiting, recovered / not sent / declined, walk-in, crowd). Staff language follows the phone (Malayalam or English) with a small EN / മലയാളം toggle in the footer. Yes needs a second deliberate press, No is one press. Alert sound and vibration when a question arrives (armed by the first tap on the page), polling every 2 s with a reconnect notice, nothing technical outside the 'Details' expander. Hands-free yes / no via `POST /api/volunteer/live-turn` (same reply shape as the pilgrim live endpoint, replies cached in `voice_seed`). Walk-in: tap 'Book for a pilgrim', the pilgrim (or volunteer) speaks, language is detected from the speech, the slot is read back in it, the big time is shown.
- **Judge and graph**: simplified; judge shows QR, rush button, chain, before / after, 'Flagsmith decides' (live values for this visitor via `/api/flags/decisions`), rollout percent, A/B card labelled TEST TRAFFIC, link to /sponsors.
- **Add-on 1 Flagsmith**: segment `elders_65_plus` switches `voice_first` on; the pilgrim page asks `/api/flags/decisions` with the stored age trait (set when the pilgrim says "my mother is 70") and opens the larger voice-first layout. `ui_copy` remote config is read for the example phrases and, in `slots.py`, for `slot_cap` and `slot_window_min` (30 s cache, falls back to env). Verified: decisions for an age 65+ identity show 'segment elders_65_plus (trait age_65_plus = true)'.
- **Add-on 2 A/B**: `/api/experiment` counts exposed / reached per variant; judge card says TEST TRAFFIC. Flagsmith's own experiment results are not available on this plan ("Events must be enabled to use experiment flags"): said plainly in README.
- **Add-on 3 rollout**: `scripts/rollout.sh` (built by the Flagsmith agent, real runs logged in `metrics/rollout.log`: healthy 10 / 50 / 100 and a simulated breach that paused and rolled back). Percent shown on the judge page. Rollout is back at 0.
- **Add-on 4 Read this for me**: in More help; verified over the public URL in Malayalam with `static/samples/token_card.png` (Sarvam Vision document intelligence, translate, speech). Two sample images in `app/static/samples/`.
- **Add-on 5 Is this booking site real**: in More help; verified over the public URL (high risk, spoken warning in Malayalam). Never claims a site is genuine.
- **Add-on 6 Phone line placeholder**: labelled card on the volunteer page only (inside the page footer area), no number.
- **Key rotation**: `sarvam.py` uses `sarvam_keys` (falls over to `SARVAM_API_KEY_2` on 402 / 429). `SARVAM_API_KEY_2` reaches the pod through the secret (whole `.env`). Not triggered live (both keys were not exhausted).
- **Sarvam credit protection**: all tests mock Sarvam and set `TTS_CACHE=0`; speech is cached by (language, text) on `/data` (`voice_cache`) and 20 fixed lines are shipped as audio in `app/voice_seed` (volunteer question, confirmation, please-say-yes-or-no, hands-free acks, live greeting / ask when / ask party / goodbye / unclear for ml, en, hi). Background warming of the live prompts is switched off (`LIVE_WARM=1` to enable). Real calls made by this pass: about 50 of the 60 allowed (17 to render the seed lines, the rest in the end-to-end checks).
- Core loop rehearsal (`scripts/rehearsal.sh`) re-run on the new image: OOMKilled once on the full map, 0 restarts and 37,587 requests on lite + staggered (`metrics/rehearsal1.md`). Full pytest: 189 passed.

## Usability acceptance (390 x 844, headless Chrome, fake microphone fed with recorded speech, mocked or real server as marked)
Pilgrim
- (a) Book by voice: 1 tap on the mic, then talk. Live: tap, speak "slot for tomorrow evening", speak "two people", then say yes or tap the big Yes: 2 taps, no reading, no typing. Public https run: the conversation reached the pass (17:00, Base Camp) in about 41 s including an 8 s wait the test adds for the greeting; a person answering straight away needs about 25 s. Tap-to-talk fallback: 1 tap, one sentence, slot shown (about 9 s in the mocked run).
- (b) Hear the slot again: 1 tap on 'Play again' (cached after the first time, no new call).
- (c) Waiting time at a gate: 1 tap and the question (live or single).
- (d) Not understood: spoken and written short line ('I did not catch that. Please tap and say it again.'), the mic stays the one retry tap; after two misses the typing row opens. Raw errors are never shown.
- (e) Slot survives closing and reopening (localStorage plus `/api/slots?uid`): verified by reload.
- (f) Body text 18 px, slot time 56 px, targets at least 56 px (checked: no interactive element under 44 px except a visually hidden file input), no horizontal overflow in all six languages.
- (g) Slow network: 'The network is slow. One moment.' after 10 s, progress dots while thinking, the lite page shows a one-line banner and keeps the rows.
Volunteer
- (a) Calm or question visible without scrolling. (b) Voice or Yes (two deliberate presses) / No (one). (c) Walk-in: 2 taps (Book for a pilgrim, mic) plus speech, slot shown large, spoken in the pilgrim's detected language. (d) Crowd report: 2 taps plus one sentence (or type). (e) Malayalam / English toggle, auto refresh, alert sound and vibration. (f) Nothing technical outside Details.

## Built but unverified
- iPhone Safari (no real iPhone here): WebKit was not available in this Playwright build, Chromium with a phone viewport was used. Live mode capture on iPhone (audio route, echo, barge-in thresholds) is untested; the single-tap fallback uses `audio/mp4` handling that the lead fixed earlier.
- Real microphone: the headless fake device hangs `getUserMedia` here, so the page was fed recorded speech through a replaced `getUserMedia` (real recorder, worklet, upload, server).
- A single spoken word of reply ('yes') through the live path was empty or garbled in two public runs with synthetic audio; that is why the tap Yes / No exists.
- Volunteer hands-free yes / no was tested with a mocked server and with the backend on text, not with real speech (credits). The yes path calls NudgeBee's approval webhook as before.
- Key rotation, the `rollout.sh` breach run after this integration, translations of new strings (written by agents, not native speakers).
- `app/tests/test_addons_sponsors.py` and `addons_sponsors.py` came from another agent; the full suite passes with them.

## Skipped
- Add-on 7 (count the crowd with the camera): skipped for time and credits, the brief says skip if short.

## Open items for the lead
- Run `scripts/reset_demo.sh` before recording (flags back to full / open; the rehearsal flips them).
- The pod's `/data` is an emptyDir: the speech cache is lost when the pod is replaced (a restart after an OOM keeps it); the shipped seed lines survive.
