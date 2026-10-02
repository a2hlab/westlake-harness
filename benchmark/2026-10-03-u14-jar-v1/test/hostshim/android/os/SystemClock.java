package android.os;

/**
 * TEST-ONLY host-ART shim (never deployed): android.os.SystemClock without libandroid_runtime's natives, which host
 * ART lacks. Placed on the boot class path before framework.jar so Handler.post (sendMessageDelayed ->
 * SystemClock.uptimeMillis) can enqueue on the real MessageQueue. Monotonic, from System.nanoTime.
 */
public final class SystemClock {
    private SystemClock() {}

    public static long uptimeMillis() { return System.nanoTime() / 1_000_000L; }
    public static long uptimeNanos() { return System.nanoTime(); }
    public static long elapsedRealtime() { return System.nanoTime() / 1_000_000L; }
    public static long elapsedRealtimeNanos() { return System.nanoTime(); }
    public static long currentThreadTimeMillis() { return System.nanoTime() / 1_000_000L; }
    public static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException ignored) { }
    }
}
