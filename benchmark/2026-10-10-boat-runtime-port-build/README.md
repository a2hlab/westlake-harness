# Boat runtime port — build base + candidate ABI gate (cc-t3 #91)

Evidence-first. **Offline, container builds only; no board, no VM shell, no push.**

## 1. Cold reproduction of 18763dd4 — PASS (byte-identical)

Per `knowledge/gates/rebuildable-artifacts.json` entry `runtime-u13-18763dd4` (`build_command.status = verified`):

```
WORKSPACES=… python3 benchmark/2026-10-10-adapter-buildchain/prepare_runtime_cold.py --out <fresh>
DOCKBUILD_MOUNTS="…/westlake-harness-bms-deploy:…/westlake-harness-t3" \
  …/westlake-inputs/tools/dockbuild.sh run -- bash <fresh>/run.sh 2>&1 | tee <fresh>/build.log
```

Container `a2hlab-build:24.04` (`sha256:12ffb932…`), frozen clang-15 (`b107ce03`), source snapshot
`t2c-runtime-reproduction-20261010/runtime187-inputs.tar.gz` (`ba5906c6`). Built
`liboh_android_runtime.so` = **`18763dd4…` — byte-identical to the deployed runtime**
(`evidence/build-provenance.json`; build log tee'd to the persistent `<fresh>/build.log`).

> The stale FZ-009 note ("byte-repro FAIL: webview_publication.cpp TU missing, +9408 bytes") is **superseded**:
> the t2c snapshot is complete and includes that TU; two independent cold builds both land on `18763dd4`.

### Patchable working copy

The geometry TU the recipe compiles (recipe.sh **L318**) is the worktree file
`benchmark/2026-10-02-m1-session-slots/runtime/src/android_graphics_compat_shim.cpp` (`e28f4bc3`, git-tracked).
Its HEAD state **is** the baseline commit with an empty patch series. Candidate builds copy the patched TU over it
and `git checkout` restores it afterwards — the worktree is left clean.

## 2. cx-bms draft geometry patch — applies to source, but FAILS TO LINK

cx-bms's spec `benchmark/2026-10-10-boat-runtime-port-spec/` (`771128f482`) ships `u13-geometry-draft.patch`
(single TU, +17/−21, on the M1 geometry TU per `source-bindings.json`; **not** a b87/Boat wholesale swap). The patch
applies cleanly and the spec's `test_port.py` is **8/8 green** — but building the patched runtime **fails at link**:

```
ld.lld: error: undefined symbol: android::(anonymous namespace)::nwfs_apply_window_geometry(void*, char const*, int, int)
>>> referenced by BBQ_nativeUpdate
```
(`evidence/draft-link-failure.txt`)

### Root cause

The original `nwfs_seed_window_geometry` is `extern "C"` — **C linkage, namespace-agnostic** — so its forward
declaration inside `android::(anonymous namespace)` (line 544, next to the caller `BBQ_nativeUpdate`) and its
definition at **global scope** (line 1225, after `} // namespace android`@1129) resolve to the *same* C symbol.

The draft introduces the new helper `nwfs_apply_window_geometry` as **`static`** (C++ **internal** linkage), but
keeps the same split: forward-declared inside `android::(anon)`, defined at global scope. With C++ linkage the
namespace matters, so these are **two different symbols** — the caller references
`android::(anon)::nwfs_apply_window_geometry`, which is never defined → undefined symbol.

### Why the spec's tests didn't catch it

`test_port.py` validates the **source-text transform** and `git apply --check` only; it never compiles or links. The
source passes while the build fails — the same class of gap as the **T8 lesson** (a candidate judged against an image
reference, not against what the board/linker actually consumes). Recommendation to cx-bms: add a **build/link gate**
to the spec tests, not just a source-text check.

### Minimal fix (`cc-linkfix-over-draft.patch`)

Relocate the single `static void nwfs_apply_window_geometry(...)` **forward declaration from inside
`android::(anon)` to global scope** (before `namespace android {`). Declaration and definition then share one
internal-linkage symbol, and the in-namespace call resolves to it via enclosing-namespace lookup. One line moved; no
re-architecture, no b87/Boat source. cx-bms should fold this into `u13-geometry-draft.patch`.

## 3. Link-fixed candidate — meets every ABI criterion

`= 18763dd4 cold-repro source + cx-bms geometry patch + cc-t3 link-fix`, built the same way →
`liboh_android_runtime.so` **`94718e0d…`** (differs from base, as the geometry changed).

| criterion | requirement | result |
|---|---|---|
| exports | ⊇ the 787 of 18763dd4, 0 removed | **787→787, 0 removed, 0 added, 0 drift, 0 consumer-break** (`evidence/candidate-abi.txt`) — the helper is internal, not exported |
| SQLite/CursorWindow registrars | still **GLOBAL** real bodies | `SQLiteDebug` / `CursorWindow` / `SQLiteGlobal` / `SQLiteConnection` all **`T`** (`evidence/candidate-registrars.txt`); contrast adc125f4 = all `W` weak stubs |
| 4 geometry functions | disasm semantically match `instruction-deltas.json` | **all four match** (below) |

Geometry disasm, baseline(18763dd4) → candidate (`evidence/{base,cand}-*.txt`):

- `nwfs_seed_window_geometry`: `NativeWindowHandleOpt` 1→0, `#1200` 2→0, `#1920` 2→0 → non-mutating (**delta A**).
- `ANativeWindow_fromSurface`: `NativeWindowHandleOpt` 1→0, constants 2→0 → inlined setter removed (**delta B**).
- `ANativeWindow_setBuffersGeometry`: `cbz` 1→**2** → the `width==0` preserve-geometry guard added; setter kept (**delta D**).
- `BBQ_nativeUpdate`: `#1200`/`#1920` 2/2→0/0, `NativeWindowHandleOpt` unchanged → hardcoded constants replaced by the requested-dimension registers (**delta C**).

The PCs differ from `instruction-deltas.json` (those are the *libandroid* PCs; this is the 3.2 MB *runtime*), so the
check is the **semantic** shift, confirmed in all four functions.

## Conclusion

The build base is ready and 18763dd4 reproduces byte-for-byte. The port approach is **validated**: carrying the Boat
geometry delta on the full runtime keeps all 787 exports and the real SQLite/CursorWindow registrars (the surface
adc125f4 dropped) while reproducing the four render deltas. The **only** blocker is cx-bms's draft link defect, with
a one-line fix supplied here. No board, no single-variable render re-proof yet — those are the next steps.

## Files

- `results.json`, `cc-linkfix-over-draft.patch` (the fix for cx-bms to fold in).
- `evidence/build-provenance.json` (dirs, .so + build-log SHAs, toolchain), `draft-link-failure.txt`,
  `candidate-abi.{txt,json}`, `candidate-registrars.txt`, `{base,cand}-<fn>.txt` (geometry disasm).

Build artifacts (`.so`, full logs) are gitignored; their persistent paths + SHAs are in `build-provenance.json`.
