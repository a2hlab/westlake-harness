// Donor for adapter-mainline-stubs android.net.wifi.ScanResult (merge rule: see ../NetworkInfo.java).
// Source: AOSP android-14.0.0_r1 packages/modules/Wifi/framework/java/android/net/wifi/ScanResult.java.
// Adds the public fields apps read and AOSP's copy constructor for them; WifiManager.getScanResults() returns an
// empty list here, so these objects only exist when an app builds or copies one itself.
package android.net.wifi;

public class ScanResult {
    public ScanResult() {}                                                    // [existing]

    public String SSID;
    public String BSSID;
    public String capabilities;
    public int level;
    public int frequency;
    public long timestamp;
    public CharSequence venueName;      // AOSP :758; the no-arg constructor (:1482) sets no field
    public int channelWidth;
    public int centerFreq0;

    /** AOSP copy constructor, restricted to the fields this stub carries. */
    public ScanResult(ScanResult source) {
        if (source != null) {
            SSID = source.SSID;
            BSSID = source.BSSID;
            capabilities = source.capabilities;
            level = source.level;
            frequency = source.frequency;
            timestamp = source.timestamp;
            venueName = source.venueName;
            channelWidth = source.channelWidth;
            centerFreq0 = source.centerFreq0;
        }
    }
}
