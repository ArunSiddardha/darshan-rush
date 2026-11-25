# NudgeBee setup for Darshan Rush (click by click)

The two YAML files here are best-effort definitions: the Workflow Builder import format was NOT verified. If import fails, build both by hand as below (same tasks and fields). Replace the placeholders:

| Placeholder | Where to get it |
|---|---|
| `{PUBLIC_URL}` | `repo/metrics/public_url.txt` (written by `scripts/tunnel.sh`; changes each time the tunnel restarts) |
| `{INCIDENT_TOKEN}` | `INCIDENT_TOKEN` in `repo/.env` |
| `{FLAGSMITH_ADMIN_KEY}` | `FLAGSMITH_ADMIN_KEY` in `repo/.env` (paste into the NudgeBee task field only, never into git or the video) |
| `{FLAGSMITH_ENV_ID}` | `119864` (numeric id of the Flagsmith environment, project 55985) |
| `{MAP_MODE_FEATURE_ID}` | `303272` |
| `{SLOT_MODE_FEATURE_ID}` | `303273` |

## 0. Agent (once)
1. app.nudgebee.com > Admin > Integrations > Kubernetes Clusters > Add K8s Account (Non-production). Copy the agent key.
2. `scripts/nudgebee_agent.sh <agent-key>`. Wait until `kubectl --context kind-nb -n nudgebee-agent get pods` shows Running.
3. Make sure the cluster `nb` appears as connected in the console.

## 1. Workflow `darshan-rush-investigate`
1. Workflows > New. Name: `darshan-rush-investigate`. Set Automation timeout to 1200 s.
2. Trigger: Event (`event.created`). Filters: namespace = `darshan`, type = OOMKilled and CrashLoopBackOff (at least one filter is required).
3. Add task `llm.event_investigate`: account_id `{{ Inputs.event.cloud_account_id }}`, event_id `{{ Inputs.event.id }}`. Task timeout 900 s.
4. Add task `integrations.http`: method POST, URL `{PUBLIC_URL}/api/incident`, headers `Content-Type: application/json` and `X-Incident-Token: {INCIDENT_TOKEN}`. Body: JSON with `source`, `namespace` = darshan, `event_id`, `summary` (previous task `log_summary`) and `rca` (previous task `investigation`), exactly as in the YAML.
5. Save, enable. Test: `scripts/rush.sh 40 30` kills the pod (OOMKilled); the workflow should run and the app should show the incident on the volunteer page.

## 2. Workflow `darshan-staggered-approved`
1. Admin > Integrations > Webhooks > Automation Webhook > add. Create the workflow with trigger Webhook and link it (the URL only appears once linked). Copy the URL (`.../api/webhooks/workflow?token=...`) into `NUDGEBEE_APPROVE_WEBHOOK` in `repo/.env`, then run `scripts/secrets.sh` and `scripts/deploy.sh` so the app can call it. Never publish the URL.
2. Task `core.approval` (approval type in_app). Message: `Volunteer approved by voice: {{ Inputs.webhook_json.transcript }}`. The volunteer's spoken yes is recorded as the audit note; click Approve in the NudgeBee UI on camera (this is the human gate). Task and automation timeouts above 5 min.
3. Exactly two `integrations.http` tasks, in this order. Auth type API key, header name `Authorization`, value `Api-Key {FLAGSMITH_ADMIN_KEY}`, header `Content-Type: application/json`. Each is one POST (no version uuid to carry between tasks):
   - `flip_map_mode`: POST `https://api.flagsmith.com/api/v1/environments/119864/features/303272/versions/` body
     `{"publish_immediately": true, "feature_states_to_update": [{"feature_segment": null, "enabled": true, "feature_state_value": {"type": "unicode", "string_value": "lite"}}]}`
   - `flip_slot_mode`: POST `https://api.flagsmith.com/api/v1/environments/119864/features/303273/versions/` body
     the same JSON with `"string_value": "staggered"`.
4. Check: the app re-reads flags every 2 seconds, so `{PUBLIC_URL}/api/flags` shows `map_mode: lite` and `slot_mode: staggered` within a few seconds.

## Flagsmith request (verified for real, 25 Nov 2026)
```bash
curl -s -X POST "https://api.flagsmith.com/api/v1/environments/119864/features/303272/versions/" \
  -H "Authorization: Api-Key $FLAGSMITH_ADMIN_KEY" -H 'Content-Type: application/json' \
  -d '{"publish_immediately": true, "feature_states_to_update": [{"feature_segment": null, "enabled": true, "feature_state_value": {"type": "unicode", "string_value": "lite"}}]}'
```
Read-back (client key, no admin key): `curl -s -H "X-Environment-Key: $FLAGSMITH_CLIENT_KEY" https://edge.api.flagsmith.com/api/v1/flags/`.

## Manual fallback (if NudgeBee cannot do it)
`scripts/flip.sh lite staggered` does the same flips from the terminal. `scripts/reset_demo.sh` puts everything back (full, open, state cleared, pod restarted). If you use the fallback on camera, say so plainly.
