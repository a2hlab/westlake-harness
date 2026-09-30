/* J5 (#webview): single-purpose file (freeze unit) -- Java side of the N3b WebView publication contract. */
package adapter.core;

import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;

/**
 * J5 (#webview): the Java half of benchmark/2026-09-30-n3b-webview/JAVA-HANDOFF.md, paired with cx-t0's
 * N3b runtime (7c9c6240). OHOS runs no SystemServer, so nothing owns the webviewupdate service or the
 * WebView provider PackageInfo; WebViewFactory then fails before Tutanota (and other WebView apps) draw.
 *
 * This class ports the donor (Westlake 532633da) WebView boundary into the runtime JAR:
 *   - getSideloadedWebViewPackageInfo(): the provider PackageInfo, gated on ASX_WEBVIEW_APK pointing at a
 *     real file (public API only, verbatim from the donor). Returns null when no provider APK is staged.
 *   - a local IWebViewUpdateService in ServiceManager.sCache under "webviewupdate" (WlMediaRouter shape:
 *     a reflective Proxy over the hidden interface + a LocalBinder, so the runtime JAR needs no
 *     compile-time hidden WebView API), installed ONLY when a provider is available.
 *   - nativePrime()/nativePublishAfterBind(): the two ()Z entries exported by
 *     /system/android/lib64/liboh_android_runtime.so (N3b). prime seeds/verifies the service cache and
 *     holds the feature false before bind; publish is called after Application.onCreate, before the first
 *     Activity, on the main thread. Both honor their boolean result (a public-cache mismatch may set the
 *     feature field true yet return false -- feature=published alone is NOT success; see the donor caveat).
 *
 * INERT WITHOUT A PROVIDER APK: with no ASX_WEBVIEW_APK, getSideloadedWebViewPackageInfo() is null,
 * isAvailable() is false, no service is routed, prime/publish are not called, and hasSystemFeature stays
 * false. On any missing symbol/class/library the old no-WebView behavior is preserved -- success is never
 * turned on by catching failure. WebViewPackageFallback answers the provider getPackageInfo/
 * getApplicationInfo/hasSystemFeature in the PM projection proxy. WebViewFactory.sProviderInstance and all
 * package verification are left untouched.
 */
public final class WestlakeWebViewInstall {
    static final String WEBVIEW_PACKAGE = "com.android.webview";
    private static final int WEBVIEW_VERSION_CODE = 541412303;
    private static final String WEBVIEW_VERSION_NAME = "109.0.5414.123";
    private static final String RUNTIME_SO = "/system/android/lib64/liboh_android_runtime.so";
    private static final String IFACE = "android.webkit.IWebViewUpdateService";

    private static volatile boolean sNativeLinked;
    private static boolean sTriedLink;

    private WestlakeWebViewInstall() {}

    private static native boolean nativePrime();
    private static native boolean nativePublishAfterBind();

    /** True only when a real provider APK is staged (ASX_WEBVIEW_APK -> an existing file). */
    public static boolean isAvailable() {
        return getSideloadedWebViewPackageInfo() != null;
    }

    /**
     * Pre-bind (call after the package adapter installs, BEFORE Application bind): link the runtime and
     * call nativePrime. nativePrime resolves adapter.core.WebViewUpdateServiceAdapter by name, reads its
     * getInstance(), and SEEDS ServiceManager.sCache itself with the exact WebViewFactory.
     * WEBVIEW_UPDATE_SERVICE_NAME String object (Java must not pre-seed with a different key -- see
     * WebViewUpdateServiceAdapter). No-op (records unavailable) when no provider APK is staged, so the
     * feature stays false. Returns a short status for the [B8-WEBVIEW] log.
     */
    public static String install() {
        try {
            if (!isAvailable()) return "unavailable (no ASX_WEBVIEW_APK provider)";
            boolean linked = linkRuntime();
            boolean primed = linked && nativePrimeSafe();
            return "provider=" + WEBVIEW_PACKAGE + " nativeLinked=" + linked + " primed=" + primed
                    + " (native seeds the sCache; feature held false until publishAfterBind reports true)";
        } catch (Throwable t) {
            return "not installed: " + t;
        }
    }

    /**
     * Post-bind (call after handleBindApplication returns / Application.onCreate completes, before the
     * first Activity, on the main thread): publish. A false result is NOT publication -- the caller may
     * retry at a genuine later bind checkpoint (never a timer/log hook). No-op when unavailable/unlinked.
     */
    public static boolean publishAfterBind() {
        try {
            if (!isAvailable() || !sNativeLinked) return false;
            boolean ok = nativePublishAfterBind();
            System.err.println("[B8-WEBVIEW] publishAfterBind -> " + ok
                    + (ok ? " (application=ready, feature=published)" : " (NOT published; honor boolean)"));
            return ok;
        } catch (Throwable t) {
            System.err.println("[B8-WEBVIEW] publishAfterBind failed: " + t);
            return false;
        }
    }

