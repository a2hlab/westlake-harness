package org.westlake.webview;

import android.webkit.*;
import android.graphics.*;
import android.graphics.drawable.*;
import android.view.*;
import android.os.*;
import android.net.*;
import android.content.*;
import android.util.*;
import android.print.*;
import java.util.*;

/** android.webkit.WebViewProvider skeleton (route-a). Render core -> OhNWebController; ViewDelegate.onDraw
 *  -> NWeb frame blit; everything else a typed stub. Generated against AOSP android-14 WebViewProvider. */
public final class OhNWebProvider implements WebViewProvider {
    private final OhNWebController mController;
    private final OhNWebSettings mSettings;
    private final String mBundlePath;
    private String mUrl; private int mProgress;
    private final ViewDelegate mViewDelegate = new OhViewDelegate();
    private final ScrollDelegate mScrollDelegate = new OhScrollDelegate();
    public OhNWebProvider(OhNWebController controller, String bundlePath) {
        this.mController = controller; this.mBundlePath = bundlePath; this.mSettings = new OhNWebSettings(controller);
    }
    @Override public void init(Map<String, Object> javaScriptInterfaces,
            boolean privateBrowsing) { mController.init(null, mBundlePath, 0, 0, null); for (Map.Entry<String,Object> e : (javaScriptInterfaces==null? java.util.Collections.<String,Object>emptyMap(): javaScriptInterfaces).entrySet()) mController.addJavascriptInterface(e.getValue(), e.getKey()); }
    @Override public void setHorizontalScrollbarOverlay(boolean overlay) {  }
    @Override public void setVerticalScrollbarOverlay(boolean overlay) {  }
    @Override public boolean overlayHorizontalScrollbar() { return false; }
    @Override public boolean overlayVerticalScrollbar() { return false; }
    @Override public int getVisibleTitleHeight() { return 0; }
    @Override public SslCertificate getCertificate() { return null; }
    @Override public void setCertificate(SslCertificate certificate) {  }
    @Override public void savePassword(String host, String username, String password) {  }
    @Override public void setHttpAuthUsernamePassword(String host, String realm,
            String username, String password) {  }
    @Override public String[] getHttpAuthUsernamePassword(String host, String realm) { return null; }
    @Override public void destroy() { mController.destroy(); }
    @Override public void setNetworkAvailable(boolean networkUp) {  }
    @Override public WebBackForwardList saveState(Bundle outState) { return null; }
    @Override public boolean savePicture(Bundle b, final File dest) { return false; }
    @Override public boolean restorePicture(Bundle b, File src) { return false; }
    @Override public WebBackForwardList restoreState(Bundle inState) { return null; }
    @Override public void loadUrl(String url, Map<String, String> additionalHttpHeaders) { mController.loadUrl(url, additionalHttpHeaders); }
    @Override public void loadUrl(String url) { mController.loadUrl(url); }
    @Override public void postUrl(String url, byte[] postData) {  }
    @Override public void loadData(String data, String mimeType, String encoding) { mController.loadData(data, mimeType, encoding); }
    @Override public void loadDataWithBaseURL(String baseUrl, String data,
            String mimeType, String encoding, String historyUrl) { mController.loadDataWithBaseURL(baseUrl, data, mimeType, encoding, historyUrl); }
    @Override public void evaluateJavaScript(String script, ValueCallback<String> resultCallback) { mController.evaluateJavascript(script, resultCallback); }
    @Override public void saveWebArchive(String filename) {  }
    @Override public void saveWebArchive(String basename, boolean autoname, ValueCallback<String> callback) {  }
    @Override public void stopLoading() { mController.stopLoading(); }
    @Override public void reload() { mController.reload(); }
    @Override public boolean canGoBack() { return mController.canGoBack(); }
    @Override public void goBack() { mController.goBack(); }
    @Override public boolean canGoForward() { return false; }
    @Override public void goForward() {  }
    @Override public boolean canGoBackOrForward(int steps) { return false; }
    @Override public void goBackOrForward(int steps) {  }
    @Override public boolean isPrivateBrowsingEnabled() { return false; }
    @Override public boolean pageUp(boolean top) { return false; }
    @Override public boolean pageDown(boolean bottom) { return false; }
    @Override public void insertVisualStateCallback(long requestId, VisualStateCallback callback) {  }
    @Override public void clearView() {  }
    @Override public Picture capturePicture() { return null; }
    @Override public PrintDocumentAdapter createPrintDocumentAdapter(String documentName) { return null; }
    @Override public float getScale() { return 0; }
    @Override public void setInitialScale(int scaleInPercent) {  }
    @Override public void invokeZoomPicker() {  }
    @Override public HitTestResult getHitTestResult() { return null; }
    @Override public void requestFocusNodeHref(Message hrefMsg) {  }
    @Override public void requestImageRef(Message msg) {  }
    @Override public String getUrl() { return mUrl; }
    @Override public String getOriginalUrl() { return null; }
    @Override public String getTitle() { return null; }
    @Override public Bitmap getFavicon() { return null; }
    @Override public String getTouchIconUrl() { return null; }
    @Override public int getProgress() { return mProgress; }
    @Override public int getContentHeight() { return 0; }
    @Override public int getContentWidth() { return 0; }
    @Override public void pauseTimers() {  }
    @Override public void resumeTimers() {  }
    @Override public void onPause() { mController.onPause(); }
    @Override public void onResume() { mController.onResume(); }
    @Override public boolean isPaused() { return false; }
    @Override public void freeMemory() {  }
    @Override public void clearCache(boolean includeDiskFiles) {  }
    @Override public void clearFormData() {  }
    @Override public void clearHistory() {  }
    @Override public void clearSslPreferences() {  }
    @Override public WebBackForwardList copyBackForwardList() { return null; }
    @Override public void setFindListener(WebView.FindListener listener) {  }
    @Override public void findNext(boolean forward) {  }
    @Override public int findAll(String find) { return 0; }
    @Override public void findAllAsync(String find) {  }
    @Override public boolean showFindDialog(String text, boolean showIme) { return false; }
    @Override public void clearMatches() {  }
    @Override public void documentHasImages(Message response) {  }
    @Override public void setWebViewClient(WebViewClient client) { mController.setWebViewClient(client); }
    @Override public WebViewClient getWebViewClient() { return mController.getWebViewClient(); }
    @Override public WebViewRenderProcess getWebViewRenderProcess() { return null; }
    @Override public void setWebViewRenderProcessClient(Executor executor,
            WebViewRenderProcessClient client) {  }
    @Override public WebViewRenderProcessClient getWebViewRenderProcessClient() { return null; }
    @Override public void setDownloadListener(DownloadListener listener) {  }
    @Override public void setWebChromeClient(WebChromeClient client) { mController.setWebChromeClient(client); }
    @Override public WebChromeClient getWebChromeClient() { return mController.getWebChromeClient(); }
    @Override public void setPictureListener(PictureListener listener) {  }
    @Override public void addJavascriptInterface(Object obj, String interfaceName) { mController.addJavascriptInterface(obj, interfaceName); }
    @Override public void removeJavascriptInterface(String interfaceName) { mController.removeJavascriptInterface(interfaceName); }
    @Override public WebMessagePort[] createWebMessageChannel() { return null; }
    @Override public void postMessageToMainFrame(WebMessage message, Uri targetOrigin) {  }
    @Override public WebSettings getSettings() { return mSettings; }
    @Override public void setMapTrackballToArrowKeys(boolean setMap) {  }
    @Override public void flingScroll(int vx, int vy) {  }
    @Override public View getZoomControls() { return null; }
    @Override public boolean canZoomIn() { return false; }
    @Override public boolean canZoomOut() { return false; }
    @Override public boolean zoomBy(float zoomFactor) { return false; }
    @Override public boolean zoomIn() { return false; }
    @Override public boolean zoomOut() { return false; }
    @Override public void dumpViewHierarchyWithProperties(BufferedWriter out, int level) {  }
    @Override public View findHierarchyView(String className, int hashCode) { return null; }
    @Override public void setRendererPriorityPolicy(int rendererRequestedPriority, boolean waivedWhenNotVisible) {  }
    @Override public int getRendererRequestedPriority() { return 0; }
    @Override public boolean getRendererPriorityWaivedWhenNotVisible() { return false; }
    @Override public ViewDelegate getViewDelegate() { return null; }
    @Override public ScrollDelegate getScrollDelegate() { return null; }
    @Override public void notifyFindDialogDismissed() {  }
    public ViewDelegate getViewDelegate() { return mViewDelegate; }
    public ScrollDelegate getScrollDelegate() { return mScrollDelegate; }

