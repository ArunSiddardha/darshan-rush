#!/usr/bin/env bash
# Usage: rehearsal.sh   Full run: reset, record metrics, rush on full map until the pod restarts, flip lite+staggered, rush again. Writes metrics/rehearsal1.md.
set -uo pipefail
D="$(cd "$(dirname "$0")" && pwd)"; . "$D/_common.sh"
set -a; . "$REPO/.env"; set +a
"$D/reset_demo.sh" >/dev/null 2>&1; sleep 5
exec python3 -I "$D/rehearsal.py"
