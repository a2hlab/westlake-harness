package adapter.activity;

import android.content.pm.ActivityInfo;
import android.content.pm.ApplicationInfo;
import android.util.Log;
import java.io.File;

/** Adapted from 00.Workspace LaunchActivityAliasProjection: retain OH identity and
 * populate only targetActivity from the installed app's own manifest. This older
 * baseline lacks the upstream InstalledApkApplicationProjection dependency tree,
 * so the existing bounded binary reader supplies the same manifest fact.
 */
public final class LaunchActivityAliasProjection {
    private static final String TAG = "B5LaunchAlias";
    private LaunchActivityAliasProjection() {}

    public static void apply(ActivityInfo launch) {
        String alias = launch == null ? "<null>" : launch.name;
        try {
            apply(launch, android.os.Process.myUid());
            Log.i(TAG, "[B5-ALIAS] alias=" + alias + " target=" + launch.targetActivity
                    + " ordinary=" + (launch.targetActivity == null));
        } catch (Throwable error) {
            // The enclosing Binder scheduling callback catches Throwable. Returning
            // there would leave AMS waiting forever; a bad manifest must terminate.
            Log.e(TAG, "[B5-ALIAS] alias=" + alias + " target="
                    + (launch == null ? "<unknown>" : launch.targetActivity)
                    + " resolution_failed=" + error, error);
            android.os.Process.killProcess(android.os.Process.myPid());
            System.exit(1);
        }
    }

    static void apply(ActivityInfo launch, int callerUid) throws Exception {
        ApplicationInfo owner = launch == null ? null : launch.applicationInfo;
        if (owner == null || owner.uid != callerUid || owner.packageName == null
                || !owner.packageName.equals(launch.packageName) || owner.sourceDir == null
                || launch.name == null || launch.name.isEmpty()) {
            throw new SecurityException("Launch caller/package identity mismatch");
        }
        File apk = new File(owner.sourceDir).getCanonicalFile();
        if (!apk.isFile()) throw new java.io.IOException("Installed APK absent: " + apk);
        long size = apk.length(), mtime = apk.lastModified();
        String target = BinaryAndroidManifestOrientation.readAliasTarget(
                apk.getPath(), owner.packageName, launch.name);
        if (size != apk.length() || mtime != apk.lastModified()) {
            throw new SecurityException("Installed APK changed during alias resolution");
        }
        // ActivityThread uses targetActivity for class loading while component/name,
        // ApplicationInfo, theme, flags and OH token correlation remain untouched.
        launch.targetActivity = target;
    }
}
