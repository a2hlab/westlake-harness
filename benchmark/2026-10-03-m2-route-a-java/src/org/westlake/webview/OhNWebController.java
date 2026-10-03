package org.westlake.webview;

import android.net.Uri;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.ByteArrayInputStream;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Route-a WebView logic: the render core (construct / settings / clients / load / evaluateJavascript /
 * addJavascriptInterface) forwarded to an {@link NWebBackend}, plus the native->Java callback translation
 * (implements {@link NWebCallbackSink}) into the app's {@link WebViewClient} / {@link WebChromeClient} on the
 * hosted {@link WebView}. {@link OhNWebProvider} (the android.webkit.WebViewProvider skeleton) is a thin adapter
 * over this; this class holds all the behaviour so it is unit-testable against a {@link MockNWebBackend}.
 *
 * Scope = the m2-webview-surface "render core (12)" + the Wikipedia open-an-article callbacks
 * (shouldInterceptRequest / onPageFinished / shouldOverrideUrlLoading / onProgressChanged).
 */
public final class OhNWebController implements NWebCallbackSink {

    private final NWebBackend backend;
    private long handle;

    private WebView webView;                 // the hosted WebView (callback target; may be null in unit tests)
    private WebViewClient webViewClient;
    private WebChromeClient webChromeClient;

    private final Map<Integer, ValueCallback<String>> pendingEval = new ConcurrentHashMap<>();
    private final AtomicInteger evalSeq = new AtomicInteger(1);

    public OhNWebController(NWebBackend backend) {
        if (backend == null) throw new IllegalArgumentException("backend == null");
        this.backend = backend;
    }

    /** Create the NWeb instance for this WebView. bundlePath = the app's installed bundle (SetBundlePath). */
    public void init(WebView webView, String bundlePath, int width, int height, Object surface) {
        this.webView = webView;
        this.handle = backend.create(bundlePath, width, height, surface, this);
    }

    public long handle() { return handle; }
    public boolean isReady() { return handle != 0L; }

    // ---- render core: load ----
    public void loadUrl(String url) { backend.loadUrl(handle, url, null); }
    public void loadUrl(String url, Map<String, String> additionalHttpHeaders) {
        backend.loadUrl(handle, url, additionalHttpHeaders);
    }
    public void loadDataWithBaseURL(String baseUrl, String data, String mimeType, String encoding, String historyUrl) {
        backend.loadDataWithBaseURL(handle, baseUrl, data, mimeType, encoding, historyUrl);
    }
    public void loadData(String data, String mimeType, String encoding) {
        backend.loadData(handle, data, mimeType, encoding);
    }
    public void postUrl(String url, byte[] postData) { backend.postUrl(handle, url, postData); }

    // ---- render core: script bridge ----
    public void evaluateJavascript(String script, ValueCallback<String> resultCallback) {
        int id = evalSeq.getAndIncrement();
        if (resultCallback != null) pendingEval.put(id, resultCallback);
        backend.evaluateJavascript(handle, script, id);
    }
    public void addJavascriptInterface(Object object, String name) { backend.addJavascriptInterface(handle, object, name); }
    public void removeJavascriptInterface(String name) { backend.removeJavascriptInterface(handle, name); }

    // ---- render core: settings (driven by OhNWebSettings) ----
    public void setJavaScriptEnabled(boolean enabled) { backend.setJavaScriptEnabled(handle, enabled); }
    public void setDomStorageEnabled(boolean enabled) { backend.setDomStorageEnabled(handle, enabled); }

    // ---- render core: clients + nav + lifecycle ----
    public void setWebViewClient(WebViewClient client) { this.webViewClient = client; }
    public WebViewClient getWebViewClient() { return webViewClient; }
    public void setWebChromeClient(WebChromeClient client) { this.webChromeClient = client; }
    public WebChromeClient getWebChromeClient() { return webChromeClient; }

    public void reload() { backend.reload(handle); }
    public void stopLoading() { backend.stopLoading(handle); }
    public boolean canGoBack() { return backend.canGoBack(handle); }
    public void goBack() { backend.goBack(handle); }
    public void onPause() { backend.onPause(handle); }
    public void onResume() { backend.onResume(handle); }
    public void draw(Object canvas, int width, int height) { backend.drawFrame(handle, canvas, width, height); }
    public void destroy() { backend.destroy(handle); handle = 0L; pendingEval.clear(); }

