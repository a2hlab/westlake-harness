/* J7 (#fd-catima): single-purpose file (freeze unit) -- APPWIDGET_SERVICE fetcher. */
package adapter.activity;

import java.lang.reflect.Array;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.Map;

/**
 * J7 (#fd-catima): AppWidgetManager.getInstance(Context) resolves to Context.getSystemService(appwidget),
 * whose stock fetcher returns null when FEATURE_APP_WIDGETS is absent on route-A, so
 * protect.card_locker.ListWidget.updateAll does {@code AppWidgetManager.getInstance(ctx).getClass()} (an R8
 * not-null check) on null and NPEs (NULL-PRODUCERS.md). Allocate an AppWidgetManager without its constructor
 * and set its IAppWidgetService mService to a type-zero stub so getInstance is non-null and its calls answer
 * type-zero (empty id arrays / false). Both the "appwidget" name and the AppWidgetManager.class->name mapping
 * are registered, since getInstance uses getSystemService(AppWidgetManager.class) on newer API levels.
 * Self-contained reflection helpers.
 */
public final class AppWidgetFetcher {

    private AppWidgetFetcher() {}

    public static void install() {
        replaceFetcher("appwidget", new Builder() {
            @Override public Object build(Object context) throws Throwable { return buildAppWidgetManager(context); }
        });
        registerServiceName("android.appwidget.AppWidgetManager", "appwidget");
    }

    /** AppWidgetManager (allocated) whose IAppWidgetService mService is a type-zero stub. */
    private static Object buildAppWidgetManager(Object context) throws Throwable {
        Class<?> awm = Class.forName("android.appwidget.AppWidgetManager");
        Object instance = allocateInstance(awm);
        Class<?> iaws = Class.forName("com.android.internal.appwidget.IAppWidgetService");
        Object service = Proxy.newProxyInstance(iaws.getClassLoader(), new Class<?>[] {iaws},
                new ZeroHandler("WlAppWidgetServiceStub"));
        setField(instance, "mService", service);
        trySetField(instance, "mContext", context);
        trySetField(instance, "mPackageName", context == null ? null
                : (String) context.getClass().getMethod("getOpPackageName").invoke(context));
        System.err.println("[B8-FETCH] appwidget AppWidgetManager allocated (mService stubbed, type-zero)");
        return instance;
    }

    @SuppressWarnings("unchecked")
    private static void registerServiceName(String apiClassName, String name) {
        try {
            Class<?> ssr = Class.forName("android.app.SystemServiceRegistry");
            Class<?> apiClass = Class.forName(apiClassName);
            Field f = ssr.getDeclaredField("SYSTEM_SERVICE_NAMES");
            f.setAccessible(true);
            Map<Class<?>, String> names = (Map<Class<?>, String>) f.get(null);
            String prev = names.put(apiClass, name);
            System.err.println("[B8-FETCH] " + name + " class->name registered for " + apiClassName
                    + " (prev=" + prev + ")");
        } catch (Throwable t) {
            System.err.println("[B8-FETCH] " + name + " class->name register failed: " + t);
        }
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
