/* J8 (#webview-provider): single-purpose file (freeze unit) -- WebViewFactory provider seed. */
package adapter.activity;

import java.lang.reflect.Array;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * J8 cluster <b>webview-provider</b> (fd-tutanota). first_fatal:
 * <pre>
 *   RuntimeException: Unable to start activity ...MainActivity: UnsupportedOperationException
 *   Caused by: java.lang.UnsupportedOperationException
 *       at android.webkit.WebViewFactory.getProvider(WebViewFactory.java:338)
 *       at android.webkit.WebView.getFactory(WebView.java:2605)
 *       at android.webkit.WebView.ensureProviderCreated(WebView.java:2599)
 *       at android.webkit.WebView.<init>(WebView.java:421)
 * </pre>
 * Constructing a {@code WebView} calls {@code WebViewFactory.getProvider()}, which on route-A has no
 * Chromium provider to load and throws {@code UnsupportedOperationException} — killing the activity
 * before any WebView content is attempted.
 *
 * <b>AOSP 14 r1 reference behaviour:</b>
 *   - frameworks/base/core/java/android/webkit/WebViewFactory.java#getProvider() first returns the
 *     cached singleton: {@code if (sProviderInstance != null) return sProviderInstance;} (top of
 *     getProvider, before the native provider load that is the throw site at WebViewFactory.java:338).
 *   - {@code private static WebViewFactoryProvider sProviderInstance;} is the cache field.
 *   - frameworks/base/core/java/android/webkit/WebViewFactoryProvider.java is the provider interface
 *     ({@code getStatics()}, {@code createWebView(WebView, PrivateAccess)}, {@code getGeolocationPermissions()}, ...).
 *
 * Fix: seed {@code WebViewFactory.sProviderInstance} with a type-zero {@code WebViewFactoryProvider}
 * stub so {@code getProvider()} short-circuits on the cache and never reaches the throwing native load.
 * This clears only the first_fatal (the getProvider throw); a route-A build has no real Chromium
 * renderer, so later WebView drawing is still a no-op — out of scope for this first_fatal round.
 * Self-contained reflection helpers.
 */
public final class WebViewProviderFix {

    private WebViewProviderFix() {}

    public static void install() {
        try {
            Class<?> factory = Class.forName("android.webkit.WebViewFactory");
            Field cache = factory.getDeclaredField("sProviderInstance");
            cache.setAccessible(true);
            if (cache.get(null) != null) {
                System.err.println("[B8-WEBVIEW] sProviderInstance already set; leaving as-is");
                return;
            }
            Class<?> providerIface = Class.forName("android.webkit.WebViewFactoryProvider");
            Object provider = Proxy.newProxyInstance(providerIface.getClassLoader(),
                    new Class<?>[] {providerIface}, new ZeroHandler("WlWebViewFactoryProviderStub"));
            cache.set(null, provider);
            System.err.println("[B8-WEBVIEW] WebViewFactory.sProviderInstance seeded (type-zero stub) "
                    + "— getProvider() short-circuits instead of throwing UnsupportedOperationException");
        } catch (Throwable t) {
            System.err.println("[B8-WEBVIEW] provider seed failed: " + t);
        }
    }

    /** Type-correct-zero handler: primitives->0/false, arrays->empty, interfaces->nested stub, else null. */
    private static final class ZeroHandler implements InvocationHandler {
        private final String label;
        ZeroHandler(String label) { this.label = label; }
        @Override
        public Object invoke(Object proxy, Method method, Object[] args) {
            String n = method.getName();
            if ("toString".equals(n)) return label;
            if ("hashCode".equals(n)) return Integer.valueOf(System.identityHashCode(proxy));
            if ("equals".equals(n)) return Boolean.valueOf(args != null && args.length == 1 && args[0] == proxy);
            Class<?> t = method.getReturnType();
            if (t == boolean.class) return Boolean.FALSE;
            if (t == int.class) return Integer.valueOf(0);
            if (t == long.class) return Long.valueOf(0L);
            if (t == void.class) return null;
            if (t.isArray()) return Array.newInstance(t.getComponentType(), 0);
            if (t.isInterface()) {
                try {
                    return Proxy.newProxyInstance(t.getClassLoader(), new Class<?>[] {t}, new ZeroHandler(label));
                } catch (Throwable ignore) {
                    return null;
                }
            }
            return null;
        }
    }
}
