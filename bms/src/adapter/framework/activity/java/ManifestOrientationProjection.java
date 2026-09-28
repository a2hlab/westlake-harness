/*
 * ManifestOrientationProjection.java
 *
 * Restores the Android activity-orientation contract when an APK is registered
 * through the OpenHarmony BMS compatibility path.  The APK installer already
 * parses screenOrientation, but the current BMS registration bridge does not
 * persist it in InnerAbilityInfo.  The original, installed base.apk therefore
 * remains the authoritative fallback; no application identity or display size
 * is encoded here.
 */
package adapter.activity;

import android.app.Activity;
import android.app.Application;
import android.content.pm.ActivityInfo;
import android.content.pm.ApplicationInfo;
import android.content.res.Configuration;
import android.graphics.Rect;
import android.view.Gravity;
import android.view.SurfaceView;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;
import java.util.concurrent.ConcurrentHashMap;

/** Manifest-driven, fail-open projection for fixed-orientation Android APKs. */
public final class ManifestOrientationProjection {
    private static final String TAG = "ManifestOrientation";
    private static final int NO_ORIENTATION = Integer.MIN_VALUE;

    // OpenHarmony Rosen Orientation values from dm_common.h.  Keep the mapping
    // here beside Android's public ActivityInfo constants so both sides consume
    // one parsed manifest result.
    private static final int OH_VERTICAL = 1;
    private static final int OH_HORIZONTAL = 2;
    private static final int OH_REVERSE_VERTICAL = 3;
    private static final int OH_REVERSE_HORIZONTAL = 4;
    private static final int OH_SENSOR = 5;
    private static final int OH_AUTO_ROTATION_RESTRICTED = 8;
    private static final int OH_AUTO_ROTATION_PORTRAIT_RESTRICTED = 9;
    private static final int OH_AUTO_ROTATION_LANDSCAPE_RESTRICTED = 10;
    private static final int OH_LOCKED = 11;
    private static final int OH_FOLLOW_RECENT = 12;
    private static final int OH_AUTO_ROTATION_UNSPECIFIED = 13;
    private static final int OH_USER_ROTATION_PORTRAIT = 14;
    private static final int OH_USER_ROTATION_LANDSCAPE = 15;

    private static final ConcurrentHashMap<String, Integer> sAndroidOrientations =
            new ConcurrentHashMap<>();
    private static final ConcurrentHashMap<String, Integer> sOhOrientations =
            new ConcurrentHashMap<>();
    private static final ConcurrentHashMap<String, Boolean> sPrivateWindowPolicies =
            new ConcurrentHashMap<>();
    private static final Map<Activity, int[]> sProjectedFrames =
            Collections.synchronizedMap(new WeakHashMap<Activity, int[]>());
    private static boolean sLifecycleInstalled;

    private ManifestOrientationProjection() { }

    /** Lets an already accepted app-private size-compat policy retain ownership. */
    public static void registerPrivateWindowPolicy(String packageName) {
        if (packageName != null && !packageName.isEmpty()) {
            sPrivateWindowPolicies.put(packageName, Boolean.TRUE);
            android.util.Log.i(TAG, "[APK-ORIENTATION] private window policy retained package="
                    + packageName);
        }
    }

    /**
     * Restore only the ActivityInfo field that the BMS bridge omitted. Every
     * other field remains owned by the normal OH-to-Android conversion.
     */
    public static void applyActivityInfo(String packageName, ActivityInfo target) {
        if (target == null || packageName == null || packageName.isEmpty()) return;
        try {
            int orientation = resolveArchiveOrientation(packageName, target.name,
                    target.applicationInfo);
            if (orientation == NO_ORIENTATION) {
                android.util.Log.w(TAG,
                        "[APK-ORIENTATION] archive activity not resolved package="
                        + packageName + " activity=" + target.name
                        + " bms=" + target.screenOrientation);
                return;
            }

            target.screenOrientation = orientation;
            cache(packageName, orientation);
            Application app = currentApplication();
            if (app != null && !hasPrivateWindowPolicy(packageName)) {
                installLifecycleProjection(app);
            }
            android.util.Log.i(TAG, "[APK-ORIENTATION] ActivityInfo package=" + packageName
                    + " activity=" + target.name + " android=" + orientation
                    + " oh=" + androidToOh(orientation));
        } catch (Throwable t) {
            // Orientation recovery must never make an otherwise launchable APK
            // fail.  The frozen oracle will reject the candidate if this path is
            // reached for a fixed-orientation target.
            android.util.Log.e(TAG, "[APK-ORIENTATION] ActivityInfo projection failed", t);
        }
    }

