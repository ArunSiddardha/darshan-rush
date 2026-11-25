# NOTES_CARE: Care requests (complaint or help, tracked, routed to the nearest volunteer)

A pilgrim says a complaint or a need for help in any of six languages. The system understands it, opens a tracked request (id like `C-27`),
sends it to the nearest on-duty volunteer, and keeps the pilgrim informed until it is closed. All NEW files; no existing file was edited.

## Files
- `app/care_store.py`: persistence (`<dir of STATE_FILE>/care.json`, audio in `care_audio/`), the roster, check-in.
- `app/addons_care.py`: rules, model step, routing, escalation, policy, hooks, router `router`.
- `app/tests/test_addons_care.py`: 59 tests, Sarvam mocked (`cd app && ../.venv/bin/python -m pytest -q tests/test_addons_care.py`).
- `app/addons_ui/care_pilgrim.html` + `.js`, `care_staff.html` + `.js`.
- Throwaway live app: `/Users/arun/hackathon/festive/_tools/care_live.py PORT` (serves the router and both fragments on one page; `?l=te&s=ml` picks languages).

## Integration steps
1. `main.py`: `import addons_care` then `app.include_router(addons_care.router)`. No new env vars (uses `STATE_FILE`, `SARVAM_API_KEY`).
   Optional: `addons_care.start_watcher()` in startup (re-routes unacknowledged requests every 15 s). Without it, escalation still runs on every `/api/care*` call.
2. Pilgrim page, "More help": paste `care_pilgrim.html`, include `care_pilgrim.js`, then
   `CarePilgrim.init(document.getElementById('care-pilgrim'), {uid: () => uid, lang: () => lang, stop: () => lastKnownStopId || null})`.
   Inside the conversation: in the assistant/turn handler call `care = addons_care.from_assistant(text, uid, lang, position_gate_id)`.
   It returns `None` for ordinary questions, else the same dict as POST /api/care (without audio). Use `care["reply_text"]` as the spoken reply, set `action: "call_volunteer"`,
   and call `CarePilgrim.refresh()` (or just show the status card) so the request number appears. It uses rules only (no model call, 0 ms).
3. Staff screen, third state "Requests near you": paste `care_staff.html`, include `care_staff.js`,
   `CareStaff.init(el, {volunteer: staffName, stop: staffStopId, lang: () => lang, onMapItems: items => ...})`. The "Check in here" form turns a staff member into a real volunteer
   (`simulated: false`) at a stop. `onMapItems` gives `[{id, stop_id, urgency, category, status}]` for pins on the site-overview map (emergency = red). The summary strip is in the fragment;
   the sponsors page can read `GET /api/care/stats`.
4. Flagsmith `care_policy` (remote config, JSON string): in `main.py` startup,
   `addons_care.set_policy_source(lambda: flags.get_remote_value("care_policy"))` (whatever the flags module offers to read a flag value; return a dict or JSON string, or None).
   Shape (all keys optional, invalid values ignored, any error = defaults):
   `{"ack_minutes":{"emergency":2,"urgent":5,"normal":15},"language_slack_stops":1,"emergency_language_slack_stops":0,"max_reroutes":4,"duty_officer_on_emergency":true,"use_model":true}`.
   Policy is re-read on every routing decision, so a flag change takes effect at once.
5. NudgeBee hooks (nothing is called by this module itself):
   `addons_care.set_hooks(on_emergency=fn, on_unacknowledged=fn)`. Each `fn(request_dict)` is run in a daemon thread, errors swallowed. `on_emergency` fires once when an emergency is
   opened (duty officer notified). `on_unacknowledged` fires each time the acknowledge limit passes with nobody acknowledging (before re-routing). Typically `fn = lambda r: httpx.post(NUDGEBEE_WEBHOOK, json={...})`.

## JSON contracts
`POST /api/care`: multipart (`audio`, `uid`, `lang`, `stop`?, `position`?, `choice`?) or JSON `{text, uid, lang, stop?, position?, choice?}`; `choice` is `medical|lost_person|tout_payment|other` (the four buttons; medical = emergency).
```
{ id:"C-27", category, urgency:"emergency|urgent|normal", urgency_reason, stop:{id,name}|null,
  assigned_to:{name, stop (name), stop_id, distance_stops, eta_min, simulated}|null, reply_text, audio_base64|null,
  status:"open|assigned|on_the_way|resolved|could_not_resolve", needs_stop:bool, summary_en, transcript, lang, via:"rules|model|button|rules_fallback", notice }
```
Voice or Sarvam failure never fakes anything: `audio_base64` is null with a `notice`; if speech to text fails nothing is created (`status:"not_created"`, `id:null`).
A repeat of the same category by the same pilgrim within 3 minutes returns the existing request (`notice:"duplicate"`).
Categories: medical, lost_person, lost_item, safety_crowd, harassment_theft, tout_payment, accessibility, water_toilet_clean, slot_booking, staff_behaviour, suggestion, other.
- `POST /api/care/{id}/stop {stop}`: pilgrim names the stop later (when `needs_stop`), re-routes.
- `GET /api/care/mine?uid=` -> `{requests:[request]}` newest first. Request = `{id, uid, language, transcript, summary_en, category, urgency, urgency_reason, stop_id, stop_name, status, assigned_to,
  escalated, created_at, acknowledged_at, resolved_at, resolution_note, has_audio, audio_url, waiting_s, status_text (in the pilgrim's language), timeline:[{t,event,by,note}], duty_officer_notified, via}`.
