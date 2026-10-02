# U13 Stage A window3: restoration binds the dispatched gate bytes

The 5cd runner initially refused restoration because the outer reviewer appended unrelated U14 exceptions during the active window. The gate binding correctly detected the registry SHA change and refused before rollback device I/O. The outer reviewer reverted those bytes. The unchanged finish command then passed its original binding; no assertion or exception was bypassed. The first `before_unlock=1` result remains intact alongside the successful manual retry.

The same approved per-board U13 packages were used: 5ea/5cd armed `2abe4a49` on `190afedd`, and 61b armed `0a31ad35` on effective base `c0adc4a9`. Manifest `85aef68e` and inputs `c40faa79` are common. Actual Mac and fresh-VM production runs all passed, with N1 55 and N2 104 excepted, zero rejected. Activation smoke passed on all boards and checked 321 identities over 319 unique paths. No installation service changed.

At the 35-minute cutoff, finished observations were 21/19/24 on 5ea/5cd/61b. Planned observations were 27/19/47; 6/0/23 remained unattempted. Two 5ea attempts had no t20 because desktop icon lookup failed: Minesweeper and Frequent-habits. They are explicitly separate in coverage.json and cannot count as screenshot-comparable evidence. No auxiliary long waits were repeated. Outer signoff a5d9180e99 classifies the 64 attempts and the Minesweeper launcher failure; this delivery makes no independent lit count.

Selftest schema2 found zero selftest_error, badtag, or probe_error on every board. Unknown processes are 2/4/0 and remain unknown. Empty cutoff groups retain their zero-record reports rather than inventing PASS observations. Per-shard details are in selftest-summary.json.

All boards were restored to true U10.1T8, including 318 assertions over 316 unique paths, empty diff/absent, parent/child views, recovery HelloWorld/ZigZag smoke, and final verification. Finish completed 42.98/42.63/43.98 minutes after lock. All held checks are empty. Runtime fingerprints are f3b604c94df4 on 5ea/5cd and d6848fa2c989 on 61b; boot is e3806b65a079 on every board. The signed installation-service difference remains unchanged.

Pre-lock gate work required a preventive OrbStack restart and a fresh VM gate run; no restart occurred under board locks. Final pre-lock RSS was 2,361,584 KiB with orb latency 0.110 s. After-window RSS was 2,240,304 KiB with orb latency 0.105 s. Receipts preserve the complete pre-lock sequence, including the failed initial bind attempt and the successful explicit mount.

Verbatim run_facts outputs are in evidence/facts and were posted on the board. Exact screenshots and normalized records are in evidence/{5ea,5cd,61b}; sheets/*-t20.jpeg include candidate and restored controls, with matching order files. Public text normalization changes only machine paths; public-evidence-index.json links it to raw SHA values. The raw archive is `$WORKSPACES/westlake-inputs/generations/u13-stageA-window3-20261003`: 125,893 files, 772,205,015 bytes, 168 inventory chunks. It retains the failed finish, successful retry, full logs and diagnostics. No raw evidence was discarded.

Offline validation: `python3 -m unittest benchmark/2026-10-03-u13-stage-a-plan/window3/test_window3.py` (1 test, OK). This report authorizes no board action; window4 follows its separate outer dispatch.
