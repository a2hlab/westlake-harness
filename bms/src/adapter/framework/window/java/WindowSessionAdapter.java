/*
 * WindowSessionAdapter.java
 *
 * Replaces IWindowSessionBridge (InvocationHandler pattern) with a direct
 * class inheritance approach extending IWindowSession.Stub.
 *
 * Routes Android IWindowSession calls to OpenHarmony ISession /
 * ISceneSessionManager system services via JNI.
 *
 * Methods are categorized as:
 *   [BRIDGED] - Mapped to OH equivalent via native call
 *   [STUB]    - No OH equivalent, returns safe default
 */
package adapter.window;

import adapter.window.InputEventBridge;

import android.content.ClipData;
import android.content.res.Configuration;
import android.graphics.Point;
import android.graphics.Rect;
import android.graphics.Region;
import android.os.Bundle;
import android.os.IBinder;
import android.os.RemoteCallback;
import android.os.RemoteException;
import android.util.Log;
import android.util.MergedConfiguration;
import android.view.DisplayCutout;
import android.view.InputChannel;
import android.view.IWindow;
import android.view.IWindowId;
import android.view.IWindowSession;
import android.view.MotionEvent;
import android.view.InsetsSourceControl;
import android.view.InsetsState;
import android.view.Surface;
import android.view.SurfaceControl;
import android.view.WindowManager;
import android.window.ClientWindowFrames;
import android.window.OnBackInvokedCallbackInfo;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Adapter that bridges Android's IWindowSession to OpenHarmony's
 * ISession + ISceneSessionManager.
 *
 * Extends IWindowSession.Stub directly instead of using an InvocationHandler
 * proxy, providing compile-time safety for all 42 AIDL methods.
 */
public class WindowSessionAdapter extends IWindowSession.Stub {

    private static final String TAG = "OH_WSAdapter";
    private static volatile WindowSessionAdapter sInstance;

    public static WindowSessionAdapter getInstance() {
        if (sInstance == null) {
            synchronized (WindowSessionAdapter.class) {
                if (sInstance == null) {
                    sInstance = new WindowSessionAdapter();
                }
            }
        }
        return sInstance;
    }

    // §3.1.4.1 / E02 — Curated allowlist of LayoutParams flags that the
    // bridge carries through to nativeCreateSession.  The list is derived from
    // AOSP PhoneWindow.generateLayout() (frameworks/base/core/java/com/
    // android/internal/policy/PhoneWindow.java:2423-2548), which sets these
    // flags for ordinary Activities either by default or via common themes.
    // FLAG_FULLSCREEN and the power/lock-screen flags below are translated to
    // real OH WindowProperty state in oh_window_manager_client.cpp.  Only the
    // layout/rendering bits without a distinct legacy WindowProperty field are
    // accepted as audited no-ops.
    // Every flag outside this list must be explicitly mapped to OH or rejected
    // fail-closed; silently dropping flags violates the design contract.
    private static final int SUPPORTED_LAYOUT_FLAGS =
            WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED
            | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
            | WindowManager.LayoutParams.FLAG_LAYOUT_INSET_DECOR
            | WindowManager.LayoutParams.FLAG_SPLIT_TOUCH
            | WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS
            | WindowManager.LayoutParams.FLAG_FULLSCREEN
            // These four public LayoutParams bits carry keep-awake,
            // lock-screen visibility, wake, and keyguard intent.  The native
            // boundary maps them to OH WindowProperty state; they are not
            // accepted as no-ops.
            | WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
            | WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
            | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
            | WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD;
    // NOTE: FLAG_SHOW_WALLPAPER is intentionally excluded.  PhoneWindow sets
    // it for Theme.Wallpaper, but the OH creation path currently does not
    // request wallpaper-behind composition or wallpaper touch forwarding, so
    // allowing it would silently discard behavior.  Keep it fail-closed until
    // a real mapping is implemented and device-verified.

    private final long mOhSession;

    // Track OH sessions created by this adapter, keyed by IWindow IBinder
    private final Map<IBinder, int[]> mSessionMap = new HashMap<>();

    // 2026-05-25 (a) fix — per-session persistent SurfaceControl, mirroring AOSP
    // WMS WindowStateAnimator.mSurfaceController (createSurfaceLocked() reuses it;
    // relayoutWindow copies it into outSurfaceControl on every call).  Returning
    // the SAME SurfaceControl handle across relayouts makes ViewRootImpl's
    // BLASTBufferQueue.isSameSurfaceControl() == true → BBQ.update() instead of
    // destroy+recreate → the hwui RenderThread keeps one EGLSurface and does NOT
    // re-run eglCreateWindowSurface on an already-bound window (the same-process
    // SecondActivity 2nd-window abort).  Keyed by OH sessionId.
    private final Map<Integer, SurfaceControl> mSurfaceControlMap = new HashMap<>();

    // 2026-06-01 (BBQ-null crash fix): per-session last viewVisibility passed to
    // relayout.  When a window goes non-VISIBLE (minimize → Activity onStop →
    // GONE), ViewRootImpl runs renderer.pause()+destroySurface() → mBlastBufferQueue
    // = null.  On the hidden→VISIBLE restore the persistent SurfaceControl makes
    // relayout look "unchanged", so ViewRootImpl neither pauses the RenderThread
    // (to drain in-flight frames) nor re-runs the full surface setup — an in-flight
    // RT frame's onFrameDraw then calls applyPendingTransactions() on the null BBQ
    // (ViewRootImpl.java:4601) → JNI NPE abort after a few minimize/restore cycles.
    // Reporting RELAYOUT_RES_SURFACE_CHANGED on the non-VISIBLE→VISIBLE edge makes
    // ViewRootImpl pause+drain the RT and recreate the BBQ (steady-state VISIBLE→
    // VISIBLE relayouts still do NOT set it, avoiding the 2026-05-25 churn abort).
    private final Map<Integer, Integer> mLastViewVis = new HashMap<>();

    // 2026-05-26 Layer-1 fix — per-session last reverse-pushed window size,
    // packed as ((long)w << 32) | (h & 0xffffffffL).  The IWindow.resized
    // reverse-push now fires ONLY when this size actually changes, mirroring
    // AOSP WMS (which calls IWindow.resized only on a real server-side frame
    // change, never every relayout).  Pushing every relayout with
    // forceLayout=true perpetually re-armed ViewRootImpl.mForceNextWindowRelayout
    // → requestLayout → relayout → push → infinite relayout oscillation.
    private final Map<Integer, Long> mLastPushedSize = new HashMap<>();

    // 2026-06-01 issue-1 (flicker): sessionId -> owning activity token, recorded
    // when the window relayouts VISIBLE (its owner is then foreground; attrs.token
    // is null in the relayout path).  Used to decide covered (keep) vs minimized
    // (remove) when the window later hides.
    private final Map<Integer, IBinder> mSessionOwner =
            new java.util.concurrent.ConcurrentHashMap<>();

    // 2026-06-02 deterministic show-before-hide.  Sessions whose RemoveWindow was
    // DEFERRED because they were covered by a newer foreground sibling (a window
    // relayouts GONE before the covering window's relayout VISIBLE arrives).  The
    // deferred removal is flushed (RemoveWindow) when ANY window is next shown
    // (the coverer is then composited on top -> no launcher gap), so a covered
    // window is removed promptly instead of lingering to be revealed on
    // home/back-to-desktop.  Event-driven (no timer) -> no race.
    private final java.util.Set<Integer> mDeferredHide =
            java.util.concurrent.ConcurrentHashMap.newKeySet();

    /** Flush deferred hides — RemoveWindow each covered window now that a coverer is up. */
    private void flushDeferredHides() {
        if (mDeferredHide.isEmpty()) return;
        for (Integer sid : new java.util.ArrayList<>(mDeferredHide)) {
            mDeferredHide.remove(sid);
            int rc = nativeHideWindow(sid);
            System.err.println("[OH_WSA-relayout] flush deferred hide session=" + sid + " rc=" + rc);
        }
    }

