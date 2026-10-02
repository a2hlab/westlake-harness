package adapter.activity;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * Makes androidx.webkit find org.chromium.support_lib_glue.SupportLibReflectionUtil (2026-10-03-u13-java-walls-2).
 *
 * androidx.webkit loads that class with {@code Class.forName(name, false, WebView.getWebViewClassLoader())}, and
 * WebView.getWebViewClassLoader() is WebViewFactoryProvider.getWebViewClassLoader() of the seeded provider. J10e's
 * provider is a java.lang.reflect.Proxy whose handler does not answer that method, so the lookup reaches no loader
 * that has the glue and androidx falls back to an empty feature list.
 *
 * install() runs right after J10eWebView/J10gWebExtras.install(): it re-wraps WebViewFactory.sProviderInstance in a
 * Proxy that answers getWebViewClassLoader() with this runtime's class loader (which holds the glue) and forwards
 * every other call to the J10e handler unchanged. If the provider is not a Proxy, or anything fails, nothing
 * changes.
 */
public final class WebkitSupportGlue {
    private WebkitSupportGlue() {}

    public static void install() {
        try {
            Class<?> factory = Class.forName("android.webkit.WebViewFactory");
            Field f = factory.getDeclaredField("sProviderInstance");
            f.setAccessible(true);
            Object provider = f.get(null);
            if (provider == null || !Proxy.isProxyClass(provider.getClass())) {
                System.err.println("[WEBKIT-GLUE] provider is not the J10e proxy; unchanged");
                return;
            }
            final InvocationHandler inner = Proxy.getInvocationHandler(provider);
            final ClassLoader glueLoader = WebkitSupportGlue.class.getClassLoader();
            Class<?> iface = Class.forName("android.webkit.WebViewFactoryProvider");
            Object wrapped = Proxy.newProxyInstance(iface.getClassLoader(), new Class<?>[] {iface},
                    new InvocationHandler() {
                        @Override
                        public Object invoke(Object proxy, Method m, Object[] args) throws Throwable {
                            if ("getWebViewClassLoader".equals(m.getName()) && (args == null || args.length == 0)) {
                                return glueLoader;
                            }
                            return inner.invoke(proxy, m, args);
                        }
                    });
            f.set(null, wrapped);
            System.err.println("[WEBKIT-GLUE] getWebViewClassLoader -> runtime loader (support_lib_glue visible)");
        } catch (Throwable t) {
            System.err.println("[WEBKIT-GLUE] install failed: " + t);
        }
    }
}
