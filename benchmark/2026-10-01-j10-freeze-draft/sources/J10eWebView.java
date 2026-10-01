/* J10e (#webview-delegate-cookiemanager): single-purpose file (freeze unit) -- enrich the route-A
 * WebViewFactoryProvider seed so (1) the ViewDelegate forwards View-level calls back to the real
 * WebView via WebView.PrivateAccess.super_* (so WebView.mLayoutParams / mFrame get set), and
 * (2) getCookieManager()/getWebStorage()/getGeolocationPermissions() return concrete empty instances
 * instead of null. Builds on J8 WebViewProviderFix (which only seeds a type-zero stub). */
package adapter.activity;

import android.webkit.CookieManager;
import android.webkit.ValueCallback;
import android.webkit.WebView;

import java.lang.reflect.Array;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * J10e cluster <b>webview-delegate / webview-cookiemanager</b>
 * (caniwebview, jslab, beecount, trickytripper; degeder-yam, vaults-randomlydie, paultirk-yatoo).
 *
 * <b>Why the J8 type-zero stub leaves apps dead:</b>
 * <ul>
 *   <li><b>ViewGroup NPE</b> (caniwebview/jslab/beecount/trickytripper): AOSP 14
 *       {@code WebView.java:2658-2659} {@code setLayoutParams(p)} only does
 *       {@code mProvider.getViewDelegate().setLayoutParams(p)}. The real Chromium ViewDelegate calls
 *       back {@code WebView.PrivateAccess.super_setLayoutParams(p)} ({@code WebView.java:2465-2466}
 *       -&gt; {@code WebView.super.setLayoutParams(p)}) to store it on the View. The J8
 *       {@code WebViewProviderFix.ZeroHandler} does nothing for void methods, so {@code WebView}'s
 *       {@code mLayoutParams} stays null and the parent layout NPEs
 *       ({@code ConstraintLayout.onViewAdded}/{@code generateLayoutParams(view.getLayoutParams())};
 *       {@code FrameLayout.measureChildWithMargins} reading {@code null.leftMargin}).</li>
 *   <li><b>CookieManager NPE</b> (degeder-yam/vaults-randomlydie/paultirk-yatoo):
 *       {@code WebViewFactoryProvider.getCookieManager()} ({@code WebViewFactoryProvider.java:127})
 *       returns the <b>abstract class</b> {@code CookieManager} (not an interface), so ZeroHandler's
 *       {@code else return null} hands back null and {@code CookieManager.getInstance()} usage NPEs.</li>
 * </ul>
 *
 * <b>Fix:</b> re-seed {@code WebViewFactory.sProviderInstance} with an enriched
 * {@code WebViewFactoryProvider} proxy that:
 * <ul>
 *   <li>{@code createWebView(webView, privateAccess)} -&gt; a {@code WebViewProvider} proxy whose
 *       {@code getViewDelegate()} is a forwarding {@code ViewDelegate}: for each method {@code m(args)}
 *       it invokes {@code privateAccess.super_<m>(args)} when {@code WebView.PrivateAccess} declares a
 *       public same-named {@code super_*} with identical parameter types (covers {@code setLayoutParams}
 *       -&gt; {@code super_setLayoutParams}, {@code setFrame} -&gt; {@code super_setFrame}, plus
 *       onHoverEvent/dispatchKeyEvent/performLongClick/requestFocus/... automatically); otherwise zero.</li>
 *   <li>{@code getCookieManager()} -&gt; a concrete empty {@link CookieManager} subclass
 *       ({@code acceptCookie}=true, {@code getCookie}=null, everything else no-op). The other
 *       abstract-returning getters (getWebStorage/getGeolocationPermissions/getTracingController/
 *       getServiceWorkerController) stay null: their public android.jar constructors are not accessible
 *       to a concrete subclass (the SDK narrows them from the AOSP-source {@code public}), and none is
 *       in the observed NPE corpus -- add a stub-backed subclass when a window surfaces one.</li>
 * </ul>
 * Markers: {@code [J10e-WEBVIEW] delegate forwards setLayoutParams} (first forward) and
 * {@code [J10e-WEBVIEW] CookieManager stub installed} (first getCookieManager).
 *
 * The proxies are reflection-only (no compile dep on WebViewFactoryProvider/WebViewProvider/ViewDelegate
 * /PrivateAccess). The three concrete managers compile against a compile-only {@code android.webkit}
 * stub set (CookieManager carries two {@code @hide @SystemApi} abstract methods -- {@code getCookie
 * (String,boolean)}, {@code hasCookies(boolean)} -- that the public android.jar omits; they MUST be
 * overridden or the runtime class stays abstract and {@code new} throws InstantiationException).
 */
public final class J10eWebView {
    private J10eWebView() {}

    private static volatile boolean sLoggedDelegate = false;
    private static volatile boolean sLoggedCookie = false;
    private static volatile CookieManager sCookie;

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
                if (sCookie == null) sCookie = new WlCookieManager();
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
                        new DelegateForward(privateAccess));
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

    /** ViewDelegate handler: forward m(args) -> PrivateAccess.super_m(args) when present. */
    private static final class DelegateForward implements InvocationHandler {
        private final Object privateAccess;
        DelegateForward(Object pa) { this.privateAccess = pa; }
        @Override public Object invoke(Object proxy, Method method, Object[] args) {
            String n = method.getName();
            if ("toString".equals(n)) return "WlViewDelegate";
            if ("hashCode".equals(n)) return Integer.valueOf(System.identityHashCode(proxy));
            if ("equals".equals(n)) return Boolean.valueOf(args != null && args.length == 1 && args[0] == proxy);
            if (privateAccess != null) {
                try {
                    Method sup = privateAccess.getClass().getMethod("super_" + n, method.getParameterTypes());
                    Object r = sup.invoke(privateAccess, args);
                    if ("setLayoutParams".equals(n) && !sLoggedDelegate) {
                        sLoggedDelegate = true;
                        System.err.println("[J10e-WEBVIEW] delegate forwards setLayoutParams");
                    }
                    return r;
                } catch (NoSuchMethodException noSuper) {
                    // no super_<n> counterpart -> fall through to zero
                } catch (Throwable t) {
                    // defensive: never let the delegate throw into the parent layout path
                }
            }
            return zero(method.getReturnType());
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

    /** Concrete empty CookieManager (16 abstract methods, incl. the two @hide @SystemApi ones). */
    static final class WlCookieManager extends CookieManager {
        @Override public void setAcceptCookie(boolean accept) {}
        @Override public boolean acceptCookie() { return true; }
        @Override public void setAcceptThirdPartyCookies(WebView webview, boolean accept) {}
        @Override public boolean acceptThirdPartyCookies(WebView webview) { return false; }
        @Override public void setCookie(String url, String value) {}
        @Override public void setCookie(String url, String value, ValueCallback<Boolean> callback) {}
        @Override public String getCookie(String url) { return null; }
        @Override public String getCookie(String url, boolean privateBrowsing) { return null; } // @hide
        @Override public void removeSessionCookie() {}
        @Override public void removeSessionCookies(ValueCallback<Boolean> callback) {}
        @Override public void removeAllCookie() {}
        @Override public void removeAllCookies(ValueCallback<Boolean> callback) {}
        @Override public boolean hasCookies() { return false; }
        @Override public boolean hasCookies(boolean privateBrowsing) { return false; } // @hide
        @Override public void removeExpiredCookie() {}
        @Override public void flush() {}
    }
}