    private static native long nativeGetOHSessionService();
    /**
     * Spec: doc/window_manager_ipc_adapter_design.html §3.1.5.2 / §3.1.5.6.1
     * - bundleName/abilityName/moduleName: SCB decoration / theme routing (§3.1.4.2)
     * - ohTokenAddr: OH AbilityRecord token raw pointer; lookup via
     *   AppSchedulerBridge.OhTokenRegistry.findOhToken(attrs.token).
     *   Native side reinterpret_cast → sptr<IRemoteObject> → CreateAndConnect
     *   with property->SetTokenState(true). Pre-fix value 0 meant "no token";
     *   non-zero closes the §3.1.4.6.3 流转断点.
     * Returns int[10]: {sessionId, surfaceNodeId, displayId, w, h, wsErrCode,
     *                  frameLeft, frameTop, frameRight, frameBottom}.
     *   wsErrCode = 0 on success, OH WSError integer on failure (§3.1.5.6.2).
     *   frame* = actual OH window rect after AddWindow; may be int[6] for legacy
     *   BCP jars, in which case frame falls back to w/h.
     */
    private static native int[] nativeCreateSession(Object androidWindow,
            String bundleName, String abilityName, String moduleName,
            String windowName,
            int androidWindowType, int displayId,
            int requestedWidth, int requestedHeight,
            int androidFlags,
            long ohTokenAddr);
    private static native int nativeUpdateSessionRect(int sessionId,
            int x, int y, int width, int height);
    private static native int nativeNotifyDrawingCompleted(int sessionId);
    private static native void nativeDestroySession(int sessionId);
    // 2026-05-19: visibility transition helpers — counterpart to AddWindow at
    // session creation.  Called from relayout based on viewVisibility arg.
    // See oh_window_manager_client.cpp::hideWindow / showWindow for design
    // notes (in-App-process C++ cache, idempotent at native layer).
    private static native int nativeHideWindow(int sessionId);
    private static native int nativeShowWindow(int sessionId);
    private static native long nativeGetSurfaceNodeId(int sessionId);
    private static native int nativeInjectTouchEvent(int sessionId, int action,
            float x, float y, long downTime, long eventTime);

    // Surface bridge native methods
    private static native boolean nativeCreateOHSurface(int sessionId, String windowName,
            int width, int height, int format);
    private static native long nativeGetSurfaceHandle(int sessionId,
            int width, int height, int format);
    private static native void nativeNotifySurfaceDrawingCompleted(int sessionId);
    private static native void nativeUpdateSurfaceSize(int sessionId, int width, int height);
    private static native void nativeDestroyOHSurface(int sessionId);
    private static native int[] nativeDequeueBuffer(long producerHandle,
            int width, int height, int format, long usage);
    private static native int nativeQueueBuffer(long producerHandle, int slot, int fenceFd,
            long timestamp, int cropLeft, int cropTop, int cropRight, int cropBottom);
    private static native int nativeCancelBuffer(long producerHandle, int slot, int fenceFd);

    /**
     * Creates a new WindowSessionAdapter.
     */
    public WindowSessionAdapter() {
        mOhSession = nativeGetOHSessionService();
        Log.i(TAG, "WindowSessionAdapter created, ohSession=0x" + Long.toHexString(mOhSession));
    }

    // §3.1.5.6.3 — Android attrs.type → "is this the main DecorView?" predicate.
    // Reuse path applies only to main windows; sub windows / system overlays
    // legitimately need their own SceneSession.
    private static boolean isMainAppWindow(int androidWindowType) {
        // TYPE_BASE_APPLICATION=1 / TYPE_APPLICATION=2 / TYPE_APPLICATION_STARTING=3
        return androidWindowType >= 1 && androidWindowType <= 3;
    }

    // §3.1.5.6.2 — OH WSError to AOSP ADD_* code. Real WSError enum values
    // (from foundation/window/window_manager/window_scene/interfaces/include/ws_common.h):
    //   0  = WS_OK
    //   1  = WS_DO_NOTHING
    //   2..18 = various invalid/permission codes
    //   8  = WS_ERROR_NOT_SYSTEM_APP
    //   1000 = WS_ERROR_NEED_REPORT_BASE
    //   1001 = WS_ERROR_NULLPTR
    //   1002 = WS_ERROR_INVALID_TYPE
    //   1003 = WS_ERROR_INVALID_PARAM
    //   1004 = WS_ERROR_SAMGR
    //   1005 = WS_ERROR_IPC_FAILED   ← G2.14 currently observed, comes from
    //                                  early-exit when ssmProxy_==nullptr (3-hop
    //                                  chain blocked by foundation-side IMockSession
    //                                  systemic IPC issue)
    private static int mapWsErrorToAddCode(int wsErr) {
        // Precondition: this helper is only called when nativeCreateSession has
        // already signalled failure. A wsErr of 0 with an invalid session receipt
        // must stay fail-closed; the success path checks wsErr == 0 and a valid
        // sessionId before reaching this method.
        switch (wsErr) {
            case 7:    // WM_ERROR_INVALID_PERMISSION / WS_ERROR_INVALID_PERMISSION
                return android.view.WindowManagerGlobal.ADD_PERMISSION_DENIED;      // -8
            case 8:    // WM_ERROR_NOT_SYSTEM_APP / WS_ERROR_NOT_SYSTEM_APP
                return android.view.WindowManagerGlobal.ADD_PERMISSION_DENIED;      // -8
            case 10:   // WM_ERROR_INVALID_DISPLAY / WS_ERROR_INVALID_DISPLAY
                return android.view.WindowManagerGlobal.ADD_INVALID_DISPLAY;        // -9
            case 11:   // WM_ERROR_INVALID_PARENT / WS_ERROR_INVALID_PARENT
                return android.view.WindowManagerGlobal.ADD_BAD_SUBWINDOW_TOKEN;    // -2
            case 13:   // WM_ERROR_REPEAT_OPERATION
                return android.view.WindowManagerGlobal.ADD_DUPLICATE_ADD;          // -5
            case 14:   // WM_ERROR_INVALID_SESSION — session lifecycle mismatch
                return android.view.WindowManagerGlobal.ADD_INVALID_DISPLAY;        // -9 (no closer AOSP constant)
            case 15:   // WM_ERROR_INVALID_CALLING — caller/sa context mismatch
                return android.view.WindowManagerGlobal.ADD_INVALID_DISPLAY;        // -9 (no closer AOSP constant)
            case 1002: // WS_ERROR_INVALID_TYPE — bad windowType param
                return android.view.WindowManagerGlobal.ADD_INVALID_TYPE;           // -10
            case 1003: // WS_ERROR_INVALID_PARAM — real "bad token / bad window" cause
                return android.view.WindowManagerGlobal.ADD_BAD_APP_TOKEN;          // -1
            case 0:    // Defensive: caller should never pass this, but if it does,
            case 12:   // WM_ERROR_INVALID_OP_IN_CUR_STATUS
            case 1001: // WS_ERROR_NULLPTR
            case 1004: // WS_ERROR_SAMGR
            case 1005: // WS_ERROR_IPC_FAILED
            default:
                // There is no Android ADD_INVALID_OPERATION constant; the closest
                // Android-compatible failure that is not a fake pass is the IPC
                // layer default used by the legacy adapter.
                return android.view.WindowManagerGlobal.ADD_INVALID_DISPLAY;        // -9
        }
    }

    /**
     * §3.1.4.1 / E02 — fail-closed check for LayoutParams flags.
     * Returns the unsupported flag bits, or 0 if all set flags are known.
     */
    private static int unsupportedLayoutParamsFlags(WindowManager.LayoutParams attrs) {
        if (attrs == null) return 0;
        return attrs.flags & ~SUPPORTED_LAYOUT_FLAGS;
    }

    // §3.1.4.2 — best-effort lookup of the App's bundleName.
    // ActivityThread.currentPackageName() may return null very early (before
    // handleBindApplication completes); fall back to "android" so the SSM
    // call still has a non-null bundleName for SCB routing.
    private static String currentPackageName() {
        try {
            Class<?> c = Class.forName("android.app.ActivityThread");
            String name = (String) c.getMethod("currentPackageName").invoke(null);
            if (name != null && !name.isEmpty()) return name;
        } catch (Throwable ignored) {}
        return "android";
    }

    // §3.1.4.2 — best-effort lookup of the current Activity's simple name.
    // We don't have a stable ActivityThread API for this, so we walk the
    // top-of-stack record reflectively. Falls back to "MainAbility" so
    // native side fallback kicks in identically.
    private static String currentActivityName() {
        try {
            Class<?> at = Class.forName("android.app.ActivityThread");
            Object instance = at.getMethod("currentActivityThread").invoke(null);
            if (instance == null) return "MainAbility";
            java.lang.reflect.Field f = at.getDeclaredField("mActivities");
            f.setAccessible(true);
            Object map = f.get(instance);
            if (map instanceof java.util.Map) {
                @SuppressWarnings("unchecked")
                java.util.Map<Object, Object> m = (java.util.Map<Object, Object>) map;
                for (Object record : m.values()) {
                    if (record == null) continue;
                    java.lang.reflect.Field af = record.getClass().getDeclaredField("activity");
                    af.setAccessible(true);
                    Object activity = af.get(record);
                    if (activity != null) {
                        String full = activity.getClass().getName();
                        int dot = full.lastIndexOf('.');
                        return (dot >= 0 && dot + 1 < full.length()) ? full.substring(dot + 1) : full;
                    }
                }
            }
        } catch (Throwable ignored) {}
        return "MainAbility";
    }

