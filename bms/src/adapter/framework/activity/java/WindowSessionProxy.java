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
            if (current == null) return;                     // nothing to wrap yet
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
        Object result = method.invoke(delegate, args);
        try {
            if (name.startsWith("addToDisplay")) {
                result = retryAddOnInvalidType(method, args, result);
            } else if ("relayout".equals(name)) {
                clampRelayout(args);
            }
        } catch (Throwable t) {
            System.err.println("[B8-WSP] " + name + " post-process skipped: " + t);
        }
        return result;
    }

    /** On ADD_INVALID_TYPE, mask the LayoutParams flags to the supported set and retry once. */
    private Object retryAddOnInvalidType(Method method, Object[] args, Object result) throws Throwable {
        if (!(result instanceof Integer) || (Integer) result != ADD_INVALID_TYPE) return result;
        android.view.WindowManager.LayoutParams attrs = findAttrs(args);
        if (attrs == null) return result;
        int original = attrs.flags;
        int masked = original & SUPPORTED_LAYOUT_FLAGS;
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

    /** Clamp a degenerate (<=1px) relayout frame in the WindowRelayoutResult out-parameter. */
    private void clampRelayout(Object[] args) throws Exception {
        if (args == null) return;
        for (Object a : args) {
            if (a == null) continue;
            if ("android.window.WindowRelayoutResult".equals(a.getClass().getName())) {
                Object frames = readField(a, "frames");
                if (frames != null) clampFramesObject(frames);
                return;
            }
            if ("android.window.ClientWindowFrames".equals(a.getClass().getName())) {
                clampFramesObject(a);
                return;
            }
        }
    }

    private void clampFramesObject(Object frames) throws Exception {
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
}
