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

    // J8 (#nextcloud-accountmanager-null / fd-client): return null instead of throwing. The throw aborted
    // MainApp.onCreate (OkHttp/TLS stack build) -> Dagger object graph never built -> every @Inject field
    // (incl. SessionMixin.accountManager) stayed null -> first Activity NPE'd on the @NonNull param
    // (NULL-PRODUCERS.md). AOSP 14 r1 javax.net.ssl.SSLContextSpi.engineCreateSSLEngine is abstract and a
    // real provider returns an engine; route-A has no SSLEngine, but returning null defers the absence to
    // the first actual engine use (OkHttp creates its SSLSocketFactory lazily, not at init) so Application
    // creation completes and the DI graph is built. Pairs with FZ-008 (SSLSockets) on the socket path.
    @Override
    protected SSLEngine engineCreateSSLEngine() {
        return null;
    }

    @Override
    protected SSLEngine engineCreateSSLEngine(String host, int port) {
        return null;
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
