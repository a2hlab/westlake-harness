# M2 route-a, Java side: an NWeb-backed `WebViewProvider` skeleton + native interface + mock + unit test

#90, offline, no deploy. The Java half of M2 route-a (cc-t3 owns native/NWeb loading + A0; I own the Java
side). Implements the m2-webview-surface **render core (12)** + the Wikipedia **open-an-article callbacks**
(`shouldInterceptRequest`/`onPageFinished`/`shouldOverrideUrlLoading`/`onProgressChanged`), behind one native
backend interface (JNI signatures matching cc-t3's A0 `NWebHelper`/`CreateNWeb` call surface), with a pure-Java
mock so the Java side unit-tests offline. Compiles against `android.jar` (JDK 21); test runs **19/19 PASS**.

## What is implemented (and where)
- **`OhNWebController`** — the route-a logic, unit-tested. Render core forwarded to the backend:
  `init`(construct NWeb) · `loadUrl` · `loadUrl(url,headers)` · `loadDataWithBaseURL` · `loadData` · `postUrl` ·
  `evaluateJavascript(script, ValueCallback)` · `addJavascriptInterface` · `removeJavascriptInterface` ·
  `setJavaScriptEnabled` · `setDomStorageEnabled` · `setWebViewClient`/`setWebChromeClient` ·
  `reload`/`stopLoading`/`canGoBack`/`goBack`/`onPause`/`onResume`/`draw`/`destroy`. And the **native→Java
  callback dispatch** (implements `NWebCallbackSink`): `onPageStarted`/`onPageFinished` →
  `WebViewClient.onPageStarted/onPageFinished`; `onProgressChanged`/`onReceivedTitle` → `WebChromeClient`;
  `shouldOverrideUrlLoading`/`shouldInterceptRequest` → `WebViewClient` (building a `WebResourceRequest` and
  translating the returned `WebResourceResponse`); `onEvaluateResult` → the matched `ValueCallback<String>`.
- **`NWebBackend`** — the one backend contract; **`NativeNWebBackend`** — JNI `native` declarations (no native
  code here) mirroring cc-t3 A0: `nativeInitEngine` ↔ `NWebHelper::Instance/Init/SetBundlePath/
  SetRenderProcessMode/LoadWebEngine/InitAndRun`; `nativeCreateNWeb` ↔ `NWebHelper::CreateNWeb(NWebCreateInfo)`;
  `nativeRegisterHandler` ↔ `NWeb::RegisterNWebHandler`; `nativeLoadUrl`/`nativeLoadWithDataAndBaseUrl` ↔
  `NWeb::Load.../LoadWithDataAndBaseUrl`; `nativeExecuteJavaScript` ↔ `NWeb::ExecuteJavaScript`; plus settings/
  nav/`nativeOnDraw` (blit the `OutputFrameCallback` CPU frame)/`nativeDestroy`. Native upcalls the registered
  `NWebCallbackSink` directly (no extra Java entry points). **`MockNWebBackend`** — pure-Java mock: records every
  call and synthesises the handler callbacks (page lifecycle + a pagelib `shouldInterceptRequest` + progress +
  evaluate result) so the Java side tests with no `.so` and no Android runtime.
- **`OhNWebProvider` / `OhNWebFactoryProvider` / `OhNWebSettings`** — the `android.webkit.WebViewProvider` /
  `WebViewFactoryProvider` / `WebSettings` skeletons (generated from the AOSP android-14 contract): render core +
  `getViewDelegate().onDraw` → controller; everything else a typed stub. `createWebView(webView, privateAccess)`
  → `new OhNWebProvider(new OhNWebController(backend), bundlePath)`.
- **`OhNWebProviderFix.install()`** — the wiring (below).

## Native interface ↔ cc-t3 A0 (the contract)
`NWebBackend`/`NativeNWebBackend` is the whole Java↔native surface. cc-t3's A0 implements the `native` methods
(RegisterNatives) over `NWebHelper`/`NWeb`/`NWebHandler`; the handler upcalls `NWebCallbackSink`. The Java side
never touches NWeb types directly — only this interface — so the mock can stand in 1:1 for the `.so`.

## Unit test — 19/19 PASS (`evidence/test-run.log`)
`NWebRouteATest` (no JUnit, no native, no Android objects): **T1** drives `MockNWebBackend` through an
open-an-article sequence and asserts the handler callbacks fire in order and the `shouldInterceptRequest` return
flows back; **T2** asserts `OhNWebController` forwards the render core to the backend (loadUrl / settings /
addJavascriptInterface / loadDataWithBaseURL) and the `evaluateJavascript` → `ValueCallback` round-trip delivers,
and that callbacks with no client set are safe no-ops. The `android.webkit` translation (sink →
WebViewClient/WebChromeClient) is **compile-checked** (it uses `WebView`/`WebResourceRequest`/`WebResourceResponse`)
but not JVM-run, because android.jar method bodies are runtime stubs — that leg is for the on-board test.

## Where our framework selects the provider — the wiring point
`android.webkit.WebViewFactory.getProvider()` returns the cached `sProviderInstance` first
(AOSP: `if (sProviderInstance != null) return sProviderInstance;`). Today two bind-fixes seed that cache with a
no-op (so `new WebView()` doesn't throw but never renders):
`adapter.activity.WebViewProviderFix.install()` (J8, type-zero `WebViewFactoryProvider` proxy) and
`adapter.activity.J10eWebView.install()` (J10e/J10g, enriched proxy). **Route-a re-seeds the same field:**
`OhNWebProviderFix.install()` sets `sProviderInstance = new OhNWebFactoryProvider()` (loaded by name via
reflection, so the wiring builds with no compile dep on the @hide provider interface). **Call it in the bind-fix
sequence right after `J10eWebView.install()`**, gated on the NWeb engine being available, so it overrides the
enriched no-op. (`wiring/` has the one-paragraph patch note + the exact call site.)

## Compile against framework.jar — the reality (`evidence/compile-*.log`)
- **The core + wiring compile green against the public `android.jar`** (JDK 21): they use only the public
  `android.webkit` API (`WebView`, `WebViewClient`, `WebChromeClient`, `WebResourceRequest/Response`,
  `ValueCallback`) + reflection for the @hide seed. 9 classes; test 19/19.
- **The concrete `WebViewProvider`/`WebSettings` skeletons do NOT compile against the public android.jar** — it
  is a STUB that strips the @hide types the contract needs (`WebView.PrivateAccess` in `createWebView`,
  `TokenBindingService`, `TranslationSpec.DataFormat`) and skews the `WebSettings` abstract-method set
  (41 errors, `evidence/compile-provider.log`). The **deployed framework.jar carries all of them**
  (`dexdump`: `WebViewProvider`, `WebViewFactoryProvider`, `WebView$PrivateAccess`, `TokenBindingService` — all
  `PUBLIC INTERFACE ABSTRACT`/present), and it is **dex** (javac cannot target it). So the concrete provider is a
  framework-classpath artifact that **links at runtime** against the deployed framework.jar; against the public
  stub it cannot be javac'd. **This is exactly why J8/J10e seed `sProviderInstance` by reflection instead of
  implementing the interface** — and why route-a's wiring (`OhNWebProviderFix`) does the same.

## This round's rule
The route-a Java surface factors into (1) an android-free backend contract (`NWebBackend`/`NWebCallbackSink`)
that a mock can fully stand in for — so the render core + callback dispatch are unit-testable offline — and (2)
a thin `WebViewProvider` adapter that only the framework classpath can compile. Seed the provider the way the
framework already does (reflection into `WebViewFactory.sProviderInstance`, after J10e), not by compiling against
the public SDK, which strips the @hide contract.

## Files
- `src/org/westlake/webview/` — `NWebBackend`, `NWebCallbackSink`, `NativeNWebBackend` (JNI decls),
  `MockNWebBackend`, `OhNWebController` (the tested core), `OhNWebProvider`/`OhNWebFactoryProvider`/
  `OhNWebSettings` (the skeleton), `OhNWebProviderFix` (the wiring).
- `test/NWebRouteATest.java` — the dependency-free unit test (19/19).
- `recipe/build.sh` — reproducible compile + test (`ANDROID_JAR`/`JAVA_HOME`/`WORKSPACES` env).
- `recipe/compile-refs/android/annotation/` — tiny no-op annotation stubs for the skeleton compile.
- `evidence/compile-core.log` (green), `evidence/test-run.log` (19/19), `evidence/compile-provider.log`
  (the @hide blockers + why), `wiring/wiring.md`.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no deploy; no push. cc-t3 owns the `.so` (the `native` methods + NWeb loading/A0) and the on-board run;
this is the Java half + a mock. The sink→WebViewClient translation is compile-checked + on-board-verified (not
JVM-run under the android.jar stub). The concrete provider compiles on the framework classpath (not the public
stub); the deployed framework.jar carries the contract (dexdump). Sources read read-only: the AOSP android-14
webkit interfaces (`westlake-inputs/aosp-14.0.0_r1-src`), the deployed framework.jar + the existing seeders
(`westlake-harness-walls .../activity/java/WebViewProviderFix.java`, `J10eWebView.java`), cc-t3's A0 roadmap
(`benchmark/2026-10-03-m2-webview-roadmap`).
