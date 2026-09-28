package adapter.activity;

/**
 * APK-private fixed-orientation projection for Capybara Adventure.
 *
 * Android WMS runs this non-resizeable landscape Activity in a top-aligned
 * size-compat frame on a portrait display.  The OH adapter does not yet have
 * that task-level policy, so project this APK's existing Unity SurfaceView
 * into the same frame without changing the APK.
 */
public final class CapybaraLetterboxProjection {
    private static final String PACKAGE = "com.Revenko.org.CapybaraAdventure";
    private static final String TAG = "CapybaraProjection";
    private static boolean sInstalled;

    private CapybaraLetterboxProjection() { }

    public static synchronized void install(android.app.Application app,
            String bundleName) {
        if (!PACKAGE.equals(bundleName) || app == null) return;
        ManifestOrientationProjection.registerPrivateWindowPolicy(bundleName);
        if (sInstalled) return;

        app.registerActivityLifecycleCallbacks(
                new android.app.Application.ActivityLifecycleCallbacks() {
            @Override
            public void onActivityPreCreated(android.app.Activity activity,
                    android.os.Bundle state) {
                // ActivityThread invokes this before the APK's onCreate.  Set
                // the size-compat window before Unity constructs its
                // top-aligned SurfaceView, EGL surface, and first producer
                // buffers.
                prepareWindow(activity, "preCreate");
            }

            @Override
            public void onActivityCreated(android.app.Activity activity,
                    android.os.Bundle state) {
                apply(activity);
            }

            @Override
            public void onActivityResumed(android.app.Activity activity) {
                // Unity may rebuild its GL view after a foreground cycle.
                apply(activity);
            }

            @Override public void onActivityStarted(android.app.Activity activity) { }
            @Override public void onActivityPaused(android.app.Activity activity) { }
            @Override public void onActivityStopped(android.app.Activity activity) { }
            @Override public void onActivitySaveInstanceState(android.app.Activity activity,
                    android.os.Bundle state) { }
            @Override public void onActivityDestroyed(android.app.Activity activity) { }
        });
        sInstalled = true;
        android.util.Log.i(TAG, "[CAPY-LETTERBOX] lifecycle callback registered");
    }

    private static void apply(android.app.Activity activity) {
        if (activity == null || !PACKAGE.equals(activity.getPackageName())) return;

        try {
            int[] frame = prepareWindow(activity, "apply");
            if (frame == null) return;
            int targetWidth = frame[0];
            int targetHeight = frame[1];
            int realWidth = frame[2];
            int realHeight = frame[3];

            Object unityPlayer = findFieldValue(activity, "mUnityPlayer");
            if (unityPlayer == null) {
                android.util.Log.w(TAG,
                        "[CAPY-LETTERBOX] mUnityPlayer unavailable after onCreate");
                return;
            }

            // Resource metrics exclude system-bar insets on this portrait OH
            // display (1200x1790), which incorrectly projects the Android
            // landscape frame to 1200x804. Android size-compat uses the
            // physical 1200x1920 display and therefore produces 1200x750.
            if (unityPlayer instanceof android.view.View) {
                ((android.view.View) unityPlayer).setBackgroundColor(
                        android.graphics.Color.BLACK);
            }
            android.view.View decor = activity.getWindow().getDecorView();
            android.view.View content = decor.findViewById(android.R.id.content);
            if (content != null) {
                content.setBackgroundColor(android.graphics.Color.BLACK);
            }
            android.view.SurfaceView surface = findFirstSurfaceView(unityPlayer);
            if (surface == null) {
                android.util.Log.w(TAG,
                        "[CAPY-LETTERBOX] Unity main SurfaceView not found");
                return;
            }
            android.view.ViewGroup.LayoutParams base = surface.getLayoutParams();
            if (base instanceof android.widget.FrameLayout.LayoutParams) {
                android.widget.FrameLayout.LayoutParams lp =
                        (android.widget.FrameLayout.LayoutParams) base;
                lp.width = targetWidth;
                lp.height = targetHeight;
                lp.gravity = android.view.Gravity.TOP
                        | android.view.Gravity.CENTER_HORIZONTAL;
                surface.setLayoutParams(lp);
            } else {
                android.util.Log.w(TAG, "[CAPY-LETTERBOX] unexpected layout params="
                        + (base == null ? "null" : base.getClass().getName()));
                return;
            }
            // A layout-only resize changes composition, but the OH-backed
            // BufferQueue can retain its old 1200x1920 default.  A fixed holder
            // size also changes ANativeWindow width/height, which is what Unity
            // uses to rebuild the render target and camera aspect.
            surface.getHolder().setFixedSize(targetWidth, targetHeight);
            surface.requestLayout();
            android.util.Log.i(TAG, "[CAPY-LETTERBOX] applied frame="
                    + targetWidth + "x" + targetHeight
                    + " realDisplay=" + realWidth + "x" + realHeight
                    + " gravity=TOP|CENTER_HORIZONTAL");
        } catch (Throwable t) {
            android.util.Log.e(TAG, "[CAPY-LETTERBOX] apply failed", t);
        }
    }