    // ====================================================================
    // Category 1: Window Lifecycle
    // ====================================================================

    /**
     * [BRIDGED] addToDisplay -> OH ISceneSessionManager.CreateAndConnectSpecificSession
     */
    @Override
    public int addToDisplay(IWindow window, WindowManager.LayoutParams attrs,
            int viewVisibility, int layerStackId, int requestedVisibleTypes,
            InputChannel outInputChannel, InsetsState insetsState,
            InsetsSourceControl.Array activeControls, Rect attachedFrame,
            float[] sizeCompatScale) throws RemoteException {
        System.err.println("[OH_WSA] ENTRY addToDisplay attrs.type=" + attrs.type
                + " attrs.token=" + attrs.token + " w=" + attrs.width + " h=" + attrs.height
                + " flags=0x" + Integer.toHexString(attrs.flags)
                + " (HW_ACCEL=" + ((attrs.flags
                        & WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED) != 0)
                + ")");

        // §3.1.4.1 / E02 — fail-closed on unsupported LayoutParams flags.
        int unsupportedFlags = unsupportedLayoutParamsFlags(attrs);
        if (unsupportedFlags != 0) {
            Log.e(TAG, "addToDisplay: unsupported LayoutParams flags=0x"
                    + Integer.toHexString(unsupportedFlags)
                    + "; returning ADD_INVALID_TYPE");
            return android.view.WindowManagerGlobal.ADD_INVALID_TYPE;
        }

        logBridged("addToDisplay", "-> OH ISceneSessionManager.CreateAndConnectSpecificSession");

        String windowName = attrs.getTitle() != null ? attrs.getTitle().toString() : "AndroidWindow";
        int windowType = attrs.type;
        // 2026-05-11 G2.14ak — for MATCH_PARENT / FILL_PARENT (-1) / WRAP_CONTENT (-2)
        // attrs.width/height we must resolve to actual display pixels here, because
        // (a) AOSP IPC carries the raw flag (-1) — server side resolves;
        // (b) we are the binder server (extends IWindowSession.Stub) in this scope;
        // (c) OH IWindowManager::CreateWindow/AddWindow take rect IN only, no out param
        //     for resolved rect (verified via oh_window_manager_client.cpp + OH 7.0.0.18
        //     headers).  Source of truth = DisplayManagerGlobal → our OH_DisplayMgrAdapter
        //     → OH NativeDisplayManager, which returns DAYU200 native 720×1280.
        // Old code hardcoded 1080×2340 fallback (dayu210 residue); that propagated through
        // sessionInfo → relayout → SurfaceControl.setBufferSize → hwui drew at 1080×2340
        // coordinates → frame buffer mostly-white because content was outside 720×1280
        // composited region.
        int[] dispWH = getDefaultDisplaySize();
        int width = attrs.width > 0 ? attrs.width : dispWH[0];
        int height = attrs.height > 0 ? attrs.height : dispWH[1];

        // §3.1.4.2 — fetch real bundleName/abilityName from ActivityThread so
        // OH SCB routes window decoration / theme correctly. Native side
        // applies safe fallbacks ("entry" / "MainAbility") if any are blank.
        String bundleName  = currentPackageName();
        String abilityName = currentActivityName();
        String moduleName  = "entry";  // HAP default; P3: derive from APK manifest

        // §3.1.5.6.1 P1 — close the token 流转断点. attrs.token is the Activity's
        // adapter-side IBinder set by OhTokenRegistry on ScheduleLaunchAbility;
        // findOhToken reverses it to the OH AbilityRecord token raw pointer
        // which is what SCB CreateAndConnectSpecificSession expects in its
        // token IRemoteObject param. 0 = no token (P1 fallback).
        long ohTokenAddr = 0L;
        if (attrs.token != null) {
            Long addr = adapter.core.OhTokenRegistry.findOhToken(attrs.token);
            if (addr != null) ohTokenAddr = addr;
        }

        // §3.1.5.6.3 P2 — reuse OH SCB-auto-created main SceneSession when
        // available, instead of creating a duplicate via CreateAndConnect.
        // The capture happens in SessionStageAdapter (when SCB binds an
        // already-created main session to our stage) and writes into
        // OhTokenRegistry.setMainSessionId. If no captured session,
        // fall through to the normal CreateAndConnect path.
        // NOTE: capture wiring is currently API-only (registry surface is in
        // place) — concrete trigger awaits an OH-side mechanism to expose
        // the auto-created main session's persistentId to our SessionStage.
        // Until then, getMainSessionId returns -1 and we always go to create.
        if (isMainAppWindow(windowType) && attrs.token != null) {
            int existing = adapter.core.OhTokenRegistry.getMainSessionId(attrs.token);
            if (existing > 0) {
                Log.i(TAG, "addToDisplay: reusing existing OH main SceneSession id="
                        + existing + " (skipping CreateAndConnect)");
                int[] reuseInfo = new int[] { existing, -1, layerStackId, width, height, 0 };
                mSessionMap.put(window.asBinder(), reuseInfo);
                if (outInputChannel != null) {
                    InputChannel clientChannel = InputEventBridge.getInstance()
                            .createInputChannelPair(window.asBinder(), existing, windowName);
                    clientChannel.copyTo(outInputChannel);
                }
                if (insetsState != null) insetsState.set(new InsetsState());
                if (sizeCompatScale != null && sizeCompatScale.length > 0) sizeCompatScale[0] = 1.0f;
                return buildAddDisplayFlags(attrs);  // ADD_FLAG_APP_VISIBLE | IN_TOUCH_MODE
            }
        }

        System.err.println("[OH_WSA] PRE-native nativeCreateSession");
        int[] sessionInfo;
        try {
            sessionInfo = nativeCreateSession(window.asBinder(),
                    bundleName, abilityName, moduleName, windowName,
                    windowType, layerStackId, width, height,
                    attrs.flags,
                    ohTokenAddr);
            System.err.println("[OH_WSA] POST-native sessionInfo length=" + (sessionInfo == null ? -1 : sessionInfo.length));
        } catch (Throwable t) {
            System.err.println("[OH_WSA] nativeCreateSession threw " + t);
            t.printStackTrace(System.err);
            throw t;
        }

        // §3.1.5.6.2 — semantic error code mapping. nativeCreateSession returns
        // int[10]={sessionId, surfaceNodeId, displayId, w, h, wsErr,
        // frameLeft, frameTop, frameRight, frameBottom} — wsErr is the raw OH
        // WSError on failure. Legacy BCP jars may return int[6]; the frame
        // fallback below handles both. Map each error to the AOSP ADD_* code
        // that most closely reflects the cause; avoid the pre-fix blanket
        // ADD_BAD_APP_TOKEN which masquerades as a token problem.
        if (sessionInfo == null || sessionInfo.length < 6) {
            Log.e(TAG, "nativeCreateSession returned malformed array");
            return android.view.WindowManagerGlobal.ADD_INVALID_DISPLAY;  // -3, JNI fault
        }
        if (sessionInfo[0] < 0) {
            int wsErr = sessionInfo[5];
            int addCode = mapWsErrorToAddCode(wsErr);
            Log.e(TAG, "Failed to create OH session, wsErr=" + wsErr
                    + " -> addCode=" + addCode);
            return addCode;
        }

        // G2.14d — instrument with System.err so logs appear via [stderr]
        // tag (Log.i with TAG=OH_WSAdapter inexplicably hides post-construction
        // calls in this build's hilog; stderr always survives). Each step
        // identifies which line throws if ViewRootImpl post-add code or
        // adapter post-success code triggers preallocated NCDFE.
        System.err.println("[OH_WSA] step1 native returned sessionId=" + sessionInfo[0]
                + " surfaceNode=" + sessionInfo[1] + " size="
                + sessionInfo[3] + "x" + sessionInfo[4]);
        mSessionMap.put(window.asBinder(), sessionInfo);
        System.err.println("[OH_WSA] step2 mSessionMap.put OK");

        if (outInputChannel != null) {
            try {
                InputChannel clientChannel = InputEventBridge.getInstance()
                        .createInputChannelPair(window.asBinder(), sessionInfo[0], windowName);
                System.err.println("[OH_WSA] step3a createInputChannelPair OK");
                clientChannel.copyTo(outInputChannel);
                System.err.println("[OH_WSA] step3b InputChannel.copyTo OK");
            } catch (Throwable t) {
                System.err.println("[OH_WSA] step3 FAIL " + t);
                t.printStackTrace(System.err);
                throw t;
            }
        } else {
            System.err.println("[OH_WSA] step3 SKIP outInputChannel=null");
        }

        if (insetsState != null) {
            try {
                insetsState.set(new InsetsState());
                System.err.println("[OH_WSA] step4 insetsState.set(new InsetsState) OK");
            } catch (Throwable t) {
                System.err.println("[OH_WSA] step4 FAIL " + t);
                t.printStackTrace(System.err);
                throw t;
            }
        } else {
            System.err.println("[OH_WSA] step4 SKIP insetsState=null");
        }

        if (sizeCompatScale != null && sizeCompatScale.length > 0) {
            sizeCompatScale[0] = 1.0f;
            System.err.println("[OH_WSA] step5 sizeCompatScale[0]=1.0f OK");
        }

        if (attachedFrame != null) {
            try {
                // 2026-07-26: use the actual OH window rect returned by native.
                // On the legacy WMS path all successful windows end at the
                // full requested display rect.
                // If the legacy int[6] format is returned, fall back to w/h.
                int[] _wh = getDefaultDisplaySize();
                int frameLeft = sessionInfo.length > 6 ? sessionInfo[6] : 0;
                int frameTop = sessionInfo.length > 7 ? sessionInfo[7] : 0;
                int frameRight = sessionInfo.length > 8 ? sessionInfo[8] :
                        (sessionInfo[3] > 0 ? sessionInfo[3] : _wh[0]);
                int frameBottom = sessionInfo.length > 9 ? sessionInfo[9] :
                        (sessionInfo[4] > 0 ? sessionInfo[4] : _wh[1]);
                attachedFrame.set(frameLeft, frameTop, frameRight, frameBottom);
                System.err.println("[OH_WSA] step6 attachedFrame.set OK "
                        + "frame=[" + frameLeft + "," + frameTop + ","
                        + frameRight + "," + frameBottom + "]");
            } catch (Throwable t) {
                System.err.println("[OH_WSA] step6 FAIL " + t);
                t.printStackTrace(System.err);
                throw t;
            }
        }

        int flags = buildAddDisplayFlags(attrs);
        System.err.println("[OH_WSA] step7 returning addFlags=0x" + Integer.toHexString(flags));
        return flags;
    }

