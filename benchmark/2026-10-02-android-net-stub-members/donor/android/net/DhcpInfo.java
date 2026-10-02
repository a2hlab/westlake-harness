// NEW class for adapter-mainline-stubs (absent from the deployed BCP; WifiManager.getDhcpInfo() returns it).
// Source: AOSP android-14.0.0_r1 packages/modules/Connectivity/framework/src/android/net/DhcpInfo.java, verbatim
// except putAddress: AOSP calls the hidden NetworkUtils.intToInetAddress(addr).getHostAddress(); the same
// little-endian int -> dotted quad is inlined so the class needs no hidden API.
package android.net;

import android.os.Parcel;
import android.os.Parcelable;

public class DhcpInfo implements Parcelable {
    public int ipAddress;
    public int gateway;
    public int netmask;
    public int dns1;
    public int dns2;
    public int serverAddress;
    public int leaseDuration;

    public DhcpInfo() {
        super();
    }

    public DhcpInfo(DhcpInfo source) {
        if (source != null) {
            ipAddress = source.ipAddress;
            gateway = source.gateway;
            netmask = source.netmask;
            dns1 = source.dns1;
            dns2 = source.dns2;
            serverAddress = source.serverAddress;
            leaseDuration = source.leaseDuration;
        }
    }

    public String toString() {
        StringBuffer str = new StringBuffer();
        str.append("ipaddr "); putAddress(str, ipAddress);
        str.append(" gateway "); putAddress(str, gateway);
        str.append(" netmask "); putAddress(str, netmask);
        str.append(" dns1 "); putAddress(str, dns1);
        str.append(" dns2 "); putAddress(str, dns2);
        str.append(" DHCP server "); putAddress(str, serverAddress);
        str.append(" lease ").append(leaseDuration).append(" seconds");
        return str.toString();
    }

    private static void putAddress(StringBuffer buf, int addr) {
        buf.append(addr & 0xff).append('.').append((addr >> 8) & 0xff).append('.')
                .append((addr >> 16) & 0xff).append('.').append((addr >>> 24) & 0xff);
    }

    public int describeContents() {
        return 0;
    }

    public void writeToParcel(Parcel dest, int flags) {
        dest.writeInt(ipAddress);
        dest.writeInt(gateway);
        dest.writeInt(netmask);
        dest.writeInt(dns1);
        dest.writeInt(dns2);
        dest.writeInt(serverAddress);
        dest.writeInt(leaseDuration);
    }

    public static final Creator<DhcpInfo> CREATOR =
        new Creator<DhcpInfo>() {
            public DhcpInfo createFromParcel(Parcel in) {
                DhcpInfo info = new DhcpInfo();
                info.ipAddress = in.readInt();
                info.gateway = in.readInt();
                info.netmask = in.readInt();
                info.dns1 = in.readInt();
                info.dns2 = in.readInt();
                info.serverAddress = in.readInt();
                info.leaseDuration = in.readInt();
                return info;
            }

            public DhcpInfo[] newArray(int size) {
                return new DhcpInfo[size];
            }
        };
}
