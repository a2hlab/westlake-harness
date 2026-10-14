/* J7b (#fd-catima): single-purpose file (freeze unit) -- local no-op "search" service. */
package adapter.compat;

import android.os.Binder;
import android.os.IBinder;
import android.os.IInterface;
import java.lang.reflect.Array;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * J7b (#fd-catima): after AppWidgetFetcher clears the getInstance NPE, catima reaches SearchManager, whose
 * static init does ISearchManager.Stub.asInterface(ServiceManager.getService("search")); OHServiceManager
 * returns null for "search" so getServiceOrThrow throws ServiceNotFoundException "search"
 * (IllegalStateException). Publish a local no-op ISearchManager under "search" in ServiceManager.sCache so
 * asInterface's queryLocalInterface returns the proxy and SearchManager initialises. Same sCache-binder shape
 * as WlMediaRouter/WlMediaSession.
 */
public final class WlSearchService {

    private static final String SERVICE = "search";                    // Context.SEARCH_SERVICE
    private static final String IFACE = "android.app.ISearchManager";

    private WlSearchService() {}

    static final class LocalBinder extends Binder {}

    /** No-ops every ISearchManager method: void/object -> null, primitive -> 0/false, array -> empty. */
    static final class Inert implements InvocationHandler {
        private final IBinder binder;
        Inert(IBinder binder) { this.binder = binder; }
        @Override
        public Object invoke(Object proxy, Method method, Object[] args) {
            String n = method.getName();
            if ("asBinder".equals(n)) return binder;
            if ("toString".equals(n)) return "WlSearchManagerService";
            if ("hashCode".equals(n)) return Integer.valueOf(System.identityHashCode(proxy));
            if ("equals".equals(n)) return Boolean.valueOf(args != null && args.length == 1 && args[0] == proxy);
            Class<?> t = method.getReturnType();
            if (t == void.class) return null;
            if (t == boolean.class) return Boolean.FALSE;
            if (t == int.class || t == short.class || t == byte.class || t == char.class) return Integer.valueOf(0);
            if (t == long.class) return Long.valueOf(0L);
            if (t == float.class) return Float.valueOf(0f);
            if (t == double.class) return Double.valueOf(0d);
            if (t.isArray()) return Array.newInstance(t.getComponentType(), 0);
            return null;
        }
    }

    public static String install() {
        try {
            ClassLoader loader = WlSearchService.class.getClassLoader();
            Class<?> iface = Class.forName(IFACE, false, loader);
            Class<?> ibinder = Class.forName("android.os.IBinder", false, loader);
            LocalBinder binder = new LocalBinder();
            Object svc = Proxy.newProxyInstance(loader, new Class<?>[] { iface, ibinder }, new Inert(binder));
            binder.attachInterface((IInterface) svc, IFACE);

            Class<?> sm = Class.forName("android.os.ServiceManager", false, loader);
            java.lang.reflect.Field f = sm.getDeclaredField("sCache");
            f.setAccessible(true);
            Object value = f.get(null);
            if (!(value instanceof java.util.Map)) return "sCache is not a Map";
            @SuppressWarnings("unchecked")
            java.util.Map<String, IBinder> cache = (java.util.Map<String, IBinder>) value;
            if (cache.get(SERVICE) != null) return "already present";
            cache.put(SERVICE, binder);
            IInterface readback = binder.queryLocalInterface(IFACE);
            boolean ok = readback != null && iface.isInstance(readback) && readback.asBinder() == binder;
            return "installed search, queryLocalInterface=" + (ok ? "OK" : "WRONG");
        } catch (Throwable t) {
            return "FAILED: " + t.getClass().getName() + ": " + t.getMessage();
        }
    }
}
