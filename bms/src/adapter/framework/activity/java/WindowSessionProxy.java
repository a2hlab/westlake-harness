package adapter.activity;

import android.os.IBinder;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * B8 (#82/r15): a runtime-JAR proxy over WindowManagerGlobal.sWindowSession (the BCP
 * WindowSessionAdapter, an IWindowSession.Stub). Two BCP behaviours are fixed here without a
 * boot-image rebuild, using the same java.lang.reflect.Proxy pattern proven by
 * PackageManagerProjectionProxy:
 *
 *  - addToDisplay* (INVENTORY/#82 4, aegis): the BCP adapter fail-closes on LayoutParams flags
 *    outside its allow-list and returns ADD_INVALID_TYPE (-10), surfacing as
 *    "InvalidDisplayException: the specified window type N is not valid". When that happens we retry
 *    once with the flags masked to the supported set (the unsupported flags become no-ops).
 *  - relayout (CLAMP48 / Layout-79): OH can report a torn-down 1px window rect that is reverse-pushed
 *    into the app-global Configuration and persists; a later StaticLayout width goes negative and the
 *    app _exit(1)s. After the delegate returns we clamp the WindowRelayoutResult frame width/height
 *    (and the merged Configuration bounds) to the last healthy size, else the display max bounds.
 *
 * The proxy delegates EVERY other method (and asBinder) unchanged, and any failure inside the two
 * intercepts falls through to the delegate's own result -- a window is never lost to this class.
 */
public final class WindowSessionProxy implements InvocationHandler {
    private static final int ADD_INVALID_TYPE = -10;   // WindowManagerGlobal.ADD_INVALID_TYPE

    // The LayoutParams flags the BCP WindowSessionAdapter accepts (from its SUPPORTED_LAYOUT_FLAGS).
    private static final int SUPPORTED_LAYOUT_FLAGS =
            android.view.WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED
            | android.view.WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
            | android.view.WindowManager.LayoutParams.FLAG_LAYOUT_INSET_DECOR
            | android.view.WindowManager.LayoutParams.FLAG_SPLIT_TOUCH
            | android.view.WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS
            | android.view.WindowManager.LayoutParams.FLAG_FULLSCREEN
            | android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
            | android.view.WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
            | android.view.WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
            | android.view.WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD;

    private static volatile int sLastGoodWidth = 0;
    private static volatile int sLastGoodHeight = 0;

    private final Object delegate;   // the real IWindowSession (WindowSessionAdapter)

    private WindowSessionProxy(Object delegate) {
        this.delegate = delegate;
    }

    /** Wrap WindowManagerGlobal.sWindowSession with this proxy, once, at bind time. */
    public static void install() {
        try {
            Class<?> iface = Class.forName("android.view.IWindowSession");
            Class<?> global = Class.forName("android.view.WindowManagerGlobal");
            java.lang.reflect.Field field = global.getDeclaredField("sWindowSession");
            field.setAccessible(true);
            Object current = field.get(null);
            if (current == null) {
                // sWindowSession is lazily created on the first getWindowSession() (first window
                // add). Force it now so we can wrap it before that add; getWindowSession() caches
                // into sWindowSession, so the later add returns our proxy.
                try { current = global.getMethod("getWindowSession").invoke(null); } catch (Throwable ignore) {}
                if (current == null) current = field.get(null);
            }
            if (current == null) {
                System.err.println("[B8-WSP] sWindowSession still null; cannot wrap");
                return;
            }
            if (Proxy.isProxyClass(current.getClass())
                    && Proxy.getInvocationHandler(current) instanceof WindowSessionProxy) {
                return;                                      // already installed
            }
            Object proxy = Proxy.newProxyInstance(iface.getClassLoader(), new Class<?>[] {iface},
                    new WindowSessionProxy(current));
            field.set(null, proxy);
            System.err.println("[B8-WSP] IWindowSession proxy installed over " + current.getClass().getName());
        } catch (Throwable t) {
            System.err.println("[B8-WSP] not installed: " + t);
        }
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        String name = method.getName();
        if ("asBinder".equals(name)) {
            return ((android.os.IInterface) delegate).asBinder();
        }
        // r17p (EGL): the BCP WindowSessionAdapter.relayout reverse-pushes IWindow.resized whenever the
        // window size "changed" (app requestedWH=0x0 vs useWH=real). ViewRootImpl already has that size
        // from the relayout RETURN, so the push is redundant and re-traverses -> HWUI rebuilds the EGL
        // surface: repeated pushes -> BAD_ALLOC (wikipedia/newpipe/noice/antennapod), a single firstCreate
        // push -> SURFACE_CHANGED churn -> dropped first frame / white (fd-AppManager/tusky/k9). We cannot
        // change the delegate's method body (BCP, in oh-adapter-framework.jar), but the delegate calls
        // resized() on the IWindow we pass IN to relayout -- so wrap it and DROP those resized() calls.
        // The genuine 0x0 death-spiral recovery is still provided below by reversePushOnce, which targets
        // the REAL (unwrapped) window, so ZigZag/termux keep their one bootstrap push.
        Object realWindow = "relayout".equals(name) ? wrapRelayoutWindow(args) : null;
        Object result = method.invoke(delegate, args);
        try {
            if (name.startsWith("addToDisplay")) {
                result = retryAddOnInvalidType(method, args, result);
            } else if ("relayout".equals(name)) {
                // Only reverse-push when the frame WAS degenerate (the 0x0 death spiral). A window that
                // already relayouts to a real size (ZigZag) must not be disturbed by an extra
                // IWindow.resized -- doing so on every window regressed ZigZag to a white screen (r17h).
                boolean degenerate = clampRelayout(args);
                if (degenerate && realWindow != null) reversePushOnce(realWindow);
            }
        } catch (Throwable t) {
            System.err.println("[B8-WSP] " + name + " post-process skipped: " + t);
        }
        return result;
    }

    // r17r (markor): the board delegate 5bfa99ba (an older WindowSessionAdapter) fail-closes on the
    // power/lock-screen flags -- newer adapters translate them, this one returns ADD_INVALID_TYPE.
    // Our SUPPORTED_LAYOUT_FLAGS constant's *runtime* value on this generation is a superset that
    // already contains these bits (0x81e90580 includes FLAG_KEEP_SCREEN_ON 0x80), so masking with it
    // alone leaves 0x80 in and masked==original -> the retry never fired and markor died with
    // InvalidDisplayException("window type 1 is not valid"). Strip them so the retry actually removes
    // what the delegate refuses. They are cosmetic (keep-screen-on / show-when-locked).
    // Device-standard literal bit values (NOT the android.jar constants: this generation's compile
    // android.jar bakes quirky flag values -- SUPPORTED_LAYOUT_FLAGS' runtime value 0x81e90580 already
    // carries these bits -- so the named constants cannot be trusted to strip the on-device 0x80).
    private static final int POWER_LOCK_FLAGS =
            0x00000080   // FLAG_KEEP_SCREEN_ON  (the flag the board delegate logs as unsupported)
            | 0x00080000 // FLAG_SHOW_WHEN_LOCKED
            | 0x00200000 // FLAG_TURN_SCREEN_ON
            | 0x00400000; // FLAG_DISMISS_KEYGUARD

    /** On ADD_INVALID_TYPE, mask the LayoutParams flags to the supported set and retry once. */
    private Object retryAddOnInvalidType(Method method, Object[] args, Object result) throws Throwable {
        if (!(result instanceof Integer) || (Integer) result != ADD_INVALID_TYPE) return result;
        android.view.WindowManager.LayoutParams attrs = findAttrs(args);
        if (attrs == null) return result;
        int original = attrs.flags;
        int masked = original & SUPPORTED_LAYOUT_FLAGS & ~POWER_LOCK_FLAGS;
        if (masked == original) return result;               // flags were not the problem
        attrs.flags = masked;
        Object retry = method.invoke(delegate, args);
        System.err.println("[B8-WSP] addToDisplay flags 0x" + Integer.toHexString(original)
                + " -> 0x" + Integer.toHexString(masked) + " retry=" + retry);
        return retry;
    }

    private static android.view.WindowManager.LayoutParams findAttrs(Object[] args) {
        if (args == null) return null;
        for (Object a : args) {
            if (a instanceof android.view.WindowManager.LayoutParams) {
                return (android.view.WindowManager.LayoutParams) a;
            }
        }
        return null;
    }

    /** Clamp a degenerate (<=1px) relayout frame; returns true when a frame WAS degenerate. */
    private boolean clampRelayout(Object[] args) throws Exception {
        if (args == null) return false;
        for (Object a : args) {
            if (a == null) continue;
            if ("android.window.WindowRelayoutResult".equals(a.getClass().getName())) {
                Object frames = readField(a, "frames");
                return frames != null && clampFramesObject(frames);
            }
            if ("android.window.ClientWindowFrames".equals(a.getClass().getName())) {
                return clampFramesObject(a);
            }
        }
        return false;
    }

    private boolean clampFramesObject(Object frames) throws Exception {
        boolean any = false;
        for (String fieldName : new String[] {"frame", "displayFrame", "parentFrame"}) {
            Object rectObj = readField(frames, fieldName);
            if (rectObj instanceof android.graphics.Rect) {
                any |= clampRect((android.graphics.Rect) rectObj);
            }
        }
        if (any) {
            System.err.println("[B8-WSP] CLAMP48 degenerate relayout frame clamped to "
                    + sLastGoodWidth + "x" + sLastGoodHeight);
        }
        return any;
    }

    /** Record the healthy size; substitute the last-good / display max bounds when an axis is <=1. */
    private boolean clampRect(android.graphics.Rect r) {
        int w = r.width(), h = r.height();
        if (w > 1 && h > 1) {
            sLastGoodWidth = w;
            sLastGoodHeight = h;
            return false;
        }
        int newW = w, newH = h;
        if (w <= 1 && sLastGoodWidth > 1) newW = sLastGoodWidth;
        if (h <= 1 && sLastGoodHeight > 1) newH = sLastGoodHeight;
        if (newW <= 1 || newH <= 1) {
            android.graphics.Rect max = maxBounds();   // Configuration.windowConfiguration is @hide
            if (max != null) {
                if (newW <= 1 && max.width() > 1) newW = max.width();
                if (newH <= 1 && max.height() > 1) newH = max.height();
            }
        }
        if (newW == w && newH == h) return false;
        r.right = r.left + newW;
        r.bottom = r.top + newH;
        return true;
    }

    /** Resources.getSystem().getConfiguration().windowConfiguration.getMaxBounds() via reflection
     *  (both the field and getMaxBounds are @hide, absent from the compile android.jar). */
    private static android.graphics.Rect maxBounds() {
        try {
            android.content.res.Configuration cfg = android.content.res.Resources.getSystem().getConfiguration();
            Object wc = cfg.getClass().getField("windowConfiguration").get(cfg);
            if (wc == null) return null;
            Object rect = wc.getClass().getMethod("getMaxBounds").invoke(wc);
            return rect instanceof android.graphics.Rect ? (android.graphics.Rect) rect : null;
        } catch (Throwable t) {
            return null;
        }
    }

    private static Object readField(Object obj, String fieldName) {
        try {
            java.lang.reflect.Field f = obj.getClass().getField(fieldName);
            return f.get(obj);
        } catch (Throwable t) {
            return null;
        }
    }

    // ---- r17p (EGL): wrap the IWindow so the delegate's redundant resized() reverse-push is dropped --
    // Keyed by the real IWindow's binder so one wrapper serves every relayout on that window and its
    // asBinder() stays stable for the delegate's mSessionMap lookups.
    private final java.util.Map<android.os.IBinder, Object> sWrappers =
            java.util.Collections.synchronizedMap(new java.util.WeakHashMap<android.os.IBinder, Object>());

    /** For a relayout call, replace its IWindow arg with a wrapper that drops the delegate's resized()
     *  reverse-push. Returns the REAL window (so the caller reverse-pushes it directly) or null. */
    private Object wrapRelayoutWindow(Object[] args) {
        try {
            if (args == null) return null;
            Class<?> iWindow = Class.forName("android.view.IWindow");
            for (int i = 0; i < args.length; i++) {
                Object a = args[i];
                if (a == null || !iWindow.isInstance(a)) continue;
                if (Proxy.isProxyClass(a.getClass())
                        && Proxy.getInvocationHandler(a) instanceof DropResizedHandler) {
                    return ((DropResizedHandler) Proxy.getInvocationHandler(a)).real;   // already wrapped
                }
                android.os.IBinder key = ((android.os.IInterface) a).asBinder();
                Object wrapper = sWrappers.get(key);
                if (wrapper == null) {
                    wrapper = Proxy.newProxyInstance(iWindow.getClassLoader(),
                            new Class<?>[] {iWindow}, new DropResizedHandler(a));
                    sWrappers.put(key, wrapper);
                }
                args[i] = wrapper;
                return a;
            }
        } catch (Throwable t) {
            System.err.println("[B8-WSP] wrap relayout window skipped: " + t);
        }
        return null;
    }

    /** Forwards every IWindow call to the real window except resized(), which is dropped -- that is the
     *  delegate's redundant size-changed reverse-push that rebuilds the EGL surface. */
    private static final class DropResizedHandler implements InvocationHandler {
        final Object real;
        DropResizedHandler(Object real) { this.real = real; }
        @Override public Object invoke(Object proxy, Method m, Object[] a) throws Throwable {
            if ("resized".equals(m.getName())) {
                System.err.println("[B8-WSP] delegate IWindow.resized dropped (redundant size-changed reverse-push)");
                Class<?> rt = m.getReturnType();
                if (rt == boolean.class) return Boolean.FALSE;
                if (rt == int.class) return Integer.valueOf(0);
                if (rt == long.class) return Long.valueOf(0L);
                return null;                                   // void / object returns
            }
            try {
                return m.invoke(real, a);
            } catch (java.lang.reflect.InvocationTargetException e) {
                throw e.getCause() != null ? e.getCause() : e;
            }
        }
    }

    // ---- G2.14as r4: reverse-push IWindow.resized once per window --------------------------------
    // OH's server never calls IWindow.resized, so ViewRootImpl in LOCAL_LAYOUT mode measures 0x0 ->
    // relayout frame (0,0,0,0) -> measures 0 again (death spiral) and the first frame is never
    // committed (termux TermuxActivity, fd-mobile: alive, mWindowAdded, but blank/black). After each
    // relayout we reverse-push the real display frame exactly once so ViewRootImpl.handleResized ->
    // setFrame breaks the spiral. Copied from Westlake WindowSessionAdapter L1044-1060.
    private static final java.util.Set<android.os.IBinder> sReversePushed =
            java.util.Collections.synchronizedSet(new java.util.HashSet<android.os.IBinder>());

    private void reversePushOnce(Object window) {
        try {
            if (window == null) return;
            Class<?> iWindow = Class.forName("android.view.IWindow");
            android.os.IBinder key = ((android.os.IInterface) window).asBinder();
            if (!sReversePushed.add(key)) return;                 // once per window
            android.graphics.Rect max = maxBounds();
            int width = max != null && max.width() > 1 ? max.width()
                    : (sLastGoodWidth > 1 ? sLastGoodWidth : 1080);
            int height = max != null && max.height() > 1 ? max.height()
                    : (sLastGoodHeight > 1 ? sLastGoodHeight : 1920);
            Object frames = buildClientWindowFrames(width, height);
            if (frames == null) { sReversePushed.remove(key); return; }
            Object cfg = Class.forName("android.util.MergedConfiguration").getDeclaredConstructor().newInstance();
            Object insets = Class.forName("android.view.InsetsState").getDeclaredConstructor().newInstance();
            Method resized = findResized(iWindow);
            if (resized == null) { sReversePushed.remove(key); return; }
            resized.setAccessible(true);
            Object[] ra = buildResizedArgs(resized.getParameterTypes(), frames, cfg, insets);
            resized.invoke(window, ra);
            System.err.println("[B8-WSP] reverse-pushed IWindow.resized (once): " + width + "x" + height);
        } catch (Throwable t) {
            System.err.println("[B8-WSP] reverse-push skipped: " + t);
        }
    }

    /** ClientWindowFrames with frame/displayFrame/parentFrame/attachedFrame = (0,0,width,height). */
    private static Object buildClientWindowFrames(int width, int height) {
        try {
            Object frames = Class.forName("android.window.ClientWindowFrames")
                    .getDeclaredConstructor().newInstance();
            android.graphics.Rect r = new android.graphics.Rect(0, 0, width, height);
            for (String f : new String[] {"frame", "displayFrame", "parentFrame"}) {
                Object rectObj = readField(frames, f);
                if (rectObj instanceof android.graphics.Rect) ((android.graphics.Rect) rectObj).set(r);
            }
            try {
                java.lang.reflect.Field af = frames.getClass().getField("attachedFrame");
                af.set(frames, new android.graphics.Rect(r));
            } catch (Throwable ignore) {
            }
            return frames;
        } catch (Throwable t) {
            return null;
        }
    }

    /** The IWindow.resized overload whose first parameter is ClientWindowFrames (the modern one). */
    private static Method findResized(Class<?> iWindow) {
        Method best = null;
        for (Method m : iWindow.getMethods()) {
            if (!"resized".equals(m.getName())) continue;
            Class<?>[] p = m.getParameterTypes();
            if (p.length > 0 && "android.window.ClientWindowFrames".equals(p[0].getName())) return m;
            if (best == null || p.length > best.getParameterTypes().length) best = m;
        }
        return best;
    }

    /** Fill resized() args: frames/cfg/insets by type, ints 0, forceLayout (2nd boolean) true else
     *  false, everything else null -- matches Westlake's resized(frames,false,cfg,insets,true,...). */
    private static Object[] buildResizedArgs(Class<?>[] pt, Object frames, Object cfg, Object insets) {
        Object[] a = new Object[pt.length];
        int boolIdx = 0;
        for (int i = 0; i < pt.length; i++) {
            Class<?> t = pt[i];
            String n = t.getName();
            if ("android.window.ClientWindowFrames".equals(n)) a[i] = frames;
            else if ("android.util.MergedConfiguration".equals(n)) a[i] = cfg;
            else if ("android.view.InsetsState".equals(n)) a[i] = insets;
            else if (t == int.class) a[i] = Integer.valueOf(0);
            else if (t == boolean.class) { a[i] = Boolean.valueOf(boolIdx == 1); boolIdx++; }
            else a[i] = null;
        }
        return a;
    }
}
