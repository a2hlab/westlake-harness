/* r17d (#93): SSLSocketFactory that hands back WestlakeSSLSocket over a connected plain socket. */
package adapter.compat;

import java.io.IOException;
import java.net.InetAddress;
import java.net.Socket;

import javax.net.ssl.SSLSocketFactory;

/**
 * B8 (#93/r17d): the JSSE entry point that routes an app's HTTPS through WestlakeSSLSocket (OH's
 * OpenSSL boundary). Only installed as the default factory by WestlakeTlsInstall AFTER the native
 * self-test proves a real handshake works, so this class never sees traffic on a board where the
 * boundary library is absent or non-functional.
 *
 * createSocket connects a plain Socket to the peer, then wraps it; the TLS handshake runs lazily on
 * the first getInputStream/getOutputStream/startHandshake (WestlakeSSLSocket), matching the JSSE
 * convention that createSocket(host,port) returns a connected but not-yet-handshaken SSLSocket.
 */
public final class WestlakeSSLSocketFactory extends SSLSocketFactory {

    @Override
    public String[] getDefaultCipherSuites() {
        return supported();
    }

    @Override
    public String[] getSupportedCipherSuites() {
        return supported();
    }

    private static String[] supported() {
        return new String[] {
            "TLS_AES_128_GCM_SHA256", "TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256", "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256", "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
        };
    }

    @Override
    public Socket createSocket(Socket s, String host, int port, boolean autoClose) throws IOException {
        if (s != null && !s.isConnected()) {
            s.connect(new java.net.InetSocketAddress(host, port));
        }
        return new WestlakeSSLSocket(s != null ? s : connect(host, port), host, port, autoClose);
    }

    @Override
    public Socket createSocket(String host, int port) throws IOException {
        return new WestlakeSSLSocket(connect(host, port), host, port, true);
    }

    @Override
    public Socket createSocket(String host, int port, InetAddress localHost, int localPort)
            throws IOException {
        Socket s = new Socket();
        s.bind(new java.net.InetSocketAddress(localHost, localPort));
        s.connect(new java.net.InetSocketAddress(host, port));
        return new WestlakeSSLSocket(s, host, port, true);
    }

    @Override
    public Socket createSocket(InetAddress host, int port) throws IOException {
        Socket s = new Socket();
        s.connect(new java.net.InetSocketAddress(host, port));
        return new WestlakeSSLSocket(s, hostName(host), port, true);
    }

    @Override
    public Socket createSocket(InetAddress address, int port, InetAddress localAddress, int localPort)
            throws IOException {
        Socket s = new Socket();
        s.bind(new java.net.InetSocketAddress(localAddress, localPort));
        s.connect(new java.net.InetSocketAddress(address, port));
        return new WestlakeSSLSocket(s, hostName(address), port, true);
    }

    private static Socket connect(String host, int port) throws IOException {
        Socket s = new Socket();
        s.connect(new java.net.InetSocketAddress(host, port));
        return s;
    }

    /** Hostname for SNI / SSL_set1_host: prefer the resolved name, fall back to the literal address. */
    private static String hostName(InetAddress address) {
        String name = address.getHostName();
        return name != null && !name.isEmpty() ? name : address.getHostAddress();
    }
}
