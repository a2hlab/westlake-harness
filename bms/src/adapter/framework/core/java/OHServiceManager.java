/*
 * OHServiceManager.java
 *
 * Real-routed adapter implementation of android.os.IServiceManager.
 * Replaces the Proxy.newProxyInstance hack (which spins indefinitely under
 * init service due to ART class generation issue with multi-interface Proxy
 * over @hide AIDL types).
 *
 * Routing strategy (per 2026-04-28 user feedback):
 *   - getService("connectivity") → null    (stub, OH has no analog, harmless skip in handleBindApplication)
 *   - getService("display")      → null    (stub for now; real OH IDisplayManagerSAID route TBD)
 *   - other names                → null    (default stub)
 *   - non-getService methods     → safe defaults (empty arrays, false, no-op)
 *
 * Future: route specific service names to OH SystemAbilityManager via JNI:
 *     adapter.core.OHEnvironment.nativeGetOHSystemAbility(int saId).  Per
 *     "feedback_blame_adapter_first" rule we adapt at the IPC interface,
 *     never modify android.os.ServiceManager itself.
 */
package adapter.core;

import android.os.IBinder;
import android.os.IServiceManager;
import android.os.IServiceCallback;
import android.os.IClientCallback;
import android.os.RemoteException;
import android.os.ConnectionInfo;
import android.os.ServiceDebugInfo;

public final class OHServiceManager extends IServiceManager.Stub {

    private static final String TAG = "OHServiceManager";

    public OHServiceManager() {
        System.err.println("[" + TAG + "] instantiated (real-routed adapter, not Proxy)");
    }

    // --- Service lookup ---

    @Override
    public IBinder getService(String name) throws RemoteException {
        IBinder b = lookupAdapter(name);
        if (b != null) {
            System.err.println("[" + TAG + "] getService(\"" + name + "\") → adapter (real-routed)");
            return b;
        }
        // Track per-service stub status for the inventory.  Once a service
        // has a real adapter, add it to lookupAdapter() switch below.
        // Production HelloWorld currently hits 4 stub services:
        //   connectivity        — Network state queries (low priority for HelloWorld)
        //   network_management  — Same family
        //   content_capture     — View tree capture (analytics, low priority)
        //   game                — Game mode (low priority)
        // Future P3: each requires real OH IPC bridge to corresponding OH SA.
        System.err.println("[" + TAG + "] getService(\"" + name + "\") → null (stub — see doc/shortcuts_inventory.html#chC)");
        return null;
    }

    @Override
    public IBinder checkService(String name) throws RemoteException {
        return lookupAdapter(name);
    }

    /**
     * Returns the adapter IBinder for service names that have a real OH route,
     * or null if no adapter exists yet.  Wired services are real adapters that
     * bridge to OH inner_api via JNI — not stubs.  Add new entries here when a
     * real adapter ships.
     *
     * 2026-04-29 (post-B.29): per feedback.txt line 4, ServiceManager 真适配
     * 扩展.  Wire all 4 core Adapters that already extend IXxx.Stub via
     * Reflection so OHServiceManager doesn't have a hard compile-time dep on
     * adapter.activity.* / adapter.window.* / adapter.packagemanager.* (which
     * live in oh-adapter-framework.jar, not in core / not always loaded
     * depending on caller).  Adapter classes are loaded by the same
     * PathClassLoader that loaded OHServiceManager so reflection lookup is
     * cheap (one Class.forName + getMethod cache miss on first call).
     *
     * Per feedback.txt line 12, services with no OH analog (connectivity /
     * network_management / content_capture / game) explicitly return null
     * here.  Framework code that tries getService(CONNECTIVITY_SERVICE) on
     * Hello World path is expected to handle null gracefully (boot-path
     * skips for these are登记 in shortcuts_inventory.html#chC).
     */
    private static IBinder lookupAdapter(String name) {
        if (name == null) return null;
        switch (name) {
            case "activity":
                return getAdapterBinder("adapter.activity.ActivityManagerAdapter");
            case "activity_task":
                return getAdapterBinder("adapter.activity.ActivityTaskManagerAdapter");
            case "package":
                return getAdapterBinder("adapter.packagemanager.PackageManagerAdapter");
            case "window":
                return getAdapterBinder("adapter.window.WindowManagerAdapter");
            case "display":
                return adapter.window.DisplayManagerAdapter.getInstance().asBinder();
            // 2026-04-30 G2.9: input_method real-routed via InputMethodManagerAdapter
            // returning NO_IME baseline. Editor / TextView startup paths require
            // a non-null IInputMethodManager binder or AOSP IMM throws
            // IllegalStateException("IInputMethodManager is not available").
            // See doc/window_manager_ipc_adapter_design.html §5.
            case "input_method":
                return adapter.window.InputMethodManagerAdapter.getInstance().asBinder();
            // [UNITY-CONTENT-SVC] getService("content") must return a non-null
            // IContentService binder: ContentResolver.getContentService() caches
            // it and calls registerContentObserver(...) during Activity onResume.
            // A null here => NPE "Unable to resume activity .../UnityPlayerActivity"
            // (FIRST BCP wall after IL2CPP engine load). ContentServiceAdapter is a
            // no-op IContentService.Stub (OH has no analog). Mirrors the "user" ->
            // UserManagerAdapter arm. Lives in oh-adapter-framework.jar (BCP).
            case "content":
                return adapter.contentprovider.ContentServiceAdapter.getInstance().asBinder();
            // [UNITY-SVC-STUB] Unity device-peripheral services (DP3 P1/P2).  These return
            // minimal no-op binders so getSystemService()/getServiceOrThrow() never returns
            // null / throws ServiceNotFoundException, and Unity's runtime peripheral calls
            // (PowerManager WakeLock/isInteractive, AudioManager volume, Vibrator, Clipboard)
            // resolve to safe no-ops instead of a proxy RemoteException.  POWER is the
            // fatal one: SystemServiceRegistry's PowerManager fetcher does
            // getServiceOrThrow("power") AND getServiceOrThrow("thermalservice") at
            // construction.  Only Unity peripheral services are added here — Display /
            // Window / AMS base services are untouched (owned elsewhere, already working).
            case "power":
            case "thermalservice":
            case "audio":
            case "vibrator_manager":
            case "clipboard":
                return unitySvcStub(name);
            // Explicit stub-null whitelist (feedback.txt line 12): services
            // for which OH has no analog and HelloWorld path tolerates null.
            case "connectivity":
            case "network_management":
            case "content_capture":
            case "game":
                return null;
            default:
                return null;
        }
    }