    private final class OhViewDelegate implements ViewDelegate {
        @Override public boolean shouldDelayChildPressedState() { return false; }
        @Override public void onProvideVirtualStructure(android.view.ViewStructure structure) {  }
        @Override public AccessibilityNodeProvider getAccessibilityNodeProvider() { return null; }
        @Override public void onInitializeAccessibilityNodeInfo(AccessibilityNodeInfo info) {  }
        @Override public void onInitializeAccessibilityEvent(AccessibilityEvent event) {  }
        @Override public boolean performAccessibilityAction(int action, Bundle arguments) { return false; }
        @Override public void setOverScrollMode(int mode) {  }
        @Override public void setScrollBarStyle(int style) {  }
        @Override public void onDrawVerticalScrollBar(Canvas canvas, Drawable scrollBar, int l, int t,
                int r, int b) {  }
        @Override public void onOverScrolled(int scrollX, int scrollY, boolean clampedX, boolean clampedY) {  }
        @Override public void onWindowVisibilityChanged(int visibility) {  }
        @Override public void onDraw(Canvas canvas) { mController.draw(canvas, 0, 0); }
        @Override public void setLayoutParams(LayoutParams layoutParams) {  }
        @Override public boolean performLongClick() { return false; }
        @Override public void onConfigurationChanged(Configuration newConfig) {  }
        @Override public InputConnection onCreateInputConnection(EditorInfo outAttrs) { return null; }
        @Override public boolean onDragEvent(DragEvent event) { return false; }
        @Override public boolean onKeyMultiple(int keyCode, int repeatCount, KeyEvent event) { return false; }
        @Override public boolean onKeyDown(int keyCode, KeyEvent event) { return false; }
        @Override public boolean onKeyUp(int keyCode, KeyEvent event) { return false; }
        @Override public void onAttachedToWindow() {  }
        @Override public void onDetachedFromWindow() {  }
        @Override public void onVisibilityChanged(View changedView, int visibility) {  }
        @Override public void onWindowFocusChanged(boolean hasWindowFocus) {  }
        @Override public void onFocusChanged(boolean focused, int direction, Rect previouslyFocusedRect) {  }
        @Override public boolean setFrame(int left, int top, int right, int bottom) { return false; }
        @Override public void onSizeChanged(int w, int h, int ow, int oh) {  }
        @Override public void onScrollChanged(int l, int t, int oldl, int oldt) {  }
        @Override public boolean dispatchKeyEvent(KeyEvent event) { return false; }
        @Override public boolean onTouchEvent(MotionEvent ev) { return false; }
        @Override public boolean onHoverEvent(MotionEvent event) { return false; }
        @Override public boolean onGenericMotionEvent(MotionEvent event) { return false; }
        @Override public boolean onTrackballEvent(MotionEvent ev) { return false; }
        @Override public boolean requestFocus(int direction, Rect previouslyFocusedRect) { return false; }
        @Override public void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {  }
        @Override public boolean requestChildRectangleOnScreen(View child, Rect rect, boolean immediate) { return false; }
        @Override public void setBackgroundColor(int color) {  }
        @Override public void setLayerType(int layerType, Paint paint) {  }
        @Override public void preDispatchDraw(Canvas canvas) {  }
        @Override public void onStartTemporaryDetach() {  }
        @Override public void onFinishTemporaryDetach() {  }
        @Override public void onActivityResult(int requestCode, int resultCode, Intent data) {  }
        @Override public Handler getHandler(Handler originalHandler) { return null; }
        @Override public View findFocus(View originalFocusedView) { return null; }
    }

    private final class OhScrollDelegate implements ScrollDelegate {
        @Override public int computeHorizontalScrollRange() { return 0; }
        @Override public int computeHorizontalScrollOffset() { return 0; }
        @Override public int computeVerticalScrollRange() { return 0; }
        @Override public int computeVerticalScrollOffset() { return 0; }
        @Override public int computeVerticalScrollExtent() { return 0; }
        @Override public void computeScroll() {  }
    }
}
