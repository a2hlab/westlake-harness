// Donor for adapter-mainline-stubs android.net.wifi.WifiInfo (merge rule: see ../NetworkInfo.java).
// Source: AOSP android-14.0.0_r1 packages/modules/Wifi/framework/java/android/net/wifi/WifiInfo.java.
// The stub WifiInfo has no fields: every object is the AOSP default-constructed WifiInfo (:489), so each getter
// returns that object's value -- the same thing AOSP hands an app before association or when location access
// redacts the connection (SSID "<unknown ssid>", BSSID null, network id -1, INVALID_RSSI, LINK_SPEED_UNKNOWN).
package android.net.wifi;

import android.net.MacAddress;
import android.os.Parcel;
import java.util.Collections;
import java.util.List;

public class WifiInfo {
    public WifiInfo() {}                                                      // [existing]

    public String getSSID() { return "<unknown ssid>"; }                      // :777 WifiManager.UNKNOWN_SSID (:1883)
    public String getBSSID() { return null; }                                 // mBSSID = null
    public int getRssi() { return -127; }                                     // INVALID_RSSI (:146)
    public int getLinkSpeed() { return -1; }                                  // LINK_SPEED_UNKNOWN (:231)
    public int getTxLinkSpeedMbps() { return -1; }
    public int getRxLinkSpeedMbps() { return -1; }
    public int getMaxSupportedTxLinkSpeedMbps() { return -1; }
    public int getMaxSupportedRxLinkSpeedMbps() { return -1; }
    public int getFrequency() { return -1; }                                  // UNKNOWN_FREQUENCY
    public String getMacAddress() { return "02:00:00:00:00:00"; }             // DEFAULT_MAC_ADDRESS (:94)
    public boolean getHiddenSSID() { return false; }
    public int getNetworkId() { return -1; }
    public int getIpAddress() { return 0; }                                   // no InetAddress set
    public SupplicantState getSupplicantState() { return SupplicantState.UNINITIALIZED; }
    public int getSubscriptionId() { return -1; }                             // INVALID_SUBSCRIPTION_ID
    public int getCurrentSecurityType() { return -1; }                        // mSecurityType = -1
    public int getWifiStandard() { return 0; }                                // WIFI_STANDARD_UNKNOWN
    public String getPasspointFqdn() { return null; }
    public String getPasspointProviderFriendlyName() { return null; }
    public boolean isRestricted() { return false; }
    public int getApMloLinkId() { return -1; }                                // MloLink.INVALID_MLO_LINK_ID
    public MacAddress getApMldMacAddress() { return null; }
    public List getAffiliatedMloLinks() { return Collections.emptyList(); }   // emptyList() in the constructor
    public List getAssociatedMloLinks() { return Collections.emptyList(); }
    public List getInformationElements() { return null; }                     // null until an association has IEs
    public long getApplicableRedactions() { return 7L; }                     // :1932 REDACT_FOR_ACCESS_FINE_LOCATION|LOCAL_MAC_ADDRESS|NETWORK_SETTINGS (1|2|4)
    public WifiInfo makeCopy(long redactions) { return new WifiInfo(); }      // a copy of a default object
    public int describeContents() { return 0; }
    public void writeToParcel(Parcel dest, int flags) {}                      // nothing to write: no state
}