    /** Called by the native Ability scheduler when the parent Session exists. */
    public static int resolveOhOrientation(String packageName, String activityName) {
        if (packageName == null || packageName.isEmpty()) return -1;
        Integer cached = sOhOrientations.get(packageName);
        if (cached != null) return cached;
        try {
            Application app = currentApplication();
            ApplicationInfo appInfo = app != null ? app.getApplicationInfo() : null;
            int androidOrientation = resolveArchiveOrientation(
                    packageName, activityName, appInfo);
            if (androidOrientation == NO_ORIENTATION) return -1;
            cache(packageName, androidOrientation);
            return androidToOh(androidOrientation);
        } catch (Throwable t) {
            android.util.Log.e(TAG, "[APK-ORIENTATION] parent resolution failed", t);
            return -1;
        }
    }

    /**
     * Build the launch configuration that Android WMS would have supplied for
     * the fixed manifest axis.  Width/height come from the current OH display;
     * only their orientation is selected by the manifest.
     */
    public static Configuration projectConfiguration(Configuration base,
            int screenOrientation) {
        if (base == null || axisFor(screenOrientation) == 0) return base;
        Application app = currentApplication();
        if (app != null && hasPrivateWindowPolicy(app.getPackageName())) return base;
        try {
            int[] display = readDisplaySnapshot(base);
            int widthPx = orientWidth(display[0], display[1], screenOrientation);
            int heightPx = orientHeight(display[0], display[1], screenOrientation);
            if (widthPx <= 0 || heightPx <= 0) return base;

            Configuration projected = new Configuration(base);
            int densityDpi = display[2] > 0 ? display[2] : projected.densityDpi;
            if (densityDpi <= 0) {
                densityDpi = android.content.res.Resources.getSystem()
                        .getDisplayMetrics().densityDpi;
            }
            if (densityDpi > 0) {
                projected.densityDpi = densityDpi;
                projected.screenWidthDp = Math.max(1,
                        Math.round(widthPx * 160.0f / densityDpi));
                projected.screenHeightDp = Math.max(1,
                        Math.round(heightPx * 160.0f / densityDpi));
                projected.smallestScreenWidthDp = Math.min(
                        projected.screenWidthDp, projected.screenHeightDp);
                setIntField(projected, "compatScreenWidthDp", projected.screenWidthDp);
                setIntField(projected, "compatScreenHeightDp", projected.screenHeightDp);
                setIntField(projected, "compatSmallestScreenWidthDp",
                        projected.smallestScreenWidthDp);
            }
            projected.orientation = widthPx >= heightPx
                    ? Configuration.ORIENTATION_LANDSCAPE
                    : Configuration.ORIENTATION_PORTRAIT;
            setWindowBounds(projected, widthPx, heightPx,
                    display[0] == widthPx && display[1] == heightPx ? display[3] : -1);
            android.util.Log.i(TAG, "[APK-ORIENTATION] launch config android="
                    + screenOrientation + " pixels=" + widthPx + "x" + heightPx
                    + " dp=" + projected.screenWidthDp + "x"
                    + projected.screenHeightDp + " display=" + display[0] + "x"
                    + display[1] + " rotation=" + display[3]);
            return projected;
        } catch (Throwable t) {
            android.util.Log.e(TAG, "[APK-ORIENTATION] Configuration projection failed", t);
            return base;
        }
    }