    /**
     * Build the bitfield return value for addToDisplay/addToDisplayAsUser per
     * AOSP IWindowSession protocol. Mirrors AOSP WindowManagerService.addWindow
     * (line 1797-1799 frameworks/base/services/.../WindowManagerService.java):
     *
     *   if (mActivityRecord == null || mActivityRecord.isClientVisible()) {
     *       res |= ADD_FLAG_APP_VISIBLE;
     *   }
     *   res |= ADD_FLAG_IN_TOUCH_MODE  (when display is in touch mode)
     *
     * adapter mapping (legacy WMS / SCB both apply since this is the AOSP
     * client-side protocol, independent of OH internal routing):
     *
     *   ADD_FLAG_APP_VISIBLE — set when (a) attrs.token == null (system window,
     *      AOSP isClientVisible() returns true for null mActivityRecord), or
     *      (b) attrs.token registered in OhTokenRegistry (ability is in
     *      launching/resuming, AOSP equivalent of mActivityRecord.isClientVisible())
     *   ADD_FLAG_IN_TOUCH_MODE — always set (DAYU200 is touch device)
     *   ADD_FLAG_USE_BLAST — NOT set (BLAST adapter incompatible with OH SurfaceControl)
     *   ADD_FLAG_ALWAYS_CONSUME_SYSTEM_BARS — NOT set (left for future)
     *
     * Without ADD_FLAG_APP_VISIBLE, ViewRootImpl initializes mAppVisible=false
     * (line 1469 ~/aosp/.../ViewRootImpl.java), getHostVisibility() returns
     * View.GONE, relayoutWindow vis=false, RenderThread does not draw frames,
     * helloworld window never appears on screen even though AMS state is
     * FOREGROUND. Verified G2.14y via hitrace.
     *
     * 2026-05-08 G2.14ag — ADD_FLAG_USE_BLAST attempt reverted:
     *   Initial hypothesis was that setting ADD_FLAG_USE_BLAST would route
     *   ViewRootImpl through BBQ_nativeGetSurface so mSurface.mNativeObject
     *   gets a real OHNativeWindow*. Implemented + deployed; helloworld cold
     *   start regressed to LIFECYCLE_TIMEOUT before reaching setView at all
     *   (onCreate→onResume gap independent of this flag). Reverted to keep
     *   diagnostic baseline; the onCreate→onResume gap is the actual blocker
     *   and has nothing to do with the BLAST gating in ViewRootImpl.
     */
    private int buildAddDisplayFlags(WindowManager.LayoutParams attrs) {
        int flags = android.view.WindowManagerGlobal.ADD_FLAG_IN_TOUCH_MODE;
        boolean isSystemWindow = (attrs == null || attrs.token == null);
        boolean isClientVisible = isSystemWindow
                || adapter.core.OhTokenRegistry.findOhToken(attrs.token) != null;
        if (isClientVisible) {
            flags |= android.view.WindowManagerGlobal.ADD_FLAG_APP_VISIBLE;
        }
        return flags;
    }

    /**
     * [BRIDGED] addToDisplayAsUser -> OH ISceneSessionManager.CreateAndConnectSpecificSession (with userId)
     */
    @Override
    public int addToDisplayAsUser(IWindow window, WindowManager.LayoutParams attrs,
            int viewVisibility, int layerStackId, int userId, int requestedVisibleTypes,
            InputChannel outInputChannel, InsetsState insetsState,
            InsetsSourceControl.Array activeControls, Rect attachedFrame,
            float[] sizeCompatScale) throws RemoteException {
        System.err.println("[OH_WSA] ENTRY addToDisplayAsUser userId=" + userId
                + " attrs.type=" + attrs.type
                + " flags=0x" + Integer.toHexString(attrs.flags)
                + " (HW_ACCEL=" + ((attrs.flags
                        & WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED) != 0)
                + ")");
        logBridged("addToDisplayAsUser", "-> OH ISceneSessionManager.CreateAndConnectSpecificSession");
        try {
            int r = addToDisplay(window, attrs, viewVisibility, layerStackId,
                    requestedVisibleTypes, outInputChannel, insetsState,
                    activeControls, attachedFrame, sizeCompatScale);
            System.err.println("[OH_WSA] addToDisplayAsUser delegate returned " + r);
            return r;
        } catch (Throwable t) {
            System.err.println("[OH_WSA] addToDisplayAsUser delegate threw " + t);
            t.printStackTrace(System.err);
            throw t;
        }
    }

    /**
     * [BRIDGED] addToDisplayWithoutInputChannel -> OH ISession (no input channel variant)
     */
    @Override
    public int addToDisplayWithoutInputChannel(IWindow window, WindowManager.LayoutParams attrs,
            int viewVisibility, int layerStackId, InsetsState insetsState,
            Rect attachedFrame, float[] sizeCompatScale) throws RemoteException {
        logBridged("addToDisplayWithoutInputChannel", "-> OH ISession (no input channel variant)");
        // TODO: Phase 2 - call native bridge without input channel
        return 0;
    }

    /**
     * [BRIDGED] remove -> OH ISession.Disconnect + ISceneSessionManager.DestroySession
     */
    @Override
    public void remove(IWindow window) throws RemoteException {
        logBridged("remove", "-> OH ISession.Disconnect");

        // Clean up InputChannel
        InputEventBridge.getInstance().destroyInputChannel(window.asBinder());

        int[] sessionInfo = mSessionMap.remove(window.asBinder());
        if (sessionInfo != null) {
            int sessionId = sessionInfo[0];
            // Destroy OH surface resources (RSSurfaceNode, RSUIDirector, OHGraphicBufferProducer)
            nativeDestroyOHSurface(sessionId);
            // Destroy OH window session (ISession.Disconnect + SSM.DestroyAndDisconnect)
            // 2026-05-11 G2.14am Bug B note: nativeDestroySession internally calls
            // IWindowManager::DestroyWindow which triggers
            // WindowNodeContainer::DestroyWindowNode → StartingWindow::Release
            // StartWinSurfaceNode (OH window_node_container.cpp:626) — leashWindow +
            // startingWindow cleanup happens in this path for graceful Activity
            // destroy.  For aa force-stop kill (process death without remove()
            // invocation), cleanup relies on OH foundation's REMOTE_DIED
            // handler.  No additional adapter-side work needed here; OH-side
            // patch (ohos_patches/) is the right venue for force-stop fix.
            nativeDestroySession(sessionId);
            // 2026-05-25 (a) fix — release the persistent SurfaceControl cached for
            // this session (mirror WMS destroying mSurfaceController on window removal).
            SurfaceControl removedSc = mSurfaceControlMap.remove(sessionId);
            if (removedSc != null && removedSc.isValid()) {
                removedSc.release();
            }
            // 2026-05-26 Layer-1 fix — drop the reverse-push size cache so a future
            // session reusing this id re-pushes its initial frame.
            mLastPushedSize.remove(sessionId);
            Log.i(TAG, "OH session destroyed: id=" + sessionId);
        } else {
            Log.w(TAG, "remove: no session found for window");
        }
    }

