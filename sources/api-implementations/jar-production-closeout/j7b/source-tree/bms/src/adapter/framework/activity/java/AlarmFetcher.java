/* r17e (#alarm): single-purpose file (freeze unit) -- ALARM_SERVICE fetcher (split from AlarmVibratorFetcher). */
package adapter.activity;

import java.lang.reflect.Array;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.Map;

/**
 * B8 (#alarm/r17e): route-A's SystemServiceRegistry keeps the stock ALARM_SERVICE fetcher, which does not
 * consume our in-process binder and returns null, so k9/fd-android AndroidAlarmManager.&lt;init&gt; NPEs.
 * Replace the fetcher with one that builds an AlarmManager off a type-zero IAlarmManager stub.
 *
 * Split out of AlarmVibratorFetcher into an alarm-only file (freeze prerequisite, cx-bms audit 82b3d42b):
 * a freeze unit must be one fix per file, so the verified alarm fix can freeze without locking the J04
 * vibrator fix (now VibratorFetcher). Behaviour is byte-identical to the alarm half of the merged file.
 * Self-contained -- it carries its own copies of the reflection helpers so nothing it depends on is shared.
 */
public final class AlarmFetcher {

    private AlarmFetcher() {}

    public static void install() {
        replaceFetcher("alarm", new Builder() {
            @Override public Object build(Object context) throws Throwable { return buildAlarmManager(context); }
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
