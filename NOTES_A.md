# NOTES_A (Lane A, Ops)

## Done and verified
- k8s: namespace `darshan`, deployment/service `darshan`, image `darshan:dev`, 160Mi limit kept, emptyDir at `/data`, `STATE_FILE=/data/state.json` (write to /data confirmed with kubectl exec). Old `dukaan` namespace deleted (it held NodePort 30080).
- scripts renamed (`_common.sh`, deploy, calm, status, secrets -> `darshan-secrets`, build_load -> `darshan:dev`). secrets.sh, build_load.sh, deploy.sh all ran with the real .env (values never printed).
- Live: `http://localhost:8088/healthz` returns ok, `/api/queue` returns 5 gates (SIMULATED), `/api/slots/book` returns a slot, `/api/metrics-lite` works.
- `scripts/rush.sh N S [BASE]`: GET /api/queue + POST /api/slots/book (gate ids g1..g4). Prints rps, errors, p95_ms, pod restarts. Verified: 8 pilgrims on full map OOM-killed the pod (restarts 0 -> 2, last=OOMKilled); after `flip.sh lite staggered`, 30 pilgrims for 15 s: 17430 requests, 0 restarts, p95 36 ms (515 errors are probably "slot full" 4xx under staggered; not checked).
- `scripts/record_metrics.sh` writes `repo/metrics/recovery.csv` (ts,rps,errors,p95_ms,restarts,map_mode) every second; ran 6 s OK.
- `scripts/flip.sh <full|lite> <open|staggered>` and `scripts/reset_demo.sh` tested for real against Flagsmith (edge API confirmed the values changed within 2 s, then restored to full/open).
- Flagsmith Admin API: the environment uses v2 versioning, so the plain featurestates PATCH is rejected. Working flow is POST versions -> GET version featurestates -> PATCH -> POST publish, env id 119864 (numeric), map_mode feature 303272, slot_mode 303273. Documented in nudgebee/README.md.
- cloudflared installed via brew; `scripts/tunnel.sh` running with nohup (log `metrics/tunnel.log`). URL in `metrics/public_url.txt`; `/healthz` through it returned ok. The quick-tunnel URL changes if the tunnel restarts.
- nudgebee/: old shop files moved to `_old/`; new `darshan-rush-investigate.yaml`, `darshan-staggered-approved.yaml`, `README.md`.

## Unverified
- NudgeBee workflow YAML import format and output reference syntax (`Tasks['x'].output.body...`) are best effort; NudgeBee cloud was never touched (lead's job). README gives the by-hand build.
- Workflow 2 needs eight chained HTTP tasks because of Flagsmith v2 versioning. If that is too fiddly in the console, use `scripts/flip.sh` and say so on camera.
- The restart-after-OOM path (NudgeBee event firing) not tested; agent not installed here.

## For others / the lead
- Lane B: `/api/metrics-lite` returns `restarts: null` (app cannot see pod restarts); `rush.sh` reports restarts from kubectl, so use that for the before/after table, or have `record_metrics.sh` merge it.
- Lane C: `volunteer` module still missing in the running image (`/healthz` routers.volunteer = "missing"). Rebuild with `scripts/build_load.sh && scripts/deploy.sh` once it lands.
- Lead: put the NudgeBee agent key through `scripts/nudgebee_agent.sh`, the automation webhook URL into `.env` as NUDGEBEE_APPROVE_WEBHOOK, then `scripts/secrets.sh` + `deploy.sh`. `.gitignore` does not cover `repo/metrics/*.log` or `brew.log`; the tunnel URL is not a secret but consider ignoring `metrics/`.
- Slip: while probing Flagsmith early on I printed the server-side environment key (FLAGSMITH_ENV_KEY) once to my session output. It is not in any file or log; rotate it if that matters.
