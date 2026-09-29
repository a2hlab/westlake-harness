package adapter.activity;

import android.os.IBinder;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Map;

/**
 * B8 (#65) INVENTORY items 6, 7 and 15, applied from ensureBindApplication.
 *
 * Items 6/7: "appops", "uimode", "locale", "account" and "alarm" have no OH service, so
 * SystemServiceRegistry's fetchers throw ServiceNotFoundException and getSystemService returns
 * null (minetest appops; AppCompat night mode, per-app locale, AccountManager, WorkManager).
 * Westlake answers them in process with LocalServiceBinders (copied verbatim); here each is put
 * into ServiceManager.sCache only when ServiceManager has nothing for that name.
 *
 * Item 15: AppBindData.disabledCompatChanges was always new long[0]; Westlake's
 * CompatChangeTable (copied verbatim) gives the changes disabled for the app's targetSdkVersion.
 */
public final class B8BindExtras {
    // #72 service-matrix: r8b-stub (appops/uimode/locale/account/alarm), missing (notification,
    // jobscheduler), westlake-only (connectivity, location) -- the first-frame-irrelevant services
    // that only need a non-null binder so getSystemService does not NPE (#70 revision).
    // #72 service-matrix: r8b-stub (appops/uimode/locale/account/alarm), missing (notification,
    // jobscheduler), westlake-only (connectivity, location) -- the first-frame-irrelevant services
    // that only need a non-null binder so getSystemService does not NPE (#70 revision).
    // connectivity + jobscheduler are handled by OnlineConnectivityManager (SystemServiceRegistry
    // fetcher replacement, #90), not by an sCache binder stub, so they are not listed here.
    // r17b (#F): batterystats + batteryproperties added -- newpipe reads BatteryManager.getIntProperty
    // while starting its main activity; without both binders BatteryManager NPEs. LocalServiceBinders
    // answers batteryproperties.getProperty with idle-charged constants.
    private static final String[] SERVICES = {"appops", "uimode", "locale", "account", "alarm",
            "notification", "location", "webviewupdate", "shortcut",
            "batterystats", "batteryproperties", "deviceidle"};

    private B8BindExtras() {}

    @SuppressWarnings("unchecked")
    public static void installServiceStubs() {
        try {
            Class<?> serviceManager = Class.forName("android.os.ServiceManager");
            Field cacheField = serviceManager.getDeclaredField("sCache");
            cacheField.setAccessible(true);
            Map<String, IBinder> cache = (Map<String, IBinder>) cacheField.get(null);
            Method getService = serviceManager.getMethod("getService", String.class);
            for (String name : SERVICES) {
                IBinder existing = (IBinder) getService.invoke(null, name);
                if (existing != null) continue;
                IBinder local = LocalServiceBinders.get(name);
                if (local == null) continue;
                synchronized (cache) {
                    cache.put(name, local);
                }
                System.err.println("[B8-SVC] " + name + " answered in process (LocalServiceBinders)");
            }
        } catch (Throwable t) {
            System.err.println("[B8-SVC] service stubs not installed: " + t);
        }
    }

    /**
     * Item 3: called right after AppSchedulerBridge sets AppBindData.providers from
     * buildProvidersFromManifest, which carries no metaData and a synthetic applicationInfo.
     * Each provider gets its manifest metaData and the real bound ApplicationInfo.
     */
    @SuppressWarnings("unchecked")
    public static void afterProviders(Object data) {
        try {
            Field appInfoField = data.getClass().getDeclaredField("appInfo");
            appInfoField.setAccessible(true);
            android.content.pm.ApplicationInfo appInfo = (android.content.pm.ApplicationInfo) appInfoField.get(data);
            Field providersField = data.getClass().getDeclaredField("providers");
            providersField.setAccessible(true);
            java.util.List<android.content.pm.ProviderInfo> providers =
                    (java.util.List<android.content.pm.ProviderInfo>) providersField.get(data);
            if (appInfo == null || providers == null) return;
            int withMetaData = 0;
            for (android.content.pm.ProviderInfo provider : providers) {
                android.content.pm.ProviderInfo manifest = SelfComponentFallback.manifestProvider(
                        provider.name, android.content.pm.PackageManager.GET_META_DATA);
                if (manifest != null && provider.metaData == null && manifest.metaData != null) {
                    provider.metaData = manifest.metaData;
                    withMetaData++;
                }
                provider.applicationInfo = appInfo;
            }
            System.err.println("[B8-PROV] bind providers=" + providers.size() + " metaData filled=" + withMetaData);
        } catch (Throwable t) {
            System.err.println("[B8-PROV] provider list not projected: " + t);
        }
    }

    /** Called right after AppSchedulerBridge sets AppBindData.disabledCompatChanges = new long[0]. */
    public static void afterBindData(Object data) {
        try {
            Field appInfoField = data.getClass().getDeclaredField("appInfo");
            appInfoField.setAccessible(true);
            android.content.pm.ApplicationInfo appInfo = (android.content.pm.ApplicationInfo) appInfoField.get(data);
            if (appInfo == null) return;
            long[] disabled = CompatChangeTable.disabledFor(appInfo.targetSdkVersion);
            Field changes = data.getClass().getDeclaredField("disabledCompatChanges");
            changes.setAccessible(true);
            changes.set(data, disabled);
            System.err.println("[B8-COMPAT] targetSdk=" + appInfo.targetSdkVersion + " disabledCompatChanges="
                    + disabled.length + "/" + CompatChangeTable.size());
        } catch (Throwable t) {
            System.err.println("[B8-COMPAT] compat table not applied: " + t);
        }
    }
}
