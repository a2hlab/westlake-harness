/* r17 (#93): child-side installer for the Westlake HTTPS/TLS Java chain. */
package adapter.security;

import java.security.Provider;
import java.security.Security;

/**
 * B8 (#93/r17): the child-process entry point that restores Android's JCA contract on the trimmed
 * OH boot class path and installs the OH PKIX trust bridge, then hands off to OhTrustBridge.install().
 *
 * On Westlake this is done inline in AppSpawnXInit's child security block (the parent deliberately
 * never touches Security.getProviders() -- doing so pins a permanent JCA AssertionError on the Class,
 * see AppSpawnXInit L296-303). Route-A v3a ships none of it (cx-t0 copylist: zero OhTrustBridge/
 * WestlakeSSL/WestlakeSecureRandom in any payload jar), so we run the same sequence from the runtime
 * JAR at bind time -- handleBindApplication is well inside the forked child, clear of that trap, and
 * every provider.put here is an idempotent overwrite, so re-doing anything appspawn already did is
 * harmless. A process-wide guard makes this run once.
 *
 * The AOSP-repackaged Bouncy Castle in the OH boot class path carries the implementation classes but
 * comments out their JCA provider mappings ("Android-removed: Unsupported algorithm") on the
 * assumption that Conscrypt owns those algorithms. OH has no Conscrypt, so PKIX validation, signature
 * verification and fresh-install key generation all fail until the mappings are restored here.
 */
public final class WestlakeTlsInstall {
    private static boolean done;

    private WestlakeTlsInstall() {}

    public static synchronized void install() {
        if (done) return;
        done = true;                       // one attempt per process; never loop on a partial failure
        try {
            // r17f: the OHOS Bouncy Castle AndroidDigestFactory.<clinit> asserts "Provider
            // AndroidOpenSSL must exist" unless WESTLAKE_USE_BC_DIGESTS=1, in which case it selects the
            // pure-Java BC digest backend (CONSCRYPT=null) -- route-A has no Conscrypt. Westlake sets
            // this in the boot/appspawn env; route-A's child does not, so set it here BEFORE the first
            // touch of AndroidDigestFactory (OhTrustBridge.initializeBouncyCastleDigests below).
            try {
                android.system.Os.setenv("WESTLAKE_USE_BC_DIGESTS", "1", true);
            } catch (Throwable t) {
                System.err.println("[B8-TLS] setenv WESTLAKE_USE_BC_DIGESTS failed: " + t);
            }
            Provider bc = Security.getProvider("BC");
            if (bc == null) {
                System.err.println("[B8-TLS] BC provider absent; TLS chain not installed");
                return;
            }
            registerMessageDigests(bc);
            registerAes(bc);
            registerX509CertificateFactory(bc);
            // OhTrustBridge publishes SecureRandom.WestlakeKernel, restores the BC RSA/EC signature and
            // EC KeyFactory registrations, and installs TrustManagerFactory.OH-PKIX/PKIX/X509 backed by
            // OhSystemTrustManager (platform CA bundle). Its own `installed` guard dedupes as well.
            OhTrustBridge.install();
            System.err.println("[B8-TLS] Westlake HTTPS/TLS Java chain installed via " + bc.getName());
            installSocketFactoryIfSelfTestPasses(bc);
        } catch (Throwable t) {
            // Never fail the bind for a crypto-registration problem: an app that does not do HTTPS at
            // first frame still needs to reach its UI. Report and move on.
            System.err.println("[B8-TLS] install failed (non-fatal): " + t);
        }
    }

