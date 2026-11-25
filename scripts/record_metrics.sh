#!/usr/bin/env bash
# Usage: record_metrics.sh [BASE_URL=http://localhost:8088]   Polls /api/metrics-lite every second and appends to repo/metrics/recovery.csv (ts,rps,errors,p95_ms,restarts,map_mode). Ctrl-C to stop.
set -uo pipefail
. "$(cd "$(dirname "$0")" && pwd)/_common.sh"
[ "${1:-}" = "-h" ] && { sed -n '2p' "$0"; exit 0; }
BASE="${1:-http://localhost:8088}"; OUT="$REPO/metrics/recovery.csv"
mkdir -p "$REPO/metrics"
[ -s "$OUT" ] || echo "ts,rps,errors,p95_ms,restarts,map_mode" > "$OUT"
while true; do
  T=$(date +%s)
  curl -s -m 2 "$BASE/api/metrics-lite" | python3 -I -c "
import sys, json
try:
    d = json.load(sys.stdin); print(','.join(str(x) for x in ($T, d.get('rps',''), d.get('errors',''), d.get('p95_ms',''), d.get('restarts',''), d.get('map_mode',''))))
except Exception:
    print('$T,,,,,down')" >> "$OUT"
  sleep 1
done
