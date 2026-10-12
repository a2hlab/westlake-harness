# Quiet discovery revision

The preceding helper emitted a six-field JSON denial for every unrelated PID in a full `/proc` discovery scan. Each denial invoked `od` six times. The scan runs before spawn without a total deadline; redirecting stderr does not eliminate that work. The observed new-boot guardian was in `pipe_read`, seq=0, with a ready parent and no spawn. These facts identify a plausible pre-spawn cost regression; they do not prove a child UID race or measure the device scan completion time.

The new helper makes only discovery denials quiet. `rb_owned_pids` sets `RB_AUDIT_QUIET=1` inside a subshell; `rb_deny` returns the same rejection without building JSON in that context. Target strict/readiness/signal guards retain diagnostics and every identity predicate. No signals or device operations were performed. Watchdog `423e60f7`, worker `c0326a4b`, and launch-common `d065f354` are byte-identical to the accepted predecessor. Old files remain untouched.

`evidence/tests.stderr.txt` records 10 passing tests. The real functions with captured tool-result fixtures scan 52 PIDs: 50 rejected plus two owned. Old/new PID sets are identical; discovery encoding calls change from 300 to zero. A subsequent target UID rejection still emits one JSON row using six `od` calls. The actual root-parent/readiness and rejection fixtures also pass. These are offline fixtures, not hardware acceptance.

The revised `compose.py` uses a pinned 24-member current plan and a proven PRESENT worker preimage with exact SHA/mode/uid/gid/label. It refreshes the existing worker member without adding a duplicate, preserves actual startup parameters, and emits an execution-disabled package. The old 23-member absence plan is not a valid current base. Outer must supply fresh current preimages and a new authorization; this directory grants none.

Run `python3 benchmark/2026-10-12-child-readiness/r2-quiet-scan/test_quiet_scan.py`. Check `checkpoint-manifest.json` for exact candidate and raw-log hashes. Composition CLI retains `--base`, `--base-plan`, `--base-plan-sha256`, `--worker-preimage`, `--worker-preimage-sha256`, and `--out`.
