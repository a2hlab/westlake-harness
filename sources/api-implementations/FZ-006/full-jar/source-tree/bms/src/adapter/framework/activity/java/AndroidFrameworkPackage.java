/* J2 (#newpipe): single-purpose file (freeze unit) -- synthesize getPackageInfo("android"). */
package adapter.activity;

import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;
import android.content.pm.Signature;

import java.lang.reflect.Constructor;
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

    /** A self-signed X.509 (DER, hex) used as the synthesized platform package's signature. Not a real
     *  platform key -- only a present, well-formed cert so a "platform signature" lookup stops throwing
     *  "not found" (a caller that pins a specific key correctly gets "not that key"). See
     *  installPlatformSignature. Generated 2026-09-30 (CN=Android, 2048-bit RSA, 20-year validity). */
    private static final String PLATFORM_CERT_HEX =
            "308203433082022ba00302010202142560a74cd8351b920e267542be8fbca57944c3ef300d06092a864886f70d"
            + "01010b05003031310b30090603550406130255533110300e060355040a0c07416e64726f69643110300e060355"
            + "04030c07416e64726f6964301e170d3236303933303130303533375a170d3436303932353130303533375a3031"
            + "310b30090603550406130255533110300e060355040a0c07416e64726f69643110300e06035504030c07416e64"
            + "726f696430820122300d06092a864886f70d01010105000382010f003082010a0282010100c65d66aa5677b018"
            + "e0917f8e278c246e9545af5f416603fef44b9fe41452915f32a450379604dd17dbf9cd2345d7879efb1ebea7ea"
            + "40752a1f148fa42916c56f81070bdebbb3a56b4c3646b37efe20f99a7491afc6fcd606d8849bcb11ccd7a5c5a1"
            + "f3a878a3da13ee088f346cac7139f3580652cb34919b268f0a9a572f4d0db26a68ad9a5fb0e756f574e0996812"
            + "94b8c087721c101c6b62052a4f92b7cb8654e4c8702d3d3f03c67967f7f7267ada32686934907645d4e57920f0"
            + "1c9029967a2a4db63d539d71d6bdb2085f39411674ef07756fd55d28fadb5a47d2cfbb3293bbfc866e4563a1e1"
            + "93e3a3d5cfff1591b47e9c50635939e4a2adfb4ea696150203010001a3533051301d0603551d0e041604148105"
            + "ec1aafa32c63f1f1473c2d8a2b6b79817f33301f0603551d230418301680148105ec1aafa32c63f1f1473c2d8a"
            + "2b6b79817f33300f0603551d130101ff040530030101ff300d06092a864886f70d01010b0500038201010093e1"
            + "8f03eba02dc39c064ae1adeedbab55e724e0724afe80e768591ab1cba7aeb118f24bf46bc613340efb4c5cba92"
            + "2a60c671153fed065f09cb755e754a7ee760008d18caf13a0442ffbe15af57c2780e5d9a708dc44a1421b5373a"
            + "7b85764882e6567f71d01ba1c2a17627e99a9d3aafd34a345ae60d3404efa07e2380f26e3298d5405843db1ca3"
            + "c6b0d82aeeb82dba509a5a28456876d21ebd946180192b400fb1044fa409aed5feabd3073343a2898ed8e976e6"
            + "6d849d08d26c92b08b78c17d5f34998b5de1aad72e428160e0714c1780417801c59793e0241d7f77bc5503c155"
            + "58b20defe275b5cfc88a6c9dbfa23e81538ee42e8d69aee103d2c8d5e8";

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
        installPlatformSignature(pi);
        return pi;
    }

    /**
     * J4 (#newpipe): the synthesized "android" package had no signatures, so a caller that reads the
     * platform signature during NewPipe's PlayerService bind (okhttp3.Dispatcher.<init> ->
     * MediaBrowserImpl.<init>) threw {@code IllegalStateException: Platform signature not found} (the
     * real cause the J3 [B8-AMB] getCause() dump surfaced). Populate both the legacy {@code signatures}
     * array (public {@link Signature}) and, best-effort by reflection, the modern {@code signingInfo}
     * (its {@code SigningInfo(SigningDetails)} constructor is @hide) with a self-signed platform cert.
     * The value need only be a present, well-formed X.509 -- the framework package is always signed on a
     * real device; a caller that compares it to a specific key correctly finds "not that key" rather
     * than "not found", and a caller that only checks presence/parses it is satisfied.
     */
    private static void installPlatformSignature(PackageInfo pi) {
        try {
            Signature[] sigs = new Signature[] { new Signature(PLATFORM_CERT_HEX) };
            pi.signatures = sigs;
            try {
                Class<?> sdb = Class.forName("android.content.pm.SigningDetails$Builder");
                Object b = sdb.getDeclaredConstructor().newInstance();
                sdb.getMethod("setSignatures", Signature[].class).invoke(b, (Object) sigs);
                try { sdb.getMethod("setSignatureSchemeVersion", int.class).invoke(b, 3); }
                catch (Throwable ignore) { /* scheme version optional on some builds */ }
                Object details = sdb.getMethod("build").invoke(b);
                Class<?> sd = Class.forName("android.content.pm.SigningDetails");
                Class<?> si = Class.forName("android.content.pm.SigningInfo");
                Constructor<?> c = si.getDeclaredConstructor(sd);
                c.setAccessible(true);
                PackageInfo.class.getField("signingInfo").set(pi, c.newInstance(details));
            } catch (Throwable t) {
                // Legacy signatures[] alone still satisfies a presence check; log the modern path miss.
                log("signingInfo not populated (signatures[] set): " + t);
            }
            log("platform signature installed (signatures=1" + (pi.signatures != null ? "" : "?") + ")");
        } catch (Throwable t) {
            log("platform signature NOT installed: " + t);
        }
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
