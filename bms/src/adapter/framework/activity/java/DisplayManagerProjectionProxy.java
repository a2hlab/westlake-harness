package adapter.activity;

import android.os.Binder;
import android.os.IBinder;
import android.os.IInterface;
import android.os.Parcel;
import android.os.Parcelable;
import android.os.RemoteException;
import android.os.Trace;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Child-local display-service projection for the WifiDisplayStatus contract.
 *
 * <p>The real DisplayManagerAdapter remains authoritative for display geometry
 * and every other IDisplayManager operation.  This wrapper supplies the
 * non-null immutable status required by AOSP MediaRouter and owns the
 * child-local callback registry used to project Rosen display events into
 * Android.  Keeping that registry in the hot runtime jar avoids changing the
 * boot-class-path DisplayManagerAdapter.</p>
 */
public final class DisplayManagerProjectionProxy {
    private static final String SERVICE_NAME = "display";
    private static final String DESCRIPTOR = "android.hardware.display.IDisplayManager";
    private static final String TRANSACTION_FIELD = "TRANSACTION_getWifiDisplayStatus";
    private static final String STATUS_CLASS =
            "android.hardware.display.WifiDisplayStatus";
    private static final String TRACE_QUERY =
            "ZZ.DisplayManager.getWifiDisplayStatus";
    private static final String CALLBACK_INTERFACE =
            "android.hardware.display.IDisplayManagerCallback";

    // Android DisplayManager public event-mask bits and private callback event
    // values.  These values are stable in the IDisplayManager AIDL contract.
    private static final long EVENT_FLAG_DISPLAY_ADDED = 1L << 0;
    private static final long EVENT_FLAG_DISPLAY_REMOVED = 1L << 1;
    private static final long EVENT_FLAG_DISPLAY_CHANGED = 1L << 2;
    private static final long EVENT_FLAG_ALL = EVENT_FLAG_DISPLAY_ADDED
            | EVENT_FLAG_DISPLAY_REMOVED | EVENT_FLAG_DISPLAY_CHANGED;
    private static final int EVENT_DISPLAY_ADDED = 1;
    private static final int EVENT_DISPLAY_CHANGED = 2;
    private static final int EVENT_DISPLAY_REMOVED = 3;

    private static final Object CALLBACK_LOCK = new Object();
    private static final List<Object> CALLBACKS = new ArrayList<>();
    private static final List<Long> CALLBACK_MASKS = new ArrayList<>();
    private static final List<Long> CALLBACK_GENERATIONS = new ArrayList<>();

    private static Object sDisplayDelegate;
    private static Method sGetDisplayInfo;
    private static Method sOnDisplayEvent;
    private static boolean sSnapshotReady;
    private static int sInitialWidth;
    private static int sInitialHeight;
    private static int sInitialRotation;
    private static int sCurrentWidth;
    private static int sCurrentHeight;
    private static int sCurrentRotation;
    private static long sEventGeneration;
    private static int sLastEvent;

    private DisplayManagerProjectionProxy() {}

