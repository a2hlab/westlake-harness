// [T7d 2026-10-01] wikipedia OkHttp AndroidPlatform: NoClassDefFoundError android.net.ssl.SSLSockets.
// isSupportedSocket=false -> OkHttp uses the standard SSLSocket path; setUseSessionTickets no-op.
package android.net.ssl;

public final class SSLSockets {
    private SSLSockets() {}
    public static boolean isSupportedSocket(javax.net.ssl.SSLSocket socket) { return false; }
    public static void setUseSessionTickets(javax.net.ssl.SSLSocket socket, boolean useSessionTickets) {}
}
