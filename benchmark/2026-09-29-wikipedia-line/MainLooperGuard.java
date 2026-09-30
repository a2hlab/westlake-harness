package adapter.activity;

import android.os.Handler;
import android.os.Looper;

/**
 * Main-thread looper guard for one known, non-fatal-in-practice failure (B11 v7, cc-wiki).
 *
 * route-A's boot class path only has a constructor-only stub of org.ccil.cowan.tagsoup.Parser, so
 * android.text.Html.fromHtml throws NoSuchMethodError (Parser.setProperty). Wikipedia hits it while
 * composing an error card and the uncaught error ends the process. A real tagsoup needs a boot image
 * rebuild (not available for this generation).
 *
 * Same shape as Cockroach: a task posted to the main looper runs a nested Looper.loop(); an error
 * thrown out of message dispatch lands here. Only a NoSuchMethodError whose top frame is in
 * org.ccil.cowan.tagsoup.* or android.text.Html.fromHtml is logged and the loop resumes. Anything
 * else is rethrown unchanged, so every other crash keeps its normal fatal path.
 */
public final class MainLooperGuard {
    private static boolean sInstalled;
    private static int sTolerated;

    private MainLooperGuard() {}

    public static synchronized void install() {
        if (sInstalled) return;
        Looper main = Looper.getMainLooper();
        if (main == null) {
            log("not installed: no main looper");
            return;
        }
        sInstalled = true;
        new Handler(main).post(new Runnable() {
            public void run() {
                log("installed on " + Thread.currentThread().getName());
                while (true) {
                    try {
                        Looper.loop();
                        return;
                    } catch (Throwable t) {
                        if (!tolerated(t)) rethrow(t);
                        sTolerated++;
                        StackTraceElement top = t.getStackTrace().length > 0 ? t.getStackTrace()[0] : null;
                        log("tolerated #" + sTolerated + " " + t.getClass().getName() + ": " + t.getMessage()
                                + " at " + top);
                    }
                }
            }
        });
    }

    static boolean tolerated(Throwable t) {
        if (!(t instanceof NoSuchMethodError)) return false;
        StackTraceElement[] st = t.getStackTrace();
        if (st == null || st.length == 0) return false;
        String cls = st[0].getClassName();
        return cls.startsWith("org.ccil.cowan.tagsoup.")
                || ("android.text.Html".equals(cls) && "fromHtml".equals(st[0].getMethodName()));
    }

    private static void rethrow(Throwable t) {
        if (t instanceof RuntimeException) throw (RuntimeException) t;
        if (t instanceof Error) throw (Error) t;
        throw new RuntimeException(t);
    }

    private static void log(String m) {
        System.err.println("[LOOPER-GUARD] " + m);
        System.err.flush();
    }
}
