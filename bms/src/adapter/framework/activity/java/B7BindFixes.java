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
