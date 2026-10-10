# Rebuild shared adapter+runtime from source — plan + byte-repro GATE result (cc-t3 #91)

Zero board. Outer task ①: prove `c2891f11` provenance, pick the source commit, **first byte-reproduce the deployed U13
`18763dd4`/`84695d62` with the proven frozen-clang build (if it can't reproduce, stop and report)**, then emit marked new
files, and list the chosen commit's full delta vs `c2891f11` flagging 128-app risk.

## RESULT: byte-repro GATE = **FAIL (stop, per instruction)** for the runtime; adapter is not locally buildable.

### Build mechanism (confirmed, works)
- The native build is a **frozen OHOS clang-15** cross-compile (`--target=aarch64-linux-ohos`, frozen sysroot), driven by
  `…/westlake-inputs/generations/u13-runtime-m1-v1/build/u13/{driver.sh,recipe.sh}`. The toolchain is **Linux x86_64**, so
  it runs inside the `a2hlab-build:24.04` OrbStack container (`scripts/lab/dockbuild.sh`), bind-mounting the Mac paths —
  **not** bare macOS (a bare run dies at `aidl: cannot execute binary file`). Verified clang runs in-container: OHOS clang
  15.0.4. Builds `liboh_android_runtime.so` (43 TUs); **does NOT build `liboh_adapter_bridge.so`** — the arm64 adapter build
  is a **documented KNOWN GAP** in the native repo (`compile_oh_adapter_bridge.sh` emits armv7 only; arm64 `.so` must be
  externally provided).

### The gate: the toolchain is deterministic but no longer reproduces the DEPLOYED runtime
Ran the driver in-container twice (a scratch output dir, then the canonical `build/u13` paths):
| build | sha256 (prefix) | bytes |
|---|---|---|
| scratch rebuild (in-container) | `3a316fea` | 3 184 920 |
| canonical-path rebuild (in-container) | `3a316fea` | 3 184 920 |
| **deployed / archived U13 runtime** | **`18763dd4`** | **3 194 328** |

- Two independent rebuilds produce the **identical** `3a316fea` → the frozen toolchain **is deterministic/reproducible**.
- But `3a316fea ≠ 18763dd4` → the **current on-disk `.work` source has drifted** from the state that built the deployed
  runtime. **Drift pinned:** the deployed `18763dd4` contains a `webview_publication.cpp` translation unit (u13-only symbol
  `_GLOBAL__sub_I_webview_publication.cpp`); the current `.work/b87-native/adapter` source no longer compiles it, so the
  rebuild is 9 408 bytes smaller (strings: 154 u13-only / 64 mine-only). That TU is in **neither** the live `.work` source
  **nor** the recorded `frozen-source-view` (2026-09-30) — the `18763dd4`-era source is not fully on disk.
- This is DIGEST **E.7** materialized ("artifact-only locks the fix to a vanishing build machine"): the deployed runtime's
  exact source snapshot isn't reconstructable here.

**Per the outer's "复现不了就停报": STOP.** Do **not** emit marked new runtime binaries until `18763dd4` is byte-reproduced
first — otherwise we can't attribute any render change to our patch vs the pre-existing source drift (偏移对上≠对象对上).

## Provenance of `c2891f11`
`c2891f11` is a **westlake-harness** commit (2026-09-29, "Add SQLite JNI and permitted app paths to generation v2 …") —
i.e. the **generation-metadata** commit, **not** the native C++ source commit. The native-build `package.json` records
`source_commit = "c2891f11 plus task68 recorded source snapshots"`: the runtime source is the `.work/b87-native/adapter`
snapshot (no `.git`), not a clean commit. So "该 commit 相对 c2891f11 的全部改动" can't be a git range; it's a **snapshot
diff** (below). The deployed **adapter** `84695d62` is a **boat-repro Aug-09 prebuilt** (`zigzag-persisted/strict-20260809`),
external to this native repo.

## Source delta (for when repro is restored) — runtime src `b87-native` → boat-good (`00.Workspace/src/adapter`)
`git diff --no-index`, `android-runtime/src`, 5 files:
| file | Δlines | class | port? |
|---|---|---|---|
| `android_graphics_compat_shim.cpp` | +166 | **RENDER** (nwfs_apply_window_geometry = stretch; BLAST natives already in both) | **yes — the runtime render patch** |
| `android_view_InputEventReceiver.cpp` | +35 | input (KPH/steering) | yes, if the board experiment shows input broken |
| `AndroidRuntime.cpp` | **+638** | **GENERAL — startReg/registration** | **NO — 128-app risk**, unrelated drift |
| `android_os_Process.cpp` | +10 | GENERAL | **NO — 128-app risk** |
| `android_view_DisplayEventReceiver.cpp` | +37 | GENERAL (vsync) | **NO — 128-app risk** |
| `android_view_VelocityTracker.cpp` | −80 (deleted in boat-good) | GENERAL (input) | **NO — 128-app risk** |

→ A wholesale "port boat-good runtime source" would drag +638 lines of `AndroidRuntime.cpp` + Process + DisplayEventReceiver
+ a VelocityTracker deletion into the shared runtime that all 128 apps use. The clean port is **cherry-pick only the render
hunk** (`android_graphics_compat_shim.cpp` nwfs geometry) — after repro is restored.

## Adapter (where stretch/purple/landscape actually live) — NOT a local rebuild
The stretch/purple/landscape levers are in the **adapter** (`oh_anativewindow_shim.cpp` SET_BUFFERS_GEOMETRY + pixel_format
mapper; `oh_window_manager_client.cpp` child-surface + UNITY-LANDSCAPE), and the arm64 adapter build is a **known local gap**.
U13's deployed adapter `84695d62` (Aug-09) lacks them; the boat-repro **Aug-11 `8ab85446`** (the PASS candidate's adapter,
on disk) **has** them (`SET_BUFFERS_GEOMETRY rejected` 1, `UNITY-LANDSCAPE` 2). So the adapter "port" = **re-pin U13's
adapter from `84695d62` → `8ab85446`** (same boat-repro build lineage, +2 days) — a prebuilt swap, not a local rebuild. Its
byte-provenance is the boat-repro build chain, which must be located/rebuilt separately if byte-repro of `8ab85446` is also
required.

## Next steps (ordered; gate-blocked)
1. **Restore `18763dd4` repro first** (blocker): locate the `18763dd4`-era source snapshot incl. `webview_publication.cpp`
   (not in current `.work`/frozen-source-view — likely in the "task68 recorded source snapshots" or on hw248); rebuild →
   must equal `18763dd4`. Only then is any marked rebuild trustworthy.
2. Then cherry-pick the render hunk (`android_graphics_compat_shim.cpp` nwfs geometry) → rebuild → confirm the new binary
   has the geometry marker and the non-render drift (AndroidRuntime/Process/DisplayEventReceiver/VelocityTracker) is **not**
   pulled in; diff old↔new = render-only.
3. Adapter: re-pin `84695d62`→`8ab85446` (and byte-repro `8ab85446` from the boat-repro adapter build if required).
4. cx-t0's board experiment (outer task ②: route②d + swap runtime→`adc125f4`, with surface/buffer/EGL capture) **decides
   which patches are actually required** — fold that back into the cherry-pick set before the single-variable deploy + 128-app
   full-sweep gate (jar/runtime frozen-adjacent → user sign-off).

Nothing in frozen.json touched; no board. Build ran only in the `a2hlab-build` container; the clobbered `build/u13`
output was restored to `18763dd4`.
