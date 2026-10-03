import android.webkit.ValueCallback;
import org.westlake.webview.MockNWebBackend;
import org.westlake.webview.NWebCallbackSink;
import org.westlake.webview.OhNWebController;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Dependency-free unit test for the route-a Java side (no JUnit, no native, no Android runtime objects).
 * Run: java -cp out:test-out:<android.jar> NWebRouteATest
 *
 * It exercises the android-free seam (backend contract + mock callback synthesis + controller forwarding +
 * evaluateJavascript round-trip). The android.webkit translation (sink -> WebViewClient/WebChromeClient) is
 * compile-checked and left to the on-board test, since android.jar method bodies are runtime stubs.
 */
public final class NWebRouteATest {
    private static int checks = 0, fails = 0;
    private static void check(String name, boolean cond) {
        checks++;
        System.out.println((cond ? "  PASS " : "  FAIL ") + name);
        if (!cond) fails++;
    }

    /** Recording sink (plain Java) for the backend-contract test. */
    static final class RecordingSink implements NWebCallbackSink {
        final List<String> events = new ArrayList<>();
        InterceptedResponse interceptReturn;
        boolean interceptAsked = false;
        int lastProgress = -1; Integer evalId = null; String evalValue = null;
        public void onPageStarted(String url) { events.add("started:" + url); }
        public void onPageFinished(String url) { events.add("finished:" + url); }
        public void onProgressChanged(int p) { lastProgress = p; events.add("progress:" + p); }
        public void onReceivedTitle(String t) { events.add("title:" + t); }
        public boolean shouldOverrideUrlLoading(String url, boolean mf, boolean rd, boolean g, String m, Map<String,String> h) {
            events.add("override:" + url); return false;
        }
        public InterceptedResponse shouldInterceptRequest(String url, boolean mf, boolean rd, boolean g, String m, Map<String,String> h) {
            interceptAsked = true; events.add("intercept:" + url); return interceptReturn;
        }
        public void onEvaluateResult(int id, String v) { evalId = id; evalValue = v; events.add("eval:" + id + "=" + v); }
    }

    static void testBackendContractAndCallbacks() {
        System.out.println("[T1] MockNWebBackend drives the handler through an open-an-article sequence");
        MockNWebBackend mock = new MockNWebBackend();
        RecordingSink sink = new RecordingSink();
        sink.interceptReturn = new NWebCallbackSink.InterceptedResponse(
                "text/css", "UTF-8", 200, "OK", new LinkedHashMap<>(), "body{}".getBytes());
        long h = mock.create("/data/app/el1/bundle/public/org.wikipedia", 1080, 1920, null, sink);
        check("engine initialised on first create", mock.engineInitialised());
        check("non-zero handle", h != 0L);
        Map<String,String> none = new LinkedHashMap<>();
        mock.loadDataWithBaseURL(h, "https://en.wikipedia.org/", "<html>..</html>", "text/html", "UTF-8", "https://en.wikipedia.org/wiki/Earth");
        check("onPageStarted fired", sink.events.contains("started:https://en.wikipedia.org/wiki/Earth"));
        check("shouldInterceptRequest asked for a pagelib asset", sink.interceptAsked);
        check("intercept return flowed back to backend", mock.lastIntercepted == sink.interceptReturn);
        check("onProgressChanged(100) fired", sink.lastProgress == 100);
        check("onPageFinished fired last", sink.events.get(sink.events.size()-1).startsWith("finished:"));
        mock.scriptedEvalResult = "\"wired\"";
        mock.evaluateJavascript(h, "1+1", 42);
        check("onEvaluateResult matched requestId", sink.evalId != null && sink.evalId == 42);
        check("onEvaluateResult carried value", "\"wired\"".equals(sink.evalValue));
    }

    static void testControllerForwarding() {
        System.out.println("[T2] OhNWebController forwards the render core to the backend");
        MockNWebBackend mock = new MockNWebBackend();
        OhNWebController c = new OhNWebController(mock);
        c.init(null, "/data/app/el1/bundle/public/org.wikipedia", 1080, 1920, null);  // webView=null (JVM test)
        check("controller created NWeb (ready)", c.isReady());
        check("create recorded", mock.sawOp("create"));
        c.setJavaScriptEnabled(true);
        c.setDomStorageEnabled(true);
        c.addJavascriptInterface(new Object(), "WikipediaBridge");
        c.loadDataWithBaseURL("https://en.wikipedia.org/", "<html/>", "text/html", "UTF-8", "https://en.wikipedia.org/wiki/Earth");
        c.loadUrl("https://en.wikipedia.org/wiki/Moon");
        check("setJavaScriptEnabled forwarded", mock.sawOp("setJavaScriptEnabled"));
        check("setDomStorageEnabled forwarded", mock.sawOp("setDomStorageEnabled"));
        check("addJavascriptInterface forwarded with name",
                mock.sawOp("addJavascriptInterface") && "WikipediaBridge".equals(mock.opsNamed("addJavascriptInterface").get(0).args[1]));
        check("loadDataWithBaseURL forwarded", mock.sawOp("loadDataWithBaseURL"));
        check("loadUrl forwarded", mock.sawOp("loadUrl"));

        // evaluateJavascript round-trip: ValueCallback is an interface -> runs under the android.jar stub.
        mock.scriptedEvalResult = "\"ok\"";
        final String[] got = new String[1];
        c.evaluateJavascript("document.title", (ValueCallback<String>) value -> got[0] = value);
        check("evaluateJavascript result delivered to ValueCallback", "\"ok\"".equals(got[0]));

        // null-client callbacks must be safe no-ops (no WebView/client instantiated in this JVM test).
        boolean threw = false;
        try { c.onPageFinished("u"); c.onProgressChanged(50); check("shouldInterceptRequest null-client -> null", c.shouldInterceptRequest("u", true, false, false, "GET", null) == null); }
        catch (Throwable t) { threw = true; }
        check("callbacks with no client are safe no-ops", !threw);
    }

    public static void main(String[] args) {
        testBackendContractAndCallbacks();
        testControllerForwarding();
        System.out.println("\n" + (checks - fails) + "/" + checks + " checks passed" + (fails == 0 ? "  ALL PASS" : "  *** " + fails + " FAILED ***"));
        System.exit(fails == 0 ? 0 : 1);
    }
}
