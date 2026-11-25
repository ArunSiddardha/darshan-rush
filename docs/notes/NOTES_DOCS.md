# NOTES_DOCS (documentation pass, 25 Nov 2026)

New files only: `docs/README_NEW.md`, `docs/ARCHITECTURE.md`, `docs/SCALE.md`, `docs/LIVE_VS_SIMULATED.md`, `.github/workflows/tests.yml`, this file. `README.md` and every other file untouched. No Sarvam calls made. One read-only Flagsmith edge call (flag list, no keys printed).

## Verified in code or by running
- Test count and CI: a fresh venv built only from `app/requirements.txt` (Python 3.15 here, not 3.12, because 3.12 is not installed) passed the full suite with `HTTP(S)_PROXY` pointed at a dead address, empty Sarvam and Flagsmith keys, and `STATE_FILE` set elsewhere: 354, then 355 passed (another agent is adding tests, so the README says "354 on 25 Nov, grows"). So no network and no extra packages are needed. The workflow YAML was not run on GitHub.
- Flags: read the live edge API. Present: `map_mode`, `slot_mode`, `voice_directions`, `voice_first`, `ui_copy`, `voice_agent_v2` (off, 0 percent), `assistant_llm`, `venue_pack`, `reply_style`. Also leftover cake-shop flags (`show_demo_button`, `lite_mode`, `rush_message`, `ordering_mode`), mentioned as unused. `scripts/flagsmith_setup.py` does not create `assistant_llm`, `venue_pack` or `reply_style` (they exist in the project anyway, created by hand or another script).
- Endpoints, env var names, tokens, rush mechanics, crash marker, volunteer flow, incident receiver, key pool: read from `main.py`, `config.py`, `flags.py`, `sarvam.py`, `volunteer.py`, `crash.py`, `addons_state.py`, `slots.py`, `k8s/deployment.yaml`.
- `/api/dev/flag` is guarded (`flags.dev_set` raises when Flagsmith is configured). This answers the open item in `competitors_compare.md`.
- Rehearsal numbers copied from `metrics/rehearsal1.md`.
- No em-dashes and no TODO anywhere in the new files (grep).

## Not verified
- NudgeBee: no run on the cloud is proven in the repo. YAML import format is "UNVERIFIED". Only TWO workflow files exist (`darshan-rush-investigate`, `darshan-staggered-approved`). The brief said "four automations by name": I described the other two that the code supports (crash report to `NUDGEBEE_CRASH_WEBHOOK`, assistant health guard to `NUDGEBEE_ASSISTANT_WEBHOOK`) and left their NudgeBee names as placeholders. If the lead created different automations in the console, correct that table.
- Anything another agent is still changing (assistant, kb, flags, static pages, care, staff UI): described as the code is today; the tests passing is the only check. I did not open the pages in a browser.
- Sarvam real-call claims (ms, languages, about 27 chat calls) come from the earlier notes, not from calls I made.
- Whether the assistant health guard actually flips `assistant_llm` in NudgeBee: no workflow for it exists in the repo; README says "intended".
- Tirupati (8 Jan 2025, six dead) is from `IDEAS.md` and the storyboard; `darshan_priorart.md` says it comes from IDEAS.md and is only partly sourced. The Kerala High Court line (over a lakh against 80,000) is from Onmanorama 19 to 20 Nov 2025 in `darshan_priorart.md`. Check both before publishing, or soften.
- Business numbers are copied from `business/BUSINESS.md` and labelled estimates.

## Things the lead should know (found while reading)
- `scripts/_common.sh` hard-codes `REPO=/Users/arun/hackathon/festive/repo` and many scripts use absolute paths, so the "ten commands" only work after editing one line elsewhere. README says so.
- `LICENSE` says "Dukaan Duty team" (the old cake-shop project). Fix before publishing.
- `.gitignore` excludes `_tools/`, `_old/`, `metrics/*.log`, `metrics/recovery.csv`, so some proof files linked in the README (`metrics/rollout.log`, `metrics/recovery.csv`) will not be in the public repo. Either commit them (change `.gitignore`) or remove those links.
- `metrics/shots` is ignored too.
- `competitors_compare.md` suggests moving the 13 `NOTES_*.md` into `docs/notes/`. I did not move anything.
- Volunteer reply and crowd-report endpoints have no token (stated in the README security section).
- `app/Dockerfile` has no pytest need; requirements include `pytest`, which is fine for CI.

## Placeholders the lead must fill (all capitals, in `docs/README_NEW.md` unless noted)
- `VIDEO_URL`: the 3-minute film.
- `LIVE_URL`: the public app address (the quick tunnel changes, so use a stable one if possible).
- `REPO_URL`: the GitHub repository, in the tests badge at the top.
- `NUDGEBEE_RUN_PROOF_LINK`: a recording or screenshot of a full NudgeBee run (also in `docs/LIVE_VS_SIMULATED.md`).
- `NUDGEBEE_AUTOMATION_3_NAME` and `NUDGEBEE_AUTOMATION_4_NAME`: the NudgeBee names of the crash-report and assistant-guard automations (or delete those rows if they were not built).
- `TEAM_MEMBER_1_NAME`, `TEAM_MEMBER_1_ROLE`, `TEAM_MEMBER_2_NAME`, `TEAM_MEMBER_2_ROLE`: add rows as needed.
- `TEAM_REVIEW_STATEMENT_CONFIRM`: confirm the team really reviewed the code and can explain it; replace the whole parenthesis with the truth.
- `LICENCE_HOLDER_NAME`: copyright holder for `LICENSE`.

## Swap-in steps for the lead
1. Fill the placeholders above.
2. `mv README.md docs/README_OLD.md` (or delete), then move `docs/README_NEW.md` to `README.md`. In the new file the links `LIVE_VS_SIMULATED.md`, `ARCHITECTURE.md`, `SCALE.md` are relative to `docs/`; after the move change them to `docs/...`.
3. Re-run `cd app && ../.venv/bin/python -m pytest -q tests` and update the test count line.
4. Push, and check the Actions tab turns green.