    /** Smali-friendly overload: both launch locals occupy adjacent registers. */
    public static Configuration projectConfiguration(ActivityInfo activityInfo,
            Configuration base) {
        return projectConfiguration(base, activityInfo == null
                ? ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
                : activityInfo.screenOrientation);
    }

    private static synchronized void installLifecycleProjection(Application app) {
        if (sLifecycleInstalled) return;
        app.registerActivityLifecycleCallbacks(new Application.ActivityLifecycleCallbacks() {
            @Override
            public void onActivityPreCreated(Activity activity, android.os.Bundle state) {
                prepareWindow(activity);
            }

            @Override
            public void onActivityCreated(Activity activity, android.os.Bundle state) {
                applySurface(activity, "created");
            }

            @Override
            public void onActivityResumed(Activity activity) {
                applySurface(activity, "resumed");
            }

            @Override public void onActivityStarted(Activity activity) { }
            @Override public void onActivityPaused(Activity activity) { }
            @Override public void onActivityStopped(Activity activity) { }
            @Override public void onActivitySaveInstanceState(Activity activity,
                    android.os.Bundle state) { }
            @Override public void onActivityDestroyed(Activity activity) {
                sProjectedFrames.remove(activity);
            }
        });
        sLifecycleInstalled = true;
        android.util.Log.i(TAG, "[APK-ORIENTATION] lifecycle projection registered");
    }

    private static void prepareWindow(Activity activity) {
        if (activity == null) return;
        if (hasPrivateWindowPolicy(activity.getPackageName())) return;
        Integer orientation = sAndroidOrientations.get(activity.getPackageName());
        if (orientation == null || axisFor(orientation) == 0) return;
        try {
            Window window = activity.getWindow();
            WindowManager.LayoutParams attributes = window.getAttributes();
            // Respect any earlier application-private size-compat policy.  The
            // generic projection owns only an otherwise MATCH_PARENT/default
            // fixed-orientation window.
            if (attributes.width > 0 || attributes.height > 0) {
                android.util.Log.i(TAG, "[APK-ORIENTATION] explicit window frame retained package="
                        + activity.getPackageName() + " frame=" + attributes.width + "x"
                        + attributes.height);
                return;
            }

            int[] display = readDisplaySnapshot(activity.getResources().getConfiguration());
            int width = orientWidth(display[0], display[1], orientation);
            int height = orientHeight(display[0], display[1], orientation);
            if (width <= 0 || height <= 0) return;
            attributes.width = width;
            attributes.height = height;
            attributes.gravity = Gravity.TOP | Gravity.START;
            window.setAttributes(attributes);
            sProjectedFrames.put(activity, new int[] { width, height });
            android.util.Log.i(TAG, "[APK-ORIENTATION] preCreate window=" + width + "x"
                    + height + " package=" + activity.getPackageName());
        } catch (Throwable t) {
            android.util.Log.e(TAG, "[APK-ORIENTATION] preCreate window failed", t);
        }
    }

    private static void applySurface(Activity activity, String phase) {
        int[] frame = sProjectedFrames.get(activity);
        if (frame == null) return;
        try {
            View decor = activity.getWindow().getDecorView();
            SurfaceView surface = findFirstSurfaceView(decor);
            if (surface == null) {
                android.util.Log.w(TAG, "[APK-ORIENTATION] " + phase
                        + " SurfaceView unavailable");
                return;
            }
            ViewGroup.LayoutParams params = surface.getLayoutParams();
            if (params != null) {
                params.width = frame[0];
                params.height = frame[1];
                surface.setLayoutParams(params);
            }
            surface.getHolder().setFixedSize(frame[0], frame[1]);
            surface.requestLayout();
            android.util.Log.i(TAG, "[APK-ORIENTATION] " + phase + " SurfaceView="
                    + frame[0] + "x" + frame[1]);
        } catch (Throwable t) {
            android.util.Log.e(TAG, "[APK-ORIENTATION] " + phase
                    + " SurfaceView projection failed", t);
        }
    }

