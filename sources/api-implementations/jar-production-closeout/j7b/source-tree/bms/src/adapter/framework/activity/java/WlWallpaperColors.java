/* J7b (#fd-reader): single-purpose file (freeze unit) -- WallpaperManager.sGlobals seed. */
package adapter.compat;

import java.lang.reflect.Array;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * J7b (#fd-reader): after VibratorFetcher's mLock fix clears the getVibratorIds NPE, fd-reader reaches
 * WallpaperManager.getWallpaperColors(), whose body calls sGlobals.getWallpaperColors(...). The static
 * WallpaperManager.sGlobals is only created from a Context-carrying entry point; on route-A it is null here,
 * so getWallpaperColors NPEs on null WallpaperManager$Globals (WallpaperManager.java:1630). Allocate a
 * WallpaperManager$Globals without its constructor, set its IWallpaperManager mService to a type-zero stub
 * (getWallpaperColors -> null, not a crash), and seed the static sGlobals so getWallpaperColors returns null
 * colours instead of NPEing. Idempotent: leaves an existing non-null sGlobals alone.
 */
public final class WlWallpaperColors {

    private WlWallpaperColors() {}

    public static String install() {
        try {
            ClassLoader loader = WlWallpaperColors.class.getClassLoader();
            Class<?> wm = Class.forName("android.app.WallpaperManager", false, loader);
            Field sGlobals = wm.getDeclaredField("sGlobals");
            sGlobals.setAccessible(true);
            if (sGlobals.get(null) != null) return "already present";

            Class<?> globals = Class.forName("android.app.WallpaperManager$Globals", false, loader);
            Object instance = allocateInstance(globals);
            Class<?> iwp = Class.forName("android.app.IWallpaperManager", false, loader);
            Object service = Proxy.newProxyInstance(loader, new Class<?>[] {iwp}, new ZeroHandler("WlWallpaperStub"));
            trySetField(instance, "mService", service);
            sGlobals.set(null, instance);
            return "seeded sGlobals (mService stubbed)";
        } catch (Throwable t) {
            return "FAILED: " + t.getClass().getName() + ": " + t.getMessage();
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

    private static void trySetField(Object obj, String name, Object value) {
        for (Class<?> c = obj.getClass(); c != null; c = c.getSuperclass()) {
            try {
                Field f = c.getDeclaredField(name);
                f.setAccessible(true);
                f.set(obj, value);
                return;
            } catch (NoSuchFieldException ignore) {
            } catch (Throwable ignore) {
                return;
            }
        }
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
}
