import android.content.ComponentName;
import android.content.Intent;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;

import java.lang.ref.WeakReference;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.Map;

/**
 * Host-ART ordering harness for the termux wall (benchmark/2026-10-03-u14-jar-v1), on the boards' boot class path.
 *
 * Real code under test: the runtime jar's ActivityManagerBindProxy.postInProcessBind (with or without the U14 needle)
 * and InProcessBindOrder; framework.jar's Handler / MessageQueue.enqueueMessage / Message, Activity's per-Activity
 * lifecycle callback dispatch (dispatchActivityPostStarted / dispatchActivityDestroyed, registerActivityLifecycleCallbacks),
 * ActivityThread.ActivityClientRecord's lifecycle state, LoadedApk.ServiceDispatcher(.InnerConnection) fields.
 *
 * Stand-ins (host ART has none of libandroid_runtime's natives): the main Looper and its MessageQueue are allocated
 * without their constructors (no nativeInit) and the queue is drained by hand in FIFO order instead of Looper.loop
 * (nativePollOnce); ActivityThread.sCurrentActivityThread is an allocated ActivityThread whose mActivities holds the
 * test Activity's record. The "RESUMED transaction" that OH's FOREGROUND callback posts 5 ms after onCreate's bind
 * (U10.1T8 termux) is modelled as one main-looper message: record ON_START, TermuxActivity.onStart (mIsVisible = true),
 * Activity.dispatchActivityPostStarted (real), record ON_RESUME. Every message runs, including the real bind runnable
 * ActivityManagerBindProxy$1: a RecordingService is pre-registered in ActivityManagerBindProxy.sServices under
 * TermuxService's class name, so $1 takes its "service already created" branch and calls RecordingService.onBind,
 * which records the Activity's lifecycle state and mIsVisible at that moment (what TermuxActivity.onServiceConnected
 * checks right after onBind returns).
 */
public class BindOrderAndroidTest {
    static Object unsafe;
    static Method allocate;
    static Object queue;
    static int ON_CREATE, ON_START, ON_RESUME;
    static int failures;
    static Launch current;

    /** Stands in for an already-created TermuxService: records when the real bind path reaches onBind. */
    public static class RecordingService extends android.app.Service {
        @Override public IBinder onBind(Intent intent) {
            try {
                if (current != null && current.delivered == null) {
                    current.delivered = "state=" + current.state() + " mIsVisible=" + current.visible;
                }
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
            return null;
        }
    }

    static Object alloc(String cls) throws Exception { return allocate.invoke(unsafe, Class.forName(cls)); }

    static Field field(Class<?> c, String n) throws Exception {
        for (Class<?> k = c; k != null; k = k.getSuperclass()) {
            try {
                Field f = k.getDeclaredField(n);
                f.setAccessible(true);
                return f;
            } catch (NoSuchFieldException ignored) { }
        }
        throw new NoSuchFieldException(c.getName() + "." + n);
    }

    static void set(Object o, String n, Object v) throws Exception { field(o.getClass(), n).set(o, v); }
    static Object get(Object o, String n) throws Exception { return field(o.getClass(), n).get(o); }
    static void setStatic(String cls, String n, Object v) throws Exception { field(Class.forName(cls), n).set(null, v); }

    static Object call(Object o, String name) throws Exception {
        for (Class<?> k = o.getClass(); k != null; k = k.getSuperclass()) {
            try {
                Method m = k.getDeclaredMethod(name);
                m.setAccessible(true);
                return m.invoke(o);
            } catch (NoSuchMethodException ignored) { }
        }
        throw new NoSuchMethodException(name);
    }

    /** One launch: a TermuxActivity-like Activity at `initialState` binds in-process; then `tx` is posted. */
    static class Launch {
        final Object activity, record, connection;
        boolean visible;          // TermuxActivity.mIsVisible, set in onStart
        String delivered;         // state when ActivityManagerBindProxy$1 reached the head of the main queue

