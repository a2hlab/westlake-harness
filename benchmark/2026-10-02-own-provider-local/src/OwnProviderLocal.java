package adapter.activity;

import android.content.pm.ProviderInfo;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * #90 toutiao wall 1 (own-provider lookup): answer IActivityManager.getContentProvider for a provider that belongs to
 * this app and can run in this process the way AOSP's ActivityManagerService does -- a holder with provider == null
 * and mLocal == true, so the stock ActivityThread.acquireProvider instantiates the provider in-process
 * (installProvider -> attachInfo -> onCreate) and records it in mProviderMap / mLocalProvidersByName.
 *
 * Copied from AOSP android-14.0.0_r1:
 *   ContentProviderHelper.getContentProviderImpl :256 / :455  `if (r != null && cpr.canRunHere(r))` ->
 *       `ContentProviderHolder holder = cpr.newHolder(null, true); holder.provider = null;`
 *   ContentProviderRecord.canRunHere :122  `(info.multiprocess || info.processName.equals(app.processName))
 *       && uid == app.info.uid`
 *   ActivityThread.acquireProvider :7293  waits only when `holder.provider == null && !holder.mLocal`, else
 *       installProvider(...) locally.
 *
 * Why: the deployed ContentProviderRegistry.acquireProvider (BCP) answers every authority it has not published with
 * an OH DataShare bridge holder (provider != null). For the app's OWN authority asked before handleBindApplication
 * installs providers (toutiao: Mira's PluginPackageManager in attachBaseContext, content://<pkg>.pm.PPMP "query_binder"),
 * ActivityThread caches that bridge under the authority; the bridge's call() fails in DataShare ("Creator: token is
 * nullptr"), and when the real provider is installed later installProviderAuthoritiesLocked keeps the cached bridge
 * ("Content provider ... already published as ..."), so every later lookup keeps failing (U10 61b hilog 32087/32471).
 *
 * Scope: only providers from this app's own bind data (AppBindData.providers) whose process is this process (or
 * multiprocess). Anything else -- other packages, other processes of the same app, any failure here -- is delegated
 * unchanged. New file; wired by a build-time smali needle right after ActivityManagerBindProxy.install(), i.e. before
 * handleBindApplication, so it wraps the B8-AMB proxy and is wrapped by anything the app installs later (Mira).
 */
public final class OwnProviderLocal implements InvocationHandler {
    private static final Set<String> sLogged = ConcurrentHashMap.newKeySet();

    private final Object delegate;

    private OwnProviderLocal(Object delegate) {
        this.delegate = delegate;
    }

    /** Wrap ActivityManager.IActivityManagerSingleton.mInstance once (same pattern as ActivityManagerBindProxy). */
    public static void install() {
        try {
            Class<?> iface = Class.forName("android.app.IActivityManager");
            Class<?> am = Class.forName("android.app.ActivityManager");
            java.lang.reflect.Field singletonField = am.getDeclaredField("IActivityManagerSingleton");
            singletonField.setAccessible(true);
            Object singleton = singletonField.get(null);
            Class<?> singletonClass = Class.forName("android.util.Singleton");
            java.lang.reflect.Field instanceField = singletonClass.getDeclaredField("mInstance");
            instanceField.setAccessible(true);
            singletonClass.getMethod("get").invoke(singleton);
            Object current = instanceField.get(singleton);
            if (current == null) {
                System.err.println("[OWN-PROV-LOCAL] not installed: no IActivityManager instance");
                return;
            }
            if (Proxy.isProxyClass(current.getClass())
                    && Proxy.getInvocationHandler(current) instanceof OwnProviderLocal) {
                return;
            }
            Object proxy = Proxy.newProxyInstance(iface.getClassLoader(), new Class<?>[] {iface},
                    new OwnProviderLocal(current));
            instanceField.set(singleton, proxy);
            System.err.println("[OWN-PROV-LOCAL] installed over " + current.getClass().getName());
        } catch (Throwable t) {
            System.err.println("[OWN-PROV-LOCAL] not installed: " + t);
        }
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        // getContentProvider(IApplicationThread caller, String callingPackage, String name, int userId, boolean stable)
        if ("getContentProvider".equals(method.getName()) && args != null && args.length == 5
                && args[2] instanceof String) {
            try {
                Object holder = localHolder((String) args[2]);
                if (holder != null) {
                    return holder;
                }
            } catch (Throwable t) {
                System.err.println("[OWN-PROV-LOCAL] lookup skipped for " + args[2] + ": " + t);
            }
        }
        try {
            return method.invoke(delegate, args);
        } catch (java.lang.reflect.InvocationTargetException e) {
            throw e.getCause() != null ? e.getCause() : e;
        }
    }

    /** A local ContentProviderHolder for an own provider that can run here, else null (delegate). */
    private static Object localHolder(String authority) throws Exception {
        Class<?> at = Class.forName("android.app.ActivityThread");
        Object thread = at.getMethod("currentActivityThread").invoke(null);
        if (thread == null) return null;
        java.lang.reflect.Field boundField = at.getDeclaredField("mBoundApplication");
        boundField.setAccessible(true);
        Object bound = boundField.get(thread);
        if (bound == null) return null;
        Class<?> bindData = bound.getClass();
        java.lang.reflect.Field providersField = bindData.getDeclaredField("providers");
        providersField.setAccessible(true);
        java.lang.reflect.Field processField = bindData.getDeclaredField("processName");
        processField.setAccessible(true);
        @SuppressWarnings("unchecked")
        List<ProviderInfo> providers = (List<ProviderInfo>) providersField.get(bound);
        String processName = (String) processField.get(bound);
        if (providers == null) return null;
        for (ProviderInfo info : providers) {
            if (info == null || info.authority == null) continue;
            boolean match = false;
            for (String a : info.authority.split(";")) {
                if (a.equals(authority)) {
                    match = true;
                    break;
                }
            }
            if (!match) continue;
            // ContentProviderRecord.canRunHere: multiprocess, or the provider's process is this process (the uid
            // is ours by construction: these are this package's own bind-data providers)
            boolean canRunHere = info.multiprocess
                    || (info.processName != null && info.processName.equals(processName))
                    || (info.processName == null && processName != null && processName.equals(info.packageName));
            if (!canRunHere) return null;
            Class<?> holderClass = Class.forName("android.app.ContentProviderHolder");
            Object holder = holderClass.getConstructor(ProviderInfo.class).newInstance(info);
            holderClass.getField("mLocal").setBoolean(holder, true);
            holderClass.getField("noReleaseNeeded").setBoolean(holder, true);
            // provider stays null: "don't give caller the provider object, it needs to make its own"
            if (sLogged.add(authority)) {
                System.err.println("[OWN-PROV-LOCAL] " + authority + " -> local holder " + info.name
                        + " (process " + processName + ")");
            }
            return holder;
        }
        return null;
    }
}
