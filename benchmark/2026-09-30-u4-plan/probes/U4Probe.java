package adapter.diagnostics;

/** Temporary diagnostic only; never part of U4 or a production repair. */
public final class U4Probe implements java.lang.reflect.InvocationHandler {
    private final Object delegate;
    private U4Probe(Object delegate) { this.delegate = delegate; }
    private static String packageName = "";
    private static final boolean CHANGE_APP_THEME = false; // builder changes only this in B

    public static void beforeBind(Object appInfo) {
        try {
            packageName = (String) appInfo.getClass().getField("packageName").get(appInfo);
            if (!"org.videolan.vlc".equals(packageName)) return;
            java.lang.reflect.Field theme = appInfo.getClass().getField("theme");
            int before = theme.getInt(appInfo);
            if (CHANGE_APP_THEME) theme.setInt(appInfo, 0x7f1402ec);
            System.err.println("[U4-VLC] appInfo=" + System.identityHashCode(appInfo)
                    + " before=0x" + Integer.toHexString(before)
                    + " after=0x" + Integer.toHexString(theme.getInt(appInfo))
                    + " change=" + CHANGE_APP_THEME);
        } catch (Throwable e) { System.err.println("[U4-PROBE-ERROR] " + e); }
    }

    public static void finish(Object token, int code, Object data, int finishTask) {
        if (!"com.termux".equals(packageName)) return;
        try {
            // Do not print Intent contents or user data. Preserve the original finish return path.
            System.err.println("[U4-TERMUX-FINISH] token=" + System.identityHashCode(token)
                    + " code=" + code + " task=" + finishTask
                    + " thread=" + Thread.currentThread().getName());
            new Throwable("U4 finish caller").printStackTrace(System.err);
        } catch (Throwable ignored) { }
    }

    public static Object controller(Object original) {
        if (!"com.termux".equals(packageName)) return original;
        try {
            Class<?> iface = Class.forName("android.app.IActivityClientController");
            Object proxy = java.lang.reflect.Proxy.newProxyInstance(iface.getClassLoader(),
                    new Class<?>[] {iface}, new U4Probe(original));
            System.err.println("[U4-TERMUX] controller proxy installed delegate=" + original.getClass().getName());
            return proxy;
        } catch (Throwable e) {
            System.err.println("[U4-PROBE-ERROR] controller " + e);
            return original;
        }
    }

    @Override public Object invoke(Object proxy, java.lang.reflect.Method method, Object[] args) throws Throwable {
        if ("finishActivity".equals(method.getName()) && args != null && args.length == 4)
            finish(args[0], ((Integer)args[1]).intValue(), args[2], ((Integer)args[3]).intValue());
        try { return method.invoke(delegate, args); }
        catch (java.lang.reflect.InvocationTargetException e) { throw e.getCause(); }
    }
}
