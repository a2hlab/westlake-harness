# U14 Stage B wiring review

The disabled port passed 16 known-answer tests on each of Mac and OrbStack. Candidate identity is 322 assertions/320 unique paths; rollback targets the signed per-board U13 321/319 maps. Variant `runner.py` configures the hook/backend for both local and VM execution. Fresh outer signatures bind board, window, package, smoke and identity. Failed crypto reports cannot be explained away; only exact unknowns can be reviewed.

Two changes are needed before enablement:

1. **P1, recovery budget:** `review_wait_u14.py` permits waiting until lock+24min, reserving six minutes. The actual r3 `before-unlock.log` birthtime to `finish.json` mtime measured 479.0s, 450.3s and 447.7s. The Stage B backend reuses this full rollback/identity/recovery-smoke/final sequence. A timeout near minute24 can exceed the strict30-minute limit. End signature waiting earlier, reserving at least10min; do not remove recovery checks. Measurements are operational filesystem timestamps, not UI verdicts.
2. **P2, pre-lock native freshness:** `promotion_hook_u14_runtime.admission()` checks summarized receipts and `u7_executor.policy_binding`, which does not bind the native-exceptions registry/checker bytes. Full executor `native_tickets` do bind them. The Stage A backend asserts these tickets; the Stage B hook bypasses its admission. Read the full receipts and assert both candidate/baseline tickets before LOCK. The production executor still recomputes native gates before writes, so this is a late-detection gap, not an observed gate bypass.

The captured old smoke specifications are already clearly marked as snapshots, not final execution specs. Before activation copy the approved r3 specs, rebind composition SHAs, and refresh all four production receipts. Keep the disabled plans disabled until Stage A's126-reference decision, schema2 coverage/explanations and separate Stage B authorization are signed. This review did not modify master code or use a board.
