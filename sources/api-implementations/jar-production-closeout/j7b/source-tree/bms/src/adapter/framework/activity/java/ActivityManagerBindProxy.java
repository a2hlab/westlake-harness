package adapter.activity;

import android.content.ComponentName;
import android.content.Intent;
import android.os.Binder;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.concurrent.ConcurrentHashMap;

/**
 * B8 (#82/r15): a runtime-JAR proxy over ActivityManager.IActivityManagerSingleton's IActivityManager
 * (the BCP ActivityManagerAdapter). The deployed adapter routes EVERY bindService to OH
 * ConnectAbility, so an app binding its OWN in-process Service (termux TermuxService, noice
 * SoundPlaybackService) gets a bind failure (returns 0 -> ContextImpl throws bindService() failed).
 *
 * Copies Westlake's in-app branch (a2hlab/westlake-current framework/activity/java
 * ActivityManagerAdapter.bindService + InProcessServiceBinder): when the target Service is in this
 * app's own package, instantiate it in-process the way ActivityThread.handleBindService does
 * (attach + onCreate + onBind) and deliver the binder to the app's IServiceConnection on the main
 * thread, returning "bind initiated" (1). Everything else is delegated to the real adapter unchanged;
 * any failure inside the intercept falls through to the delegate.
 *
 * All hidden APIs (ActivityThread, Service.attach, IServiceConnection.connected, IActivityManager,
 * ActivityManager.IActivityManagerSingleton) are reached by reflection -- none is in the compile
 * android.jar.
 */
public final class ActivityManagerBindProxy implements InvocationHandler {
    private static final ConcurrentHashMap<String, Object> sServices = new ConcurrentHashMap<>();

    private final Object delegate;   // the real IActivityManager (ActivityManagerAdapter)

    private ActivityManagerBindProxy(Object delegate) {
        this.delegate = delegate;
    }

    /** Wrap ActivityManager.IActivityManagerSingleton.mInstance with this proxy, once, at bind. */
    public static void install() {
        try {
            Class<?> iface = Class.forName("android.app.IActivityManager");
            Class<?> am = Class.forName("android.app.ActivityManager");
            java.lang.reflect.Field singletonField = am.getDeclaredField("IActivityManagerSingleton");
            singletonField.setAccessible(true);
            Object singleton = singletonField.get(null);
            Class<?> singletonClass = Class.forName("android.util.Singleton");
            java.lang.reflect.Field instanceField = singletonClass.getDeclaredField("mInstance");
            instanceField.setAccessible(true);
            // Force creation of the real instance, then read it.
            singletonClass.getMethod("get").invoke(singleton);
            Object current = instanceField.get(singleton);
            if (current == null) return;
            if (Proxy.isProxyClass(current.getClass())
                    && Proxy.getInvocationHandler(current) instanceof ActivityManagerBindProxy) {
                return;
            }
            Object proxy = Proxy.newProxyInstance(iface.getClassLoader(), new Class<?>[] {iface},
                    new ActivityManagerBindProxy(current));
            instanceField.set(singleton, proxy);
            System.err.println("[B8-AMB] IActivityManager bindService proxy installed over "
                    + current.getClass().getName());
        } catch (Throwable t) {
            System.err.println("[B8-AMB] not installed: " + t);
        }
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        String name = method.getName();
        if ("asBinder".equals(name)) {
            return ((android.os.IInterface) delegate).asBinder();
        }
        if (("bindService".equals(name) || "bindServiceInstance".equals(name)) && args != null) {
            try {
                Intent service = firstOfType(args, Intent.class);
                ComponentName comp = service == null ? null : service.getComponent();
                Object connection = firstServiceConnection(args);
                if (comp != null && connection != null && isInApp(comp)) {
                    System.err.println("[B8-AMB] " + name + " -> in-process in-app service " + comp);
                    postInProcessBind(service, comp, connection);
                    return Integer.valueOf(1);
                }
            } catch (Throwable t) {
                System.err.println("[B8-AMB] in-app bind intercept skipped: " + t);
            }
        }
        // r17c (#noice): PendingIntent.getActivity/getService/getBroadcast/getForegroundService call
        // IActivityManager.getIntentSender(WithFeature). route-A returns null, so PendingIntent is null
        // and Noice's <get-mainActivityPi>/getValue NPE and System.exit(1) once the receiver guard lets
        // its playback service run this far. Hand back a local no-op IIntentSender so the PendingIntent
        // constructs; its send() does nothing (no notification actions on the first screen).
        if ("getIntentSender".equals(name) || "getIntentSenderWithFeature".equals(name)) {
            Object real = null;
            try {
                real = method.invoke(delegate, args);
            } catch (java.lang.reflect.InvocationTargetException e) {
                // fall through to the stub
            }
            if (real != null) return real;
            Object stub = intentSenderStub();
            if (stub != null) {
                System.err.println("[B8-AMB] " + name + " -> local no-op IIntentSender stub");
                return stub;
            }
        }
        // r17c (#noice): sendBroadcast -> broadcastIntent(WithFeature) hits nativePublishCommonEvent's
        // missing JNI (UnsatisfiedLinkError). Tolerate it the same way the receiver guard tolerates
        // registerReceiver, so a foreground/playback broadcast does not take the app down.
        if (name.startsWith("broadcastIntent")) {
            try {
                return method.invoke(delegate, args);
            } catch (java.lang.reflect.InvocationTargetException e) {
                Throwable c = e.getCause();
                if (c instanceof UnsatisfiedLinkError) {
                    System.err.println("[B8-AMB] " + name + " -> missing CommonEvent JNI, no-op ("
                            + c.getMessage() + ")");
                    return method.getReturnType() == void.class ? null : Integer.valueOf(0);
                }
                throw c != null ? c : e;
            }
        }
        // r17 (#93/cc-wiki): unwrap InvocationTargetException so the delegate's real exception crosses
        // this proxy transparently. Otherwise a checked ITE from Method.invoke is re-wrapped by the
        // Proxy runtime into UndeclaredThrowableException, and a guard stacked outside us
        // (OnlineConnectivityManager.installReceiverGuard, which answers registerReceiver's missing-JNI
        // UnsatisfiedLinkError as a no-op) can no longer recognise the original cause.
        try {
            return method.invoke(delegate, args);
        } catch (java.lang.reflect.InvocationTargetException e) {
            throw e.getCause() != null ? e.getCause() : e;
        }
    }

