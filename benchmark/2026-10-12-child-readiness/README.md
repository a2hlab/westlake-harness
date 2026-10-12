# Bounded new-child readiness candidate

The prior guardian could reject a newly spawned child before its UID specialization completed, but the actual historical failing predicate was not captured. One diagnostic spawn passed all 24 checks and later aborted in WebView; this change is not a proven SIG11 or WebView fix.

This candidate allows at most two seconds of read-only waiting for the one newly spawned PID and initial birth, only when all non-UID identity checks pass and all four UIDs are zero. Attach remains strict. The original complete child guard must still pass after readiness. Failure records name the predicate and observed/expected values. No parent or application signals, data deletion, or historical stop changes were added.

Source: cx-t0 worktree, stable byte snapshot recorded in results.json. The outer captured that snapshot while the inner connection was retrying. BMS-authored independent assertions passed 10 tests, including identity changes during waiting, and all three Rust contract selectors passed. The root-parent/child-UID variable collision was corrected before this snapshot. Evidence is under evidence/. These are fixture checks, not board or UI acceptance.

Use compose.py with the explicitly pinned actual base plan and fresh absent-helper preimage. It preserves actual startup values and inserts the worker into both the placement plan and boot member inventory. Output stays disabled; current-boot preimages, authorization, snapshot and policy checks remain mandatory. Original 9436 and alias artifacts are unchanged.
