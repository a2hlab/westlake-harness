# T30 resource-free Request failure recovery — DESIGN SUMMARY + file boundary (for peer review)

Read-only analysis + offline design. **No REA, no HDC, no device, no build, no deploy.** Code lands only
in my isolated analysis tree under `benchmark/2026-10-20-t30-request-recovery/**` + the T30 selector; I do
**not** touch frozen files, T29/T26 originals, or main. The spec selector is a **pending, not-yet-tested
obligation** — it is NOT reported as passed. This doc is the **design review** requested before I implement
the source/tests; if the directory needs to change, I will ask the outer loop.

## 1. Evidence alignment (actual, SHA-pinned log)
BASE `$HOME/.local/share/westlake/toutiao-resume-20261020/t29-5cd-window-01`,
`candidate-log-7635-r29/selected.raw` (33,093,780 B, sha256 `7254a067…`, 343,241 lines; main candidate
bridge `b0e5602a` / shim `9f3cecde`). First video OK (640×360 YV12, subtitles dynamic); this round also
covered **RGBX 720×1280 fmt2 → outfmt2 flush0** and early YV12 640×360 success (RGBX IS reached — prior
"RGBX untouched" wording is retired). After fullscreen: 4 frames identical for ~20 s; after Back: still the
same frame.

Consumer transition (key=2 SurfaceTexture identity, same OH **address** `7eef2e2790`, 1.5 ms apart):
- `L180081` `side=consumer p=4 ns=250797426 oldw=7eef2e2790 neww=0 unref=1/1/0` — old window destroy (unref ok rc0)
- `L180084` `side=consumer p=4 ns=250798885 key=4294967295 wrap=0 called=0` — nested no-window destroy (invalid lane)
- `L180085` `side=consumer p=3 ns=250798932 oldw=0 neww=7eef2e2790 ref=1/1/0` — re-create on the **same address** (ref ok rc0)

Producer poisoning 3.106 s later (wrapper `7dadc6f3d0`, oh `7eef2e2790`):
- `L185695` `cpu p=3 Q=1/1/40601000 buf=0 native=0 bits=0 H=0/0/0 N=0/0/0 M=0/0/0 fence=0/0/0 close=0/0/0
  U=0/0/0 F=0/0/0 B=0/0/0 retained=1 A=0/0/0 rc=-5 stage=37 errno=9` — **first Request fails; nothing
  acquired; yet `retained=1`.** ← the poisoning record.
- `L185697` `cpu p=3 A=1/1/1 B=0/0/0 retained=1 rc=-5 stage=15` — this is the pair's record (self=`pair_observe`):
  `A` = **owner acquire** = 1/1/1 (success); `B` = abort = 0/0/0 (Abort NOT called). So the owner ref WAS
  acquired, yet `report.retained=1` keeps the pair from releasing it (see §4).
- `L185699` `cpu p=0 CACHE raw=-16 rc=-16 stage=32 retained=0 errno=5`; `L185701` `… rc=-16 stage=32 errno=16`
  — subsequent cache lookups on the same wrapper/OH return **-16 (EBUSY)**; player logs `drawPicture …
  Unable to lock window buffer ret:-5` then `ret:-16`; frames freeze.

**Poisoning chain (exact, from the pinned source):**
`window_module.c` `complete()` (L35-40) on the fail arg does `r->retained=1; slot.state=FAILED`
*unconditionally*. The fail path (L106-116) calls `complete(m,idx,&r,0)` for EVERY failure, then `done:`
runs `r26_finish(m->extension, token, r.retained)` with `r.retained=1` → **R26_FAILED**. On the next
`r14_lock`, L77 calls `r26_lock_begin` FIRST (stage=32); a FAILED R26 returns **-EBUSY/-16 at stage=32**
(matching `L185699/L185701`), before the L80 slot scan. So one harmless no-resource failure poisons the
R26 token (and leaves the R14 slot FAILED), and every later lock returns -16.

`pair.c` `wl_r20_pair_lock` (L111-123) ALREADY contains the correct recovery shape:
`int acquired=owner_acquire(window);` (= `L185697` A=1/1/1) … `int rc=r20_lock(context,window,out,dirty,&report);`
then `if(rc && !report.retained){released=1;release_rc=owner_release(window);if(release_rc!=1)rc=-EPROTO;}`.
It releases the extra owner ref **exactly when `!report.retained`**, and turns a failed release into
**`-EPROTO`**. Because `complete(…,0)` forces `report.retained=1`, this branch never fires — the owner ref
is never released. **The single defect is the unconditional `retained=1` in the window_module fail path.**