    // ====================================================================
    // Category 2: Window Layout
    // ====================================================================

    /**
     * [BRIDGED] relayout -> OH ISession.UpdateSessionRect + UpdateSizeChangeReason
     */
    @Override
    public int relayout(IWindow window, WindowManager.LayoutParams attrs,
            int requestedWidth, int requestedHeight, int viewVisibility,
            int flags, int seq, int lastSyncSeqId, ClientWindowFrames outFrames,
            MergedConfiguration outMergedConfiguration, SurfaceControl outSurfaceControl,
            InsetsState insetsState, InsetsSourceControl.Array activeControls,
            Bundle bundle) throws RemoteException {
        logBridged("relayout", "-> OH ISession.UpdateSessionRect");

        int[] sessionInfo = mSessionMap.get(window.asBinder());
        if (sessionInfo == null) {
            Log.w(TAG, "relayout: no session found for window; returning 0 (AOSP win==null semantics)");
            return 0;
        }

        int sessionId = sessionInfo[0];
        int width = requestedWidth > 0 ? requestedWidth : sessionInfo[3];
        int height = requestedHeight > 0 ? requestedHeight : sessionInfo[4];
        // mirror WMS relayoutWindow result flags — RELAYOUT_RES_SURFACE_CHANGED is
        // set only on first surface creation (see the outSurfaceControl block below).
        int relayoutResult = 0;

        // G2.14as r3 — log actual width/height that relayout will use
        System.err.println("[OH_WSA-relayout] session=" + sessionId
                + " requestedWH=" + requestedWidth + "x" + requestedHeight
                + " sessionInfo[3,4]=" + sessionInfo[3] + "x" + sessionInfo[4]
                + " -> useWH=" + width + "x" + height
                + " visibility=" + viewVisibility);

        // 2026-05-19: visibility transition — when AOSP signals INVISIBLE/GONE,
        // hide the WMS window so launcher can claim foreground; when VISIBLE
        // returns, re-show.  Idempotent at C++ layer (wmsShown cache on
        // SessionEntry), so calling every relayout is safe and 0 extra IPC.
        // Without this, helloworld stays z-order top after home-key press.
        // See android.view.View constants: VISIBLE=0, INVISIBLE=4, GONE=8.
        if (viewVisibility == android.view.View.VISIBLE) {
            // A window only relayouts VISIBLE while its owning activity is
            // foreground (RESUMED), so the current foreground activity IS this
            // session's owner.  attrs.token is null in this path, so record the
            // mapping here for the covered-vs-minimized decision in the hide
            // branch below.
            android.os.IBinder owner = adapter.activity.LifecycleAdapter.getForegroundToken();
            if (owner != null) {
                mSessionOwner.put(sessionId, owner);
            }
            // We are showing this window, so cancel any pending deferred hide of it.
            mDeferredHide.remove(sessionId);
            int rcShow = nativeShowWindow(sessionId);
            if (rcShow != 0) {
                System.err.println("[OH_WSA-relayout] nativeShowWindow session=" + sessionId
                        + " rc=" + rcShow);
            }
            // 2026-06-02 deterministic show-before-hide: the covering window is now
            // up, so flush any windows whose removal was deferred when they were
            // covered (see the GONE branch below).  Removing them now leaves no
            // launcher gap (the coverer already composites on top), AND — crucially
            // — it does NOT leave a covered window lingering in WMS.  The old "keep
            // forever" let a covered window (e.g. Main behind Second) survive into
            // home/back-to-desktop: WMS, after the top was removed, re-focused that
            // lingering window (UpdateActiveStatus isActive=1) and the desktop never
            // showed.  Event-driven (triggered by this show), so no timer/race.
            flushDeferredHides();
        } else {
            // 2026-06-02 back-stack fix (issue 1, flicker) — deferred hide.
            // If this window is being COVERED by a newer foreground sibling (e.g.
            // Main covered by Second in the same mission), do NOT RemoveWindow yet:
            // RemoveWindow before the covering window is added leaves a ~250ms gap
            // through which the launcher flickers.  Instead DEFER the removal — it
            // is flushed (RemoveWindow) the moment the covering window's relayout
            // VISIBLE shows it (above), so the covered window is removed with no gap
            // AND does not linger to be revealed on home/back-to-desktop.
            // Not covered (minimize-to-home / back-pop-of-top: foreground is itself
            // or an older sibling) -> remove immediately.
            android.os.IBinder actToken = mSessionOwner.get(sessionId);
            if (adapter.activity.LifecycleAdapter.isCoveredByNewerForeground(actToken)) {
                mDeferredHide.add(sessionId);
                System.err.println("[OH_WSA-relayout] session=" + sessionId
                        + " covered by newer sibling -> DEFER hide (flush on coverer show)");
            } else {
                mDeferredHide.remove(sessionId);
                int rcHide = nativeHideWindow(sessionId);
                if (rcHide != 0) {
                    System.err.println("[OH_WSA-relayout] nativeHideWindow session=" + sessionId
                            + " rc=" + rcHide);
                }
                // This window is minimizing (not covered: home / back-pop-of-top).
                // Any window whose hide was deferred while covered must ALSO go now
                // — the mission is going to background, nothing covers them anymore,
                // so they must not linger to be revealed (home-to-desktop).  This
                // also closes the race where a coverer's VISIBLE relayout arrived
                // before the covered window's GONE-defer (so the show-path flush
                // missed it).
                flushDeferredHides();
            }
        }

        // Update OH session rect
        nativeUpdateSessionRect(sessionId, 0, 0, width, height);

        // Ensure OH surface bridge is created for this session
        String windowName = "OH_Surface_" + sessionId;
        int pixelFormat = (attrs != null) ? attrs.format : 1; // default RGBA_8888
        nativeCreateOHSurface(sessionId, windowName, width, height, pixelFormat);

        // Get (or create) the OHGraphicBufferProducer handle
        long surfaceHandle = nativeGetSurfaceHandle(sessionId, width, height, pixelFormat);
        if (surfaceHandle != 0) {
            Log.i(TAG, "relayout: OH surface handle=0x" + Long.toHexString(surfaceHandle)
                    + " for session " + sessionId);
        } else {
            Log.e(TAG, "relayout: Failed to get OH surface handle for session " + sessionId);
        }

        // Update surface size if dimensions changed
        nativeUpdateSurfaceSize(sessionId, width, height);

        // Populate output frames
        if (outFrames != null) {
            Rect frame = new Rect(0, 0, width, height);
            outFrames.frame.set(frame);
            outFrames.displayFrame.set(frame);
            outFrames.parentFrame.set(frame);
            // G2.14as r3 — verify outFrames really populated
            System.err.println("[OH_WSA-relayout] outFrames populated: frame=" + outFrames.frame
                    + " displayFrame=" + outFrames.displayFrame
                    + " parentFrame=" + outFrames.parentFrame);
        } else {
            System.err.println("[OH_WSA-relayout] outFrames == null !!");
        }

        // 2026-05-25 (b) fix: build the window Configuration ONCE and share it
        // with BOTH the IWindow.resized reverse-push (below) and
        // outMergedConfiguration.  Previously the reverse-push passed an EMPTY
        // MergedConfiguration; ViewRootImpl.handleResized -> performConfigurationChange
        // then reset mLastReportedMergedConfiguration to winConfig.mBounds=0x0 every
        // frame, which perpetually mismatched the good mPendingMergedConfiguration
        // this same relayout sets -> mForceNextWindowRelayout stayed true ->
        // infinite relayout loop -> the activity never settled (gray translucent
        // window) -> 10s foreground timeout -> flicker back to launcher.
        // Reuse the framework's real global Configuration (correct densityDpi /
        // screenWidthDp / ...; DAYU200 = 240dpi) and override ONLY this window's
        // bounds, so the two configs are byte-identical with zero hardcoded
        // density/dp constants (no 160, no 320).  width/height come from the OH
        // session's real window rect, not a hardcode.
        Configuration winCfg = new Configuration(
                android.content.res.Resources.getSystem().getConfiguration());
        Rect winBounds = new Rect(0, 0, width, height);
        winCfg.windowConfiguration.setBounds(winBounds);
        winCfg.windowConfiguration.setAppBounds(winBounds);
        winCfg.windowConfiguration.setMaxBounds(winBounds);

        // 2026-05-11 G2.14as r4 — reverse-push frame to ViewRootImpl via IWindow.resized.
        // AOSP WMS pushes frame to client via IWindow.resized (not just relayout
        // return).  ViewRootImpl in LOCAL_LAYOUT mode computeFrames(measuredWidth=0,
        // measuredHeight=0) → frame=(0,0,0,0) → relayoutAsync=true → outFrames
        // not returned by oneway path → mTmpFrames.frame stays (0,0,0,0) forever
        // (death spiral: 0 → measure 0 → relayout 0).  IWindow.resized breaks the
        // spiral by reverse-pushing the real frame, which ViewRootImpl.handleResized
        // calls setFrame(frame, false) → mWinFrame=(0,0,720,1280) → next measure
        // uses real size.  Adapter must mimic this path since OH server doesn't
        // know to call it.
        // 2026-05-26 Layer-1 fix — only reverse-push when the window size actually
        // changes (mirror AOSP WMS), and with forceLayout=false.  The previous
        // unconditional push with forceLayout=true re-armed mForceNextWindowRelayout
        // every frame → requestLayout → relayout → push → infinite relayout
        // oscillation (root cause B; see Window_Lifecycle design).  First call
        // (frame 0×0 → 720×1280 or new session) still pushes once so ViewRootImpl
        // gets the correct frame and escapes the LOCAL_LAYOUT computeFrames 0×0
        // death spiral; once size is stable we stop pushing and dispatchResized
        // takes its no-op return path (frame/config unchanged + forceLayout=false).
        long sizeKey = (((long) width) << 32) | (height & 0xffffffffL);
        Long lastPushed = mLastPushedSize.get(sessionId);
        if (lastPushed == null || lastPushed.longValue() != sizeKey) {
            try {
                ClientWindowFrames pushedFrames = new ClientWindowFrames();
                pushedFrames.frame.set(0, 0, width, height);
                pushedFrames.displayFrame.set(0, 0, width, height);
                pushedFrames.parentFrame.set(0, 0, width, height);
                pushedFrames.attachedFrame = new Rect(0, 0, width, height);
                android.util.MergedConfiguration cfg = new android.util.MergedConfiguration();
                // 2026-05-25 (b): carry the SAME real config as outMergedConfiguration
                // (shared winCfg) so handleResized does not reset lastReported to 0x0.
                cfg.setOverrideConfiguration(winCfg);
                cfg.setGlobalConfiguration(new Configuration(winCfg));
                InsetsState pushedInsets = new InsetsState();
                // displayId for default display
                int displayId = 0;
                window.resized(pushedFrames, false /* reportDraw */, cfg, pushedInsets,
                        false /* forceLayout — was true; true caused the infinite relayout loop */,
                        false /* alwaysConsumeSystemBars */,
                        displayId, 0 /* syncSeqId */, false /* dragResizing */);
                mLastPushedSize.put(sessionId, sizeKey);
                System.err.println("[OH_WSA-relayout] reverse-pushed via IWindow.resized (size changed): "
                        + width + "x" + height);
            } catch (Throwable t) {
                System.err.println("[OH_WSA-relayout] IWindow.resized reverse-push failed: " + t);
            }
        } else {
            // size unchanged — skip reverse-push (mirror WMS; breaks the relayout loop)
        }

        // Populate output MergedConfiguration by REUSING the shared winCfg built
        // above (G2.14as r6 winConfig.mBounds fix folded in).  winConfig.mBounds
        // (= real OH window rect) breaks the LOCAL_LAYOUT computeFrames 0x0 death
        // spiral; sharing the SAME winCfg as the reverse-push keeps pending ==
        // last-reported so there is no relayout loop.  No hardcoded density/dp.
        if (outMergedConfiguration != null) {
            outMergedConfiguration.setOverrideConfiguration(winCfg);
            outMergedConfiguration.setGlobalConfiguration(new Configuration(winCfg));
            System.err.println("[OH_WSA-relayout] outMergedConfiguration set: "
                    + "winConfig.mBounds=" + winBounds
                    + " screenDp=" + winCfg.screenWidthDp + "x" + winCfg.screenHeightDp
                    + " densityDpi=" + winCfg.densityDpi);
        }

        // Create a SurfaceControl backed by the OH RSSurfaceNode.  2026-05-02
        // G2.14r: outSurfaceControl is now stamped with sessionId via
        // nativeAttachSessionToSc so the downstream BLASTBufferQueue can resolve
        // it back to the OH RSSurfaceNode (via OHWindowManagerClient.getOhNativeWindow)
        // and produce a real OHNativeWindow* for hwui's eglCreateWindowSurface.
        // Without this step, BBQ_nativeGetSurface returns nullptr and the whole
        // hwui render path runs on an empty Surface (mNativeObject==0), causing
        // the post-activityResumed SIGABRT.  See doc/graphics_rendering_design
        // appendix G2.14r for the full causal chain.
        if (outSurfaceControl != null) {
            long surfaceNodeId = nativeGetSurfaceNodeId(sessionId);
            // 2026-05-25 (a) fix — mirror WMS createSurfaceControl() + createSurfaceLocked():
            // build the SurfaceControl ONCE per session and REUSE it on every
            // subsequent relayout, so the underlying surface handle stays stable.
            // AOSP WMS never rebuilds the SurfaceControl per relayout — it copies
            // the persistent winAnimator.mSurfaceController into outSurfaceControl.
            // A fresh SurfaceControl each relayout made ViewRootImpl's
            // BLASTBufferQueue.isSameSurfaceControl()==false → destroy+recreate BBQ
            // → new Surface → hwui re-ran eglCreateWindowSurface on the (already
            // EGLSurface-bound) SecondActivity window → EGL reject → skia ASSERT →
            // libhwui abort.
            SurfaceControl persistentSc = mSurfaceControlMap.get(sessionId);
            boolean firstCreate = (persistentSc == null || !persistentSc.isValid());
            if (firstCreate) {
                try {
                    persistentSc = new SurfaceControl.Builder()
                            .setName(windowName)
                            .setBufferSize(width, height)
                            .build();
                    mSurfaceControlMap.put(sessionId, persistentSc);
                    Log.i(TAG, "relayout: created persistent SurfaceControl session=" + sessionId
                            + " surfaceNodeId=" + surfaceNodeId
                            + " producerHandle=0x" + Long.toHexString(surfaceHandle));
                } catch (Exception e) {
                    Log.e(TAG, "Failed to create SurfaceControl", e);
                    persistentSc = null;
                }
            }
            // G2.14r: the session ID reaches BLASTBufferQueue via OHWindowManagerClient's
            // "last attached session" thread-local — set in nativeUpdateSessionRect
            // (already called above for this session) — so the persistent SurfaceControl
            // resolves to the right OH RSSurfaceNode.
            if (persistentSc != null && persistentSc.isValid()) {
                // mirror WMS surfaceController.getSurfaceControl(outSurfaceControl):
                // copy the SAME persistent handle each relayout (stable handle).
                outSurfaceControl.copyFrom(persistentSc, "OH_relayout");
                // mirror WMS createSurfaceControl(): RELAYOUT_RES_SURFACE_CHANGED is
                // set when the surface did not exist before (first creation), OR on
                // the hidden→VISIBLE restore edge.  On restore the App's ViewRootImpl
                // destroyed its mBlastBufferQueue when the window went GONE
                // (renderer.pause()+destroySurface() on minimize); the persistent
                // SurfaceControl otherwise makes relayout look unchanged, so
                // ViewRootImpl would neither drain the RenderThread nor recreate the
                // BBQ → an in-flight RT frame hits the null BBQ (ViewRootImpl:4601).
                // Setting SURFACE_CHANGED here makes ViewRootImpl pause+drain the RT
                // and rebuild the BBQ.  Steady-state VISIBLE→VISIBLE must NOT set it
                // (that caused the 2026-05-25 EGL-recreate-on-bound-surface abort).
                Integer prevVis = mLastViewVis.get(sessionId);
                boolean wasHidden = (prevVis != null
                        && prevVis.intValue() != android.view.View.VISIBLE);
                if (firstCreate
                        || (viewVisibility == android.view.View.VISIBLE && wasHidden)) {
                    relayoutResult |= android.view.WindowManagerGlobal.RELAYOUT_RES_SURFACE_CHANGED;
                    System.err.println("[OH_WSA-relayout] session=" + sessionId
                            + " SURFACE_CHANGED (firstCreate=" + firstCreate
                            + " wasHidden=" + wasHidden + ") -> ViewRootImpl drains RT + rebuilds BBQ");
                }
            }
        }

        // Populate InsetsState
        if (insetsState != null) {
            insetsState.set(new InsetsState());
        }

        // Record this relayout's viewVisibility so the NEXT relayout can detect a
        // hidden→VISIBLE restore edge (see the SURFACE_CHANGED block above).
        mLastViewVis.put(sessionId, viewVisibility);

        // mirror WMS relayoutWindow: return the accumulated result flags (carries
        // RELAYOUT_RES_SURFACE_CHANGED on first creation or a hidden→visible restore).
        return relayoutResult;
    }

