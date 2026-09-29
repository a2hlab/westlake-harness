/* r17e (#alarm/#vibrator): SystemServiceRegistry fetcher replacements binder -> Manager. */
package adapter.activity;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.Map;

/**
 * B8 (#alarm/#vibrator/r17e): route-A's SystemServiceRegistry keeps the stock fetchers, which either
 * do not consume our in-process binder (ALARM_SERVICE returns null -> k9/fd-android
 * AndroidAlarmManager.<init> NPE) or return a Manager whose array API is null (VIBRATOR_MANAGER_SERVICE
 * -> fossify-reader). Replace those two fetcher entries with ones that build a non-null Manager,
 * mirroring OnlineConnectivityManager / WlMediaSession. All hidden APIs are reached by reflection.
 */
public final class SystemServiceFetcherStubs {

    private SystemServiceFetcherStubs() {}

    public static void install() {
        replaceFetcher("alarm", new Builder() {
            @Override public Object build(Object context) throws Throwable { return buildAlarmManager(context); }
        });
        // media_session (noice/musicplayer): the plain MediaSessionManager(Context) constructor calls
        // MediaFrameworkPlatformInitializer.getMediaServiceManager(), a NoSuchMethodError on this
        // generation, so WlMediaSession's fetcher returns null and getSystemService(MEDIA_SESSION_
        // SERVICE) is null. Allocate the Manager without its constructor and force mService instead.
        replaceFetcher("media_session", new Builder() {
            @Override public Object build(Object context) throws Throwable { return buildMediaSessionManager(context); }
        });
        // r17q (etar): PowerManager.isIgnoringBatteryOptimizations -> getPowerExemptionManager() ->
        // getSystemService(PowerExemptionManager.class), whose stock fetcher does new
        // PowerExemptionManager(ctx) -> ctx.getSystemService(DeviceIdleManager.class).getService(),
        // and DeviceIdleManager is null on route-A, so the fetcher NPEs and returns null;
        // getPowerExemptionManager() then returns null and isAllowListed NPEs (etar
        // AllInOneActivity.dozeDisabled). Allocate a PowerExemptionManager without its constructor and
        // give it a type-zero IDeviceIdleController so isAllowListed -> isPowerSaveWhitelistApp -> false.
        replaceFetcher("power_exemption", new Builder() {
            @Override public Object build(Object context) throws Throwable { return buildPowerExemptionManager(context); }
        });
        registerServiceName("android.os.PowerExemptionManager", "power_exemption");
        // r17s (fd-meet/jitsi): getSystemService(RESTRICTIONS_SERVICE) is null on route-A, so
        // jitsi MainActivity NPEs invoking RestrictionsManager.getApplicationRestrictions() on null.
        // Build a real RestrictionsManager(Context, IRestrictionsManager) whose stubbed service returns
        // an EMPTY Bundle (not null) so getApplicationRestrictions() -> non-null Bundle.
        replaceFetcher("restrictions", new Builder() {
            @Override public Object build(Object context) throws Throwable { return buildRestrictionsManager(context); }
        });
        registerServiceName("android.content.RestrictionsManager", "restrictions");
        // vibrator_manager is deferred: VibratorManager/Vibrator have package-private constructors, so a
        // subclass stub will not compile; it needs an IVibratorManagerService-level proxy instead.
    }

    /** RestrictionsManager(Context, IRestrictionsManager) with a stub service returning empty Bundles. */
    private static Object buildRestrictionsManager(Object context) throws Throwable {
        Class<?> rm = Class.forName("android.content.RestrictionsManager");
        Class<?> irm = Class.forName("android.content.IRestrictionsManager");
        Object service = Proxy.newProxyInstance(irm.getClassLoader(), new Class<?>[] {irm},
                new InvocationHandler() {
                    @Override public Object invoke(Object p, Method m, Object[] a) {
                        String n = m.getName();
                        if ("asBinder".equals(n)) return new android.os.Binder();
                        Class<?> rt = m.getReturnType();
                        if (rt == android.os.Bundle.class) return new android.os.Bundle();
                        if (java.util.List.class.isAssignableFrom(rt)) return new java.util.ArrayList<Object>();
                        if (rt == boolean.class) return Boolean.FALSE;
                        if (rt == int.class) return Integer.valueOf(0);
                        if (rt == long.class) return Long.valueOf(0L);
                        return null;
                    }
                });
        Class<?> contextType = Class.forName("android.content.Context");
        Constructor<?> ctor = rm.getDeclaredConstructor(contextType, irm);
        ctor.setAccessible(true);
        System.err.println("[B8-FETCH] restrictions RestrictionsManager built (empty-Bundle service)");
        return ctor.newInstance(context, service);
    }

