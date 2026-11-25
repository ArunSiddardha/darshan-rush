# NOTES_FLAGS: Flagsmith additions

All new files only; no existing file was edited.

## Built
- `scripts/flagsmith_setup.py`: idempotent (re-run is safe), never prints keys. Creates segments `elders_65_plus` (age_65_plus = true), `lang_ml/ta/te/kn/hi` (language = x), `rollout_voice_agent_v2` (PERCENTAGE_SPLIT); features `voice_first` (bool, off by default, ON override for elders_65_plus), `ui_copy` (JSON remote config: banners per language, slot_window_min, slot_cap, mic examples, footer line), `voice_agent_v2` (bool, ON override for the rollout segment). Also `--set-rollout N` and `--get-rollout`.
- `app/addons_flags.py`: `router` with `GET /api/flags/decisions?uid=&lang=&age65=`, `GET /api/ui-copy?lang=`, `GET /api/rollout`.
- `scripts/rollout.sh`: 10 -> 50 -> 100, `--dry-run`, `--fast`, `--wait`, `--steps`, `--breach-at PCT` (demo of the rollback, logged as SIMULATED). Reads `/api/metrics-lite` (errors / (rps*10) in its 10 s window), needs >= 20 requests (`--min-requests`) before judging. Above 2 percent: logs PAUSE, rolls back one step, exits 2. Log: `metrics/rollout.log`.
- `app/tests/test_addons_flags.py` (6 tests, Flagsmith mocked): pass.
- `app/addons_ui/flags_panel.html/.js` ("Flagsmith decides": flag, value, why) and `ab_card.html/.js` (reads `/api/experiment`, exposed / reached / rate per variant, "test traffic" badge). Plain CSS variables with fallbacks, one namespaced global `DarshanAddons`.

## Verified for real
- Setup ran against project 55985 / env 119864. Edge API check: identity with age_65_plus=true gets `voice_first` enabled, one with false does not; `ui_copy` is served. Setup script exits 1 if this check fails.
- Percentage split: at 50 percent, 26 of 60 test identities got `voice_agent_v2` on via the edge API.
- rollout.sh real runs against Flagsmith: (a) `--breach-at 50`: set 10, set 50, spike, PAUSE, rolled back to 10, exit 2; (b) healthy `--fast` run 10, 50, 100 with real metrics from the cluster (localhost:8088), exit 0. Then set back to 0 percent (confirmed with `--get-rollout` = 0).
- Router live on a throwaway app (port 18931, `_tools/flags_addon_app.py`, stopped by PID): decisions showed voice_first ON by segment elders_65_plus for an elder, default for others, voice_directions as variant; ui-copy came from Flagsmith (source "flagsmith"); rollout read 0 percent from Flagsmith.

## Gotchas found
- Segment create API rejects a blank property on PERCENTAGE_SPLIT; a non-blank property makes the engine hash that trait (so nobody matched). The script creates with "x" then PATCHes property to null. Do not hand-edit that rule with a property.
- v2 versioning: overrides are created by POST `/versions/` with `feature_states_to_create` and a non-null `feature_state_value` even for boolean flags.
- Edge changes show within a few seconds.

## Integration
1. In `main.py`: `from addons_flags import router as addons_flags_router` then `app.include_router(addons_flags_router)` (or `_mount("addons_flags")`).
2. Env in the pod/app: `FLAGSMITH_CLIENT_KEY` (or the existing `FLAGSMITH_ENV_KEY`) for decisions and ui-copy; `FLAGSMITH_ADMIN_KEY` only if `/api/rollout` should read the live percentage from Flagsmith (otherwise it falls back to the last `pct=` in the log). Optional: `ROLLOUT_LOG`. Admin key in the pod is a security choice: skip it and the log fallback works.
3. UI: paste `addons_ui/flags_panel.html` and `ab_card.html` where wanted (judge or ops view), and add `<script src="/static/addons_ui/flags_panel.js">` and `ab_card.js` (copy or mount the folder). To make the panel follow the language picker: `el.dispatchEvent(new CustomEvent('flags:refresh',{detail:{lang:'ml',age65:true}}))`.
4. Use `/api/ui-copy?lang=` in the frontend for the banner, mic examples, slot window and cap.
5. Demo: `scripts/rollout.sh --fast` (healthy), `--fast --breach-at 50` (rollback). Reset: `python3 scripts/flagsmith_setup.py --set-rollout 0`.

## Unverified / notes
- Language segments exist but no flag has a language override yet (voice_first is the only segment-driven flag; ui_copy picks language in the app). Add language overrides in the dashboard if wanted.
- The "why" column infers the reason by comparing the visitor value with the environment default plus a fixed flag-to-segment map; the edge API does not return segment names.
- Identities created by decisions calls persist their traits in Flagsmith (test ids like `live1`, `setup-check-*`, `u0..u59` exist).
- Rollout detection needs >= 20 requests in the 10 s window, so a quiet system never trips it. Error rate from a real OOM crash would show as metrics unreachable (WARN), not a breach.
- UI fragments were syntax-checked (`node --check`) but not rendered in a browser.
- `metrics/_rollout_dryrun.log` holds the earlier dry-run output; ignore it.
