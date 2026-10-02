package adapter.activity;

import android.app.Activity;
import android.app.Application;
import android.content.Context;
import android.content.ContextWrapper;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;

import java.lang.ref.WeakReference;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Map;

/**
 * Android's ordering for a service bound from Activity.onCreate (2026-10-03-termux-and-u12-jar-check).
 *
 * On Android the launch transaction carries LaunchActivityItem plus its ResumeActivityItem, so onCreate, onStart and
 * onResume run in one main-looper message, and a ServiceConnection queued from onCreate is delivered after onResume.
 * On route A the launch transaction only creates the Activity; onStart/onResume come from a later RESUMED transaction
 * (OH FOREGROUND). ActivityManagerBindProxy.postInProcessBind queues the in-process create+bind+onServiceConnected
 * runnable from inside onCreate, so it runs BEFORE onStart. Termux checks its onStart-set mIsVisible in
 * onServiceConnected and finishes itself when it is false (U10.1T8: white, TermuxActivity finished 2 ms after
 * connect).
 *
 * wrap(): postInProcessBind still posts, but the runnable it posts is wrapped. When the wrapper runs (first main-looper
 * turn after onCreate) and the connection belongs to an Activity whose ActivityClientRecord is still before ON_START,
 * the bind is held until that Activity's onActivityPostStarted (per-Activity lifecycle callbacks, API 29) and then
 * posted, which lands after the onResume of the same RESUMED transaction, as on Android. If the Activity is destroyed
 * first, the bind is dropped (it died with the Activity). Everything else, including every failure to identify the
 * Activity, runs the bind immediately exactly as before.
 */
public final class InProcessBindOrder {
    private static final int ON_START = 2;

    private InProcessBindOrder() {}

    public static Runnable wrap(final Runnable bind, final Object connection) {
        return new Runnable() {
            @Override
            public void run() {
                hold(bind, connection);
            }
        };
    }

    static void hold(final Runnable bind, Object connection) {
        Activity activity = null;
        int state = -1;
        try {
            activity = activityOf(connection);
            if (activity != null) state = lifecycleState(activity);
        } catch (Throwable t) {
            activity = null;
        }
        if (activity == null || state < 0 || state >= ON_START || activity.isFinishing()) {
            bind.run();
            return;
        }
        final String name = activity.getClass().getName();
        System.err.println("[B8-AMB-ORDER] holding in-process bind until " + name + " is started (state=" + state + ")");
        activity.registerActivityLifecycleCallbacks(new Application.ActivityLifecycleCallbacks() {
            private boolean done;

            @Override public void onActivityPostStarted(Activity a) {
                if (done) return;
                done = true;
                a.unregisterActivityLifecycleCallbacks(this);
                System.err.println("[B8-AMB-ORDER] " + name + " started; delivering in-process bind after this transaction");
                new Handler(Looper.getMainLooper()).post(bind);
            }

            @Override public void onActivityDestroyed(Activity a) {
                if (done) return;
                done = true;
                a.unregisterActivityLifecycleCallbacks(this);
                System.err.println("[B8-AMB-ORDER] " + name + " destroyed before start; in-process bind dropped");
            }

            @Override public void onActivityCreated(Activity a, Bundle b) {}
            @Override public void onActivityStarted(Activity a) {}
            @Override public void onActivityResumed(Activity a) {}
            @Override public void onActivityPaused(Activity a) {}
            @Override public void onActivityStopped(Activity a) {}
            @Override public void onActivitySaveInstanceState(Activity a, Bundle b) {}
        });
    }

    /** IServiceConnection (LoadedApk$ServiceDispatcher$InnerConnection) -> its dispatcher's Context -> Activity. */
    static Activity activityOf(Object connection) throws Exception {
        if (connection == null) return null;
        Object ref = field(connection, "mDispatcher");
        Object dispatcher = ref instanceof WeakReference ? ((WeakReference<?>) ref).get() : null;
        if (dispatcher == null) return null;
        Object ctx = field(dispatcher, "mContext");
        for (int i = 0; ctx instanceof Context && i < 8; i++) {
            if (ctx instanceof Activity) return (Activity) ctx;
            ctx = ctx instanceof ContextWrapper ? ((ContextWrapper) ctx).getBaseContext() : null;
        }
        return null;
    }

    /** ActivityThread.mActivities[activity.mToken].getLifecycleState(): 0 pre-create, 1 ON_CREATE, 2 ON_START ... */
    static int lifecycleState(Activity activity) throws Exception {
        Class<?> at = Class.forName("android.app.ActivityThread");
        Object thread = at.getMethod("currentActivityThread").invoke(null);
        Object token = field(activity, "mToken");
        Object map = field(thread, "mActivities");
        if (!(map instanceof Map) || token == null) return -1;
        Object record = ((Map<?, ?>) map).get(token);
        if (record == null) return -1;
        Method m = record.getClass().getDeclaredMethod("getLifecycleState");
        m.setAccessible(true);
        return (Integer) m.invoke(record);
    }

    private static Object field(Object o, String name) throws Exception {
        for (Class<?> c = o.getClass(); c != null; c = c.getSuperclass()) {
            try {
                Field f = c.getDeclaredField(name);
                f.setAccessible(true);
                return f.get(o);
            } catch (NoSuchFieldException ignored) {
                // keep walking up
            }
        }
        return null;
    }
}
