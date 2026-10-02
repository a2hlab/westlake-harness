// Donor for adapter-mainline-stubs android.net.NetworkCapabilities (merge rule: see NetworkInfo.java).
// Source: AOSP android-14.0.0_r1 packages/modules/Connectivity/framework/src/android/net/NetworkCapabilities.java.
package android.net;

public class NetworkCapabilities {
    public NetworkCapabilities() {}                                   // [existing]

    /** AOSP returns mTransportInfo, null when the transport attached none (no WifiInfo on route-A). */
    public TransportInfo getTransportInfo() { return null; }
}