## 2. Preserved UNKNOWNs (do not over-claim)
- **The first `Q=40601000` root cause is UNKNOWN** and owned by cx; T30 does **not** explain or fix it. We
  only remove the *persistent* -16 that a proven-no-resource failure causes afterward.
- **Same OH address ≠ same object / ≠ reuse.** `unref=1/1/0` (rc 0) is only the unref *return*; it does not
  prove the object was freed (the bridge may hold another ref). Whether `7eef2e2790` at 250.798 is the same
  live object or a realloc at the same address needs destroy/free + generation evidence this log lacks.
- `errno=9` (EBADF) at the Q fail is the ambient saved errno; `close=0/0/0` means **no fd was closed here**,
  consistent with (but not by itself proving) `fd==-1`. The fix reads the real fd/map/op state from source,
  never from the error code or errno.

## 3. Minimal recovery predicate (v1, strict — per contract)
Recover **only** when ALL hold for the current lock's single Request:
1. `request_called == 1` and `request_rc != 0` (this Request failed),
2. `buffer == NULL`,
3. `native == NULL`,
4. `mapped == 0`,
5. `fd == -1`,
6. `H / N / M / U / F / B` all **not called** (0/0/0 each), and `fence`/`close`/`prepare` not called.

No ownership is inferred from the error-code name. If **any** of these is false — `fd != -1`, a returned
buffer, a Mapped buffer, any op called, or any cleanup failure — the path stays on the **old conservative
retained=1 / FAILED** route (even a *successful* Abort does not widen recovery this round). Widening the fd
condition later requires an accurate provider resource contract + cases + a spec revision first.

## 4. Recovery action — ONE change in `window_module.c`; pair.c and R26 are UNCHANGED
There is **NO new cross-layer transaction** and **no new mutex/rollback**. Each layer keeps its own
independent mutex and linearization point, in the existing order: **R14 mutex (`complete`) → `r26_finish`
(its own mutex) → return to pair → pair `owner_release`**. In-lock we only transfer this call's reservation;
a non-owner thread never clears another's slot. The only edit is at the window_module fail path:

> compute `recoverable = t30_request_resource_free(&r, buffer, native, mapped, fd)` (pure predicate, §3),
> then call `complete(m, idx, &r, recoverable)` instead of `complete(m, idx, &r, 0)`.

Everything else then falls out of the EXISTING code with no further change:
- `recoverable==1` → `complete(…,1)` takes the existing success arm (`memset` the slot → **FREE**, i.e. the
  R14 reservation is released) and leaves `r.retained==0`.
- `done:` runs the existing `r26_finish(m->extension, token, r.retained)` with `r.retained==0` → **R26 IDLE**
  (token restored to usable; the R26 resident geometry/cache ref is untouched — only this call's token state
  resets). The next `r26_lock_begin` no longer returns -16.
- back in `pair.c`, the existing `if(rc && !report.retained){released=1;release_rc=owner_release(window);
  if(release_rc!=1)rc=-EPROTO;}` now fires (because `retained==0`) and releases the extra owner ref **exactly
  once**.
- The ORIGINAL normalized error is still returned with `raw_rc` preserved (`40601000`); the first error is
  never swallowed. `recoverable==0` keeps the old `complete(…,0)` behavior verbatim (retained=1, FAILED).

**Owner-release-fail is not fake recovery (already correct in pair.c):** when `owner_release` returns
non-success, the existing code sets `rc=-EPROTO`. At that point the R14 slot is already **FREE** and R26 is
already **IDLE** (the release is the last step); the original Q `raw_rc` and the real `release_rc` are both
recorded (`pair_observe` / `diagnostic`), and an error is returned — no ref-balance is claimed and nothing is
force-zeroed (contract scenario 4). No Q retry within one lock: recovery only makes the slot reusable for the
**next** lock entry, which follows the original success path unchanged.

## 5. Preserved behavior (regression)
Geometry, YV12 layout/convert, RGBX output, the 3-slot same-provider gate, owner-instance validation, the
8-slot alias set, and lifecycle premises are **unchanged**. The original format success path keeps its output
bytes/stride/format/alpha, provider call order/count, errno, and unknown-format reject behavior; `retained`
is not widened beyond the specified no-resource failure. T29 diagnostic budget / regular-file sink / errno
discipline are preserved.

## 6. Static pre-verify points (to check before/while deriving — no board)
- **P1** The single fail-path decision site in `window_module.c` where `complete(…,0)` + `r26_finish(token,
  retained=1)` currently run **unconditionally**; the predicate gates ONLY the no-resource branch there.