    private static SurfaceView findFirstSurfaceView(View view) {
        if (view instanceof SurfaceView) return (SurfaceView) view;
        if (!(view instanceof ViewGroup)) return null;
        ViewGroup group = (ViewGroup) view;
        for (int i = 0; i < group.getChildCount(); i++) {
            SurfaceView found = findFirstSurfaceView(group.getChildAt(i));
            if (found != null) return found;
        }
        return null;
    }

    private static int resolveArchiveOrientation(String packageName, String activityName,
            ApplicationInfo suppliedInfo) throws Exception {
        Application app = currentApplication();
        if (app == null) return NO_ORIENTATION;
        String apkPath = suppliedInfo != null ? suppliedInfo.sourceDir : null;
        if (apkPath == null || !new java.io.File(apkPath).isFile()) {
            apkPath = app.getPackageCodePath();
        }
        if (apkPath == null || !new java.io.File(apkPath).isFile()) {
            return NO_ORIENTATION;
        }

        return BinaryAndroidManifestOrientation.read(
                apkPath, packageName, activityName);
    }

    private static Application currentApplication() {
        try {
            Class<?> activityThread = Class.forName("android.app.ActivityThread");
            Method method = activityThread.getDeclaredMethod("currentApplication");
            method.setAccessible(true);
            Object result = method.invoke(null);
            return result instanceof Application ? (Application) result : null;
        } catch (Throwable ignored) {
            return null;
        }
    }

    private static void cache(String packageName, int androidOrientation) {
        sAndroidOrientations.put(packageName, androidOrientation);
        int oh = androidToOh(androidOrientation);
        if (oh >= 0) sOhOrientations.put(packageName, oh);
    }

    private static boolean hasPrivateWindowPolicy(String packageName) {
        return packageName != null && sPrivateWindowPolicies.containsKey(packageName);
    }

    private static int axisFor(int orientation) {
        switch (orientation) {
            case ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE:
            case ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE:
            case ActivityInfo.SCREEN_ORIENTATION_REVERSE_LANDSCAPE:
            case ActivityInfo.SCREEN_ORIENTATION_USER_LANDSCAPE:
                return Configuration.ORIENTATION_LANDSCAPE;
            case ActivityInfo.SCREEN_ORIENTATION_PORTRAIT:
            case ActivityInfo.SCREEN_ORIENTATION_SENSOR_PORTRAIT:
            case ActivityInfo.SCREEN_ORIENTATION_REVERSE_PORTRAIT:
            case ActivityInfo.SCREEN_ORIENTATION_USER_PORTRAIT:
                return Configuration.ORIENTATION_PORTRAIT;
            default:
                return 0;
        }
    }

    private static int orientWidth(int width, int height, int orientation) {
        return axisFor(orientation) == Configuration.ORIENTATION_LANDSCAPE
                ? Math.max(width, height) : Math.min(width, height);
    }

    private static int orientHeight(int width, int height, int orientation) {
        return axisFor(orientation) == Configuration.ORIENTATION_LANDSCAPE
                ? Math.min(width, height) : Math.max(width, height);
    }

