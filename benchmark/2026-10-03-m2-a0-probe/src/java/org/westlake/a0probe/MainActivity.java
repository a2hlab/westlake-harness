package org.westlake.a0probe;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;

/** M2 A0 probe launcher (test-only): shows a label, then starts the in-process ArkWeb probe through liba0shim.so. */
public class MainActivity extends Activity {
    static native String nativeStart(String nativeLibraryDir, String bundleName);

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        TextView t = new TextView(this);
        t.setText("A0 ArkWeb probe");
        t.setTextSize(32);
        setContentView(t);
        try {
            System.loadLibrary("a0shim");
            System.err.println("[A0-JAVA] " + nativeStart(getApplicationInfo().nativeLibraryDir, getPackageName()));
        } catch (Throwable e) {
            System.err.println("[A0-JAVA] shim failed: " + e);
        }
    }
}
