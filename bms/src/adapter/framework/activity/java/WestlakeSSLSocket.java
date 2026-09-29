/* r17 (#93): Java side of the Westlake OpenSSL-backed TLS boundary. */
package adapter.compat;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.Socket;
import java.net.SocketAddress;
import java.security.cert.Certificate;
import java.util.ArrayList;
import java.util.List;

import javax.net.ssl.HandshakeCompletedListener;
import javax.net.ssl.SSLSession;
import javax.net.ssl.SSLSocket;

/**
 * B8 (#93/r17): the Java half of Westlake's self-built HTTPS chain. Westlake ships no Conscrypt and no
 * libjavacrypto.so; instead the board's own OpenSSL 3.x is driven across a JNI boundary. The seven
 * native methods below are bound by the native side's wl_register_tls_natives(env)
 * (AndroidRuntime.cpp L3285: RegisterNatives(adapter/compat/WestlakeSSLSocket, {...})). This class
 * must therefore exist with EXACTLY these seven names and JNI descriptors or that registration prints
 * "adapter/compat/WestlakeSSLSocket NOT FOUND -- TLS off".
 *
 *   nativeHandshake  (ILjava/lang/String;I)J        fd, host, port         -> SSL* handle (long)
 *   nativeRead       (JI[BIII)I                      handle, fd, buf,off,len,timeoutMs -> count
 *   nativeWrite      (JI[BIII)I                      handle, fd, buf,off,len,timeoutMs -> count
 *   nativePeerCert   (J)[B                           handle                 -> leaf cert DER
 *   nativePeerChain  (J)[B                           handle                 -> concatenated chain DER
 *   nativeInfo       (JI)Ljava/lang/String;          handle, selector       -> protocol/cipher string
 *   nativeClose      (J)V                            handle
 *
 * The native side performs the real certificate verification (cacert.pem) and SSL_set1_host name
 * check. This wrapper adapts an already-connected plain Socket to the JSSE SSLSocket contract on top
 * of that handle. It is dormant until a WestlakeSSLSocketFactory routes through it (that factory's
 * source is not in the tree -- see the r17 README honest-limits note); the class is shipped now so the
 * native registration binds and so the wrapper is ready the moment a factory is added.
 */
public final class WestlakeSSLSocket extends SSLSocket {
    // nativeInfo selectors (mirror the native WL_TLS_info switch: 0 protocol, 1 cipher suite).
    private static final int INFO_PROTOCOL = 0;
    private static final int INFO_CIPHER = 1;

    static native long nativeHandshake(int fd, String host, int port);
    static native int nativeRead(long handle, int fd, byte[] b, int off, int len, int timeoutMs);
    static native int nativeWrite(long handle, int fd, byte[] b, int off, int len, int timeoutMs);
    static native byte[] nativePeerCert(long handle);
    static native byte[] nativePeerChain(long handle);
    static native String nativeInfo(long handle, int which);
    static native void nativeClose(long handle);

    // r17d: gate for wiring the default SSLSocketFactory. The native runs ONE handshake self-test
    // (dlopen board OpenSSL + cacert.pem validation + SSL_set1_host against a fixed reachable host) at
    // load and returns whether the whole chain -- not just RegisterNatives -- actually works. Until
    // cx-t0's liboh_tls_boundary provides it, this method is unregistered and selfTestPassed() catches
    // the UnsatisfiedLinkError and returns false, so the factory stays dormant (never routes all HTTPS
    // to a handshake that would fail).
    static native boolean nativeTlsSelfTestOk();

    /** True only when the native TLS chain self-tested a real handshake successfully (fail-closed). */
    public static boolean selfTestPassed() {
        try {
            return nativeTlsSelfTestOk();
        } catch (Throwable t) {
            System.err.println("[WESTLAKE-441] TLS self-test unavailable, factory stays dormant: " + t);
            return false;
        }
    }

    private final Socket underlying;
    private final String peerHost;
    private final int peerPort;
    private final boolean autoClose;

