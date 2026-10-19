# Do the R15 tests PROVE the contract? (test_adapter.c `81404051…`, 44 cases)

The question is whether the assertions are *mechanical proofs* or a success-only mock that could hide
a swallowed rc. Finding: the harness has three structural properties that make swallowing detectable.

## 1. Two-layer journal (public vs internal) — defeats rc-swallowing
The fake provider journals both `public.*` (the R14→adapter ops boundary) and `internal.*`
(simulated lower HDI: `internal.Map`, `internal.GetVirAddr`, `internal.Unmap`, `internal.CancelBuffer`)
— lines 37-56. Because `count(public.X)` and `internal.*` are independent, a test can assert e.g. the
sentinel path did `!public.unmap` **and** the normal path did `internal.Map==2` (the GetVirAddr
re-Map, matching the R14 ELF evidence) without a 3rd Map. An adapter that faked a successful Unmap to
clear a poisoned slot would raise `public.unmap`/`internal.Unmap` and fail the `!count(...)` asserts.
This directly covers "host假后端需独立两层journal区分公共调用与内部模拟行为".

## 2. Guard page — proves the 24-byte read bound mechanically
`make()` (66-67) mmaps two pages, `mprotect(PROT_NONE)` on the second, `prefix=alloc+page-24`. A read
past byte 23 faults the process. `signed32-copy-at-guard-page` (94) exercises the exact read. This is
stronger than any length assertion.

## 3. pthread barrier/gate — proves real concurrency, not interleaving-by-luck
`struct gate` + `pause_provider` (33-36) block a provider call at a chosen point; `entered()`/`release()`
(125-126) let the main thread act **while** the worker is parked inside the lower call. This yields
genuine proofs:
- `barrier-{request,map,unmap,flush}` (129-132): same window → `-EBUSY`; **same-OH alias** →
  `-EBUSY` with `!count(w10,"public.request")`; a **distinct** window proceeds concurrently
  (`!lock_w(e,1)`) — proving no global lock is held across the blocked provider call.
- `duplicate-during-map-no-publish` (138): collision created while window-0 is parked in `map`; on
  resume window-0 refuses to publish and R14's unmap denies. This is the true-concurrency proof of the
  retroactive-poison + next-op-gate (see `duplicate-identity.md`).

## Per-scenario coverage vs t10 rules
t10 has **7 scenarios**: the 6 below are automated and PASS on the outer's independent host run (44
cases). The 7th (可复现离线产物与准入边界) is `审核: human` → **PendingReview** (not mapped to a row,
not marked pass here). The OH compile-only ABI object is byte-identical at SHA `5a3ed9e2…` (OH object
only).
| t10 scenario | test group/case | proves |
|---|---|---|
| 真实类型的正常配对 | pair (7, format sweep) | one public Map, two internal Map, one unmap/flush, no abort, fence closed once, byte→pixel stride, record reclaimed (`r15_record_for==-ENOENT` after) |
| 短前缀边界与有符号字段 | layout invalid 0-8 + guard-page | int32→int64 sign-extend, no flush on illegal, no tail read |
| ABI和区域拒绝 | region 0-5 | LTRB→xywh by-value, reversed/overflow/zero rejected pre-flush |
| Map异常与清理风险 | failures kind1-3 + map-error-nonnull + request/conv | sentinel/err suppress lower Unmap/Abort; raw vs synthetic separate; failed retained |
| 二次内部Map与取消吞rc | failures (internal.Map==2; abort raw_rc==0 retained) | no extra Map/retry; Abort=0 not release |
| 并发身份和容量拒绝 | concurrency (8) | barrier/gate proofs above + 9th `-ENOSPC` no side-effect + duplicate buffer/native |

## Honest gaps (NOT blockers)
- The `receipt` scenario is `审核: human`; the OH compile-only ABI assertions are proven by the
  **outer's** byte-identical OH object, not by a run I performed.
- Some abort-count assertions are omitted for `null_handle`/`null_convert` (k=3/4, line 114 only checks
  `!public.map`); the adapter *permits* a clean abort there (gate checks `uncertain`, not `failed`),
  but the test does not pin whether R14 aborts. Behaviourally safe; just untested-by-assertion.
- Real provider/object/caller-routing and playback are out of scope and remain `unknown`.

## Verdict
The assertions are mechanical proofs of the contract on the pinned source, not a permissive mock.
