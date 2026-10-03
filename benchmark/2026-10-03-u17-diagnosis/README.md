# U17 diagnosis batch — root cause + fix + layer + predicted move for the 4 actionable U17 candidates

#90, offline, no board. Diagnoses the four actionable items from `benchmark/2026-10-03-u14-predicted-vs-actual`'s
`u17-candidates.csv`, each read on the latest unified state (U14 window1 r3 fault-thread stacks) with the first-fatal
as ground truth and corpus DEX hits only as the upper bound (AGENTS). Priority is by **actual first-fatal-blocked key
count**, not the static upper bound; the one item whose predicted move is **0** is flagged *do not start*.

## Priority (actual first-fatal-blocked keys in the latest U14; static = loose upper bound)
| rank | item | layer | actual (U14) | static upper bound | tractability | start? |
|---|---|---|---|---|---|---|
| 1 | **① fd-plus `Surface was not locked`** | native (compat shim + oh_canvas_renderer) | 1 (fd-plus) | 39 apks ref lockCanvas/unlock (loose: many are lockHardwareCanvas) | **high** (wire an existing renderer) | **yes** |
| 2 | **③ fd-im-vector Realm DB-open crash** | native (libc/pthread compat) or app | 1 (im-vector; +mcdonalds unlocalized → ≤2) | 2 (Realm apps) | low (Realm Core engine) | probe-first |
| 3 | **④ fennec Gecko `putenv`** | native (libc/env compat) | 1 (fennec) | 1 | low (Gecko env bootstrap) | probe-first |
| 4 | **② termux bootstrap** | sandbox config (appspawn_x_sandbox.json) | **0 (already lit)** | 1 (termux) + DEX: only Termux family | medium | **no — predicted move 0** |

## ① fd-plus — `IllegalStateException: Surface was not locked` (native, START)
- **Actual first-fatal (U14).** `[CHILD_CK] J_invokeStaticMain_main_threw: java.lang.IllegalStateException: Surface was
  not locked` → `android.view.Surface.unlockSwCanvasAndPost(Surface.java:507)` ← `Surface.unlockCanvasAndPost(491)` ←
  `SurfaceView$1.unlockCanvasAndPost(SurfaceView.java:1730)`. fd-plus (past the U14 `ScanCallback` bind fix) draws its
  SurfaceView with a **software** canvas (`lockCanvas`/`unlockCanvasAndPost`).
- **Root cause.** AOSP `Surface.lockCanvas` sets `mLockedObject = nativeLockCanvas(...)`; `unlockSwCanvasAndPost`
  throws when `mLockedObject == 0`. Our `S_nativeLockCanvas` (`android_graphics_compat_shim.cpp:219`) is a hard stub:
  `return 0;` (comment: *"Without a real surface buffer to lock … HelloWorld doesn't use Surface.lockCanvas"*), and
  `S_nativeUnlockCanvasAndPost` is an empty stub. So `mLockedObject` stays 0 → the unlock throws. The **real
  software-canvas renderer already exists but is unwired**: `oh_canvas_renderer.cpp OHCanvasRenderer::lockCanvas`
  (dequeueBuffer → mmap → OH_Drawing_Bitmap/Canvas) + its unlock→flush→queueBuffer.
- **Fix (minimal).** Wire `S_nativeLockCanvas` → `OHCanvasRenderer::lockCanvas` on the surface's producer, wrap the
  OH_Drawing_Canvas in an `android.graphics.Canvas`, and **return its native ptr** (becomes `mLockedObject`); wire
  `S_nativeUnlockCanvasAndPost` → the renderer's flush + `queueBuffer`. Layer = **native** (both files already in the
  adapter; this connects them). Route-a WebView (Option A) does not need this (NWeb renders via the SurfaceView
  producer directly), but fd-plus and any non-WebView SurfaceView software-canvas app does.
- **Predicted move.** +1 confirmed (fd-plus: first-fatal moves past `unlockCanvasAndPost` to whatever its draw does
  next). Upper bound 39 is loose (lockHardwareCanvas is the HW RenderNode path, unaffected); the realistic beneficiary
  set is SurfaceView *software*-canvas apps, run-confirmed only for fd-plus so far.
- **Dispatchable:** *"Wire S_nativeLockCanvas/S_nativeUnlockCanvasAndPost (android_graphics_compat_shim) to the existing
  OHCanvasRenderer software path so Surface.lockCanvas sets mLockedObject; predicted +1 (fd-plus), native, no boot."*

## ③ fd-im-vector — crash inside `librealm-jni.so` opening the Realm DB (native/app, probe-first)
- **Actual first-fatal (U14).** Fault thread `im.vector.app`, signal 11; stack #09
  `Java_io_realm_internal_OsSharedRealm_nativeGetSharedRealm+132` → `art_quick_generic_jni_trampoline` → #00-#08 all
  inside the app's own `librealm-jni.so` (stripped). So it is **past the U14 `_ctype_` relocation wall** (u14-native-abi-v2)
  and now crashes executing Realm Core while **opening/creating the shared realm database**.
- **Class.** Not symbol-not-found (no `MUSL-LDSO relocating failed` at the fault) and not a bare syscall frame — it is a
  crash **inside Realm Core's DB-open** path. Realm Core opens the `.realm` with mmap + `ftruncate` + **robust
  pthread mutexes** (`PTHREAD_MUTEX_ROBUST`) + file locks; these are the classic bionic-vs-musl ABI/syscall divergences
  (musl's robust-mutex / mmap-growth / fcntl-lock semantics differ). So the class is **ABI/syscall (Realm Core DB
  open)**, app-packaged lib.
