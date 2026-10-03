// U16 t1: android.net.wifi.WifiManager methods fd-wifianalyzer calls that adapter-mainline-stubs
// (U15 94a94905) lacks — stub_member_gap on com.vrem.wifianalyzer_72.apk.282a06fc: exactly 8.
// Semantics per specs/u16-batch/t1-wifimanager.spec.md: "no Wi-Fi device" — no service exists on
// route-A, so the radio reads DISABLED (outer 11:45 overrode the 2026-10-02 donor's "enabled"):
// empty scan list, false toggles/queries, default WifiInfo; nothing throws.
// Signatures mirrored from AOSP android-14.0.0_r1 packages/modules/Wifi/framework/
// java/android/net/wifi/WifiManager.java (same file the 2026-10-02 donor cites; donor copy kept
// verbatim at benchmark/2026-10-02-android-net-stub-members/donor for cross-check).
package android.net.wifi;

import java.util.Collections;
import java.util.List;

public class WifiManager {
    // AOSP: public WifiInfo getConnectionInfo()
    public WifiInfo getConnectionInfo() { return new WifiInfo(); }   // default WifiInfo (donor WifiInfo.java)
    // AOSP: public List<ScanResult> getScanResults()
    public List<ScanResult> getScanResults() { return Collections.emptyList(); }
    // AOSP: public boolean is5GHzBandSupported()  (service ask; no radio -> false)
    public boolean is5GHzBandSupported() { return false; }
    // AOSP: public boolean is6GHzBandSupported()
    public boolean is6GHzBandSupported() { return false; }
    // AOSP: public boolean isScanThrottleEnabled()
    public boolean isScanThrottleEnabled() { return false; }
    // AOSP: public boolean isWifiEnabled()  (no radio -> disabled)
    public boolean isWifiEnabled() { return false; }
    // AOSP: public boolean setWifiEnabled(boolean)  (AOSP Q+: apps cannot toggle -> false)
    public boolean setWifiEnabled(boolean enabled) { return false; }
    // AOSP: public boolean startScan()  (AOSP: request not accepted -> false)
    public boolean startScan() { return false; }
}