    // =========================== NWebCallbackSink (native -> Java) ===========================

    @Override public void onPageStarted(String url) {
        if (webViewClient != null) webViewClient.onPageStarted(webView, url, null);
    }
    @Override public void onPageFinished(String url) {
        if (webViewClient != null) webViewClient.onPageFinished(webView, url);
    }
    @Override public void onProgressChanged(int newProgress) {
        if (webChromeClient != null) webChromeClient.onProgressChanged(webView, newProgress);
    }
    @Override public void onReceivedTitle(String title) {
        if (webChromeClient != null) webChromeClient.onReceivedTitle(webView, title);
    }
    @Override
    public boolean shouldOverrideUrlLoading(String url, boolean isForMainFrame, boolean isRedirect,
                                            boolean hasUserGesture, String method, Map<String, String> headers) {
        if (webViewClient == null) return false;
        return webViewClient.shouldOverrideUrlLoading(webView,
                new NWebResourceRequest(url, isForMainFrame, isRedirect, hasUserGesture, method, headers));
    }
    @Override
    public InterceptedResponse shouldInterceptRequest(String url, boolean isForMainFrame, boolean isRedirect,
                                                      boolean hasUserGesture, String method, Map<String, String> headers) {
        if (webViewClient == null) return null;
        WebResourceResponse resp = webViewClient.shouldInterceptRequest(webView,
                new NWebResourceRequest(url, isForMainFrame, isRedirect, hasUserGesture, method, headers));
        return resp == null ? null : toIntercepted(resp);
    }
    @Override public void onEvaluateResult(int requestId, String jsonResult) {
        ValueCallback<String> cb = pendingEval.remove(requestId);
        if (cb != null) cb.onReceiveValue(jsonResult);
    }

    private static InterceptedResponse toIntercepted(WebResourceResponse r) {
        byte[] data = null;
        try {
            java.io.InputStream in = r.getData();
            if (in != null) {
                java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
                byte[] buf = new byte[8192]; int n;
                while ((n = in.read(buf)) > 0) bos.write(buf, 0, n);
                data = bos.toByteArray();
            }
        } catch (Exception ignore) { /* leave data null -> native fetches */ }
        return new InterceptedResponse(r.getMimeType(), r.getEncoding(), r.getStatusCode(),
                r.getReasonPhrase(), r.getResponseHeaders(), data);
    }

    /** Minimal {@link WebResourceRequest} (the AOSP type is an interface) for the client callbacks. */
    private static final class NWebResourceRequest implements WebResourceRequest {
        private final String url; private final boolean mainFrame, redirect, gesture; private final String method;
        private final Map<String, String> headers;
        NWebResourceRequest(String url, boolean mainFrame, boolean redirect, boolean gesture,
                            String method, Map<String, String> headers) {
            this.url = url; this.mainFrame = mainFrame; this.redirect = redirect; this.gesture = gesture;
            this.method = method == null ? "GET" : method;
            this.headers = headers == null ? Collections.emptyMap() : new LinkedHashMap<>(headers);
        }
        @Override public Uri getUrl() { return Uri.parse(url); }
        @Override public boolean isForMainFrame() { return mainFrame; }
        @Override public boolean isRedirect() { return redirect; }
        @Override public boolean hasGesture() { return gesture; }
        @Override public String getMethod() { return method; }
        @Override public Map<String, String> getRequestHeaders() { return headers; }
    }

    // Convenience for the real backend path / tests: build a WebResourceResponse from an InterceptedResponse.
    public static WebResourceResponse toWebResourceResponse(InterceptedResponse r) {
        if (r == null) return null;
        WebResourceResponse out = new WebResourceResponse(r.mimeType, r.encoding,
                new ByteArrayInputStream(r.data == null ? new byte[0] : r.data));
        if (r.statusCode > 0) out.setStatusCodeAndReasonPhrase(r.statusCode,
                r.reasonPhrase == null ? "OK" : r.reasonPhrase);
        if (r.responseHeaders != null) out.setResponseHeaders(r.responseHeaders);
        return out;
    }
}
