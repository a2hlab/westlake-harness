/* J10d (#appcompat-actionbar-theme): single-purpose file (freeze unit) -- give a launching activity its
 * OWN manifest android:theme just before scheduleTransaction, so performLaunchActivity.setTheme uses the
 * activity's (e.g. *.NoActionBar) theme instead of the application's parent theme. */
package adapter.activity;

import android.content.pm.ActivityInfo;

/**
 * J10d cluster <b>appcompat-actionbar</b> (deadhash/knot/diaspora/memory/yahtzeedicer/advancedpassgen/
 * itsdicey/textpad). <b>Root cause (proven by the J10c diagnostic window on 5ea):</b> the launching
 * activity ends up resolved against the APPLICATION theme (knot: Theme.Knot, {@code windowActionBar=true}),
 * not the manifest activity theme (knot MainActivity: {@code Theme.Knot.NoActionBar} = 0x7f11019e,
 * {@code windowActionBar=false}). AppCompatDelegateImpl.createSubDecor reads the app's own androidx
 * {@code windowActionBar} and, seeing true, requests FEATURE_SUPPORT_ACTION_BAR -&gt; WindowDecorActionBar
 * -&gt; setSupportActionBar throws "This Activity already has an action bar supplied by the window decor".
 *
 * Why the activity gets the app theme: {@code AppSchedulerBridge.nativeOnScheduleLaunchAbility}, right
 * before {@code scheduleTransaction}, overwrites {@code activityInfo.theme} with the enriched/app theme
 * (and the newer source force-zeros it); {@code ActivityInfo.getThemeResource()} then returns
 * {@code applicationInfo.theme} (AOSP 14 ActivityThread.performLaunchActivity:3745 ->
 * ActivityInfo.getThemeResource:1585 {@code theme != 0 ? theme : applicationInfo.theme}).
 * {@code [B47-SLA]} logged the correct {@code activityInfo.theme=0x7f11019e} earlier, before that overwrite.
 *
 * <b>Fix:</b> just before scheduleTransaction, set {@code activityInfo.theme} back to the activity's OWN
 * manifest theme ({@link ManifestJsonFallback#activityTheme(String, String)}, the same source
 * SelfComponentFallback.correctSelfActivityTheme uses). Marker:
 * {@code [J10d-THEME] <activity> theme=0x.. (manifest 0x..)}. No-op (logged) when the manifest has no
 * activity theme.
 */
public final class J10dTheme {
    private J10dTheme() {}

    /** Called from AppSchedulerBridge.nativeOnScheduleLaunchAbility just before scheduleTransaction. */
    public static void restore(ActivityInfo ai) {
        try {
            if (ai == null || ai.name == null) return;
            String pkg = ai.applicationInfo != null && ai.applicationInfo.packageName != null
                    ? ai.applicationInfo.packageName : ai.packageName;
            if (pkg == null) return;
            int theme = ManifestJsonFallback.activityTheme(pkg, ai.name);
            if (theme != 0 && theme != ai.theme) {
                int prev = ai.theme;
                ai.theme = theme;
                System.err.println("[J10d-THEME] " + ai.name + " theme=0x" + Integer.toHexString(theme)
                        + " (manifest 0x" + Integer.toHexString(theme) + "; was 0x" + Integer.toHexString(prev) + ")");
            } else if (theme != 0) {
                System.err.println("[J10d-THEME] " + ai.name + " theme=0x" + Integer.toHexString(theme)
                        + " (manifest 0x" + Integer.toHexString(theme) + "; already set)");
            }
        } catch (Throwable t) {
            System.err.println("[J10d-THEME] restore failed: " + t);
        }
    }
}