    /** Install before DisplayManagerGlobal resolves and retains IDisplayManager. */
    @SuppressWarnings("unchecked")
    public static void install() {
        try {
            Class<?> displayInterface = Class.forName(DESCRIPTOR);
            Class<?> stub = Class.forName("android.hardware.display.IDisplayManager$Stub");
            Field transactionField = stub.getDeclaredField(TRANSACTION_FIELD);
            transactionField.setAccessible(true);
            int transaction = transactionField.getInt(null);
            if (transaction <= 0) {
                throw new IllegalStateException("invalid IDisplayManager transaction="
                        + transaction);
            }

            Parcelable unavailableStatus = createUnavailableStatus();
            Class<?> serviceManager = Class.forName("android.os.ServiceManager");
            Field cacheField = serviceManager.getDeclaredField("sCache");
            cacheField.setAccessible(true);
            Object value = cacheField.get(null);
            if (!(value instanceof Map)) {
                throw new IllegalStateException("ServiceManager.sCache is not a Map");
            }
            Map<String, IBinder> cache = (Map<String, IBinder>) value;
            Object delegateForPrime;
            synchronized (cache) {
                IBinder existing = cache.get(SERVICE_NAME);
                if (existing == null) {
                    Method getService = serviceManager.getDeclaredMethod(
                            "getService", String.class);
                    getService.setAccessible(true);
                    existing = (IBinder) getService.invoke(null, SERVICE_NAME);
                }
                if (existing == null) {
                    throw new IllegalStateException("display adapter binder is unavailable");
                }
                if (existing instanceof DisplayBinder) {
                    System.err.println("[ZZ-DISPLAY] projection already installed");
                    return;
                }

                Method asInterface = stub.getDeclaredMethod("asInterface", IBinder.class);
                asInterface.setAccessible(true);
                Object delegate = asInterface.invoke(null, existing);
                if (!displayInterface.isInstance(delegate)) {
                    throw new IllegalStateException(
                            "display adapter does not implement " + DESCRIPTOR);
                }

                // Keep the local-interface fast path.  Forcing all calls through
                // Parcel changes framework behavior: parceling OverlayProperties
                // initializes Android native ownership hooks which do not exist in
                // the OH child.  The dynamic local interface overrides exactly one
                // method and invokes every other method directly on the existing
                // DisplayManagerAdapter.
                cache.put(SERVICE_NAME, new DisplayBinder(existing,
                        displayInterface, delegate, transaction, unavailableStatus));
                delegateForPrime = delegate;
            }
            primeDisplayEventBridge(displayInterface, delegateForPrime);
            System.err.println("[ZZ-DISPLAY] installed WifiDisplayStatus projection transaction="
                    + transaction);
        } catch (Throwable t) {
            throw new IllegalStateException(
                    "Unable to install child-local display projection", t);
        }
    }

    static final class DisplayBinder extends Binder {
        private final IBinder delegate;
        private final int transaction;
        private final Parcelable unavailableStatus;
        @SuppressWarnings("unused")
        private final IInterface localInterface;

        DisplayBinder(IBinder delegate, Class<?> displayInterface,
                Object localDelegate, int transaction,
                Parcelable unavailableStatus) {
            this.delegate = delegate;
            this.transaction = transaction;
            this.unavailableStatus = unavailableStatus;
            Object projection = Proxy.newProxyInstance(
                    DisplayManagerProjectionProxy.class.getClassLoader(),
                    new Class<?>[] {displayInterface},
                    new DisplayInvocationHandler(this, localDelegate,
                            unavailableStatus));
            this.localInterface = (IInterface) projection;
            attachInterface(localInterface, DESCRIPTOR);
        }

        @Override
        protected boolean onTransact(int code, Parcel data, Parcel reply, int flags)
                throws RemoteException {
            if (code == IBinder.INTERFACE_TRANSACTION) {
                if (reply != null) {
                    reply.writeString(DESCRIPTOR);
                }
                return true;
            }
            if (code != transaction) {
                return delegate.transact(code, data, reply, flags);
            }

            data.enforceInterface(DESCRIPTOR);
            data.enforceNoDataAvail();
            Trace.beginSection(TRACE_QUERY);
            try {
                if (reply == null) {
                    throw new RemoteException("getWifiDisplayStatus requires a reply Parcel");
                }
                reply.writeNoException();
                reply.writeTypedObject(
                        unavailableStatus, Parcelable.PARCELABLE_WRITE_RETURN_VALUE);
                System.err.println(
                        "[ZZ-DISPLAY] getWifiDisplayStatus feature=UNAVAILABLE");
                return true;
            } finally {
                Trace.endSection();
            }
        }
    }

    static final class DisplayInvocationHandler implements InvocationHandler {
        private final IBinder binder;
        private final Object delegate;
        private final Parcelable unavailableStatus;

        DisplayInvocationHandler(IBinder binder, Object delegate,
                Parcelable unavailableStatus) {
            this.binder = binder;
            this.delegate = delegate;
            this.unavailableStatus = unavailableStatus;
        }

