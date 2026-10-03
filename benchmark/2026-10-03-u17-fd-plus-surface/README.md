# U17 ① fd-plus Surface.lockCanvas — A2 software-canvas candidate (REV3: ANW1 unwrap + directPathLive bypass; built, gate-clean, not deployed)

#90, offline, built on the hw248 compile host, **not deployed / not pushed**. Fixes fd-plus's U14
first-fatal `IllegalStateException: Surface was not locked` by implementing the two hard-stub Surface JNI
natives `S_nativeLockCanvas` / `S_nativeUnlockCanvasAndPost` on the U16 runtime `1d42dbfb`. The outer
rejected a gate-③ waiver (no new NEEDED) and asked me to **first establish by evidence** who implements
`android.graphics.Canvas`'s native and whether it can take an external buffer, else use the pure-Java path.
The evidence forced **A2 (pure-Java via JNI upcalls + inner libsurface)**; it is built, reproduces the base
byte-identical, changes only the two functions, and adds **zero new NEEDED / zero new object**.

## 坐实 — why A2, by evidence (not A1, not OHCanvasRenderer)
The runtime's Surface nativeObject **is** the `OHNativeWindow*` (not a C++ `android::Surface`): `S_native-
GetFromBlastBufferQueue` returns `b->ohNativeWindow`, and `ANativeWindow_fromSurface` casts `mNativeObject`
straight to it. So lockCanvas needs a buffer from that OHNativeWindow and a `Canvas` bound to its pixels.

| path | who draws the pixels | new NEEDED it pulls | gate ③ |
|---|---|---|---|
| **A1** native `graphics::Canvas(env,obj).setBuffer` | AOSP hwui `graphics::Canvas` | **libhwui** — the runtime has **no** exported `graphics::Canvas::setBuffer/setBitmap` symbol (`readelf --dyn-syms`: absent) and does **not** NEED libhwui | **FAIL** |
| OHCanvasRenderer (dispatched) | OH_Drawing NDK | **libnative_drawing** (not in NEEDED); object not in link set | **FAIL** |
| **A2 (chosen)** JNI upcall to the real Java Bitmap/Canvas + inner libsurface dequeue/queue | the registered skia-backed Java `android.graphics.{Bitmap,Canvas}` | **none** — libsurface already NEEDED | **PASS** |

A2 touches only (a) **inner libsurface** (already NEEDED; the runtime's only two libsurface imports today are
`NativeWindowHandleOpt` + `NativeObjectReference`) via the **inner** `NativeWindow*` names — NOT the `OH_`-
prefixed NDK names, which live in `libnative_window` and would add a NEEDED; and (b) **JNI upcalls** to the
real registered Java `Bitmap`/`Canvas` (skia-backed by the hwui port) — pure `JNIEnv` calls, no link symbol.
`NativeWindowRequestBuffer` / `NativeWindowFlushBuffer` / `GetBufferHandleFromNative` are all defined in
`graphic_surface/surface/src/native_window.cpp` → `ohos_shared_library("surface")` = **libsurface.z.so**
(the already-NEEDED lib), confirmed in the OH source tree and by the +3-import readelf delta below.

## REV3 (2026-10-03) — ANW1 unwrap + directPathLive-gate bypass (candidate `35c36d00763d1682`; supersedes REV2 `cee0098c` / REV1 `4d968008`)
cc-t3 A0 window18 (board `98ab67b9e8`) proved a SurfaceView's `Surface.mNativeObject` is **not** a raw OH
`OHNativeWindow*` — it is an **`AdapterAnw` wrapper** (`oh_anativewindow_shim.cpp`:
`{ ANativeWindow aosp; OHNativeWindow* oh @ +0xc0; uint32_t magic == 'ANW1' 0x414E5731; }`). Passing the
wrapper straight to libsurface trips OH's magic check → `GetSurfaceId rc=40001000`. **REV3 unwraps to the
real OH window** before any libsurface call.
**Why not `oh_anw_get_oh` alone (REV2's bug):** cc-t3 A0 window19 found that on the board `oh_anw_get_oh`
**returns 0** for that same SurfaceView wrapper — its build gates on `directPathLive`
(`return a && directPathLive(a) ? a->oh : nullptr`; `directPathLive` is TRUE only for `State::UNBOUND|LIVE`),
which is **FALSE on the software-lockCanvas path**. So REV2 (which relied on `oh_anw_get_oh` with a raw
fallback) would fall through to the raw wrapper → RequestBuffer rejects it → **no-op** (fd-plus still crashes).
**REV3 hybrid** (`swlock_oh`): try `oh_anw_get_oh` (fast path, ungated builds / live path); if it returns 0,
**read the wrapper's `->oh @ +0xc0` directly after a `magic @ +0xc8 == 'ANW1'` check** — bypassing the gate.
Offsets are **source + disasm double-confirmed**: disasm of `oh_anw_get_oh` in `liboh_adapter_bridge.so`
(`ldr w8,[x0,#200]`=magic@0xc8 cmp `'ANW1'`; `ldr x0,[x0,#192]`=oh@0xc0) + cc-t3 window19 on-board (+0xc0 is
the real OH window, GetSurfaceId OK; window19 lit a SurfaceView through exactly `->oh` even with directPathLive
false). `oh_anw_get_oh` is already imported by the deployed runtime and the raw read adds no symbol, so the
unwrap stays **zero-new-NEEDED / zero-new-UND**. TODO(next-U runtime): export an **ungated `oh_anw_unwrap`** so
the raw `+0xc0` offset can be dropped. Paths (`evidence/anw1-unwrap.txt`): both SurfaceView (WMClient
`oh_anw_wrap`:1380) and SurfaceControl-backed software Surfaces (:1589) store an ANW1 wrapper → unwrap;
SurfaceTexture/unbound → `0xCAFE5C0X` sentinel → return 0; legacy direct → raw fallback.
Why REV1 passed its gates but was still wrong: `equiv.py`/`abi_diff` prove *which code* changed, not a
*semantic assumption about an external object's type* — exactly the gap cc-t3's board run caught.

