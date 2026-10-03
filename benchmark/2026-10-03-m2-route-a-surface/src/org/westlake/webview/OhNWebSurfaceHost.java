package org.westlake.webview;

import android.content.Context;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.ViewGroup;
import android.widget.AbsoluteLayout;

/**
 * M2 route-a, Option A: host a {@link SurfaceView} inside the hosted WebView (android.webkit.WebView extends
 * AbsoluteLayout, a ViewGroup) and feed its holder's Surface to the NWeb backend. The SurfaceView gives us the one
 * thing cc-t3 window14 showed the bridge's Activity-window surface cannot: a self-drawing child RSSurfaceNode
 * ("AdapterSurfaceView", [STAGE2-SURFACEVIEW] -> oh_rs_get_child_surface_window) that RS actually composites into the
 * window layer. The View framework drives the SurfaceView's position/size/visibility/z-order, so NO manual native
 * geometry sync is needed (that is Option B / mode-32's burden).
 *
 * Framework-classpath only (android.view.SurfaceView etc. are @hide-free but android.*): this is the wiring draft; the
 * testable lifecycle is {@link NWebSurfaceLifecycle} (unit-tested offline). OhNWebProvider calls
 * {@link #attach(ViewGroup)} from its WebView init / onAttachedToWindow, and forwards loadUrl/settings/onPause/onResume
 * and canGoBack/goBack to the {@link NWebSurfaceLifecycle}.
 */
public final class OhNWebSurfaceHost implements SurfaceHolder.Callback {

    private final NWebSurfaceLifecycle lifecycle;
    private SurfaceView surfaceView;

    public OhNWebSurfaceHost(NWebBackend backend, NWebCallbackSink sink, String bundlePath) {
        this.lifecycle = new NWebSurfaceLifecycle(backend, sink, bundlePath);
    }

    /** Add a match-parent SurfaceView to the hosted WebView (a ViewGroup) and register for its surface lifecycle. */
    public void attach(ViewGroup webView) {
        Context ctx = webView.getContext();
        surfaceView = new SurfaceView(ctx);
        // The WebView itself paints nothing (route-a has no AOSP render path); NWeb draws into the SurfaceView's own
        // composited child layer. Put the SurfaceView above the (empty) WebView content; it is not a media overlay
        // behind the window -- it IS the WebView's content.
        surfaceView.setZOrderMediaOverlay(true);
        webView.addView(surfaceView, new AbsoluteLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT, 0, 0));
        surfaceView.getHolder().addCallback(this);
    }

    public NWebSurfaceLifecycle lifecycle() { return lifecycle; }

    // SurfaceHolder.Callback — create NWeb only once the surface is live (avoids the M3 EGL-IAE early-touch).
    @Override public void surfaceCreated(SurfaceHolder holder) {
        int w = surfaceView.getWidth(), h = surfaceView.getHeight();
        lifecycle.onSurfaceReady(holder.getSurface(), w, h);
    }
    @Override public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
        lifecycle.onSurfaceChanged(width, height);
    }
    @Override public void surfaceDestroyed(SurfaceHolder holder) {
        lifecycle.onSurfaceLost();
    }
}
