# GLESv1_CM crux — decision note (2026-09-27, claude-3)

Scope: reconnaissance + smallest crux only. NOT a gl4es port.

## The wall
`fd-stk` (SuperTuxKart) is the one un-lit app that rendered its OWN error UI:
`SDL Error: Error loading shared library libGLESv1_CM.so: (needed by .../libSDL2.so)`.

## (a) Does OH 6.1.0.31 ship libGLESv1_CM.so? — NO
- Empirical ground truth: the STK error is a **DT_NEEDED file-not-found** — OH's linker search paths
  (`/system/lib64`, `/vendor/lib64`, …) do not contain `libGLESv1_CM.so`. OH ships only **GLESv2/v3**
  (programmable shader pipeline); it dropped the legacy **GLES 1.x fixed-function Common-Lite** library.
- (hw248 source-tree confirmation appended if/when the background grep returns; the runtime error is
  already definitive.)

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
| **A. symlink** `libGLESv1_CM.so → libGLESv2.so` | ❌ insufficient | Gets past "file not found", but BIND_NOW then demands the 14 GLESv1/OES symbols, which libGLESv2 lacks → "cannot locate symbol glMatrixMode". Same failure, different message. |
| **B. thin stub** (export exactly those 14 as no-ops) | ✅ recommended | Satisfies BIND_NOW → libSDL2 loads. Modern STK renders via **GLES3**, so these fixed-function entry points are never CALLED → no-op bodies never run. Stub logs on call, so if STK *does* touch ES1 the child stderr says so. |
| **C. gl4es** (full GL1.x→GLES2 fixed-function translator) | ⛔ not needed | Only required if the app actually RENDERS via fixed-function at runtime. STK does not. Weeks of work for zero gain here. |

Keep the stub MINIMAL — export ONLY those 14. Core GLES2 symbols (`glClear`, `glDrawArrays`,
`glCreateShader`, …) must resolve from the REAL libGLESv2.so, so the stub must not shadow them.

## (c) Crux test — `run_crux.sh` (待 5ea34a45 回挂即测；now runnable)
`glesv1_cm_stub.c` + `run_crux.sh [symlink|stub]`:
1. build stub (OH SDK clang),
2. probe stages STK libs into `/data/local/tmp/asx/lib/arm64-v8a` & launches → baseline "file not found",
3. inject `libGLESv1_CM.so` (symlink or stub) into that dir,
4. re-exec the probe's `run.sh` to relaunch STK,
5. snapshot + child stderr → `screens/stk_<mode>.jpeg`, `out-glesv1cm-crux/<mode>/stk_child.err`.

**Expected & what it proves:**
- symlink → "cannot locate symbol glMatrixMode" ⇒ confirms symlink insufficient (BIND_NOW).
- stub → SDL error gone; STK reaches its GL menu (LIT) OR the next wall. If any
  `[glesv1_cm_stub] CALLED …` line appears ⇒ STK uses ES1 fixed-function ⇒ escalate to gl4es.

**Payoff if stub lights STK:** the same `libGLESv1_CM.so` stub is a drop-in for every SDL2/ES1-linked
app on OH — a reusable one-file shim for a whole class, far cheaper than per-app work.
