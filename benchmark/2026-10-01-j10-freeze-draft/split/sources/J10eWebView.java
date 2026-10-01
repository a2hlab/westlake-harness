/* J10e (#webview-provider-seed): single-purpose freeze unit -- the enriched WebViewFactoryProvider SEED
 * and its routing. Re-seeds WebViewFactory.sProviderInstance (replacing the J8 type-zero stub) and routes
 * each provider getter to the per-fix freeze units: createWebView.getViewDelegate -> J10eViewDelegate,
 * getCookieManager -> J10eCookieManager, getSettings -> J10fWebSettings, the other android.webkit
 * abstract-class getters -> J10gWebExtras. Split so each fix is its own file (behaviour unchanged). */
package adapter.activity;

import java.lang.reflect.Array;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

public final class J10eWebView {
    private J10eWebView() {}

    private static volatile boolean sLoggedCookie = false;
    private static volatile android.webkit.CookieManager sCookie;

    /** Re-seed {@code WebViewFactory.sProviderInstance} with the enriched provider, replacing the J8
     *  type-zero stub. Idempotent: no-op if our enriched provider is already seeded. Injected right
     *  after the J8 {@code WebViewProviderFix.install()} call site. */
    public static void install() {
        try {
            Class<?> factory = Class.forName("android.webkit.WebViewFactory");
            java.lang.reflect.Field cache = factory.getDeclaredField("sProviderInstance");
            cache.setAccessible(true);
            Object cur = cache.get(null);
            if (cur != null && Proxy.isProxyClass(cur.getClass())
                    && Proxy.getInvocationHandler(cur) instanceof ProviderEnrich) {
                return; // already enriched
            }
            Class<?> providerIface = Class.forName("android.webkit.WebViewFactoryProvider");
            Object provider = Proxy.newProxyInstance(providerIface.getClassLoader(),
                    new Class<?>[] {providerIface}, new ProviderEnrich());
            cache.set(null, provider);
            System.err.println("[J10e-WEBVIEW] enriched WebViewFactoryProvider seeded "
                    + "(forwarding ViewDelegate + concrete CookieManager + J10g extras)");
        } catch (Throwable t) {
            System.err.println("[J10e-WEBVIEW] install failed: " + t);
        }
        // J10g: seed WebViewFactory.sPackageInfo (getCurrentWebViewPackage non-null). Idempotent.
        try { J10gWebExtras.install(); } catch (Throwable t) { System.err.println("[J10g-WEBVIEW] install failed: " + t); }
    }

    /** Top-level WebViewFactoryProvider handler. */
    private static final class ProviderEnrich implements InvocationHandler {
        @Override public Object invoke(Object proxy, Method method, Object[] args) {
            String n = method.getName();
            if ("toString".equals(n)) return "WlEnrichedWebViewFactoryProvider";
            if ("hashCode".equals(n)) return Integer.valueOf(System.identityHashCode(proxy));
            if ("equals".equals(n)) return Boolean.valueOf(args != null && args.length == 1 && args[0] == proxy);
            if ("createWebView".equals(n)) {
                Object privateAccess = (args != null && args.length >= 2) ? args[1] : null;
                Class<?> wvp = method.getReturnType(); // android.webkit.WebViewProvider
                return Proxy.newProxyInstance(wvp.getClassLoader(), new Class<?>[] {wvp},
                        new ProviderInstance(privateAccess));
            }
            if ("getCookieManager".equals(n)) {
                if (sCookie == null) sCookie = new J10eCookieManager();
                if (!sLoggedCookie) { sLoggedCookie = true;
                    System.err.println("[J10e-WEBVIEW] CookieManager stub installed"); }
                return sCookie;
            }
            // J10g: every other WebViewFactoryProvider getter that returns an android.webkit abstract
            // class gets a concrete empty instance (ServiceWorkerController/TracingController/
            // TokenBindingService/WebStorage/GeolocationPermissions). getStatics() stays a zero proxy
            // (it is an interface, handled by zero()).
            try {
                switch (n) {
                    case "getServiceWorkerController": J10gWebExtras.logOnce(); return J10gWebExtras.getServiceWorkerController();
                    case "getTracingController":       J10gWebExtras.logOnce(); return J10gWebExtras.getTracingController();
                    case "getTokenBindingService":     J10gWebExtras.logOnce(); return J10gWebExtras.getTokenBindingService();
                    case "getWebStorage":              J10gWebExtras.logOnce(); return J10gWebExtras.getWebStorage();
                    case "getGeolocationPermissions":  J10gWebExtras.logOnce(); return J10gWebExtras.getGeolocationPermissions();
                    default: break;
                }
            } catch (Throwable t) {
                System.err.println("[J10g-WEBVIEW] " + n + " failed: " + t);
            }
            return zero(method.getReturnType());
        }
    }

    /** WebViewProvider instance handler: forwards getViewDelegate to a forwarding ViewDelegate. */
    private static final class ProviderInstance implements InvocationHandler {
        private final Object privateAccess;
        ProviderInstance(Object pa) { this.privateAccess = pa; }
        @Override public Object invoke(Object proxy, Method method, Object[] args) {
            String n = method.getName();
            if ("toString".equals(n)) return "WlWebViewProvider";
            if ("hashCode".equals(n)) return Integer.valueOf(System.identityHashCode(proxy));
            if ("equals".equals(n)) return Boolean.valueOf(args != null && args.length == 1 && args[0] == proxy);
            if ("getViewDelegate".equals(n)) {
                Class<?> vd = method.getReturnType(); // android.webkit.WebViewProvider$ViewDelegate
                return Proxy.newProxyInstance(vd.getClassLoader(), new Class<?>[] {vd},
                        new J10eViewDelegate(privateAccess));
            }
            if ("getSettings".equals(n)) {
                // J10f: WebViewProvider.getSettings() returns the abstract class WebSettings; route-A
                // WebView apps call getSettings().setJavaScriptEnabled(..) at launch, so a null here is
                // fatal. Hand back a concrete WlWebSettings.
                try { return J10fWebSettings.get(); }
                catch (Throwable t) { System.err.println("[J10f-WEBVIEW] getSettings failed: " + t); }
            }
            return zero(method.getReturnType()); // getScrollDelegate() and the rest
        }
    }

    /** Type-correct-zero: primitives->0/false, void->null, array->empty, interface->nested zero, else null. */
    static Object zero(Class<?> t) {
        if (t == boolean.class) return Boolean.FALSE;
        if (t == int.class) return Integer.valueOf(0);
        if (t == long.class) return Long.valueOf(0L);
        if (t == void.class) return null;
        if (t.isArray()) return Array.newInstance(t.getComponentType(), 0);
        if (t.isInterface()) {
            try { return Proxy.newProxyInstance(t.getClassLoader(), new Class<?>[] {t}, new ZeroH()); }
            catch (Throwable ignore) { return null; }
        }
        return null;
    }

    private static final class ZeroH implements InvocationHandler {
        @Override public Object invoke(Object proxy, Method m, Object[] a) {
            String n = m.getName();
            if ("toString".equals(n)) return "WlZero";
            if ("hashCode".equals(n)) return Integer.valueOf(System.identityHashCode(proxy));
            if ("equals".equals(n)) return Boolean.valueOf(a != null && a.length == 1 && a[0] == proxy);
            return zero(m.getReturnType());
        }
    }
}
