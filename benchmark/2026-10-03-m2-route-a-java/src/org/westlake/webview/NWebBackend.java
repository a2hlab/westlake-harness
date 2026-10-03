package org.westlake.webview;

import java.util.Map;

/**
 * Route-a backend contract: the Java WebView provider drives OpenHarmony NWeb through this one interface.
 * Two implementations:
 *   - {@link NativeNWebBackend}: JNI into cc-t3's A0 ({@code NWebHelper::SetBundlePath/InitAndRun/CreateNWeb},
 *     {@code NWeb::Load.../ExecuteJavaScript}, {@code NWeb::RegisterNWebHandler}).
 *   - {@link MockNWebBackend}: pure-Java mock so the Java side unit-tests offline (no native, no Android).
 *
 * A {@code handle} is an opaque NWeb instance id (0 = no instance). All calls are no-ops on handle 0.
 */
public interface NWebBackend {

    /**
     * Create an NWeb instance for one WebView/window and register its handler.
     * cc-t3 A0: NWebHelper::SetBundlePath(bundlePath) + (first time) Instance()/Init()/LoadWebEngine()/InitAndRun(),
     * then CreateNWeb(NWebCreateInfo{width,height,surface,OutputFrameCallback}) + RegisterNWebHandler(sink-backed handler).
     * @return opaque handle, or 0 on failure.
     */
    long create(String bundlePath, int width, int height, Object surface, NWebCallbackSink sink);

    void loadUrl(long handle, String url, Map<String, String> additionalHttpHeaders);

    void loadDataWithBaseURL(long handle, String baseUrl, String data, String mimeType,
                             String encoding, String historyUrl);

    void loadData(long handle, String data, String mimeType, String encoding);

    void postUrl(long handle, String url, byte[] postData);

    /** NWeb::ExecuteJavaScript; the result is delivered via {@link NWebCallbackSink#onEvaluateResult}. */
    void evaluateJavascript(long handle, String script, int requestId);

    void setJavaScriptEnabled(long handle, boolean enabled);

    void setDomStorageEnabled(long handle, boolean enabled);

    void addJavascriptInterface(long handle, Object object, String name);

    void removeJavascriptInterface(long handle, String name);

    void reload(long handle);

    void stopLoading(long handle);

    boolean canGoBack(long handle);

    void goBack(long handle);

    void onPause(long handle);

    void onResume(long handle);

    /** Composite the current NWeb output frame onto the WebView canvas (NWebCreateInfo OutputFrameCallback -> blit). */
    void drawFrame(long handle, Object canvas, int width, int height);

    void destroy(long handle);
}
