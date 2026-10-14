/* r17 (#93): SSLSession view over a Westlake OpenSSL handle. */
package adapter.compat;

import java.security.Principal;
import java.security.cert.Certificate;
import java.security.cert.X509Certificate;
import java.util.HashMap;
import java.util.Map;

import javax.net.ssl.SSLPeerUnverifiedException;
import javax.net.ssl.SSLSession;
import javax.net.ssl.SSLSessionContext;

/**
 * B8 (#93/r17): a read-only SSLSession backed by a Westlake TLS handle. Peer certificates come from
 * the native chain (decoded by OhPeerCertificates); protocol and cipher suite come from nativeInfo.
 * A handle of 0 means "handshake did not complete" -- the session is invalid and exposes no peer.
 */
final class WestlakeSSLSession implements SSLSession {
    private static final int INFO_PROTOCOL = 0;
    private static final int INFO_CIPHER = 1;

    private final WestlakeSSLSocket socket;
    private final long handle;
    private final String peerHost;
    private final int peerPort;
    private final long creationTime = System.currentTimeMillis();
    private final Map<String, Object> values = new HashMap<>();
    private final byte[] id;

    WestlakeSSLSession(WestlakeSSLSocket socket, long handle, String peerHost, int peerPort) {
        this.socket = socket;
        this.handle = handle;
        this.peerHost = peerHost;
        this.peerPort = peerPort;
        this.id = Long.toHexString(handle).getBytes();
    }

    @Override public boolean isValid() { return handle != 0; }
    @Override public byte[] getId() { return id.clone(); }
    @Override public SSLSessionContext getSessionContext() { return null; }
    @Override public long getCreationTime() { return creationTime; }
    @Override public long getLastAccessedTime() { return creationTime; }
    @Override public String getPeerHost() { return peerHost; }
    @Override public int getPeerPort() { return peerPort; }
    @Override public int getPacketBufferSize() { return 16709; }       // TLS record + overhead
    @Override public int getApplicationBufferSize() { return 16384; }  // max TLS plaintext record

    @Override public String getCipherSuite() {
        String c = socket.info(INFO_CIPHER);
        return c != null ? c : "SSL_NULL_WITH_NULL_NULL";
    }
    @Override public String getProtocol() {
        String p = socket.info(INFO_PROTOCOL);
        return p != null ? p : "NONE";
    }

    @Override public Certificate[] getPeerCertificates() throws SSLPeerUnverifiedException {
        return socket.peerCertificates();
    }
    @Override public Certificate[] getLocalCertificates() { return null; }

    @Override public Principal getPeerPrincipal() throws SSLPeerUnverifiedException {
        Certificate[] chain = getPeerCertificates();
        if (chain.length == 0 || !(chain[0] instanceof X509Certificate)) {
            throw new SSLPeerUnverifiedException("no peer principal");
        }
        return ((X509Certificate) chain[0]).getSubjectX500Principal();
    }
    @Override public Principal getLocalPrincipal() { return null; }

    /** Deprecated legacy cert API (javax.security.cert). Not supported by this bridge. */
    @Override
    public javax.security.cert.X509Certificate[] getPeerCertificateChain()
            throws SSLPeerUnverifiedException {
        throw new SSLPeerUnverifiedException("legacy peer certificate chain is not supported");
    }

    @Override public void invalidate() { /* one-shot handle owned by the socket */ }

    @Override public void putValue(String name, Object value) {
        values.put(name, value);
    }
    @Override public Object getValue(String name) { return values.get(name); }
    @Override public void removeValue(String name) { values.remove(name); }
    @Override public String[] getValueNames() { return values.keySet().toArray(new String[0]); }
}
