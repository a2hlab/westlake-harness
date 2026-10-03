# fd-libre (Aves): the one Flutter key the U14 EGL fix didn't move — a raster-thread eglGetProcAddress bypass

#90, offline, static. fd-libre = **`deckers.thibault.aves.libre`** (Aves, a Flutter photo gallery). On U14 window1 r3 it
was the only cluster-A Flutter key the EGL interposer (`u14-flutter-libandroid` fff9be31) did NOT move: still
`ANativeWindow_getFormat` + a separate fdsan crash (readout `unchanged`). This pins why, reads the fdsan event, and
gives a minimal fix that folds into the U16 Flutter libandroid cx-bms is already building. **Source of truth: the U14
r3 hilog; everything here is static.**

## TL;DR (three answers)
1. **The interposer fires but only on the UI thread; libre's `1.raster` GPU thread bypasses it.** libre's libflutter
   imports `eglCreateWindowSurface` *and* `eglGetProcAddress` (both PLT). The U14 interposer (libandroid NEEDED pos 4,
   before libEGL at 5) catches the **PLT** call — which the UI thread made (tid 6031: `detected ANW shim …2150 →
   OH NativeWindow …A10`). But the **fatal** `eglCreateWindowSurface` is on tid 6038 = `1.raster`, and its stack goes
   `libflutter #07 → platform libEGL #06 → mali` with **no libandroid frame** — i.e. the raster/GPU backend resolved
   the entry via **`eglGetProcAddress`** (a cached proc pointer), getting the *platform* `eglCreateWindowSurface`,
   which never unwraps → mali `new_window_surface → ANativeWindow_getFormat(raw AdapterAnw)` → SIGSEGV.
   **`ANativeWindow_getFormat` is NOT implemented in our libandroid** (fff9 exports only the 4 EGL funcs); mali binds
   it to `/vendor/lib64/libnativewindow.z.so` internally, unreachable by app-namespace interposition — so the fix is
   at the proc-address layer, not by adding `ANativeWindow_getFormat`.
