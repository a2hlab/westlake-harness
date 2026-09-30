/* J3 (#fd-api): single-purpose file (freeze unit) -- an activity-alias target keeps its OWN theme. */
package adapter.activity;

import android.content.pm.ActivityInfo;

/**
 * B8 (#fd-api, J3): when OH launches an activity-alias, ScheduleLaunchAbility builds the ActivityInfo
 * for the ALIAS and resolveActivityTheme fills the ALIAS's theme (termux:API's
 * TermuxAPILauncherActivity resolves to 0x1030237 = @android:style/Theme.Translucent.NoTitleBar, which
 * makes the launcher invisible). LaunchActivityAliasProjection.apply then rewrites
 * ActivityInfo.targetActivity to the real class (TermuxAPIMainActivity, an AppCompatActivity) but
 * deliberately leaves theme/flags untouched -- so ActivityThread instantiates the TARGET with the
 * alias's non-Theme.AppCompat theme and AppCompat's onCreate throws "You need to use a Theme.AppCompat
 * theme (or descendant)".
 *
 * Re-resolve the theme for the TARGET activity (its own android:theme, else the application theme --
 * an AppCompat descendant for an AppCompat app) so performLaunchActivity applies a theme that matches
 * the class it actually creates. Called from AppSchedulerBridge immediately AFTER
 * LaunchActivityAliasProjection.apply, so launch.targetActivity is already set. Its own file (added
 * class, freeze-friendly) because LaunchActivityAliasProjection ships in the b5 baseline and the build
 * keeps the baseline copy -- a fix there would be skipped, so the seam must be a new injected helper.
 * Ordinary (non-alias) activities have targetActivity == null and are left untouched.
 */
public final class AliasTargetTheme {
    private AliasTargetTheme() {}

    public static void apply(ActivityInfo launch) {
        if (launch == null) return;
        String target = launch.targetActivity;
        if (target == null || target.isEmpty() || target.equals(launch.name)) return;
        try {
            int targetTheme = ManifestJsonFallback.activityTheme(launch.packageName, target);
            if (targetTheme != 0 && targetTheme != launch.theme) {
                int prev = launch.theme;
                launch.theme = targetTheme;
                System.err.println("[B8-ALIASTHEME] " + target + " theme re-resolved 0x"
                        + Integer.toHexString(prev) + " -> 0x" + Integer.toHexString(targetTheme));
            } else {
                System.err.println("[B8-ALIASTHEME] " + target + " theme unchanged (0x"
                        + Integer.toHexString(launch.theme) + "); activityTheme returned 0x"
                        + Integer.toHexString(targetTheme));
            }
        } catch (Throwable t) {
            System.err.println("[B8-ALIASTHEME] target theme re-resolve failed for " + target + ": " + t);
        }
    }
}
