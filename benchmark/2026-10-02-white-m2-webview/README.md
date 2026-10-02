# M2: full-screen WebView without a renderer

## Correction and rule

The old assumption was that the single lit full-WebView app proved a working renderer, or that resuming the paused HTML shim would render these five apps. Both are false. **All six selected app PIDs use the same type-zero/enriched proxy provider and report no real provider APK.** CanIWebView's native controls are visible; its WebView body is blank. HTML compat patches `android.text.Html.fromHtml`, not `android.webkit.WebView`.

The new rule: count native UI signoff separately from DOM/JS content, and distinguish a requested environment flag from a library that actually loaded. Preserve unique Java stderr markers when filtering by app PID.

## Ground truth and route

`results.json` binds the exact outer-signed U10.1T8 reference, screenshot hashes, raw hilog hashes, app PIDs and runtime fingerprints. No board access or new candidate occurred. Hilog ends 4.77–5.89 seconds before t20; these are earlier route observations, not an invented complete t20 trace.

| Key | PID | Signed result | J8 / J10e / unavailable hilog lines | VRT line and geometry |
|---|---:|---|---|---|
| cv2-ca-vaults-randomlydie | 4227 | white | 30820 / 30821 / 30965 | 32674, CapacitorWebView 1200x1920 |
| cv2-com-degeder-yam | 28873 | white | 42579 / 42585 / 42676 | 44267, CapacitorWebView 1200x1920 |
| cv2-com-paultirk-yatoo | 3307 | white | 42346 / 42351 / 42481 | 44048, CapacitorWebView 1200x1920 |
| cv2-dev-obfusk-jiten-webview | 5215 | white | 36617 / 36618 / 36754 | 39625, WebView 1200x1920 |
| cv2-timur-webrtc-check | 11749 | black | 48236 / 48237 / 48333 | 49872, WebView 1200x1920 |
| cv2-com-caniwebview-android | 28630 | lit control | 36661 / 36662 / 36758 | 38464, WebView 1200x1539 |

Each row's source path and numbered excerpt are in `results.json` and `evidence/<key>-hilog.txt`. All six also seed fake `com.android.webview 9999` PackageInfo. That is not an installed provider. Their app-owned maps have zero HTML/Chromium/WebView DSOs; maps coverage is recorded, not generalized beyond those captures. All six APKs have zero embedded native libraries.

`evidence/runtime-methods.json` is an exact deployed-DEX dump, not a current source guess. `WebViewProviderFix.install` seeds `WebViewFactory.sProviderInstance`; J10e replaces it with an enriched proxy. `ProviderInstance.invoke` special-cases ViewDelegate and settings, then returns type-zero defaults. `loadUrl` and `evaluateJavascript` therefore do not execute a browser. `WestlakeWebViewInstall.install` exits with the observed unavailable message when the provider APK is absent. Concrete settings/cookie/service-worker stubs prevent some Java exceptions but supply no DOM/CSS/JS renderer.

### Deployed pieces

Artifact identity PASS is preserved in `evidence/artifact-identity.txt`:

- Effective `bundle/framework/oh-adapter-runtime.jar`: `5ae3dd29d45c2270e8a53a9dc4bbeeca8972b9b092f91898a15d605bc1cc0108`.
- Boot `framework.jar`: `3e106350d882cd1f2f6d71c3cc4e9f124412d16f50a2dcb160007c34e6dde9af`.
- Native publication owner `liboh_android_runtime.so`: `ac59dec077195bc7678c712505b0d802c56e07edea8d049be4a188d20485b7bf`.

The same-named runtime jar in the native payload is stale `d5000c4e`; do not inspect it as the effective jar. The actual native manifest contains private libjnigraphics copies and the existing graphics/window support but no Chromium provider, provider APK or `libwestlake_html_compat.so`. `evidence/native-publication.txt` and the N3b source excerpt show service-cache/feature publication; they do not install a rendering provider. Native WebView functor JNI registration is support machinery, not evidence of a renderer.

## HTML pause scope

`WESTLAKE_HTML_COMPAT` remains requested: all six PIDs say `env set`, then `System.load` fails because the absolute HTML library path is outside the app domain. The effective deployed DEX retains that conditional branch. `deployed_whois` finds no such library in this generation (`evidence/whois-html.txt`). It is not active; do not describe the switch as disabled.

