# Shot list: who records what

Deadline: all raw clips in by 15:30 IST, final video by 16:00, submit by 17:00.
Beat numbers match SCRIPT.md. The lead = the Claude session on the Mac. Arun = on the phone at the venue.

| Beat | Shot | Who | How | File name |
|---|---|---|---|---|
| 1 | Title card, 8 Jan text card | lead | made by assemble.sh (title) and one extra text line in EDIT.txt | - |
| 2 | Pilgrim page, Telugu speech, slot read back | **Arun** (phone) | iPhone, public URL, section B | `pilgrim_te.mov` |
| 3 | Judge page, QR, phones counter | lead | `record_pages.cjs` page `judge` | `raw/judge-1280x720.webm` |
| 3 | Room: judges scanning | **Arun** (phone, optional) | normal Camera app, 5 to 8 s, landscape | `room.mov` |
| 4 | Recovery graph while rush runs | lead | `record_pages.cjs` page `graph` | `raw/graph-1280x720.webm` |
| 4 | Pod killed, restart count | lead | `record_pages.cjs` page `kube` (live `kubectl get pods`) | `raw/kube-1280x720.webm` |
| 5 | NudgeBee finds the cause, its words | lead | NudgeBee execution view, section A3 | `raw/nudgebee_*.webm` |
| 6 | Volunteer page, Malayalam question, spoken yes | **Arun** (phone) | iPhone, public URL `/volunteer`, section B | `volunteer_ml.mov` |
| 7 | Approve in NudgeBee, flags flip in Flagsmith | lead | section A3 and A4 | `raw/nudgebee_approve.webm`, `raw/flagsmith.webm` |
| 8 | Recovery numbers, before and after | lead | graph after recovery plus the two-column card | `raw/graph-...`, card in EDIT.txt |
| 9 | Segments and A/B card | lead | Flagsmith dashboard segments, `/static/addons_ui/ab_card` fragment if mounted | `raw/flagsmith_ab.webm` |
| 10 | End card | lead | assemble.sh (end) | - |
| all | Narration audio (English) | **Arun** | voice memo, section B5 | `narration.m4a` |

## A. The lead, on the Mac (headless browser, nothing touches your own Chrome)

Run order for the full take (needs about 6 minutes; do it once as a rehearsal first):

1. Reset: `/Users/arun/hackathon/festive/repo/scripts/reset_demo.sh`
2. Start the captures you need in the background, each for the length of the run (example 150 s):
   `cd /Users/arun/hackathon/festive/repo/demo && node record_pages.cjs 150 graph kube`
   (the judge page needs `PRESS=1` only if you want the script, not a person, to press "Cause the rush": `PRESS=1 node record_pages.cjs 150 judge`).
   Pages written to `demo/raw/<page>-<size>.webm` at 1280x720 (desktop pages) or 390x844 (pilgrim, volunteer).
3. NudgeBee execution view (beats 5 and 7): the helper scripts in `/Users/arun/hackathon/festive/_tools/` (`nb_exec.cjs` opens the running execution, `nb_approve.cjs` clicks approve) attach to a logged-in browser through `hb.cjs`. Record that browser tab with the same `recordVideo` option, or take a screenshot every 2 s and use them as stills in EDIT.txt. Show the investigation text and the approval card clearly; the approval click must be visible.
4. Flagsmith dashboard (beats 7 and 9): open the project's feature list, with `map_mode` and `slot_mode` visible; capture before and after the approval so the values visibly change from full to lite and open to staggered. Never show the admin key or the environment key. Segments page for the age 65+ and language traits.
5. After recovery stop the captures; check the files with `ffprobe` and by extracting one frame each.

If a capture misses the moment (the flip is quick): run `scripts/flip.sh lite staggered` while recording, then `scripts/reset_demo.sh`, and label nothing as live that was not.

## B. Arun, on his iPhone at the venue

### B1. Setup (5 minutes, before any take)
1. Charge above 50%. Turn on Do Not Disturb (swipe down from the top right, tap Focus, Do Not Disturb) so no banner or call shows in the video.
2. Settings > Control Centre: make sure "Screen Recording" is in the list (green plus if not).
3. Safari: open the public URL. The lead will send it (it is the cloudflare address in `metrics/public_url.txt`; it changes if the tunnel restarts, so use the latest). Allow the microphone for the site when asked (Settings > Safari > Microphone if it was refused).
4. Join the same Wi-Fi as the venue or use mobile data. Open the page once now to check it loads.
5. Volume up so the app's spoken reply is audible, but not at maximum.

