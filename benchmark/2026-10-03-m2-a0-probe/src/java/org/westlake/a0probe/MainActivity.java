package org.westlake.a0probe;

import android.app.Activity;
import android.os.Bundle;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.widget.FrameLayout;
import android.widget.TextView;

/** M2 A0 probe launcher (test-only): a label + a SurfaceView. liba0shim.so starts the in-process ArkWeb probe.
 *  surfaceCreated hands native both the SurfaceView holder Surface (mode 64, route-a FORMAL / cc-wiki Plan A) and the
 *  SurfaceView's content-area rect in the window (mode 32 child-node bounds). Window 17: nativeSurfaceReady is registered
 *  by the RUNTIME entry (libwestlake_html_compat.so, B7BindFixes-loaded), NOT the app-ns a0shim -- so if the entry has
 *  not registered it yet we get UnsatisfiedLinkError and log + retry (the entry registers via currentApplication()). */
public class MainActivity extends Activity implements SurfaceHolder.Callback {
    static native String nativeStart(String nativeLibraryDir, String bundleName);
    // Registered by the entry (not a0shim). (surface, x, y, w, h): holder Surface + the SurfaceView rect in the window.
    static native void nativeSurfaceReady(Object surface, int x, int y, int w, int h);

    private SurfaceView surfaceView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        FrameLayout root = new FrameLayout(this);
        TextView t = new TextView(this);
        t.setText("A0 ArkWeb probe");
        t.setTextSize(32);
        root.addView(t);
        surfaceView = new SurfaceView(this);
        surfaceView.setZOrderMediaOverlay(true);      // above the window content so NWeb's frame can be seen
        surfaceView.getHolder().addCallback(this);
        root.addView(surfaceView);
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
        int[] loc = new int[2];
        surfaceView.getLocationInWindow(loc);          // position of the SurfaceView within the window = content-area offset
        int x = loc[0], y = loc[1], w = surfaceView.getWidth(), ht = surfaceView.getHeight();
        for (int attempt = 0; attempt < 20; attempt++) {   // the entry registers nativeSurfaceReady via currentApplication()
            try {
                nativeSurfaceReady(h.getSurface(), x, y, w, ht);
                System.err.println("[A0-JAVA] surfaceCreated -> nativeSurfaceReady loc=" + x + "," + y
                        + " size=" + w + "x" + ht + " (attempt " + attempt + ")");
                return;
            } catch (UnsatisfiedLinkError e) {
                if (attempt == 0) {
                    System.err.println("[A0-JAVA] nativeSurfaceReady not yet registered by entry, retrying: " + e);
                }
                try { Thread.sleep(150); } catch (InterruptedException ie) { Thread.currentThread().interrupt(); }
            } catch (Throwable e) {
                System.err.println("[A0-JAVA] nativeSurfaceReady failed: " + e);
                return;
            }
        }
        System.err.println("[A0-JAVA] nativeSurfaceReady STILL unregistered after retries (entry did not register it)");
    }

    @Override public void surfaceChanged(SurfaceHolder h, int format, int w, int ht) {}
    @Override public void surfaceDestroyed(SurfaceHolder h) {}
}
