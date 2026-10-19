# candidate-r14-offline — independent review (t9; reviewer lane)

Independent review of CX's offline window lock/unlock module + tests + build/receipt closure in t4
`candidate-r14-offline/`. Offline, no device call, no modification of CX files. Verdict: **NO
blocker** — contract-faithful, defensively correct, rigorous test/build/receipt closure.

## Reviewed files (SHA-256, stable across the review)
| file | sha256 |
|---|---|
| window_module.h | `28a88796febf5063e374fbc3d1d007a53f1004eafb24f46d6f925783724cbe32` |
| window_module.c | `1f42a3936449b75db6c08163c21cf68882d664065705c2d2f9afd7e2c1af4707` |
| test_window.c | `bc442a4a7ea8648264e223b29cbcada4156b682e9ecef726d6501ab77fc6fb6b` |
| build_host.py | `747493a5299fb596642920652d071e7d8525ced9c07fee902fd44cd4222503f7` |
| check_receipt.py | `0a3ba0249c9c827eace6631dffa36439625a572b546324f4af82b58cf07cccef` |
| run_checks.py | `95f73f34919afe2d7e0829a5ef21f200ba55e23026086ec682c90bec261f3832` |
| DONOR.md | `a7e62ab2320b8d693ec72c53390274f43124c4357fe50602c6ddf46a89ae91b1` |

## window_module.h/.c — contract-faithful, defensively correct
- ops fully injected (no dlsym/resolver); wrapper never dereferenced; `unwrap`-NULL → `-ENODEV`, no
  slot, no raw cast. Status `OFFLINE_MODULE_ONLY_NOT_DEPLOYABLE`; `r14_destroy` → `-EBUSY` if any
  reservation (no force-drop).
- **8-slot alias serialization = reservation-held-while-mutex-released**: slot set `CLAIMED` (oh/
  wrapper) and mutex released (`.c:69`) BEFORE the blocking provider calls; mutable fields + `LOCKED`
  committed under mutex at `.c:84`; a concurrent same-OH lock scan (`oh==` or `wrapper==`) → `-EBUSY`;
  `COMPLETING`/`FAILED` also block. (This is the hardest EDGE-CONTRACT point — implemented correctly.)
- fence single monotonic total deadline (`R14_FENCE_MS=3000`): EINTR/EAGAIN retries non-extending,
  POLLIN-only (ERR/NVAL/HUP → `-EIO`, even POLLIN+HUP), fd closed exactly once, `-1` no-close,
  `fd<-1` → `-EINVAL`. `request` owns the returned fence even on error (closed).
- Map/Unmap paired on actual Map success; `bits` only from `map()` success → **NO virAddr fallback**;
  stride unit/divisibility/≥width + size/overflow validated; **div-by-zero averted** by `!fmt`
  short-circuit before `%bytes` (and `height<=0` before `/height`).
- flush-failure retention: slot freed ONLY on unmap-ok ∧ flush-ok; on Unmap-fail → no abort (ownership
  unknown, retained `FAILED`); no double cancel/flush; no Abort-rc0=released assumption.

## test_window.c — exhaustive, real concurrency (49 cases: pair 7 / failures 34 / concurrency 8)
- **Real 2-party barrier** (pthread mutex/cond, generation-based, macOS-safe; no sleeps/fake
  scheduler) + independent event **journal** + an **overlap detector** (`enter/leave` asserts
  `active[id]==1`; `finish` asserts `!overlap`).
- **Reservation-held-while-mutex-released proof** (`concurrency`): a worker is parked INSIDE a provider
  (`block_event` at request/map/unmap/flush) holding the slot; the test then asserts `lockw(10)` —
  which unwraps to the **same OH** as window 0 — returns `-EBUSY`, `unlock` of both wrappers `-EBUSY`,
  while a **different** window (`lockw(1)`) proceeds; worker resumes rc=0; exactly one call per stage.
- **fence total-deadline proof**: 3× EINTR/EAGAIN each elapsing 1s → `-ETIMEDOUT`, asserting each
  poll's `ms` == `3000 − 1000·i` (3000→2000→1000, deadline not extended), `close_called==1`, no map.
- **failure ownership**: unmap/flush failure → `retained`, no abort, re-lock/unlock `-EBUSY`,
  `report_for` matches, `destroy → -EBUSY`; 8-slot quarantine + release-reuse; untrusted wrapper →
  `-ENODEV` with zero journal (never dereferenced); map-error-with-nonnull-bits is not success.
- Fail-closed note honored: each failure case uses a **fresh module** (`init`), consistent with the
  permanent-`FAILED` retention design.

## build_host.py / check_receipt.py / run_checks.py — source-lock + receipt closure
- `build_host`: `check_frozen` first; persistent OUT required (rejects /tmp); **no shared library** —
  only `window_module.o` (static object) + `test_window` exe (`role: host-only-not-deployable`);
  records source/header-dependency/tool SHAs + raw command.json/stdout/stderr/rc; strict
  `-Wall -Wextra -Werror -pedantic -pthread`.
- `check_receipt`: rigorous closure — status `OFFLINE_MODULE_ONLY_NOT_DEPLOYABLE`+complete,
  device_calls 0, shared_library/production_binding False; source/header/tool/artifact SHA match; exact
  command sequence; each rc 0 + raw-file SHA + `.rc=='0\n'`; **exact case counts pair 7 / failures 34 /
  concurrency 8**, unique names, all PASS.
- `run_checks`: unique persistent output; and for `receipt`, **6 negative tampering tests** proving the
  verifier REJECTS `status=DEPLOYABLE`, source drift, command rc tamper, case-count tamper, artifact
  SHA tamper, and `production_binding=True`.

## Verdict + boundary (unchanged)
**NO blocker.** The module, tests, build and receipt fully honor t9 + EDGE-CONTRACT; the source-lock/
receipt closure is complete and tamper-tested. Status remains `OFFLINE_MODULE_ONLY_NOT_DEPLOYABLE`:
**deployment is NOT authorized by this** — it still requires R13 positive object + exact provider/
namespace/instance binding + provider ABI + caller-scoped lock/unlock routing + build-ABI gate +
time-boxed window, none of which this module provides.
Non-blocking carry-over: the `format()` donor code→bytes map (DONOR.md `a7e62ab2…`) is self-tested
against the suite's own expectations; a cross-check vs the real Android format enum remains a DONOR.md
item, not a blocker.