- **P2** The request-outcome struct actually carries `buffer/native/mapped/fd` and the H/N/M/U/F/B/fence/
  close/prepare call flags the predicate reads (the T29 R29 record already surfaces these — `L185695`).
- **P3** R26 resident geometry/cache ref is distinct from this call's token state; recovery resets only the
  latter (grep the R26 ref-count sites; the successful first-video `retained=0` cache at `L36454` is the
  baseline).
- **P4** The 8-slot alias / 3-slot same-provider gate / owner-instance validation code is NOT on the recovery
  path (recovery only releases *this* reservation).
- **P5** Diff the derived fail path vs the pinned T29 production source: the ONLY change is the predicate +
  the no-resource recovery branch; conservative path byte-unchanged.

## 7. Failure-injection test plan (real derived pair/R14/R26; only OH/provider/sink are doubles)
Offline host fixture that drives the **real derived** lock/unlock entry with an external OH Request fault
injector + a valid owner double:
- **T30-A** (`ttvideo_t30_request_recovery`): inject first Request → `40601000`, buf NULL, fd -1, no ops;
  second Request → valid buffer. Assert: first returns the original error, `raw=40601000`, `H…B=0`,
  `retained=0`, extra owner ref released once; second Requests, Maps, Flushes, is **not** -16; cache refs
  not deleted.
- **T30-B** (`ttvideo_t30_request_recovery`): ≥2 no-resource fails + 2 threads racing the same OH wrapper
  aliases under a controlled barrier; each provider-entering lock calls Request **once**; a non-reservation
  thread never clears another's slot; after failure the slot is **available**, 8 slots not exhausted, refs
  not increased.
- **T30-C** (`ttvideo_t30_retained`): Request fail with non-NULL buffer / fd != -1 / already-held / injected
  close/Unmap/Abort/Flush error → first error + cleanup raw rc preserved, `retained=1` + FAILED kept, no
  repeated Abort, no release of unknown owner, no auto re-Request.
- **T30-D** (`ttvideo_t30_retained`): no-resource extra-owner release returns non-success → record the real
  result and return error; no fake ref-balance / force-zero.
- **T30-E** (`ttvideo_t30_success_regression`): RGBX2 + even-YV12 valid + unknown-format reject → output
  bytes/stride/format/alpha, provider order/count, errno, reject behavior unchanged; retained not widened.
- `ttvideo_t30_runtime_evidence` (**审核: human**): real-device before/after frames — outer deploys/reviews;
  machine-pass ≠ device recovery; if the device never hit the Q fail, only the window-switch result is proven.

## 8. File boundary (what I will add; nothing else)
```
benchmark/2026-10-20-t30-request-recovery/
  DESIGN.md                      (this review)
  src/request_recovery.h         (t30_request_outcome, t30_recoverable predicate, t30_apply_recovery API)
  src/request_recovery.c         (derived from the pinned T29 production fail path: predicate + atomic
                                   recovery set vs conservative retained; values-only, mutex/linearization
                                   preserved; real owner-release return honored)
  test/test_request_recovery.c   (real host fixture: scenarios T30-A..E with OH/provider/sink doubles)
  test/check.py                  (builds + runs the fixture; dispatched by the Rust selector)
  design/source-pins.json        (pinned T29 production baseline + derived SHAs + patch)
  tests/landing-paths.txt, receipts/   (pure paths + durable receipt index)
tools/spec-checks/tests/toutiao_t30_recovery.rs   (selectors: request_recovery / retained /
                                                   success_regression / runtime_evidence — pending,
                                                   NOT reported passed until the real fixture is green)
```
To derive `src/` I need the exact pinned **T29 production source** for the `window_module.c` fail path +
`r26_finish`/R14 reservation + the pair extra-owner ref (bridge `b0e5602a`). I will pin its SHA like the
T29 originals before deriving. **Open question for peer/outer:** confirm the T30 benchmark dir name
(`benchmark/2026-10-20-t30-request-recovery/`) and point me at the pinned production-source path for the
fail path/R26/R14/pair so the derivation matches what is actually deployed.

## 9. Scope / boundary
Does not investigate random exit, does not fix the first Request error source, does not widen to all-failures-
retriable, adds no device call / deployer / permanent config / video-seal conclusion / API-freeze upgrade.
Offline machine-pass is necessary, not sufficient; the runtime-evidence scenario is outer-reviewed (human).
Peer report with the evidenced source chain: commit `eea6f0d5f` at
`westlake-harness-t26-navigation/benchmark/2026-10-20-t29-runtime-review`.
