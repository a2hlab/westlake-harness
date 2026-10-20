# T29 consumer — CC delivery (METHOD-READY)

Independent derivation + hidden logger for the T29 consumer observation. **No REA, no HDC, no device,
no production build, no deploy.** Scope owned by CC: `consumer/**` + `tools/spec-checks/tests/
toutiao_t29_consumer.rs`. The pinned originals are read-only; the real on-board/method comparison is
base5's integration fixture (see below). Commit-only on `analysis/toutiao-video-20261019`.

## Four method-ready sources (current SHA256 — stable)
| source | sha256 |
|---|---|
| `logger/observe29c.h` | `dfc07b884e03e82d4f2b0c5dfd58ebd6b27b8d5d9db40b227ec134b3aca1fd67` |
| `logger/observe29c.c` | `ddd684fb6ee75b3f32634a6f730ccf07e35c0e48dff7cff7956909f440e46664` |
| `derived/oh_surface_texture_jni.cpp` | `7bac8975d4afa98b7dcedc788f66f4543c9494283ed068a693c07c97639a583a` |
| `derived/oh_texture_view_jni.cpp` | `973b287218535b0a3fd9b7343db98dd46de9d0d205fd6d60171f554653922910` |

Baseline pins (derived from, byte-identical, read-only):
`oh_surface_texture_jni.cpp` = `c8d3bb70…c9c6f3f61` (17597 B);
`oh_texture_view_jni.cpp` = `7189e5c2…1878a0558b` (3538 B). Machine-readable: `design/source-pins.json`.

## Base5 integration fixture (the real 40-case method comparison)
Entry: `../westlake-harness-api-progress-peer/benchmark/2026-10-20-t29-consumer-test-peer/replay.py`
```
replay.py --source-root <MAIN> \
          --consumer-source-dir <repo>/benchmark/2026-10-20-t29-window-observation/consumer/derived \
          --extra-source        <repo>/benchmark/2026-10-20-t29-window-observation/consumer/logger/observe29c.c \
          --include-dir         <repo>/benchmark/2026-10-20-t29-window-observation/consumer/logger \
          --out                 <new durable dir>
```
40 per-case independent-process checks (27 consumer + 13 producer): OH identity, self, old→new
correlation, ref(-29)/unref(-31) double rc; originals baseline preserved. **This is the final gate for
`ttvideo_t29_consumer_calls` / `_invalid` / `_producer`.** CC does not re-implement the method fixture
(no duplication).

