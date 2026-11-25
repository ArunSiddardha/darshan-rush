# NOTES_SARVAM: Sarvam additions (read a photo, site check, key pool)

Nothing existing was edited. Nothing committed. New files only:
`app/sarvam_keys.py`, `app/addons_read.py`, `app/addons_scam.py`, `app/tests/test_addons_sarvam.py`,
`app/static_samples/{token_card,signboard}.png`, `app/addons_ui/{read_photo.html,read_photo.js,site_check.html,site_check.js,phone_line_card.html}`.
Helper scripts (outside repo): `/Users/arun/hackathon/festive/_tools/{make_sarvam_samples.py,probe_docai.py,sarvam_addons_app.py}`. Pillow was installed into repo/.venv (add `pillow` to requirements only if you want to regenerate the samples; the app does not need it).

## Which Sarvam image API works (verified with our key)
**Sarvam Vision / Document AI**, an async job API (docs: docs.sarvam.ai/api/api-guides-tutorials/document-intelligence/how-to/parse.md):
`POST /doc-ai/v1/job/parse` (multipart `file`, `language`, `output_format=md`, returns 201 + job_id) then poll `GET /doc-ai/v1/job/{id}/status` then `GET /doc-ai/v1/job/{id}/results` (JSON blocks with text and reading_order). Real calls worked, about 1.3 to 2 s end to end for a small image (one run 5 to 7 s, so we allow 25 s polling).
I did not test whether a vision chat model accepts images (not needed, Document AI works). No other vendor used.
Finding: language hint matters. With `en-IN` Sarvam Vision hallucinated garbage Malayalam on the Malayalam lines of the mixed signboard; with an Indic hint (ml/te/hi) both the English and Malayalam lines read correctly, and the English token card reads correctly under every hint. So the endpoint defaults the OCR hint to `hi` (env `READ_OCR_HINT`, or form field `source_lang`).

## Endpoints
- `POST /api/read-photo` multipart `image`, `lang`, `uid` (optional `source_lang`) returns `{text, translated_text, audio_base64 (WAV), lang, latency{read_ms,translate_ms,tts_ms,total_ms}, notice}`. Max 8 MB, PNG/JPEG/TIFF/PDF. Errors return the same shape with a `notice` and status: 402 (credits, text "Voice unavailable (Sarvam credits). Type instead."), 429, 415, 413, 503 (no key), 504. If only TTS fails, text and translation are still returned with a notice. English pilgrims with English text skip translation.
- `POST /api/site-check` JSON `{text|url, lang, uid}` returns `{verdict: caution|high_risk|unknown, reply_text, audio_base64, reasons (English strings), reason_codes, lang, latency, notice}`.
  Rules first: payment, urgency, VIP/skip-queue, OTP/Aadhaar asks, tout phrases, shortened links, lookalike host words, odd TLDs, non-government site asking for booking. The Sarvam chat model (sarvam-105b) is called only when rules find nothing, and can only raise to caution/high_risk. Only a host that really ends in `.gov.in` (parsed hostname, so `gov.in.evil.com` and `x.gov.in@evil.com` do not count) gets "This looks like a government address, still check on the official notice board...". No reply ever says genuine, safe, legitimate or authentic (a test checks this). Reply is written in English by template, translated with /translate, spoken with bulbul.
  `reasons` stay in English (the spoken/shown reply is in the pilgrim's language).

## Verified for real (25 Nov 2026, own sample images, real key, throwaway app on port 8791, stopped)
Read photo, total ms (read / translate / tts): token card ml 5325 (1533/1421/2370), te 5670, hi 4909; signboard ml 5766, te 4814, hi 4829. Translations came back in correct Malayalam, Telugu, Hindi scripts with audio.
Site check, total ms: "pay 500 for a quick darshan pass" ml 5603, te 6078, hi 5849 (all high_risk); non-gov booking link ml 5824 (caution); .gov.in link te 3915 (unknown, gov line); a chat-classified harmless message (hi) 4689 with classify 1.0 s (verdict unknown, so chat path works). Latency is dominated by translate (~1.5 s) plus bulbul TTS (2 to 4.5 s). Offline tests: `cd app && ../.venv/bin/python -m pytest -q tests/test_addons_sarvam.py` gives 12 passed.

## Key pool and the two-line change for app/sarvam.py (I did not edit it)
`sarvam_keys.py`: `current()` returns SARVAM_API_KEY or SARVAM_API_KEY_2 (first not cooling), `on_status(code)` puts the current key on cooldown after 402 (10 min) or 429 (30 s) so the next `current()` is the other key, `request()` retries once on the other key. My two routers already use it. To make the existing client use it: add `import sarvam_keys`; in `_headers()` replace `config.SARVAM_API_KEY()` with `sarvam_keys.current()` (also the `Bearer` line in `chat()`); in `_post()` right after `ms = ...` add `sarvam_keys.on_status(r.status_code)`. (Optional: make `available()` use `sarvam_keys.available()`.) The 402 then still raises for that call and the next call uses key 2. Rotation across the two keys was only unit tested, not triggered live (key 1 has credits now).

## Integration
In main.py: `from addons_read import router as read_router`, `from addons_scam import router as scam_router`, `app.include_router(read_router)`, `app.include_router(scam_router)`. Env: SARVAM_API_KEY (+ optional SARVAM_API_KEY_2, SARVAM_TTS_MODEL/SPEAKER, SARVAM_CHAT_MODEL, READ_OCR_HINT, READ_POLL_TIMEOUT_S). python-multipart is already in the venv; confirm it is in requirements.txt (needed for the upload). Both routers import `sarvam_keys` and `addons_read` as top-level modules (app dir is on the path, as for sarvam.py).
UI: paste the three `.html` fragments where wanted (each is a `<details>`, collapsed by default; phone_line_card is a plain labelled note with no number), load `read_photo.js` and `site_check.js`, then call `AddonsReadPhoto.init(document.getElementById('ad-read'), {uid})` and `AddonsSiteCheck.init(document.getElementById('ad-site'), {uid})`. Language is taken from `window.DARSHAN_LANG` if set, else the select in the fragment (set the global, or delete the select). Styles use CSS variables with fallbacks. Only globals are `AddonsReadPhoto` and `AddonsSiteCheck`.

## Unverified / caveats
- UI fragments were not opened in a browser (no time); they are plain DOM code. Camera capture (`capture=environment`) behaviour on iOS/Android untested. The "spoken description" input is typed text (use the existing STT path to fill the textarea if wanted).
- Real photos (glare, blur, angles) not tested, only clean PIL images. Document AI is built for documents; a distant signboard may read poorly.
- Key rotation not triggered live. Rules are keyword based and English-centred, plus a few Hindi/Telugu/Malayalam money words; non-English descriptions rely on the chat model second pass (which only fires when rules find nothing).
- Wording of the Malayalam/Telugu/Hindi warnings comes from Sarvam translate; not reviewed by a native speaker.
- Port 8765 was already used by someone else's process; I did not touch it.