        Launch(int initialState, boolean identifiable) throws Exception {
            activity = alloc("android.app.Activity");
            IBinder token = (IBinder) Proxy.newProxyInstance(IBinder.class.getClassLoader(),
                    new Class<?>[] {IBinder.class}, (p, m, a) -> m.getName().equals("hashCode")
                            ? System.identityHashCode(p) : m.getName().equals("equals") ? p == a[0] : null);
            set(activity, "mToken", token);
            set(activity, "mActivityLifecycleCallbacks", new ArrayList<>());
            Object app = alloc("android.app.Application");
            set(app, "mActivityLifecycleCallbacks", new ArrayList<>());
            set(activity, "mApplication", app);
            Class<?> acr = Class.forName("android.app.ActivityThread$ActivityClientRecord");
            Object r;
            try {
                Constructor<?> c = acr.getDeclaredConstructor();
                c.setAccessible(true);
                r = c.newInstance();
            } catch (Throwable t) {
                r = allocate.invoke(unsafe, acr);
            }
            record = r;
            setState(initialState);
            Object thread = Class.forName("android.app.ActivityThread").getMethod("currentActivityThread").invoke(null);
            @SuppressWarnings("unchecked") Map<Object, Object> acts = (Map<Object, Object>) get(thread, "mActivities");
            acts.clear();
            acts.put(token, record);
            if (identifiable) {
                Object dispatcher = alloc("android.app.LoadedApk$ServiceDispatcher");
                set(dispatcher, "mContext", activity);
                connection = alloc("android.app.LoadedApk$ServiceDispatcher$InnerConnection");
                set(connection, "mDispatcher", new WeakReference<>(dispatcher));
            } else {
                connection = new Object();
            }
        }

        void setState(int s) throws Exception {
            record.getClass().getMethod("setState", int.class).invoke(record, s);
        }

        int state() throws Exception {
            return (Integer) record.getClass().getMethod("getLifecycleState").invoke(record);
        }
    }

    static void bindFromOnCreate(Launch l) throws Exception {
        current = l;
        Class<?> amb = Class.forName("adapter.activity.ActivityManagerBindProxy");
        Object proxy = allocate.invoke(unsafe, amb);
        Method post = amb.getDeclaredMethod("postInProcessBind", Intent.class, ComponentName.class, Object.class);
        post.setAccessible(true);
        post.invoke(proxy, new Intent(), new ComponentName("com.termux", "com.termux.app.TermuxService"), l.connection);
    }

