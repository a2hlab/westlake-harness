# Route-a provider wiring — where our framework selects the WebView provider, and where to plug in

## How WebViewFactory picks the provider (AOSP 14, unchanged on route-A)
`android.webkit.WebView.<init>` → `ensureProviderCreated()` → `getFactory()` →
`android.webkit.WebViewFactory.getProvider()`. The top of `getProvider()` is:

```java
static WebViewFactoryProvider getProvider() {
    synchronized (sProviderLock) {
        if (sProviderInstance != null) return sProviderInstance;   // <-- cache short-circuit
        ...                                                         // (native provider load; throws on route-A)
```

`private static WebViewFactoryProvider sProviderInstance;` is the cache. On route-A there is no Chromium provider
to load, so the fall-through path throws `UnsupportedOperationException` (`WebViewFactory.java:338`) and kills the
activity — unless `sProviderInstance` is already set.

## Current seeders (no-op) — the seam route-a reuses
- `adapter.activity.WebViewProviderFix.install()` — J8: seeds `sProviderInstance` with a type-zero
  `WebViewFactoryProvider` proxy (ZeroHandler). Stops the throw; renders nothing.
- `adapter.activity.J10eWebView.install()` — J10e/J10g: re-seeds with an enriched proxy (createWebView returns a
  WebViewProvider proxy with a forwarding ViewDelegate; getters return concrete empties). Still no renderer.

Both are **reflection** (no compile dep on the @hide `WebViewFactoryProvider`/`WebViewProvider`), set from the
bind-fix sequence during app init.

## Route-a plug-in (this benchmark)
Add one call **after** `J10eWebView.install()` in that same bind-fix sequence, gated on the NWeb engine:

```java
// ... existing ...
WebViewProviderFix.install();   // J8  (type-zero stub)
J10eWebView.install();          // J10e/J10g (enriched no-op)
org.westlake.webview.OhNWebProviderFix.install();   // M2 route-a: re-seed with the NWeb-backed provider
```

`OhNWebProviderFix.install()` reflects `WebViewFactory.sProviderInstance` and sets it to a
`org.westlake.webview.OhNWebFactoryProvider` (loaded by name, so the call site has no compile dep on it). Because
it runs last, it overrides the enriched no-op. On failure it logs `[M2-ROUTEA] ... skipped` and leaves J10e's
stub in place (getProvider still won't throw).

## Gating (cc-t3 owns the native readiness signal)
Only re-seed when NWeb is actually usable (bundle path set; `NWebHelper::InitAndRun` succeeded in A0). Suggested:
`OhNWebProviderFix.install()` returns false if `NativeNWebBackend`'s engine init fails, so the loader can keep the
J10e no-op. The exact readiness check is cc-t3's (A0) to provide; the Java side just needs a boolean.

## Packaging
`org.westlake.webview.*` ships in the runtime JAR family alongside the `adapter.activity.*` seeders (or as a new
file per the "new fixes go into new files" rule). The concrete `OhNWebProvider`/`OhNWebFactoryProvider`/
`OhNWebSettings` are compiled on the framework classpath (they implement the @hide contract the deployed
framework.jar carries); `OhNWebController` + `NWebBackend`/`NativeNWebBackend`/`OhNWebProviderFix` compile against
the public API.