The historical pause is specifically the native ArtMethod rewrite for `Html.fromHtml`, not a ban on browser-provider work. Board evidence lines 2011, 2765, 2770 and 2784 are frozen in `evidence/html-pause.json`: the retry loaded the library but crashed; the outer closed this line and selected real tagsoup boot support instead. Historical source commit `fe153eb8f226a2dd281dd2c1220fbeb7046b9d6f`, `benchmark/2026-09-29-westlake-port/html-compat/westlake_html_compat.cpp:167`, targets `android/text/Html`; it never supplies a WebView provider. Restoring this branch would risk ArtMethod-layout incompatibility across libart generations and predicts **zero M2 content-wall moves**.

## Why 1/117 lit differs from 5/16 white

CanIWebView's existing signed screenshot has a native toolbar, URL input, Load button and WebView/Config navigation outside the blank WebView. The VRT independently records `MaterialButton ... text='Load'` (39415) and `AppCompatTextView ... text='WebView'` (39425); the WebView itself is 1200x1539, about 80% of screen height, rather than 1200x1920. The static `webview_full` bucket does not mean every screen pixel or native control needs the renderer.

The three Capacitor keys depend on their WebView for virtually all content and JS dispatch. YAM is actually a CapacitorWebView in both app DEX and hilog, despite the earlier static feature flag being false. Jiten and WebRTC also place a plain WebView across the screen. Per-APK call points and HTML/JS/CSS asset lists are admitted in `evidence/<key>-calls.json` and `results.json`. A lit native shell is a negative control for provider availability, not proof that local HTML worked.

## Minimal repair and prediction

**Layer:** JAR provider selection plus native provider-loader/namespace closure; not `Html.fromHtml`, not per-app cosmetic placeholders.

1. Introduce an opt-in real-provider route before the J8/J10 proxy cache is seeded. AOSP14 `WebViewFactory.getProvider` first returns a nonnull cached provider; setting `ASX_WEBVIEW_APK` alone after the proxy is cached is insufficient. Only replace a recognized fallback after a real provider is ready; keep the existing fallback for non-target apps.
2. Supply a pinned compatible provider APK, its actual PackageInfo/resources/class loader and the required native closure in the unique owner domain. Local `westlake-inputs/webview/webview-t.apk` and its libwebviewchromium are donor inputs, **not deployed pieces or a proven ready-to-use closure**. Verify generation identity, all NEEDED libraries, Java/native registration, singleton owners and surfaces before proposing a window.
3. Port the verified provider-loading sequence, not just feature flags: the upstream `vm-copies/westlake-current/framework/activity/jni/activity_task_manager_adapter.cpp:419` continues provider-context assets, `WebViewLibraryLoader.loadNativeLibrary` and `getWebViewProviderClass`; file commit `e2b0bf669ca33459c74618883614f4c603fbccbb`. This framework-68 donor is a different architecture from route-A. Its historical WebView/DOM ledger is not evidence that these five keys unlock here. The deployed N3b publication-only code and exact DEX remain the authoritative baseline.

Prediction: **0 unconditional first-fatal moves**, because these are signed living blank/black windows without a demonstrated process fatal event. **Up to 5 first-content walls conditionally move** only with a complete real renderer. RandomlyDie/YAM/Yatoo may next hit Capacitor JS/asset interception; Jiten may next hit networking/TLS/navigation; WebRTC may next hit JS media, permission or camera/microphone support. All next fatal points and post-repair t20 verdicts are unknown. Do not promise five new lit screens or change their signed results.

Do **not** restore the paused HTML-native branch for this repair. It predicts 0 and adds unrelated global boot-method/layout risk. Chromium/provider integration has its own memory, TLS, native-closure and single-copy graphics risks; require a separate scoped, reversible candidate and admission review. This delivery creates none.

## Replay

`python3 benchmark/2026-10-02-white-m2-webview/collect.py` reads local frozen inputs only. The admitted tests require no `.artifacts`, APKs or external worktrees:

```
python3 benchmark/2026-10-02-white-m2-webview/test_evidence.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test white_m2_webview
```