    /** True if comp targets a service in this app's own package. */
    private static boolean isInApp(ComponentName comp) {
        try {
            Object app = currentApplication();
            if (app == null || comp == null) return false;
            String pkg = (String) app.getClass().getMethod("getPackageName").invoke(app);
            return pkg != null && pkg.equals(comp.getPackageName());
        } catch (Throwable t) {
            return false;
        }
    }

    private void postInProcessBind(final Intent service, final ComponentName comp, final Object connection) {
        new Handler(Looper.getMainLooper()).post(new Runnable() {
            @Override
            public void run() {
                try {
                    Object app = currentApplication();
                    Object thread = currentActivityThread();
                    String cls = comp.getClassName();
                    Object svc = sServices.get(cls);
                    if (svc == null) {
                        Class<?> svcClass = ((ClassLoader) app.getClass().getMethod("getClassLoader")
                                .invoke(app)).loadClass(cls);
                        svc = svcClass.getDeclaredConstructor().newInstance();
                        attachService(svc, app, thread, cls, serviceActivityManager());
                        svc.getClass().getMethod("onCreate").invoke(svc);
                        sServices.put(cls, svc);
                        System.err.println("[B8-AMB] created in-process service " + cls);
                    }
                    IBinder binder = (IBinder) svc.getClass().getMethod("onBind", Intent.class).invoke(svc, service);
                    deliverConnected(connection, comp, binder);
                    System.err.println("[B8-AMB] connected " + cls + " binder=" + binder);
                } catch (Throwable t) {
                    dumpBindFailure(comp, t);
                }
            }
        });
    }

    /**
     * J3 (#newpipe): after AndroidFrameworkPackage synthesizes getPackageInfo("android"), NewPipe's
     * PlayerService in-process bind still throws in the same millisecond, but the old one-line print
     * showed only the outermost InvocationTargetException ("... : java.lang.reflect.Invocation-
     * TargetException") and hid the real internal cause. Walk the whole getCause() chain and print the
     * root cause's top 5 stack frames so the actual culprit (whatever PlayerService.onCreate/onBind
     * fails on next) is legible in hilog. Diagnostic only -- the fix follows once the chain is read.
     */
    private static void dumpBindFailure(ComponentName comp, Throwable t) {
        StringBuilder sb = new StringBuilder("[B8-AMB] in-process bind failed for ").append(comp);
        Throwable root = t;
        int depth = 0;
        for (Throwable c = t; c != null && depth < 12; depth++) {
            sb.append(depth == 0 ? ": " : "\n[B8-AMB]   caused by: ").append(c.getClass().getName());
            String msg = c.getMessage();
            if (msg != null) sb.append(": ").append(msg);
            root = c;
            Throwable next = c.getCause();
            if (next == c) break;
            c = next;
        }
        StackTraceElement[] frames = root.getStackTrace();
        int n = Math.min(5, frames.length);
        for (int i = 0; i < n; i++) sb.append("\n[B8-AMB]   at ").append(frames[i]);
        System.err.println(sb.toString());
        System.err.flush();
    }

    /** Service.attach(Context, ActivityThread, String, IBinder, Application, Object activityManager). */
    private static void attachService(Object svc, Object app, Object thread, String cls,
            Object activityManager) throws Exception {
        for (Method m : Class.forName("android.app.Service").getDeclaredMethods()) {
            if (!"attach".equals(m.getName())) continue;
            Class<?>[] p = m.getParameterTypes();
            if (p.length == 6) {
                m.setAccessible(true);
                // 6th arg is the IActivityManager the Service keeps as mActivityManager: a running
                // in-process Service calls it back (startForeground -> setServiceForeground). It must
                // not be null (r17/#droidify: fd-droidify's SyncService NPE'd Service.startForeground).
                m.invoke(svc, app, thread, cls, new Binder(), app, activityManager);
                return;
            }
        }
        throw new NoSuchMethodException("Service.attach(6-arg) not found");
    }

