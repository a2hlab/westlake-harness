// Donor for adapter-mainline-stubs android.net.LinkProperties (merge rule: see NetworkInfo.java).
// Source: AOSP android-14.0.0_r1 packages/modules/Connectivity/framework/src/android/net/LinkProperties.java.
// The stub LinkProperties is always the AOSP default-constructed object, so each getter returns what AOSP returns
// for that object: empty unmodifiable lists, null strings, private DNS off.
package android.net;

import java.net.Inet4Address;
import java.net.InetAddress;
import java.util.Collections;
import java.util.List;

public class LinkProperties {
    public LinkProperties() {}                                        // [existing]

    public List<InetAddress> getDnsServers() { return Collections.emptyList(); }
    public List<LinkAddress> getLinkAddresses() { return Collections.emptyList(); }
    public List<RouteInfo> getRoutes() { return Collections.emptyList(); }
    public String getDomains() { return null; }
    public String getPrivateDnsServerName() { return null; }
    public boolean isPrivateDnsActive() { return false; }
    public String getInterfaceName() { return null; }                  // mIfaceName unset
    public Inet4Address getDhcpServerAddress() { return null; }        // mDhcpServerAddress unset
    public ProxyInfo getHttpProxy() { return null; }                   // mHttpProxy unset
}
