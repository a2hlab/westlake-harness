/* r17k (#93): a resolvable com.android.org.conscrypt.OpenSSLProvider for route-A (no Conscrypt). */
package com.android.org.conscrypt;

/**
 * B8 (#93/r17k): route-A ships no Conscrypt, so the class
 * {@code com.android.org.conscrypt.OpenSSLProvider} does not exist. VLC (its Application installs a
 * security provider) and Tusky (via androidx.startup InitializationProvider) look it up by name and
 * die at bindApplication with ClassNotFoundException -> System.exit(1), before their first Activity
 * ever adds a window (cc-wiki installer batch-2).
 *
 * Provide the class so those lookups resolve. It extends the runtime AndroidOpenSSL provider
 * (BC-low-level-backed MessageDigests), so an app that instantiates it and adds it to the JCA gets a
 * working, correctly-named ("AndroidOpenSSL") provider; the constructor's name argument is ignored
 * because Conscrypt's OpenSSLProvider is always the "AndroidOpenSSL" provider. Registering the same
 * provider name twice is a no-op in Security.addProvider, so this never conflicts with the copy
 * WestlakeTlsInstall already published.
 */
public final class OpenSSLProvider extends adapter.security.WestlakeAndroidOpenSsl {
    private static final long serialVersionUID = 1L;

    public OpenSSLProvider() {
        super();
    }

    /** Conscrypt exposes OpenSSLProvider(String defaultProviderName); the name is always AndroidOpenSSL. */
    public OpenSSLProvider(String defaultProviderName) {
        super();
    }
}
