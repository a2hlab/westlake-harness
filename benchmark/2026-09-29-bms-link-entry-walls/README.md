# B7 (#54): the UnsatisfiedLinkError and "ART entry" walls on 5cd

Seven apps that B4 v3 bucketed as `unsatisfied-link` (5) and `art-entry` (2) were reproduced one by one
on 5cd (OH 6.1.0.31, pr03-touch generation, runtime JAR 06141543). Every first cause below is an original
hilog line with its file and SHA-256 (`results.json`, excerpts in `evidence/<key>.txt`; raw runs are
archived at VM `~/a2hlab/board/b7-54/runs`, 418 MB, not in git).

## What was wrong in the earlier classification

- **"ART entry, nterp crash" (fd-catima, fd-fennec_fdroid) was not an ART problem.** The 61b faultlog frame
  `libart.so(nterp_op_nop+0)` is only where ART's implicit null check faulted. On 5cd the same launch ends in
  `NullPointerException ... UserManager.isUserUnlockingOrUnlocked(int)` from
  `ContextImpl.getSharedPreferences(ContextImpl.java:601)`: targetSdk >= 26 contexts whose `dataDir` equals the
  credential-protected dir consult `getSystemService(UserManager.class)`, and this child has no `"user"` service.
- **opencamera's "cannot create namespace" is every pure-Java APK.** BMS reports no `cpuAbi`/`nativeLibraryPath`
  for an APK without `.so`, `PackageInfoBuilder` falls back to `/system/app/<pkg>/lib/armeabi-v7a`, and the route-A
  app-native-loader refuses a search path that is not an existing directory. Same wall in the white-window set
  (fd-etar, burgerking; markor/wifianalyzer have no lib dir either).
- **fd-k9 never reached launch on 5cd.** The B3 installer refused it: `adaptive composition failed for 0x7f0800f1
  (res/qr.xml)` then `no launcher icon; refusing template placeholder` → 9568260. K9's launcher icon is vector only
  (`drawable/ic_launcher` = `@drawable/ic_app_logo` vector + v26 adaptive XML; zero PNG/WebP in the APK).
- **fd-android/fd-k9 (SQLite)**: `liboh_android_runtime.so` 9ccf64f8 links the weak registrars from
  `android_graphics_compat_shim.cpp:66-69` (`mov w0,wzr; ret`, disassembled on the board copy): neither
  real-work `compile_oh_android_runtime*.sh` lists `android_database_*.cpp`/`sqlite3.c`, although the real sources
  exist in bms/ and real-work (and Westlake v3-hbc keeps `REG_JNI(register_android_database_*)`).
- **Flutter (fd-libre, fd-saber)**: `FlutterJNI.loadLibrary` is ReLinker. The first `System.loadLibrary("flutter")`
  error is swallowed (its logger lambda is R8-emptied; dexdump), libflutter is never mapped, and the fallback
  `System.load(<dataDir>/app_lib/libflutter.so)` is refused by `app_native_loader.c path_is_in_app_domain`, which
  compares only `app_search_paths` (line 337) while AOSP also permits the class-loader permitted path. Westlake's
  `OpenNativeLibrary` is a plain `dlopen(path, RTLD_NOW)` with neither check.

## Fixes (all 5cd, all with rollback)

