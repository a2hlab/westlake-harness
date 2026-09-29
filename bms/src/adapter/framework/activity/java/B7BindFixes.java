package adapter.activity;

import android.content.pm.ApplicationInfo;

import java.io.File;

/**
 * B7 (2026-09-29): two bind-time repairs applied to the resolved ApplicationInfo
 * before ActivityThread.handleBindApplication runs.
 *
 * 1. "user" service. ContextImpl.getSharedPreferences(File,int) consults
 *    getSystemService(UserManager.class) for credential-protected contexts
 *    (targetSdk >= 26, dataDir == credentialProtectedDataDir). This child has no
 *    system_server "user" service, so the fetcher returns null and the query NPEs
 *    (catima in Activity.attachBaseContext, fennec in Application.attachBaseContext).
 *    The existing UserManagerProjectionProxy answers only isUserUnlockingOrUnlocked.
 *
 * 2. nativeLibraryDir. For an APK without native code BMS reports no cpuAbi and no
 *    nativeLibraryPath, so PackageInfoBuilder falls back to
 *    /system/app/<pkg>/lib/armeabi-v7a, which does not exist. The app-native-loader
 *    refuses a namespace whose search path is not an existing directory, so
 *    LoadedApk.getClassLoader throws UnsatisfiedLinkError during bind (opencamera).
 *    Point it at the package's own installed code directory instead: it exists and
 *    holds no libraries, which is exactly "this app has no native code".
 */
public final class B7BindFixes {
    private B7BindFixes() {}

    public static void apply(ApplicationInfo ai) {
        try {
            UserManagerProjectionProxy.install();
        } catch (Throwable t) {
            System.err.println("[B7] user binder not installed: " + t);
        }
        try {
            fixNativeLibraryDir(ai);
        } catch (Throwable t) {
            System.err.println("[B7] nativeLibraryDir check failed: " + t);
        }
        // B8 (#65): record the bound self ApplicationInfo for the self-package
        // getProviderInfo/resolveContentProvider fallback (SelfComponentFallback).
        SelfComponentFallback.bind(ai);
        // B8 (#65) items 6/7: appops/uimode/locale/account/alarm answered in process.
        B8BindExtras.installServiceStubs();
        // B8 (#70/INVENTORY 19): Flutter Impeller fallback -- add EnableImpeller=false to the app's
        // metaData Bundle so a Flutter engine that honours the opt-out uses the Skia GLES path.
        applyImpellerFallback(ai);
        // B8 (#82/r15): tolerant uncaught-exception handler. AOSP RuntimeInit's KillApplicationHandler
        // calls System.exit on ANY uncaught exception, so a crash on a background worker takes the
        // whole app down (many "exit 1"). Westlake keeps only the main thread fatal.
        installTolerantUncaughtHandler();
        // B8 (#82/r15): runtime-JAR proxies over the BCP IWindowSession (addToDisplay flag-allow +
        // relayout CLAMP48) and IActivityManager (in-app bindService). Same reflect.Proxy pattern as
        // PackageManagerProjectionProxy; each install is idempotent and defensive.
        try { WindowSessionProxy.install(); } catch (Throwable t) { System.err.println("[B8-WSP] " + t); }
        try { ActivityManagerBindProxy.install(); } catch (Throwable t) { System.err.println("[B8-AMB] " + t); }
        // r16 (#90): cc-wiki's OnlineConnectivityManager -- replaces the SystemServiceRegistry
        // connectivity (+ jobscheduler) fetchers with an online-reporting ConnectivityManager
        // subclass (Wikipedia onGoOffline, WorkManager). Called reflectively so this class does not
        // need the Westlake-sourced OnlineConnectivityManager on its compile classpath.
        try {
            Class.forName("adapter.activity.OnlineConnectivityManager").getMethod("install").invoke(null);
        } catch (Throwable t) {
            System.err.println("[B8-OCM] not installed: " + t);
        }
        // r17 (cc-wiki): answer IPackageManager.getPackagesForUid/getNameForUid for this process's own
        // uid. route-A's package projection returns nothing for self-uid, so StorageManager.getVolumeList
        // logs "Missing package names" and returns an empty StorageVolume[] without asking the (already
        // installed) child-local mount binder; amaze-filemanager's AppConfig <clinit> then indexes [0] of
        // the empty array and dies. Passthrough for every other call.
        try {
            SelfUidPackages.install(ai);
        } catch (Throwable t) {
            System.err.println("[SELF-UID] not installed: " + t);
        }
        // r17 (#93): Westlake HTTPS/TLS Java side. OhTrustBridge restores the BC JCA registrations the
        // trimmed BCP dropped (MessageDigest, AES, X.509 CertificateFactory, RSA/EC signatures, EC
        // KeyFactory) and publishes SecureRandom.WestlakeKernel + TrustManagerFactory.OH-PKIX/PKIX/X509
        // backed by the platform CA bundle (OhSystemTrustManager). WestlakeSSLSocket declares the seven
        // OpenSSL-boundary natives so cx-t0's wl_register_tls_natives binds. Called reflectively (the
        // TLS classes compile in a separate android-bootclasspath pass) at bind in the forked child --
        // clear of AppSpawnXInit's parent Security.getProviders() clinit trap (L296-303).
        try {
            Class.forName("adapter.security.WestlakeTlsInstall").getMethod("install").invoke(null);
        } catch (Throwable t) {
            System.err.println("[B8-TLS] not installed: " + t);
        }
    }

