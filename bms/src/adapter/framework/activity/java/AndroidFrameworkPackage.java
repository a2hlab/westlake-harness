/* J2 (#newpipe): single-purpose file (freeze unit) -- synthesize getPackageInfo("android"). */
package adapter.activity;

import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * B8 (#newpipe, J2): route-A's BMS denies GET_BUNDLE_INFO_PRIVILEGED and synthesizes no "android"
 * framework package, so IPackageManager.getPackageInfo("android", ...) returns not-found. NewPipe's
 * PlayerService (MediaBrowserServiceCompat) builds a MediaSessionCompat in onCreate, which looks the
 * "android" package up for a media-button receiver; the NameNotFoundException surfaces as an
 * InvocationTargetException out of the in-process bind and the service never starts.
 *
 * Answer getPackageInfo("android") by name with a synthesized system PackageInfo (the framework
 * package is always present on a real device); every other call passes through. Same shape as
 * SelfUidPackages (an IPackageManager proxy over ActivityThread.sPackageManager), installed from
 * B7BindFixes.apply AFTER SelfUidPackages so it chains over it. Its own file so it can be frozen
 * without locking the sibling PM projections.
 */
public final class AndroidFrameworkPackage {
    private static boolean sLogged;

    private AndroidFrameworkPackage() {}

    public static void install() {
        try {
            Class<?> activityThread = Class.forName("android.app.ActivityThread");
            Method getPm = activityThread.getDeclaredMethod("getPackageManager");
            getPm.setAccessible(true);
            final Object current = getPm.invoke(null);
            if (current == null) { log("not installed: ActivityThread.getPackageManager() is null"); return; }
            Class<?> iface = Class.forName("android.content.pm.IPackageManager");
            Object proxy = Proxy.newProxyInstance(iface.getClassLoader(), new Class<?>[] { iface },
                    new InvocationHandler() {
                        @Override public Object invoke(Object p, Method m, Object[] a) throws Throwable {
                            String n = m.getName();
                            if ("asBinder".equals(n)) return ((android.os.IInterface) current).asBinder();
                            boolean androidPkg = "getPackageInfo".equals(n) && a != null && a.length >= 1
                                    && "android".equals(a[0]);
                            try {
                                Object r = m.invoke(current, a);
                                if (androidPkg && r == null) { note("null"); return synthesize(); }
                                return r;
                            } catch (InvocationTargetException e) {
                                if (androidPkg) { note("threw " + e.getCause()); return synthesize(); }
                                throw e.getCause();
                            }
                        }
                    });
            Field f = activityThread.getDeclaredField("sPackageManager");
            f.setAccessible(true);
            f.set(null, proxy);
            log("installed over " + current.getClass().getName());
        } catch (Throwable t) {
            log("not installed: " + t);
        }
    }

    /** A minimal but valid framework PackageInfo -- enough for a media-button-receiver lookup. */
    private static PackageInfo synthesize() {
        PackageInfo pi = new PackageInfo();
        pi.packageName = "android";
        pi.versionCode = android.os.Build.VERSION.SDK_INT;
        pi.versionName = String.valueOf(android.os.Build.VERSION.RELEASE);
        ApplicationInfo ai = new ApplicationInfo();
        ai.packageName = "android";
        ai.uid = android.os.Process.SYSTEM_UID;
        ai.flags = ApplicationInfo.FLAG_SYSTEM | ApplicationInfo.FLAG_INSTALLED;
        ai.enabled = true;
        ai.sourceDir = "/system/framework/framework-res.apk";
        ai.publicSourceDir = ai.sourceDir;
        pi.applicationInfo = ai;
        return pi;
    }

    private static void note(String why) {
        if (sLogged) return;
        sLogged = true;
        log("getPackageInfo(android) " + why + " -> synthesized system package");
    }

    private static void log(String m) {
        System.err.println("[B8-ANDROIDPKG] " + m);
        System.err.flush();
    }
}