2. **The fdsan crash is NON-FATAL and separate.** Aves bundles the Flutter `media_kit` plugin
   (`media_kit_libs_android_video`, libmpv/libmediandk). It dlopens `libmediandk.so` →
   `Xpm check failed for libmediandk.so, errno for mmap is: 22` (EINVAL) → "failed to map header". During that failed
   dlopen, musl `load_library_header → close(fd 61)` raw-closes an fd a stdio `FILE*` (`0x…e6e8`) still owns →
   `MUSL-FDSAN … DEBUG SIGNAL(FDSAN)` = **signo 42, non-fatal**. Owner tag = a `FILE*`; closer = musl ld-so. It does
   not block launch and is not the terminal; it is the same lazy `libmediandk` dlopen that lit `fd-mpv` survives
   (DIGEST L459). (DIGEST clusters.csv A's "libre → libmpv → libmediandk Xpm mmap EINVAL" clue = exactly this.)
3. **Minimal fix (folds into U16 native):** extend the already-built U16 `eglGetProcAddress` interposer
   (`flutter_egl_getprocaddress.cpp`, A″ `b1c9f76e`) to return our own unwrapping hooks for the 4 window/surface EGL
   names *before* delegating to the platform resolver (`patch/flutter_egl_getprocaddress.egl-names.patch`). Then the
   raster thread's `eglGetProcAddress("eglCreateWindowSurface")` gets the ANW-unwrapping hook too. **Predicted:**
   libre moves past `eglCreateWindowSurface` (EGLSurface non-zero, like localsend) → then the same U16 interposer
   stubs the Impeller GLES proc gap → parity with cluster A. +0→+1 lit (deep Flutter wall + non-fatal media_kit
   remain), but the anomaly is resolved. Additive (no new export), no boot rebuild.

## 1. The ANativeWindow path — interposer fires on the UI thread, raster thread bypasses it
Both `eglCreateWindowSurface` and `eglGetProcAddress` are PLT imports of libre's libflutter (build `fdf0a0a6`), same
as localsend's (`0d216f3f`) — identical EGL import set (`evidence/libflutter-imports.txt`). The U14 interposer
(`fff9be31`) is in the Flutter-private `libandroid.so` at NEEDED position 4, before platform `libEGL` at 5, so a
**PLT** call to `eglCreateWindowSurface` binds to it (`flutter_egl.cpp`: unwrap `oh_anw_get_oh(window)` → real
platform `eglCreateWindowSurface(oh_window)`).

- **localsend (SUCCESS):** its window surface is created on tid 30548 via the PLT → interposer → `detected ANW shim →
  unwrapped → EGLSurface=<non-zero>`; its `1.raster` (30552) only crashes *later*, deep in Impeller (`libflutter+0x4b655c`).
- **libre (CRASH):** interposer fires on tid 6031 (UI, 12:32:25.566) — `detected ANW shim …2150 → OH NativeWindow
  …A10` — but the fatal SIGSEGV is on tid 6038 = `1.raster` at **25.546, 20 ms earlier, on another thread**, and its
  stack has **no libandroid frame** (`#07 libflutter → #06 platform libEGL eglCreateWindowSurface → mali
  new_window_surface → #00 ANativeWindow_getFormat+60`, `evidence/crash-backtraces.txt` Event B). The raster/GPU
  backend resolved its surface entry via `eglGetProcAddress`, which returns the *platform* `eglCreateWindowSurface`
  (the PLT interposer only overrides the PLT symbol, not a proc-address pointer). The platform function hands mali the
  raw AdapterAnw → `ANativeWindow_getFormat` on the wrapper → SEGV.

The difference between libre and localsend is **not** the imported symbols (identical) but **which thread/path creates
the fatal surface** — a Flutter engine-version/renderer difference (libre's GPU backend creates the window surface on
the raster thread via proc-address; localsend's on the platform thread via the PLT). `ANativeWindow_getFormat` is not
in our libandroid (only `eglCreateWindowSurface/eglDestroySurface/eglSwapBuffers/eglSwapBuffersWithDamageKHR`), and
mali resolves it to vendor `libnativewindow.z.so` internally — so we cannot fix it by implementing
`ANativeWindow_getFormat`; we must make the window that reaches mali already unwrapped on *every* resolution path.

## 2. The fdsan crash — non-fatal, media_kit/libmediandk XPM, not the blocker
`evidence/crash-backtraces.txt` Event A: on tid 6027 (io.flutter/platform), `media_kit` (`package:
media_kit_libs_android_video attached`) dlopens `libmediandk.so`; OH XPM (code-sign) rejects the header mmap
(`errno 22`/EINVAL). During the failed dlopen the musl loader opens the `.so` (fd 61), the mmap fails, and it
`close(61)` — but fd 61 is still owned by a stdio `FILE*` (`0x0000007f9bc1e6e8`), so fdsan raises
`DEBUG SIGNAL(FDSAN)` = **signo 42 (non-fatal diagnostic)**, `LastFatalMessage:attempted to close file descriptor 61
…owned by FILE*`. Owner tag = a `FILE*`; closer = musl ld-so `load_library_header`. The app process survives this
(signo 42 ∈ non-terminal). This is the same lazy `libmediandk` dlopen DIGEST L459 notes the already-lit `fd-mpv`
tolerates, and the clusters.csv A libre clue. It only disables Aves's *video* playback, not the gallery grid, so it
is **not** on the critical path to lighting libre. (A cleaner musl `load_library_header` that doesn't raw-`close` a
reused fd would silence the fdsan noise, but that is an OH-musl hygiene fix, separate from lighting the app.)

## 3. Minimal fix + predicted move + U16 foldability
The U16 build already adds an `eglGetProcAddress` interposer (A″ `b1c9f76e` = U15 `9b824502` +
`flutter_egl_getprocaddress.cpp`) for the Impeller GLES proc-NULL gap. **But it does not cover libre**
(`evidence/u16-getprocaddr-gap.txt`): it calls the platform `eglGetProcAddress` first and returns its result for any
non-`gl*` name, so `eglGetProcAddress("eglCreateWindowSurface")` returns the *platform* function, never our unwrapping
hook. The raster bypass survives A″.

**Fix** (`patch/flutter_egl_getprocaddress.egl-names.patch`): before the platform delegation, return our own
`eglCreateWindowSurface / eglDestroySurface / eglSwapBuffers / eglSwapBuffersWithDamageKHR` (already exported by
`flutter_egl.cpp` in the same `libandroid.so`) when the name matches. Now both the PLT path and the proc-address path
get the ANW unwrap. Additive: **no new export** (those 4 symbols already exist in the .so; only `eglGetProcAddress`'s
body changes), no new NEEDED, no boot rebuild.

**Predicted move (confidence):**
- *High* — libre's raster `eglGetProcAddress("eglCreateWindowSurface")` now returns the unwrapping hook → mali gets
  the OH NativeWindow (exactly localsend's working path) → **past `eglCreateWindowSurface`, EGLSurface non-zero** →
  readout `unchanged → match`, rejoining cluster A.
- *Medium* — then the same U16 interposer stubs the Impeller GLES procs (`glDepthRange` slot) → past `pc=0`. Whether
  libre then **lights** depends only on the gallery grid rendering (pure Flutter); the `media_kit`/`libmediandk` XPM
  failure stays but is non-fatal (video only). So **+0 to +1 lit**; at minimum the first-fatal moves and the one
  anomaly in the U14 Flutter readout is resolved.

**Fold into U16 native (cx-bms merging):** yes — it is a 4-line extension of the file already in the U16 Flutter
libandroid (`flutter_egl_getprocaddress.cpp`). Rebuild A‴ with the same recipe; gates = only-rebuilt function
`eglGetProcAddress`, exports Δ0, equiv on all other functions. Include before the U16 Flutter libandroid is frozen;
if `9b824502`/the Flutter libandroid is already frozen, it takes the "add-feature-preserve-old" (reason=extension)
path the U16 build README already anticipates.

## Files
- `evidence/crash-backtraces.txt` — both fault events (fdsan non-fatal signo 42; the fatal SIGSEGV on `1.raster`).
- `evidence/egl-path-libre-vs-localsend.txt` — the interposer logs + tids showing UI-thread catch vs raster bypass.
- `evidence/libflutter-imports.txt` — `llvm-nm -D` of both libflutter builds (identical EGL import set).
- `evidence/u16-getprocaddr-gap.txt` — why A″'s `eglGetProcAddress` passes `eglCreateWindowSurface` through to platform.
- `patch/flutter_egl_getprocaddress.egl-names.patch` — the minimal fix.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline/static; no board, no deploy, no push, no rebuild (the fix is a patch + prediction; cx-bms/cx-t0 build & verify
on board). The build/A‴ byte-identity and the on-board move are theirs to confirm. The screenshot stays ground truth
for whether libre lights. Sources read read-only: the U14 r3 hilog, the Aves + localsend APK `libflutter.so`
(`westlake-inputs/apks`), and the U14/U16 flutter-libandroid benchmarks.
