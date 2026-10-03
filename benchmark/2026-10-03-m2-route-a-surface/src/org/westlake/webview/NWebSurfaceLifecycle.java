package org.westlake.webview;

/**
 * M2 route-a surface lifecycle (Option A: a SurfaceView hosted inside the WebView supplies the NWeb producer surface).
 *
 * This is the android-free core of {@link OhNWebSurfaceHost}: it decides WHEN to create / resize / destroy the NWeb
 * instance from the SurfaceView's SurfaceHolder.Callback events, and holds the backend handle. Keeping it free of
 * android.view.* makes it unit-testable offline with {@link MockNWebBackend} and a plain Object as the surface.
 *
 * Why Option A (see benchmark/2026-10-03-m2-route-a-surface/README.md): our runtime does NOT composite a bare window
 * node's own surface (cc-t3 window14); only a self-drawing child RSSurfaceNode AddChild'd under the window node is
 * GPU-composited. A SurfaceView already gets exactly such a node — the [STAGE2-SURFACEVIEW] path
 * (android_graphics_compat_shim -> oh_rs_get_child_surface_window -> "AdapterSurfaceView") — which FlutterSurfaceView
 * uses and on which U14's Flutter EGL fix produced a non-zero EGLSurface. So the provider hosts a SurfaceView in the
 * WebView (a ViewGroup) and hands NWeb that holder's Surface; the View framework syncs position/size/visibility/z-order
 * for free.
 *
 * Lifecycle contract (mirrors SurfaceHolder.Callback), the key correctness points:
 *   - NWeb is created ONLY after the surface exists (onSurfaceReady), never before — this avoids the M3-cluster EGL
 *     IllegalArgumentException "the SurfaceView/SurfaceHolder has a valid Surface" that bit GLSurfaceView apps that
 *     touched EGL before surfaceCreated.
 *   - a size change before creation just updates the pending extent; after creation it drives drawFrame/resize.
 *   - onSurfaceLost destroys the handle; a later onSurfaceReady recreates it (surface identity can change).
 */
public final class NWebSurfaceLifecycle {

    private final NWebBackend backend;
    private final NWebCallbackSink sink;
    private final String bundlePath;

    private long handle = 0L;          // 0 = no NWeb instance
    private int width, height;
    private boolean jsEnabled = true, domStorageEnabled = true;
    private String pendingUrl;         // a loadUrl requested before the surface was ready

    public NWebSurfaceLifecycle(NWebBackend backend, NWebCallbackSink sink, String bundlePath) {
        if (backend == null) throw new IllegalArgumentException("backend");
        this.backend = backend;
        this.sink = sink;
        this.bundlePath = bundlePath;
    }

    public long handle() { return handle; }
    public boolean isActive() { return handle != 0L; }

    /** SurfaceHolder.Callback#surfaceCreated — create the NWeb instance on the (now-live) SurfaceView child surface. */
    public synchronized long onSurfaceReady(Object surface, int w, int h) {
        this.width = w > 0 ? w : this.width;
        this.height = h > 0 ? h : this.height;
        if (handle != 0L) return handle;                 // already created for this surface
        handle = backend.create(bundlePath, this.width, this.height, surface, sink);
        if (handle != 0L) {
            backend.setJavaScriptEnabled(handle, jsEnabled);
            backend.setDomStorageEnabled(handle, domStorageEnabled);
            if (pendingUrl != null) { backend.loadUrl(handle, pendingUrl, null); pendingUrl = null; }
        }
        return handle;
    }

    /** SurfaceHolder.Callback#surfaceChanged — new geometry on the same surface. */
    public synchronized void onSurfaceChanged(int w, int h) {
        this.width = w; this.height = h;
        if (handle != 0L) backend.drawFrame(handle, null, w, h);   // nativeOnDraw resizes the NWeb to the new extent
    }

    /** SurfaceHolder.Callback#surfaceDestroyed — tear the NWeb instance down; it is recreated on the next surface. */
    public synchronized void onSurfaceLost() {
        if (handle != 0L) { backend.destroy(handle); handle = 0L; }
    }

    // --- settings/navigation that must survive a create (applied at onSurfaceReady) or forward immediately ---
    public synchronized void setJavaScriptEnabled(boolean e) {
        jsEnabled = e; if (handle != 0L) backend.setJavaScriptEnabled(handle, e);
    }
    public synchronized void setDomStorageEnabled(boolean e) {
        domStorageEnabled = e; if (handle != 0L) backend.setDomStorageEnabled(handle, e);
    }
    public synchronized void loadUrl(String url, java.util.Map<String, String> headers) {
        if (handle != 0L) backend.loadUrl(handle, url, headers);
        else pendingUrl = url;                             // defer until the surface (and NWeb) exist
    }
    public synchronized void onPause() { if (handle != 0L) backend.onPause(handle); }
    public synchronized void onResume() { if (handle != 0L) backend.onResume(handle); }
}
