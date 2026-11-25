# INFRA notes

## Run and verified (25 Nov 2026)
- `scripts/cluster_up.sh`: kind cluster `nb` (1 control-plane + 2 workers) created; host 8088 -> NodePort 30080 works.
- Placeholder app image built and loaded first (manifests fine), then real app (`app/main.py` present by then) via `scripts/build_load.sh`, `scripts/deploy.sh` with a dummy secret (`INCIDENT_TOKEN`, `HEAVY_MB`; no real keys).
- `GET localhost:8088/healthz` -> 200, `/api/products` returns products.
- `scripts/rush.sh 10 8`: all 3552 requests errored and restarts went 0 -> 2, `status.sh` showed `last=OOMKilled`. So the rush reliably OOMKills the 160Mi pod (the intended incident). Use a gentler rush (e.g. `rush.sh 5 20`) if you want some orders to succeed first, and note recovery takes about 20-40 s (CrashLoop backoff).
- Bash syntax of all scripts checked with `bash -n`.

## Unverified
- `nudgebee_agent.sh`, `tunnel.sh` (cloudflared not tested), `calm.sh`, `secrets.sh` against a real .env.
- NudgeBee workflow YAML import format is a guess; use `nudgebee/README.md` click path as the fallback. `core.approval` pre-approval by voice, and the Flagsmith Admin API featurestates paths, are unverified (see flagsmith.md note).
- README "our feedback" cells are TODO.
- Cluster `nb` is left running with the shop deployed (dummy secret): rerun `scripts/secrets.sh` with the real `.env` then `scripts/deploy.sh`.
- App image runs as uid 10001; the Dockerfile expects `app/requirements.txt` (exists).
