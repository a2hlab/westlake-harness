package adapter.activity;

import java.lang.reflect.Method;

/**
 * "telephony.registry" present-but-off binder (2026-10-03-u13-jar-v2), the same way TelephonyFetcher seeds
 * "phone" (WlTelephonyStub) and "isub" (WlSubStub).
 *
 * TelephonyRegistryManager caches ITelephonyRegistry.Stub.asInterface(ServiceManager.getService("telephony.registry"))
 * in a static field. On route A that service is absent (OHServiceManager -> null), so every
 * TelephonyManager.listen() / registerTelephonyCallback() dies with an NPE on listenWithEventList. U12 window 4: x's
 * first fatal after the U12 telephony fixes (com.twitter.util.telephony.a.run -> TelephonyManager.listen).
 *
 * install() calls TelephonyFetcher.seedSafeBinder("telephony.registry", ITelephonyRegistry, "WlTelephonyRegistryStub"):
 * a Binder whose queryLocalInterface returns a Proxy of the interface answering every call with the zero value of
 * its return type (void listeners -> no-op), put into ServiceManager's cache. It runs at bind, before app code can
 * construct a TelephonyRegistryManager. Nothing else changes.
 */
public final class TelephonyRegistryStub {
    private TelephonyRegistryStub() {}

    public static void install() {
        try {
            Method seed = Class.forName("adapter.activity.TelephonyFetcher").getDeclaredMethod("seedSafeBinder", String.class, String.class,
                    String.class);
            seed.setAccessible(true);
            seed.invoke(null, "telephony.registry", "com.android.internal.telephony.ITelephonyRegistry",
                    "WlTelephonyRegistryStub");
        } catch (Throwable t) {
            System.err.println("[B8-FETCH] telephony.registry seed failed: " + t);
        }
    }
}
