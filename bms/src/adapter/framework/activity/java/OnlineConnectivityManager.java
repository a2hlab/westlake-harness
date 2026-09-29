package adapter.activity;

import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkInfo;
import android.net.NetworkRequest;
import android.os.Handler;
import android.os.Looper;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.Map;

/**
 * Runtime-JAR connectivity fix (no boot-image rebuild).
 *
 * The board's AOT android.net.ConnectivityManager stub reports offline
 * (getActiveNetwork/getActiveNetworkInfo return null, registerDefaultNetworkCallback is a no-op),
 * so Wikipedia's ConnectionStateMonitor decides offline -> MainActivity.onGoOffline ->
 * MainFragment.getCurrentFragment() NPE -> System.exit(1). We cannot change the AOT'd class, but
 * ConnectivityManager is NOT final and has a public no-arg constructor, so we subclass it and make
 * getSystemService("connectivity") hand out this online subclass by replacing the
 * SystemServiceRegistry fetcher at bind time (B7BindFixes.apply -> install()).
 *
 * NetworkInfo/NetworkCapabilities are likewise self-contained offline stubs (isConnected/
 * hasCapability return const 0), so we subclass those too and return the online variants.
 */
public class OnlineConnectivityManager extends ConnectivityManager {

    public OnlineConnectivityManager() {
        super();
    }

    private static Network net() {
        return new Network();
    }

    @Override
    public Network getActiveNetwork() {
        log("getActiveNetwork -> online");
        return net();
    }

    @Override
    public Network[] getAllNetworks() {
        return new Network[] { net() };
    }

    @Override
    public NetworkInfo getActiveNetworkInfo() {
        log("getActiveNetworkInfo -> connected WIFI");
        return new OnlineNetworkInfo();
    }

    @Override
    public NetworkInfo getNetworkInfo(Network network) {
        return new OnlineNetworkInfo();
    }

    @Override
    public NetworkCapabilities getNetworkCapabilities(Network network) {
        return new OnlineNetworkCapabilities();
    }

    @Override
    public boolean isDefaultNetworkActive() {
        return true;
    }

    @Override
    public boolean isActiveNetworkMetered() {
        return false;
    }

    @Override
    public int getRestrictBackgroundStatus() {
        return 1; // RESTRICT_BACKGROUND_STATUS_DISABLED
    }

    @Override
    public Network getBoundNetworkForProcess() {
        return null;
    }

    @Override
    public boolean bindProcessToNetwork(Network network) {
        return true;
    }

    @Override
    public void registerDefaultNetworkCallback(NetworkCallback cb) {
        deliverAvailable(cb);
    }

    @Override
    public void registerDefaultNetworkCallback(NetworkCallback cb, Handler handler) {
        deliverAvailable(cb);
    }

    @Override
    public void registerNetworkCallback(NetworkRequest req, NetworkCallback cb) {
        deliverAvailable(cb);
    }

    @Override
    public void registerNetworkCallback(NetworkRequest req, NetworkCallback cb, Handler handler) {
        deliverAvailable(cb);
    }

    @Override
    public void requestNetwork(NetworkRequest req, NetworkCallback cb) {
        deliverAvailable(cb);
    }

    @Override
    public void unregisterNetworkCallback(NetworkCallback cb) {
        // no-op
    }

    /** Drive the callback "available + validated" once, on the main looper, after register returns. */
    private static void deliverAvailable(final NetworkCallback cb) {
        if (cb == null) return;
        Runnable r = new Runnable() {
            public void run() {
                try {
                    Network n = net();
                    cb.onAvailable(n);
                    cb.onCapabilitiesChanged(n, new OnlineNetworkCapabilities());
                } catch (Throwable t) {
                    log("callback delivery failed: " + t);
                }
            }
        };
        Looper main = Looper.getMainLooper();
        if (main != null) {
            new Handler(main).post(r);
        } else {
            r.run();
        }
    }

    private static void log(String m) {
        System.err.println("[ONLINE-CM] " + m);
        System.err.flush();
    }

