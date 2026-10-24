# Complete historical recovery evidence and ordinary baseline reopening

The earlier 4 MiB prefix omitted the recovery events. The complete **28,216,090-byte / 263,375-line** PID7013 log contains two successful session-publication markers, both beyond that prefix. Separately, the ordinary baseline window's combined verification boolean was false because its image-review consumption ended before the late feed review; it is **not evidence that no feed appeared**. Original run files remain unchanged.

The private full file is `../.private/7013-full-log-01/7013.stderr`, SHA `9940ebdcb209b1c63361064fc6e91e2d293ff65ec4ff049cbd130bafa8ab14b2`. Before/after stat and whole-file SHA agree; all three collection commands returned local rc0, metadata shell commands also explicit remote rc0. A verified durable copy, receipts, source excerpts' complete source files and historical mapping receipts are indexed in `backup.json` under `$HOME/.local/share/westlake/t136-7013-full-log-20261025/collection-01`. Full logs and UI images remain private.

Safe exact excerpts (full-file line numbers):

```text
257406: [WESTLAKE-STAGE] SetActive
257407: [HOST-SESSION] logical=29 outcome=6
257432: [WESTLAKE-STAGE] SetActive
257433: [HOST-SESSION] logical=30 outcome=6
257436: [FOCUS34] RequestFocus session=30 window=39 scene=1 ipc=0 rc=0
257444: [WESTLAKE-STAGE] UpdateRect
257445: [WESTLAKE-STAGE] UpdateRect
257446: [WESTLAKE-STAGE] UpdateFocus
```

`session-recovery/candidate/session_recovery.h:88` defines outcome6 as `Committed` (SHA `cc1a2b3ccae8f2810a5ee8c8b68fde50d8ef03927b43c9ded83f1f8839f3ce1f`). `session_recovery.cpp:58–61` returns it only after successful publication; `wmc_recovery_impl.inc:168` emits the marker. All three source SHAs match `candidate-build-02/results.json`, linked candidate `3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819`. Historical 43e2a3 firstopen/recreated binding receipts retain child7013/birth12014 under boot23b9968b, actual mapped candidate dev66352/inode574477, and host change4981→10685. This supports actual recovery publication, not just visible retained content. It does not supply the missing recreated touch verification or complete t3 acceptance.

The full log contains **0 literal NotifyDestroy matches**; absence of this text does not prove that no call occurred. The file was collected in later boot70b5dc15. File metadata, embedded historical PID/time and historical mapping evidence correlate it with the old run; it is not a live current-boot7013 observation. The two marker lines have no wall-clock timestamp, so no exact03:04 commit time is assigned.

In the separate baseline run `execute-20261025-040803-e6f12a`, the one icon command ran04:09:05.322–05.707. `0099-ordinary-presence-98` first observed child25535/b90062 at04:09:35.439–35.583, after a preceding no-child sample. Host5218/b12629 remained. s40 was externally reviewed white; s60 was captured04:10:07.004–07.460 and externally reviewed feed, as was final. These are sampled bounds, not exact startup/feed onset. The original combined boolean remains false; **visible feed is confirmed, swipe/content interaction is not verified in this run**. Power returned30000/10000 and the lock was released. CC owns the separate follow-up touch window; its result is not imported here.

Run `python3 benchmark/2026-10-24-native-host-window-recovery/device-validation/t136/ordinary-evidence-01/check_evidence.py` to reproduce source/hash/binding/line checks offline. `facts.txt` is dynamically counted; `raw-index.json` pins the private evidence. No new native change, deployment, UI action, API freeze or seal is claimed by this report.
