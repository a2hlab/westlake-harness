# HelloWorld black under v2 (5cd) — read-only diagnosis (2026-10-10)

Outer rejected my "per-app quirk" dismissal: HelloWorld is the smoke **control** (lights on every Mac-deploy restore),
so v2-black = a real v2-vs-deploy gap. This is the read-only investigation (zero board write). ZigZag lit; HW black.

## Symptom, pinned (evidence `evidence/5cd-v2/hw-hilog-v2-cold.txt`, process 3874)

HelloWorld reaches the screen pipeline but **never produces a frame**:
- lifecycle `INITIAL→FOREGROUND→RESUMED` (OK), window shown (`WMClient.showWindow session=31 rc=0`,
  `updateSessionRect [0,0,1200,1920]`), surface created (`SurfaceBridge.createSurface OH_Surface_31 1200x1920`),
  **EGL window surface created** (`eglCreateWindowSurface … -> EGLSurface`, `OpenGLWrapper CreateEglSurface`).
- VSync loop runs: `OH_DER_VSync scheduleVsync → RequestFrame → onOhVsync` repeatedly.
- **But ZERO frame production**: no `eglSwapBuffers` / `queueBuffer` / `FlushBuffer` / `drawFrame` / RenderThread draw in
  3874's entire log. So the hwui RenderThread requests VSync but **never swaps a buffer** → the surface stays empty →
  black. ZigZag (Unity, its own GL) *does* swap → lit.

So the black is **not** a crash, SELinux label, spawn, app-load, or window-attach failure — HW is up, has an EGL surface,
and is asking for frames; it just never draws one.

## What is RULED OUT (so the fix is not here)

| Hypothesis | Evidence it's NOT the cause |
|---|---|
| spawn / domain / caps | HW(3874) & lit-ZZ(4035) both `u:r:normal_hap:s0`, CapEff 0, children of appspawn-x 3858 (PPID 1) |
| SELinux labels (errno-13/127) | 0 `data_file`/`data_local_tmp` in HW maps; android tree mislabel=0; appspawn-x=`appspawn_exec` |
| env / boot image | HW & ZZ env KEYS identical (ANDROID_ROOT, ANDROID_BOOT_IMAGE, LD_*, ICU_DATA, …) |
| app crash | no SIGSEGV/FATAL/abort/cppcrash for 3874; it reaches RESUMED |
| RS colorspace/metadata | `Bufferqueue SetMetadata -5` + `skia SetBufferColorSpace fail` are board-wide RenderService(854) noise — ZigZag lit *despite* them, so not the HW discriminator |

## Noted anomaly (likely not causal)

HW(3874) mount ns has `/system/android` **double-bound** (86 entries, `dup=43`), while ROOT(pid1)=43/dup0,
appspawn-x parent(3858)=43/dup0, ZZ(4035)=43/dup0. So the double is **appspawn-x's first-spawned-child ns behavior**
(not my recover — root is clean single), and both layers are **identical bytes**, so file resolution is unaffected. Flagged
for completeness; not the black cause.

## The real discriminator + what's still needed

The open question: **why does HW's hwui RenderThread never swap a frame under v2, when it does under Mac-deploy?** This
needs the exact段比对 the outer asked for — the **deploy-lit HelloWorld hilog + render-init** (from cx-t0's `5a172dd057`
Mac-deploy) vs this v2 capture. **That deploy-lit HW record is not in the repo** (it was a cx-t0 board run); the only HW
hilog present (`benchmark/2026-09-28-bms-route-deploy/spawn-ab/`) is an early, different config. So I cannot complete the
段比对 or name the single differing input without it.

**Request**: cx-t0's `5a172dd057` deploy-lit HelloWorld hilog (its RenderThread/`eglSwapBuffers` sequence + the libs its
RenderThread loads) and/or a deploy-state mount-ns + graphics-lib record — or authorize a 5cd deploy run to capture the
baseline (not read-only; would overwrite v2). Then the diff is: what does deploy give HW's hwui RenderThread (a graphics/
hwui lib, a prop, a surface-transform path — note v2 logs `OH_SurfaceControl [A-stub] SetTransformHint … TODO`) that lets
it swap, which v2 lacks.

## Board state

5cd read-only throughout (launched HW/ZZ, read hilog + /proc; no `/system` write). v2 state intact (libinstalls
`51e1b525`, autostart enabled, ZigZag lit). Fix TBD pending the deploy baseline → then report a window.
