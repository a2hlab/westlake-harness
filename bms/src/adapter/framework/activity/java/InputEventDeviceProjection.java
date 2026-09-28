package adapter.activity;

import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.InputDevice;
import android.view.InputEvent;
import android.view.InputEventReceiver;
import android.view.MotionEvent;

/**
 * Repairs the device identity lost by the adapter's legacy six-argument
 * MotionEvent reconstruction before dispatching the event to ViewRootImpl.
 *
 * The repair is deliberately narrow: only a touchscreen MotionEvent whose
 * device id does not resolve is copied.  Key events and already-valid input
 * events are forwarded byte-for-byte at the Java object level.
 */
public final class InputEventDeviceProjection {
    private static final String TAG = "OH_InputDeviceProjection";
    private static volatile Handler sMainHandler;
    private static volatile java.lang.reflect.Method sDispatchMethod;
    private static volatile int sTouchDeviceId = Integer.MIN_VALUE;

    private InputEventDeviceProjection() {
    }

    private static Handler getMainHandler() {
        Handler handler = sMainHandler;
        if (handler == null) {
            synchronized (InputEventDeviceProjection.class) {
                handler = sMainHandler;
                if (handler == null) {
                    handler = new Handler(Looper.getMainLooper());
                    sMainHandler = handler;
                }
            }
        }
        return handler;
    }

    private static java.lang.reflect.Method resolveDispatchMethod() {
        java.lang.reflect.Method method = sDispatchMethod;
        if (method == null) {
            synchronized (InputEventDeviceProjection.class) {
                method = sDispatchMethod;
                if (method == null) {
                    try {
                        method = InputEventReceiver.class.getDeclaredMethod(
                                "dispatchInputEvent", int.class, InputEvent.class);
                        method.setAccessible(true);
                        sDispatchMethod = method;
                    } catch (Throwable t) {
                        Log.e(TAG, "dispatch method lookup failed: " + t);
                    }
                }
            }
        }
        return method;
    }

    private static int resolveTouchDeviceId() {
        int cached = sTouchDeviceId;
        if (cached != Integer.MIN_VALUE) {
            return cached;
        }
        synchronized (InputEventDeviceProjection.class) {
            cached = sTouchDeviceId;
            if (cached != Integer.MIN_VALUE) {
                return cached;
            }
            int resolved = 0;
            try {
                int[] ids = InputDevice.getDeviceIds();
                if (ids != null) {
                    for (int id : ids) {
                        InputDevice device = InputDevice.getDevice(id);
                        if (device != null
                                && device.supportsSource(InputDevice.SOURCE_TOUCHSCREEN)) {
                            resolved = id;
                            break;
                        }
                    }
                }
            } catch (Throwable t) {
                Log.w(TAG, "touch device lookup failed: " + t);
            }
            sTouchDeviceId = resolved;
            Log.i(TAG, "touch device projection resolved id=" + resolved);
            return resolved;
        }
    }

    private static InputEvent projectDevice(InputEvent inputEvent) {
        if (!(inputEvent instanceof MotionEvent)) {
            return inputEvent;
        }
        MotionEvent source = (MotionEvent) inputEvent;
        try {
            int sourceDeviceId = source.getDeviceId();
            if (sourceDeviceId != 0) {
                InputDevice sourceDevice = InputDevice.getDevice(sourceDeviceId);
                if (sourceDevice != null
                        && sourceDevice.supportsSource(InputDevice.SOURCE_TOUCHSCREEN)) {
                    return source;
                }
            }
            if (!source.isFromSource(InputDevice.SOURCE_TOUCHSCREEN)) {
                return source;
            }
            int touchDeviceId = resolveTouchDeviceId();
            if (touchDeviceId == 0) {
                return source;
            }
            MotionEvent projected = MotionEvent.obtain(
                    source.getDownTime(), source.getEventTime(), source.getAction(),
                    source.getX(), source.getY(), source.getPressure(), source.getSize(),
                    source.getMetaState(), source.getXPrecision(), source.getYPrecision(),
                    touchDeviceId, source.getEdgeFlags());
            projected.setSource(source.getSource());
            Log.i(TAG, "projected MotionEvent deviceId=" + sourceDeviceId
                    + "->" + touchDeviceId + " source=0x"
                    + Integer.toHexString(source.getSource()));
            return projected;
        } catch (Throwable t) {
            Log.w(TAG, "MotionEvent projection failed: " + t);
            return source;
        }
    }

    public static void dispatchOnMainThread(final InputEventReceiver receiver,
                                            final int seq,
                                            final InputEvent inputEvent) {
        if (receiver == null || inputEvent == null) {
            return;
        }
        final java.lang.reflect.Method method = resolveDispatchMethod();
        if (method == null) {
            return;
        }
        final InputEvent projected = projectDevice(inputEvent);
        final Handler handler = getMainHandler();
        if (Looper.myLooper() == handler.getLooper()) {
            try {
                method.invoke(receiver, Integer.valueOf(seq), projected);
            } catch (Throwable t) {
                Log.w(TAG, "inline dispatch failed: " + t);
            }
            return;
        }
        handler.post(new Runnable() {
            @Override
            public void run() {
                try {
                    method.invoke(receiver, Integer.valueOf(seq), projected);
                } catch (Throwable t) {
                    Log.w(TAG, "posted dispatch failed: " + t);
                }
            }
        });
    }
}
