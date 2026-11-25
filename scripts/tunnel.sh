#!/usr/bin/env bash
# Usage: tunnel.sh   Opens a cloudflared quick tunnel to localhost:8088 and prints the public URL (use it as PUBLIC_URL in NudgeBee).
# Install cloudflared first: brew install cloudflared
set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd)/_common.sh"
[ "${1:-}" = "-h" ] && { sed -n '2,3p' "$0"; exit 0; }
command -v cloudflared >/dev/null || { echo "cloudflared missing. Install: brew install cloudflared"; exit 1; }
LOG="/Users/arun/hackathon/festive/repo/metrics/tunnel.log"; URLF="/Users/arun/hackathon/festive/repo/metrics/public_url.txt"; : > "$LOG"
cloudflared tunnel --url http://localhost:8088 >"$LOG" 2>&1 &
PID=$!
for i in $(seq 1 30); do
  URL=$(grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -1 || true)
  [ -n "$URL" ] && break; sleep 1
done
[ -n "${URL:-}" ] || { echo "no URL yet, see $LOG"; exit 1; }
printf "%s\n" "$URL" > "$URLF"
echo "PUBLIC_URL=$URL  (cloudflared pid $PID; stop with: kill $PID)"
wait $PID