| Fix | Where | Result |
|---|---|---|
| child-local `"user"` binder (the repo's existing `UserManagerProjectionProxy`, verbatim) | runtime JAR overlay, one call from `AppSchedulerBridge.ensureBindApplication` | catima/fennec: `[ZZ-USER] isUserUnlockingOrUnlocked user=200 result=true`, original NPE count 0 |
| non-existent `nativeLibraryDir` → the package's own code dir | `B7BindFixes` (same call) | opencamera/fd-etar/burgerking: `[B7] nativeLibraryDir ... using .../android`, namespace error count 0 |
| B5 alias fix (verbatim sources) carried on the same overlay (r3) | one call after `buildActivityInfoFromAbility` | fennec: `alias=org.mozilla.fennec_fdroid.App target=org.mozilla.fenix.HomeActivity` |
| installer: icon resolving only to vector/adaptive XML → template placeholder (`DECLARED_XML_ONLY`) | `apk_installer.cpp` `ClassifyIconlessApk` | k9: `class=DECLARED_XML_ONLY` → `result is 0, [SUCCESS]`; tamper cases still refuse (host test N01/N02) |

- JAR overlay: `build.py` (dockbuild `a2hlab-b5-java`) → r2 `a92f8135` (B7) / r3 `5aff7a2b` (B5+B7), baseline
  `06141543`, only `AppSchedulerBridge` changed; `deploy.py apply|rollback` bind-mounts over
  `/system/android/framework/oh-adapter-runtime.jar` (loaded per child after fork, so no daemon restart; lost on reboot).
- Installer: local `oh61-bms-kit` + dockbuild, 31/31; the unmodified HEAD rebuilds to the deployed `675536e8`
  byte for byte, the B7 build is `1ebf78ab` (differs only by this change). `deploy_installer.py apply|rollback`
  (#55 procedure: both paths, atomic rename, `begetctl` foundation restart). Foundation restart left the known
  36627 B black desktop → full reboot → non-black desktop (`evidence/screens/installer-*`).
- Host test (`run_resources_hap_host_tests.sh`, now also compiling `adaptive_icon.cpp` + `directory_ex_shim.cpp`,
  which it had been missing since B2/B3): P01 icon-less, P02 vector-only (k9 APK, optional), N01 truncated and
  N02 unreadable-icon refused (`evidence/installer/host-test-run.log`).

## Where each app stops now (unified `bms_batch.py`, both fixes live)

opencamera and catima: AppCompat theme wall (`ApplicationInfo.theme` zeroed by `[G2.5-PIB]`); fennec (r3):
`IStorageManager` null; all bind paths also hit `androidx.startup.InitializationProvider` `getProviderInfo`
NameNotFound (fd-etar, burgerking, ooniprobe, fluffychat, immich, kitchenowl too; minetest: FileProvider
meta-data) — that is #65 items 1–3. No app reached its own UI, so there is nothing for visual sign-off.

## Blocked (fix site outside B7)

- **SQLite JNI**: rebuilding the runtime library is not deployable here — the route-A provider is compiled with
  `-DWLAR_ANDROID_RUNTIME_SHA256_HEX` (`build_route_a_generation_in_container.sh:690`) and embeds 9ccf64f8;
  belongs with a whole-generation rebuild (B6 track).
- **Flutter**: `libapp_native_loader.so` is a route-A provider dependency (`verify_route_a_generation.py:693`).
- **Bridge 84695d62 on 5cd**: the pr03 provider pins bridge 7db99e1b; a bind-mounted 84695d62 made HelloWorld die with
  `exact adapter bridge admission failed before runtime load` (exit 123, rolled back). It must come with provider
  80c9aee0, i.e. the ZigZag candidate generation.

## Rules learned

1. A faultlog frame inside `nterp_*` is where an implicit null check faulted, not an interpreter bug; read the Java
   exception that follows (on 5cd DFX reports it and ART still throws the NPE).
2. `uitest` resets the screen-off override to 10 s on every call (5cd/5ea/61b all show `OverrideTimeout=10000ms`),
   so a t+20 capture after a desktop click is the lock screen unless the timeout is re-set after the click
   (done in `bms_batch.py`). hilog's buffer is 256 K by default (max 16 M): `hilog -x` at t+20 loses the app's lines.
3. The strict `--focus-check` in `bms_batch.py` rejects a HelloWorld that is visibly on screen on 5cd (focus window id
   with no WMS row, app window listed at ZOrder -1); screenshots decide.
4. Route-A pins travel in pairs: runtime library and adapter bridge SHA-256 are compiled into the provider.

## Acceptance

`verify.py` via `tools/spec-checks` (`b7_*`): first_cause pass, wall_crossed pass, blocked_reason pass;
lit_by_outer_review fail (no survivor with its own UI); no_regression fail (HelloWorld verified by screenshot,
ZigZag not launched on the pr03 generation). R2: first causes and wall crossings **verified** on board;
lighting **not achieved**; ZigZag **unverified**.