    /**
     * Non-main-thread uncaught exceptions end only that thread (logged), not the process; the main
     * thread is handed back to the original handler (AOSP's exit behaviour). Copies the intent of
     * Westlake's AppSpawnXInit tolerant handler but as a per-bind Thread default handler in the
     * runtime JAR, so no boot-image change is needed.
     */
    static void installTolerantUncaughtHandler() {
        try {
            final Thread.UncaughtExceptionHandler original = Thread.getDefaultUncaughtExceptionHandler();
            final Thread mainThread = android.os.Looper.getMainLooper().getThread();
            Thread.setDefaultUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler() {
                @Override
                public void uncaughtException(Thread thread, Throwable ex) {
                    if (thread == mainThread) {
                        if (original != null) original.uncaughtException(thread, ex);
                        return;
                    }
                    System.err.println("[B8-UEH] background thread '" + thread.getName()
                            + "' uncaught, thread ended (process kept alive): " + ex);
                    ex.printStackTrace();
                }
            });
            System.err.println("[B8-UEH] tolerant uncaught-exception handler installed");
        } catch (Throwable t) {
            System.err.println("[B8-UEH] not installed: " + t);
        }
    }

    static void applyImpellerFallback(ApplicationInfo ai) {
        try {
            if (ai == null) return;
            if (ai.metaData == null) ai.metaData = new android.os.Bundle();
            if (!ai.metaData.containsKey("io.flutter.embedding.android.EnableImpeller")) {
                ai.metaData.putBoolean("io.flutter.embedding.android.EnableImpeller", false);
                System.err.println("[B8-IMPELLER] EnableImpeller=false injected into metaData");
            }
        } catch (Throwable t) {
            System.err.println("[B8-IMPELLER] not applied: " + t);
        }
    }

    static void fixNativeLibraryDir(ApplicationInfo ai) {
        if (ai == null) return;
        String current = ai.nativeLibraryDir;
        if (current != null && new File(current).isDirectory()) return;
        if (ai.sourceDir == null) return;
        File codeDir = new File(ai.sourceDir).getParentFile();
        if (codeDir == null || !codeDir.isDirectory()) return;
        File arm64 = new File(codeDir, "lib/arm64-v8a");
        String replacement = arm64.isDirectory() ? arm64.getPath() : codeDir.getPath();
        ai.nativeLibraryDir = replacement;
        System.err.println("[B7] nativeLibraryDir " + current + " does not exist; using "
                + replacement);
    }
}
