package org.westlake.webview;

import java.util.Map;

/**
 * Native -> Java callbacks from the NWeb backend. Deliberately free of any {@code android.webkit.*} type so the
 * backend (and its JNI/mock impls) do not depend on the Android framework. {@link OhNWebController} implements
 * this and translates each call into the app's {@link android.webkit.WebViewClient} /
 * {@link android.webkit.WebChromeClient} on the hosted {@code WebView}.
 *
 * The backend invokes these from NWeb's handler (cc-t3 A0: the {@code NWebHandler} registered via
 * {@code NWeb::RegisterNWebHandler}). The subset here is exactly what "open a Wikipedia article" needs:
 * page lifecycle, progress, url-override and resource-intercept (Wikipedia serves its page template + pagelib
 * CSS/JS locally via shouldInterceptRequest), title, and evaluateJavascript results.
 */
public interface NWebCallbackSink {

    /** NWebHandler::OnPageLoadBegin */
    void onPageStarted(String url);

    /** NWebHandler::OnPageLoadEnd */
    void onPageFinished(String url);

    /** NWebHandler::OnLoadingProgress (0..100) */
    void onProgressChanged(int newProgress);

    /** NWebHandler::OnReceivedTitle */
    void onReceivedTitle(String title);

    /**
     * NWebHandler url-load policy. Maps to {@code WebViewClient.shouldOverrideUrlLoading}.
     * @return true if the host consumed the navigation (NWeb must not load it).
     */
    boolean shouldOverrideUrlLoading(String url, boolean isForMainFrame, boolean isRedirect,
                                     boolean hasUserGesture, String method, Map<String, String> requestHeaders);

    /**
     * NWebHandler resource interception. Maps to {@code WebViewClient.shouldInterceptRequest}.
     * @return a response to serve locally, or null to let NWeb fetch the resource.
     */
    InterceptedResponse shouldInterceptRequest(String url, boolean isForMainFrame, boolean isRedirect,
                                               boolean hasUserGesture, String method, Map<String, String> requestHeaders);

    /** Result of {@code evaluateJavascript} (NWeb::ExecuteJavaScript callback), matched by requestId. */
    void onEvaluateResult(int requestId, String jsonResult);

    /**
     * Android-free carrier for a shouldInterceptRequest reply. {@link OhNWebController} converts it to an
     * {@code android.webkit.WebResourceResponse} for the WebViewClient, and converts a WebResourceResponse the
     * client returns back into this for the backend. Keeps android.webkit out of the backend/mock.
     */
    final class InterceptedResponse {
        public final String mimeType;
        public final String encoding;
        public final int statusCode;
        public final String reasonPhrase;
        public final Map<String, String> responseHeaders;
        public final byte[] data;

        public InterceptedResponse(String mimeType, String encoding, int statusCode, String reasonPhrase,
                                   Map<String, String> responseHeaders, byte[] data) {
            this.mimeType = mimeType;
            this.encoding = encoding;
            this.statusCode = statusCode;
            this.reasonPhrase = reasonPhrase;
            this.responseHeaders = responseHeaders;
            this.data = data;
        }
    }
}
