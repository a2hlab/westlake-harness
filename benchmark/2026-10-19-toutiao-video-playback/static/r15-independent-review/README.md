# r15 typed-provider-adapter — independent review (t10; reviewer lane)

Role: **independent reviewer** of cx-seal's R15 typed provider adapter (implementation owned by
cx-seal in the t4 tree `candidate-r15-provider-offline/`). I do **not** implement or modify it, and I
do not touch R14 (`candidate-r14-offline/`, read-only). I certify that its **method** honours the t10
contract and that failure-cleanup and duplicate-identity behaviour are register/SHA-grounded and
self-consistent. No device, no deploy, no push. No OH/production binding is claimed.

## Verdict
**NO CODE BLOCKER — bounded pass.** t10 has **7 scenarios**: the **6 automated** ones
(pair / layout×2 / failures×2 / concurrency) are method-conformant on the pinned source; the **7th**
(可复现离线产物与准入边界, `审核: human`) is **PendingReview**, human-owned — I do not mark it pass.
Duplicate-identity and failure-cleanup (the two emphasised axes) are **fail-closed-correct**. The
residual items in `results.json` are *conditions/couplings*, not defects. Status stays
`OFFLINE_ADAPTER_ONLY_NOT_DEPLOYABLE`; real factory/object/provider/caller-routing + playback remain
separately unproven (out of scope here).

## Inputs reviewed (read-only, SHA-pinned — author-fixed, verified on disk)
- Contract: main tree `specs/toutiao-video-playback/t10-typed-provider-adapter.spec.md` (6 scenarios).
- Prior: main tree `static/r14-provider-next-review/README.md` (Map/Unmap/Abort ELF evidence).
- **Under review (candidate-r15-provider-offline/):**
  - `provider_adapter.c` = `5fc32ea58014a43a78d2942ccbe5e79229abef372bb612f8f14a7bfcd8b01617` ✓ (matches author pin)
  - `test_adapter.c`     = `814040519123905407b7bc4f33384815ff4e45c18cb74145b857ee1e6e51acb5` ✓ (matches author pin)
  - `provider_adapter.h`, `build.py`, `verify.py`, `run_checks.py` (read, SHAs in `sources.json`).
- **R14 (read-only, build.py R14_PINS — verified no drift):**
  - `window_module.c` = `1f42a3936449b75db6c08163c21cf68882d664065705c2d2f9afd7e2c1af4707` ✓
  - `window_module.h` = `28a88796febf5063e374fbc3d1d007a53f1004eafb24f46d6f925783724cbe32` ✓

## Run evidence (not re-run by me; outer is authoritative)
The outer loop independently full-cored the R15 raw receipts: **27 files / 1149 raw all SHA-matched**.
The host suite is **44 cases** (pair 7 / layout 16 / failures 13 / concurrency 8, per `verify.py`
COUNTS), all `PASS` on the outer's independent rebuild. Separately, the OH **compile-only** object
(ET_REL `provider_adapter.o`) is **byte-identical** to the outer's rebuild at SHA `5a3ed9e2…`.
"Byte-identical" refers to the **OH object only**, not to the 44 host cases (which are a case count,
not a byte comparison). I did **not** re-run the compile (outer directive, keep pins). My certification
is the independent method/logic trace over the pinned source + cross-check against R14's own driver;
where a property is proven only by the OH compile I attribute it to that byte-identical OH object, not
to my own run.

## What I verified (detail in the per-axis files)
- **Duplicate identity** (`duplicate-identity.md`): a lower op is dispatched only for an identity that
  is unique under the lock at dispatch. A duplicate created by a provider return value or a concurrent
  peer is detected on return (`collision()`) or at the next op (`by_identity()`→`-1`); thereafter bits
  are **not published** and no **further** lower op is dispatched for the poisoned records (cleanup
  suppressed, slots retained). An already-dispatched **in-flight** lower call **cannot be revoked** and
  completes: test_adapter.c:138 blocks window-0 *inside* the `map` provider call, so that map runs — on
  return the adapter refuses to publish its bits and R14's unmap thunk denies, and the aliasing peer's
  new ops are gate-denied.
- **Failure cleanup** (`failure-cleanup.md`): the `uncertain`-flag lever drives R14's unmap/abort
  suppression exactly; all-1s sentinel, map-error, request-contradiction all suppress lower cleanup;
  public `Abort=0` is never counted as release; failed slots are retained; only a fully-successful
  flush reclaims (`memset`). Cross-checked against R14 fail-path window_module.c:86-92.
- **Signed 24-byte handle + Region by value** (`review-adapter.md`): offset→field cross-over is
  correct, `int32→int64` sign-extends, the 24-byte bound is proven by a **guard page**
  (test_adapter.c:66-67/94); Region passed by value, `rectNumber=1`, `fence=-1`, LTRB→xywh validated
  before the provider call.
- **Tests prove the contract** (`tests-prove-contract.md`): guard page, two-layer public/internal
  journal, pthread barrier + gate are mechanical proofs, not success-only mocks.

## Protocol
Un-collected / out-of-scope ⇒ `unknown`. Human review owns real winner/object/playback. I certify
method-conformance + register/SHA self-consistency of the offline adapter only.
