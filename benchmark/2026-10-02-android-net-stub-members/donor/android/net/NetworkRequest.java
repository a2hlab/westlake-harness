// Donor for adapter-mainline-stubs android.net.NetworkRequest (merge rule: see NetworkInfo.java).
// Source: AOSP android-14.0.0_r1 packages/modules/Connectivity/framework/src/android/net/NetworkRequest.java.
// The deployed NetworkRequest.Builder records nothing (addCapability/addTransportType return the builder and keep
// no state), so a stub request is a request with no requirements: no capabilities or transports to report, and
// any network satisfies it. Builder.setIncludeOtherUidNetworks returns the builder like the AOSP setter.
package android.net;

public class NetworkRequest {
    public NetworkRequest() {}                                        // [existing]

    public int[] getCapabilities() { return new int[0]; }
    public int[] getTransportTypes() { return new int[0]; }
    public boolean hasCapability(int capability) { return false; }
    public boolean hasTransport(int transportType) { return false; }
    public boolean canBeSatisfiedBy(NetworkCapabilities nc) { return nc != null; }

    public static class Builder {
        public Builder() {}                                           // [existing]
        public Builder setIncludeOtherUidNetworks(boolean include) { return this; }
    }
}
