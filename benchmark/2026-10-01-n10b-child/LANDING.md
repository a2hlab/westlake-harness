# N10b landing handoff

Source worktree: `westlake-harness-u7-executor`; branch `analysis/u7-production-executor`.
Implementation/evidence commit: `4e3d9b03511c8d7a5a09a7ff79a0fff34e011816`. `landing-paths.txt` enumerates the
exact tracked delivery. Large ELF/object archives remain outside git; no board
evidence is claimed. Raw earlier failed N10/U8 runs are intentionally not listed.

Merge only the N10b additions in root README and DIGEST, preserving master
updates. The project spec change names the task-selected baseline (U8). The
new t2/t3 specs and Rust selectors belong to this delivery.

Outer ACK95 12:50:41 approves 154 exact findings only for the N10b short window.
`batch-u8-exception-proposal.json` remains the original reviewed proposal; master
should register that exact manifest/input/issue binding and the approval scope.
It must not carry over historical U7/Emboss-only proposals. Native manifest:
`342198db40765741b513a5055cf78fbb8a84cb406ca7eecfd53c853867c924f2`.
This report intentionally retains the pre-approval strict rejection receipt.
After master registration, merge master and rerun production dry-run with the
new exception registry. Set rollout-ready only after the real gate passes.

Window first gate: each child maps exactly one libart, libopenjdkjvm, bridge
and runtime. Any mismatch means immediate U8 rollback. Remaining gates: HW/ZZ
t20; six session-wall keys with no unknown sessionId and screenshots; Acrylic,
ath0-rpn, glmark2; five U8-signed controls. Wait for outer board assignment
and LOCK before I/O. No board is currently owned by cx-t0.
