package adapter.activity;

import android.app.Activity;
import android.app.Application;
import android.content.Context;
import android.content.ContextWrapper;
import android.content.res.Resources;
import android.content.res.TypedArray;
import android.os.Bundle;
import android.util.TypedValue;

import java.lang.reflect.Field;
import java.lang.reflect.Method;

/**
 * Read-only theme probe for fd-api's "You need to use a Theme.AppCompat theme" (2026-10-03-u13-java-walls-2).
 *
 * DISABLED by default. Armed only when the OH parameter {@code debug.westlake.theme_probe} (read through
 * android.os.SystemProperties, which this runtime routes to OH GetParameter) lists the process's package name
 * (comma separated). When armed it registers ActivityLifecycleCallbacks and, in onActivityPreCreated (right before
 * Activity.onCreate, i.e. before AppCompatDelegateImpl.setContentView checks the theme), prints to stderr:
 *   - the theme resource the Activity holds (ContextThemeWrapper.getThemeResId) and the one in its ActivityInfo,
 *     with names, plus the application theme;
 *   - how the Activity's theme resolves the app's {@code windowActionBar} attribute (the attribute AppCompat checks
 *     via R.styleable.AppCompatTheme) and android:windowActionBar, with the style that supplied each value;
 *   - the theme's attribute-resolution stack (API 29) and the base-context class chain;
 *   - whether this Activity's Resources can name the theme id at all (an AssetManager without the app's package
 *     would resolve nothing).
 * Nothing is changed; every failure is caught and printed.
 */
public final class ThemeProbe {
    private static final String TAG = "[THEME-PROBE] ";
    private static final String PARAM = "debug.westlake.theme_probe";

    private ThemeProbe() {}

    public static void install() {
        try {
            String pkg = currentPackageName();
            String list = systemProperty(PARAM);
            if (pkg == null || list == null || list.isEmpty()) return;
            boolean armed = false;
            for (String p : list.split(",")) {
                if (p.trim().equals(pkg)) armed = true;
            }
            if (!armed) return;
            Application app = currentApplication();
            if (app == null) {
                System.err.println(TAG + "armed pkg=" + pkg + " but ActivityThread.currentApplication() is null");
                return;
            }
            app.registerActivityLifecycleCallbacks(new Callbacks());
            System.err.println(TAG + "armed pkg=" + pkg);
        } catch (Throwable t) {
            System.err.println(TAG + "install failed: " + t);
        }
    }

    private static final class Callbacks implements Application.ActivityLifecycleCallbacks {
        @Override public void onActivityPreCreated(Activity a, Bundle b) { probe(a, "pre-create"); }
        @Override public void onActivityCreated(Activity a, Bundle b) { probe(a, "post-create"); }
        @Override public void onActivityStarted(Activity a) {}
        @Override public void onActivityResumed(Activity a) {}
        @Override public void onActivityPaused(Activity a) {}
        @Override public void onActivityStopped(Activity a) {}
        @Override public void onActivitySaveInstanceState(Activity a, Bundle b) {}
        @Override public void onActivityDestroyed(Activity a) {}
    }

