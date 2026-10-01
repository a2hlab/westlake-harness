/* U11 (#apex-services, phone cluster): single-purpose file (freeze unit) -- PHONE + telephony_subscription
 * SystemServiceRegistry fetchers. New feature, new file; no frozen file touched. */
package adapter.activity;

import java.lang.reflect.Array;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.Map;

/**
 * U11 (#apex-services): route-A ships a STOCK android.app.SystemServiceRegistry whose apex
 * TelephonyFrameworkInitializer.registerServiceWrappers() runs and registers "phone" ->
 * {@code new TelephonyManager(ctx)} (fetcher = SystemServiceRegistry$140). On this OH build that fetcher
 * nevertheless resolves to null (same class as the WIFI_SERVICE null-producer already handled by
 * {@link WifiFetcher}), so an app that does {@code getSystemService("phone") as TelephonyManager} (x =
 * com.twitter.util.telephony, an R8/Kotlin not-null cast) NPEs. Mirror WifiFetcher: replace the "phone" and
 * "telephony_subscription_service" fetchers with ones that build a NON-NULL manager by allocating it WITHOUT
 * its constructor (the ctor would reach SubscriptionManager/service-manager paths), and back it with a
 * present-but-off local binder (no SIM, empty identifiers -- nothing fabricated, same floor as account/
 * location). Registration follows AOSP 14 TelephonyFrameworkInitializer (phone -> TelephonyManager,
 * telephony_subscription_service -> SubscriptionManager). Self-contained reflection helpers.
 *
 * Present-but-off (NOT fabricated): the ITelephony/ISub stub returns type-zero -- getDeviceId()/getSimOperator()
 * /line1Number() -> null (no fake IMEI/number/operator), getSimState()/getPhoneType()/getCallState()/
 * getDataState() -> 0 (UNKNOWN / PHONE_TYPE_NONE / IDLE / DISCONNECTED), isNetworkRoaming()/hasIccCard() ->
 * false. Honest "no telephony hardware", so an app takes its no-service branch instead of crashing.
 */
public final class TelephonyFetcher {

    private TelephonyFetcher() {}

    private static final int DEFAULT_SUBSCRIPTION_ID = Integer.MAX_VALUE; // AOSP SubscriptionManager default

    public static void install() {
        // Best-effort: make getITelephony()/getSubscriptionService() resolve to a present-but-off stub so
        // CALLS (toutiao: 15 phone + subscription) answer type-zero instead of NPEing. Must run before the
        // managers are first used; failure here still leaves a non-null manager (clears the cast wall).
        seedSafeBinder("phone", "com.android.internal.telephony.ITelephony", "WlTelephonyStub");
        seedSafeBinder("isub", "com.android.internal.telephony.ISub", "WlSubStub");
        ensureTelephonyServiceManager();

        replaceFetcher("phone", new Builder() {
            @Override public Object build(Object context) throws Throwable {
                return buildManager("android.telephony.TelephonyManager", context, true);
            }
        });
        replaceFetcher("telephony_subscription_service", new Builder() {
            @Override public Object build(Object context) throws Throwable {
                return buildManager("android.telephony.SubscriptionManager", context, false);
            }
        });
    }

    /** Allocate a manager WITHOUT its ctor; set mContext (+ mSubId for TelephonyManager). Non-null by design. */
    private static Object buildManager(String className, Object context, boolean isTelephony) throws Throwable {
        Class<?> mgr = Class.forName(className);
        Object instance = allocateInstance(mgr);
        trySetField(instance, "mContext", context);
        if (isTelephony) {
            trySetField(instance, "mSubId", Integer.valueOf(DEFAULT_SUBSCRIPTION_ID));
        }
        System.err.println("[B8-FETCH] " + (isTelephony ? "phone TelephonyManager" : "telephony_subscription_service SubscriptionManager")
                + " allocated (non-null)");
        return instance;
    }

