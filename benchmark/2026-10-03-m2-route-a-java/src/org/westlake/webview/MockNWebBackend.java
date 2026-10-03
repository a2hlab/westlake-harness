package org.westlake.webview;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Pure-Java mock backend: records every {@link NWebBackend} call and synthesises the NWeb handler callbacks that
 * the real native layer would emit, so the Java side (controller + callback dispatch) unit-tests offline with no
 * native library and no Android runtime. It is deliberately free of {@code android.webkit.*}.
 *
 * "Open an article" synthesis: on any load*, it drives the sink through
 * onPageStarted -> shouldInterceptRequest(a pagelib asset) -> onProgressChanged(100) -> onReceivedTitle ->
 * onPageFinished, mirroring how Wikipedia serves its page template + pagelib CSS/JS locally via interception.
 * evaluateJavascript drives onEvaluateResult(requestId, scripted value).
 */
public final class MockNWebBackend implements NWebBackend {

    public static final class Call {
        public final String op; public final Object[] args;
        public Call(String op, Object... args) { this.op = op; this.args = args; }
        @Override public String toString() { return op + java.util.Arrays.deepToString(args); }
    }

    public final List<Call> calls = new ArrayList<>();
    /** Captured return of the last synthesised shouldInterceptRequest (null if the sink declined). */
    public NWebCallbackSink.InterceptedResponse lastIntercepted;
    /** Scripted result string the mock returns for evaluateJavascript. */
    public String scriptedEvalResult = "null";

    private long nextHandle = 1;
    private final Map<Long, NWebCallbackSink> sinks = new LinkedHashMap<>();
    private boolean engineInitialised = false;

    private void record(String op, Object... a) { calls.add(new Call(op, a)); }
    public List<Call> opsNamed(String op) {
        List<Call> r = new ArrayList<>();
        for (Call c : calls) if (c.op.equals(op)) r.add(c);
        return Collections.unmodifiableList(r);
    }
    public boolean sawOp(String op) { return !opsNamed(op).isEmpty(); }

    @Override
    public long create(String bundlePath, int width, int height, Object surface, NWebCallbackSink sink) {
        engineInitialised = true;
        record("create", bundlePath, width, height);
        long h = nextHandle++;
        sinks.put(h, sink);
        return h;
    }

    public boolean engineInitialised() { return engineInitialised; }

    private void synthesisePageLoad(long handle, String url, String baseForAssets) {
        NWebCallbackSink sink = sinks.get(handle);
        if (sink == null) return;
        sink.onPageStarted(url);
        // Wikipedia pulls pagelib assets relative to the base URL; the app serves them via shouldInterceptRequest.
        String asset = (baseForAssets == null ? "" : baseForAssets) + "assets/pagelib/wikimedia-page-library.css";
        Map<String, String> hdrs = new LinkedHashMap<>();
        hdrs.put("Accept", "text/css");
        lastIntercepted = sink.shouldInterceptRequest(asset, false, false, false, "GET", hdrs);
        sink.onProgressChanged(100);
        sink.onReceivedTitle("Article");
        sink.onPageFinished(url);
    }

    @Override
    public void loadUrl(long handle, String url, Map<String, String> additionalHttpHeaders) {
        record("loadUrl", handle, url, additionalHttpHeaders);
        synthesisePageLoad(handle, url, null);
    }

    @Override
    public void loadDataWithBaseURL(long handle, String baseUrl, String data, String mimeType,
                                    String encoding, String historyUrl) {
        record("loadDataWithBaseURL", handle, baseUrl, mimeType, encoding, historyUrl);
        synthesisePageLoad(handle, historyUrl != null ? historyUrl : baseUrl, baseUrl);
    }

    @Override
    public void loadData(long handle, String data, String mimeType, String encoding) {
        record("loadData", handle, mimeType, encoding);
        synthesisePageLoad(handle, "data:" + mimeType, null);
    }

    @Override public void postUrl(long handle, String url, byte[] postData) { record("postUrl", handle, url); }

    @Override
    public void evaluateJavascript(long handle, String script, int requestId) {
        record("evaluateJavascript", handle, script, requestId);
        NWebCallbackSink sink = sinks.get(handle);
        if (sink != null) sink.onEvaluateResult(requestId, scriptedEvalResult);
    }

    @Override public void setJavaScriptEnabled(long handle, boolean enabled) { record("setJavaScriptEnabled", handle, enabled); }
    @Override public void setDomStorageEnabled(long handle, boolean enabled) { record("setDomStorageEnabled", handle, enabled); }
    @Override public void addJavascriptInterface(long handle, Object object, String name) { record("addJavascriptInterface", handle, name); }
    @Override public void removeJavascriptInterface(long handle, String name) { record("removeJavascriptInterface", handle, name); }
    @Override public void reload(long handle) { record("reload", handle); }
    @Override public void stopLoading(long handle) { record("stopLoading", handle); }
    @Override public boolean canGoBack(long handle) { record("canGoBack", handle); return false; }
    @Override public void goBack(long handle) { record("goBack", handle); }
    @Override public void onPause(long handle) { record("onPause", handle); }
    @Override public void onResume(long handle) { record("onResume", handle); }
    @Override public void drawFrame(long handle, Object canvas, int width, int height) { record("drawFrame", handle, width, height); }
    @Override public void destroy(long handle) { record("destroy", handle); sinks.remove(handle); }
}
