// Donor for adapter-mainline-stubs android.net.wifi.WifiManager (merge rule: see ../NetworkInfo.java).
// Source: AOSP android-14.0.0_r1 packages/modules/Wifi/framework/java/android/net/wifi/WifiManager.java.
// route-A has no WifiService. The network the runtime reports is connected Wi-Fi (OnlineConnectivityManager), so
// the radio reads as enabled; everything that would need the service answers the way AOSP answers an app without
// the privileges for it (empty scan results / configured networks, startScan and setWifiEnabled refused).
package android.net.wifi;

import android.net.DhcpInfo;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.Executor;

public class WifiManager {
    public WifiManager() {}                                                   // [existing]

    /** AOSP :5221, verbatim (MIN_RSSI -100 :1833, MAX_RSSI -55 :1837). */
    public static int calculateSignalLevel(int rssi, int numLevels) {
        if (rssi <= -100) {
            return 0;
        } else if (rssi >= -55) {
            return numLevels - 1;
        } else {
            float inputRange = (-55 - -100);
            float outputRange = (numLevels - 1);
            return (int) ((float) (rssi - -100) * outputRange / inputRange);
        }
    }

    public WifiInfo getConnectionInfo() { return new WifiInfo(); }            // default WifiInfo, see WifiInfo.java
    public DhcpInfo getDhcpInfo() { return new DhcpInfo(); }                  // all-zero DhcpInfo
    public List<ScanResult> getScanResults() { return Collections.emptyList(); }
    public List<WifiConfiguration> getConfiguredNetworks() { return Collections.emptyList(); }  // AOSP Q+ for apps
    public boolean isWifiEnabled() { return true; }
    public int getWifiState() { return 3; }                                   // WIFI_STATE_ENABLED (:1089)
    public boolean startScan() { return false; }                              // AOSP: request not accepted
    public boolean setWifiEnabled(boolean enabled) { return false; }          // AOSP Q+: apps cannot toggle
    public void addSuggestionConnectionStatusListener(Executor executor,
            SuggestionConnectionStatusListener listener) {}                   // no suggestions, no events
    public WifiLock createWifiLock(String tag) { return new WifiLock(tag); }
    public WifiLock createWifiLock(int lockType, String tag) { return new WifiLock(tag); }   // AOSP: type recorded
    public boolean is5GHzBandSupported() { return false; }          // AOSP :4111 asks the service; no radio info
    public boolean is6GHzBandSupported() { return false; }          // AOSP :4137
    public MulticastLock createMulticastLock(String tag) { return new MulticastLock(tag); }

    /** AOSP :9423 interface (method signature verbatim). */
    public interface SuggestionConnectionStatusListener {
        void onConnectionStatus(WifiNetworkSuggestion wifiNetworkSuggestion, int failureReason);
    }

    /** AOSP :7618 WifiLock: the same reference counting, without the service acquire/release calls. */
    public class WifiLock {
        private String mTag;
        private int mRefCount;
        private boolean mRefCounted;
        private boolean mHeld;

        WifiLock(String tag) {   // AOSP: private; package-private so d8 needs no synthetic accessor class
            mTag = tag;
            mRefCount = 0;
            mRefCounted = true;
            mHeld = false;
        }

        public void acquire() {
            synchronized (this) {
                if (mRefCounted ? (++mRefCount == 1) : (!mHeld)) {
                    mHeld = true;
                }
            }
        }

        public void release() {
            synchronized (this) {
                if (mRefCounted ? (--mRefCount == 0) : (mHeld)) {
                    mHeld = false;
                }
                if (mRefCount < 0) {
                    throw new RuntimeException("WifiLock under-locked " + mTag);
                }
            }
        }

        public void setReferenceCounted(boolean refCounted) { mRefCounted = refCounted; }

        public boolean isHeld() {
            synchronized (this) {
                return mHeld;
            }
        }

        public String toString() {
            return "WifiLock{ " + mTag + "; held=" + mHeld + "; refcount=" + mRefCount + " }";
        }
    }

    /** AOSP :8004 MulticastLock: the same reference counting, without the service calls. */
    public class MulticastLock {
        private String mTag;
        private int mRefCount;
        private boolean mRefCounted;
        private boolean mHeld;

        MulticastLock(String tag) {   // AOSP: private; package-private, see WifiLock
            mTag = tag;
            mRefCount = 0;
            mRefCounted = true;
            mHeld = false;
        }

        public void acquire() {
            synchronized (this) {
                if (mRefCounted ? (++mRefCount == 1) : (!mHeld)) {
                    mHeld = true;
                }
            }
        }

        public void release() {
            synchronized (this) {
                if (mRefCounted ? (--mRefCount == 0) : (mHeld)) {
                    mHeld = false;
                }
                if (mRefCount < 0) {
                    throw new RuntimeException("MulticastLock under-locked " + mTag);
                }
            }
        }

        public void setReferenceCounted(boolean refCounted) { mRefCounted = refCounted; }

        public boolean isHeld() {
            synchronized (this) {
                return mHeld;
            }
        }

        public String toString() {
            return "MulticastLock{ " + mTag + "; held=" + mHeld + "; refcount=" + mRefCount + " }";
        }
    }
}
