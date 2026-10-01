/* U11 (#apex-services / cluster 5 content-provider): single-purpose file (freeze unit) -- install the app's
 * OWN declared ContentProviders at bind, so getContentResolver().query(ownAuthority) resolves. New file. */
package adapter.activity;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;

/**
 * U11 (#content-provider): route-A projects the app's ProviderInfo into AppBindData.providers (AppSchedulerBridge
 * .buildProvidersFromManifest + B8BindExtras.afterProviders) but **never instantiates them** -- the stock
 * ActivityThread.installContentProviders step is not run, so the app's own ContentProvider objects are never
 * attached/published and ContentProviderRegistry has no entry for their authorities. An app that does
 * getContentResolver().query(content://<its own authority>) at startup then gets a null Cursor
 * (cv2-com-nononsenseapps-notepad: Cursor.moveToFirst() on null; its authority is
 * content://com.nononsenseapps.notepad.MyContentAuthority). 120/168 U9 keys declare >=1 provider.
 *
 * Mirror AOSP 14 ActivityThread.installContentProviders/installProvider (local path): for each ProviderInfo,
 * load + instantiate the ContentProvider, attachInfo(appContext, info) (runs its onCreate), take its
 * IContentProvider, build a ContentProviderHolder, and publish the batch into our
 * adapter.contentprovider.ContentProviderRegistry (what ActivityManagerAdapter.getContentProvider/acquireProvider
 * reads). All hidden APIs by reflection. Called by a smali needle right AFTER B8BindExtras.afterProviders(data),
 * where the Application is already live (AppSchedulerBridge). Per-provider try/catch: one bad provider never
 * blocks the rest, and failure leaves the app exactly at its U9 state (no regression).
 */
public final class AppContentProviders {

    private AppContentProviders() {}

    @SuppressWarnings("unchecked")
    public static void install(Object appBindData) {
        try {
            Object ctx = appContext();
            if (ctx == null) {
                System.err.println("[B8-PROV-INSTALL] no live Application context at bind; app providers not installed");
                return;
            }
            Field provField = appBindData.getClass().getDeclaredField("providers");
            provField.setAccessible(true);
            List<Object> providers = (List<Object>) provField.get(appBindData);
            if (providers == null || providers.isEmpty()) return;

            ClassLoader cl = ((android.content.Context) ctx).getClassLoader();
            Class<?> cphClass = Class.forName("android.app.ContentProviderHolder");
            Constructor<?> cphCtor = cphClass.getConstructor(android.content.pm.ProviderInfo.class);
            Field cphProvider = cphClass.getField("provider");
            Field cphNoRelease = cphClass.getField("noReleaseNeeded");
            Method getIContentProvider = android.content.ContentProvider.class.getMethod("getIContentProvider");

            List<Object> holders = new ArrayList<>();
            int ok = 0, total = providers.size();
            for (Object cpiObj : providers) {
                android.content.pm.ProviderInfo cpi = (android.content.pm.ProviderInfo) cpiObj;
                if (cpi == null || cpi.authority == null || cpi.name == null) continue;
                try {
                    Class<?> providerClass = cl.loadClass(cpi.name);
                    android.content.ContentProvider lp =
                            (android.content.ContentProvider) providerClass.getDeclaredConstructor().newInstance();
                    lp.attachInfo((android.content.Context) ctx, cpi);   // runs the provider's onCreate
                    Object iContentProvider = getIContentProvider.invoke(lp);
                    Object holder = cphCtor.newInstance(cpi);
                    cphProvider.set(holder, iContentProvider);
                    cphNoRelease.setBoolean(holder, true);
                    holders.add(holder);
                    ok++;
                } catch (Throwable perProvider) {
                    System.err.println("[B8-PROV-INSTALL] " + cpi.authority + " (" + cpi.name + ") not installed: "
                            + perProvider);
                }
            }
            if (!holders.isEmpty()) {
                publish(holders);
            }
            System.err.println("[B8-PROV-INSTALL] installed " + ok + "/" + total + " app providers");
        } catch (Throwable t) {
            System.err.println("[B8-PROV-INSTALL] app provider install skipped: " + t);
        }
    }

    /** The live Application (a Context) bound for this process. */
    private static Object appContext() {
        try {
            Class<?> at = Class.forName("android.app.ActivityThread");
            Object app = at.getMethod("currentApplication").invoke(null);
            if (app != null) return app;
            Object thread = at.getMethod("currentActivityThread").invoke(null);
            if (thread != null) {
                Object a = at.getMethod("getApplication").invoke(thread);
                if (a != null) return a;
            }
        } catch (Throwable ignore) { }
        return null;
    }

    /** adapter.contentprovider.ContentProviderRegistry.getInstance().publishProviders(List<ContentProviderHolder>). */
    private static void publish(List<Object> holders) throws Throwable {
        Class<?> reg = Class.forName("adapter.contentprovider.ContentProviderRegistry");
        Object instance = reg.getMethod("getInstance").invoke(null);
        reg.getMethod("publishProviders", List.class).invoke(instance, holders);
    }
}
