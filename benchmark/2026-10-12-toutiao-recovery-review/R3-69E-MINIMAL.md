# R3 exact-byte minimal review

## Evidence and decision

**Offline accept** commit `69e15c4ae058d1fe17ba5f4355883e460ac9859b` for outer's fresh controlled-window composition. This is not actual startup, UI, recovery, or seal acceptance. No device, remote, VM, signal, or candidate mutation was performed.

The c30 predecessor produced a complete ready diagnostic but exited 124. Ready text cannot override the command exit. OH measured the old six-od diagnostic at 1.93/2.14/2.40 seconds and the new single-od diagnostic at 1.43/1.11/1.41 seconds. Single od remains expensive; **removing successful-path encoding**, not treating one od as free, is the essential change. Whole live-worker OH timing remains pending. A root-pending iteration still encodes and may consume much of the unchanged two-second envelope.

## Independent changed-path checks

- All 17 checkpoint SHA/size entries match exact Git objects; the manifest and landing list are archived separately. All 13 boot-member hashes, entry helper pin, startup member pin, and expected-startup hash close.
- Relative to frozen `379d1a46de0c388e105157d455916d356c11028b`, helper code outside `rb_guard_json` is byte-identical. Load-time quiet reset and discovery-only subshell quiet scope remain intact.
- Worker differs only by removal of the successful diagnostic and two explanatory comments. All context, boot, stop, lock, birth, UID, exe/SHA, PPID, namespace, and inode predicates remain. Watchdog, launch-common, and compose are byte-identical. The caller still uses timeout 2, rejects nonzero exit, then executes original complete `child_owned`; attach is not granted a wait exception.
- Three actual old/new encoder executions decode to identical six-field objects, including empty values, quotes, backslash, newline, tab, and a control byte. Old/new od counts are 6/1.
- od failure, truncated delimiter frame, and closed diagnostic descriptor are nonzero. Their exact exits are recorded; truncation is not a successful JSON event.
- The exact successful worker, replaying the previously landed captured-field fixture, exits 0 with empty stdout/stderr even when od is instrumented to fail. This proves zero successful-path encoding. This local elapsed time is explicitly **not OH budget evidence**.

Seven changed-path executions passed; no previously accepted full R1/readiness/recovery matrix was rerun. The first checker attempt could not resolve the author's untracked ancestor fixture from the t0 Git object; the second uses the immutable main `ee50b0cd6ce8892d7f527ee656ab21c866817f1f` fixture. The first raw failure is retained and is a review-input issue, not a candidate failure.

## Publication boundary

Candidate helper is `6bce7c3c8f84ad1047313c5dd76bcb084637d9095b9163dc710c88aaee12fe4c`; worker is `2d3ce1546c9df1e3a222e23f19c39f8f4aec82fb551d59f37dbe7fd343573717`. Startup remains disabled and approval pending. Outer must pin fresh actual 24-member preimages, current boot, composition, and authorization. Any whole-worker measurement must remain read-only and must not fabricate a lock/owner or alter current child/state to obtain success. Natural new-window execution remains the real acceptance boundary.

Raw independent output and results are in `evidence/r3-69e/`. The full source checkpoint archive stays in `.artifacts/r3-69e-run2/frozen/`. Current-board timing originals are in the main tree's `benchmark/2026-10-12-v1-seal-execution/r3-diagnostic-timing/`. The old c30 failure originals and old R2 receipts remain unchanged.
