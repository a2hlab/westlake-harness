package adapter.activity;

import android.content.pm.ApplicationInfo;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * Answer IPackageManager.getPackagesForUid / getNameForUid for this process's own uid.
 *
 * StorageManager.getVolumeList(int, int) first asks ActivityThread.currentOpPackageName(), which is
 * null until the Application object exists, then falls back to
 * ActivityThread.getPackageManager().getPackagesForUid(Process.myUid()). route-A's package-manager
 * projection answers that with nothing, so the framework logs "Missing package names; no storage
 * volumes available" and returns an empty StorageVolume[] without ever asking the (already
 * installed) child-local mount binder. Environment.getExternalStorageDirectory() then indexes [0]
 * of the empty array: amaze-filemanager's Application class (AppConfig) dies in its <clinit>.
 *
 * Westlake's PackageManagerAdapter resolves uid -> package for getPackagesForUid/getNameForUid; here
 * only the own-uid case is filled, after the real answer comes back empty (or throws). Every other
 * call passes through unchanged. Installed from B7BindFixes.apply with the bound ApplicationInfo,
 * before the Application class is instantiated.
 */
public final class SelfUidPackages {
    private static boolean sLogged;

    private SelfUidPackages() {}

    public static void install(ApplicationInfo ai) {
        try {
            if (ai == null || ai.packageName == null) return;
            final String pkg = ai.packageName;
            final int uid = android.os.Process.myUid();
            Class<?> activityThread = Class.forName("android.app.ActivityThread");
            Method getPm = activityThread.getDeclaredMethod("getPackageManager");
            getPm.setAccessible(true);
            final Object current = getPm.invoke(null);
            if (current == null) {
                log("not installed: ActivityThread.getPackageManager() is null");
                return;
            }
            Class<?> iface = Class.forName("android.content.pm.IPackageManager");
            Object proxy = Proxy.newProxyInstance(iface.getClassLoader(), new Class<?>[] { iface },
                    new InvocationHandler() {
                        public Object invoke(Object p, Method m, Object[] a) throws Throwable {
                            String n = m.getName();
                            if ("asBinder".equals(n)) {
                                return ((android.os.IInterface) current).asBinder();
                            }
                            boolean ownUid = a != null && a.length >= 1 && a[0] instanceof Integer
                                    && ((Integer) a[0]).intValue() == uid;
                            boolean packagesForUid = ownUid && "getPackagesForUid".equals(n);
                            boolean nameForUid = ownUid && "getNameForUid".equals(n);
                            Object r;
                            try {
                                r = m.invoke(current, a);
                            } catch (InvocationTargetException e) {
                                if (packagesForUid || nameForUid) {
                                    note(n, pkg, "threw " + e.getCause());
                                    return packagesForUid ? new String[] { pkg } : pkg;
                                }
                                throw e.getCause();
                            }
                            if (packagesForUid && (r == null || ((String[]) r).length == 0)) {
                                note(n, pkg, "empty");
                                return new String[] { pkg };
                            }
                            if (nameForUid && r == null) {
                                note(n, pkg, "null");
                                return pkg;
                            }
                            return r;
                        }
                    });
            Field f = activityThread.getDeclaredField("sPackageManager");
            f.setAccessible(true);
            f.set(null, proxy);
            log("installed for " + pkg + " uid=" + uid + " over " + current.getClass().getName());
        } catch (Throwable t) {
            log("not installed: " + t);
        }
    }

    private static void note(String method, String pkg, String why) {
        if (sLogged) return;
        sLogged = true;
        log(method + "(own uid) " + why + " -> " + pkg);
    }

    private static void log(String m) {
        System.err.println("[SELF-UID] " + m);
        System.err.flush();
    }
}
