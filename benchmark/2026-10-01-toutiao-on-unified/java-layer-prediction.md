# Toutiao Java-layer wall prediction (after libflipped/libstdc++), startup-ordered

After wall-1 (libstdc++) clears `libflipped` (native-closure-prediction: bootstrap resolves), these are the
predicted **Java-layer** walls on Toutiao's startup path, from the B10 scanners run against toutiao only
(`com.ss.android.article.news` 13.9.0, apk `a1112a0c`) + the reference `benchmark/2026-08-23-toutiao`
gap-registry. Rows in `java-layer-prediction.csv`. **Caveat:** 53/59 native symbols are `gap_status=
reference-only` (statically referenced, not a *proven* execution wall); the value here is the **ordering +
category + U10 status**, to be confirmed by a dynamic trace once Toutiao runs on U10.

## Headline
- **Toutiao is NOT an appcompat NoActionBar app** — B10 theme-graphics: `startup_actionbar_theme=0`,
  `later_actionbar_theme=0`, `signed_t20=desktop`. So **J10d (theme restore) does not apply**; the walls are
  JNI-native-registration, a few null system services, and android.graphics native constructors.
- App shape: 54 ContentProviders, 57 receivers, 233 services, 973 activities; 213,034 classes; 3,257 native
  declarations (1,945 unbound), 32 missing_class, 103 missing_method (gap-registry).

## Startup order → predicted walls

### Stage I — ContentProvider.onCreate (54, BEFORE Application)
Earliest Java code. ByteDance infra providers run first: `com.bytedance.mira.am.PluginActivityManagerProvider`
/ `PluginPackageManagerProvider` (Mira plugin framework), `keva.KevaMultiProcessContentProvider`,
`apm.battery.dao.MonitorContentProvider`, `bdinstall.BDInstallProvider`, then `androidx.startup.
InitializationProvider` (EmojiCompat / ProcessLifecycle / ProfileInstaller). **Wall if** a provider onCreate
reads a null system service or references one of the 32 missing_class. Not changed by U10 native/jar unless
it touches libstdc++/a null service. *(Static: which provider onCreate fails needs the call graph; the Mira
plugin + keva + apm providers are the earliest risk.)*

### Stage II — MuteArticleApplicationStub.attachBaseContext → Tinker
Tinker/MultiDex patch load. Low risk (file I/O, no system service). The `MuteArticleApplicationStub`
(classes15.dex) is the manifest `application android:name`.

### Stage III — MuteArticleApplicationStub.onCreate → DelegateApp → ByteDance SDK init
- **System services we return null** (our stub covers 20: uimode/power/alarm/clipboard/account/audio/appops/
  locale/notification/jobscheduler/connectivity/location/webviewupdate/shortcut/batterystats/batteryproperties/
  deviceidle/media_session/power_exemption/restrictions). **Likely used-and-null** by the SDK init:
  `phone`(TelephonyManager), `wifi`(WifiManager), `sensor`, `vibrator`, `usagestats` → `getSystemService`
  returns null → NPE if read without a null-check. *(Exact witness needs the service-consumer scan; flagged.)*
- **JNI native (NDK), early**: `AAssetManager_fromJava`/`AAsset_*` (asset load) + `ALooper_*` (message loop) →
  provider `libandroid.so` (in `shared_sonames`, resolves) **BUT `AAssetManager_fromJava` hits the N10b
  `gAssetManagerOffsets` cache wall** (DIGEST N10b: per-copy offset caching; the "fid==null GetLongField"
  family) — not fixed by the U10 jar.
- **metasec** (`ms.bd.c` JNI) is a ByteDance-specific hack **NOT ported** (mainline decision); its native
  dispatch stays an unbound-native gap — Toutiao may hit/retry it; accepted/deferred, not a shared-layer fix.

### Stage IV — MainActivity + render
- **`libjnigraphics.so` (3: `AndroidBitmap_lockPixels`/`unlockPixels`/`getInfo`)** → **U10 adds libjnigraphics
  to shared_sonames (native-closure-prediction) → resolves.**
- **`libnativewindow.so` (35: `ANativeWindow_*`, `AHardwareBuffer_*`)** → **NOT in `shared_sonames`** → native
  surface/buffer registration wall for native rendering. (B10: "Surface registration; compatibility converter
  not automatically the AOSP cached implementation.") Render-stage; the biggest remaining native group.
- **android.graphics native constructors (9: `BitmapShader.nativeCreate`, `LinearGradient`/`RadialGradient`/
  `SweepGradient.nativeCreate`, `ColorMatrixColorFilter`/`BlendModeColorFilter`, `BlurMaskFilter`, path
  effects)** → route-A `libhwui`/`libart` graphics JNI registration (N10 BitVector territory); **not changed
  by the U10 jar/libstdc++/libjnigraphics**.

## What U10 (jar 37465d6d + native libstdc++/libjnigraphics) clears vs leaves
- **Clears:** libflipped bootstrap (libstdc++); the 3 `AndroidBitmap_*` (libjnigraphics). Toutiao is not
  appcompat so no theme wall; Predicate/CookieManager/WebSettings (J10e/f) help its WebView if it renders.
- **Leaves (next walls, generic candidates):** `libnativewindow.so` (×35, surface/buffer — add to
  shared_sonames if route-A provides it, same one-liner, oc-t4 to confirm provider); graphics-native
  constructors (libhwui/libart registration — N10 lane); a few null system services (phone/wifi/sensor/
  vibrator — add to the stub set if the SDK init NPEs on them); the Mira plugin providers + metasec
  (ByteDance-specific, deferred). Order the fixes by which fires first on the U10 on-board run.

## Recommendation
Run Toutiao as an ordinary U10 key; its FIRST Java-layer wall after libflipped is most likely a Stage-I/III
null system service (phone/wifi) or `AAssetManager` offsets, not a render-stage native. Fix generically
(stub the service / the N10b asset offsets) with the regression gate; `libnativewindow` + graphics
constructors are render-stage, addressed when the app reaches them.

## Outer-loop correction (2026-10-01 20:10)

"libnativewindow ×35" does not hold: none of toutiao's 138 `.so` NEED libnativewindow.so and none reference
`AHardwareBuffer_*` (oc-t4's sweep-wide scan also found 0 consumers). Seven `.so` reference eight `ANativeWindow_*`
symbols through **libandroid.so** (already in shared_sonames). Against U9's libandroid.so export table two are missing:
`ANativeWindow_lock` and `ANativeWindow_unlockAndPost` -- the CPU draw-into-window path, the same capability gap as
fd-plus's Surface software-lock wall (cx-bms no-fatal-fixplan). That is the render-time native wall to plan for.
