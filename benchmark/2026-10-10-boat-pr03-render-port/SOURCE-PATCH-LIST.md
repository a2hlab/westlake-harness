# BoatAttack render — source-patch list via strings-diff → git history (cc-t3 #91)

Zero board. Follows the outer's "按源码抄" directive: deployed-binary strings-diff of the three render owners, then
`git log`/`-S` in `~/orca/00.Workspace-games-ad1ab0a7` (games/boatattack-repro, 1069 commits) to find the introducing
commit, then symptom mapping and an incremental-port judgment. Corrects the diff *pair* used in CORRECTION-render-owner.md.

## 0. Correction to the diff pair (先写哪里又错了)
The outer's SHA matrix compared U13 vs the `pr03-74e6-portable` base. That base is an **Aug-11 underlay** the PASS run
**bind-mounts the Sept-24 candidate over** — its runtime has only 4320 strings vs U13's 16080, and the two diverge on
different branches, so "PR03-has / U13-lacks" is not a clean superset there. The correct **good-vs-bad** pair is the files
the PASS run actually loaded — the **Sept-24 candidate**: runtime `adc125f4` (745 KB, a real runtime, *not* a merged
libandroid blob as I earlier implied) + adapter `8ab85446`. Diffed against U13 runtime `18763dd4` + adapter `84695d62`.

## 1. Strings-diff: present in the GOOD candidate binary, absent in the U13 binary

