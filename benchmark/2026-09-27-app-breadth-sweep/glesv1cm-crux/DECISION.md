# GLESv1_CM crux — decision note (2026-09-27, claude-3)

Scope: reconnaissance + smallest crux only. NOT a gl4es port.

## The wall
`fd-stk` (SuperTuxKart) is the one un-lit app that rendered its OWN error UI:
`SDL Error: Error loading shared library libGLESv1_CM.so: (needed by .../libSDL2.so)`.

## (a) Does OH 6.1.0.31 ship libGLESv1_CM.so? — NO, and no GLESv1 Khronos surface exists at all
On-device inventory (board 5ea34a45, `find /system /vendor -name 'libGLES*' -o -name 'libEGL*'`):
- `/system/lib64/ndk/libGLESv2.so` ✅ (NDK GLESv2 frontend — this IS on the app namespace search path,
  so libSDL2's *other* DT_NEEDED, libGLESv2.so, resolves fine; that's why STK errored only on GLESv1_CM)
- `/system/lib64/platformsdk/{libEGL.so, libGLESv3.so}` ✅
- `/vendor/lib64/chipsetsdk/{libGLES_mali.z.so, libGLESv1_impl.so, libGLESv2_impl.so, libEGL_impl.so}` —
  the **Mali driver backends**. `libGLESv1_impl.so` exists (16.7 MB) BUT `readelf --dyn-syms` shows it
  **exports 0 `gl*` symbols** — it's an internal backend reached through EGL/dispatch, not the Khronos
  `gl*` names. And `/vendor/lib64/chipsetsdk` is NOT even on the app namespace search path (line 491 of
  probe_source_app.py).
- **No `libGLESv1_CM.so` and no library exporting the Khronos GLESv1 `gl*` fixed-function names exists
  anywhere on device.** hw248 OH-6.1 source grep also returned nothing. Confirmed: OH dropped the legacy
  GLES 1.x Common-Lite surface entirely.

## (b) Minimal viable path — thin STUB, not symlink, not gl4es
readelf on the APK's `lib/arm64-v8a/*.so`:
- `libmain.so` (STK game code) references **no gl\* symbols** — it goes through SDL (`SDL_GL_*`).
- `libSDL2.so` **DT_NEEDED `libGLESv1_CM.so` AND `libGLESv2.so`**, and is linked **`FLAGS: BIND_NOW`
  (+ FLAGS_1: NOW)** = eager binding → every UND symbol must resolve AT LOAD.
- `libSDL2.so` UND-references **10 GLESv1-only fixed-function symbols** (`glMatrixMode`, `glColor4f`,
  `glEnableClientState`, `glDisableClientState`, `glLoadIdentity`, `glOrthof`, `glColorPointer`,
  `glTexCoordPointer`, `glTexEnvf`, `glVertexPointer`) **+ 4 OES ext** (`glBindFramebufferOES`,
  `glGenFramebuffersOES`, `glBlendEquationOES`, `glDrawTexfOES`) that libGLESv2 does NOT export.

| Path | Verdict | Why |
|------|---------|-----|
| **A. symlink** `libGLESv1_CM.so → libGLESv2.so` (or → any device lib) | ❌ impossible | **Verified on-device**: BIND_NOW demands the 14 GLESv1/OES symbols, and NO device library exports them — `/system/lib64/ndk/libGLESv2.so` is GLESv2-only; `libGLESv1_impl.so` exports 0 `gl*`. Any symlink → "cannot locate symbol glMatrixMode". Nothing to point at. |
| **B. thin stub** (export exactly those 14 as no-ops) | ✅ required + built | The ONLY way to satisfy BIND_NOW. Built with OH SDK clang: `libGLESv1_CM.so.stub` (14632 B, sha256 `a1ae3950…b37bf`, soname `libGLESv1_CM.so`, exports exactly the 14). Modern STK renders via **GLES3**, so these entry points are never CALLED → no-op bodies never run. Stub logs on call, so if STK *does* touch ES1 the child stderr says so → then escalate to gl4es. |
| **C. gl4es** (full GL1.x→GLES2 fixed-function translator) | ⛔ not needed | Only if STK actually RENDERS via fixed-function at runtime. Modern STK is GLES3. Weeks of work for zero gain here. |

Keep the stub MINIMAL — export ONLY those 14. Core GLES2 symbols (`glClear`, `glDrawArrays`,
`glCreateShader`, …) must resolve from the REAL libGLESv2.so, so the stub must not shadow them.

## (c) Deployment — needs one runtime-staging line (board-runner), NOT a one-shot injection
Tried on 5ea34a45 (2026-09-27), both self-contained injection routes are blocked:
- **Modify the APK** (add `lib/arm64-v8a/libGLESv1_CM.so`): `probe_source_app.py` rejects it —
  `ValueError: Changed original APK input: fd-stk.apk` (it verifies `apk_sha256` from app-inputs.lock.json).
- **Drop the .so on the app namespace search path**: the writable dirs on that path
  (`<logical>/lib/arm64-v8a`, `<logical>/webview-t-lib`, `<logical>`) are the per-run staged runtime root,
  recreated & torn down each probe run; the persistent dirs (`/system/lib64/*`, `/vendor/lib64/*`) are
  read-only. `--runtime-env` can't override `LD_LIBRARY_PATH`/`WESTLAKE_ANDROID_NATIVE_SEARCH_PATH`
  (the launcher sets them; line 512 rejects replacements). Re-exec of the probe's `run.sh` also fails —
  `cd /data/local/tmp/asx: No such file` (that dir is ephemeral).

**Board-runner recipe (the one integration that stages the stub into `<logical>/lib/arm64-v8a` beside
libSDL2, so the windowed probe launch finds it):** add `libGLESv1_CM.so` to fd-stk's `native_libraries`
in `app-inputs.lock.json` pointing at `libGLESv1_CM.so.stub` (sha256 `a1ae3950…b37bf`), then run the
normal probe on fd-stk.

**What that run proves (final crux):**
- SDL "Error loading shared library libGLESv1_CM.so" is gone ⇒ stub satisfied BIND_NOW.
- STK reaches its GL menu (⇒ **LIT**, and the stub is a drop-in for every SDL2/ES1-linked app on OH — a
  reusable one-file shim for a whole class), OR the next wall shows.
- If any `[glesv1_cm_stub] CALLED …` line appears in the child stderr ⇒ STK actually uses ES1
  fixed-function ⇒ escalate to gl4es (only then).

Artifacts here: `glesv1_cm_stub.c` (source), `libGLESv1_CM.so.stub` (built, ready to stage),
`run_crux.sh` (the re-exec approach — kept for reference; superseded by the manifest recipe above),
`artifacts/stk_impl.err` (evidence the run.sh re-exec hit the ephemeral-`asx` wall).
