#!/bin/bash
# Staged rollout of voice_agent_v2 through Flagsmith: 10 -> 50 -> 100 percent.
# After each step it watches http://localhost:8088/api/metrics-lite. If 5xx errors exceed 2% of
# requests it PAUSES and rolls back one step. Logs to repo/metrics/rollout.log.
#
#   rollout.sh [--dry-run] [--fast] [--wait SECS] [--steps "10 50 100"] [--url URL]
#              [--max-error-pct 2] [--min-requests 20] [--breach-at PCT]
#   --dry-run    no Flagsmith writes; only logs what would happen
#   --fast       demo mode: 8 s watch per step, 2 s samples
#   --breach-at  demo/test: pretend the error rate spikes at that step (logged as SIMULATED)
# Keys come from FLAGSMITH_ADMIN_KEY (sourced from repo/.env when unset). Keys are never printed.
REPO="/Users/arun/hackathon/festive/repo"
SETUP="$REPO/scripts/flagsmith_setup.py"
LOG="${ROLLOUT_LOG:-$REPO/metrics/rollout.log}"
URL="${METRICS_URL:-http://localhost:8088/api/metrics-lite}"
STEPS="10 50 100"; WAIT=60; SAMPLE=5; MAXPCT=2; MINREQ=20; DRY=0; BREACH_AT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --fast) WAIT=8; SAMPLE=2 ;;
    --wait) WAIT="$2"; shift ;;
    --steps) STEPS="$2"; shift ;;
    --url) URL="$2"; shift ;;
    --max-error-pct) MAXPCT="$2"; shift ;;
    --min-requests) MINREQ="$2"; shift ;;
    --breach-at) BREACH_AT="$2"; shift ;;
    *) echo "unknown option $1" >&2; exit 64 ;;
  esac
  shift
done
if [ -z "$FLAGSMITH_ADMIN_KEY" ] && [ -f "$REPO/.env" ]; then set -a; . "$REPO/.env"; set +a; fi
mkdir -p "$(dirname "$LOG")"
log() { echo "$(date '+%Y-%m-%dT%H:%M:%S%z') $*" | tee -a "$LOG"; }
setpct() {  # $1 = percent
  if [ "$DRY" = 1 ]; then log "DRY-RUN would set voice_agent_v2 rollout to $1%"; return 0; fi
  /usr/bin/env python3 "$SETUP" --set-rollout "$1" >/dev/null 2>&1 || { log "ERROR could not set rollout to $1% (Flagsmith call failed)"; return 1; }
}
# prints "errors total pct" from the metrics endpoint ("na" when unreachable)
sample() {
  curl -s -m 3 "$URL" | /usr/bin/env python3 -c '
import sys, json
try:
    m = json.load(sys.stdin)
    total = round(float(m.get("rps", 0)) * 10)  # metrics_lite window is 10 s
    err = int(m.get("errors", 0))
    print(err, total, round(100.0 * err / total, 2) if total else 0.0)
except Exception:
    print("na")
'
}
PREV=0
log "START voice_agent_v2 rollout steps=[$STEPS] wait=${WAIT}s max_error=${MAXPCT}% dry_run=$DRY"
for PCT in $STEPS; do
  setpct "$PCT" || exit 1
  log "STEP pct=$PCT action=set"
  END=$((SECONDS + WAIT)); WORST=0; BAD=0
  while [ $SECONDS -lt $END ]; do
    sleep "$SAMPLE"
    if [ "$BREACH_AT" = "$PCT" ]; then
      ERR=9; TOTAL=100; RATE=9.0; TAG=" (SIMULATED spike)"
    else
      S=$(sample); TAG=""
      if [ "$S" = "na" ] || [ -z "$S" ]; then log "WARN pct=$PCT metrics unreachable at $URL"; continue; fi
      set -- $S; ERR=$1; TOTAL=$2; RATE=$3
    fi
    log "WATCH pct=$PCT errors=$ERR requests=$TOTAL error_rate=${RATE}%$TAG"
    if [ "$TOTAL" -ge "$MINREQ" ] && [ "$(/usr/bin/env python3 -c "print(1 if $RATE > $MAXPCT else 0)")" = 1 ]; then BAD=1; WORST=$RATE; break; fi
  done
  if [ "$BAD" = 1 ]; then
    log "PAUSE pct=$PCT error_rate=${WORST}% is above ${MAXPCT}%: rolling back one step to ${PREV}%"
    setpct "$PREV" || exit 1
    log "ROLLBACK pct=$PREV action=rollback_one_step status=PAUSED"
    exit 2
  fi
  log "OK pct=$PCT held ${WAIT}s with error rate within ${MAXPCT}%"
  PREV=$PCT
done
log "DONE pct=$PREV rollout complete"
