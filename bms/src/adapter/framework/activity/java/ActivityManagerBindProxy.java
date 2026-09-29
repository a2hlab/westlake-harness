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
        return method.invoke(delegate, args);
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
                        attachService(svc, app, thread, cls);
                        svc.getClass().getMethod("onCreate").invoke(svc);
                        sServices.put(cls, svc);
                        System.err.println("[B8-AMB] created in-process service " + cls);
                    }
                    IBinder binder = (IBinder) svc.getClass().getMethod("onBind", Intent.class).invoke(svc, service);
                    deliverConnected(connection, comp, binder);
                    System.err.println("[B8-AMB] connected " + cls + " binder=" + binder);
                } catch (Throwable t) {
                    System.err.println("[B8-AMB] in-process bind failed for " + comp + ": " + t);
                }
            }
        });
    }

    /** Service.attach(Context, ActivityThread, String, IBinder, Application, Object) via reflection. */
    private static void attachService(Object svc, Object app, Object thread, String cls) throws Exception {
        for (Method m : Class.forName("android.app.Service").getDeclaredMethods()) {
            if (!"attach".equals(m.getName())) continue;
            Class<?>[] p = m.getParameterTypes();
            if (p.length == 6) {
                m.setAccessible(true);
                m.invoke(svc, app, thread, cls, new Binder(), app, null);
                return;
            }
        }
        throw new NoSuchMethodException("Service.attach(6-arg) not found");
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
