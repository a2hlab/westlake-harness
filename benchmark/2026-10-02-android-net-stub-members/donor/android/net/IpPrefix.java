// Donor for adapter-mainline-stubs android.net.IpPrefix (merge rule: see NetworkInfo.java). Source: AOSP
// android-14.0.0_r1 packages/modules/Connectivity/framework/src/android/net/IpPrefix.java. No prefix is ever built.
package android.net;

import java.net.InetAddress;

public class IpPrefix {
    public IpPrefix() {}                                              // [existing]
    public InetAddress getAddress() { return null; }
    public int getPrefixLength() { return 0; }
}
