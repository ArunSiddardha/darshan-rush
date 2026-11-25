# NOTES_DEMO (demo kit, 25 Nov 2026)

All new files, all under `repo/demo/` (plus this note). No existing file touched. No Sarvam call was made.

## Built
- `demo/SCRIPT.md`: 10 beats with timings, narration (399 words counted), Telugu and Malayalam phrases with Roman and meaning, on-screen content, sponsor per beat, and a 90-second cut-down.
- `demo/SHOTLIST.md`: who records what. Lead on Mac (judge, graph, kubectl view, NudgeBee, Flagsmith), Arun on iPhone (pilgrim and volunteer, step-by-step with mic on, how to hold a take, how to send files), typed-input fallback.
- `demo/record_pages.cjs`: `node record_pages.cjs <seconds> [judge graph pilgrim volunteer kube]`. Headless Chrome for Testing, own profile `_tools/tmp-profile-demo`, recordVideo 1280x720 (desktop pages) and 390x844 (phone pages), output `demo/raw/<page>-<size>.webm`. The judge token is read from `.env` and never printed. `kube` renders a live `kubectl get pods` (context kind-nb, ns darshan) as a terminal look-alike, since a headless browser cannot capture a real terminal. `PRESS=1` clicks "Cause the rush" on the judge page.
- `demo/assemble.sh [EDIT.txt] [narration]` + `make_cards.cjs`: builds `darshan-rush-demo.mp4` (1080p30, h264/aac) and `contact-sheet.jpg`. Layouts: full, phone-left-with-caption, side-by-side (`a+b`), title, end. Loudness -16 LUFS. ffmpeg here has no drawtext, so captions, title and end card are rendered to PNG by headless Chrome in the Anek fonts (from `static_v2/fonts` if present, otherwise `static/fonts`; static_v2 does not exist yet).
- `demo/EDIT.txt`: the 20-second dry-run edit (pipe format: file | in | out | layout | caption). The real edit must be written after the clips exist.
- `demo/SUBMISSION.md`: form text, sponsor table with file paths, simulated list, AI disclosure, team placeholder, and the "Judge this in 90 seconds" README block.
- `demo/.gitignore` ignores `raw/`, `work/`, `*.mov`.

## Verified
- `record_pages.cjs` recorded all five pages (5 s and 3 s runs) on the live app at :8088; ffprobe size correct; frames looked at.
- `assemble.sh` dry run: 21 s, 1920x1080 h264 + aac; contact sheet and end card frame looked at (fonts render, captions legible, phone layout and side-by-side fine). With a synthetic tone as narration the output measures -16.0 LUFS integrated.
- Narration word count per beat done by script.

## Not verified / caveats
- The current dry-run pages looked unfinished at capture time: the judge page bottom is cut at 1280x720 (the "Cause the rush" button sits at the edge) and the recovery graph shows "No data yet". Frame the real take after a rush, and check the judge page at 1280x720 (maybe use a taller viewport or edit the page).
- The two Telugu lines and the Malayalam yes were written by me, not checked by a native speaker; have a Telugu speaker listen once. I did not confirm the app reacts to "my mother is 70" (age trait); SCRIPT.md says to cut it if rehearsal shows nothing.
- NudgeBee and Flagsmith dashboard captures were not tested; the existing `_tools/nb_*.cjs` helpers attach to a logged-in browser via `hb.cjs` and I did not run them. SHOTLIST describes the intended capture; the lead may need screenshots as stills instead of video.
- Numbers in beat 8 (about 3,100 ms to 16 ms, 28 s to OOM) come from `metrics/rehearsal1.md`; re-read them from the real take before narrating. The narration says "sixteen milliseconds" and "twenty-eight seconds".
- iPhone steps are from standard iOS behaviour (Control Centre long-press for the microphone); wording of menus may differ by iOS version.
- The public URL is a quick tunnel that changes on restart; SUBMISSION uses [PUBLIC_URL] placeholders.
- Beat 2 requires Sarvam credits to work by voice; without them the page shows the typed fallback notice. Check credits before Arun films.

## For the lead, next
1. Check Sarvam credits, run `scripts/reset_demo.sh`, rehearse once.
2. Send Arun SHOTLIST section B and the public URL; get `pilgrim_te.mov`, `volunteer_ml.mov`, `narration.m4a`.
3. Record Mac clips (`node record_pages.cjs ...`), write the real `EDIT.txt`, run `demo/assemble.sh demo/EDIT.txt <narration.m4a>`, check `contact-sheet.jpg`, upload the video.
4. Paste the "Judge this in 90 seconds" block into README (README is not edited by me), fill SUBMISSION placeholders.
