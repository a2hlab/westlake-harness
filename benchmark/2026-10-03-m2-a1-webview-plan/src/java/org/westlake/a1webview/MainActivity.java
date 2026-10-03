package org.westlake.a1webview;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/** M2 A1 test app (test-only): a real android.webkit.WebView filling the content area, backed by cc-wiki's route-a
 *  WebView provider (overlaid at window time: oh-adapter-runtime.jar + shim/worker .so). No hand-written NWeb and no app
 *  native lib — this exercises the REAL WebView path end-to-end. Two load modes, selected at launch:
 *   - default: loadDataWithBaseURL the #12ab34 data: page (A1 data window; needs no param).
 *   - URL: intent extra "wl_url" (aa start --ps wl_url <url>) OR SystemProperties debug.westlake.a1.url -> loadUrl
 *          (A1 Wikipedia window). */
public class MainActivity extends Activity {

    static final String HTML =
        "<!doctype html><html><head><meta charset='utf-8'>"
        + "<meta name='viewport' content='width=device-width,initial-scale=1'></head>"
        + "<body id='b' style='margin:0;height:100vh;background:#ffffff'>"
        + "<h1 style='font-size:48px'>中文 A1 WebView</h1>"
        + "<script>document.getElementById('b').style.background='#12ab34';"
        + "document.documentElement.style.background='#12ab34';console.log('A1 JS ran');</script>"
        + "</body></html>";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        WebView wv = new WebView(this);
        WebSettings s = wv.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setLoadsImagesAutomatically(true);
        wv.setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView v, String url) {
                System.err.println("[A1-JAVA] onPageFinished " + url);
            }
            @Override public void onReceivedError(WebView v, WebResourceRequest req, WebResourceError err) {
                System.err.println("[A1-JAVA] onReceivedError " + err);
            }
        });
        setContentView(wv);
        String url = resolveUrl();
        if (url != null && !url.isEmpty()) {
            System.err.println("[A1-JAVA] loadUrl " + url);
            wv.loadUrl(url);
        } else {
            System.err.println("[A1-JAVA] loadData #12ab34 page");
            wv.loadDataWithBaseURL("https://a1.local/", HTML, "text/html", "utf-8", null);
        }
    }

    /** Intent extra first (aa start --ps wl_url <url> -> Want param -> Intent extra on route-a), then the OH/Android
     *  system property via reflection; empty -> the data: page. */
    private String resolveUrl() {
        try {
            if (getIntent() != null) {
                String u = getIntent().getStringExtra("wl_url");
                if (u != null && !u.isEmpty()) return u;
            }
        } catch (Throwable t) { /* fall through */ }
        try {
            Class<?> sp = Class.forName("android.os.SystemProperties");
            String u = (String) sp.getMethod("get", String.class, String.class)
                    .invoke(null, "debug.westlake.a1.url", "");
            if (u != null && !u.isEmpty()) return u;
        } catch (Throwable t) { /* fall through */ }
        return null;
    }
}