    /** Online NetworkInfo: the board stub hardcodes isConnected()==false, so override the checks. */
    public static class OnlineNetworkInfo extends NetworkInfo {
        public OnlineNetworkInfo() {
            super();
        }
        @Override public boolean isConnected() { return true; }
        @Override public boolean isAvailable() { return true; }
        @Override public boolean isConnectedOrConnecting() { return true; }
        @Override public boolean isRoaming() { return false; }
        @Override public int getType() { return 1; /* TYPE_WIFI */ }
        @Override public String getTypeName() { return "WIFI"; }
        // getState()/getDetailedState() left to super: board NetworkInfo.State/DetailedState runtime
        // shape (enum vs plain class) is uncertain; the boolean checks above are the primary signal.
    }

    /** Online NetworkCapabilities: board stub hardcodes hasCapability()==false. */
    public static class OnlineNetworkCapabilities extends NetworkCapabilities {
        public OnlineNetworkCapabilities() {
            super();
        }
        @Override public boolean hasCapability(int capability) { return true; }
        @Override public boolean hasTransport(int transportType) {
            return transportType == 1; /* TRANSPORT_WIFI */
        }
    }

    /**
     * A no-op JobScheduler whose getAllPendingJobs() returns an EMPTY list (not null): the board
     * jobscheduler stub returns null there, which makes androidx.work's getWmJobScheduler() NPE on
     * .getClass()/iteration -> WorkManagerInitializer -> androidx.startup InitializationProvider fails
     * -> bindApplication aborts before WikipediaApp.onCreate -> the later getWikiSite NPE.
     */
    public static class OnlineJobScheduler extends android.app.job.JobScheduler {
        public OnlineJobScheduler() { super(); }
        @Override public int schedule(android.app.job.JobInfo job) { return 1; /* RESULT_SUCCESS */ }
        @Override public int enqueue(android.app.job.JobInfo job, android.app.job.JobWorkItem work) { return 1; }
        @Override public void cancel(int jobId) {}
        @Override public void cancelAll() {}
        @Override public java.util.List<android.app.job.JobInfo> getAllPendingJobs() {
            return new java.util.ArrayList<android.app.job.JobInfo>();
        }
        @Override public android.app.job.JobInfo getPendingJob(int jobId) { return null; }
        // API 34+: JobScheduler.forNamespace()/other concrete methods throw
        // "Not implemented. Must override in a subclass." by default; WorkManager calls forNamespace().
        @Override public android.app.job.JobScheduler forNamespace(String namespace) { return this; }
    }

    /**
     * Replace the SystemServiceRegistry fetchers for the services whose board stubs return null in a
     * way that breaks app-init components. Called from B7BindFixes.apply at bind (cache empty then).
     *   connectivity  -> OnlineConnectivityManager  (fixes Wikipedia onGoOffline)
     *   jobscheduler  -> OnlineJobScheduler          (fixes WorkManager/coil3 InitializationProvider)
     */
    public static void install() {
        replaceFetcher("connectivity", new OnlineConnectivityManager());
        try {
            replaceFetcher("jobscheduler", new OnlineJobScheduler());
            // r17n: route-A never registered "jobscheduler" at all (fetcher prev=null above), so
            // SYSTEM_SERVICE_NAMES lacks JobScheduler.class -> getSystemService(JobScheduler.class),
            // the typed API fossify/androidx use, resolves the name to null and returns null BEFORE
            // the by-name fetcher is ever consulted (fossify calendar MainActivity JobScheduler
            // .cancel(int) NPE, v3c+r17j 5ea sweep). AOSP registerService writes BOTH maps; mirror
            // Westlake AppSpawnXInit nameMap.put(schedulerType,"jobscheduler").
            registerServiceName("android.app.job.JobScheduler", "jobscheduler");
        } catch (Throwable t) {
            log("jobscheduler stub not installed: " + t);
        }
        installReceiverGuard();
    }