- **Fix.** No single-symbol fix; needs (a) a symbolized `librealm-jni.so` to name the exact Realm Core function at
  #00, then (b) a targeted libc/pthread probe (robust-mutex / mmap / fcntl). Layer = **native** (a libc/pthread compat
  for Realm Core) if it is a bionic-semantics gap, else app-specific. Low confidence; this is a probe, not a fix.
- **Predicted move.** 1 (im-vector); mcdonalds (cluster C) was `process-disappeared` on U14 (cause uncaptured) — it may
  be the same Realm-open or different, so upper bound 2, confirmed 1.
- **Dispatchable:** *"Symbolize im.vector.app librealm-jni.so, name the Realm-Core fn at the nativeGetSharedRealm crash
  frame, and probe the robust-mutex/mmap/fcntl musl-vs-bionic gap; diagnosis-only, predicted ≤2 (im-vector[+mcdonalds])."*

## ④ fennec — crash in `GeckoLoader.putenv → strdup` (native/libc, probe-first)
- **Actual first-fatal (U14).** Fault thread `Gecko`, signal 11; stack #04
  `Java_org_mozilla_gecko_mozglue_GeckoLoader_putenv+44` → #03 `strdup+48` → #00-#02 `libmozglue.so`. Gecko's native
  `GeckoLoader.putenv` (which does `putenv(strdup(value))`) crashes in `strdup`.
- **Class.** Past the U14 `__gnu_strerror_r` symbol wall; now a **libc/env ABI** crash — Gecko manages `environ`
  directly and musl's `environ`/`putenv`/`strdup` handling differs from bionic (the OH_RegHook shows our
  `libcore.io.Linux.environ/setenv/unsetenv` route to libjavacore, but Gecko's *native* putenv bypasses that and hits
  musl's `putenv` + a direct `environ` touch). Not symbol-not-found, not a syscall.
- **Fix.** Investigate the `strdup` arg (a null/garbage env string from the Java side) and musl `putenv`/`environ`
  ownership vs Gecko's assumptions; possibly a small libc-env compat for the Gecko bootstrap. Layer = **native**
  (libc/env). Deep + Gecko-specific; low confidence.
- **Predicted move.** 1 (fennec). vlc (the other cluster-D key) is already lit on U14, so D's remaining first-fatal is
  just fennec.
- **Dispatchable:** *"Trace fennec's GeckoLoader_putenv strdup crash — check the env string arg and musl putenv/environ
  ownership vs bionic; diagnosis/probe, predicted +1 (fennec), native libc-env."*

## ② termux — bootstrap `/data/data/<pkg>/files` (sandbox config; DO NOT START — predicted move 0)
- **Status.** termux is **already lit** on U14 (its own terminal UI shows; `summary.gains`), so its first-fatal-move is
  **0** — the bootstrap error is a *functional* wall behind the lit screen, not a lighting blocker. Per AGENTS
  (预测为 0 的不开工) it should not be scheduled for U17 lighting; diagnosed here for completeness.
- **Root + fix layer.** termux hardcodes `TERMUX_FILES_DIR=/data/data/com.termux/files` (bypasses `getFilesDir()`,
  which our `fixDataDirs` overrides to the writable `/data/app/el2/<uid>/base/<pkg>`). The sandbox binds
  `/data/data/<PackageName>` from the **absent host path** (`appspawn_x_sandbox.json` lines 123-126 → APPSPAWN
  errno:2), leaving it empty. **Fix layer = sandbox config** (`appspawn_x_sandbox.json`): make the `/data/data/<PackageName>`
  mount (and the `/data/user/0/<PackageName>` symlink) resolve to the real el2 base dir — either bind the real
  `/data/app/el2/<userId>/base/<PackageName>` onto the sandbox `/data/data/<PackageName>`, or a runtime symlink in
  `fixDataDirs` after the dataDir override.
- **Side effects.** The sandbox template is global (per-app), so every app's `/data/data/<pkg>` would then point at the
  real dir. Apps that use `getFilesDir()` are unaffected (same target); apps that read `/data/data/<pkg>` directly now
  see the real (previously empty) dir — strictly an improvement. Must reverify the lit set (the 28 lit WebView/View
  apps) does not regress. DEX scan: **only the Termux family hardcodes `/data/data/<pkg>/files`**, so the only
  beneficiary is termux (+com.termux.api if run) — and termux is already lit. Net lighting value: 0.
- **Dispatchable:** *"(defer) termux is already lit; the /data/data/<pkg>→real-dataDir sandbox-config fix only restores
  bootstrap functionality (0 lighting), so it is not a U17 lighting item."*

## Summary
- **Start now:** ① Surface lockCanvas — native, tractable, +1 (fd-plus), broad SurfaceView-software-canvas benefit.
- **Probe-first (deep ABI, low confidence):** ③ Realm DB-open, ④ Gecko putenv — each +1, need symbolization/probes.
- **Do not start:** ② termux — already lit, predicted lighting move 0.

## Files
- `u17-diagnosis.csv` — the 4-item table (item, layer, actual, upper_bound, class, fix, predicted, start).
- `evidence/lockcanvas-corpus-scan.txt` — the ① upper-bound scan. `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board, no deploy, no push. First-fatal from the U14 window1 r3 fault-thread stacks (screenshot/signoff for
lit); corpus DEX hits are the upper bound only. No fix built here — root cause + layer + predicted move + a dispatchable
one-liner per item, for the outer to schedule.
