/* J7 (#fd-wifianalyzer): single-purpose file (freeze unit) -- WIFI_SERVICE fetcher. */
package adapter.activity;

import java.lang.reflect.Array;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.Map;

/**
 * J7 (#fd-wifianalyzer): route-A's SystemServiceRegistry WIFI_SERVICE fetcher returns null, so
 * com.vrem.wifianalyzer.MainActivity.onCreate does {@code getSystemService("wifi").getClass()} (an R8/Kotlin
 * not-null check on the result) on null and NPEs (NULL-PRODUCERS.md: getSystemService("wifi") -> null).
 * Allocate a WifiManager without its constructor (which would asInterface a null binder) and set its
 * IWifiManager mService to a type-zero stub so getSystemService(WIFI_SERVICE) is non-null and its calls
 * answer type-zero (empty scan results / false) instead of NPEing. Self-contained reflection helpers.
 */
public final class WifiFetcher {

    private WifiFetcher() {}

    public static void install() {
        replaceFetcher("wifi", new Builder() {
            @Override public Object build(Object context) throws Throwable { return buildWifiManager(context); }
        });
    }

    /** WifiManager (allocated) whose IWifiManager mService is a type-zero stub. */
    private static Object buildWifiManager(Object context) throws Throwable {
        // J7b (board 02:19): android.net.wifi.WifiManager IS in the boot class path (adapter-mainline-stubs),
        // but the hidden service interface android.net.wifi.IWifiManager is NOT on this OH build (J7 failed with
        // ClassNotFoundException IWifiManager). So allocate a bare WifiManager (enough to clear fd-wifianalyzer's
        // getSystemService("wifi").getClass() not-null check) and set mService ONLY if IWifiManager exists.
        Class<?> wm = Class.forName("android.net.wifi.WifiManager");
        Object instance = allocateInstance(wm);
        trySetField(instance, "mContext", context);
        try {
            Class<?> iwifi = Class.forName("android.net.wifi.IWifiManager");
            Object service = Proxy.newProxyInstance(iwifi.getClassLoader(), new Class<?>[] {iwifi},
                    new ZeroHandler("WlWifiManagerStub"));
            trySetField(instance, "mService", service);
        } catch (ClassNotFoundException noIface) {
            System.err.println("[B8-FETCH] wifi IWifiManager absent on this build; bare WifiManager (non-null only)");
        }
        try { trySetField(instance, "mLooper", Class.forName("android.os.Looper")
                .getMethod("getMainLooper").invoke(null)); } catch (Throwable ignore) { }
        System.err.println("[B8-FETCH] wifi WifiManager allocated (non-null)");
        return instance;
    }

    private static Object allocateInstance(Class<?> type) throws Throwable {
        Class<?> unsafeClass = Class.forName("sun.misc.Unsafe");
        Field theUnsafe = unsafeClass.getDeclaredField("theUnsafe");
        theUnsafe.setAccessible(true);
        Object unsafe = theUnsafe.get(null);
        Method allocate = unsafeClass.getMethod("allocateInstance", Class.class);
        return allocate.invoke(unsafe, type);
    }

    private static void setField(Object obj, String name, Object value) throws Throwable {
        for (Class<?> c = obj.getClass(); c != null; c = c.getSuperclass()) {
            try {
                Field f = c.getDeclaredField(name);
                f.setAccessible(true);
                f.set(obj, value);
                return;
            } catch (NoSuchFieldException ignore) {
            }
        }
        throw new NoSuchFieldException(name + " on " + obj.getClass().getName());
    }

    private static void trySetField(Object obj, String name, Object value) {
        try { setField(obj, name, value); } catch (Throwable ignore) { }
    }

    private interface Builder {
        Object build(Object context) throws Throwable;
    }

    /** Type-correct-zero handler: primitives->0/false, arrays->empty, interfaces->nested stub, else null. */
    private static final class ZeroHandler implements InvocationHandler {
        private final String label;
        ZeroHandler(String label) { this.label = label; }
        @Override
        public Object invoke(Object proxy, Method method, Object[] args) {
            String n = method.getName();
            if ("asBinder".equals(n)) return new android.os.Binder();
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

    @SuppressWarnings("unchecked")
    private static void replaceFetcher(final String name, final Builder builder) {
        try {
            Class<?> ssr = Class.forName("android.app.SystemServiceRegistry");
            Class<?> fetcherIface = Class.forName("android.app.SystemServiceRegistry$ServiceFetcher");
            Object proxy = Proxy.newProxyInstance(ssr.getClassLoader(), new Class<?>[] {fetcherIface},
                    new InvocationHandler() {
                        private Object cached;
                        @Override
                        public synchronized Object invoke(Object p, Method m, Object[] a) {
                            if (!"getService".equals(m.getName())) {
                                Class<?> rt = m.getReturnType();
                                if (rt == int.class) return Integer.valueOf(0);
                                if (rt == boolean.class) return Boolean.FALSE;
                                return null;
                            }
                            if (cached != null) return cached;
                            try {
                                cached = builder.build(a != null && a.length > 0 ? a[0] : null);
                            } catch (Throwable t) {
                                System.err.println("[B8-FETCH] " + name + " build failed: " + t);
                                return null;
                            }
                            return cached;
                        }
                    });
            Field f = ssr.getDeclaredField("SYSTEM_SERVICE_FETCHERS");
            f.setAccessible(true);
            Map<String, Object> fetchers = (Map<String, Object>) f.get(null);
            Object prev = fetchers.put(name, proxy);
            System.err.println("[B8-FETCH] " + name + " fetcher replaced (prev="
                    + (prev == null ? "null" : prev.getClass().getName()) + ")");
        } catch (Throwable t) {
            System.err.println("[B8-FETCH] " + name + " fetcher replace failed: " + t);
        }
    }
}
