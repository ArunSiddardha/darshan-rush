# Proof of one real end-to-end run (25 Nov 2026, 15:18 to 15:21 IST)

One unbroken run on our local kind cluster with the NudgeBee agent installed and NudgeBee cloud, Flagsmith cloud and Sarvam live.

1. `kubectl_watch.txt`: the real `kubectl get pods -w` lines. The rush started at 15:18:01; the pod was OOMKilled and restarted 36 seconds later.
2. NudgeBee investigated and its plain summary reached the volunteer screen 13 seconds after the crash: "The online darshan booking server crashed because it ran out of memory while handling visitor requests. To keep the system running safely right now, please switch the booking service to lite map mode and use staggered time slots."
3. The volunteer's yes (typed in Malayalam in this run) called the NudgeBee automation `darshan-staggered-approved`, which waited for an in-app approval: `nb_approval_pending.png`, then `nb_approved.png`.
4. NudgeBee's two HTTP tasks changed the Flagsmith flags: `flagsmith_before.png` (map_mode full, slot_mode open) and `flagsmith_after.png` (map_mode lite, slot_mode staggered).
5. The same rush then ran for 45 seconds: about 1,028 requests a second, 0 errors, p95 14 ms, 0 restarts.

The crowd is simulated. The crash, the investigation, the approval and the flag change are real.
