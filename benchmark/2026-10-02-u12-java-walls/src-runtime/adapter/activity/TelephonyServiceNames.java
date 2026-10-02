package adapter.activity;

import java.lang.reflect.Field;
import java.util.Map;

/**
 * Class-to-name entries for the telephony fetchers TelephonyFetcher installs.
 *
 * AOSP fills both SystemServiceRegistry maps from TelephonyFrameworkInitializer.registerServiceWrappers(); route-A's
 * stub of that class registers nothing, so TelephonyFetcher replaces the "phone" and
 * "telephony_subscription_service" fetchers (log: "fetcher replaced (prev=null)") but SYSTEM_SERVICE_NAMES has no
 * TelephonyManager / SubscriptionManager entry. getSystemService(String) works, getSystemService(Class) returns null
 * (Linkify.gatherTelLinks: "TelephonyManager.getSimCountryIso() on a null object reference", clipboardeditor).
 * Same registration as OnlineConnectivityManager.registerServiceName / AppWidgetFetcher, only where the fetcher
 * exists and the class has no name yet.
 */
public final class TelephonyServiceNames {
    private static final String[][] NAMES = {
        {"android.telephony.TelephonyManager", "phone"},
        {"android.telephony.SubscriptionManager", "telephony_subscription_service"},
    };

    private TelephonyServiceNames() {}

    @SuppressWarnings("unchecked")
    public static void install() {
        try {
            Class<?> registry = Class.forName("android.app.SystemServiceRegistry");
            Map<Class<?>, String> names = (Map<Class<?>, String>) staticField(registry, "SYSTEM_SERVICE_NAMES");
            Map<String, ?> fetchers = (Map<String, ?>) staticField(registry, "SYSTEM_SERVICE_FETCHERS");
            for (String[] entry : NAMES) {
                Class<?> type = Class.forName(entry[0]);
                String present = names.get(type);
                if (present != null) {
                    log(entry[1] + " class->name already " + present + " for " + entry[0]);
                } else if (fetchers.get(entry[1]) == null) {
                    log(entry[1] + " class->name skipped: no fetcher");
                } else {
                    names.put(type, entry[1]);
                    log(entry[1] + " class->name registered for " + entry[0] + " (prev=null)");
                }
            }
        } catch (Throwable t) {
            log("telephony class->name skipped: " + t);
        }
    }

    private static Object staticField(Class<?> owner, String name) throws ReflectiveOperationException {
        Field field = owner.getDeclaredField(name);
        field.setAccessible(true);
        return field.get(null);
    }

    private static void log(String message) {
        System.err.println("[B8-FETCH] " + message);
    }
}
