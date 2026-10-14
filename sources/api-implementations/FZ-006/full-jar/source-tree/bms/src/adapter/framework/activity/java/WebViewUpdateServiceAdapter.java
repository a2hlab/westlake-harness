/* J5b (#webview): single-purpose file (freeze unit) -- the class N3b's native prime/publish resolves by name. */
package adapter.core;

import android.content.pm.PackageInfo;
import android.os.Binder;
import android.os.IInterface;

import java.lang.reflect.Array;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * J5b (#webview): the exact class N3b's runtime (7c9c6240) native prime/publish resolves BY NAME.
 * webview_publication.cpp does:
 *   FindClass("adapter/core/WebViewUpdateServiceAdapter")
 *   CallStaticBooleanMethod(isAvailable, "()Z")
 *   CallStaticObjectMethod(getInstance, "()Ladapter/core/WebViewUpdateServiceAdapter;")
 *   ServiceManager.sCache.put(WebViewFactory.WEBVIEW_UPDATE_SERVICE_NAME, <getInstance()>)  // native seeds
 *   then get()/public getService() readback must be the SAME object.
 * So getInstance() must return an IBinder (the cache is Map<String,IBinder> and getService returns it),
 * and the NATIVE -- not Java -- seeds the cache with the exact WEBVIEW_UPDATE_SERVICE_NAME String object
 * (a Java-side put with a freshly-allocated "webviewupdate" key can miss under the ART String/ArrayMap
 * defect the cpp documents). J5's first cut only shipped WestlakeWebViewInstall with an anonymous proxy
 * and a Java-side route, so this class was absent from the DEX (cx-bms webview-contract-gap.json,
 * definition_found=false) and native prime aborted at FindClass.
 *
 * It cannot extend the hidden IWebViewUpdateService.Stub (absent from the compile android.jar), so it
 * extends the public android.os.Binder and attaches a reflective IWebViewUpdateService proxy: WebViewFactory
 * does IWebViewUpdateService.Stub.asInterface(getService(name)) -> queryLocalInterface -> this proxy.
 * isAvailable() gates on a real provider APK (WestlakeWebViewInstall.getSideloadedWebViewPackageInfo()).
 */
public final class WebViewUpdateServiceAdapter extends Binder {
    private static final String IFACE = "android.webkit.IWebViewUpdateService";
    private static final WebViewUpdateServiceAdapter INSTANCE = new WebViewUpdateServiceAdapter();

    private WebViewUpdateServiceAdapter() {
        try {
            ClassLoader cl = WebViewUpdateServiceAdapter.class.getClassLoader();
            Class<?> iface = Class.forName(IFACE, false, cl);
            Object proxy = Proxy.newProxyInstance(cl, new Class<?>[] { iface }, new Handler(this, cl));
            attachInterface((IInterface) proxy, IFACE);
        } catch (Throwable t) {
            System.err.println("[B8-WEBVIEW] WebViewUpdateServiceAdapter proxy not attached: " + t);
        }
    }

    /** Called by native prime BY NAME: true only when a real provider APK is staged. */
    public static boolean isAvailable() {
        return WestlakeWebViewInstall.getSideloadedWebViewPackageInfo() != null;
    }

    /** Called by native prime BY NAME: the singleton IBinder the native seeds into the sCache. */
    public static WebViewUpdateServiceAdapter getInstance() {
        return INSTANCE;
    }

    /** Answers the IWebViewUpdateService methods WebViewFactory calls (via the attached proxy). */
    private static final class Handler implements InvocationHandler {
        private final Binder binder;
        private final ClassLoader loader;
        Handler(Binder binder, ClassLoader loader) { this.binder = binder; this.loader = loader; }

        @Override
        public Object invoke(Object proxy, Method method, Object[] args) {
            String n = method.getName();
            if ("asBinder".equals(n)) return binder;
            if ("toString".equals(n)) return "WestlakeWebViewUpdateService";
            if ("hashCode".equals(n)) return Integer.valueOf(System.identityHashCode(proxy));
            if ("equals".equals(n)) return Boolean.valueOf(args != null && args.length == 1 && args[0] == proxy);
            if ("getCurrentWebViewPackage".equals(n)) return WestlakeWebViewInstall.getSideloadedWebViewPackageInfo();
            if ("getCurrentWebViewPackageName".equals(n) || "changeProviderAndSetting".equals(n)) {
                PackageInfo pi = WestlakeWebViewInstall.getSideloadedWebViewPackageInfo();
                return pi != null ? pi.packageName : null;
            }
            if ("waitForAndGetProvider".equals(n)) return buildProviderResponse();
            if ("isMultiProcessEnabled".equals(n)) return Boolean.FALSE;
            Class<?> t = method.getReturnType();
            if (t == void.class) return null;
            if (t == boolean.class) return Boolean.FALSE;
            if (t == int.class || t == short.class || t == byte.class || t == char.class) return Integer.valueOf(0);
            if (t == long.class) return Long.valueOf(0L);
            if (t.isArray()) return Array.newInstance(t.getComponentType(), 0);
            return null;
        }

        /** new WebViewProviderResponse(pi, pi != null ? 0 : 4) via reflection (LIBLOAD_SUCCESS / _NULL). */
        private Object buildProviderResponse() {
            try {
                PackageInfo pi = WestlakeWebViewInstall.getSideloadedWebViewPackageInfo();
                Class<?> resp = Class.forName("android.webkit.WebViewProviderResponse", false, loader);
                for (Constructor<?> c : resp.getDeclaredConstructors()) {
                    Class<?>[] p = c.getParameterTypes();
                    if (p.length == 2 && p[0] == PackageInfo.class && p[1] == int.class) {
                        c.setAccessible(true);
                        return c.newInstance(pi, pi != null ? 0 : 4);
                    }
                }
            } catch (Throwable ignore) { /* fall through */ }
            return null;
        }
    }
}
