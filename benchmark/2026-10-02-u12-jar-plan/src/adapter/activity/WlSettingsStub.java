package adapter.activity;

/**
 * Upstream Westlake path B of the in-process settings answer, copied verbatim (rule: copy what is verified).
 *
 * Source: a2hlab/westlake, ref corpus2-fixes 2c46770aa27f, file
 * framework/appspawn-x/java/com/android/internal/os/AppSpawnXInit.java (blob 30a699c1), lines 2273-2360:
 * installSettingsContentProviderStub() and injectProviderHolder(), as of commit 1c883ad (ANDROID_ID answer).
 * The only edit: installSettingsContentProviderStub is public instead of private, because route-A's
 * AppSpawnXInit keeps its own hollowed method of that name and calls this class from preInitSettingsCache
 * (one smali needle, see build_u12.py).
 */
public final class WlSettingsStub {
    private WlSettingsStub() {}

    public static void installSettingsContentProviderStub() {
        System.err.println("[SettingsCache] installSettingsContentProviderStub enter");
        try {
            Class<?> icpClass = Class.forName("android.content.IContentProvider");
            java.lang.reflect.InvocationHandler h = (proxy, method, args) -> {
                String mname = method.getName();
                if ("call".equals(mname)) {
                    // Empty Bundle = lookup miss, the caller's default -- except the few values
                    // Android never leaves unset (ANDROID_ID), answered by WlSettingsProvider.
                    // call(attributionSource, authority, method, arg, extras): the last two Strings.
                    android.os.Bundle b = new android.os.Bundle();
                    String settingsMethod = null, settingsArg = null;
                    for (Object a : args == null ? new Object[0] : args) {
                        if (a instanceof String) { settingsMethod = settingsArg; settingsArg = (String) a; }
                    }
                    String value = adapter.activity.WlSettingsProvider.answer(settingsMethod, settingsArg);
                    if (value != null) b.putString("value", value);
                    return b;
                }
                if ("query".equals(mname)) return null;
                Class<?> rt = method.getReturnType();
                if (rt == void.class) return null;
                if (rt == boolean.class) return Boolean.FALSE;
                if (rt == int.class) return 0;
                if (rt == long.class) return 0L;
                return null;
            };
            Object stub = java.lang.reflect.Proxy.newProxyInstance(
                    icpClass.getClassLoader(),
                    new Class<?>[]{icpClass},
                    h);
            // Inject into all three Settings holders
            for (String settingsCls : new String[]{
                    "android.provider.Settings$Global",
                    "android.provider.Settings$Secure",
                    "android.provider.Settings$System"}) {
                injectProviderHolder(settingsCls, stub);
            }
            System.err.println("[SettingsCache] IContentProvider Proxy installed in 3 holders");
        } catch (Throwable t) {
            System.err.println("[SettingsCache] installSettingsContentProviderStub FAIL: " + t);
        }
    }

    private static void injectProviderHolder(String settingsCls, Object stubProvider) {
        try {
            Class<?> cls = Class.forName(settingsCls);
            java.lang.reflect.Field cacheField = null;
            for (java.lang.reflect.Field f : cls.getDeclaredFields()) {
                if (f.getType().getSimpleName().equals("NameValueCache")
                        && java.lang.reflect.Modifier.isStatic(f.getModifiers())) {
                    cacheField = f;
                    break;
                }
            }
            if (cacheField == null) return;
            cacheField.setAccessible(true);
            Object cache = cacheField.get(null);
            if (cache == null) return;
            // mProviderHolder field on cache (or super)
            java.lang.reflect.Field holderField = null;
            try { holderField = cache.getClass().getDeclaredField("mProviderHolder"); }
            catch (NoSuchFieldException e1) {
                try { holderField = cache.getClass().getSuperclass().getDeclaredField("mProviderHolder"); }
                catch (NoSuchFieldException e2) {}
            }
            if (holderField == null) return;
            holderField.setAccessible(true);
            Object holder = holderField.get(cache);
            if (holder == null) return;
            // Holder.mContentProvider is private IContentProvider
            java.lang.reflect.Field cpField = null;
            try { cpField = holder.getClass().getDeclaredField("mContentProvider"); }
            catch (NoSuchFieldException e) {
                for (java.lang.reflect.Field f : holder.getClass().getDeclaredFields()) {
                    if (f.getType().getName().equals("android.content.IContentProvider")) {
                        cpField = f; break;
                    }
                }
            }
            if (cpField == null) return;
            cpField.setAccessible(true);
            cpField.set(holder, stubProvider);
            System.err.println("[SettingsCache]   injected mContentProvider into " + settingsCls + " holder");
        } catch (Throwable t) {
            System.err.println("[SettingsCache]   injectProviderHolder " + settingsCls + " FAIL: " + t);
        }
    }
}