    /**
     * Publish a present-but-off binder for {@code serviceName} into ServiceManager.sCache. getITelephony()/
     * getSubscriptionService() reach it via TelephonyServiceManager.ServiceRegisterer.get() ->
     * ServiceManager.getService(name) -> IInterface.Stub.asInterface(binder), which first tries
     * binder.queryLocalInterface(descriptor). Our Binder returns a type-zero Proxy of the service interface,
     * so asInterface returns it directly (no transact). Absent interface -> skip (bare non-null manager still
     * clears the cast wall), exactly like WifiFetcher's IWifiManager-absent path.
     */
    private static void seedSafeBinder(String serviceName, String ifaceName, String label) {
        try {
            final Class<?> iface = Class.forName(ifaceName);
            final Object[] localIface = new Object[1];
            // a Binder whose queryLocalInterface(anything) returns our type-zero service proxy
            android.os.Binder binder = new android.os.Binder() {
                @Override public android.os.IInterface queryLocalInterface(String descriptor) {
                    return (android.os.IInterface) localIface[0];
                }
            };
            Object proxy = Proxy.newProxyInstance(iface.getClassLoader(), new Class<?>[] {iface},
                    new ZeroHandler(label, binder));
            localIface[0] = proxy;
            putServiceCache(serviceName, binder);
            System.err.println("[B8-FETCH] " + serviceName + " present-but-off binder seeded (" + label + ")");
        } catch (ClassNotFoundException noIface) {
            System.err.println("[B8-FETCH] " + serviceName + " " + ifaceName + " absent on this build; bare non-null manager");
        } catch (Throwable t) {
            System.err.println("[B8-FETCH] " + serviceName + " binder seed failed: " + t);
        }
    }

    /** getITelephony() dereferences TelephonyFrameworkInitializer.getTelephonyServiceManager(); if null it NPEs
     *  before reaching ServiceManager. Set a default instance when the framework left it null. Best-effort. */
    private static void ensureTelephonyServiceManager() {
        try {
            Class<?> tfi = Class.forName("android.telephony.TelephonyFrameworkInitializer");
            Method get = tfi.getMethod("getTelephonyServiceManager");
            Object cur = get.invoke(null);
            if (cur == null) {
                Class<?> tsm = Class.forName("android.os.TelephonyServiceManager");
                Object fresh;
                try { fresh = tsm.getDeclaredConstructor().newInstance(); }
                catch (Throwable noCtor) { fresh = allocateInstance(tsm); }
                Method set = tfi.getMethod("setTelephonyServiceManager", tsm);
                set.invoke(null, fresh);
                System.err.println("[B8-FETCH] TelephonyServiceManager was null; default installed");
            }
        } catch (Throwable t) {
            System.err.println("[B8-FETCH] ensureTelephonyServiceManager skipped: " + t);
        }
    }

    @SuppressWarnings("unchecked")
    private static void putServiceCache(String name, android.os.IBinder binder) throws Throwable {
        Class<?> sm = Class.forName("android.os.ServiceManager");
        Field cacheField = sm.getDeclaredField("sCache");
        cacheField.setAccessible(true);
        Map<String, android.os.IBinder> cache = (Map<String, android.os.IBinder>) cacheField.get(null);
        cache.put(name, binder);
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

    /** Type-correct-zero handler: primitives->0/false, arrays->empty, interfaces->nested stub, else null.
     *  asBinder() returns the backing Binder so IInterface.asBinder() stays consistent. */
    private static final class ZeroHandler implements InvocationHandler {
        private final String label;
        private final android.os.IBinder binder;
        ZeroHandler(String label, android.os.IBinder binder) { this.label = label; this.binder = binder; }
        @Override
        public Object invoke(Object proxy, Method method, Object[] args) {
            String n = method.getName();
            if ("asBinder".equals(n)) return binder != null ? binder : new android.os.Binder();
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
                    return Proxy.newProxyInstance(t.getClassLoader(), new Class<?>[] {t}, new ZeroHandler(label, binder));
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
