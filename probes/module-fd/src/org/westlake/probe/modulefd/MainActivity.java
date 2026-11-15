package org.westlake.probe.modulefd;

import android.app.Activity;
import android.content.res.AssetManager;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.util.Log;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;

import dalvik.system.DelegateLastClassLoader;
import dalvik.system.PathClassLoader;

/**
 * Whether Westlake's loaders take a module through a descriptor path (westlake ADR-0005), one line each:
 * [WL-MODFD-PROBE] <name> = <value>.
 *
 * A Play host can hand a client its module files as read-only descriptors; the client would then name them
 * /proc/self/fd/<n>. The probe opens its own APK read-only and loads, through that path only:
 * - a class, with a PathClassLoader whose parent is the system class loader (so the class can only come from the
 *   descriptor), and with a DelegateLastClassLoader, the loader Play services' module loader uses;
 * - an asset, with an AssetManager given the descriptor path.
 * Native libraries inside an APK (<apk>!/lib/<abi>/...) are not tested here: the probe has none.
 */
public class MainActivity extends Activity {
    private static final String TAG = "WL-MODFD-PROBE";

    static void line(String name, Object value) {
        String text = "[" + TAG + "] " + name + " = " + value;
        System.err.println(text);
        Log.i(TAG, text);
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        int passed = 0;
        ParcelFileDescriptor apk;
        try {
            apk = ParcelFileDescriptor.open(new File(getApplicationInfo().sourceDir), ParcelFileDescriptor.MODE_READ_ONLY);
        } catch (Exception e) {
            line("open own apk", "failed: " + e);
            line("verdict", "FAIL_OPEN");
            return;
        }
        String path = "/proc/self/fd/" + apk.getFd();
        File file = new File(path);
        line("descriptor path", "is file " + file.isFile() + ", readable " + file.canRead() + ", length " + file.length());

        try {
            ClassLoader loader = new PathClassLoader(path, ClassLoader.getSystemClassLoader());
            Class<?> marker = loader.loadClass("org.westlake.probe.modulefd.Marker");
            line("path class loader", (marker.getClassLoader() == loader ? "defined by the descriptor loader" : "defined elsewhere")
                    + ": " + marker.getDeclaredConstructor().newInstance());
            if (marker.getClassLoader() == loader) passed++;
        } catch (Throwable t) {
            line("path class loader", "failed: " + t);
        }

        try {
            ClassLoader loader = new DelegateLastClassLoader(path, ClassLoader.getSystemClassLoader());
            Class<?> marker = loader.loadClass("org.westlake.probe.modulefd.Marker");
            line("delegate-last class loader", (marker.getClassLoader() == loader ? "defined by the descriptor loader" : "defined elsewhere")
                    + ": " + marker.getDeclaredConstructor().newInstance());
            if (marker.getClassLoader() == loader) passed++;
        } catch (Throwable t) {
            line("delegate-last class loader", "failed: " + t);
        }

        try {
            AssetManager assets = AssetManager.class.getDeclaredConstructor().newInstance();
            int cookie = (Integer) AssetManager.class.getMethod("addAssetPath", String.class).invoke(assets, path);
            String text;
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(assets.open("wl-marker.txt")))) {
                text = reader.readLine();
            }
            line("asset manager", "cookie " + cookie + ", read \"" + text + "\"");
            if (cookie != 0 && "module-fd marker asset".equals(text)) passed++;
        } catch (Throwable t) {
            line("asset manager", "failed: " + t);
        }
        line("verdict", passed == 3 ? "PASS_ALL" : "PASSED_" + passed + "_OF_3");
    }
}
