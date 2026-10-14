/* J4 (#noice): single-purpose file (freeze unit) -- a local IMediaRouterService so MediaRouter builds. */
package adapter.compat;

import android.os.Binder;
import android.os.IBinder;
import android.os.IInterface;

import java.lang.reflect.Array;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * B8 (#noice, J4): getSystemService(MEDIA_ROUTER_SERVICE) builds an android.media.MediaRouter whose
 * Static.&lt;init&gt; does IMediaRouterService.Stub.asInterface(ServiceManager.getService("media_router"))
 * and immediately rebindAsUser -&gt; mMediaRouterService.registerClientAsUser(...). route-A's
 * OHServiceManager returns null for "media_router", so mMediaRouterService is null and
 * registerClientAsUser NPEs before Noice's SystemMediaRouteProvider (and thus its player UI) is built
 * (J3 hilog: MediaRouter.java:451 rebindAsUser -&gt; NPE on a null IMediaRouterService).
 *
 * Same shape as WlMediaSession: put a LocalBinder carrying a no-op IMediaRouterService proxy into
 * ServiceManager.sCache under "media_router", so asInterface's queryLocalInterface returns the proxy
 * and every IMediaRouterService call (registerClientAsUser, setDiscoveryRequest, getState, ...) is a
 * harmless no-op. Its own file (added class, freeze unit) so it can freeze independently of
 * WlMediaSession. Idempotent: skips if a "media_router" binder is already cached.
 */
public final class WlMediaRouter {
    private static final String SERVICE = "media_router";                 // Context.MEDIA_ROUTER_SERVICE
    private static final String IFACE = "android.media.IMediaRouterService";

    private WlMediaRouter() {}

    static final class LocalBinder extends Binder {}

    /** No-ops every IMediaRouterService method: void/object -> null, primitive -> 0/false, array -> empty. */
    static final class Inert implements InvocationHandler {
        private final IBinder binder;
        Inert(IBinder binder) { this.binder = binder; }

        @Override
        public Object invoke(Object proxy, Method method, Object[] args) {
            String n = method.getName();
            if ("asBinder".equals(n)) return binder;
            if ("toString".equals(n)) return "WlMediaRouterService";
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
            ClassLoader loader = WlMediaRouter.class.getClassLoader();
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
            return "installed media_router, queryLocalInterface=" + (ok ? "OK" : "WRONG");
        } catch (Throwable t) {
            return "FAILED: " + t.getClass().getName() + ": " + t.getMessage();
        }
    }
}
