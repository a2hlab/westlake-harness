// Donor for adapter-mainline-stubs android.net.wifi.WifiConfiguration (merge rule: see ../NetworkInfo.java).
// Source: AOSP android-14.0.0_r1 packages/modules/Wifi/framework/java/android/net/wifi/WifiConfiguration.java.
// Only fields whose AOSP initial value is the Java default (SSID = null :3198, hiddenSSID = false :3204) are
// added: the deployed constructor cannot be changed, so allowedKeyManagement / enterpriseConfig (non-null objects
// in AOSP) are left out rather than shipped as nulls.
package android.net.wifi;

import android.net.ProxyInfo;

public class WifiConfiguration {
    public WifiConfiguration() {}                                     // [existing]

    public String SSID;                                               // AOSP :1027
    public boolean hiddenSSID;                                        // AOSP :1229
    public ProxyInfo getHttpProxy() { return null; }                  // AOSP :3832; no IpConfiguration proxy
}