    /**
     * [BRIDGED] relayoutAsync -> OH ISession.UpdateSessionRect (async, oneway)
     */
    @Override
    public void relayoutAsync(IWindow window, WindowManager.LayoutParams attrs,
            int requestedWidth, int requestedHeight, int viewVisibility,
            int flags, int seq, int lastSyncSeqId) throws RemoteException {
        logBridged("relayoutAsync", "-> OH ISession.UpdateSessionRect (async)");
        // TODO: Phase 2 - call native bridge async
    }

    /**
     * [BRIDGED] outOfMemory -> OH memory pressure notification
     */
    @Override
    public boolean outOfMemory(IWindow window) throws RemoteException {
        logBridged("outOfMemory", "-> OH memory management");
        return false;
    }

    // ====================================================================
    // Category 3: Insets and Drawing
    // ====================================================================

    /**
     * [BRIDGED] setInsets -> OH ISession.SetAvoidArea
     */
    @Override
    public void setInsets(IWindow window, int touchableInsets, Rect contentInsets,
            Rect visibleInsets, Region touchableRegion) throws RemoteException {
        logBridged("setInsets", "-> OH ISession.SetAvoidArea");
        // TODO: Phase 2 - call native bridge to set avoid area
    }

    /**
     * [BRIDGED] finishDrawing -> OH ISessionStage.NotifyDrawingCompleted
     */
    @Override
    public void finishDrawing(IWindow window, SurfaceControl.Transaction postDrawTransaction,
            int seqId) throws RemoteException {
        logBridged("finishDrawing", "-> OH ISessionStage.NotifyDrawingCompleted");

        int[] sessionInfo = mSessionMap.get(window.asBinder());
        if (sessionInfo != null) {
            int sessionId = sessionInfo[0];
            // [Fn04.A02/A13/A14/A16] ViewRootImpl draw completion boundary.
            // seqId correlates with AOSP reportDrawFinished(t, seqId); sessionId
            // correlates with OH window/surface identity in native logs.
            Log.i(TAG, "[Fn04] finishDrawing enter window=" + window.asBinder()
                    + " sessionId=" + sessionId + " seqId=" + seqId);
            // Flush RSUIDirector::SendMessages() to commit render instructions to RenderService
            nativeNotifySurfaceDrawingCompleted(sessionId);
            // Notify OH ISession that drawing is completed
            int notifyResult = nativeNotifyDrawingCompleted(sessionId);
            Log.i(TAG, "[Fn04] finishDrawing exit sessionId=" + sessionId
                    + " seqId=" + seqId + " notifyResult=" + notifyResult);
        } else {
            Log.w(TAG, "[Fn04] finishDrawing: no session found for window seqId=" + seqId);
        }
    }