    private final List<HandshakeCompletedListener> listeners = new ArrayList<>();
    private String[] enabledProtocols = {"TLSv1.2", "TLSv1.3"};
    private String[] enabledCipherSuites = getSupportedCipherSuites();
    private boolean clientMode = true;
    private boolean enableSessionCreation = true;
    private boolean needClientAuth;
    private boolean wantClientAuth;

    private long handle;                 // 0 until a successful handshake
    private volatile boolean handshakeStarted;
    private WestlakeSSLSession session;

    public WestlakeSSLSocket(Socket underlying, String host, int port, boolean autoClose) {
        this.underlying = underlying;
        this.peerHost = host;
        this.peerPort = port;
        this.autoClose = autoClose;
    }

    // ---- SSLSocket handshake / session ------------------------------------------------------------

    @Override
    public synchronized void startHandshake() throws IOException {
        if (handshakeStarted) return;
        handshakeStarted = true;
        int fd = fileDescriptor(underlying);
        if (fd < 0) throw new IOException("cannot resolve underlying socket fd for TLS handshake");
        long h = nativeHandshake(fd, peerHost, peerPort);
        if (h == 0) throw new IOException("Westlake TLS handshake failed for " + peerHost + ":" + peerPort);
        handle = h;
        session = new WestlakeSSLSession(this, h, peerHost, peerPort);
        HandshakeCompletedListener[] snapshot;
        synchronized (listeners) { snapshot = listeners.toArray(new HandshakeCompletedListener[0]); }
        for (HandshakeCompletedListener l : snapshot) {
            try {
                l.handshakeCompleted(new javax.net.ssl.HandshakeCompletedEvent(this, session));
            } catch (Throwable ignore) {
                // A listener must not abort a completed handshake.
            }
        }
    }

    @Override
    public SSLSession getSession() {
        if (session == null) {
            try {
                startHandshake();
            } catch (IOException e) {
                return new WestlakeSSLSession(this, 0L, peerHost, peerPort);  // invalid, no peer certs
            }
        }
        return session;
    }

    @Override
    public InputStream getInputStream() throws IOException {
        startHandshake();
        final int fd = fileDescriptor(underlying);
        final int timeout = safeSoTimeout();
        return new InputStream() {
            private final byte[] one = new byte[1];
            @Override public int read() throws IOException {
                int n = read(one, 0, 1);
                return n <= 0 ? -1 : (one[0] & 0xff);
            }
            @Override public int read(byte[] b, int off, int len) throws IOException {
                if (len == 0) return 0;
                int n = nativeRead(handle, fd, b, off, len, timeout);
                return n <= 0 ? -1 : n;
            }
            @Override public void close() throws IOException { WestlakeSSLSocket.this.close(); }
        };
    }

    @Override
    public OutputStream getOutputStream() throws IOException {
        startHandshake();
        final int fd = fileDescriptor(underlying);
        final int timeout = safeSoTimeout();
        return new OutputStream() {
            @Override public void write(int b) throws IOException { write(new byte[] {(byte) b}, 0, 1); }
            @Override public void write(byte[] b, int off, int len) throws IOException {
                int written = 0;
                while (written < len) {
                    int n = nativeWrite(handle, fd, b, off + written, len - written, timeout);
                    if (n <= 0) throw new IOException("Westlake TLS write failed (" + n + ")");
                    written += n;
                }
            }
        };
    }

    /** Peer chain as X.509 certificates, decoded by OhPeerCertificates (no silent parse failures). */
    Certificate[] peerCertificates() throws javax.net.ssl.SSLPeerUnverifiedException {
        byte[] der = handle == 0 ? null : nativePeerChain(handle);
        if (der == null || der.length == 0) {
            throw new javax.net.ssl.SSLPeerUnverifiedException("no peer certificates");
        }
        return adapter.security.OhPeerCertificates.decode(der);
    }

    String info(int which) {
        return handle == 0 ? null : nativeInfo(handle, which);
    }

    // ---- config getters/setters (JSSE contract) ---------------------------------------------------