    /**
     * Reflectively load Adapter class + invoke getInstance() + asBinder().
     * Returns null on any failure so framework code falls through to its
     * null-handling path.  Each Adapter caches its singleton internally so
     * subsequent calls are cheap field reads after the first reflection.
     */
    private static IBinder getAdapterBinder(String fqcn) {
        try {
            Class<?> cls = Class.forName(fqcn);
            Object inst = cls.getMethod("getInstance").invoke(null);
            return ((android.os.IBinder) inst);
        } catch (Throwable t) {
            System.err.println("[" + TAG + "] getAdapterBinder(" + fqcn + ") FAIL: " + t);
            return null;
        }
    }

    // [UNITY-SVC-STUB] Lazy singletons for the Unity peripheral-service stub binders.
    // Each *Stub is an auto-generated (adapter.core.unitysvc.*) subclass of the
    // corresponding android AIDL .Stub returning safe defaults; clipboard keeps an
    // in-memory ClipData.  Held as IBinder so OHServiceManager has no hard compile dep
    // beyond the generated classes (which ship in this same jar).
    private static IBinder sUnityPower, sUnityThermal, sUnityAudio, sUnityVibratorMgr, sUnityClipboard;

    private static synchronized IBinder unitySvcStub(String name) {
        switch (name) {
            case "power":
                if (sUnityPower == null) sUnityPower = new adapter.core.unitysvc.PowerManagerStub();
                return sUnityPower;
            case "thermalservice":
                if (sUnityThermal == null) sUnityThermal = new adapter.core.unitysvc.ThermalServiceStub();
                return sUnityThermal;
            case "audio":
                if (sUnityAudio == null) sUnityAudio = new adapter.core.unitysvc.AudioServiceStub();
                return sUnityAudio;
            case "vibrator_manager":
                if (sUnityVibratorMgr == null) sUnityVibratorMgr = new adapter.core.unitysvc.VibratorManagerStub();
                return sUnityVibratorMgr;
            case "clipboard":
                if (sUnityClipboard == null) sUnityClipboard = new adapter.core.unitysvc.ClipboardStub();
                return sUnityClipboard;
            default:
                return null;
        }
    }

    @Override
    public void addService(String name, IBinder service, boolean allowIsolated, int dumpPriority)
            throws RemoteException {
        // No-op: adapter does not register services with OH SAM via this path.
        System.err.println("[" + TAG + "] addService(\"" + name + "\") ignored");
    }

    @Override
    public String[] listServices(int dumpPriority) throws RemoteException {
        return new String[0];
    }

    @Override
    public void registerForNotifications(String name, IServiceCallback callback)
            throws RemoteException {
        // No-op
    }

    @Override
    public void unregisterForNotifications(String name, IServiceCallback callback)
            throws RemoteException {
        // No-op
    }

    @Override
    public boolean isDeclared(String name) throws RemoteException {
        return false;
    }

    @Override
    public String[] getDeclaredInstances(String iface) throws RemoteException {
        return new String[0];
    }

    @Override
    public String updatableViaApex(String name) throws RemoteException {
        return null;
    }

    @Override
    public String[] getUpdatableNames(String apexName) throws RemoteException {
        return new String[0];
    }

    @Override
    public ConnectionInfo getConnectionInfo(String name) throws RemoteException {
        return null;
    }

    @Override
    public void registerClientCallback(String name, IBinder service, IClientCallback callback)
            throws RemoteException {
        // No-op
    }

    @Override
    public void tryUnregisterService(String name, IBinder service) throws RemoteException {
        // No-op
    }

    @Override
    public ServiceDebugInfo[] getServiceDebugInfo() throws RemoteException {
        return new ServiceDebugInfo[0];
    }
}
