import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.os.IBinder;
import android.os.Looper;
import android.os.SystemClock;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.List;

/**
 * Host-ART harness for the x trampoline hand-off (benchmark/2026-10-03-u15-jar-v1), on the boards' boot class path.
 *
 * Real code under test: the runtime jar's TrampolineFinishOrder (U15 v1; absent in U14 v1 0349eb83, the negative
 * control) and framework.jar's ActivityTaskManager.getService (IActivityTaskManagerSingleton), ActivityClient
 * (setActivityClientController, getInstance().finishActivity -> mKnownInstance), ActivityThread.currentPackageName,
 * Handler / MessageQueue.enqueueMessage / Message.
 *
 * Stand-ins: the delegates TrampolineFinishOrder wraps on the board are BCP adapters whose bodies are OH natives
 * (ActivityTaskManagerAdapter -> StartAbility, ActivityClientControllerAdapter.finishActivity -> TerminateAbility).
 * Here they are recording proxies of the same framework interfaces: "OH" sees exactly the calls that reach them. The
 * board's two needles in AppSchedulerBridge.nativeOnScheduleLaunchAbility are modelled by their one-line effects:
 * the controller LaunchActivityItem carries = TrampolineFinishOrder.controller(adapter) (U14: the adapter itself), and
 * the next ScheduleLaunchAbility = TrampolineFinishOrder.onLaunchAbility (U14: nothing). The main Looper / queue are
 * allocated without nativeInit and drained by hand in `when` order (waiting real time for delayed messages).
 */
public class TrampolineOrderTest {
    static final String PKG = "com.twitter.android";
    static Object unsafe;
    static Method allocate;
    static Object queue;
    static int failures;
    static boolean hasFix;
    static Class<?> tfo;
    static final List<String> oh = new ArrayList<>();      // calls that reached the "OH" adapters, in order
    static final List<Long> ohAt = new ArrayList<>();
    static int startRc;

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

    static IBinder token(String name) {
        return (IBinder) Proxy.newProxyInstance(IBinder.class.getClassLoader(), new Class<?>[] {IBinder.class},
                (p, m, a) -> m.getName().equals("hashCode") ? System.identityHashCode(p)
                        : m.getName().equals("equals") ? p == a[0] : m.getName().equals("toString") ? name : null);
    }

    static void record(String what) {
        oh.add(what);
        ohAt.add(SystemClock.uptimeMillis());
        System.out.println("  OH <- " + what);
    }

    /** Looper.loop stand-in: run messages in `when` order, sleeping until a delayed one is due. */
    static void drain() throws Exception { drain(true); }

    /** wait=false: run only the messages already due (the main thread between two binder callbacks). */
    static void drain(boolean wait) throws Exception {
        for (int guard = 0; guard < 50; guard++) {
            Object m = get(queue, "mMessages");
            if (m == null) return;
            long when = (Long) get(m, "when");
            long now = SystemClock.uptimeMillis();
            if (when > now && !wait) return;
            if (when > now) Thread.sleep(when - now);
            set(queue, "mMessages", get(m, "next"));
            Runnable cb = (Runnable) get(m, "callback");
            if (cb != null) cb.run();
        }
        throw new IllegalStateException("queue did not drain");
    }

    static int start(Intent intent) throws Exception {
        Object atm = Class.forName("android.app.ActivityTaskManager").getMethod("getService").invoke(null);
        Method m = null;
        for (Method k : Class.forName("android.app.IActivityTaskManager").getMethods()) {
            if (k.getName().equals("startActivity")) m = k;
        }
        return (Integer) m.invoke(atm, null, PKG, null, intent, null, null, null, 0, 0, null, null);
    }

    static boolean finish(IBinder t) throws Exception {
        Object client = Class.forName("android.app.ActivityClient").getMethod("getInstance").invoke(null);
        return (Boolean) client.getClass().getMethod("finishActivity", IBinder.class, int.class, Intent.class, int.class)
                .invoke(client, t, 0, null, 0);
    }

    static void launch(String ability) throws Exception {
        System.out.println("  ScheduleLaunchAbility " + ability);
        if (hasFix) tfo.getMethod("onLaunchAbility", String.class, String.class).invoke(null, PKG, ability);
    }

