package org.westlake.a0probe;

import android.app.Activity;
import android.os.Bundle;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.widget.FrameLayout;
import android.widget.TextView;

/** M2 A0 probe launcher (test-only): a label + a SurfaceView. liba0shim.so starts the in-process ArkWeb probe; for
 *  mode 64 (route-a FORMAL / cc-wiki Plan A) the SurfaceView's holder Surface is handed to native on surfaceCreated. */
public class MainActivity extends Activity implements SurfaceHolder.Callback {
    static native String nativeStart(String nativeLibraryDir, String bundleName);
    static native void nativeSurfaceReady(Object surface);   // mode 64: hand the SurfaceView holder Surface to a0shim

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        FrameLayout root = new FrameLayout(this);
        TextView t = new TextView(this);
        t.setText("A0 ArkWeb probe");
        t.setTextSize(32);
        root.addView(t);
        SurfaceView sv = new SurfaceView(this);
        sv.setZOrderMediaOverlay(true);           // above the window content so NWeb's frame can be seen
        sv.getHolder().addCallback(this);
        root.addView(sv);
        setContentView(root);
        try {
            System.loadLibrary("a0shim");
            System.err.println("[A0-JAVA] " + nativeStart(getApplicationInfo().nativeLibraryDir, getPackageName()));
        } catch (Throwable e) {
            System.err.println("[A0-JAVA] shim failed: " + e);
        }
    }

    @Override
    public void surfaceCreated(SurfaceHolder h) {
        try {
            nativeSurfaceReady(h.getSurface());
            System.err.println("[A0-JAVA] surfaceCreated -> nativeSurfaceReady");
        } catch (Throwable e) {
            System.err.println("[A0-JAVA] nativeSurfaceReady failed: " + e);
        }
    }

    @Override public void surfaceChanged(SurfaceHolder h, int format, int w, int ht) {}
    @Override public void surfaceDestroyed(SurfaceHolder h) {}
}