    private static boolean nativePrimeSafe() {
        try {
            boolean held = nativePrime();
            System.err.println("[B8-WEBVIEW] nativePrime -> " + held + " (held-unsupported before bind)");
            return held;
        } catch (Throwable t) {
            System.err.println("[B8-WEBVIEW] nativePrime failed: " + t);
            return false;
        }
    }

    /** System.load the resident runtime .so in the owning ClassLoader so the two ()Z symbols resolve. */
    private static synchronized boolean linkRuntime() {
        if (sTriedLink) return sNativeLinked;
        sTriedLink = true;
        try {
            System.load(RUNTIME_SO);
            sNativeLinked = true;
        } catch (Throwable t) {
            System.err.println("[B8-WEBVIEW] runtime .so not linked (" + RUNTIME_SO + "): " + t);
            sNativeLinked = false;
        }
        return sNativeLinked;
    }


    /**
     * The provider PackageInfo, gated on ASX_WEBVIEW_APK -> an existing file (verbatim from Westlake
     * 532633da PackageManagerAdapter.getSideloadedWebViewPackageInfo; public API only). Null when no
     * provider APK is staged -- the whole capability then stays inert and the feature stays false.
     */
    public static PackageInfo getSideloadedWebViewPackageInfo() {
        String apkPath = System.getenv("ASX_WEBVIEW_APK");
        if (apkPath == null || apkPath.isEmpty() || !new java.io.File(apkPath).isFile()) return null;

        String libDir = getenv("ASX_WEBVIEW_LIB_DIR", "/data/local/tmp/asx/webview-t-lib");
        String dataDir = getenv("ASX_WEBVIEW_DATA_DIR", "/data/local/tmp/asx/webview-t-data");

        ApplicationInfo ai = new ApplicationInfo();
        ai.packageName = WEBVIEW_PACKAGE;
        ai.processName = WEBVIEW_PACKAGE;
        ai.className = "org.chromium.android_webview.nonembedded.WebViewApkApplication";
        ai.sourceDir = apkPath;
        ai.publicSourceDir = apkPath;
        ai.dataDir = dataDir;
        ai.deviceProtectedDataDir = dataDir;
        ai.nativeLibraryDir = libDir;
        ai.uid = android.os.Process.myUid();
        ai.enabled = true;
        ai.flags = ApplicationInfo.FLAG_HAS_CODE | ApplicationInfo.FLAG_INSTALLED
                | ApplicationInfo.FLAG_EXTRACT_NATIVE_LIBS | ApplicationInfo.FLAG_MULTIARCH;
        ai.minSdkVersion = 24;
        ai.targetSdkVersion = 33;
        ai.splitSourceDirs = new String[0];
        ai.splitPublicSourceDirs = new String[0];
        ai.splitNames = new String[0];
        ai.sharedLibraryFiles = new String[0];
        ai.metaData = new android.os.Bundle();
        ai.metaData.putString("com.android.webview.WebViewLibrary", "libwebviewchromium.so");
        // @hide ApplicationInfo fields absent from the compile android.jar (present at runtime) -- set by
        // reflection so the donor's completeness is preserved without a full-framework compile jar; an
        // absent field on this platform is silently skipped.
        setField(ai, "scanSourceDir", apkPath);
        setField(ai, "scanPublicSourceDir", apkPath);
        setField(ai, "credentialProtectedDataDir", dataDir);
        setField(ai, "nativeLibraryRootDir", libDir);
        setField(ai, "nativeLibraryRootRequiresIsa", Boolean.FALSE);
        setField(ai, "primaryCpuAbi", "arm64-v8a");
        setField(ai, "compileSdkVersion", Integer.valueOf(33));
        setField(ai, "longVersionCode", Long.valueOf(WEBVIEW_VERSION_CODE));
        setField(ai, "splitDependencies", new android.util.SparseArray<int[]>(0));
        setField(ai, "resourceDirs", new String[0]);
        setField(ai, "seInfo", "default");
        setField(ai, "seInfoUser", "");

        PackageInfo pi = new PackageInfo();
        pi.packageName = WEBVIEW_PACKAGE;
        pi.versionCode = WEBVIEW_VERSION_CODE;
        pi.versionName = WEBVIEW_VERSION_NAME;
        pi.applicationInfo = ai;
        pi.signatures = null;   // WebViewFactory treats two null signature arrays as equal (donor comment).
        setField(pi, "compileSdkVersion", Integer.valueOf(33));
        return pi;
    }

    /** Set a field that may be @hide (absent from the compile android.jar) but present at runtime. */
    private static void setField(Object target, String name, Object value) {
        try {
            java.lang.reflect.Field f = target.getClass().getField(name);
            f.set(target, value);
        } catch (Throwable t) {
            // Field not present on this platform -- donor-completeness only, safe to skip.
        }
    }

    private static String getenv(String name, String fallback) {
        String value = System.getenv(name);
        return value == null || value.isEmpty() ? fallback : value;
    }
}
