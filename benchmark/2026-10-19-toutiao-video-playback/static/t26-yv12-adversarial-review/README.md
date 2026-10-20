# T26 YV12 scratch/RGBX — adversarial review (implementation BLOCKERS only)

Read-only review of `westlake-harness-t4/specs/toutiao-video-playback/t26-yv12-presentation.spec.md`
(parse 0 / lint 88 %, 9 scenarios) + `benchmark/2026-10-20-t26-yv12/BLUEPRINT.md` + the observation blueprint.
Design-only packet; no implement/build/device. No REA (by CC). BLOCKERS below are gaps that break the build if
unresolved; covered areas are marked COVERED. No style notes.

## 1. Independent derived wiring
- **BLOCKER W1 — seam must sit on the player-bound SHIM lock path, not a bypassed libandroid R14.** The player
  binds the *shim's* `ANativeWindow_lock`/`unlockAndPost` (proven: WL-R20 markers win over libandroid-765). The
  blueprint places `prepare_output`/`before_unmap` in a "derived R14 glue copy" (`window_module.c:82–84`). If
  that derived R14 is not the TU the shim's lock actually delegates to, the scratch seam never executes. Pin: the
  two seams run inside the same shim lock/unlock the player reaches (the R20 path), reusing the three slots
  `0x472490/0x472760/0x472048`. (The three-slot + mixed-765 refuse is otherwise COVERED.)

## 2. Cache reference / eviction
- **BLOCKER C1 — "active cannot evict" must be atomic with owner-ref release.** The concurrency scenario
  interleaves idle-evict / active-evict / quiescent-destroy / double-unlock under a pthread barrier. Unless the
  active-transaction check and the cache-entry owner-ref release are under one lock spanning both, an idle
  eviction can race an incoming lock and release the trusted-owner reference the lock is about to use (TOCTOU) →
  use-after-release of the OH window. Same-OH overlap *refuse* and "release exactly once / FAILED-retained" are
  COVERED; the **atomicity of the active-vs-evict decision** is the gap to pin.

## 3. Geometry failure state
- COVERED (failed call keeps prior request; format0 preserves; evicted→must re-geometry; unknown-history lock
  refuses). **One edge to pin (B-minor):** a refused lock for evicted/unknown history returns an error to the
  player *mid-draw* — it must return the **same error code the player already tolerates for a failed lock**, not
  a novel failure, or the cure trades the format gap for a lock-refuse crash/hang. (Downstream player behavior is
  out of T26 scope but the chosen return value is in scope.)

## 4. Original RGB regression
- **BLOCKER R1 — byte-identical must be proven THROUGH the new glue copy, not by "original file untouched".**
  Once the derived glue copy is on the shim lock path (W1), *every* app's RGB lock traverses T26's copy, not the
  original TU. So the `{1,2,3,4,5,22,43}` regression must be byte-identical **through the derived copy** (bits/
  stride/format/rc + operation journal + zero scratch), including the **no-recorded-request** RGB case (wrapper
  that never hit T26 geometry). The regression scenario lists recorded formats; add the unrecorded-wrapper RGB
  pass-through as an explicit case. Export tuple/symbol-version/NEEDED/hidden-helper + T25 byte-identical relink
  are COVERED as obligations.

## 5. Scratch overflow / odd stride
- **BLOCKER S1 (sharpest correctness) — the YV12 scratch strides handed to the player must match the player's own
  YV12 plane-offset assumption.** The scratch is the buffer the *player writes decoded YV12 into*; if the player
  computes Y/V/U offsets with a stride different from `YS=align_up(W,16)` / `CS=align_up(ceil(W/2),16)`, it writes
  chroma to offsets the converter does not read → **silently wrong colors, not a clean failure**. The spec pins
  the donor formula but does **not** pin the *player's* expected YV12 stride from evidence. Pin that stride (from
  exact-player evidence) and prove scratch strides equal it, before trusting the conversion. Overflow/budget/
  checked-arithmetic/odd-dims (1×1,3×5,17×3) + dest stride (÷4, ≥4W, padding preserved) are COVERED.

## 6. Failure cleanup
- **BLOCKER F1 — mid-conversion failure has no defined outcome.** Failure scenarios cover allocator/map/Unmap/
  Flush/owner-release, but **not a failure during the YV12→RGBX conversion itself** (checked-arithmetic trip or
  dest-validation fail *after* the player filled scratch, *before* Unmap). It must **not** Flush/publish a
  partially-converted dest: define it as FAILED-retained, no publish, original cleanup order, dest not left
  half-written-and-flushed. Fence/request/map/unmap/flush/abort retention + separate cache-vs-pair ref counting +
  no-retry + convert-then-Unmap/Flush-once are COVERED.

## Observation blueprint
- COVERED and well-guarded (GetConfig no-rc, usage_low32 only, no `eglGetError` consume, no `dlopen`/NOLOAD, no
  raw +0x18, resolve only via retained T20/R23 handles, errno preserved). No blocker.

## Net
Six areas: **W1, C1, R1, S1, F1** are implementation blockers to resolve before build authorization; geometry-
failure + observation are COVERED (one minor return-value pin). S1 (player YV12 stride contract) and W1 (seam on
the real shim path) are the two that most directly decide whether the fix works at all. No implement/build/device
until outer admits the draft. CC did not call REA.

## Scope
Read-only on delivered T26 spec/blueprint/observation. No REA (by CC), no board/build/push.