    private static int[] prepareWindow(android.app.Activity activity, String phase) {
        if (activity == null || !PACKAGE.equals(activity.getPackageName())) return null;
        try {
            android.util.DisplayMetrics realMetrics = new android.util.DisplayMetrics();
            activity.getWindowManager().getDefaultDisplay().getRealMetrics(realMetrics);
            int shortPx = Math.min(realMetrics.widthPixels, realMetrics.heightPixels);
            int longPx = Math.max(realMetrics.widthPixels, realMetrics.heightPixels);
            if (shortPx <= 0 || longPx <= 0) return null;
            int targetWidth = shortPx;
            int targetHeight = Math.round((float) shortPx * (float) shortPx
                    / (float) longPx);

            android.view.Window window = activity.getWindow();
            window.setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(
                    android.graphics.Color.BLACK));
            window.setStatusBarColor(android.graphics.Color.TRANSPARENT);
            window.setNavigationBarColor(android.graphics.Color.BLACK);
            window.setFlags(android.view.WindowManager.LayoutParams.FLAG_FULLSCREEN,
                    android.view.WindowManager.LayoutParams.FLAG_FULLSCREEN);
            android.view.WindowManager.LayoutParams attributes = window.getAttributes();
            attributes.width = targetWidth;
            attributes.height = targetHeight;
            attributes.gravity = android.view.Gravity.TOP
                    | android.view.Gravity.CENTER_HORIZONTAL;
            window.setAttributes(attributes);
            android.view.View decor = window.getDecorView();
            decor.setBackgroundColor(android.graphics.Color.BLACK);
            decor.setSystemUiVisibility(
                    android.view.View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                    | android.view.View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    | android.view.View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                    | android.view.View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    | android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                    | android.view.View.SYSTEM_UI_FLAG_FULLSCREEN);
            android.util.Log.i(TAG, "[CAPY-LETTERBOX] " + phase + " target="
                    + targetWidth + "x" + targetHeight + " realDisplay="
                    + realMetrics.widthPixels + "x" + realMetrics.heightPixels);
            return new int[] { targetWidth, targetHeight,
                    realMetrics.widthPixels, realMetrics.heightPixels };
        } catch (Throwable t) {
            android.util.Log.e(TAG, "[CAPY-LETTERBOX] " + phase + " failed", t);
            return null;
        }
    }

    private static Object findFieldValue(Object target, String name) {
        for (Class<?> type = target.getClass(); type != null; type = type.getSuperclass()) {
            try {
                java.lang.reflect.Field field = type.getDeclaredField(name);
                field.setAccessible(true);
                return field.get(target);
            } catch (NoSuchFieldException ignored) {
                // Continue through the Activity superclass chain.
            } catch (Throwable t) {
                return null;
            }
        }
        return null;
    }

    private static android.view.SurfaceView findFirstSurfaceView(Object root) {
        if (root instanceof android.view.SurfaceView) {
            return (android.view.SurfaceView) root;
        }
        if (!(root instanceof android.view.ViewGroup)) return null;

        android.view.ViewGroup group = (android.view.ViewGroup) root;
        for (int i = 0; i < group.getChildCount(); i++) {
            android.view.SurfaceView found = findFirstSurfaceView(group.getChildAt(i));
            if (found != null) return found;
        }
        return null;
    }
}
