// Donor for adapter-mainline-stubs android.net.ConnectivityManager (see NetworkInfo.java header for the merge rule).
// Source: AOSP android-14.0.0_r1 packages/modules/Connectivity/framework/src/android/net/ConnectivityManager.java.
// route-A has no ConnectivityService: methods that AOSP answers through mService get a safe default derived from
// the stub's own getActiveNetworkInfo(); handler overloads delegate to the stub's existing 2-arg methods, which the
// runtime's OnlineConnectivityManager overrides -- adding them to the base is what lets those overrides be reached
// (ART resolves a call against the referenced class, so a member missing from the base is NoSuchMethodError even
// when the receiver's subclass defines it).
package android.net;

import android.os.Handler;

public class ConnectivityManager {
    public ConnectivityManager() {}                                                       // [existing]
    public NetworkInfo getActiveNetworkInfo() { return null; }                           // [existing]
    public void registerDefaultNetworkCallback(NetworkCallback cb) {}                     // [existing]
    public void registerNetworkCallback(NetworkRequest r, NetworkCallback cb) {}          // [existing]
    public void requestNetwork(NetworkRequest r, NetworkCallback cb) {}                   // [existing]
    public static class NetworkCallback { public NetworkCallback() {} }                   // [existing]

    /** AOSP :1651 asks mService; here the active network (if any) is the only network. Never null. */
    public NetworkInfo[] getAllNetworkInfo() {
        NetworkInfo active = getActiveNetworkInfo();
        return active == null ? new NetworkInfo[0] : new NetworkInfo[] { active };
    }

    /** AOSP (deprecated) getNetworkInfo(int): the active network when its type matches, else null as in AOSP. */
    public NetworkInfo getNetworkInfo(int networkType) {
        NetworkInfo active = getActiveNetworkInfo();
        return active != null && active.getType() == networkType ? active : null;
    }

    /** AOSP :5482 asks mService; RESTRICT_BACKGROUND_STATUS_DISABLED (:5433) = data saver off. */
    public int getRestrictBackgroundStatus() { return 1; }

    /** AOSP :5365 returns the process-bound network, null when the process is not bound. */
    public Network getBoundNetworkForProcess() { return null; }

    /** AOSP :2761 asks mService whether the default network's radio is active. */
    public boolean isDefaultNetworkActive() {
        NetworkInfo active = getActiveNetworkInfo();
        return active != null && active.isConnected();
    }

    /** AOSP :2714 registers with mService for radio-active events; route-A emits none, so nothing to register. */
    public void addDefaultNetworkActiveListener(OnNetworkActiveListener l) {}

    /** AOSP counterpart of addDefaultNetworkActiveListener. */
    public void removeDefaultNetworkActiveListener(OnNetworkActiveListener l) {}

    /** AOSP :3520 forwards an app's connectivity report to mService; nothing consumes it here. */
    public void reportNetworkConnectivity(Network network, boolean hasConnectivity) {}

    /** AOSP overload with a Handler: same registration, callbacks on the handler's thread. */
    public void registerDefaultNetworkCallback(NetworkCallback cb, Handler handler) {
        registerDefaultNetworkCallback(cb);
    }

    /** AOSP overload with a Handler. */
    public void registerNetworkCallback(NetworkRequest request, NetworkCallback cb, Handler handler) {
        registerNetworkCallback(request, cb);
    }

    /** AOSP overload with a timeout (ms): same request; the stub's registration answers synchronously. */
    public void requestNetwork(NetworkRequest request, NetworkCallback cb, int timeoutMs) {
        requestNetwork(request, cb);
    }

    /** AOSP :2686, verbatim interface. */
    public interface OnNetworkActiveListener {
        void onNetworkActive();
    }
}
