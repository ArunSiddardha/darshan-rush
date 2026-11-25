#!/usr/bin/env bash
# Usage: set_flag.sh <assistant_llm|venue_pack|reply_style|care_policy> <value>
# Publishes one Flagsmith string value immediately (same call the NudgeBee HTTP task makes). Never prints the key.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
{ [ $# -ne 2 ]; } && { sed -n '2,3p' "$0"; exit 0; }
set -a; . "$REPO/.env"; set +a
ENV_ID=119864
case "$1" in assistant_llm) FID=303510;; venue_pack) FID=303511;; reply_style) FID=303512;; care_policy) FID=303528;; *) echo "unknown flag" >&2; exit 2;; esac
code=$(curl -sS -o /tmp/setflag_resp.txt -w '%{http_code}' -X POST \
  "https://api.flagsmith.com/api/v1/environments/$ENV_ID/features/$FID/versions/" \
  -H "Authorization: Api-Key $FLAGSMITH_ADMIN_KEY" -H "Content-Type: application/json" \
  -d "{\"publish_immediately\": true, \"feature_states_to_update\": [{\"feature_segment\": null, \"enabled\": true, \"feature_state_value\": {\"type\": \"unicode\", \"string_value\": \"$2\"}}]}")
case "$code" in 2*) echo "$1 -> $2 (published)";; *) echo "Flagsmith HTTP $code: $(head -c 200 /tmp/setflag_resp.txt)" >&2; exit 1;; esac