| # | symptom | owning source file | distinctive string (marker) | commit (date) | U13 bin | CAND bin | owning .so |
|---|---|---|---|---|---|---|---|
| P1 | **stretch** (internal render res upscaled) | `src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp` | `nwfs_apply_window_geometry` — "apply BLAST dims only at nativeUpdate where generation-resolved; later handoffs must not invent a fallback" | **80488f376** (2026-08-13) fix(runtime): preserve resolved Unity buffer geometry (+52) | — | — | runtime |
| P2 | **stretch** (buffer geometry at the ANW) | `src/adapter/framework/window/jni/oh_anativewindow_shim.cpp` | `perform SET_BUFFERS_GEOMETRY rejected %dx%d: no live geometry` | 7266868a1 (2026-07-30, Fn04 lane) | **0** | **1** | adapter |
| P3 | **stretch** (child surface window) | `src/adapter/framework/window/jni/oh_window_manager_client.cpp` | `oh_rs_get_child_surface_window: resize geometry %dx%d failed` | 64564707d (08-04) / b77b83576 (08-11) | — | — | adapter |
| P4 | **purple / tint** (wrong pixel format) | `src/adapter/framework/window/jni/oh_anativewindow_shim.cpp` | `[WALL2-FMT]` + `pixel_format_mapper.h`: AOSP `RGBA_8888=1` (EGL_NATIVE_VISUAL_ID) → OH `GraphicPixelFormat RGBA_8888=12` before `OH_OP_SET_FORMAT`; **unmapped → OH fmt 1 = CLUT → gralloc mis-reads color** | WALL2-FMT seed 2026-06-29, wired in the SET_BUFFERS_GEOMETRY/SET_FORMAT path (shim) | (format map lives inside the P2 geometry path that U13 lacks) | present | adapter |
| P5 | **landscape orientation** | `src/adapter/framework/window/jni/oh_window_manager_client.cpp` | `[UNITY-LANDSCAPE] parent MainSession id=%d orientation=10` + `WindowSessionProperty::SetRequestedOrientation` | b77b83576 / c2864bfda (2026-08-11, Capybara 上屏) | **0** | **2** | adapter |
| P6 | **render-at-all / empty Surface** (white) | `android_graphics_compat_shim.cpp` | BLAST natives `nativeSetSyncTransaction`/`nativeSetNextTransaction`/`S_nativeGetFromBlastBufferQueue` + `oh_wm_get_last_session` / "render will use empty Surface" | ea5f04250 (08-03 task79 白屏定根) → 5144a51eb (08-04) re-added | BBQ natives **0** | present | runtime |
| P7 | **KPH / steering** (touch input) | `src/adapter/framework/android-runtime/src/android_view_InputEventReceiver.cpp` | input-event receiver wiring | **ca3b9f952** (2026-08-16 #55 boat-attack 复现闭包, +35) | — | — | runtime |

Clean static facts (binary string counts): U13 adapter `84695d62` has **0** of `SET_BUFFERS_GEOMETRY rejected` and
`UNITY-LANDSCAPE`; candidate adapter `8ab85446` has **1** and **2**. U13 runtime `18763dd4` lacks the BBQ natives the
candidate runtime `adc125f4` carries. (`git log -S` on the whole repo is noisy here — synced terminal logs + a satellite-
repo *move* commit 759c43aec contain these strings — so the file-scoped `-S` / `git grep` above is the reliable locator.)

## 2. Symptom attribution (direct)
- **stretch = internal render resolution**, not window geometry (both runs are 1920×1200 `AdapterSurfaceView`). The lever is
  the ANW/BLAST geometry preservation (P1+P2+P3): without `nwfs_apply_window_geometry` + the live-geometry guard, the
  producer buffer isn't pinned to the resolved extent → Unity renders small and the BufferQueue upscales (`scalingMode=1`).
- **purple = pixel format** (P4), not the colorspace-metadata path (that `SetBufferColorSpace`/`SetMetadata -5` fails
  310/78× in the GOOD PASS run too). Unmapped AOSP format 1 → OH CLUT = channel/palette misread = purple.
- **white/empty = P6** (BLAST session resolution); **KPH/steering = P7** (input receiver).

## 3. Step ③ — markers in PASS vs 61b hilog (partial; capture-gap caveat)
These are **error-only `ALOGE`** strings — they print on the failure path, so absence is ambiguous, and the 61b
`apply/hilog.txt` is a 162k-line whole-window capture (not Boat-isolated). What is visible:
- `oh_rs_get_child_surface_window` → **PASS 0 / 61b 2** — on 61b the child-surface geometry path is *firing its failure
  branch*, direct evidence U13's geometry handling is breaking (consistent with P2/P3).
- `SET_BUFFERS_GEOMETRY rejected` / `UNITY-LANDSCAPE` / "empty Surface" → 0 in both: in PASS because the path succeeds; on
  61b because **U13's binary doesn't contain the code to log them**. `BBQ.update` 61b 17 / PASS 0 (whole-window, not
  attributable). A clean per-line pin still needs a Boat-isolated route②d capture with `surface-node`/`buffer-configs`/EGL.

## 4. Step ④ — where is the fix, and is it portable to U13?
**Key finding: the fixes already exist in the canonical WestLake source.** The U13 build source tree
`~/orca/workspaces/westlake-bms-suite/src/adapter/...` contains every marker (identical to the boat-repro tree:
`pixel_format_mapper` 11 files, `SET_BUFFERS_GEOMETRY rejected` 1 file, `oh_wm_get_last_session` 6 files). But the U13
**deployed** binaries lack them because they were built from an older commit — the U13 native receipt pins source
`c2891f11` (not present in either boat-repro or westlake-bms-suite HEAD → an older westlake snapshot predating the
window/jni render-shim merge). U13's adapter artifact `84695d62` is in fact a boat-repro **Aug-09** build
(`zigzag-persisted/strict-20260809`), two days before the Aug-11 geometry/orientation/format work.

So the "port" is **not new code to write** — it is a **rebuild of U13's `liboh_adapter_bridge` + `liboh_android_runtime`
from the current canonical source** (which already has P1–P7), producing binaries that contain the markers (like the Aug-11
candidate). cx-build has shown the local Docker frozen-clang build reproduces these byte-for-byte.

Per-patch incremental judgment (frozen rule ③ — same artifact, add function, original behavior preserved):
- P1/P2/P3/P4 are **additive** (a geometry-pin helper, a live-geometry guard, a format mapper on the SET path) — pure
  increments; original non-Unity apps hit the same path with geometry already valid → no behavior change.
- P6 (BLAST natives) was **added→reverted→re-added** (5144a51eb → 9faaf5edd revert → re-present in the Sept candidate) —
  treat as the one to single-variable-verify first; it binds natives the framework *declares*, additive but the revert
  history warns of a regression mode.
- P7 input is additive (receiver wiring).
- **All three owners are SHARED system libs** (adapter + runtime), used by all 128 apps → this is a **shared frozen-state
  rebuild**, not an app-private overlay. Must go through: single-variable swap (`compare_runs.py` variables:1) → 128-app
  full sweep must not regress → register in frozen.json. The runtime/jar are frozen-adjacent → **user sign-off**.

### Recommended close-out (zero-board prep, then one board window)
1. Rebuild `liboh_adapter_bridge` + `liboh_android_runtime` from `westlake-bms-suite` HEAD with the frozen-clang Docker;
   confirm the rebuilt binaries now contain `SET_BUFFERS_GEOMETRY rejected`, `UNITY-LANDSCAPE`, `pixel_format_mapper`, and
   the BBQ natives (strings check) — i.e. they match the candidate's render surface.
2. Single-variable swap on a spare board: U13 → rebuilt adapter (P2/P3/P4/P5), read Boat screenshot (stretch+purple), then
   add rebuilt runtime (P1/P6); capture `surface-node`/`buffer-configs`/EGL this time.
3. 128-app full sweep must not regress before either stands; then frozen.json + user sign-off for the jar/runtime.

**Remaining to confirm (not closed this session):** the exact U13 build-source commit `c2891f11`'s repo + that it truly
predates the shim merge (locate the third westlake snapshot); and the rebuild's byte-repro. Nothing in frozen.json touched;
no board.
