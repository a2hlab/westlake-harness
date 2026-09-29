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
        // vibrator_manager is deferred: VibratorManager/Vibrator have package-private constructors, so a
        // subclass stub will not compile; it needs an IVibratorManagerService-level proxy instead.
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
