/* U11 (#apex-services / cluster 5 content-provider): single-purpose file (freeze unit) -- install the app's
 * OWN declared ContentProviders after bind, so getContentResolver().query(ownAuthority) resolves. New file. */
package adapter.activity;

import android.content.ComponentName;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * U11 (#content-provider): route-A projects the app's ProviderInfo into AppBindData.providers
 * (AppSchedulerBridge.buildProvidersFromManifest) and calls the stock ActivityThread.handleBindApplication,
 * but the app's own ContentProviders are **never published** -- U9 hilog for provider apps (notepad, fd-k9)
 * shows `[B43-BIND] providers populated: N` + `handleBindApplication returned OK` but **no** publishContentProviders
 * / provider instantiation. So getContentResolver().query(content://<its own authority>) gets a null Cursor
 * (cv2-com-nononsenseapps-notepad: Cursor.moveToFirst() on null; authority
 * content://com.nononsenseapps.notepad.MyContentAuthority). 120/168 U9 keys declare >=1 provider (366 total).
 *
 * Mirror AOSP 14 ActivityThread.installContentProviders/installProvider (local path): for each ProviderInfo,
 * load + instantiate the ContentProvider, attachInfo(appContext, info) (runs its onCreate), take its
 * IContentProvider, build a ContentProviderHolder, and publish the batch into
 * adapter.contentprovider.ContentProviderRegistry (what ActivityManagerAdapter.getContentProvider reads). All
 * hidden APIs by reflection; per-provider try/catch logs the class name and never blocks the rest (failure
 * leaves the app at its U9 state, no regression).
 *
 * ORDERING: wired by a smali needle AFTER the stock handleBindApplication reflection call returns in
 * AppSchedulerBridge (the "[B43-BIND] handleBindApplication returned OK" point), where
 * ActivityThread.currentApplication() is non-null. AOSP installs providers inside handleBindApplication
 * (makeApplication -> installContentProviders -> callApplicationOnCreate), i.e. before Application.onCreate;
 * here the opaque stock handleBindApplication has already run both makeApplication AND callApplicationOnCreate,
 * so provider onCreate runs just AFTER Application.onCreate. That is correct for apps that query their own
 * provider at ACTIVITY-launch time (notepad: MainActivity.onCreate, which is after bind); an app that queries
 * its own provider inside Application.onCreate is not covered by this seam (none observed; the stock path not
 * running at all is the larger, pre-existing problem -- late install is strictly better than never).
 */
public final class AppContentProviders {

    private AppContentProviders() {}

    @SuppressWarnings("unchecked")
    public static void install() {
        try {
            Object ctx = appContext();
            if (ctx == null) {
                System.err.println("[B8-PROV-INSTALL] no live Application context; app providers not installed");
                return;
            }
            Object appBindData = boundApplication();
            if (appBindData == null) {
                System.err.println("[B8-PROV-INSTALL] ActivityThread.mBoundApplication null; app providers not installed");
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

            Map stockLocal = localProvidersByName();   // ActivityThread.mLocalProvidersByName (ComponentName -> record)
            List<Object> holders = new ArrayList<>();
            int ok = 0, already = 0, total = providers.size();
            for (Object cpiObj : providers) {
                android.content.pm.ProviderInfo cpi = (android.content.pm.ProviderInfo) cpiObj;
                if (cpi == null || cpi.authority == null || cpi.name == null) continue;
                // Skip providers the stock installContentProviders already instantiated, so we never run a
                // ContentProvider's onCreate twice (and so the probe distinguishes "stock did it" from "we did it").
                if (stockLocal != null && cpi.packageName != null
                        && stockLocal.get(new ComponentName(cpi.packageName, cpi.name)) != null) {
                    already++;
                    System.err.println("[B8-PROV-INSTALL] " + cpi.authority + " already instantiated by stock; skipped");
                    continue;
                }
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
                    System.err.println("[B8-PROV-INSTALL] provider " + cpi.name + " (authority " + cpi.authority
                            + ") not installed: " + perProvider);
                }
            }
            if (!holders.isEmpty()) {
                publish(holders);
            }
            System.err.println("[B8-PROV-INSTALL] installed " + ok + "/" + total + " app providers ("
                    + already + " already instantiated by stock)");
        } catch (Throwable t) {
            System.err.println("[B8-PROV-INSTALL] app provider install skipped: " + t);
        }
    }

    /** ActivityThread.mLocalProvidersByName (ComponentName -> ProviderClientRecord): providers stock already
     *  instantiated locally. Used to skip double-instantiation. */
    private static Map localProvidersByName() {
        try {
            Class<?> at = Class.forName("android.app.ActivityThread");
            Object thread = at.getMethod("currentActivityThread").invoke(null);
            if (thread == null) return null;
            Field f = at.getDeclaredField("mLocalProvidersByName");
            f.setAccessible(true);
            return (Map) f.get(thread);
        } catch (Throwable ignore) {
            return null;
        }
    }

    /** The AppBindData bound for this process (ActivityThread.mBoundApplication). */
    private static Object boundApplication() {
        try {
            Class<?> at = Class.forName("android.app.ActivityThread");
            Object thread = at.getMethod("currentActivityThread").invoke(null);
            if (thread == null) return null;
            Field f = at.getDeclaredField("mBoundApplication");
            f.setAccessible(true);
            return f.get(thread);
        } catch (Throwable ignore) {
            return null;
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
