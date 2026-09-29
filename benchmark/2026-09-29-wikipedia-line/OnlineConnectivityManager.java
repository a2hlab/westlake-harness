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
     * Replace the SystemServiceRegistry "connectivity" fetcher so getSystemService(CONNECTIVITY_SERVICE)
     * returns our online subclass process-wide. Called from B7BindFixes.apply at bind (cache empty then).
     */
    @SuppressWarnings("unchecked")
    public static void install() {
        try {
            final Object singleton = new OnlineConnectivityManager();
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
            Object prev = fetchers.put("connectivity", proxy);
            log("connectivity fetcher replaced (prev=" + (prev == null ? "null" : prev.getClass().getName()) + ")");
        } catch (Throwable t) {
            log("install failed: " + t);
        }
    }
}
