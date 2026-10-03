# U14 Stage A window 2: partial sampling and safe restoration

The entire window is not complete: 61b physically disappeared from USB during AntennaPod trial 6. Its runner correctly stopped the remaining shards on rc=2, but unconditional finish returned `assigned serial detached` before rollback started. The board remains locked with its original `active_verified` journal. Do not infer U13 restoration from the two other boards.

All four fresh Mac/VM production gate runs passed before dispatch. All three candidate activation smokes passed. The same approved v5 trial order and candidate payloads were retained. Regular wrapped trials / unmeasured trials are 15/24 on 5ea, 16/26 on 5cd, and 2/44 on 61b. These are sampling counts, not UI verdicts. AntennaPod trial 6 has zero captured screenshots and unknown liveness and remains unmeasured. Exact `run_facts.py` outputs and t20 paths are provided per board.

5ea and 5cd stopped opening keys after the 35-minute cutoff. Only a fresh, owned, zero-record post-cutoff batch was interrupted to make the unchanged runner enter unconditional finish; no in-flight app capture was interrupted. Both completed finish within the 45-minute window, restored U13, passed recovery HW/ZZ smoke and parent/child verification, and released their locks. Final identity: 321 assertions, 319 unique paths, empty diff and absent lists, runtime `821de739cf81`, boot `ee927db88a67`. 5cd was released for cc-t3 A0.

61b recovery requires physical reconnect. Then first collect boot ID, uptime, and foundation/appspawn crash evidence around 13:50; retry the original rollback and recovery smoke; unlock only after the exact final identity passes. No shared HDC/VM restart or hub power operation was performed.

The Stage B P1/P2 corrections landed by cx-bms were independently re-read. P1 uses pre-lock runner birthtime plus 20 minutes, rejects a signature arriving at/after cutoff, and reserves at least 10 minutes for rollback. P2 checks full executor receipts and ownership, and applies production `assert_unchanged` to all four candidate/baseline native tickets. Mac and VM each passed 23 known-answer tests. Stage B remains disabled.

Large original evidence is preserved under `$WORKSPACES/westlake-inputs/evidence/u14-A2-20261003T131427/raw-evidence-snapshot.tar.gz`; see `archive.json` for its SHA and size. This archive deliberately records 61b as unrecovered. Raw originals were not removed. Post-window vmgr RSS was 2.02 GiB; `orb -m a2hlab true` returned rc=0 in 0.116 seconds.

UI classification remains pending the outer screenshot review. No light count is claimed here.
