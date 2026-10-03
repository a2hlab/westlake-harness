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

/** android.webkit.WebViewFactoryProvider skeleton: createWebView -> OhNWebProvider (backed by NWeb).
 *  Seeded into WebViewFactory.sProviderInstance by OhNWebProviderFix.install(). */
public final class OhNWebFactoryProvider implements WebViewFactoryProvider {
    private final NWebBackend mBackend;
    public OhNWebFactoryProvider() { this(new NativeNWebBackend()); }
    public OhNWebFactoryProvider(NWebBackend backend) { this.mBackend = backend; }
    private static String bundlePathForCurrentApp() { return System.getProperty("westlake.bundle.path", ""); }
    @Override public Statics getStatics() { return new OhStatics(); }
    @Override public WebViewProvider createWebView(WebView webView, WebView.PrivateAccess privateAccess) { OhNWebController c = new OhNWebController(mBackend); return new OhNWebProvider(c, bundlePathForCurrentApp()); }
    @Override public GeolocationPermissions getGeolocationPermissions() { return null; }
    @Override public CookieManager getCookieManager() { return null; }
    @Override public TokenBindingService getTokenBindingService() { return null; }
    @Override public TracingController getTracingController() { return null; }
    @Override public ServiceWorkerController getServiceWorkerController() { return null; }
    @Override public WebIconDatabase getWebIconDatabase() { return null; }
    @Override public WebStorage getWebStorage() { return null; }
    @Override public WebViewDatabase getWebViewDatabase(Context context) { return null; }
    @Override public ClassLoader getWebViewClassLoader() { return null; }
    private static final class OhStatics implements Statics {
        @Override public String findAddress(String addr) { return null; }
        @Override public String getDefaultUserAgent(Context context) { return null; }
        @Override public void freeMemoryForTests() {  }
        @Override public void setWebContentsDebuggingEnabled(boolean enable) {  }
        @Override public void clearClientCertPreferences(Runnable onCleared) {  }
        @Override public void enableSlowWholeDocumentDraw() {  }
        @Override public Uri[] parseFileChooserResult(int resultCode, Intent intent) { return null; }
        @Override public void initSafeBrowsing(Context context, ValueCallback<Boolean> callback) {  }
        @Override public void setSafeBrowsingWhitelist(List<String> hosts, ValueCallback<Boolean> callback) {  }
        @Override public Uri getSafeBrowsingPrivacyPolicyUrl() { return null; }
    }
}
