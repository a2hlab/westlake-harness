Stage A window 3
================

Window 2 stopped after a completed foreground_unconfirmed batch returned rc=1. Master 0f83d75444 fixes that distinction: all-wrapped rc=1 continues; missing, started or batch_interrupted records stop the board. The 20 runner tests passed after merge.

Window 3 recorded 77 completed app attempts (26/26/25). The 35-minute cutoff left 60 attempts unknown (20/22/18). Each first shard remained incomplete at cutoff, so its rc=1 correctly stopped remaining shards. No candidate member was rebuilt; all plans bind armed bundle 190afedd. Exact facts are under each board directory and were posted verbatim; facts are not lighting verdicts.

Every board finished before its 45-minute deadline. U9 rollback, recovery HW/ZZ smoke and final 318 assertions passed; diff/absent are empty and held is empty. Final RUNTIME is 565fc6fdc116 for 5ea/5cd and a2919b793eb6 for 61b; BOOT is 4db882a81732 on all boards.

Outer signed window 3 in master ba7036a8ef; screenshot verdicts remain in ../window3-signoff/outer-signoff.json. TrickyTripper showed desktop with no live t20 process; outer requires two further attempts, rather than declaring a confirmed regression from one crash. Window 4 is authorized separately. No lighting count is inferred in this report.

results.json lists each measured/unmeasured key and raw shard directory. screens/<key>/t20.jpeg is the t20 evidence for outer contact sheets; restored-screens/ contains final U9 controls. portable-evidence.json binds original and normalized-copy SHA values. Large logs and all raw transaction/record evidence remain in the SHA-inventoried westlake-inputs audit directory, not git. No new tool code, board reboot or installation-service replacement occurred.
