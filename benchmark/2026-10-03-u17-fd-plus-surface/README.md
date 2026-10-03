# U17 ① fd-plus Surface.lockCanvas — A2 software-canvas candidate (built, gate-clean, not deployed)

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

## What the two functions now do (AOSP-faithful; `src/a2-lockcanvas.inc.cpp`)
- **lockCanvas**: sentinel-check `nativeObject`; `NativeWindowRequestBuffer` the OHNativeWindow; read
  `GetBufferHandleFromNative` → `{width,height,stride,virAddr}`; JNI `Bitmap.createBitmap(w,h,ARGB_8888)`;
  JNI `Canvas.setBitmap(canvas,bmp)` so the app's draws land on it; stash `{nw,buf,bmp,addr,stride,w,h}` in a
  16-slot side-table (keyed by the OHNativeWindow, since there is no C++ Surface to stash it in); **return the
  non-zero handle** → `Surface.mLockedObject != 0` → `unlockSwCanvasAndPost` no longer throws.
- **unlockCanvasAndPost**: recover the lock; JNI `Canvas.setBitmap(null)`; `Bitmap.copyPixelsToBuffer` into a
  temp then stride-correct `memcpy` into the dequeued buffer; `NativeWindowFlushBuffer` (rectNumber=0 = whole
  buffer) → the AdapterSurfaceView child node → GPU-composited (the window14-proven self-drawing-child path).

## Build (A′ byte-identical lock; `recipe/build_a2_hw248.sh`, log `evidence/build-a2.log`)
Base `liboh_android_runtime 1d42dbfb` = cc-t3's 112-object relink; the shim slot = `shim_split.o`
(`003a4edb…`, = `n2-native` shim + m1 `split.patch`). Method: recompile the baseline with the frozen recipe
→ **reproduced byte-identical to `003a4edb`** (command locked), then apply the A2 patch and recompile with the
identical `cxxc`, then relink into a **fresh** out dir (cc-t3's `t4-a/t4-b` untouched).
- baseline: `shim_split.o` repro **== 003a4edb** → `BASELINE LOCKED`.
- candidate `liboh_android_runtime.so` **sha256 `4d968008a90973a5…`**, size 3199024 (base +4224 B), **×2
  byte-identical**. Kept on hw248 (`/home/alvin/cc-wiki-u17-fdplus/`; `*.so` gitignored, repo is public).

## Gates (all PASS; evidence/ )
| gate | result | evidence |
|---|---|---|
| ① ×2 byte-identical | **PASS** `4d968008…` both | build-a2.log |
| A′ baseline lock | **PASS** repro == `003a4edb` | build-a2.log |
| ② only the 2 functions change | **PASS** abi_diff: "2 function(s) differ" (`S_nativeLockCanvas`, `S_nativeUnlockCanvasAndPost`) + byte-identical baseline of all other objects | gate-abidiff-calls.txt, gate-equiv.txt |
| ④ abi_diff `--calls` REMOVED empty | **PASS** both CALLS+ only; removed 0; 0 consumer breaks | gate-abidiff-calls.txt |
| ③ exports Δ0 | **PASS** 788 == 788 | gate-readelf-facts.txt |
| ③ NEEDED identical | **PASS** 23 == 23 (no libnative_window / libhwui / libnative_drawing) | gate-readelf-facts.txt |
| ③ UND delta | **+3 only**: `NativeWindowRequestBuffer`, `NativeWindowFlushBuffer`, `GetBufferHandleFromNative` (from already-NEEDED libsurface) | gate-readelf-facts.txt |
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
- `src/a2-lockcanvas.inc.cpp` — the A2 implementation (the exact text spliced into the shim).
- `recipe/apply_a2.py` — anchored splice (asserts exactly-one stub match); `recipe/build_a2_hw248.sh` — the
  full hw248 build (baseline lock → A2 → relink ×2).
- `deploy/generation.json` — release manifest (artifact sha/path on hw248, base, recipe, gates, risks).
- `evidence/` — build-a2.log, gate-abidiff-calls.txt, gate-equiv.txt, gate-readelf-facts.txt,
  gate-open-sites-{dep,cand}.txt, needed-and-linkset.txt, surfaceholder-lockcanvas-upper-bound.txt.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline build on the hw248 compile host; **no board, no deploy, no push**. cc-t3's `t4-a/t4-b` untouched
(fresh `/home/alvin/cc-wiki-u17-fdplus`). Static/ABI gates only — on-board rendering is cc-t3's to verify.