    /**
     * r17 (#droidify): a non-null IActivityManager for the in-process Service's mActivityManager.
     * OH's route-A adapter cannot service the lifecycle callbacks a running Service makes -- notably
     * Service.startForeground -> IActivityManager.setServiceForeground -- so answer those as harmless
     * no-ops and delegate every other call to the real adapter (unwrapping InvocationTargetException
     * so the delegate's own exceptions stay recognisable). Non-first-frame notification plumbing is a
     * no-op by the B8 stub rule; the Service still reaches its onCreate/onBind UI work.
     */
    private Object serviceActivityManager() {
        try {
            final Class<?> iface = Class.forName("android.app.IActivityManager");
            return Proxy.newProxyInstance(iface.getClassLoader(), new Class<?>[] {iface},
                    new InvocationHandler() {
                        @Override
                        public Object invoke(Object p, Method m, Object[] a) throws Throwable {
                            String n = m.getName();
                            if ("asBinder".equals(n)) {
                                return ((android.os.IInterface) delegate).asBinder();
                            }
                            if (n.equals("setServiceForeground") || n.equals("stopServiceToken")
                                    || n.equals("serviceDoneExecuting") || n.equals("publishService")
                                    || n.equals("unbindFinished") || n.equals("setServiceForegroundNode")
                                    || n.equals("requestServiceBinding")) {
                                return defaultReturn(m.getReturnType());
                            }
                            try {
                                return m.invoke(delegate, a);
                            } catch (java.lang.reflect.InvocationTargetException e) {
                                throw e.getCause() != null ? e.getCause() : e;
                            }
                        }
                    });
        } catch (Throwable t) {
            System.err.println("[B8-AMB] service IActivityManager stub not built: " + t);
            return null;
        }
    }

    /**
     * r17c (#noice): a fresh no-op android.content.IIntentSender for getIntentSender*. Each call gets
     * its own Binder so distinct PendingIntents stay distinct; send() and every other method are
     * type-correct no-ops. Reflection throughout -- IIntentSender is not in the compile android.jar.
     */
    private static Object intentSenderStub() {
        try {
            final Class<?> iface = Class.forName("android.content.IIntentSender");
            final android.os.Binder binder = new android.os.Binder();
            return Proxy.newProxyInstance(iface.getClassLoader(), new Class<?>[] {iface},
                    new InvocationHandler() {
                        @Override
                        public Object invoke(Object p, Method m, Object[] a) {
                            if ("asBinder".equals(m.getName())) return binder;
                            return defaultReturn(m.getReturnType());
                        }
                    });
        } catch (Throwable t) {
            System.err.println("[B8-AMB] IIntentSender stub not built: " + t);
            return null;
        }
    }

    /** Type-correct harmless default for a stubbed IActivityManager method (B8 no-op rule). */
    private static Object defaultReturn(Class<?> type) {
        if (type == boolean.class) return Boolean.TRUE;   // "accepted / done" for service callbacks
        if (type == int.class || type == long.class || type == short.class || type == byte.class) {
            return type == long.class ? (Object) 0L : (Object) 0;
        }
        return null;                                       // void and object returns
    }

    /** IServiceConnection.connected(ComponentName, IBinder, boolean) via reflection. */
    private static void deliverConnected(Object connection, ComponentName comp, IBinder binder) throws Exception {
        for (Method m : connection.getClass().getMethods()) {
            if (!"connected".equals(m.getName())) continue;
            Class<?>[] p = m.getParameterTypes();
            if (p.length == 3 && p[0] == ComponentName.class && p[1] == IBinder.class && p[2] == boolean.class) {
                m.invoke(connection, comp, binder, false);
                return;
            }
            if (p.length == 2 && p[0] == ComponentName.class && p[1] == IBinder.class) {
                m.invoke(connection, comp, binder);
                return;
            }
        }
        throw new NoSuchMethodException("IServiceConnection.connected not found");
    }

    private static Object currentApplication() throws Exception {
        return Class.forName("android.app.ActivityThread").getMethod("currentApplication").invoke(null);
    }

    private static Object currentActivityThread() throws Exception {
        return Class.forName("android.app.ActivityThread").getMethod("currentActivityThread").invoke(null);
    }

    @SuppressWarnings("unchecked")
    private static <T> T firstOfType(Object[] args, Class<T> type) {
        for (Object a : args) if (type.isInstance(a)) return (T) a;
        return null;
    }

    /** The IServiceConnection arg: an IInterface whose interface chain names IServiceConnection. */
    private static Object firstServiceConnection(Object[] args) {
        for (Object a : args) {
            if (!(a instanceof android.os.IInterface)) continue;
            for (Class<?> c = a.getClass(); c != null; c = c.getSuperclass()) {
                for (Class<?> i : c.getInterfaces()) {
                    if (i.getName().contains("IServiceConnection")) return a;
                }
            }
        }
        return null;
    }
}
