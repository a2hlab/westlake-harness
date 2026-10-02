package android.util;

/**
 * TEST-ONLY host-ART shim (never deployed): android.util.Log without the liblog natives that host ART lacks, placed
 * on the boot class path before framework.jar so the runtime's AppSpawnXInit.overrideJcaProvidersForOH() can run to
 * the end (it logs between rewriting the provider list and installing OHSecureRandomProvider). Prints to stdout.
 */
public final class Log {
    public static final int VERBOSE = 2, DEBUG = 3, INFO = 4, WARN = 5, ERROR = 6, ASSERT = 7;

    private Log() {}

    private static int p(String level, String tag, String msg, Throwable tr) {
        System.out.println("[hostlog " + level + "/" + tag + "] " + msg + (tr != null ? " " + tr : ""));
        return 0;
    }

    public static int v(String tag, String msg) { return p("V", tag, msg, null); }
    public static int v(String tag, String msg, Throwable tr) { return p("V", tag, msg, tr); }
    public static int d(String tag, String msg) { return p("D", tag, msg, null); }
    public static int d(String tag, String msg, Throwable tr) { return p("D", tag, msg, tr); }
    public static int i(String tag, String msg) { return p("I", tag, msg, null); }
    public static int i(String tag, String msg, Throwable tr) { return p("I", tag, msg, tr); }
    public static int w(String tag, String msg) { return p("W", tag, msg, null); }
    public static int w(String tag, String msg, Throwable tr) { return p("W", tag, msg, tr); }
    public static int w(String tag, Throwable tr) { return p("W", tag, "", tr); }
    public static int e(String tag, String msg) { return p("E", tag, msg, null); }
    public static int e(String tag, String msg, Throwable tr) { return p("E", tag, msg, tr); }
    public static int wtf(String tag, String msg) { return p("F", tag, msg, null); }
    public static int wtf(String tag, String msg, Throwable tr) { return p("F", tag, msg, tr); }
    public static int wtf(String tag, Throwable tr) { return p("F", tag, "", tr); }
    public static int println(int priority, String tag, String msg) { return p(String.valueOf(priority), tag, msg, null); }
    public static boolean isLoggable(String tag, int level) { return true; }

    public static String getStackTraceString(Throwable tr) {
        if (tr == null) return "";
        java.io.StringWriter sw = new java.io.StringWriter();
        tr.printStackTrace(new java.io.PrintWriter(sw));
        return sw.toString();
    }
}
