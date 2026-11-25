#!/usr/bin/env bash
# Usage: flip.sh <map_mode: full|lite> <slot_mode: open|staggered>
# Flips both Flagsmith flags with one request each (publish_immediately). Same two calls the NudgeBee workflow makes.
# Reads FLAGSMITH_ADMIN_KEY from repo/.env. Never prints it.
set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd)/_common.sh"
{ [ "${1:-}" = "-h" ] || [ $# -ne 2 ]; } && { sed -n '2,4p' "$0"; exit 0; }
case "$1" in full|lite) ;; *) echo "map_mode must be full or lite" >&2; exit 2;; esac
case "$2" in open|staggered) ;; *) echo "slot_mode must be open or staggered" >&2; exit 2;; esac
set -a; . "$REPO/.env"; set +a
ENV_ID=119864
put() { # feature_id value
  code=$(curl -sS -o /tmp/flip_resp.txt -w '%{http_code}' -X POST \
    "https://api.flagsmith.com/api/v1/environments/$ENV_ID/features/$1/versions/" \
    -H "Authorization: Api-Key $FLAGSMITH_ADMIN_KEY" -H "Content-Type: application/json" \
    -d "{\"publish_immediately\": true, \"feature_states_to_update\": [{\"feature_segment\": null, \"enabled\": true, \"feature_state_value\": {\"type\": \"unicode\", \"string_value\": \"$2\"}}]}")
  case "$code" in 2*) ;; *) echo "Flagsmith HTTP $code: $(head -c 200 /tmp/flip_resp.txt)" >&2; exit 1;; esac
}
put 303272 "$1"; echo "map_mode -> $1 (published)"
put 303273 "$2"; echo "slot_mode -> $2 (published)"
