# M2 A0 in-process ArkWeb probe: test APK + probe `.so` built (deterministic, every symbol resolved against the board libraries), one-window board script ready; not yet run on a board

#90, offline preparation for `2026-10-03-m2-webview-roadmap` route a, stage A0. **Nothing ran on a board.** The window
waits for a free board (U13 promotion and U14 stage A hold the boards). No runtime JAR, bridge, BCP or frozen piece is
touched. The native build ran on hw248; the APK build ran on the Mac.

## Release (`$WORKSPACES/westlake-inputs/generations/m2-a0-probe-v1/`, `SHA256SUMS`)

| artifact | sha256 | what |
|---|---|---|
| `a0probe.apk` | `d4d9556ff71f6bb8524fd12a1bcac6bb9a526980969026ff7620748c49343551` | test bundle `org.westlake.a0probe`, debug-signed, built twice byte-identical |
| `liba0probe.so` (in the APK) | `355ac614dd1df6c728b8eef758c71e53a009376d30fb9afbd143ee2b2a3a1191` | the probe, built twice byte-identical |
| `liba0shim.so` (in the APK) | `42e581b0175b774e2be431a3eb38da86c1b46ccb0c1edc277f64c62719cd48d3` | JNI shim, built twice byte-identical |

## How the probe gets into an Android app process (the path chosen, and why)

**Chosen: a separate test APK.** `MainActivity.onCreate` shows a label, then:
1. it calls `System.loadLibrary("a0shim")`;
2. `liba0shim.so` (C, NEEDED only libc) resolves musl's `dlns_get` / `dlopen_ns` at run time and opens `liba0probe.so`
   from the APK's own lib dir in the **`default` namespace**. That is the namespace `liboh_adapter_bridge.so` lives in,
   and the one where `/system/lib64/platformsdk` is visible (roadmap evidence);
3. the shim calls `a0_probe_start(bundle)`.

The process is an ordinary appspawn-x child, like helloworld's. Every bundle gets the `arkwebcore` sandbox mount; the
roadmap showed it in helloworld's child.

**Rejected:**
- **Modifying helloworld.** It is a pinned control input (`knowledge/smoke/controls-apps.json`, apk `2d122a79…`), not a
  test vehicle.
- **The adapter's existing load hooks.** `B7BindFixes.loadLib` only loads fixed `/system/android/lib64/…` paths
  (`libwestlake_jni_gapfill.so`, `liboh_tls_boundary.so`, `libwestlake_html_compat.so`). Using one would mean writing
  into the deployed runtime directory and changing every app's process. The runtime JAR has no other library-load
  hook, only the `debug.westlake.theme_probe` property.
- **Loading the probe directly with `System.loadLibrary`.** It would land in the app's ANL namespace, where the OH
  platformsdk NEEDED libraries are not guaranteed to resolve.

## The probe (`src/native/a0probe.cpp`)

It runs on its own OH `EventRunner` thread. Every step logs `[A0] Sn …` under hilog tag `WL-A0` (domain `0xD000F00`):

| step | does | uses |
|---|---|---|
| S0 | pid / uid, OH main EventRunner present?, ApplicationContext already present? | `EventRunner::GetMainEventRunner`, `Context::GetApplicationContext` |
| S1 | where `NWebHelper` resolved | `dladdr` |
| S2 | attach an ApplicationContext (`ContextImpl` + `ApplicationInfo{bundleName}`) unless one exists. Needed by `GetWebEngine` / `GetInitArgs` (`nweb_helper.cpp:655-722`); a normal app's `GetBaseDir` = `/data/storage/el2/base` needs nothing else | `ApplicationContext::GetInstance` / `AttachContextImpl` (libapp_context) |
| S3 | `SetBundlePath("/data/storage/el1/bundle/arkwebcore")`; `Init(fromArk)` loads the engine; then the optional `SetRenderProcessMode(SINGLE_MODE)`. The order matters: `SetRenderProcessMode` is a no-op until the engine is loaded (`nweb_helper.cpp:1053`) | libarkweb_core_loader |
| S4 | `InitAndRun(fromArk)`. `fromArk=1` uses the fixed `/data/storage/el1/bundle/arkwebcore/libs/arm64` (`arkweb_utils.cpp:65`); `0` uses the bundle path + `libs/arm64` (the mock path, same directory) | |
| S5 | `CreateNWeb(our NWebCreateInfo)`: 720×720, **our `NWebOutputFrameCallback`**, and a producer surface whose consumer we read ourselves (so GPU-path buffers are sampled too) | `IConsumerSurface::Create`, `Surface::CreateSurfaceAsProducer` |
| S6 | handler (load / console / render-exit / FCP), `PutJavaScriptEnabled(true)`, `Resize`, `OnContinue` | |
| S7 | `LoadWithDataAndBaseUrl("https://a0probe.local/", <h1>中文 A0 探针</h1> + a script that sets the page background to `#12ab34` and logs `A0 JS ran`)` | |
| S8 | every frame (callback and/or consumer): centre pixel → `js_colour=1` when it is `12ab34`. First 5, then every 30th, and the first JS-coloured frame are logged. After 20 s: **`[A0] RESULT PASS/FAIL stage=… callback_frames= callback_js= surface_frames= surface_js= console_js= load_end= render_exit=`** | |

