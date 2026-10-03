package adapter.activity;

import android.app.IActivityClientController;
import android.content.ComponentName;
import android.content.Intent;
import android.os.Handler;
import android.os.IBinder;
import android.os.IInterface;
import android.os.Looper;
import android.os.SystemClock;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Android's order for a trampoline: the started activity exists before the finishing one is removed
 * (benchmark/2026-10-03-x-trampoline-handover).
 *
 * On route A an Activity.startActivity is asynchronous on OH (an SCB pending session; AppMgr has no record of the new
 * ability yet), and the finish() that follows it reaches AMS first. AMS PrepareCloseUIAbility -> AppMgr
 * PrepareTerminate sees the closing ability as the app record's LAST ability ([ARM938] "ability is the last") and marks
 * the record terminating; the next ability's LoadAbility then skips that record and cold-starts a second process
 * (x: ~11 s; 36 keys pay 1.7-2.7 s). The CLOSE itself is dropped in the pending state, so the first process stays.
 *
 * install(): a runtime-JAR proxy over ActivityTaskManager.IActivityTaskManagerSingleton (the B8-AMB pattern) that notes
 * a successful start of an activity in this app's own package (explicit component or package).
 * controller(): a proxy over the IActivityClientController that LaunchActivityItem hands to ActivityClient. While a
 * noted start has not reached this process (no ScheduleLaunchAbility yet, at most HOLD_MS), finishActivity is held and
 * returns true (the adapter's own answer); onLaunchAbility() (the next ScheduleLaunchAbility of this process) or the
 * HOLD_MS timeout forwards it unchanged on the main thread. A second finishActivity for a token already forwarded or
 * held is dropped (AOSP returns true for an activity that is already finishing; the adapter's second OH
 * TerminateAbility only fails with rc=22). Everything else, and every failure inside the intercepts, goes to the
 * delegate unchanged.
 */
public final class TrampolineFinishOrder {
    static final long HOLD_MS = 3000;

    private static final Object LOCK = new Object();
    private static final ArrayList<Held> sHeld = new ArrayList<>();
    private static final Map<IBinder, Boolean> sFinishing = new WeakHashMap<>();
    private static long sStartAt;        // uptime of the last own-package start not yet launched here; 0 = none
    private static String sStartTarget;
    private static int sLaunches;        // ScheduleLaunchAbility count, to ignore a launch racing the start call
    private static Object sControllerDelegate;
    private static IActivityClientController sControllerProxy;

    private TrampolineFinishOrder() {}

    /** Wrap ActivityTaskManager.IActivityTaskManagerSingleton.mInstance, once, at bind (next to B8-AMB). */
    public static void install() {
        try {
            Class<?> iface = Class.forName("android.app.IActivityTaskManager");
            Field singletonField = Class.forName("android.app.ActivityTaskManager")
                    .getDeclaredField("IActivityTaskManagerSingleton");
            singletonField.setAccessible(true);
            Object singleton = singletonField.get(null);
            Class<?> singletonClass = Class.forName("android.util.Singleton");
            Field instanceField = singletonClass.getDeclaredField("mInstance");
            instanceField.setAccessible(true);
            singletonClass.getMethod("get").invoke(singleton);
            Object current = instanceField.get(singleton);
            if (current == null) return;
            if (Proxy.isProxyClass(current.getClass())
                    && Proxy.getInvocationHandler(current) instanceof StartObserver) {
                return;
            }
            Object proxy = Proxy.newProxyInstance(iface.getClassLoader(), new Class<?>[] {iface},
                    new StartObserver(current));
            instanceField.set(singleton, proxy);
            System.err.println("[TFO] IActivityTaskManager start observer installed over "
                    + current.getClass().getName());
        } catch (Throwable t) {
            System.err.println("[TFO] start observer not installed: " + t);
        }
    }

    /** The controller LaunchActivityItem carries (it becomes ActivityClient's mKnownInstance); wrapped once. */
    public static IActivityClientController controller(IActivityClientController real) {
        if (real == null) return null;
        try {
            synchronized (LOCK) {
                if (real == sControllerDelegate && sControllerProxy != null) return sControllerProxy;
                if (Proxy.isProxyClass(real.getClass())
                        && Proxy.getInvocationHandler(real) instanceof FinishHold) {
                    return real;
                }
                Class<?> iface = Class.forName("android.app.IActivityClientController");
                IActivityClientController proxy = (IActivityClientController) Proxy.newProxyInstance(
                        iface.getClassLoader(), new Class<?>[] {iface}, new FinishHold(real));
                sControllerDelegate = real;
                sControllerProxy = proxy;
                System.err.println("[TFO] IActivityClientController finish order proxy over " + real.getClass().getName());
                return proxy;
            }
        } catch (Throwable t) {
            System.err.println("[TFO] controller proxy not installed: " + t);
            return real;
        }
    }

    /** ScheduleLaunchAbility reached this process: the app record now holds another ability; release held finishes. */
    public static void onLaunchAbility(String bundleName, String abilityName) {
        ArrayList<Held> ready;
        synchronized (LOCK) {
            sLaunches++;
            sStartAt = 0;
            sStartTarget = null;
            if (sHeld.isEmpty()) return;
            ready = new ArrayList<>(sHeld);
            sHeld.clear();
        }
        for (Held h : ready) {
            System.err.println("[TFO] " + abilityName + " launched in this process; releasing held finish of " + h.what);
            main().post(h);
        }
    }

    static Handler main() {
        return new Handler(Looper.getMainLooper());
    }

    static Object forward(Object delegate, Method method, Object[] args) throws Throwable {
        try {
            return method.invoke(delegate, args);
        } catch (InvocationTargetException e) {
            throw e.getCause() != null ? e.getCause() : e;
        }
    }

    static String ownPackage() {
        try {
            return (String) Class.forName("android.app.ActivityThread").getMethod("currentPackageName").invoke(null);
        } catch (Throwable t) {
            return null;
        }
    }

    /** A finishActivity held until the next launch of this process or HOLD_MS. */
    static final class Held implements Runnable {
        final Object delegate;
        final Method method;
        final Object[] args;
        final String what;
        boolean done;

        Held(Object delegate, Method method, Object[] args, String what) {
            this.delegate = delegate;
            this.method = method;
            this.args = args;
            this.what = what;
        }

        @Override
        public void run() {
            synchronized (LOCK) {
                if (done) return;
                done = true;
                sHeld.remove(this);
            }
            try {
                forward(delegate, method, args);
            } catch (Throwable t) {
                System.err.println("[TFO] held finish of " + what + " failed: " + t);
            }
        }
    }

    static final class FinishHold implements InvocationHandler {
        private final Object delegate;

        FinishHold(Object delegate) {
            this.delegate = delegate;
        }

        @Override
        public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
            String name = method.getName();
            if ("asBinder".equals(name)) {
                return ((IInterface) delegate).asBinder();
            }
            if ("finishActivity".equals(name) && args != null && args.length == 4 && args[0] instanceof IBinder) {
                Held held = null;
                try {
                    IBinder token = (IBinder) args[0];
                    synchronized (LOCK) {
                        if (sFinishing.containsKey(token)) {
                            System.err.println("[TFO] duplicate finishActivity dropped (token already finishing)");
                            return Boolean.TRUE;
                        }
                        sFinishing.put(token, Boolean.TRUE);
                        long now = SystemClock.uptimeMillis();
                        if (sStartAt != 0 && now - sStartAt < HOLD_MS) {
                            held = new Held(delegate, method, args, String.valueOf(token));
                            sHeld.add(held);
                            System.err.println("[TFO] finishActivity held: own-package start " + sStartTarget
                                    + " has not reached this process (" + (now - sStartAt) + " ms ago)");
                        }
                    }
                } catch (Throwable t) {
                    System.err.println("[TFO] finish intercept skipped: " + t);
                    held = null;
                }
                if (held != null) {
                    final Held h = held;
                    main().postDelayed(new Runnable() {
                        @Override
                        public void run() {
                            synchronized (LOCK) {
                                if (h.done) return;
                            }
                            System.err.println("[TFO] no launch within " + HOLD_MS + " ms; releasing held finish of " + h.what);
                            h.run();
                        }
                    }, HOLD_MS);
                    return Boolean.TRUE;
                }
            }
            return forward(delegate, method, args);
        }
    }

    static final class StartObserver implements InvocationHandler {
        private final Object delegate;

        StartObserver(Object delegate) {
            this.delegate = delegate;
        }

        @Override
        public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
            String name = method.getName();
            if ("asBinder".equals(name)) {
                return ((IInterface) delegate).asBinder();
            }
            String target = null;
            int launches = 0;
            if (args != null && ("startActivity".equals(name) || "startActivityAsUser".equals(name)
                    || "startActivities".equals(name) || "startActivityWithConfig".equals(name))) {
                try {
                    target = ownTarget(args);
                    synchronized (LOCK) {
                        launches = sLaunches;
                    }
                } catch (Throwable t) {
                    target = null;
                }
            }
            Object result = forward(delegate, method, args);
            if (target != null && !(result instanceof Integer && (Integer) result < 0)) {
                synchronized (LOCK) {
                    if (launches == sLaunches) {
                        sStartAt = SystemClock.uptimeMillis();
                        sStartTarget = target;
                        System.err.println("[TFO] " + name + " -> own-package " + target + " (rc=" + result
                                + "); finishes wait for its launch, at most " + HOLD_MS + " ms");
                    }
                }
            }
            return result;
        }

        private static String ownTarget(Object[] args) {
            Intent intent = null;
            for (Object a : args) {
                if (a instanceof Intent) {
                    intent = (Intent) a;
                    break;
                }
                if (a instanceof Intent[] && ((Intent[]) a).length > 0) {
                    intent = ((Intent[]) a)[0];
                    break;
                }
            }
            if (intent == null) return null;
            ComponentName c = intent.getComponent();
            String pkg = c != null ? c.getPackageName() : intent.getPackage();
            String own = ownPackage();
            if (pkg == null || own == null || !pkg.equals(own)) return null;
            return c != null ? c.getClassName() : pkg;
        }
    }
}