        @Override
        public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
            String name = method.getName();
            int argumentCount = args == null ? 0 : args.length;
            if ("asBinder".equals(name) && argumentCount == 0) {
                return binder;
            }
            if ("getWifiDisplayStatus".equals(name) && argumentCount == 0) {
                Trace.beginSection(TRACE_QUERY);
                try {
                    System.err.println(
                            "[ZZ-DISPLAY] getWifiDisplayStatus feature=UNAVAILABLE");
                    return unavailableStatus;
                } finally {
                    Trace.endSection();
                }
            }
            if ("registerCallback".equals(name) && argumentCount == 1) {
                registerDisplayCallback(args[0], EVENT_FLAG_ALL);
                return null;
            }
            if ("registerCallbackWithEventMask".equals(name)
                    && argumentCount == 2) {
                long eventsMask = args[1] instanceof Number
                        ? ((Number) args[1]).longValue() : 0L;
                registerDisplayCallback(args[0], eventsMask);
                return null;
            }
            try {
                return method.invoke(delegate, args);
            } catch (InvocationTargetException e) {
                throw e.getCause();
            }
        }
    }

    /**
     * Called from the Rosen listener in liboh_adapter_bridge.so.  The native
     * listener is registered while {@link #primeDisplayEventBridge} performs
     * the first real display query, before an Activity or Unity Surface exists.
     */
    @SuppressWarnings("unused")
    private static void dispatchDisplayEvent(int event) {
        List<Object> pending = new ArrayList<>();
        synchronized (CALLBACK_LOCK) {
            if (event == EVENT_DISPLAY_CHANGED) {
                refreshSnapshotLocked();
            }
            sEventGeneration++;
            sLastEvent = event;
            long eventMask = eventMask(event);
            for (int i = 0; i < CALLBACKS.size(); i++) {
                if ((CALLBACK_MASKS.get(i) & eventMask) == 0L) {
                    continue;
                }
                CALLBACK_GENERATIONS.set(i, sEventGeneration);
                pending.add(CALLBACKS.get(i));
            }
        }
        for (Object callback : pending) {
            invokeDisplayCallback(callback, event);
        }
        System.err.println("[ZZ-DISPLAY-EVENT] event=" + event
                + " generation=" + sEventGeneration
                + " callbacks=" + pending.size()
                + " geometry=" + currentGeometry());
    }

    private static void primeDisplayEventBridge(Class<?> displayInterface,
            Object delegate) {
        try {
            Method getDisplayInfo = displayInterface.getMethod(
                    "getDisplayInfo", int.class);
            getDisplayInfo.setAccessible(true);
            Class<?> callbackInterface = Class.forName(CALLBACK_INTERFACE);
            Method onDisplayEvent = callbackInterface.getMethod(
                    "onDisplayEvent", int.class, int.class);
            onDisplayEvent.setAccessible(true);
            synchronized (CALLBACK_LOCK) {
                sDisplayDelegate = delegate;
                sGetDisplayInfo = getDisplayInfo;
                sOnDisplayEvent = onDisplayEvent;
            }

            // DisplayManagerAdapter's first native geometry getter installs
            // the OH listener.  This is a real snapshot, not a guessed size.
            Object displayInfo = getDisplayInfo.invoke(delegate, 0);
            int[] snapshot = readSnapshot(displayInfo);
            synchronized (CALLBACK_LOCK) {
                if (snapshot != null) {
                    sInitialWidth = sCurrentWidth = snapshot[0];
                    sInitialHeight = sCurrentHeight = snapshot[1];
                    sInitialRotation = sCurrentRotation = snapshot[2];
                    sSnapshotReady = true;
                }
            }
            System.err.println("[ZZ-DISPLAY-EVENT] primed geometry="
                    + currentGeometry());
        } catch (Throwable t) {
            // Display events improve orientation/configuration fidelity but
            // must not make the otherwise usable display service unavailable.
            System.err.println("[ZZ-DISPLAY-EVENT] prime failed: " + rootCause(t));
        }
    }

    private static void registerDisplayCallback(Object callback, long eventsMask) {
        if (callback == null) {
            return;
        }
        boolean replay = false;
        int replayEvent = 0;
        synchronized (CALLBACK_LOCK) {
            int index = findCallbackLocked(callback);
            if (index < 0) {
                index = CALLBACKS.size();
                CALLBACKS.add(callback);
                CALLBACK_MASKS.add(eventsMask);
                CALLBACK_GENERATIONS.add(0L);
            } else {
                CALLBACK_MASKS.set(index, eventsMask);
            }

            // If Rosen rotated before Android/Swappy registered its listener,
            // compare a fresh real snapshot with the initial one and turn that
            // missed transition into one display-changed generation.
            boolean snapshotChanged = refreshSnapshotLocked();
            if (snapshotChanged && sEventGeneration == 0L) {
                sEventGeneration = 1L;
                sLastEvent = EVENT_DISPLAY_CHANGED;
            }
            long lastDelivered = CALLBACK_GENERATIONS.get(index);
            long lastMask = eventMask(sLastEvent);
            if (sEventGeneration > lastDelivered
                    && (eventsMask & lastMask) != 0L) {
                CALLBACK_GENERATIONS.set(index, sEventGeneration);
                replay = true;
                replayEvent = sLastEvent;
            }
        }
        if (replay) {
            invokeDisplayCallback(callback, replayEvent);
        }
        System.err.println("[ZZ-DISPLAY-EVENT] registered mask=0x"
                + Long.toHexString(eventsMask) + " replay=" + replay
                + " geometry=" + currentGeometry());
    }

    private static int findCallbackLocked(Object callback) {
        for (int i = 0; i < CALLBACKS.size(); i++) {
            if (CALLBACKS.get(i) == callback) {
                return i;
            }
        }
        return -1;
    }

    private static boolean refreshSnapshotLocked() {
        if (sDisplayDelegate == null || sGetDisplayInfo == null) {
            return false;
        }
        try {
            int[] snapshot = readSnapshot(
                    sGetDisplayInfo.invoke(sDisplayDelegate, 0));
            if (snapshot == null) {
                return false;
            }
            if (!sSnapshotReady) {
                sInitialWidth = sCurrentWidth = snapshot[0];
                sInitialHeight = sCurrentHeight = snapshot[1];
                sInitialRotation = sCurrentRotation = snapshot[2];
                sSnapshotReady = true;
                return false;
            }
            boolean changed = snapshot[0] != sCurrentWidth
                    || snapshot[1] != sCurrentHeight
                    || snapshot[2] != sCurrentRotation;
            sCurrentWidth = snapshot[0];
            sCurrentHeight = snapshot[1];
            sCurrentRotation = snapshot[2];
            return changed;
        } catch (Throwable t) {
            System.err.println("[ZZ-DISPLAY-EVENT] snapshot failed: " + rootCause(t));
            return false;
        }
    }

    private static int[] readSnapshot(Object displayInfo) throws Exception {
        if (displayInfo == null) {
            return null;
        }
        Class<?> infoClass = displayInfo.getClass();
        Field width = infoClass.getField("logicalWidth");
        Field height = infoClass.getField("logicalHeight");
        Field rotation = infoClass.getField("rotation");
        width.setAccessible(true);
        height.setAccessible(true);
        rotation.setAccessible(true);
        return new int[] {
                width.getInt(displayInfo),
                height.getInt(displayInfo),
                rotation.getInt(displayInfo)
        };
    }

    private static void invokeDisplayCallback(Object callback, int event) {
        Method method;
        synchronized (CALLBACK_LOCK) {
            method = sOnDisplayEvent;
        }
        if (method == null) {
            return;
        }
        try {
            method.invoke(callback, 0, event);
        } catch (Throwable t) {
            System.err.println("[ZZ-DISPLAY-EVENT] callback failed: " + rootCause(t));
        }
    }

    private static long eventMask(int event) {
        switch (event) {
            case EVENT_DISPLAY_ADDED:
                return EVENT_FLAG_DISPLAY_ADDED;
            case EVENT_DISPLAY_REMOVED:
                return EVENT_FLAG_DISPLAY_REMOVED;
            case EVENT_DISPLAY_CHANGED:
                return EVENT_FLAG_DISPLAY_CHANGED;
            default:
                return 0L;
        }
    }

    private static String currentGeometry() {
        synchronized (CALLBACK_LOCK) {
            if (!sSnapshotReady) {
                return "unavailable";
            }
            return sCurrentWidth + "x" + sCurrentHeight
                    + "@" + sCurrentRotation
                    + " initial=" + sInitialWidth + "x" + sInitialHeight
                    + "@" + sInitialRotation;
        }
    }

    private static Throwable rootCause(Throwable throwable) {
        if (throwable instanceof InvocationTargetException
                && ((InvocationTargetException) throwable).getCause() != null) {
            return ((InvocationTargetException) throwable).getCause();
        }
        return throwable;
    }

    private static Parcelable createUnavailableStatus() throws Exception {
        Class<?> statusClass = Class.forName(STATUS_CLASS);
        Constructor<?> constructor = statusClass.getDeclaredConstructor();
        constructor.setAccessible(true);
        Object status = constructor.newInstance();
        if (!(status instanceof Parcelable)) {
            throw new IllegalStateException(STATUS_CLASS + " is not Parcelable");
        }
        return (Parcelable) status;
    }
}
