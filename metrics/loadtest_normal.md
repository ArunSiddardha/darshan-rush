# Normal-traffic load test (25 Nov 2026, 15:05 IST)

Local kind cluster on one Mac, ONE replica of the app (224Mi limit), full map mode, no rush. Simulated pilgrims each poll `/api/state` and `/api/map` every 1.5 s and about a third make a booking. No Sarvam calls (voice is not load-tested). Script: `_tools/loadtest.py` (not in the repo).

| Simulated pilgrims at once | Requests/s | Errors | Median | Slowest 5% | Memory after | Restarts |
|---|---|---|---|---|---|---|
| 100 | 117 | 0 | 36 ms | 237 ms | 121 MiB | 0 |
| 400 | 405 | 0 | 199 ms | 420 ms | 148 MiB | 0 |
| 1,000 | 308 | 3 | 1.7 s | 4.3 s | 187 MiB | 0 |

Reading: comfortable to about 400 at once on one small replica; at 1,000 it stays up but is slow (the single worker is saturated). Memory does not fall back after the test (per-visitor state is kept in memory), so a long-running single replica would need restarts or shared storage. Voice turns are limited by the Sarvam rate limit (60 requests a minute on our plan), which is far below these numbers.
