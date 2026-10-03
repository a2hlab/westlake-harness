package org.westlake.webview;

import java.lang.reflect.Field;

/**
 * Route-a wiring: seed {@code android.webkit.WebViewFactory.sProviderInstance} with the NWeb-backed
 * {@link OhNWebFactoryProvider}, so {@code WebViewFactory.getProvider()} short-circuits on the cache
 * (AOSP {@code WebViewFactory.java}: {@code if (sProviderInstance != null) return sProviderInstance;}) and
 * every {@code new WebView(...)} gets an NWeb provider instead of the J8/J10e no-op stub.
 *
 * This is the SAME seam the shipping no-op providers use:
 *   adapter.activity.WebViewProviderFix.install()  (J8: type-zero stub)
 *   adapter.activity.J10eWebView.install()          (J10e/J10g: enriched proxy, still no renderer)
 * Route-a replaces that seed. Call {@code OhNWebProviderFix.install()} in the bind-fix sequence AFTER
 * J10eWebView.install() (so it overrides the enriched stub), gated on the NWeb engine being available.
 *
 * Reflection-only here on purpose: this file compiles against the public android.jar (no compile dep on the
 * @hide {@code WebViewFactory.sProviderInstance} field or on {@code WebViewFactoryProvider}). The concrete
 * {@link OhNWebFactoryProvider} is loaded by name, so this wiring builds even where the provider is compiled in
 * a later framework-classpath step; at runtime the deployed framework.jar carries WebViewProvider /
 * WebView$PrivateAccess / TokenBindingService (dexdump-verified), so the provider links.
 */
public final class OhNWebProviderFix {

    private OhNWebProviderFix() {}

    /** @return true if sProviderInstance now holds the route-a provider. */
    public static boolean install() {
        try {
            Class<?> factory = Class.forName("android.webkit.WebViewFactory");
            Field cache = factory.getDeclaredField("sProviderInstance");
            cache.setAccessible(true);
            Object current = cache.get(null);
            // Load the concrete provider by name so this wiring has no compile-time dep on it (and on the
            // @hide WebViewFactoryProvider interface it implements).
            Object provider = Class.forName("org.westlake.webview.OhNWebFactoryProvider")
                    .getDeclaredConstructor().newInstance();
            cache.set(null, provider);
            System.err.println("[M2-ROUTEA] WebViewFactory.sProviderInstance seeded with OhNWebFactoryProvider "
                    + "(NWeb-backed); replaced=" + (current != null ? current.getClass().getName() : "null"));
            return true;
        } catch (Throwable t) {
            // Leave whatever J8/J10e seeded (no-op stub) so getProvider() still does not throw.
            System.err.println("[M2-ROUTEA] route-a provider seed skipped: " + t);
            return false;
        }
    }
}