**Modes** come from `param debug.westlake.a0probe.mode` (not persistent; reset to 0 on rollback), so one window can
try fallbacks without a rebuild:
- `1` = single render process;
- `2` = `InitAndRun(false)` through the bundle path;
- `4` = skip the ApplicationContext attach;
- `8` = no producer surface (callback only).

## Build (`build_a0_hw248.sh`, `resolve_includes_hw248.sh`, `build_apk.py`; logs in `logs/`)

**Native, on hw248.**
- **Compiler:** the OH tree's prebuilt clang `feef13a3`, the frozen compiler, with `libcxx-ohos` (ABI namespace `__h`,
  matching the board libraries).
- **Linking:** against the board-library copies (`platform-link`; input hashes in
  `logs/hw248-r1-inputs-and-includes.txt`) with `--no-undefined`, `-fvisibility=hidden`, `-fno-rtti`, and prefix maps
  that leave no host path in the ELF (`llvm-strings`: 0).
- **Result:** two builds byte-identical. `evidence/elf-check.txt`: 80 undefined symbols, all defined by the NEEDED
  board libraries except 3 weak crt references.

**Header tree** (`evidence/oh-tree-identity.txt`). It is hw248 `$OH610`, `OpenHarmony-6.1.0.31` (= the boards'
`const.ohos.fullname`); git HEADs are recorded for the 11 projects used. On the include path:
- **One local modification:** `application_info.h` gains `BundleType::APP_ANDROID = 10`, an enum value with no layout
  effect.
- **`ability_runtime` modifications** are appmgr service sources, not on the include path.

**What went wrong on the way, and the rule each one gave** (all fixed):
1. **Wrong same-named headers.** An unguided include search picked same-named headers from `simulator`, `*_lite` and
   the C kit (`application_info.h`, `want.h`, `event_handler.h`, `configuration.h`). It still passed `-fsyntax-only`;
   it would have been a silent ABI mismatch. Fixed with a hand-checked seed (`src/include-seed.txt`) plus excluding
   those trees.
2. **Two IDL-generated headers missing.** `ibundle_mgr_ext.h` and `iverify_manager.h` are absent from a source-only
   tree. They are used only as null `sptr<T>` in inline defaults, so each becomes an empty `RefBase`-derived stand-in
   (`src/genstub/`; the resolver generates one only when the matching `.idl` exists and logs it). A use that needed
   more would not compile.
3. **Compiler flags.** OH's own `-Wno-c++11-narrowing` and `-fno-rtti` (no `typeinfo` exported).
4. **Missing namespace API.** The NDK sysroot `libc.so` stub lacks `dlns_get` / `dlopen_ns`, so the shim takes them
   from `dlsym(RTLD_DEFAULT)` (the board libc has them).

**APK, on the Mac.**
- Built with aapt2 (build-tools 34), the pinned javac / d8 of `build_u12.py`, fixed zip timestamps, `zipalign -p 4`,
  and `apksigner` (Android debug key). apksigner runs on JDK 17, because the default 1.8 cannot read the PKCS12
  keystore.
- Built twice: byte-identical.

