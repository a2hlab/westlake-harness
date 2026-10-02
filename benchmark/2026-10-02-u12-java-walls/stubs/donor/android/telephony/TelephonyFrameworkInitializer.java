package android.telephony;

import android.os.TelephonyServiceManager;

/**
 * Donor for the deployed adapter-mainline-stubs TelephonyFrameworkInitializer, which shadows framework.jar's class on
 * the boot class path and lacks getTelephonyServiceManager(): TelephonyManager.getSubscriptionService()
 * (AOSP 14 TelephonyManager.java:16354) then throws NoSuchMethodError (x: datadog getPhoneType() inside a provider
 * onCreate fails the whole bind). Only getTelephonyServiceManager and its field are merged (members.tsv); the deployed
 * registerServiceWrappers / setTelephonyServiceManager stay as they are (the setter is deployed as a no-op).
 *
 * AOSP 14 returns the instance SystemServiceRegistry hands to setTelephonyServiceManager at boot. Route-A never
 * stores one, so the getter creates framework.jar's TelephonyServiceManager on first use: its registerers look the
 * services up in ServiceManager by name ("isub", "phone" are seeded by TelephonyFetcher), as AOSP's do.
 */
public class TelephonyFrameworkInitializer {
    private static volatile TelephonyServiceManager sTelephonyServiceManager;

    private TelephonyFrameworkInitializer() {}

    public static void registerServiceWrappers() {}

    public static void setTelephonyServiceManager(TelephonyServiceManager manager) {}

    public static TelephonyServiceManager getTelephonyServiceManager() {
        TelephonyServiceManager manager = sTelephonyServiceManager;
        if (manager == null) {
            synchronized (TelephonyFrameworkInitializer.class) {
                if (sTelephonyServiceManager == null) {
                    sTelephonyServiceManager = new TelephonyServiceManager();
                }
                manager = sTelephonyServiceManager;
            }
        }
        return manager;
    }
}