    /**
     * A PowerExemptionManager whose constructor path fetches the (null-on-route-A) DeviceIdleManager;
     * allocate it without a constructor and set its final IDeviceIdleController mService to a type-zero
     * proxy so isAllowListed()/isPowerSaveWhitelistApp() answer false instead of NPEing.
     */
    private static Object buildPowerExemptionManager(Object context) throws Throwable {
        Class<?> pem = Class.forName("android.os.PowerExemptionManager");
        Object instance = allocateInstance(pem);
        Class<?> ideviceidle = Class.forName("android.os.IDeviceIdleController");
        Object service = Proxy.newProxyInstance(ideviceidle.getClassLoader(),
                new Class<?>[] {ideviceidle}, new TypeZeroHandler());
        setField(instance, "mService", service);
        trySetField(instance, "mContext", context);
        System.err.println("[B8-FETCH] power_exemption PowerExemptionManager allocated (mService stubbed)");
        return instance;
    }

    /**
     * Map an API Class -> service name in SystemServiceRegistry.SYSTEM_SERVICE_NAMES so
     * getSystemService(ApiClass.class) resolves to our replaced fetcher (harmless if already mapped).
     */
    @SuppressWarnings("unchecked")
    private static void registerServiceName(String apiClassName, String name) {
        try {
            Class<?> ssr = Class.forName("android.app.SystemServiceRegistry");
            Class<?> apiClass = Class.forName(apiClassName);
            Field f = ssr.getDeclaredField("SYSTEM_SERVICE_NAMES");
            f.setAccessible(true);
            java.util.Map<Class<?>, String> names = (java.util.Map<Class<?>, String>) f.get(null);
            String prev = names.put(apiClass, name);
            System.err.println("[B8-FETCH] " + name + " class->name registered for " + apiClassName
                    + " (prev=" + prev + ")");
        } catch (Throwable t) {
            System.err.println("[B8-FETCH] " + name + " class->name register failed: " + t);
        }
    }

    /**
     * A MediaSessionManager whose constructor path (MediaFrameworkPlatformInitializer) is broken on
     * route-A: allocate it without running any constructor and set mService to a type-zero
     * ISessionManager whose createSession returns a non-null ISession proxy.
     */
    private static Object buildMediaSessionManager(Object context) throws Throwable {
        Class<?> mgr = Class.forName("android.media.session.MediaSessionManager");
        Object instance = allocateInstance(mgr);
        Class<?> iSessionManager = Class.forName("android.media.session.ISessionManager");
        Object service = Proxy.newProxyInstance(iSessionManager.getClassLoader(),
                new Class<?>[] {iSessionManager}, new TypeZeroHandler());
        setField(instance, "mService", service);
        trySetField(instance, "mContext", context);
        System.err.println("[B8-FETCH] media_session MediaSessionManager allocated (mService stubbed)");
        return instance;
    }

    /** Allocate an instance without invoking any constructor (sun.misc.Unsafe, reachable on ART). */
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
        try {
            setField(obj, name, value);
        } catch (Throwable ignore) {
        }
    }

    private interface Builder {
        Object build(Object context) throws Throwable;
    }

    /** AlarmManager(IAlarmManager, Context) built from a type-zero IAlarmManager proxy. */
    private static Object buildAlarmManager(Object context) throws Throwable {
        Class<?> iAlarm = Class.forName("android.app.IAlarmManager");
        Object service = Proxy.newProxyInstance(iAlarm.getClassLoader(), new Class<?>[] {iAlarm},
                new TypeZeroHandler());
        Class<?> alarmManager = Class.forName("android.app.AlarmManager");
        Class<?> contextType = Class.forName("android.content.Context");
        for (Constructor<?> c : alarmManager.getDeclaredConstructors()) {
            Class<?>[] p = c.getParameterTypes();
            if (p.length == 2 && p[0].isAssignableFrom(iAlarm) && p[1].isAssignableFrom(contextType)) {
                c.setAccessible(true);
                return c.newInstance(service, context);
            }
        }
        // Fallback: some builds expose only AlarmManager(Context). Better a Manager than null.
        for (Constructor<?> c : alarmManager.getDeclaredConstructors()) {
            Class<?>[] p = c.getParameterTypes();
            if (p.length == 1 && p[0].isAssignableFrom(contextType)) {
                c.setAccessible(true);
                return c.newInstance(context);
            }
        }
        throw new NoSuchMethodException("no usable AlarmManager constructor");
    }

    /** A type-correct-zero InvocationHandler for a stubbed IInterface (mirrors LocalServiceBinders). */
    private static final class TypeZeroHandler implements InvocationHandler {
        @Override
        public Object invoke(Object proxy, Method method, Object[] args) {
            String n = method.getName();
            if ("asBinder".equals(n)) return new android.os.Binder();
            if ("toString".equals(n)) return "WlAlarmManagerStub";
            if ("hashCode".equals(n)) return Integer.valueOf(System.identityHashCode(proxy));
            if ("equals".equals(n)) return Boolean.valueOf(args != null && args.length == 1 && args[0] == proxy);
            Class<?> t = method.getReturnType();
            if (t == boolean.class) return Boolean.FALSE;
            if (t == int.class) return Integer.valueOf(0);
            if (t == long.class) return Long.valueOf(0L);
            if (t == void.class) return null;
            // Return a non-null nested stub for interface returns (e.g. ISessionManager.createSession
            // -> ISession), so a caller that dereferences the result does not NPE.
            if (t.isInterface()) {
                try {
                    return Proxy.newProxyInstance(t.getClassLoader(), new Class<?>[] {t}, new TypeZeroHandler());
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
