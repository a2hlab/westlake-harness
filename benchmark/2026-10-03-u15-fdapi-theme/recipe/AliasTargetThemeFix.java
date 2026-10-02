package adapter.activity;

import android.content.pm.ActivityInfo;
import android.util.Log;

/**
 * U15 fd-api fix (cc-t3 JAR, independent class + one needle). AOSP semantics: an <activity-alias> with no android:theme
 * INHERITS the target activity's theme. route-A leaves the alias launch ActivityInfo.theme at the application theme
 * (AppSchedulerBridge:793 fallback), so an aliased AppCompatActivity (e.g. com.termux.api TermuxAPIMainActivity, launched
 * via TermuxAPILauncherActivity) attaches with the DeviceDefault application theme and AppCompatDelegate.createSubDecor
 * throws "need a Theme.AppCompat theme". This sets launch.theme to the TARGET activity's declared theme so the Activity's
 * ContextThemeWrapper (what AppCompatDelegate reads) carries the app's AppCompat theme.
 *
 * Call AFTER launch.targetActivity is resolved and AFTER the generic theme resolution, so it is not re-clobbered.
 */
public final class AliasTargetThemeFix {
    private static final String TAG = "B8LaunchAlias";
    private AliasTargetThemeFix() {}

    /** launch = the alias launch ActivityInfo (becomes r.activityInfo). No-op unless it is an alias with a target. */
    public static void apply(ActivityInfo launch) {
        try {
            if (launch == null || launch.targetActivity == null || launch.applicationInfo == null
                    || launch.applicationInfo.sourceDir == null) {
                return;
            }
            // Read the TARGET activity's android:theme from the installed APK's binary manifest.
            int targetTheme = BinaryAndroidManifestOrientation.readActivityTheme(
                    launch.applicationInfo.sourceDir, launch.packageName, launch.targetActivity);
            if (targetTheme != 0 && targetTheme != BinaryAndroidManifestOrientation.NOT_FOUND
                    && targetTheme != launch.theme) {
                int was = launch.theme;
                launch.theme = targetTheme;   // AOSP: alias inherits the target activity's theme
                Log.i(TAG, "[B8-ALIASTHEME] " + launch.targetActivity + " theme 0x"
                        + Integer.toHexString(was) + " -> 0x" + Integer.toHexString(targetTheme));
            }
        } catch (Throwable error) {
            // Never fatal: a theme read failure must not kill the launch; the activity keeps its current theme.
            Log.w(TAG, "[B8-ALIASTHEME] target theme resolution skipped: " + error);
        }
    }
}