    static void postResumedTransaction(Launch l) {
        new Handler(Looper.getMainLooper()).post(() -> {
            try {
                l.setState(ON_START);
                l.visible = true;                       // TermuxActivity.onStart: mIsVisible = true
                call(l.activity, "dispatchActivityPostStarted");
                l.setState(ON_RESUME);
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        });
    }

    static void postDestroy(Launch l) {
        new Handler(Looper.getMainLooper()).post(() -> {
            try {
                set(l.activity, "mFinished", true);
                call(l.activity, "dispatchActivityDestroyed");
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        });
    }

    /** Looper.loop stand-in: FIFO over the real MessageQueue's message list, each callback run in turn. */
    static void drain(Launch l) throws Exception {
        for (int guard = 0; guard < 50; guard++) {
            Object m = get(queue, "mMessages");
            if (m == null) return;
            set(queue, "mMessages", get(m, "next"));
            Runnable cb = (Runnable) get(m, "callback");
            if (cb != null) {
                System.out.println("  run " + cb.getClass().getName());
                cb.run();
            }
        }
        throw new IllegalStateException("queue did not drain");
    }

    static void check(String name, boolean ok, String detail) {
        System.out.println("CASE " + name + ": " + (ok ? "PASS" : "FAIL") + " " + detail);
        if (!ok) failures++;
    }

    public static void main(String[] args) throws Exception {
        Class<?> uc = Class.forName("sun.misc.Unsafe");
        Field the;
        try { the = uc.getDeclaredField("THE_ONE"); } catch (NoSuchFieldException e) { the = uc.getDeclaredField("theUnsafe"); }
        the.setAccessible(true);
        unsafe = the.get(null);
        allocate = uc.getMethod("allocateInstance", Class.class);
        Class<?> li = Class.forName("android.app.servertransaction.ActivityLifecycleItem");
        ON_CREATE = li.getField("ON_CREATE").getInt(null);
        ON_START = li.getField("ON_START").getInt(null);
        ON_RESUME = li.getField("ON_RESUME").getInt(null);
        System.out.println("framework ActivityLifecycleItem ON_CREATE=" + ON_CREATE + " ON_START=" + ON_START + " ON_RESUME=" + ON_RESUME);

        queue = alloc("android.os.MessageQueue");
        Object looper = alloc("android.os.Looper");
        set(looper, "mQueue", queue);
        set(looper, "mThread", Thread.currentThread());
        setStatic("android.os.Looper", "sMainLooper", looper);
        Object thread = alloc("android.app.ActivityThread");
        set(thread, "mActivities", new android.util.ArrayMap<>());
        setStatic("android.app.ActivityThread", "sCurrentActivityThread", thread);
        Class<?> ambc = Class.forName("adapter.activity.ActivityManagerBindProxy");
        Field svc = field(ambc, "sServices");
        @SuppressWarnings("unchecked") Map<Object, Object> services = (Map<Object, Object>) svc.get(null);
        services.put("com.termux.app.TermuxService", new RecordingService());
        boolean hasFix;
        try { Class.forName("adapter.activity.InProcessBindOrder"); hasFix = true; } catch (ClassNotFoundException e) { hasFix = false; }
        System.out.println("runtime jar has InProcessBindOrder: " + hasFix);

        // 1. termux: bindService from onCreate (record ON_CREATE), OH's RESUMED transaction queued after the bind
        Launch t = new Launch(ON_CREATE, true);
        bindFromOnCreate(t);
        postResumedTransaction(t);
        drain(t);
        check("1 onCreate bind is delivered after onStart (termux mIsVisible=true)",
                t.delivered != null && t.delivered.contains("mIsVisible=true"),
                "bind delivered at " + t.delivered + (t.delivered != null && t.delivered.contains("mIsVisible=false")
                        ? " -> TermuxActivity.onServiceConnected sees mIsVisible=false and finishes (U10.1T8)" : ""));

        // 2. bind from an Activity that is already resumed: delivered at once, ahead of later messages
        Launch r = new Launch(ON_RESUME, true);
        r.visible = true;
        bindFromOnCreate(r);
        postResumedTransaction(r);
        drain(r);
        check("2 bind from a resumed Activity is delivered immediately", r.delivered != null
                && r.delivered.startsWith("state=" + ON_RESUME), "bind delivered at " + r.delivered + " (before the next transaction)");

        // 3. connection not attributable to an Activity (e.g. a Service or Application context): unchanged behaviour
        Launch n = new Launch(ON_CREATE, false);
        bindFromOnCreate(n);
        postResumedTransaction(n);
        drain(n);
        check("3 unattributable connection runs exactly as before (first in queue)", n.delivered != null
                && n.delivered.contains("mIsVisible=false"), "bind delivered at " + n.delivered);

        // 4. the Activity is destroyed before it ever starts: the held bind is dropped with it
        Launch d = new Launch(ON_CREATE, true);
        bindFromOnCreate(d);
        postDestroy(d);
        drain(d);
        check("4 bind of an Activity destroyed before onStart is not delivered", d.delivered == null,
                "bind delivered at " + d.delivered);

        System.out.println("FAILURES " + failures);
        System.exit(failures == 0 ? 0 : 1);
    }
}
