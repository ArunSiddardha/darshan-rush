import json, os, subprocess, sys, time, urllib.request
B = "http://localhost:8088"; TOK = os.environ["RUSH_TOKEN"]; REPO = "/Users/arun/hackathon/festive/repo"
KC = ["/opt/homebrew/bin/kubectl", "--context", "kind-nb", "-n", "darshan"]
def get(p):
    try: return json.load(urllib.request.urlopen(B + p, timeout=3))
    except Exception: return None
def post(p):
    r = urllib.request.Request(B + p, method="POST", headers={"X-Rush-Token": TOK}); return json.load(urllib.request.urlopen(r, timeout=10))
def restarts():
    o = subprocess.run(KC + ["get", "pods", "-l", "app=darshan", "-o", "jsonpath={.items[0].status.containerStatuses[0].restartCount}"], capture_output=True, text=True).stdout
    return int(o or 0)
def phase(name, maxs, stop_on_restart):
    rows, r0, t0, sent, failed = [], restarts(), time.time(), 0, 0
    ttk = None
    while time.time() - t0 < maxs:
        time.sleep(1)
        m = get("/api/metrics-lite"); st = get("/api/rush/status")
        if m: rows.append(m)
        if st: sent, failed = st["sent"], st["failed"]
        if stop_on_restart and restarts() > r0: ttk = time.time() - t0; break
    return dict(name=name, rows=rows, restarts=restarts() - r0, sent=sent, failed=failed, secs=time.time() - t0, ttk=ttk)
def summ(ph):
    r = ph["rows"]
    return dict(rps_peak=max([x["rps"] for x in r] or [0]), rps_mean=sum(x["rps"] for x in r) / max(1, len(r)),
                p95_max=max([x["p95_ms"] for x in r] or [0]), p95_last=(r[-1]["p95_ms"] if r else 0),
                err=sum(x["errors"] for x in r), **{k: ph[k] for k in ("restarts", "sent", "failed", "secs", "ttk")})
rec = subprocess.Popen([REPO + "/scripts/record_metrics.sh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    print("flags", get("/api/flags")); print("rush full:", post("/api/rush/start"))
    a = phase("full map, open slots", 90, True)
    flip = subprocess.run([REPO + "/scripts/flip.sh", "lite", "staggered"], capture_output=True, text=True); print(flip.stdout.strip())
    time.sleep(4)
    # pod restarted, wait until healthy
    for _ in range(40):
        if get("/healthz"): break
        time.sleep(1)
    print("flags after flip", get("/api/flags")); print("rush lite:", post("/api/rush/start"))
    b = phase("lite map, staggered slots", 70, False)
    bk = get("/api/slots") or {}
    post("/api/rush/stop")
finally:
    rec.terminate()
A, Bs = summ(a), summ(b)
f = lambda s, k, fmt="{:.0f}": fmt.format(s[k])
md = f"""# Rehearsal 1 ({time.strftime('%d %b %Y %H:%M')})
Local kind cluster `nb`, pod memory limit 160Mi, simulated pilgrims (in-pod load generator, 16 workers ramping up one every 3 s). HEAVY_MB=12, HEAVY_HOLD_S=1.5.

| | Before: full map, open slots | After: lite map, staggered slots |
|---|---|---|
| Duration observed | {f(A,'secs')} s (stopped at first restart) | {f(Bs,'secs')} s |
| Load requests completed (queue + book pairs) | {A['sent']} | {Bs['sent']} |
| Failed requests | {A['failed']} (the pod died, so in-flight work was lost) | {Bs['failed']} |
| Errors (5xx seen in 10 s windows, summed) | {A['err']} | {Bs['err']} |
| p95 latency, worst | {f(A,'p95_max')} ms | {f(Bs,'p95_max')} ms |
| Requests per second, peak | {f(A,'rps_peak','{:.1f}')} | {f(Bs,'rps_peak','{:.1f}')} |
| Pod restarts (OOMKilled) | {A['restarts']} (after {f(A,'ttk','{:.0f}') if A['ttk'] else 'n/a'} s of rush) | {Bs['restarts']} |

Bookings after the run (persisted on /data, survive the restart): {bk.get('total')} pilgrims, busiest window {bk.get('peak_window')} of cap {bk.get('cap')}.

Notes: "sent" counters live inside the pod, so the full-map figure is only what completed before the OOM kill. Raw per-second data: metrics/recovery.csv. Flags flipped with scripts/flip.sh (same request the NudgeBee workflow makes).
"""
open(REPO + "/metrics/rehearsal1.md", "w").write(md); print(md)