    private static int androidToOh(int orientation) {
        switch (orientation) {
            case ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE: return OH_HORIZONTAL;
            case ActivityInfo.SCREEN_ORIENTATION_PORTRAIT: return OH_VERTICAL;
            case ActivityInfo.SCREEN_ORIENTATION_USER: return OH_AUTO_ROTATION_RESTRICTED;
            case ActivityInfo.SCREEN_ORIENTATION_BEHIND: return OH_FOLLOW_RECENT;
            case ActivityInfo.SCREEN_ORIENTATION_SENSOR: return OH_SENSOR;
            case ActivityInfo.SCREEN_ORIENTATION_NOSENSOR: return OH_AUTO_ROTATION_UNSPECIFIED;
            case ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE:
                return OH_AUTO_ROTATION_LANDSCAPE_RESTRICTED;
            case ActivityInfo.SCREEN_ORIENTATION_SENSOR_PORTRAIT:
                return OH_AUTO_ROTATION_PORTRAIT_RESTRICTED;
            case ActivityInfo.SCREEN_ORIENTATION_REVERSE_LANDSCAPE:
                return OH_REVERSE_HORIZONTAL;
            case ActivityInfo.SCREEN_ORIENTATION_REVERSE_PORTRAIT:
                return OH_REVERSE_VERTICAL;
            case ActivityInfo.SCREEN_ORIENTATION_FULL_SENSOR: return OH_SENSOR;
            case ActivityInfo.SCREEN_ORIENTATION_USER_LANDSCAPE:
                return OH_USER_ROTATION_LANDSCAPE;
            case ActivityInfo.SCREEN_ORIENTATION_USER_PORTRAIT:
                return OH_USER_ROTATION_PORTRAIT;
            case ActivityInfo.SCREEN_ORIENTATION_FULL_USER:
                return OH_AUTO_ROTATION_RESTRICTED;
            case ActivityInfo.SCREEN_ORIENTATION_LOCKED: return OH_LOCKED;
            default: return -1;
        }
    }

    /** {logicalWidth, logicalHeight, densityDpi, rotation}. */
    private static int[] readDisplaySnapshot(Configuration fallback) throws Exception {
        int width = 0;
        int height = 0;
        int density = fallback != null ? fallback.densityDpi : 0;
        int rotation = -1;
        try {
            Class<?> adapter = Class.forName("adapter.window.DisplayManagerAdapter");
            Object instance = adapter.getMethod("getInstance").invoke(null);
            Object info = adapter.getMethod("getDisplayInfo", int.class).invoke(instance, 0);
            if (info != null) {
                width = readIntField(info, "logicalWidth", 0);
                height = readIntField(info, "logicalHeight", 0);
                density = readIntField(info, "logicalDensityDpi", density);
                rotation = readIntField(info, "rotation", -1);
            }
        } catch (Throwable t) {
            android.util.Log.w(TAG, "[APK-ORIENTATION] DisplayInfo reflection failed", t);
        }
        if (width <= 0 || height <= 0) {
            android.util.DisplayMetrics metrics = android.content.res.Resources.getSystem()
                    .getDisplayMetrics();
            width = metrics.widthPixels;
            height = metrics.heightPixels;
            if (density <= 0) density = metrics.densityDpi;
        }
        return new int[] { width, height, density, rotation };
    }

    private static int readIntField(Object owner, String name, int fallback) {
        try {
            Field field = owner.getClass().getField(name);
            return field.getInt(owner);
        } catch (Throwable ignored) {
            return fallback;
        }
    }

    private static void setIntField(Object owner, String name, int value) {
        try {
            Field field = owner.getClass().getField(name);
            field.setInt(owner, value);
        } catch (Throwable ignored) { }
    }

    private static void setWindowBounds(Configuration configuration, int width, int height,
            int currentRotation) {
        try {
            Field field = Configuration.class.getField("windowConfiguration");
            Object windowConfiguration = field.get(configuration);
            if (windowConfiguration == null) return;
            Rect bounds = new Rect(0, 0, width, height);
            Class<?> type = windowConfiguration.getClass();
            type.getMethod("setBounds", Rect.class).invoke(windowConfiguration, bounds);
            type.getMethod("setAppBounds", Rect.class).invoke(windowConfiguration, bounds);
            type.getMethod("setMaxBounds", Rect.class).invoke(windowConfiguration, bounds);
            if (currentRotation >= 0) {
                invokeIntIfPresent(type, windowConfiguration, "setRotation", currentRotation);
                invokeIntIfPresent(type, windowConfiguration,
                        "setDisplayRotation", currentRotation);
            }
        } catch (Throwable t) {
            android.util.Log.w(TAG, "[APK-ORIENTATION] window bounds reflection failed", t);
        }
    }

    private static void invokeIntIfPresent(Class<?> type, Object target, String name, int value) {
        try {
            type.getMethod(name, int.class).invoke(target, value);
        } catch (Throwable ignored) { }
    }
}