    /**
     * The BCP ActivityManagerAdapter (AOT, oh-adapter-framework.jar) bridges registerReceiver* to the
     * JNI nativeSubscribeCommonEvent, which the loaded bridge library does not export on this
     * generation -> UnsatisfiedLinkError on the main thread -> System.exit(1). Same pattern as r15's
     * ActivityManagerBindProxy: wrap ActivityManager.IActivityManagerSingleton.mInstance and, for the
     * receiver calls only, answer "registered, no sticky intent" when the delegate hits a missing JNI.
     * Broadcast delivery is not needed for the first screen (B8 no-op-stub rule).
     */
    private static void installReceiverGuard() {
        try {
            Class<?> iface = Class.forName("android.app.IActivityManager");
            Class<?> am = Class.forName("android.app.ActivityManager");
            Field singletonField = am.getDeclaredField("IActivityManagerSingleton");
            singletonField.setAccessible(true);
            Object singleton = singletonField.get(null);
            Class<?> singletonClass = Class.forName("android.util.Singleton");
            Field instanceField = singletonClass.getDeclaredField("mInstance");
            instanceField.setAccessible(true);
            singletonClass.getMethod("get").invoke(singleton);
            final Object current = instanceField.get(singleton);
            if (current == null) { log("receiver guard: no IActivityManager instance"); return; }
            Object proxy = Proxy.newProxyInstance(iface.getClassLoader(), new Class<?>[] { iface },
                    new InvocationHandler() {
                        public Object invoke(Object p, Method m, Object[] a) throws Throwable {
                            String n = m.getName();
                            if ("asBinder".equals(n)) {
                                return ((android.os.IInterface) current).asBinder();
                            }
                            try {
                                return m.invoke(current, a);
                            } catch (java.lang.reflect.InvocationTargetException e) {
                                Throwable c = e.getCause();
                                if (c instanceof UnsatisfiedLinkError
                                        && (n.startsWith("registerReceiver") || n.startsWith("unregisterReceiver"))) {
                                    log(n + " -> missing JNI, answered as no-op (" + c.getMessage() + ")");
                                    return null;
                                }
                                throw c;
                            }
                        }
                    });
            instanceField.set(singleton, proxy);
            log("receiver guard installed over " + current.getClass().getName());
        } catch (Throwable t) {
            log("receiver guard not installed: " + t);
        }
    }

    @SuppressWarnings("unchecked")
    private static void replaceFetcher(String name, final Object singleton) {
        try {
            Class<?> ssr = Class.forName("android.app.SystemServiceRegistry");
            Class<?> fetcherIface = Class.forName("android.app.SystemServiceRegistry$ServiceFetcher");
            Object proxy = Proxy.newProxyInstance(ssr.getClassLoader(),
                    new Class<?>[] { fetcherIface },
                    new InvocationHandler() {
                        public Object invoke(Object p, Method m, Object[] a) {
                            if ("getService".equals(m.getName())) return singleton;
                            return null;
                        }
                    });
            Field f = ssr.getDeclaredField("SYSTEM_SERVICE_FETCHERS");
            f.setAccessible(true);
            Map<String, Object> fetchers = (Map<String, Object>) f.get(null);
            Object prev = fetchers.put(name, proxy);
            log(name + " fetcher replaced (prev=" + (prev == null ? "null" : prev.getClass().getName()) + ")");
        } catch (Throwable t) {
            log(name + " fetcher replace failed: " + t);
        }
    }

    /**
     * Map an API Class -> service name in SystemServiceRegistry.SYSTEM_SERVICE_NAMES so
     * getSystemService(ApiClass.class) resolves. Needed when route-A never stock-registered the
     * service (fetcher prev=null), which leaves the class map empty and makes the typed
     * getSystemService(Class) path return null before the by-name fetcher is consulted. Harmless if
     * the mapping already exists (put overwrites with the same name). Reached entirely by reflection.
     */
    @SuppressWarnings("unchecked")
    private static void registerServiceName(String apiClassName, String name) {
        try {
            Class<?> ssr = Class.forName("android.app.SystemServiceRegistry");
            Class<?> apiClass = Class.forName(apiClassName);
            Field f = ssr.getDeclaredField("SYSTEM_SERVICE_NAMES");
            f.setAccessible(true);
            java.util.Map<Class<?>, String> names = (java.util.Map<Class<?>, String>) f.get(null);
            String prev = names.put(apiClass, name);
            log(name + " class->name registered for " + apiClassName + " (prev=" + prev + ")");
        } catch (Throwable t) {
            log(name + " class->name register failed: " + t);
        }
    }
}
