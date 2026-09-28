// Mainline APEX stub.  android.net.ConnectivityManager lives in the
// Connectivity APEX module that OH does not ship.
//
// [WL-CONNECTIVITY 2026-06-27] Previously a bare stub on the assumption that
// cm is never instantiated (ActivityThread.handleBindApplication only fetches
// it when ServiceManager.getService(CONNECTIVITY_SERVICE) != null, which the
// OH IServiceManager stub forces to null, so that path is skipped).  But AOSP
// app code (WorkManager's NetworkStateTracker / ConnectivityManagerCompat /
// noice ext) does `getSystemService("connectivity") as ConnectivityManager`
// and casts non-null.  ConnectivityFrameworkInitializer.registerServiceWrappers
// now registers a real fetcher returning a `new ConnectivityManager(context)`,
// so this class must offer the methods those app paths call.  OH has no
// Connectivity binder, so every query answers "no active network".

package android.net;

import android.content.Context;

public class ConnectivityManager {

    public ConnectivityManager() {}

    public ConnectivityManager(Context context) {}

    public ProxyInfo getDefaultProxy() { return null; }

    public Network getActiveNetwork() { return null; }

    public NetworkInfo getActiveNetworkInfo() { return null; }

    public NetworkInfo getNetworkInfo(Network network) { return null; }

    public NetworkCapabilities getNetworkCapabilities(Network network) { return null; }

    public LinkProperties getLinkProperties(Network network) { return null; }

    public boolean isActiveNetworkMetered() { return false; }

    public Network[] getAllNetworks() { return new Network[0]; }

    public void registerDefaultNetworkCallback(NetworkCallback callback) {}

    public void registerNetworkCallback(NetworkRequest request, NetworkCallback callback) {}

    public void unregisterNetworkCallback(NetworkCallback callback) {}

    public static class NetworkCallback {
        public NetworkCallback() {}
        public NetworkCallback(int flags) {}
        public void onAvailable(Network network) {}
        public void onLosing(Network network, int maxMsToLive) {}
        public void onLost(Network network) {}
        public void onUnavailable() {}
        public void onCapabilitiesChanged(Network network,
                NetworkCapabilities networkCapabilities) {}
        public void onLinkPropertiesChanged(Network network,
                LinkProperties linkProperties) {}
        public void onBlockedStatusChanged(Network network, boolean blocked) {}
    }
}