    /**
     * r17d (#93): route the default HTTPS through WestlakeSSLSocket, but ONLY when the native TLS
     * boundary has self-tested a real handshake (WestlakeSSLSocket.selfTestPassed(), fail-closed).
     * Registering the factory routes every app's default SSLSocketFactory/SSLContext to the OH
     * OpenSSL boundary, so gating on "loaded" would be wrong: a loaded-but-broken native would send
     * all HTTPS down a path that always fails (worse than dormant). The self-test proves dlopen +
     * cacert validation + SSL_set1_host actually complete before we switch anything.
     */
    private static void installSocketFactoryIfSelfTestPasses(Provider bc) {
        boolean ok;
        try {
            ok = adapter.compat.WestlakeSSLSocket.selfTestPassed();
        } catch (Throwable t) {
            ok = false;
        }
        if (!ok) {
            System.err.println("[B8-TLS] native handshake self-test not passed; SSLSocketFactory stays dormant");
            return;
        }
        try {
            String spi = "adapter.compat.WestlakeSSLContextSpi";
            bc.put("SSLContext.TLS", spi);
            bc.put("SSLContext.TLSv1.2", spi);
            bc.put("SSLContext.TLSv1.3", spi);
            bc.put("SSLContext.Default", spi);
            bc.put("Alg.Alias.SSLContext.SSL", "TLS");
            javax.net.ssl.HttpsURLConnection.setDefaultSSLSocketFactory(
                    new adapter.compat.WestlakeSSLSocketFactory());
            Security.setProperty("ssl.SocketFactory.provider", "adapter.compat.WestlakeSSLSocketFactory");
            System.err.println("[B8-TLS] WestlakeSSLSocketFactory installed as default HTTPS (self-test OK)");
        } catch (Throwable t) {
            System.err.println("[B8-TLS] SSLSocketFactory install failed: " + t);
        }
    }

    /**
     * Restore MessageDigest MD5/SHA-1/-224/-256/-384/-512. The BCP dex has the SHA1$Digest classes but
     * the repackaged BC drops their registrations; PKIX signature verification looks digests up by JCA
     * name. (AppSpawnXInit child block, verbatim algorithm/class map.)
     */
    private static void registerMessageDigests(Provider bc) {
        final String pkg = "com.android.org.bouncycastle.jcajce.provider.digest.";
        String[][] map = {
            {"MD5", "MD5"}, {"SHA-1", "SHA1"}, {"SHA-224", "SHA224"},
            {"SHA-256", "SHA256"}, {"SHA-384", "SHA384"}, {"SHA-512", "SHA512"},
        };
        for (String[] e : map) bc.put("MessageDigest." + e[0], pkg + e[1] + "$Digest");
        bc.put("Alg.Alias.MessageDigest.SHA1", "SHA-1");
        bc.put("Alg.Alias.MessageDigest.SHA", "SHA-1");
        bc.put("Alg.Alias.MessageDigest.SHA224", "SHA-224");
        bc.put("Alg.Alias.MessageDigest.SHA256", "SHA-256");
        bc.put("Alg.Alias.MessageDigest.SHA384", "SHA-384");
        bc.put("Alg.Alias.MessageDigest.SHA512", "SHA-512");
    }

    /**
     * Restore the BC AES services. A fresh app install must generate its first local encryption key
     * (KeyGenerator.AES); persisted installs can hide the gap by reusing an existing key.
     * (AppSpawnXInit child block, verbatim.)
     */
    private static void registerAes(Provider bc) {
        final String aes = "com.android.org.bouncycastle.jcajce.provider.symmetric.AES$";
        bc.put("KeyGenerator.AES", aes + "KeyGen");
        bc.put("Cipher.AES", aes + "ECB");
        bc.put("Cipher.AES SupportedModes", "ECB|CBC|CFB|OFB|CTR|GCM");
        bc.put("Cipher.AES SupportedPaddings", "NOPADDING|PKCS5PADDING|PKCS7PADDING|ISO10126PADDING");
        bc.put("Cipher.AES SupportedKeyFormats", "RAW");
        bc.put("Cipher.AES/CBC/PKCS5Padding", aes + "CBC");
        bc.put("Cipher.AES/CBC/PKCS5PADDING", aes + "CBC");
        bc.put("Cipher.AES/CBC/NoPadding", aes + "CBC");
        bc.put("AlgorithmParameters.AES", aes + "AlgParams");
        bc.put("Alg.Alias.Cipher.AES/CBC/PKCS7PADDING", "AES/CBC/PKCS5PADDING");
        bc.put("Alg.Alias.Cipher.AES/CBC/PKCS7Padding", "AES/CBC/PKCS5Padding");
    }

    /**
     * Restore CertificateFactory.X.509 -- needed by NetworkSecurityConfigProvider during
     * makeApplicationInner and by OhSystemTrustManager's PKIX path. (AppSpawnXInit child block.)
     */
    private static void registerX509CertificateFactory(Provider bc) {
        bc.put("CertificateFactory.X.509",
                "com.android.org.bouncycastle.jcajce.provider.asymmetric.x509.CertificateFactory");
        bc.put("Alg.Alias.CertificateFactory.X509", "X.509");
    }
}