## Board window (`board/run_a0.sh <serial> <new out dir> [modes]`, default modes `0 1`)

**Typical length: about 8 minutes, hard stop at 25 minutes in. Order of steps:**
1. **Refusals:** an existing out dir, an APK hash ≠ `d4d9556f`, the board not in `hdc list targets`, or the board
   already held.
2. **`board_note.sh lock`.**
3. **Read-only preflight:**
   - OS name, uptime, boot_id;
   - the bundle must not be installed already;
   - on-board sha256 of the 10 libraries the probe links against, plus the engine, plus `pidof nwebspawn`.
4. **Install:** `hdc file send` → `bm install -p` → `bm dump` check.
5. **Each mode:**
   - `param set`, then `aa start -b org.westlake.a0probe -a org.westlake.a0probe.MainActivity`, then wait 28 s;
   - screenshot (`snapshot_display`), `ps`, `hilog -x`;
   - keep only the lines filtered to A0 / ArkWeb / nweb / the bundle from this launch;
   - process rows for the app and the renderer;
   - **stop at the first `RESULT PASS`.**
6. **`trap` (also on error or signal) rollback, then UNLOCK:**
   - param back to 0;
   - `aa force-stop`;
   - SIGTERM to any process with the bundle's uid (children of appspawn-x / nwebspawn only);
   - `bm uninstall`;
   - remove the pushed files;
   - check that the bundle and its processes are gone.
   **If the check fails, the lock is kept and a board note is written.**
7. **What the board keeps:** nothing. No /system, runtime, JAR, bridge, BCP or other-bundle change at any point.

**Deviation, noted:** this does not go through `board_run.py`. That tool requires a smoke spec and bms shards, i.e. a
runtime deploy; this window installs one test APK and deploys nothing. The LOCK / rollback-before-UNLOCK discipline is
the same.

## Criteria

**Pass:** `[A0] RESULT PASS`, i.e. at least one frame (callback or surface) whose centre pixel is the JS colour
`#12ab34`, and the app process is still alive in `ps` after 28 s (no crash). The run also reports:
- whether a renderer process appeared (process rows, nwebspawn lines) or single-process was used (mode 1);
- `console_js` (the JS console line arrived);
- `load_end`.

**Fail, classified by the last step reached:**

| class | evidence | what it means for route a |
|---|---|---|
| F0 install / start | no `[A0-JAVA]` line; `bm install` output | test-vehicle problem (signature / installer), not ArkWeb |
| F1 shim | `[A0-SHIM] … FAILED: <dlerror>` | the default-namespace open failed (a NEEDED library not visible) → put the code into the bridge's own namespace instead |
| F2 ApplicationContext | crash or empty baseDir at S2 | context attach needs more (configuration, resource manager) |
| F3 engine load | S3 `Init -> 0`, ArkWeb `failed to load lib file` | sandbox / namespace / engine NEEDED |
| F4 init | S4 `InitAndRun -> 0` | init args / context |
| F5 create | S5 `CreateNWeb -> 0x0` | engine-side create failure |
| F6 no frames | S7 lines but `callback_frames=0 surface_frames=0`, `OnRenderExited`, no renderer row | renderer spawn via AppMgr → nwebspawn for an appspawn-x record → retry mode 1 (single process); if that also fails, route b |
| F7 frames, wrong colour | frames>0, `*_js=0` | JS / page did not run (check `console_js`) |
| crash | process gone, fault log in `hilog-all.txt.gz` | the S-step before the crash names the dependency |

## Files

- `src/native/a0probe.cpp`, `src/native/a0shim.c`, `src/native/include/jni.h` (AOSP, `c88ce2cb`).
- `src/java/…/MainActivity.java`, `src/java/AndroidManifest.xml`.
- `src/include-seed.txt`, `src/genstub/{ibundle_mgr_ext.h, iverify_manager.h}` (the exact stand-ins the release was
  built with, byte-equal to the hw248 build dir).
- `resolve_includes_hw248.sh`, `build_a0_hw248.sh`, `build_apk.py`, `board/run_a0.sh`.
- `evidence/`: `elf-check.txt`, `oh-tree-identity.txt`. `logs/`: hw248 resolve / build logs (sanitised), input hashes +
  include list, APK build log. `results.json`.