- `GET /api/care/open?volunteer=&stop=` -> `{requests (sorted urgency, then distance, then waiting; each has distance_stops and walk_min from that volunteer/stop), stats, volunteer, volunteer_stop}`.
- `GET /api/care/assigned?volunteer=` (name or id), `GET /api/care/roster`, `GET /api/care/{id}/audio` (the pilgrim's own words).
- `POST /api/care/{id}/ack|onway|resolve|cannot` with `{volunteer, note|reason}`. `onway` also acknowledges; if another volunteer calls it, they take the request. `cannot` re-routes to the next nearest
  (marks `escalated`) and only closes as `could_not_resolve` when nobody is left. Closed request returns 409.
- `POST /api/care/checkin {volunteer, stop, languages:[...], on_duty?}` -> `{volunteer, roster}`. `on_duty:false` checks out.
- `GET /api/care/stats` -> `{total, open, open_emergencies, by_category, by_urgency, by_stop, by_status, median_ack_s, median_resolve_s, escalated, volunteers_on_duty, simulated_roster}`.

## How it decides
- Rules first (0 ms) in six scripts plus romanised forms (e.g. `naa abbai kanipinchatledu`, `wheelchair kavali`, `neellu ledu`). 34 utterances are tested. Emergencies (fainted, not breathing, chest pain, bleeding,
  stampede, lost child) are decided by rules and the model is never called for them. The model (sarvam-105b, 8 s, JSON) is asked only when rules find nothing specific; its JSON is validated
  (category, urgency, stop id; safety categories cannot be played down to normal); any failure falls back to the rules (`via: rules_fallback`).
- Stop: explicit `stop`, else a stop named in the words (gatematch), else `position`, else `assistant.get_position(uid)`. If unknown the request is still routed (language match, least loaded) and the reply asks "Which stop are you at?".
- Routing: nearest on-duty volunteer by stops along the route (same stop, then adjacent). A volunteer who speaks the pilgrim's language wins if at most `language_slack_stops` further (0 for emergencies). Ties: language, load, walking minutes.
- Escalation: emergency 2 min, urgent 5, normal 15 to acknowledge (policy). Then next nearest not yet tried, `escalated: true`, `on_unacknowledged` fires. Emergencies notify the duty officer (timeline entry + `on_emergency`).
- Reply: "I understood X. Request number C 27. Volunteer Meera from Forest Path is coming, about 4 minutes. <one safe line>". Medical: "stay with them". Never advice beyond that; never says police or an ambulance was called (tested).

## Verified for real
- Tests: 59 pass (mocked Sarvam). Live throwaway app on port 8791 (stopped): about 8 real Sarvam calls in total (limit was 12): TTS in Telugu (lost child at Forest Path, rules, 770 KB wav) and Malayalam (father fainted at River Crossing),
  TTS English; STT round trip: the generated Telugu wav posted as audio to /api/care was transcribed back and classified medical/urgent; two chat calls on unclear text (the first showed the model sometimes breaks its JSON, now handled by validation plus an example in the prompt;
  the second returned valid JSON, which the validator accepted with urgency raised).

## Not verified / limits
- The two HTML/JS fragments are syntax-checked (`node --check`) but were NOT clicked through in a browser here; MediaRecorder, the alert tone and vibration need a phone check.
- Reply sentences and labels in Hindi, Tamil, Telugu, Kannada, Malayalam were written by me, not reviewed by a native speaker. The Malayalam "from X" avoids case endings on purpose. Romanised keyword lists are guessed spellings.
- The model over-guessed `lost_person` for a vague group request (it still lands at "urgent" and a volunteer asks what is needed).
- SIMULATED: the 7 roster volunteers (Meera, Ravi, Lakshmi, Karthik, Suresh, Anita, Joseph), the duty officer, walking minutes between stops (same constants as assistant.py), eta. A checked-in staff member is real (`simulated: false`).
- Nothing contacts police or an ambulance, and nothing is sent to NudgeBee until the integrator sets the hooks. State is one JSON file (single pod); the data volume must be writable.
- Flagsmith `care_policy` flag is not created by me; until it is read via `set_policy_source` the code defaults apply.