## What the two functions now do (AOSP-faithful; `src/a2-{globals,lockcanvas}.inc.cpp`)
- **lockCanvas**: sentinel-check `nativeObject`; **`oh_anw_get_oh` to unwrap the ANW1 wrapper → real OH
  window** (raw fallback for legacy); `NativeWindowRequestBuffer` that window; read `GetBufferHandleFromNative`
  → `{width,height,stride,virAddr}`; JNI `Bitmap.createBitmap(w,h,ARGB_8888)`; JNI `Canvas.setBitmap(canvas,bmp)`
  so the app's draws land on it; stash `{key=mNativeObject, nw=unwrapped, buf,bmp,addr,stride,w,h}` in a 16-slot
  side-table; **return the non-zero handle** → `Surface.mLockedObject != 0` → `unlockSwCanvasAndPost` no longer throws.
- **unlockCanvasAndPost**: recover the lock; JNI `Canvas.setBitmap(null)`; `Bitmap.copyPixelsToBuffer` into a
  temp then stride-correct `memcpy` into the dequeued buffer; `NativeWindowFlushBuffer` (rectNumber=0 = whole
  buffer) → the AdapterSurfaceView child node → GPU-composited (the window14-proven self-drawing-child path).

## Build (A′ byte-identical lock; `recipe/build_a2_hw248.sh`, log `evidence/build-a2.log`)
Base `liboh_android_runtime 1d42dbfb` = cc-t3's 112-object relink; the shim slot = `shim_split.o`
(`003a4edb…`, = `n2-native` shim + m1 `split.patch`). Method: recompile the baseline with the frozen recipe
→ **reproduced byte-identical to `003a4edb`** (command locked), then apply the A2 patch and recompile with the
identical `cxxc`, then relink into a **fresh** out dir (cc-t3's `t4-a/t4-b` untouched).
- baseline: `shim_split.o` repro **== 003a4edb** → `BASELINE LOCKED`.
- candidate **REV3** `liboh_android_runtime.so` **sha256 `35c36d00763d1682…`**, **×2 byte-identical**. Kept on
  hw248 (`/home/alvin/cc-wiki-u17-fdplus-rev3/`; `*.so` gitignored, repo is public). (REV2 `cee0098c`, REV1 `4d968008`.)

## Gates (REV3, all PASS; evidence/ )
| gate | result | evidence |
|---|---|---|
| ① ×2 byte-identical | **PASS** `35c36d00…` both | build-a2-rev3.log |
| A′ baseline lock | **PASS** repro == `003a4edb` | build-a2-rev3.log |
| ② only the 2 functions change | **PASS** abi_diff: the 2 target functions `CALLS+` (+ internal `swlock_*` helpers); the only other entry is a benign Cortex-A53-843419 linker veneer shifted into `unixFileControl` by the +code-size (layout artifact, not a source change) | gate-abidiff-calls-rev3.txt |
| ④ abi_diff `--calls` REMOVED empty | **PASS** `CALLS+` only; removed 0; 0 consumer breaks | gate-abidiff-calls-rev3.txt |
| ③ exports Δ0 | **PASS** 788 == 788 | gate-readelf-facts-rev3.txt |
| ③ NEEDED identical | **PASS** 23 == 23 (no libnative_window / libhwui / libnative_drawing) | gate-readelf-facts-rev3.txt |
| ③ UND delta | **+3 only**: `NativeWindowRequestBuffer`, `NativeWindowFlushBuffer`, `GetBufferHandleFromNative` (from already-NEEDED libsurface). `oh_anw_get_oh` already imported + the raw `->oh@0xc0` read adds no symbol → the unwrap adds no UND. | gate-readelf-facts-rev3.txt |
| ③ open_site_scan no new open | **PASS** 197 == 197 (PC-normalized identical; dlopen/dlsym imports identical) | gate-open-sites-{dep,cand}.txt |

equiv.py itself is not runnable on the Linux build host (it is macOS/`xcrun`-oriented and its disasm parser
chokes on the frozen `llvm-objdump` line format — a tool bug, not a candidate issue); the "only 2 functions"
guarantee is carried by abi_diff + the byte-identical baseline + exports Δ0 (see `evidence/gate-equiv.txt`).

## ⑤ Predicted move + upper bound
- **Predicted to move the first-fatal: fd-plus** — the only key whose latest-unified-state (U14 window1)
  first-fatal is `Surface was not locked` @ `unlockSwCanvasAndPost` ← `SurfaceView$1.unlockCanvasAndPost`.
- **Upper bound (static, loose): 25** corpus apks that reference software `SurfaceHolder.lockCanvas`
  (`evidence/surfaceholder-lockcanvas-upper-bound.txt`) — string presence ≠ a gating software-SurfaceView
  draw, so the run-confirmed beneficiary is **fd-plus (1)**. The 14 `lockHardwareCanvas`-only apks use the HW
  RenderNode path, unaffected. Per AGENTS, priority is the actual (1), not the upper bound (25).

## Board-verify risks (do NOT affect the static gates; for cc-t3's board)
No fence wait (RequestBuffer release fence closed → possible tearing, never a crash); channel order assumed
RGBA_8888 == Java ARGB_8888 (kN32 LE) — if the board buffer is BGRA, colours swap (one-line fix); dirtyRect
ignored (whole-buffer lock/flush). Screenshot is ground truth — only a board shows whether fd-plus's
SurfaceView actually draws on screen; these gates prove the change is a surgical, admissible ABI-clean patch.

## Build-input finding (DIGEST E.7)
hw248 did **not** have the runtime's build inputs resident before this round: the OH musl sysroot
(`b6-latest/oh/out/wukong100/.../musl`, 56M) and `ADAPTER_ROOT` (`b87-native/adapter`, 201M) were absent
(only the frozen toolchain + AOSP headers were there). The U16 runtime `1d42dbfb` was therefore **not
reproducible on hw248** until those were rsync'd from the Mac — exactly the E.7 trap ("只留产物会让修复锁死在
一台会消失的构建机上"). Both trees + the n2 source + split.patch are now on hw248 at their `$WORKSPACES` paths;
`deploy/generation.json` records the exact inputs so the generation stays reproducible.

## Files
- `src/a2-globals.inc.cpp` — REV2 global-scope decls (match the shim's global `oh_anw_get_oh`/`OHNativeWindow`
  + the inner libsurface fns); `src/a2-lockcanvas.inc.cpp` — the A2 impl (helpers + the two functions, unwrap).
- `recipe/apply_a2.py` — two anchored splices (globals after `ALOGE`; impl replacing the stub; each asserts
  exactly-one match); `recipe/build_a2_hw248.sh` — the full hw248 build (baseline lock → A2 → relink ×2).
- `deploy/generation.json` — release manifest (artifact sha/path on hw248, base, recipe, gates, risks).
- `evidence/` — REV3: build-a2-rev3.log, gate-abidiff-calls-rev3.txt, gate-readelf-facts-rev3.txt,
  gate-open-sites-cand-rev3.txt, **anw1-unwrap.txt** (the ANW1 source trace, directPathLive gate, + cc-t3
  board proof window18/19). Superseded: REV2 *-rev2.*, REV1 build-a2.log / gate-*.txt / gate-equiv.txt.
  Plus needed-and-linkset.txt, surfaceholder-lockcanvas-upper-bound.txt.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline build on the hw248 compile host; **no board, no deploy, no push**. cc-t3's `t4-a/t4-b` untouched
(fresh `/home/alvin/cc-wiki-u17-fdplus`). Static/ABI gates only — on-board rendering is cc-t3's to verify.
