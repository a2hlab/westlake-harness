package org.westlake.webview;

import java.util.Map;

/**
 * JNI backend: forwards {@link NWebBackend} to cc-t3's A0 native layer. This file declares ONLY the native
 * method signatures (the call surface cc-t3 implements in the .so via RegisterNatives); it has no native code.
 * The native layer upcalls the registered {@link NWebCallbackSink} directly (JNI CallXxxMethod on the sink
 * interface) for page/progress/intercept/evaluate callbacks — so no separate Java upcall entry points are needed.
 *
 * Native call surface (maps 1:1 to the A0 roadmap, benchmark/2026-10-03-m2-webview-roadmap):
 *   nativeInitEngine      <- NWebHelper::Instance()/Init()/SetBundlePath()/SetRenderProcessMode()/LoadWebEngine()/InitAndRun()
 *   nativeCreateNWeb      <- NWebHelper::CreateNWeb(NWebCreateInfo{width,height,surface,OutputFrameCallback})
 *   nativeRegisterHandler <- NWeb::RegisterNWebHandler(handler that upcalls the sink)
 *   nativeLoadUrl / nativeLoadWithDataAndBaseUrl / nativeLoadData / nativePostUrl <- NWeb::Load / LoadWithDataAndBaseUrl
 *   nativeExecuteJavaScript <- NWeb::ExecuteJavaScript(script, callbackId)
 *   nativeSet* / nativeReload / nativeStop / nativeGoBack / nativeOnPause/Resume / nativeOnDraw / nativeDestroy
 *
 * The .so is loaded by cc-t3's A0 (System.loadLibrary on the runtime side); this class does not load it so the
 * Java side builds/tests without the native library present. loadLibrary is left to the owner / a late static hook.
 */
public final class NativeNWebBackend implements NWebBackend {

    /** First-instance engine bring-up. Returns true once the engine is initialised and running. */
    private static native boolean nativeInitEngine(String bundlePath, int renderProcessMode);

    private static native long nativeCreateNWeb(int width, int height, Object surface);
    private static native void nativeRegisterHandler(long handle, NWebCallbackSink sink);

    private static native void nativeLoadUrl(long handle, String url, String[] headerKeys, String[] headerVals);
    private static native void nativeLoadWithDataAndBaseUrl(long handle, String baseUrl, String data,
                                                            String mimeType, String encoding, String historyUrl);
    private static native void nativeLoadData(long handle, String data, String mimeType, String encoding);
    private static native void nativePostUrl(long handle, String url, byte[] postData);
    private static native void nativeExecuteJavaScript(long handle, String script, int requestId);

    private static native void nativeSetJavaScriptEnabled(long handle, boolean enabled);
    private static native void nativeSetDomStorageEnabled(long handle, boolean enabled);
    private static native void nativeAddJavascriptInterface(long handle, Object object, String name);
    private static native void nativeRemoveJavascriptInterface(long handle, String name);

    private static native void nativeReload(long handle);
    private static native void nativeStopLoading(long handle);
    private static native boolean nativeCanGoBack(long handle);
    private static native void nativeGoBack(long handle);
    private static native void nativeOnPause(long handle);
    private static native void nativeOnResume(long handle);
    private static native void nativeOnDraw(long handle, Object canvas, int width, int height);
    private static native void nativeDestroy(long handle);

    /** 0 = default (likely multi-process); matches NWebHelper::SetRenderProcessMode. */
    private final int renderProcessMode;
    private static volatile boolean sEngineReady = false;

    public NativeNWebBackend() { this(0); }
    public NativeNWebBackend(int renderProcessMode) { this.renderProcessMode = renderProcessMode; }

    @Override
    public long create(String bundlePath, int width, int height, Object surface, NWebCallbackSink sink) {
        synchronized (NativeNWebBackend.class) {
            if (!sEngineReady) {
                sEngineReady = nativeInitEngine(bundlePath, renderProcessMode);
                if (!sEngineReady) return 0L;
            }
        }
        long handle = nativeCreateNWeb(width, height, surface);
        if (handle != 0L && sink != null) nativeRegisterHandler(handle, sink);
        return handle;
    }

    @Override
    public void loadUrl(long handle, String url, Map<String, String> additionalHttpHeaders) {
        if (handle == 0L) return;
        String[] k = null, v = null;
        if (additionalHttpHeaders != null && !additionalHttpHeaders.isEmpty()) {
            k = additionalHttpHeaders.keySet().toArray(new String[0]);
            v = new String[k.length];
            for (int i = 0; i < k.length; i++) v[i] = additionalHttpHeaders.get(k[i]);
        }
        nativeLoadUrl(handle, url, k, v);
    }

    @Override
    public void loadDataWithBaseURL(long handle, String baseUrl, String data, String mimeType,
                                    String encoding, String historyUrl) {
        if (handle != 0L) nativeLoadWithDataAndBaseUrl(handle, baseUrl, data, mimeType, encoding, historyUrl);
    }

    @Override public void loadData(long handle, String data, String mimeType, String encoding) {
        if (handle != 0L) nativeLoadData(handle, data, mimeType, encoding);
    }
    @Override public void postUrl(long handle, String url, byte[] postData) {
        if (handle != 0L) nativePostUrl(handle, url, postData);
    }
    @Override public void evaluateJavascript(long handle, String script, int requestId) {
        if (handle != 0L) nativeExecuteJavaScript(handle, script, requestId);
    }
    @Override public void setJavaScriptEnabled(long handle, boolean enabled) {
        if (handle != 0L) nativeSetJavaScriptEnabled(handle, enabled);
    }
    @Override public void setDomStorageEnabled(long handle, boolean enabled) {
        if (handle != 0L) nativeSetDomStorageEnabled(handle, enabled);
    }
    @Override public void addJavascriptInterface(long handle, Object object, String name) {
        if (handle != 0L) nativeAddJavascriptInterface(handle, object, name);
    }
    @Override public void removeJavascriptInterface(long handle, String name) {
        if (handle != 0L) nativeRemoveJavascriptInterface(handle, name);
    }
    @Override public void reload(long handle) { if (handle != 0L) nativeReload(handle); }
    @Override public void stopLoading(long handle) { if (handle != 0L) nativeStopLoading(handle); }
    @Override public boolean canGoBack(long handle) { return handle != 0L && nativeCanGoBack(handle); }
    @Override public void goBack(long handle) { if (handle != 0L) nativeGoBack(handle); }
    @Override public void onPause(long handle) { if (handle != 0L) nativeOnPause(handle); }
    @Override public void onResume(long handle) { if (handle != 0L) nativeOnResume(handle); }
    @Override public void drawFrame(long handle, Object canvas, int width, int height) {
        if (handle != 0L) nativeOnDraw(handle, canvas, width, height);
    }
    @Override public void destroy(long handle) { if (handle != 0L) nativeDestroy(handle); }
}