**Outer-loop status (2026-10-20):** base5's 40 actual-method behaviors + 40 independent-process
diagnostics PASS against `consumer/derived`, and the logger's own 14 modes PASS. In this tree the Rust
selector keeps `_calls`/`_invalid`/`_producer` **NOT_YET_VERIFIED** because the fixture is not in this
tree (it is base5's, unifying into mainline) — the external PASS is recorded here, not impersonated by
a local green. One logger-classification issue remains before the FINAL logger is chosen (see below).

## Original behaviors preserved (observe-only; peer-confirmed)
- `updateTexImage`: the ORIGINAL `released`/null gate is unchanged; `void` → no public rc; the existing
  throw branch is recorded, not altered (no new ExceptionClear/exception-check side effect).
- `attach`/`detach`: reject **only** null state/image (NO `released` gate added); `detached` is set
  only by a successful call (attach→false, detach→true), never by a racy read of the non-atomic field.
- TextureView: `nCreate` still **destroys-then-creates**, **unref-before-ref**, and does `SetLongField`
  after ref within the `window!=null` branch — all preserved. The OH `ref`/`unref` **int32** returns
  are captured (the SDK prototype is int32; the original ignored them) into independent `ref_rc`/
  `unref_rc` (`rc_valid=1`); they never cross each other or substitute a method rc.
- The old window is correlated with the new one **in a single producer-replace record** via a diagnostic
  out-param from the extracted destroy body — no extra getter/GetLongField, no cross-call/thread guessing
  (this closes the T28 "same-address, reuse-unproven" gap at the point of production).

## Logger discipline (independent per-DSO; reuses observe29.c's proven core)
Values only (no address deref); OH = producer **NativeWindow** (not image); errno-neutral; provider
called once; zero extra ref/field-write/destroy; `self` always locatable (see the self note below);
private CLOEXEC regular-file
sink with saved **dev/ino** re-checked before every eligible write (pipe/socket/drift → coverage
UNKNOWN, no fallback, no SIGPIPE); one write/record, no retry, short/failed write → loss + disable;
bounded ≤768 B line with `TRUNC`; mutex-guarded identities/stats/sink + atomic call id; per-DSO budget
16×8×6×(2+2)=3072 normal + 30 invalid/overflow + 1 FIRST_LIMIT + 1 FINAL_EXHAUSTION = 3104, ≤2383872 B.
`r29c_` prefix keeps it independent of the cpu `observe29.c` (no symbol clash, no merge).

## Local checks (CC-owned, real, offline — green)
`tools/spec-checks/tests/toutiao_t29_consumer.rs` → `consumer/tests/check.py`:
- **LOGGER** `consumer/test/test_observe29c.c`, 14 modes PASS: `pipe` (real closed-reader pipe, 0 writes,
  0 attempts, SIGPIPE disposition unchanged), `fd2_rebind` (owned sink ignores fd2 rebind), `sink_drift`
  (dev/ino drift disables), `epipe`/`eintr`/`short` (one attempt, loss, disable, no retry), `hot_new`/
  `parallel` (8×10000, deterministic `writes==3`), `reserve`/`total`/`epochs` (30-invalid + disjoint
  FINAL, 3104/2383872 B, exhausted hot-path 0 cost), `long` (<768 B), `invalid_consumer` (invalid lane).
  → `ttvideo_t29_consumer_budget` / `_sink`. (The `refunref` mode asserts the **pre-fix R29-C04**
  behavior — non-zero `ref_rc` not flipping the lane — so it is NOT evidence of correct ref/unref error
  classification; see "Known logger issue R29-C04".)
- **PINS** derived baseline == pinned originals. → `ttvideo_t29_consumer_pins`.

Raw receipts (argv/stdout/stderr/rc) persisted under `$HOME/.local/share/westlake/t29-consumer-cc/`
(logger build/run, derived `-fsyntax-only`, check run, sha-index) and `consumer/tests/receipts/`.

## Known logger issue R29-C04 (owned by Codex; four sources stay as-is)
Codex's final source review found ONE logger-classification gap: `observe29c.c` `eligible()` computes
`failure = (existing_exception_branch || rc || raw_rc)` and does **not** count a non-zero **valid**
`ref_rc`/`unref_rc` as an error. So after two successes, two producer records whose only failure signal
is `unref_rc=-31` (with `rc=0`, `raw_rc=0`) are mis-classified as success, share the 2-success lane, and
can be dropped. **Scope: logger-side only.** The derived TUs are unaffected — they already record the
independent `ref_rc`/`unref_rc` with `rc_valid=1`, so once the classification includes a non-zero valid
ref/unref rc, those records land in the error lane correctly. Per the outer loop, the minimal
failure-classification fix (+ real negative cases) is done by **Codex from `ddd684fb`** in its own tree;
**CC keeps the four sources unchanged and does not concurrently patch the logger**; root selects the
single FINAL logger. `observe29c.c` here (`ddd684fb`) is the pre-fix baseline Codex derives from.

**The old `refunref` host-test case asserted the WRONG thing** — it asserts a non-zero `ref_rc` does
NOT move a record between lanes (`2 fit, 3rd → FIRST_LIMIT`), which is exactly the R29-C04 pre-fix
behavior. So the **14-mode PASS here does NOT represent the final/correct error budget**: once the
classification counts a non-zero valid ref/unref rc as an error, that assertion flips (a `unref=-31`
becomes an error-lane record). `test/test_observe29c.c` is therefore **frozen as-is** (CC does not
edit it); **Codex delivers the official replacement logger + test**, and **root unifies** both. Cite
the 14-mode PASS only for the sink/concurrency/budget-shape properties, **not** for ref/unref error
classification.

## `self` semantics (accurate)
`self` is the enclosing function's address (locatable, non-zero); `caller` is `__builtin_return_address(0)`
(0 = unknown). Precisely: surface `update`/`detach`/`attach` and TextureView `nCreate` (producer-replace)
record `self` = their own JNI entry (`&SurfaceTexture_nativeUpdateTexImage`, …, `&TextureView_nCreateNativeWindow`).
The **producer-destroy** record's `self` is the **extracted helper** `&destroyNativeWindowImpl`, **NOT**
the JNI entry `TextureView_nDestroyNativeWindow` — because the public `nDestroy` forwards to the helper
and emits no record of its own, so every producer-destroy record (whether from the public destroy or the
nested destroy inside `nCreate`) carries the helper PC. Symbolize `self` accordingly.

## Final boundary
Four sources are stable → method-ready for base5 + Codex source review to run in parallel. **final is
NOT claimed**: it awaits base5's 40-case comparison against `consumer/derived` and the unified mainline
package. No claim of a hit on the real consumer or a proven provider/root-cause (spec `审核: human`
scenario "新运行consumer绑定待真实证据").
