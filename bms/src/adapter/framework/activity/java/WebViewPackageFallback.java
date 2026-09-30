/* J5 (#webview): single-purpose file (freeze unit) -- PM projection answers for the WebView provider. */
package adapter.core;

import android.content.pm.PackageInfo;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * J5 (#webview): the package-manager half of the WebView publication contract (JAVA-HANDOFF.md item 1).
 * WebViewFactory asks IPackageManager for the provider package and asks whether the platform has the
 * "android.software.webview" feature. OHOS has no such package/feature, so both fail. This chains an
 * IPackageManager proxy over ActivityThread.sPackageManager (same shape as AndroidFrameworkPackage,
 * installed after it) that answers, ONLY when a real provider APK is staged
 * (WestlakeWebViewInstall.isAvailable()):
 *   - getPackageInfo("com.android.webview")      -> WestlakeWebViewInstall.getSideloadedWebViewPackageInfo()
 *   - getApplicationInfo("com.android.webview")  -> that PackageInfo's applicationInfo
 *   - hasSystemFeature("android.software.webview") -> true
 * The same PackageInfo/identity/signature representation the webviewupdate service returns, so both
 * callers agree (handoff acceptance). Every other call passes through. When no provider APK is staged the
 * proxy is inert: hasSystemFeature stays false and the WebView package stays not-found.
 */
public final class WebViewPackageFallback {
    private static boolean sLogged;

    private WebViewPackageFallback() {}

    public static void install() {
        try {
            Class<?> activityThread = Class.forName("android.app.ActivityThread");
            Method getPm = activityThread.getDeclaredMethod("getPackageManager");
            getPm.setAccessible(true);
            final Object current = getPm.invoke(null);
            if (current == null) { log("not installed: getPackageManager() is null"); return; }
            Class<?> iface = Class.forName("android.content.pm.IPackageManager");
            Object proxy = Proxy.newProxyInstance(iface.getClassLoader(), new Class<?>[] { iface },
                    new InvocationHandler() {
                        @Override public Object invoke(Object p, Method m, Object[] a) throws Throwable {
                            String n = m.getName();
                            if ("asBinder".equals(n)) return ((android.os.IInterface) current).asBinder();
                            try {
                                if (WestlakeWebViewInstall.isAvailable()) {
                                    Object answer = answerWebView(n, a);
                                    if (answer != NOT_HANDLED) { note(n); return answer; }
                                }
                                return m.invoke(current, a);
                            } catch (InvocationTargetException e) {
                                throw e.getCause() != null ? e.getCause() : e;
                            }
                        }
                    });
            Field f = activityThread.getDeclaredField("sPackageManager");
            f.setAccessible(true);
            f.set(null, proxy);
            log("installed over " + current.getClass().getName());
        } catch (Throwable t) {
            log("not installed: " + t);
        }
    }

    private static final Object NOT_HANDLED = new Object();

    /** Provider answers for the three WebView calls; NOT_HANDLED for everything else. */
    private static Object answerWebView(String name, Object[] a) {
        if (a == null || a.length == 0 || !(a[0] instanceof String)) return NOT_HANDLED;
        String arg0 = (String) a[0];
        if ("getPackageInfo".equals(name) && WestlakeWebViewInstall.WEBVIEW_PACKAGE.equals(arg0)) {
            return WestlakeWebViewInstall.getSideloadedWebViewPackageInfo();
        }
        if ("getApplicationInfo".equals(name) && WestlakeWebViewInstall.WEBVIEW_PACKAGE.equals(arg0)) {
            PackageInfo pi = WestlakeWebViewInstall.getSideloadedWebViewPackageInfo();
            return pi != null ? pi.applicationInfo : NOT_HANDLED;
        }
        if ("hasSystemFeature".equals(name) && "android.software.webview".equals(arg0)) {
            return Boolean.valueOf(WestlakeWebViewInstall.isAvailable());
        }
        return NOT_HANDLED;
    }

    private static void note(String call) {
        if (sLogged) return;
        sLogged = true;
        log("answering WebView " + call + " for " + WestlakeWebViewInstall.WEBVIEW_PACKAGE);
    }

    private static void log(String m) {
        System.err.println("[B8-WEBVIEWPKG] " + m);
        System.err.flush();
    }
}
