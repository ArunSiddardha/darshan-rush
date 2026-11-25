#!/usr/bin/env bash
# Usage: reset_demo.sh   Flags back to map_mode=full, slot_mode=open; clears app state; restarts the darshan pod; waits ready.
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"; . "$D/_common.sh"
[ "${1:-}" = "-h" ] && { sed -n '2p' "$0"; exit 0; }
"$D/flip.sh" full open
"$D/set_flag.sh" assistant_llm on || true
"$D/set_flag.sh" reply_style normal || true
"$D/set_flag.sh" venue_pack venue_demo || true
K="kubectl --context kind-$CLUSTER -n $NS"
# state lives in an emptyDir at /data; the restart below recreates the container, and we also remove the file when the pod is up
POD=$($K get pods -l app=darshan -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
[ -n "$POD" ] && $K exec "$POD" -- python3 -c "import os;[os.path.exists(p) and os.remove(p) for p in ('/data/state.json','/data/bookings.json','/data/rush_marker.json')]" 2>/dev/null || true
$K rollout restart deploy/darshan
$K rollout status deploy/darshan --timeout=120s
: > "$REPO/metrics/recovery.csv" 2>/dev/null || true
echo "Demo reset: map_mode=full, slot_mode=open, state cleared, pod restarted. Wait ~60 s for the Flagsmith cache in the app (or restart already refreshed it)."
