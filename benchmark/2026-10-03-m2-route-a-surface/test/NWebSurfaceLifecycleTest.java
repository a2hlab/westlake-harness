import org.westlake.webview.NWebBackend;
import org.westlake.webview.NWebCallbackSink;
import org.westlake.webview.NWebSurfaceLifecycle;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Offline unit test for the Option-A surface lifecycle (no Android, no native). A recording NWebBackend captures the
 * call order; we assert the correctness points from NWebSurfaceLifecycle's contract:
 *   1. no NWeb is created before the surface exists (loadUrl/settings before onSurfaceReady do NOT call create);
 *   2. onSurfaceReady creates with the SurfaceView holder's Surface + extent, then applies deferred settings + url;
 *   3. onSurfaceChanged drives drawFrame (resize); onSurfaceLost destroys; a later onSurfaceReady recreates.
 * Run: javac -d out -cp <m2-route-a-java/src> <src> test/NWebSurfaceLifecycleTest.java && java -cp out NWebSurfaceLifecycleTest
 */
public class NWebSurfaceLifecycleTest {

    static final List<String> log = new ArrayList<>();
    static int checks = 0;

    static void check(boolean cond, String msg) {
        checks++;
        if (!cond) throw new AssertionError("FAIL: " + msg + "  log=" + log);
    }

    /** Recording backend: returns a fixed non-zero handle from create, logs every call. */
    static final class RecordingBackend implements NWebBackend {
        Object lastSurface; int lastW, lastH; long next = 0x5151L;
        public long create(String bundlePath, int w, int h, Object surface, NWebCallbackSink sink) {
            lastSurface = surface; lastW = w; lastH = h; log.add("create(" + w + "x" + h + ",surf=" + (surface != null) + ")");
            return next;
        }
        public void loadUrl(long h, String url, Map<String, String> hdr) { log.add("loadUrl(" + url + ")"); }
        public void loadDataWithBaseURL(long h, String b, String d, String m, String e, String hi) {}
        public void loadData(long h, String d, String m, String e) {}
        public void postUrl(long h, String u, byte[] p) {}
        public void evaluateJavascript(long h, String s, int id) {}
        public void setJavaScriptEnabled(long h, boolean e) { log.add("setJS(" + e + ")"); }
        public void setDomStorageEnabled(long h, boolean e) { log.add("setDom(" + e + ")"); }
        public void addJavascriptInterface(long h, Object o, String n) {}
        public void removeJavascriptInterface(long h, String n) {}
        public void reload(long h) {}
        public void stopLoading(long h) {}
        public boolean canGoBack(long h) { return false; }
        public void goBack(long h) {}
        public void onPause(long h) { log.add("onPause"); }
        public void onResume(long h) { log.add("onResume"); }
        public void drawFrame(long h, Object c, int w, int hh) { log.add("drawFrame(" + w + "x" + hh + ")"); }
        public void destroy(long h) { log.add("destroy"); }
    }

    public static void main(String[] args) {
        RecordingBackend be = new RecordingBackend();
        NWebSurfaceLifecycle lc = new NWebSurfaceLifecycle(be, null, "/data/app/.../bundle");

        // 1. requests before the surface exists must NOT create NWeb
        lc.setJavaScriptEnabled(true);
        lc.loadUrl("https://en.wikipedia.org/wiki/OpenHarmony", null);
        check(!lc.isActive(), "no NWeb before surface");
        check(log.isEmpty(), "no backend calls before surface (deferred): " + log);

        // 2. onSurfaceReady creates with the holder's surface + extent, then applies deferred settings + url
        Object fakeSurface = new Object();                 // stands in for SurfaceView.getHolder().getSurface()
        long h = lc.onSurfaceReady(fakeSurface, 1080, 1920);
        check(h == 0x5151L && lc.isActive(), "create returned handle");
        check(be.lastSurface == fakeSurface, "created with the SurfaceView holder's Surface");
        check(be.lastW == 1080 && be.lastH == 1920, "created with the surface extent");
        check(log.contains("create(1080x1920,surf=true)"), "create logged with surface");
        check(log.indexOf("loadUrl(https://en.wikipedia.org/wiki/OpenHarmony)") > log.indexOf("create(1080x1920,surf=true)"),
              "deferred url loaded AFTER create");
        check(log.contains("setJS(true)"), "deferred JS setting applied after create");

        // 3a. a second onSurfaceReady on the same surface does not recreate
        int n = log.size();
        lc.onSurfaceReady(fakeSurface, 1080, 1920);
        check(log.size() == n, "idempotent onSurfaceReady (no double create)");

        // 3b. surfaceChanged drives drawFrame(resize)
        lc.onSurfaceChanged(1080, 1800);
        check(log.contains("drawFrame(1080x1800)"), "surfaceChanged -> drawFrame resize");

        // 3c. surfaceDestroyed tears down; a later surface recreates
        lc.onSurfaceLost();
        check(!lc.isActive() && log.contains("destroy"), "surfaceLost -> destroy, handle cleared");
        Object surface2 = new Object();
        long h2 = lc.onSurfaceReady(surface2, 1080, 1800);
        check(h2 != 0L && be.lastSurface == surface2, "recreated on the new surface");

        System.out.println("NWebSurfaceLifecycleTest: ALL " + checks + " checks PASS");
    }
}
