# J5 — WebView publication Java side (base J4 1c1bbef, pairs with N3b)

cc-t3, 2026-09-30. **sha256 = `dbce2eeada1d40d34d7904936bc09860d6ad30009781444ecd73661ad7e7e223`**
(walls source 4201970c + build-result-j5.json; jar at `vm-copies/j5-dbce2eee/`). Cumulative over J4
(NewPipe signature + noice). changed_existing = `{AppSchedulerBridge, PackageManagerProjectionProxy}` (2).

Implements the Java half of cx-t0's `westlake-harness-bms-deploy/benchmark/2026-09-30-n3b-webview/
JAVA-HANDOFF.md` (donor Westlake `532633da`). Pairs with the N3b runtime candidate
`westlake-generation-n3b-53bb18d1` (runtime 7c9c6240), which exports the two native entries. Target:
Tutanota (dies at `isWebViewSupported(false)` — the framework PM only advertises 6 hardware features and
no WebView provider).

## What it does
- **`WestlakeWebViewInstall` (adapter.core)**:
  - `getSideloadedWebViewPackageInfo()` — the provider PackageInfo for `com.android.webview`, gated on
    `ASX_WEBVIEW_APK` pointing at a real file (verbatim from the donor; public API, with the @hide
    ApplicationInfo/PackageInfo fields set by reflection so it compiles against the SDK android.jar).
  - `nativePrime()`/`nativePublishAfterBind()` `()Z` native decls + `System.load` of the resident runtime
    `.so`, in the runtime ClassLoader that owns the declarations.
  - a reflective `IWebViewUpdateService` in `ServiceManager.sCache["webviewupdate"]` (the WlMediaRouter
    shape — a `Proxy` over the hidden interface + a `LocalBinder`, so the runtime JAR needs **no**
    compile-time hidden WebView API; `WebViewProviderResponse` is built by reflection when asked).
  - pre-bind `install()` (route service + `nativePrime`, holds feature false); post-bind
    `publishAfterBind()` on the main thread via `Handler.post`. Honors the JNI boolean.
- **`WebViewPackageFallback` (adapter.core)**: an `IPackageManager` proxy (chained after
  `AndroidFrameworkPackage`) answering `getPackageInfo`/`getApplicationInfo("com.android.webview")` and
  `hasSystemFeature("android.software.webview")`, all gated on `isAvailable()`.
- **`B7BindFixes`** wires both at bind (pre-bind install+prime) and posts `publishAfterBind` (post-bind).

## Compile note (the reason for the reflection)
The compile `android.jar` is a public SDK stub: it lacks the WebView hidden interfaces
(`IWebViewUpdateService`, `WebViewProviderResponse`, `WebViewProviderInfo`) **and** 13 @hide
`ApplicationInfo`/`PackageInfo` fields (`scanSourceDir`, `credentialProtectedDataDir`, `primaryCpuAbi`,
`compileSdkVersion`, `longVersionCode`, `splitDependencies`, `seInfo`, …). The donor compiled against the
full framework. To land this in the runtime JAR without a full-framework compile jar: the service uses a
reflective `Proxy` (no `extends IWebViewUpdateService.Stub`), and the @hide fields are set via a
`setField` reflection helper (absent fields are skipped). Same technique family as WlMediaRouter (hidden
Binder interface) and AndroidFrameworkPackage (hidden `SigningInfo`).

## Status — INERT without a provider APK (by design)
There is **no WebView APK / Chromium library set** staged (the handoff's provider-payload checklist is
unfulfilled: `ASX_WEBVIEW_APK`/`LIB_DIR`/`DATA_DIR`, the matched arm64 Chromium closure, the provider
data dir, `create(WebViewDelegate)`). So right now `getSideloadedWebViewPackageInfo()` returns null →
`isAvailable()` false → nothing is routed/primed, `hasSystemFeature("android.software.webview")` stays
false, and no app lights. This is the correct "feature false with no real APK" behavior; **the machinery
is an inert capability addition until a real provider is configured** (the failure ordering is copied
faithfully — a public-cache mismatch may set the feature field true yet return false, and this honors the
boolean, never `feature=published` alone). **rollout_ready = false. No new lit app is claimed.**

## Verification
- Build: javac clean (only deprecation notes); `changed_existing` = 2; the four WebView classes are
  added_classes. Injection asserts pass.
- Offline logic: inert-without-APK holds by construction (the `ASX_WEBVIEW_APK` gate). Full behavior
  (prime held-unsupported, post-bind published, provider native load, one ART in child maps, Tutanota t20)
  needs the real APK **and** a board — both currently unavailable (boards offline for machine migration;
  no provider APK). Board validation is the outer loop's to schedule once the provider payload lands.
