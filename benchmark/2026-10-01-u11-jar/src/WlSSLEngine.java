/* U11 (#apex-services / ssl-engine cluster): single-purpose file (freeze unit) -- a non-null stub SSLEngine
 * so SSLContext.createSSLEngine() stops returning null. New feature, new file; no frozen file touched. */
package adapter.compat;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.nio.ByteBuffer;
import javax.net.ssl.SSLEngine;
import javax.net.ssl.SSLEngineResult;
import javax.net.ssl.SSLException;
import javax.net.ssl.SSLSession;

/**
 * U11 (#ssl-engine): {@link adapter.compat.WestlakeSSLContextSpi#engineCreateSSLEngine} deliberately returns
 * null (deferring "route-A has no SSLEngine" to first real use, which never comes for OkHttp's lazy
 * SSLSocketFactory). fd-client (com.nextcloud.client) instead builds its TLS stack EAGERLY in
 * MainApp.onCreate and calls {@code SSLEngine.getEnabledProtocols()} on that null -> NPE -> the Dagger object
 * graph is never built -> SessionMixin.accountManager stays null -> the first Activity NPEs on the @NonNull
 * param (U9 fatal: createSSLEngine null is the ROOT; accountManager null is the consequence).
 *
 * Return a non-null stub engine instead: the metadata getters (protocols / cipher suites / session / modes)
 * answer sane non-null values so the eager setup completes and the DI graph builds; the actual data path
 * (wrap/unwrap) throws SSLException -- if a stub engine is ever driven for real I/O that is a later, honest
 * wall, not a silent null. Lazy apps (OkHttp) never call createSSLEngine, so they are unaffected (null ->
 * non-null is strictly additive). Wired by a smali needle that points both engineCreateSSLEngine overloads at
 * {@link #create()} (WestlakeSSLContextSpi is not edited).
 */
public final class WlSSLEngine extends SSLEngine {

    private static final String[] PROTOCOLS = {"TLSv1.3", "TLSv1.2"};
    private static final String[] CIPHERS = {"TLS_AES_128_GCM_SHA256", "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"};

    private boolean clientMode = true;
    private boolean needClientAuth = false;
    private boolean wantClientAuth = false;
    private boolean enableSessionCreation = true;
    private boolean inboundDone = false;
    private boolean outboundDone = false;

    private WlSSLEngine() { super(); }

    /** Factory the smali needle calls from WestlakeSSLContextSpi.engineCreateSSLEngine(). */
    public static SSLEngine create() { return new WlSSLEngine(); }

    private static SSLException noRealTls() {
        return new SSLException("Westlake stub SSLEngine: no real TLS on route-A (metadata only)");
    }

    @Override public SSLEngineResult wrap(ByteBuffer[] srcs, int offset, int length, ByteBuffer dst) throws SSLException { throw noRealTls(); }
    @Override public SSLEngineResult unwrap(ByteBuffer src, ByteBuffer[] dsts, int offset, int length) throws SSLException { throw noRealTls(); }
    @Override public Runnable getDelegatedTask() { return null; }
    @Override public void closeInbound() { inboundDone = true; }
    @Override public boolean isInboundDone() { return inboundDone; }
    @Override public void closeOutbound() { outboundDone = true; }
    @Override public boolean isOutboundDone() { return outboundDone; }
    @Override public String[] getSupportedCipherSuites() { return CIPHERS.clone(); }
    @Override public String[] getEnabledCipherSuites() { return CIPHERS.clone(); }
    @Override public void setEnabledCipherSuites(String[] suites) { }
    @Override public String[] getSupportedProtocols() { return PROTOCOLS.clone(); }
    @Override public String[] getEnabledProtocols() { return PROTOCOLS.clone(); }
    @Override public void setEnabledProtocols(String[] protocols) { }
    @Override public SSLSession getSession() { return stubSession(); }
    @Override public void beginHandshake() throws SSLException { }
    @Override public SSLEngineResult.HandshakeStatus getHandshakeStatus() { return SSLEngineResult.HandshakeStatus.NOT_HANDSHAKING; }
    @Override public void setUseClientMode(boolean mode) { this.clientMode = mode; }
    @Override public boolean getUseClientMode() { return clientMode; }
    @Override public void setNeedClientAuth(boolean need) { this.needClientAuth = need; this.wantClientAuth = false; }
    @Override public boolean getNeedClientAuth() { return needClientAuth; }
    @Override public void setWantClientAuth(boolean want) { this.wantClientAuth = want; this.needClientAuth = false; }
    @Override public boolean getWantClientAuth() { return wantClientAuth; }
    @Override public void setEnableSessionCreation(boolean flag) { this.enableSessionCreation = flag; }
    @Override public boolean getEnableSessionCreation() { return enableSessionCreation; }

    /** A type-zero SSLSession (Proxy): primitives -> 0/false, arrays -> empty, objects -> null, protocol/
     *  cipher strings via name match. Never used for real crypto; only read for metadata. */
    private static SSLSession stubSession() {
        return (SSLSession) Proxy.newProxyInstance(SSLSession.class.getClassLoader(),
                new Class<?>[] {SSLSession.class}, new InvocationHandler() {
                    @Override public Object invoke(Object proxy, Method method, Object[] args) {
                        String n = method.getName();
                        Class<?> t = method.getReturnType();
                        if ("getProtocol".equals(n)) return "TLSv1.3";
                        if ("getCipherSuite".equals(n)) return CIPHERS[0];
                        if ("isValid".equals(n)) return Boolean.FALSE;
                        if ("getPacketBufferSize".equals(n) || "getApplicationBufferSize".equals(n)) return Integer.valueOf(16384);
                        if ("toString".equals(n)) return "WlStubSSLSession";
                        if ("hashCode".equals(n)) return Integer.valueOf(System.identityHashCode(proxy));
                        if ("equals".equals(n)) return Boolean.valueOf(args != null && args.length == 1 && args[0] == proxy);
                        if (t == boolean.class) return Boolean.FALSE;
                        if (t == int.class) return Integer.valueOf(0);
                        if (t == long.class) return Long.valueOf(0L);
                        if (t == void.class) return null;
                        if (t.isArray()) return java.lang.reflect.Array.newInstance(t.getComponentType(), 0);
                        return null;
                    }
                });
    }
}
