#!/usr/bin/env bash
# Usage: rush.sh [N_PILGRIMS=40] [SECONDS=60] [BASE_URL=http://localhost:8088]
# N concurrent pilgrims GET /api/queue and POST /api/slots/book for S seconds. Prints rps, errors, p95 (ms), pod restarts before/after.
set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd)/_common.sh"
[ "${1:-}" = "-h" ] && { sed -n '2,3p' "$0"; exit 0; }
N="${1:-40}"; S="${2:-60}"; BASE="${3:-http://localhost:8088}"
R() { kubectl --context "kind-$CLUSTER" -n "$NS" get pods -l app=darshan -o jsonpath='{.items[*].status.containerStatuses[0].restartCount}' 2>/dev/null || echo "?"; }
before=$(R)
python3 -I - "$N" "$S" "$BASE" <<'PY'
import sys, time, json, threading, urllib.request
n, secs, base = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
ok = err = 0; lat = []; lock = threading.Lock(); end = time.time() + secs
def one(i):
    global ok, err
    gate = (i % 4) + 1
    while time.time() < end:
        for req in (urllib.request.Request(f"{base}/api/queue?uid=rush{i}&lang=en"),
                    urllib.request.Request(base + "/api/slots/book", method="POST",
                        data=json.dumps({"uid": f"rush{i}", "gate": f"g{gate}"}).encode(),
                        headers={"Content-Type": "application/json"})):
            t0 = time.time()
            try:
                urllib.request.urlopen(req, timeout=10).read(); r = True
            except Exception:
                r = False; time.sleep(0.05)
            dt = (time.time() - t0) * 1000
            with lock:
                lat.append(dt)
                if r: ok += 1
                else: err += 1
ts = [threading.Thread(target=one, args=(i,)) for i in range(n)]
[t.start() for t in ts]; [t.join() for t in ts]
lat.sort(); p95 = lat[int(len(lat) * 0.95) - 1] if lat else 0
print(f"requests={ok+err} ok={ok} errors={err} rps={(ok+err)/secs:.1f} p95_ms={p95:.0f}")
PY
after=$(R)
echo "pod restarts before=$before after=$after"
