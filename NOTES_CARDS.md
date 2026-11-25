# NOTES_CARDS: non-app pictures of the film

Everything is NEW files under `demo/v2/cards/` and `demo/v2/tools/`. No Sarvam calls, no existing file edited.
Renderer: Chrome for Testing (Playwright, own profile `_tools/tmp-profile-cards`) draws the pages in the app's Anek font and palette; ffmpeg does fades and layering.
All clips: 1920x1080, H.264, 30 fps, yuv420p, no audio.

## Cards (`demo/v2/cards/clips/*.mp4`, stills in `cards/png/*.png`)
| File | Dur | Film time | What |
|---|---|---|---|
| 01_hook1.mp4 | 6.0 s | 0:00-0:06 | black, white Anek, "8 January 2025. Tirupati. ..." (fades out by 6.0) |
| 02_hook2.mp4 | 6.0 s | 0:06-0:12 | "They were not waiting for God. They were waiting for a number." text 0:06-0:11, then 1 s black ("a number." in saffron) |
| 03_lakshmamma.mp4 | 8.0 s | 0:12-0:20 | name, three facts appearing one by one, grey "fictional pilgrim" line |
| 04_later.mp4 | 2.5 s | 0:54-0:56.5 | indigo, "Later. Everyone arrives at once." + "Simulated crowd." (script has no fixed length; hard cut to the graph after) |
| 05_meera_ml.mp4 | 6.0 s | 1:20-1:26 | Meera, Malayalam speaker version |
| 05_meera_neutral.mp4 | 6.0 s | 1:20-1:26 | same without the language line (use if Meera is voiced in Telugu) |
| 06_numbers.mp4 | 7.0 s | ~1:44-1:52 | Before (saffron) then After (indigo); values from `numbers.json` |
| 07_money.mp4 | 12.0 s | 2:14-2:26 | three lines at 0.8 s, 4.6 s, 8.2 s |
| 08_honesty.mp4 | 6.0 s | 2:26-2:32 | three lines at 0.6, 1.9, 3.3 s |
| 09_closing.mp4 | 4.0 s | 2:38-2:42 | black, "This time, nobody stood in a crush for a number." |
| 10_end.mp4 | 4.0 s | 2:42-2:45 | Darshan Rush, three sponsor names as text, team line, disclaimer footer (4 s; trim to 3 if needed) |
Layout examples (made by the tools, 6 s each): `example_phone.mp4`, `example_split.mp4` (+ `cards/png/example_*.png`).
**Contact sheet: `demo/v2/cards/contact_sheet.png`** (all cards plus both layouts). Rebuild: `node tools/contact_sheet.cjs`.

## Change a number or a name and re-render one card (about 5 seconds)
```
cd /Users/arun/hackathon/festive/repo/demo/v2/tools
# 1. edit cards/numbers.json  (before/after big number, labels, lines, footnote, money.shrine_rs, money.cost_rs)
#    or cards/team.json       (team_line)   or the text in cards/cards.json
node render_cards.cjs 06_numbers      # or 07_money, 10_end ... (several ids allowed, none = all cards)
node contact_sheet.cjs                # optional
```
Take-based numbers: rehearsal defaults are in `numbers.json` (p95 3081 ms = "3.1 s", crash after 19 s, after 15 ms, 0 crashes, 1,107 rps = "1,100").
Timings and wording per card live in `cards/cards.json` (`dur`, per item `at` = fade-in second, `d` = fade length, `out` = optional fade-out, `fade` = [in, out] for the whole card). `*word*` makes saffron. If the narration runs longer, raise `dur` and the `at` values.

## Overlays (`demo/v2/cards/overlays/`, transparent 1920x1080 PNGs unless noted)
`sponsor_sarvam|nudgebee|flagsmith|all.png` (top right pill, indigo 88% with white 28 px text; the storyboard said 60%, which was hard to read on off-white), `caption_example.png`, `subtitle_example_right.png`, `subtitle_example_center.png` (46-50 px white on a soft dark plate), `phone_back.png` (opaque warm off-white, soft shadow), `phone_ring.png` (neutral bezel, no brand; place a 390x844 recording at x=168,y=107 scaled to 400x866 under it), `split_mask.png`. Sizes and positions: `tools/layout.json`; rebuild with `node tools/make_overlays.cjs`.

## Tools (`demo/v2/tools/`)
- `compose_frame.sh --src phone.mp4|png --out o.mp4 [--caption "One tap. Then she *just talks.*"] [--sponsor sarvam|nudgebee|flagsmith|all|none] [--subs cues.txt] [--dur 6] [--ss 0] [--fade 0.3] [--png still.png --png-at 2.5]`
  Phone left, caption right, subtitles in the right column (left aligned). Source may be a video (duration read from it, `--ss` start offset) or a still (default 6 s). Any aspect ratio is letterboxed onto the 400x866 screen.
- `split_screen.sh --src A --src2 B --out o.mp4 --caption "..." [--left-label NudgeBee --right-label Flagsmith] [--subs cues.txt] [--sponsor ..]`
  Two panels, labels above, caption centred under them, subtitles at the bottom centre.
- `subtitles.py cues.txt out.ass [--style laptop|right]`: cue file to .ass for an editor. Cue file lines: `start | end | text` (seconds or m:ss.s, `\n` for a line break).
- `render_cards.cjs`, `make_overlays.cjs`, `contact_sheet.cjs`, `compose.cjs` (the engine behind the two .sh files), `lib.cjs`, `layout.json`.
Never use `*` in a caption except for saffron emphasis.

## Verified
Rendered every card and both layouts, extracted frames and looked at them (stagger, fades, spacing, alignment, subtitle plate not colliding with captions); ffprobe confirms 1920x1080, h264, 30 fps, yuv420p, exact durations. Tested a video input (3 s mp4) through compose_frame.sh. Test placeholder shots from `metrics/shots/v2/`.

## Caveats
- The local ffmpeg has no libass or drawtext, so burned-in subtitles come from PNG plates drawn in Chrome (same cue file). The `.ass` from subtitles.py is for an editor that has libass, and needs the Anek TTFs installed (repo ships woff2 only).
- Subtitles switch on and off hard (no fade); captions and sponsor labels fade in.
- Card timings after 1:44 are my reading of the script; script gives no fixed length for the numbers card (7 s) or "Later" card (2.5 s). Team names are a placeholder in `cards/team.json`.
- `cards/_work/` holds temp files (page html, layers, test cues); safe to move aside.
