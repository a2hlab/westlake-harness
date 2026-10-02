// Donor for adapter-mainline-stubs android.net.RouteInfo (merge rule: see NetworkInfo.java).
// Source: AOSP android-14.0.0_r1 packages/modules/Connectivity/framework/src/android/net/RouteInfo.java.
// Stub RouteInfo objects carry no route (LinkProperties.getRoutes() is empty), so these are unreachable through
// the platform; they answer as an unset route.
package android.net;

import java.net.InetAddress;

public class RouteInfo {
    public RouteInfo() {}                                             // [existing]
    public InetAddress getGateway() { return null; }
    public IpPrefix getDestination() { return null; }
    public String getInterface() { return null; }
}
