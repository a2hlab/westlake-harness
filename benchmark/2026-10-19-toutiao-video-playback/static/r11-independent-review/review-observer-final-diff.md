# r11 observer final (master b3eb288a94) — 3-delta differential review

Scope: ONLY the 3 changes vs the reviewed `e9eb4a4f` version. observer.py now
`07bde2de6932c34e86215c746c7a78bfb7ea62fa641386ddd4c729854c052fe2` (verified on disk). Offline,
no device op. All prior A–D pass-logic verdicts (review-observer.md) unchanged by these deltas.

## Δ1 — `settings set target.process.disable-memory-cache true` (run, before connect)
Pure correctness gain: `read()`/`wrapper()` now read **live** memory, no stale LLDB cache for the
magic-gated object decode. **No on-device blocker.**

## Δ2 — `platform select remote-ohos` (+ `GetName()=='remote-ohos'` assert + `target_platform` emit)
- Ordered before `CreateTargetWithFileAndArch`/`ConnectRemote`; platform verified by name and
  recorded. **HW enforcement double-guarded**: `require-hardware-breakpoint true` is set before the
  target exists (so the new target inherits it) AND `add_bp` issues explicit `breakpoint set
  --hardware` then asserts `IsHardware()` at install and each hit — platform select cannot silently
  drop hardware-only.
- Memory is read by **raw absolute address** against `/proc/<child>/maps` rows (`containing()`), not
  by symbolication, so remote-ohos module auto-resolution is **not** on the critical path.
- **No new blocker.** On-device watch item (surfaces safely): if remote-ohos made `CreateTarget`/
  connect stall, it would hit the 120s deadline `Refuse`, not hang unbounded.

## Δ3 — `os._exit(2)` on unverified cleanup (entry)
- **Guard correct:** `if not result['cleanup']['verified']: os._exit(2)` — fires only when cleanup
  did NOT prove `detached ∧ breakpoints_deleted ∧ tracer_pid==0 ∧ state∉('T','t')`. On the clean
  path `entry()` returns normally (normal LLDB teardown after a confirmed `process detach
  --keep-stopped false`).
- **No evidence loss:** `run()`'s `finally` writes `result.json` (and `events.jsonl` is flushed per
  `emit`) **before** `run()` returns, i.e. before `os._exit`. stdout/stderr flushed first.
- **Purpose:** prevents LLDB's later implicit quit/teardown from running on an unknown attachment
  (which could look clean while the child's resume state is unproven). Hands recovery to outer and
  records `status=OUTER_RECOVERY_REQUIRED` + `outer_recovery_required=true` before exiting.
- **On-device consequence (handled, not a code defect):** an abrupt client disconnect without a
  completed detach may leave the child (Toutiao) stopped/traced per device lldb-server default. The
  code already signals `OUTER_RECOVERY_REQUIRED`; **outer's bounded window must verify child state
  (TracerPid==0, state∉T/t) and recover (resume / r10 apply-plan rollback / board reset) after any
  unverified run.** This is the intended fail-safe.

## Verdict
**No new on-device blocker introduced by the 3 deltas.** Δ1 improves read correctness; Δ2 is
order-correct and HW-double-guarded with reads off the symbolication path; Δ3 is a correctly-guarded,
evidence-preserving fail-safe whose only device-side effect (possible frozen child on the unverified
path) is already surfaced as `OUTER_RECOVERY_REQUIRED` for outer's window. On-device proof (HW slots,
attach, TracerPid, and the remote-ohos connect not stalling) remains the receipt's + human's call.
