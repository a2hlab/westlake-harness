# Toutiao's next wall after ICU: static DT_NEEDED + symbol replay under the U14 app-ns

Offline, board #90, no board/a2hlab (U13 window). After U14 clears the ICU wall (Wall-1 public-lib inherit + Wall-2 the
`_74` shim on libicuuc, `2026-10-03-u14-appns-build`), what is toutiao's next first-fatal? This statically replays the
138 toutiao arm64 native libs' `DT_NEEDED` and bionic-symbol imports against the U14 app-ns visible set (musl order), like
cc-t3's Gecko replay, and combines the Java-side BLE `ScanCallback` reference.

## Method
U14 app-ns visible set for toutiao (NOT enrolled in `native_cluster_path` → **normal bridge path**): its own apk libs +
the AOSP public libraries + my Wall-1 added publics (`libicui18n/libicuuc/libGLESv2/v3/libvulkan/libjnigraphics`) +
`libc/libc++/liblog/libz` + the bridge/runtime (`liboh_android_runtime`, `libbionic_compat`, the pthread bridge,
`libandroidfw`, `libminikin`). A `DT_NEEDED` or symbol not in that set = a gap. (`evidence/needed-and-symbol-replay.txt`.)

## What is NOT a wall (cleared by U13/U14)
- **`_ctype_` / `__ctype_get_mb_cur_max`** (toutiao `libsscronet`, `libCtaApiLib`): **covered** — `libbionic_compat.so`
  exports `_ctype_` (D) and `libwestlake_bionic_pthread_bridge.so` exports `_ctype_@@LIBC` (matching libsscronet's
  `_ctype_@LIBC`). This is the same symbol that killed mcdonalds's realm in U12; U13 provides it. Not toutiao's next wall.
- **`AAssetManager_fromJava` / `AAsset_*`** (`libkrypton`, `liblynx_helium`, `libxbnlog`): **covered** —
  `liboh_android_runtime.so` exports them (U13 asset_manager work).
- **`libGLESv2/v3`, `libvulkan`, `libjnigraphics`, `libicui18n/uc`**: covered by the Wall-1 inherit.
- **`__android_log_print` (77 libs), `__system_property_get` (36), `getauxval` (15), `__cxa_finalize` (133)**: standard,
  provided by `liblog`/`libc` on OH. Not walls.

## Genuine gaps (not bundled in any apk split, not inherited)
| missing `DT_NEEDED` | pulled by | nature | on launch path? |
|---|---|---|---|
| `libnapi_v8.so`, `libv8_libfull.cr.so` | `liblynx_v8_bridge.so` | V8 engine for the Lynx UI framework | on-demand (feed render) |
| `libart.so`, `libdexfile.so`, `libbase.so`, `libcutils.so` | `libcvt.so` | Android **ART-internal** libs — route-A ships ART as `liboh_android_runtime`, NOT these separate `.so` | on-demand |
| `libprofiler.so` | `libnpth_fd_tracker.so`, `libnpth_ref_monitor.so` | npth profiler | optional/diagnostic |
| `libaudioeffect.so` | `libkryptonaudioeffect.so` | audio effects | on-demand (audio) |

## Load order (evidence/loadorder-and-scancallback.txt)
In the U10.1T8 long-wait hilog, before the ICU SIGSEGV only **`libsscronet`** (network) and **`libmetasec_ml`** (security)
load; **Lynx/V8, libcvt, libkryptonaudioeffect, libprofiler do NOT load pre-crash** — they are on-demand (feed/feature),
not on the bind/startup critical path. The ICU crash was early (text init during `handleBindApplication`).

## Prediction for U14
1. **Toutiao most likely LIGHTS the main Activity shell at t20.** The ICU `ICUWrapper` SIGSEGV was the *startup* fatal
   (during bind); clearing it (Wall-2 shim resolves `ubrk_open_74`…) lets bind finish and the main Activity window get
   content. The startup-loaded libs (`libsscronet`, `libmetasec_ml`) have no remaining gaps (`_ctype_` covered). So the
   window should light where it previously went white → desktop.
2. **The dominant NEXT risk is the Lynx/V8 feed path** (`liblynx_v8_bridge` → missing `libnapi_v8.so` +
   `libv8_libfull.cr.so`, genuinely absent). toutiao's feed is Lynx-rendered; when a Lynx card renders it dlopen's the V8
   bridge → `dlopen_ns` fails. Because the feed loads **async after** the shell, the most likely visible outcome is a
   **lit shell with a broken/empty feed**, not a startup crash — *unless* a Lynx card is on the synchronous launch path,
   in which case this is the next first-fatal (an `UnsatisfiedLinkError`/`F02-A12` on `liblynx_v8_bridge`).
3. **Secondary on-demand walls:** `libcvt` → the Android ART libs (`libart/libdexfile/libbase/libcutils`) if a media/
   convert path runs (route-A has no separate `libart.so`); `libkryptonaudioeffect` → `libaudioeffect` on audio;
   `libnpth_*` → `libprofiler` for crash/profiling. None are on the startup path.
4. **Java-side BLE `ScanCallback`:** toutiao references the full BLE scan API (`android/bluetooth/le/ScanCallback`,
   `BluetoothLeScanner`, `ScanSettings`, …). If OH's framework/bridge lacks these and the launch path touches them, a
   `NoClassDefFoundError`/`NoSuchMethodError` fires. BLE scanning is normally lazy + runtime-permission-gated (not in
   `Application.onCreate`), so it is a **lower-likelihood** launch-path wall than the Lynx/V8 native gap — but it is the
   leading **Java-side** candidate once interactive.

**Single most-likely next first-fatal:** `liblynx_v8_bridge.so` failing on the missing V8 engine libs when the Lynx feed
renders — manifesting as a lit shell with a dead feed (async) or, if a launch-path Lynx card exists, a
`dlopen_ns`/`UnsatisfiedLinkError` next-fatal. Confirm on-board by whether t20 is a lit toutiao shell and whether the
hilog shows `liblynx_v8_bridge`/`libnapi_v8`/`libv8_libfull.cr.so` ENOENT after the ICU wall is gone.

## This round's rule
A "next wall" is found by replaying the WHOLE native closure + symbol imports against the *actual* app-ns visible set and
then ordering by **load time** (startup vs on-demand) — a lib missing a dep is only the *next first-fatal* if it loads on
the critical path. Separate the cleared gaps (`_ctype_`, AAssetManager, GLES/ICU) from the genuine ones (V8, ART-internal
libs), and keep the Java-side reference (BLE) as a parallel, lower-priority candidate.

## Files
- `evidence/needed-and-symbol-replay.txt` — the DT_NEEDED replay (missing libs) + bionic-symbol coverage status.
- `evidence/loadorder-and-scancallback.txt` — startup load order + the BLE ScanCallback dex references.
- `results.json`, `landing-paths.txt`.

## Boundaries
Offline; no board/a2hlab (U13 window). Static replay only (no execution). Sources read read-only: the toutiao apk
(`vm-copies/apks-77`, `westlake-inputs/apks`), the U13 deployed libs (`westlake-harness-bms`), the long-wait hilog
(`westlake-harness-u7-executor`).