    static int count(String prefix, int from) {
        int n = 0;
        for (int i = from; i < oh.size(); i++) if (oh.get(i).startsWith(prefix)) n++;
        return n;
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

        queue = alloc("android.os.MessageQueue");
        Object looper = alloc("android.os.Looper");
        set(looper, "mQueue", queue);
        set(looper, "mThread", Thread.currentThread());
        setStatic("android.os.Looper", "sMainLooper", looper);
        Object thread = alloc("android.app.ActivityThread");
        Object bind = alloc("android.app.ActivityThread$AppBindData");
        ApplicationInfo ai = new ApplicationInfo();
        ai.packageName = PKG;
        set(bind, "appInfo", ai);
        set(thread, "mBoundApplication", bind);
        setStatic("android.app.ActivityThread", "sCurrentActivityThread", thread);
        System.out.println("ActivityThread.currentPackageName() = "
                + Class.forName("android.app.ActivityThread").getMethod("currentPackageName").invoke(null));

        // "OH" adapters: recording IActivityTaskManager / IActivityClientController
        Class<?> iatm = Class.forName("android.app.IActivityTaskManager");
        Object atmAdapter = Proxy.newProxyInstance(iatm.getClassLoader(), new Class<?>[] {iatm}, (p, m, a) -> {
            if (m.getName().startsWith("startActivit")) {
                Intent i = (Intent) a[3];
                record("StartAbility " + (i.getComponent() != null ? i.getComponent().getClassName() : i.getAction()));
                return startRc;
            }
            return m.getReturnType() == int.class ? 0 : m.getReturnType() == boolean.class ? false : null;
        });
        Object singleton = field(Class.forName("android.app.ActivityTaskManager"), "IActivityTaskManagerSingleton").get(null);
        field(Class.forName("android.util.Singleton"), "mInstance").set(singleton, atmAdapter);
        Class<?> iacc = Class.forName("android.app.IActivityClientController");
        Object accAdapter = Proxy.newProxyInstance(iacc.getClassLoader(), new Class<?>[] {iacc}, (p, m, a) -> {
            if (m.getName().equals("finishActivity")) {
                record("TerminateAbility " + a[0]);
                return true;
            }
            if (m.getName().equals("isTopOfTask")) {
                record("isTopOfTask " + a[0]);
                return true;
            }
            return m.getReturnType() == boolean.class ? false : m.getReturnType() == int.class ? 0 : null;
        });

        try { tfo = Class.forName("adapter.activity.TrampolineFinishOrder"); hasFix = true; } catch (ClassNotFoundException e) { hasFix = false; }
        System.out.println("runtime jar has TrampolineFinishOrder: " + hasFix);
        Object controller = accAdapter;
        if (hasFix) {
            tfo.getMethod("install").invoke(null);                                         // B7BindFixes needle
            controller = tfo.getMethod("controller", iacc).invoke(null, accAdapter);       // LaunchActivityItem needle
        }
        Class.forName("android.app.ActivityClient").getMethod("setActivityClientController", iacc)
                .invoke(null, controller);                                                  // LaunchActivityItem.preExecute

        // 1. x: StartActivity.onCreate starts XLiteActivity (own package), then finish() twice; XLite's launch arrives later
        int mark = oh.size();
        start(new Intent().setComponent(new ComponentName(PKG, "com.twitter.x.lite.XLiteActivity")));
        IBinder a = token("StartActivity");
        boolean r1 = finish(a), r2 = finish(a);
        int before = count("TerminateAbility", mark);
        Thread.sleep(100);                       // the launch arrives ~0.1 s later when the process is reused
        drain(false);
        int beforeLaunch = count("TerminateAbility", mark);
        launch("com.twitter.x.lite.XLiteActivity");
        drain();
        int after = count("TerminateAbility", mark);
        check("1 trampoline: finish reaches OH only after the started ability's launch, once",
                r1 && r2 && before == 0 && beforeLaunch == 0 && after == 1,
                "finish returned " + r1 + "/" + r2 + "; TerminateAbility before launch=" + beforeLaunch + ", after=" + after
                        + (beforeLaunch > 0 ? " -> AppMgr sees the last ability before XLite is loaded ([ARM938], 2nd process)" : ""));

        // 2. the started ability never reaches this process: the held finish is released by the timeout, once
        mark = oh.size();
        long t0 = SystemClock.uptimeMillis();
        start(new Intent().setComponent(new ComponentName(PKG, "com.twitter.android.LoginActivity")));
        IBinder b = token("SplashB");
        finish(b);
        int immediate = count("TerminateAbility", mark);
        drain();
        long waited = ohAt.isEmpty() ? -1 : ohAt.get(ohAt.size() - 1) - t0;
        int total = count("TerminateAbility", mark);
        check("2 no launch: held finish released after ~3 s", hasFix ? immediate == 0 && total == 1 && waited >= 2900 && waited < 4500
                : immediate == 1 && total == 1, "immediate=" + immediate + " total=" + total + " last OH call at +" + waited + " ms");

        // 3. start into another package: finish is not held
        mark = oh.size();
        start(new Intent().setComponent(new ComponentName("org.mozilla.firefox", "org.mozilla.firefox.App")));
        finish(token("ShareC"));
        check("3 other-package start: finish goes to OH at once", count("TerminateAbility", mark) == 1,
                "TerminateAbility=" + count("TerminateAbility", mark));

        // 4. implicit start (no component, no package): not attributable to this package, finish not held
        mark = oh.size();
        start(new Intent("android.intent.action.VIEW"));
        finish(token("ViewD"));
        check("4 implicit start: finish goes to OH at once", count("TerminateAbility", mark) == 1,
                "TerminateAbility=" + count("TerminateAbility", mark));

        // 5. failed start (rc < 0): finish not held
        mark = oh.size();
        startRc = -1;
        start(new Intent().setComponent(new ComponentName(PKG, "com.twitter.android.Missing")));
        startRc = 0;
        finish(token("FailE"));
        check("5 failed own-package start: finish goes to OH at once", count("TerminateAbility", mark) == 1,
                "TerminateAbility=" + count("TerminateAbility", mark));

        // 6. plain finish twice, no start: forwarded once (U14: twice; the board's 2nd is rc=22)
        mark = oh.size();
        IBinder f = token("PlainF");
        finish(f);
        finish(f);
        int n6 = count("TerminateAbility", mark);
        check("6 duplicate finish of one token reaches OH once", n6 == 1, "TerminateAbility=" + n6);

        // 7. every other controller method passes through unchanged
        mark = oh.size();
        Object client = Class.forName("android.app.ActivityClient").getMethod("getInstance").invoke(null);
        boolean top = (Boolean) client.getClass().getMethod("isTopOfTask", IBinder.class).invoke(client, token("G"));
        check("7 other controller calls pass through", top && count("isTopOfTask", mark) == 1,
                "isTopOfTask returned " + top + ", reached OH " + count("isTopOfTask", mark));

        System.out.println("OH call log: " + oh);
        System.out.println("FAILURES " + failures);
        System.exit(failures == 0 ? 0 : 1);
    }
}