    @Override public String[] getSupportedCipherSuites() {
        return new String[] {
            "TLS_AES_128_GCM_SHA256", "TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256", "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256", "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
        };
    }
    @Override public String[] getEnabledCipherSuites() { return enabledCipherSuites.clone(); }
    @Override public void setEnabledCipherSuites(String[] suites) { enabledCipherSuites = suites.clone(); }
    @Override public String[] getSupportedProtocols() { return new String[] {"TLSv1.2", "TLSv1.3"}; }
    @Override public String[] getEnabledProtocols() { return enabledProtocols.clone(); }
    @Override public void setEnabledProtocols(String[] protocols) { enabledProtocols = protocols.clone(); }

    @Override public void addHandshakeCompletedListener(HandshakeCompletedListener l) {
        synchronized (listeners) { listeners.add(l); }
    }
    @Override public void removeHandshakeCompletedListener(HandshakeCompletedListener l) {
        synchronized (listeners) { listeners.remove(l); }
    }

    @Override public void setUseClientMode(boolean mode) { clientMode = mode; }
    @Override public boolean getUseClientMode() { return clientMode; }
    @Override public void setNeedClientAuth(boolean need) { needClientAuth = need; }
    @Override public boolean getNeedClientAuth() { return needClientAuth; }
    @Override public void setWantClientAuth(boolean want) { wantClientAuth = want; }
    @Override public boolean getWantClientAuth() { return wantClientAuth; }
    @Override public void setEnableSessionCreation(boolean flag) { enableSessionCreation = flag; }
    @Override public boolean getEnableSessionCreation() { return enableSessionCreation; }

    // ---- Socket delegation ------------------------------------------------------------------------

    @Override public synchronized void close() throws IOException {
        long h = handle;
        handle = 0;
        try {
            if (h != 0) nativeClose(h);
        } finally {
            if (autoClose && underlying != null) underlying.close();
        }
    }

    @Override public InetAddress getInetAddress() { return underlying.getInetAddress(); }
    @Override public InetAddress getLocalAddress() { return underlying.getLocalAddress(); }
    @Override public int getPort() { return underlying.getPort(); }
    @Override public int getLocalPort() { return underlying.getLocalPort(); }
    @Override public SocketAddress getRemoteSocketAddress() { return underlying.getRemoteSocketAddress(); }
    @Override public SocketAddress getLocalSocketAddress() { return underlying.getLocalSocketAddress(); }
    @Override public boolean isConnected() { return underlying.isConnected(); }
    @Override public boolean isBound() { return underlying.isBound(); }
    @Override public boolean isClosed() { return underlying.isClosed() || handle == 0 && handshakeStarted; }
    @Override public void setSoTimeout(int timeout) throws java.net.SocketException { underlying.setSoTimeout(timeout); }
    @Override public int getSoTimeout() throws java.net.SocketException { return underlying.getSoTimeout(); }
    @Override public void setTcpNoDelay(boolean on) throws java.net.SocketException { underlying.setTcpNoDelay(on); }
    @Override public boolean getTcpNoDelay() throws java.net.SocketException { return underlying.getTcpNoDelay(); }

    private int safeSoTimeout() {
        try { return underlying.getSoTimeout(); } catch (Throwable t) { return 0; }
    }

    /**
     * Resolve the raw file descriptor of an Android Socket. There is no public API; the native layer
     * needs the integer fd. Walk Socket -> SocketImpl.getFileDescriptor() -> FileDescriptor -> int,
     * all via reflection. Returns -1 when it cannot be resolved (handshake then fails cleanly).
     */
    private static int fileDescriptor(Socket socket) {
        try {
            java.lang.reflect.Method getImpl = Socket.class.getDeclaredMethod("getImpl");
            getImpl.setAccessible(true);
            Object impl = getImpl.invoke(socket);
            if (impl == null) return -1;
            java.lang.reflect.Method getFd =
                    java.net.SocketImpl.class.getDeclaredMethod("getFileDescriptor");
            getFd.setAccessible(true);
            Object fdObj = getFd.invoke(impl);
            if (!(fdObj instanceof java.io.FileDescriptor)) return -1;
            java.lang.reflect.Field descriptor = java.io.FileDescriptor.class.getDeclaredField("descriptor");
            descriptor.setAccessible(true);
            return descriptor.getInt(fdObj);
        } catch (Throwable t) {
            return -1;
        }
    }
}
