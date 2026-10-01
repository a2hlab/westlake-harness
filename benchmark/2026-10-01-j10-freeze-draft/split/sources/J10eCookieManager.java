/* J10e (#webview-cookiemanager): single-purpose freeze unit -- concrete empty CookieManager.
 * Split out of J10eWebView.java (was J10eWebView$WlCookieManager), behaviour unchanged. Overrides all
 * 16 abstract methods incl. the two @hide @SystemApi (getCookie(String,boolean), hasCookies(boolean)). */
package adapter.activity;

import android.webkit.CookieManager;
import android.webkit.ValueCallback;
import android.webkit.WebView;

public final class J10eCookieManager extends CookieManager {
    @Override public void setAcceptCookie(boolean accept) {}
    @Override public boolean acceptCookie() { return true; }
    @Override public void setAcceptThirdPartyCookies(WebView webview, boolean accept) {}
    @Override public boolean acceptThirdPartyCookies(WebView webview) { return false; }
    @Override public void setCookie(String url, String value) {}
    @Override public void setCookie(String url, String value, ValueCallback<Boolean> callback) {}
    @Override public String getCookie(String url) { return null; }
    @Override public String getCookie(String url, boolean privateBrowsing) { return null; } // @hide
    @Override public void removeSessionCookie() {}
    @Override public void removeSessionCookies(ValueCallback<Boolean> callback) {}
    @Override public void removeAllCookie() {}
    @Override public void removeAllCookies(ValueCallback<Boolean> callback) {}
    @Override public boolean hasCookies() { return false; }
    @Override public boolean hasCookies(boolean privateBrowsing) { return false; } // @hide
    @Override public void removeExpiredCookie() {}
    @Override public void flush() {}
}
