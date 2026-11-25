# Rehearsal 1 (25 Nov 2026 12:39)
Local kind cluster `nb`, pod memory limit 160Mi, simulated pilgrims (in-pod load generator, 16 workers ramping up one every 3 s). HEAVY_MB=12, HEAVY_HOLD_S=1.5.

| | Before: full map, open slots | After: lite map, staggered slots |
|---|---|---|
| Duration observed | 28 s (stopped at first restart) | 70 s |
| Load requests completed (queue + book pairs) | 17 | 35364 |
| Failed requests | 0 (the pod died, so in-flight work was lost) | 0 |
| Errors (5xx seen in 10 s windows, summed) | 0 | 0 |
| p95 latency, worst | 3129 ms | 16 ms |
| Requests per second, peak | 1.7 | 1062.1 |
| Pod restarts (OOMKilled) | 1 (after 28 s of rush) | 0 |

Bookings after the run (persisted on /data, survive the restart): 800 pilgrims, busiest window 30 of cap 30.

Notes: "sent" counters live inside the pod, so the full-map figure is only what completed before the OOM kill. Raw per-second data: metrics/recovery.csv. Flags flipped with scripts/flip.sh (same request the NudgeBee workflow makes).