### B2. Screen recording WITH your voice (microphone on)
1. Swipe down from the top-right corner to open Control Centre.
2. **Press and hold** the round Screen Recording button (do not just tap). A panel opens.
3. Tap the **Microphone** button at the bottom so it turns red and says "Microphone On". Choose Safari to be safe; the Photos option stays off.
4. Tap **Start Recording**. A 3 second countdown runs; swipe up or tap an empty spot to close Control Centre before it ends.
5. Do the take (steps B3 and B4).
6. Stop: open Control Centre and tap the red recording button, or tap the red clock in the top-left and tap Stop. The video lands in Photos > Recents.
Note: the microphone records the room (your voice and the phone's loudspeaker). The app's own voice plays out of the speaker and is picked up by the microphone. That is fine; it makes the "hears her slot" moment real.

### B3. The pilgrim take (about 40 s, beat 2, file `pilgrim_te.mov`)
1. Open the public URL `/` in Safari. Choose Telugu from the language row.
2. Start the screen recording (B2). Wait 2 seconds, still.
3. Tap the large microphone. Say slowly, like a grandmother: "Ammaa, repu poddunne darshananiki oka time ivvandi." Pause. Wait for the slot card and the voice reply. Do not touch the screen while the reply plays.
4. Tap the microphone again. Say: "Maa ammaki debbai ellu." Wait for the answer.
5. Wait 2 seconds, stop the recording.
If it goes wrong, do not narrate over it: stop, delete in Photos, start again.

### B4. The volunteer take (about 30 s, beat 6, file `volunteer_ml.mov`)
1. The lead triggers the incident (rush start, pod killed, NudgeBee finds the cause). Ask the lead "ready" before you start. Open `/volunteer`.
2. Start the screen recording (B2) when the Malayalam question appears on the page.
3. Let the question show for 3 seconds. Tap the large microphone and say in a natural, calm voice: "Sari, cheyyu." Wait for what it heard, then for "Waiting for the duty officer to confirm in NudgeBee".
4. Hold still for 2 seconds, stop the recording.
If the microphone fails, tap the Yes button on the page; this is the typed fallback and is honest ("typed yes"). Say so in the caption if you use it.

### B5. Narration (do this last, in a quiet corner)
Voice Memos app > red button > read the narration from SCRIPT.md at a calm speed, one beat at a time, with a 1 second pause between beats > stop > Share > AirDrop to the Mac or send by WhatsApp "as document" (keeps the quality). Name it `narration.m4a`.

### B6. How to hold a clean take
- Phone upright, a steady grip, elbows on the table. No notifications (Do Not Disturb on), no battery warnings, close other apps.
- Speak toward the bottom of the phone, from about 20 cm. Background noise: move away from loudspeakers.
- Start recording, wait 2 s, do the thing, wait 2 s, stop. The lead trims. Never stop mid-sentence.
- One take per file. Do each take twice and keep the better one.
- Do not show your own contact names, your Wi-Fi password or notifications. Screen recording shows the status bar: turn on Do Not Disturb first.

### B7. Sending files back (all to the lead, easiest first)
1. **AirDrop** to the Mac: Photos > select the videos > Share > AirDrop > the Mac. They land in Downloads on the Mac. Tell the lead the file names.
2. If AirDrop is not available: Photos > select > Share > Save to Files > iCloud Drive > then it syncs to the Mac, or Share > Mail/WhatsApp (choose "Actual size" or send as document, not "Auto", so it does not shrink).
3. Send the narration the same way.
4. The lead converts: `ffmpeg -i file.mov -c:v libx264 -crf 18 -c:a aac file.mp4` is done by `assemble.sh` automatically (it reads .mov as is).
Phone video is 1170x2532 (or similar); the lead's layout scales it to the left of the frame with a big caption on the right.

## C. Fallback if Arun cannot record

The lead captures the pilgrim and volunteer pages on the Mac, with typed input, and labels them clearly "Typed input on a Mac, not a voice take".
1. `cd /Users/arun/hackathon/festive/repo/demo && node record_pages.cjs 40 pilgrim volunteer` records the pages as they are (390x844 phone viewport). For typed interaction use the page's typed-question box (visible when the microphone is not available); the lead drives it with Playwright `page.fill` and `page.click` and records the same way.
2. In EDIT.txt use the caption "Typed input on a Mac (voice recording not available)" on those two clips and say so in the narration: "In this take we typed instead of speaking, because ...". Never present typed input as the voice demo.
3. Use the Sarvam sample clips as stills only if the lead has real files from earlier tests; do not call Sarvam for new audio (credits are low).
4. Narration can still be recorded on the lead's side of the table with Voice Memos; or use a quiet room on any phone.
