/* r17e (#alarm) + J04 (#vibrator): single-purpose file (freeze unit) -- ALARM/VIBRATOR fetchers. */
package adapter.activity;

import java.lang.reflect.Array;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.Map;

/**
 * B8 (#alarm/r17e + #vibrator/J04): route-A's SystemServiceRegistry keeps the stock fetchers, which
 * either do not consume our in-process binder (ALARM_SERVICE returns null -> k9/fd-android
 * AndroidAlarmManager.&lt;init&gt; NPE) or hand back a manager whose id array is null
 * (VIBRATOR_MANAGER_SERVICE: SystemVibratorManager.mService.getVibratorIds() -> null ->
 * SystemVibrator "Attempt to get length of null array", fd-reader). Replace both fetchers with ones
 * that build a non-null manager off a type-zero IInterface stub.
 *
 * Split into its own file (from SystemServiceFetcherStubs) so it can be frozen (AGENTS.md 做事方式 3)
 * without locking the power_exemption/restrictions/media_session fetchers; it carries its own copies of
 * the reflection helpers so nothing it depends on is shared/mutable.
 */
public final class AlarmVibratorFetcher {

    private AlarmVibratorFetcher() {}

    public static void install() {
        replaceFetcher("alarm", new Builder() {
            @Override public Object build(Object context) throws Throwable { return buildAlarmManager(context); }
        });
        // J04 (fd-reader): SystemVibrator delegates getVibratorIds() to VibratorManager.getVibratorIds()
        // -> SystemVibratorManager.mService.getVibratorIds(), null on route-A. Allocate a
        // SystemVibratorManager without its constructor (it would asInterface a null binder) and set its
        // final IVibratorManagerService mService to a stub whose getVibratorIds() returns int[0] (no
        // vibrators). SystemVibrator, built normally, reads this manager via getSystemService and iterates
        // an empty id array instead of NPEing. getVibratorInfo is never reached with an empty id list.
        replaceFetcher("vibrator_manager", new Builder() {
            @Override public Object build(Object context) throws Throwable { return buildVibratorManager(context); }
        });
    }

    /** AlarmManager(IAlarmManager, Context) built from a type-zero IAlarmManager proxy. */
    private static Object buildAlarmManager(Object context) throws Throwable {
        Class<?> iAlarm = Class.forName("android.app.IAlarmManager");
        Object service = Proxy.newProxyInstance(iAlarm.getClassLoader(), new Class<?>[] {iAlarm},
                new ZeroHandler("WlAlarmManagerStub"));
        Class<?> alarmManager = Class.forName("android.app.AlarmManager");
        Class<?> contextType = Class.forName("android.content.Context");
        for (Constructor<?> c : alarmManager.getDeclaredConstructors()) {
            Class<?>[] p = c.getParameterTypes();
            if (p.length == 2 && p[0].isAssignableFrom(iAlarm) && p[1].isAssignableFrom(contextType)) {
                c.setAccessible(true);
                return c.newInstance(service, context);
            }
        }
        for (Constructor<?> c : alarmManager.getDeclaredConstructors()) {
            Class<?>[] p = c.getParameterTypes();
            if (p.length == 1 && p[0].isAssignableFrom(contextType)) {
                c.setAccessible(true);
                return c.newInstance(context);
            }
        }
        throw new NoSuchMethodException("no usable AlarmManager constructor");
    }

    /** SystemVibratorManager (allocated) whose IVibratorManagerService returns an empty vibrator-id array. */
    private static Object buildVibratorManager(Object context) throws Throwable {
        Class<?> svm = Class.forName("android.os.SystemVibratorManager");
        Object instance = allocateInstance(svm);
        Class<?> ivms = Class.forName("android.os.IVibratorManagerService");
        Object service = Proxy.newProxyInstance(ivms.getClassLoader(), new Class<?>[] {ivms},
                new ZeroHandler("WlVibratorManagerStub"));
        setField(instance, "mService", service);
        trySetField(instance, "mContext", context);
        System.err.println("[B8-FETCH] vibrator_manager SystemVibratorManager allocated (getVibratorIds -> int[0])");
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
            if (t.isArray()) return Array.newInstance(t.getComponentType(), 0);   // getVibratorIds -> int[0]
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
