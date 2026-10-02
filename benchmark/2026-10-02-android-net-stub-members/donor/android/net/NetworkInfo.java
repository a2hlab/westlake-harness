// Donor for adapter-mainline-stubs android.net.NetworkInfo: ONLY the members the deployed stub lacks are merged
// (merge_smali.py); members marked [existing] are declarations so this file compiles and are dropped at merge.
// Source: AOSP android-14.0.0_r1 packages/modules/Connectivity/framework/src/android/net/NetworkInfo.java.
// The deployed stub has no fields and answers through virtual getters (runtime OnlineNetworkInfo overrides
// getType/isConnected/getTypeName), so every added getter derives from getType()/isConnected() instead of fields.
package android.net;

public class NetworkInfo {
    public NetworkInfo() {}                                   // [existing]
    public int getType() { return -1; }                       // [existing]
    public boolean isConnected() { return false; }            // [existing]

    /** AOSP :244 returns mSubtype; 0 = TelephonyManager.NETWORK_TYPE_UNKNOWN (no telephony on route-A). */
    public int getSubtype() { return 0; }

    /** AOSP :275 returns mTypeName, set from ConnectivityManager.getNetworkTypeName(type) (:1130). */
    public String getTypeName() {
        switch (getType()) {
            case -1: return "NONE";
            case 0: return "MOBILE";
            case 1: return "WIFI";
            case 2: return "MOBILE_MMS";
            case 3: return "MOBILE_SUPL";
            case 4: return "MOBILE_DUN";
            case 5: return "MOBILE_HIPRI";
            case 6: return "WIMAX";
            case 7: return "BLUETOOTH";
            case 8: return "DUMMY";
            case 9: return "ETHERNET";
            case 10: return "MOBILE_FOTA";
            case 11: return "MOBILE_IMS";
            case 12: return "MOBILE_CBS";
            case 13: return "WIFI_P2P";
            case 14: return "MOBILE_IA";
            case 15: return "MOBILE_EMERGENCY";
            case 16: return "PROXY";
            case 17: return "VPN";
            case 18: return "TEST";
            default: return Integer.toString(getType());
        }
    }

    /** AOSP :287 returns mSubtypeName; "" for non-mobile networks. */
    public String getSubtypeName() { return ""; }

    /** AOSP :559 returns mExtraInfo, null until a connection reports one. */
    public String getExtraInfo() { return null; }

    /** AOSP :489 returns mDetailedState; derived from isConnected() so the runtime's online override flows in. */
    public DetailedState getDetailedState() {
        return isConnected() ? DetailedState.CONNECTED : DetailedState.DISCONNECTED;
    }

    /** AOSP :545 returns mReason, null when no state change reason was recorded. */
    public String getReason() { return null; }

    /** AOSP :407 returns mIsFailover, false by default. */
    public boolean isFailover() { return false; }

    /** AOSP DetailedState is an enum; the deployed stub declares a plain class (super Object) and changing the
     *  superclass is a reshape the gate forbids, so the 13 AOSP constants are plain instances (== comparable). */
    public static class DetailedState {
        public DetailedState() {}                             // [existing]
        private String mName;
        private DetailedState(String name) { mName = name; }
        public String name() { return mName; }
        @Override public String toString() { return mName; }
        public static final DetailedState IDLE = new DetailedState("IDLE");
        public static final DetailedState SCANNING = new DetailedState("SCANNING");
        public static final DetailedState CONNECTING = new DetailedState("CONNECTING");
        public static final DetailedState AUTHENTICATING = new DetailedState("AUTHENTICATING");
        public static final DetailedState OBTAINING_IPADDR = new DetailedState("OBTAINING_IPADDR");
        public static final DetailedState CONNECTED = new DetailedState("CONNECTED");
        public static final DetailedState SUSPENDED = new DetailedState("SUSPENDED");
        public static final DetailedState DISCONNECTING = new DetailedState("DISCONNECTING");
        public static final DetailedState DISCONNECTED = new DetailedState("DISCONNECTED");
        public static final DetailedState FAILED = new DetailedState("FAILED");
        public static final DetailedState BLOCKED = new DetailedState("BLOCKED");
        public static final DetailedState VERIFYING_POOR_LINK = new DetailedState("VERIFYING_POOR_LINK");
        public static final DetailedState CAPTIVE_PORTAL_CHECK = new DetailedState("CAPTIVE_PORTAL_CHECK");
    }
}
