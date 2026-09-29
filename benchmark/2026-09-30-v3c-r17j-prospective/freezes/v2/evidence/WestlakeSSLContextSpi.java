/* r17d (#93): SSLContextSpi whose socket factory is WestlakeSSLSocketFactory. */
package adapter.compat;

import java.security.KeyManagementException;
import java.security.SecureRandom;

import javax.net.ssl.KeyManager;
import javax.net.ssl.SSLEngine;
import javax.net.ssl.SSLServerSocketFactory;
import javax.net.ssl.SSLSessionContext;
import javax.net.ssl.SSLContextSpi;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;

/**
 * B8 (#93/r17d): a client-only SSLContext whose getSocketFactory() returns WestlakeSSLSocketFactory,
 * so OkHttp/HttpsURLConnection code that goes SSLContext.getInstance(...).getSocketFactory() reaches
 * the OH OpenSSL boundary. Registered as SSLContext.TLS/Default by WestlakeTlsInstall only after the
 * native self-test passes.
 *
 * Trust is enforced natively (cacert.pem + SSL_set1_host inside WestlakeSSLSocket's nativeHandshake),
 * so engineInit ignores app-supplied managers rather than pretending to honour them; server-side and
 * SSLEngine paths are unsupported (this runtime only makes outbound client HTTPS calls).
 */
public final class WestlakeSSLContextSpi extends SSLContextSpi {

    @Override
    protected void engineInit(KeyManager[] km, TrustManager[] tm, SecureRandom sr)
            throws KeyManagementException {
        // No-op: the native handshake owns trust and randomness. See class comment.
    }

    @Override
    protected SSLSocketFactory engineGetSocketFactory() {
        return new WestlakeSSLSocketFactory();
    }

    @Override
    protected SSLServerSocketFactory engineGetServerSocketFactory() {
        throw new UnsupportedOperationException("WestlakeSSLContext is client-only");
    }

    @Override
    protected SSLEngine engineCreateSSLEngine() {
        throw new UnsupportedOperationException("WestlakeSSLContext has no SSLEngine");
    }

    @Override
    protected SSLEngine engineCreateSSLEngine(String host, int port) {
        throw new UnsupportedOperationException("WestlakeSSLContext has no SSLEngine");
    }

    @Override
    protected SSLSessionContext engineGetClientSessionContext() {
        return null;
    }

    @Override
    protected SSLSessionContext engineGetServerSessionContext() {
        return null;
    }
}