    static void probe(Activity a, String when) {
        String act = a.getClass().getName();
        String p = TAG + when + " " + act + " ";
        try {
            Resources res = a.getResources();
            int held = intCall(a, "getThemeResId");
            int infoTheme = -1;
            String infoName = null;
            Object info = field(a, Activity.class, "mActivityInfo");
            if (info != null) {
                infoTheme = ((Integer) info.getClass().getMethod("getThemeResource").invoke(info));
                Object tgt = info.getClass().getField("targetActivity").get(info);
                infoName = info.getClass().getField("name").get(info) + (tgt != null ? " -> " + tgt : "");
            }
            int appTheme = a.getApplicationInfo().theme;
            System.err.println(p + "themeResId=" + hex(held) + "(" + name(res, held) + ") activityInfo.theme="
                    + hex(infoTheme) + "(" + name(res, infoTheme) + ") info=" + infoName + " appInfo.theme="
                    + hex(appTheme) + "(" + name(res, appTheme) + ")");
            int appAttr = res.getIdentifier("windowActionBar", "attr", a.getPackageName());
            System.err.println(p + "attr app:windowActionBar=" + hex(appAttr) + " " + resolve(a, appAttr)
                    + " | android:windowActionBar " + resolve(a, android.R.attr.windowActionBar));
            if (appAttr != 0) {
                TypedArray ta = a.obtainStyledAttributes(new int[] {appAttr});
                System.err.println(p + "obtainStyledAttributes(app:windowActionBar).hasValue=" + ta.hasValue(0));
                ta.recycle();
            }
            try {
                Method m = Resources.Theme.class.getMethod("getAttributeResolutionStack", int.class, int.class,
                        int.class);
                int[] stack = (int[]) m.invoke(a.getTheme(), 0, 0, 0);
                StringBuilder sb = new StringBuilder();
                for (int id : stack) sb.append(hex(id)).append('(').append(name(res, id)).append(") ");
                System.err.println(p + "theme stack: " + sb);
            } catch (Throwable t) {
                System.err.println(p + "theme stack unavailable: " + t);
            }
            StringBuilder ctx = new StringBuilder();
            Context c = a.getBaseContext();
            for (int i = 0; c != null && i < 6; i++) {
                ctx.append(c.getClass().getName());
                int t = intCall(c, "getThemeResId");
                if (t != -1) ctx.append("[theme ").append(hex(t)).append(']');
                ctx.append(" > ");
                c = (c instanceof ContextWrapper) ? ((ContextWrapper) c).getBaseContext() : null;
            }
            System.err.println(p + "base contexts: " + ctx + " uiMode=" + hex(res.getConfiguration().uiMode));
            Object apk = null;
            try {
                apk = java.util.Arrays.toString((String[]) res.getAssets().getClass().getMethod("getApkPaths")
                        .invoke(res.getAssets()));
            } catch (Throwable t) {
                apk = t.toString();
            }
            System.err.println(p + "assets: " + apk);
        } catch (Throwable t) {
            System.err.println(p + "probe failed: " + t);
        }
    }

    private static String resolve(Activity a, int attr) {
        if (attr == 0) return "attr-not-found";
        TypedValue tv = new TypedValue();
        boolean ok = a.getTheme().resolveAttribute(attr, tv, true);
        if (!ok) return "resolve=false";
        String src = "";
        try {
            int s = TypedValue.class.getField("sourceResourceId").getInt(tv);
            src = " from " + hex(s) + "(" + name(a.getResources(), s) + ")";
        } catch (Throwable ignored) {
            // pre-API 29 TypedValue has no sourceResourceId
        }
        return "resolve=true type=" + tv.type + " data=" + hex(tv.data) + src;
    }

    private static String name(Resources res, int id) {
        if (id == 0 || id == -1) return "-";
        try {
            return res.getResourceName(id);
        } catch (Throwable t) {
            return "NOT-FOUND";
        }
    }

    private static String hex(int v) {
        return v == -1 ? "?" : "0x" + Integer.toHexString(v);
    }

    private static int intCall(Object o, String method) {
        try {
            Method m = findMethod(o.getClass(), method);
            if (m == null) return -1;
            m.setAccessible(true);
            return (Integer) m.invoke(o);
        } catch (Throwable t) {
            return -1;
        }
    }

    private static Method findMethod(Class<?> c, String name) {
        for (; c != null; c = c.getSuperclass()) {
            try {
                return c.getDeclaredMethod(name);
            } catch (NoSuchMethodException ignored) {
                // keep walking up
            }
        }
        return null;
    }

    private static Object field(Object o, Class<?> owner, String name) {
        try {
            Field f = owner.getDeclaredField(name);
            f.setAccessible(true);
            return f.get(o);
        } catch (Throwable t) {
            return null;
        }
    }

    private static String systemProperty(String key) {
        try {
            Class<?> sp = Class.forName("android.os.SystemProperties");
            return (String) sp.getMethod("get", String.class).invoke(null, key);
        } catch (Throwable t) {
            return null;
        }
    }

    private static String currentPackageName() {
        try {
            Class<?> at = Class.forName("android.app.ActivityThread");
            return (String) at.getMethod("currentPackageName").invoke(null);
        } catch (Throwable t) {
            return null;
        }
    }

    private static Application currentApplication() {
        try {
            Class<?> at = Class.forName("android.app.ActivityThread");
            return (Application) at.getMethod("currentApplication").invoke(null);
        } catch (Throwable t) {
            return null;
        }
    }
}
