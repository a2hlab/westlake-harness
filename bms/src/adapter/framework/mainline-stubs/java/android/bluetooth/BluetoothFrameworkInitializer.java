/*
 * Stub for android.bluetooth.BluetoothFrameworkInitializer. Real impl in
 * com.android.btservices mainline.
 *
 * Called from ActivityThread.initializeMainlineModules():
 *   BluetoothFrameworkInitializer.setBluetoothServiceManager(new BluetoothServiceManager());
 *   BluetoothFrameworkInitializer.setBinderCallsStatsInitializer(context -> ...);
 * BluetoothServiceManager is in framework.jar (android.os.BluetoothServiceManager).
 */
package android.bluetooth;

import android.content.Context;
import android.os.BluetoothServiceManager;
import java.util.function.Consumer;

public class BluetoothFrameworkInitializer {
    public static void setBluetoothServiceManager(BluetoothServiceManager m) {
        // no-op
    }
    public static void setBinderCallsStatsInitializer(Consumer<Context> init) {
        // no-op — adapter does not track per-module binder calls stats
    }
    // Called from SystemServiceRegistry.<clinit>; real impl registers the
    // BluetoothManager system-service wrappers from the btservices mainline.
    // No-op on OH (no btservices APEX).
    public static void registerServiceWrappers() {
        // no-op
    }
}