    /**
     * [STUB] clearTouchableRegion - no direct OH equivalent
     */
    @Override
    public void clearTouchableRegion(IWindow window) throws RemoteException {
        logStub("clearTouchableRegion", "no direct OH equivalent");
    }

    /**
     * [STUB] cancelDraw - returns false (do not cancel)
     */
    @Override
    public boolean cancelDraw(IWindow window) throws RemoteException {
        logStub("cancelDraw", "no OH equivalent, allowing draw");
        return false;
    }

    // ====================================================================
    // Category 4: Haptic Feedback
    // ====================================================================

    /**
     * [STUB] performHapticFeedback - OH handles haptics differently
     */
    @Override
    public boolean performHapticFeedback(int effectId, boolean always) throws RemoteException {
        logStub("performHapticFeedback", "OH haptic framework not mapped");
        return false;
    }

    /**
     * [STUB] performHapticFeedbackAsync - OH handles haptics differently (oneway)
     */
    @Override
    public void performHapticFeedbackAsync(int effectId, boolean always) throws RemoteException {
        logStub("performHapticFeedbackAsync", "OH haptic framework not mapped");
    }

    // ====================================================================
    // Category 5: Drag and Drop
    // ====================================================================

    /**
     * [BRIDGED] performDrag -> OH drag and drop framework
     */
    @Override
    public IBinder performDrag(IWindow window, int flags, SurfaceControl surface,
            int touchSource, float touchX, float touchY, float thumbCenterX,
            float thumbCenterY, ClipData data) throws RemoteException {
        logBridged("performDrag", "-> OH drag framework");
        // TODO: Phase 2 - call native drag start
        return null;
    }

    /**
     * [STUB] dropForAccessibility - no OH equivalent
     */
    @Override
    public boolean dropForAccessibility(IWindow window, int x, int y) throws RemoteException {
        logStub("dropForAccessibility", "no OH equivalent");
        return false;
    }

    /**
     * [BRIDGED] reportDropResult -> OH drag result notification (oneway)
     */
    @Override
    public void reportDropResult(IWindow window, boolean consumed) throws RemoteException {
        logBridged("reportDropResult", "-> OH drag result notification");
        // TODO: Phase 2 - call native report drop result
    }

    /**
     * [BRIDGED] cancelDragAndDrop -> OH cancel drag (oneway)
     */
    @Override
    public void cancelDragAndDrop(IBinder dragToken, boolean skipAnimation) throws RemoteException {
        logBridged("cancelDragAndDrop", "-> OH cancel drag");
        // TODO: Phase 2 - call native cancel drag
    }

    /**
     * [BRIDGED] dragRecipientEntered -> OH drag recipient notification (oneway)
     */
    @Override
    public void dragRecipientEntered(IWindow window) throws RemoteException {
        logBridged("dragRecipientEntered", "-> OH drag recipient entered");
    }

    /**
     * [BRIDGED] dragRecipientExited -> OH drag recipient notification (oneway)
     */
    @Override
    public void dragRecipientExited(IWindow window) throws RemoteException {
        logBridged("dragRecipientExited", "-> OH drag recipient exited");
    }

    // ====================================================================
    // Category 6: Wallpaper
    // ====================================================================

    /**
     * [STUB] setWallpaperPosition - OH wallpaper system differs (oneway)
     */
    @Override
    public void setWallpaperPosition(IBinder windowToken, float x, float y,
            float xstep, float ystep) throws RemoteException {
        logStub("setWallpaperPosition", "OH wallpaper position not mapped");
    }

    /**
     * [STUB] setWallpaperZoomOut - OH wallpaper system differs (oneway)
     */
    @Override
    public void setWallpaperZoomOut(IBinder windowToken, float scale) throws RemoteException {
        logStub("setWallpaperZoomOut", "OH wallpaper zoom not mapped");
    }

    /**
     * [STUB] setShouldZoomOutWallpaper - OH wallpaper system differs (oneway)
     */
    @Override
    public void setShouldZoomOutWallpaper(IBinder windowToken, boolean shouldZoom)
            throws RemoteException {
        logStub("setShouldZoomOutWallpaper", "OH wallpaper zoom not mapped");
    }

    /**
     * [STUB] wallpaperOffsetsComplete - OH wallpaper system differs (oneway)
     */
    @Override
    public void wallpaperOffsetsComplete(IBinder window) throws RemoteException {
        logStub("wallpaperOffsetsComplete", "OH wallpaper not mapped");
    }

    /**
     * [STUB] setWallpaperDisplayOffset - OH wallpaper system differs (oneway)
     */
    @Override
    public void setWallpaperDisplayOffset(IBinder windowToken, int x, int y)
            throws RemoteException {
        logStub("setWallpaperDisplayOffset", "OH wallpaper not mapped");
    }

    /**
     * [STUB] sendWallpaperCommand - OH wallpaper system differs
     */
    @Override
    public Bundle sendWallpaperCommand(IBinder window, String action, int x, int y,
            int z, Bundle extras, boolean sync) throws RemoteException {
        logStub("sendWallpaperCommand", "OH wallpaper command not mapped");
        return null;
    }

    /**
     * [STUB] wallpaperCommandComplete - OH wallpaper system differs (oneway)
     */
    @Override
    public void wallpaperCommandComplete(IBinder window, Bundle result) throws RemoteException {
        logStub("wallpaperCommandComplete", "OH wallpaper not mapped");
    }

