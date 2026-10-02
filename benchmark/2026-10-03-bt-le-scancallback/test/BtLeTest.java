import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanResult;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.Collections;

/**
 * Host-ART check on the boards' boot class path (benchmark/2026-10-03-bt-le-scancallback): the fd-plus shape
 * (an app class that extends android.bluetooth.le.ScanCallback, instantiated from Application.onCreate via
 * PluginsHelper.initPlugins -> ExternalSensorsPlugin.<init> -> DevicesHelper.<init> -> new DevicesHelper$1()).
 */
public class BtLeTest {
    static int failures;

    static class AppCallback extends ScanCallback {   // DevicesHelper$1 stand-in
        int calls;
        @Override public void onScanResult(int callbackType, ScanResult result) { calls++; }
    }

    static void check(String name, boolean ok, String detail) {
        System.out.println("CASE " + name + ": " + (ok ? "PASS" : "FAIL") + " " + detail);
        if (!ok) failures++;
    }

    public static void main(String[] args) {
        try {
            AppCallback cb = new AppCallback();
            check("1 app subclass of ScanCallback loads and instantiates", true, cb.getClass().getSuperclass().getName());
            cb.onScanResult(ScanSettingsCallbackType(), null);
            ScanCallback base = cb;
            base.onBatchScanResults(Collections.<ScanResult>emptyList());
            base.onScanFailed(4);
            check("2 callbacks dispatch (override runs, base methods are no-ops)", cb.calls == 1, "calls=" + cb.calls);
            Class<?> c = ScanCallback.class;
            check("3 ScanCallback is public abstract", Modifier.isAbstract(c.getModifiers()) && Modifier.isPublic(c.getModifiers()),
                    Modifier.toString(c.getModifiers()));
            String[] names = {"SCAN_FAILED_ALREADY_STARTED", "SCAN_FAILED_APPLICATION_REGISTRATION_FAILED",
                    "SCAN_FAILED_INTERNAL_ERROR", "SCAN_FAILED_FEATURE_UNSUPPORTED",
                    "SCAN_FAILED_OUT_OF_HARDWARE_RESOURCES", "SCAN_FAILED_SCANNING_TOO_FREQUENTLY"};
            StringBuilder sb = new StringBuilder();
            boolean ok = true;
            for (int i = 0; i < names.length; i++) {
                Field f = c.getField(names[i]);
                int v = f.getInt(null);
                ok &= v == i + 1;
                sb.append(names[i].substring(12)).append('=').append(v).append(' ');
            }
            check("4 SCAN_FAILED_* constants equal AOSP 14 (1..6)", ok, sb.toString().trim());
        } catch (Throwable t) {
            check("1 app subclass of ScanCallback loads and instantiates", false, String.valueOf(t));
        }
        try {
            Class.forName("android.bluetooth.BluetoothAdapter");
            System.out.println("INFO android.bluetooth.BluetoothAdapter present");
        } catch (Throwable t) {
            System.out.println("INFO android.bluetooth.BluetoothAdapter absent (unchanged by this fix): " + t);
        }
        System.out.println("FAILURES " + failures);
        System.exit(failures == 0 ? 0 : 1);
    }

    static int ScanSettingsCallbackType() { return 1; }   // ScanSettings.CALLBACK_TYPE_ALL_MATCHES
}