    // ====================================================================
    // Category 7: Input and Pointer
    // ====================================================================

    /**
     * [BRIDGED] updatePointerIcon -> OH input pointer icon (oneway)
     */
    @Override
    public void updatePointerIcon(IWindow window) throws RemoteException {
        logBridged("updatePointerIcon", "-> OH input pointer icon");
        // TODO: Phase 2 - call native pointer icon update
    }

    /**
     * [BRIDGED] updateTapExcludeRegion -> OH ISession tap exclude (oneway)
     */
    @Override
    public void updateTapExcludeRegion(IWindow window, Region region) throws RemoteException {
        logBridged("updateTapExcludeRegion", "-> OH ISession tap exclude");
        // TODO: Phase 2 - call native tap exclude update
    }

    /**
     * [BRIDGED] updateRequestedVisibleTypes -> OH ISession visible types (oneway)
     */
    @Override
    public void updateRequestedVisibleTypes(IWindow window, int requestedVisibleTypes)
            throws RemoteException {
        logBridged("updateRequestedVisibleTypes", "-> OH ISession visible types");
        // TODO: Phase 2 - call native visible types update
    }

    /**
     * [BRIDGED] grantInputChannel -> OH ISession input channel
     */
    @Override
    public void grantInputChannel(int displayId, SurfaceControl surface, IWindow window,
            IBinder hostInputToken, int flags, int privateFlags, int inputFeatures,
            int type, IBinder windowToken, IBinder focusGrantToken, String inputHandleName,
            InputChannel outInputChannel) throws RemoteException {
        logBridged("grantInputChannel", "-> OH ISession input channel");
        // TODO: Phase 2 - call native grant input channel
    }

    /**
     * [BRIDGED] updateInputChannel -> OH input channel update (oneway)
     */
    @Override
    public void updateInputChannel(IBinder channelToken, int displayId,
            SurfaceControl surface, int flags, int privateFlags, int inputFeatures,
            Region region) throws RemoteException {
        logBridged("updateInputChannel", "-> OH input channel update");
        // TODO: Phase 2 - call native update input channel
    }

    // ====================================================================
    // Category 8: Focus and Embedded Windows
    // ====================================================================

    /**
     * [STUB] grantEmbeddedWindowFocus - OH embedded window focus model differs
     */
    @Override
    public void grantEmbeddedWindowFocus(IWindow window, IBinder inputToken,
            boolean grantFocus) throws RemoteException {
        logStub("grantEmbeddedWindowFocus", "OH embedded window focus not mapped");
    }

    /**
     * [STUB] transferEmbeddedTouchFocusToHost - OH embedded touch model differs
     */
    @Override
    public boolean transferEmbeddedTouchFocusToHost(IWindow embeddedWindow)
            throws RemoteException {
        logStub("transferEmbeddedTouchFocusToHost", "OH embedded touch focus not mapped");
        return false;
    }

    // ====================================================================
    // Category 9: Task / Window Movement
    // ====================================================================

    /**
     * [STUB] startMovingTask - OH task management differs
     */
    @Override
    public boolean startMovingTask(IWindow window, float startX, float startY)
            throws RemoteException {
        logStub("startMovingTask", "OH task movement not mapped");
        return false;
    }

    /**
     * [STUB] finishMovingTask - OH task management differs (oneway)
     */
    @Override
    public void finishMovingTask(IWindow window) throws RemoteException {
        logStub("finishMovingTask", "OH task movement not mapped");
    }

    // ====================================================================
    // Category 10: System Gesture and Keep-Clear Areas
    // ====================================================================

    /**
     * [STUB] reportSystemGestureExclusionChanged - OH gesture exclusion not mapped (oneway)
     */
    @Override
    public void reportSystemGestureExclusionChanged(IWindow window, List<Rect> exclusionRects)
            throws RemoteException {
        logStub("reportSystemGestureExclusionChanged", "OH gesture exclusion not mapped");
    }

    /**
     * [STUB] reportKeepClearAreasChanged - OH keep-clear areas not mapped (oneway)
     */
    @Override
    public void reportKeepClearAreasChanged(IWindow window, List<Rect> restricted,
            List<Rect> unrestricted) throws RemoteException {
        logStub("reportKeepClearAreasChanged", "OH keep-clear areas not mapped");
    }

    // ====================================================================
    // Category 11: Display Hash and Back Navigation
    // ====================================================================

    /**
     * [STUB] generateDisplayHash - no OH equivalent (oneway)
     */
    @Override
    public void generateDisplayHash(IWindow window, Rect boundsInWindow,
            String hashAlgorithm, RemoteCallback callback) throws RemoteException {
        logStub("generateDisplayHash", "no OH equivalent");
    }

    /**
     * [BRIDGED] setOnBackInvokedCallbackInfo -> OH back navigation (oneway)
     */
    @Override
    public void setOnBackInvokedCallbackInfo(IWindow window,
            OnBackInvokedCallbackInfo callbackInfo) throws RemoteException {
        logBridged("setOnBackInvokedCallbackInfo", "-> OH back navigation callback");
        // TODO: Phase 2 - call native back invocation registration
    }

    // ====================================================================
    // Category 12: Accessibility and Misc
    // ====================================================================

    /**
     * [BRIDGED] onRectangleOnScreenRequested -> OH ISession visible area request (oneway)
     */
    @Override
    public void onRectangleOnScreenRequested(IBinder token, Rect rectangle)
            throws RemoteException {
        logBridged("onRectangleOnScreenRequested", "-> OH ISession visible area request");
        // TODO: Phase 2 - call native rectangle on screen
    }

    /**
     * [STUB] getWindowId - OH accessibility window ID
     */
    @Override
    public IWindowId getWindowId(IBinder window) throws RemoteException {
        logStub("getWindowId", "OH accessibility window ID not mapped");
        return null;
    }

    /**
     * [STUB] pokeDrawLock - OH does not use draw locks
     */
    @Override
    public void pokeDrawLock(IBinder window) throws RemoteException {
        logStub("pokeDrawLock", "OH does not use draw locks");
    }

    // ====================================================================
    // Helper Methods
    // ====================================================================

    /**
     * Logs a bridged method call with its OH target mapping.
     */
    private void logBridged(String method, String target) {
        Log.d(TAG, "[BRIDGED] " + method + " " + target);
    }

    /**
     * Logs a stub method call with the reason it is not bridged.
     */
    private void logStub(String method, String reason) {
        Log.d(TAG, "[STUB] " + method + " - " + reason);
    }

    /**
     * 2026-05-11 G2.14ak — resolve MATCH_PARENT / FILL_PARENT (-1) / WRAP_CONTENT
     * (-2) attrs.width|height to actual display pixels.
     *
     * Why this method exists at this architectural layer:
     *   - AOSP IWindowSession.addToDisplay carries `attrs.width = -1` over binder
     *     (server-side resolves; client never pre-resolves)
     *   - WindowSessionAdapter extends IWindowSession.Stub — IS the binder server
     *     in our adapter scope (no system_server WMS exists between us and OH)
     *   - OH IWindowManager::CreateWindow/AddWindow take rect IN, no out param for
     *     resolved rect (verified oh_window_manager_client.cpp lines 302-320 +
     *     OH 7.0.0.18 IWindowManager.h headers — no GetWindowRect(windowId,&) API)
     *
     * Data source = DisplayManagerGlobal → OH_DisplayMgrAdapter → OH NDM, which
     * already correctly returns 720×1280 on DAYU200 (per existing hilog
     * `OH_DisplayMgrAdapter getDisplayInfo(0) -> 720x1280@69Hz`).
     *
     * Baseline fallback uses DAYU200 (the project's only target board per
     * CLAUDE.md).  An earlier dayu210 hardcode (1080×2340) caused TextViews /
     * Buttons to render outside the HWC-composited 720×1280 visible region.
     */
    private static int[] getDefaultDisplaySize() {
        try {
            android.view.Display d = android.hardware.display.DisplayManagerGlobal
                    .getInstance()
                    .getRealDisplay(android.view.Display.DEFAULT_DISPLAY);
            if (d != null) {
                android.util.DisplayMetrics dm = new android.util.DisplayMetrics();
                d.getRealMetrics(dm);
                if (dm.widthPixels > 0 && dm.heightPixels > 0) {
                    return new int[]{dm.widthPixels, dm.heightPixels};
                }
            }
        } catch (Throwable t) {
            Log.w(TAG, "getDefaultDisplaySize: DisplayManagerGlobal lookup failed,"
                    + " using DAYU200 baseline 720x1280", t);
        }
        // DAYU200 native resolution (per CLAUDE.md target hardware).
        return new int[]{720, 1280};
    }
}
