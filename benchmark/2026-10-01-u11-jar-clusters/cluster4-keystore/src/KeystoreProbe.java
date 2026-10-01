import adapter.core.SoftwareAndroidKeyStore;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;

import java.io.File;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.security.Key;
import java.security.KeyStore;
import java.util.Arrays;
import java.util.Map;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Cluster-4 keystore probe (#90, moodcairns AEADBadTagException).
 *
 * Reproduces androidx.security's path on SoftwareAndroidKeyStore: generate the AES256_GCM master
 * key via KeyGenerator(AES,"AndroidKeyStore")+KeyGenParameterSpec, then run Tink's
 * AndroidKeystoreKmsClient.validateAead() self-test (the exact thing that threw on-board:
 * "the master key ... exists but is unusable" caused by AEADBadTagException: mac check in GCM failed).
 *
 * validateAead = encrypt(plaintext, aad) then decrypt(ciphertext, aad) with the SAME key, and the
 * Tink framing is iv(12) || ciphertext, tag 128 bits. If the default Cipher provider hands back an
 * IV whose length != 12 on encrypt-without-params, Tink's decrypt (which reads the first 12 bytes
 * as the IV) uses the wrong IV -> BadTag. We print the IV length to localize mapping vs tag/IV.
 */
public final class KeystoreProbe {
    private static final String ALIAS = "_androidx_security_master_key_";
    private static final int IV = 12;          // Tink IV_SIZE_IN_BYTES
    private static final int TAG = 128;         // Tink tag bits
    private static int pass = 0, fail = 0;

    public static void main(String[] args) throws Exception {
        // JDK 8 (<8u161) caps AES at 128-bit without the unlimited policy; 8u151+ enables it at runtime.
        // This is a DESKTOP-JVM artifact only -- ART/on-board has no such cap. Must run before any JCE use.
        try { java.security.Security.setProperty("crypto.policy", "unlimited"); } catch (Throwable ignore) {}
        File dir = Files.createTempDirectory("wl-keystore-probe").toFile();
        File noBackup = new File(dir, "no_backup");
        System.out.println("probe dir = " + noBackup);
        SoftwareAndroidKeyStore.install(noBackup);

        // 0. default-provider AES/GCM IV length on encrypt-without-params (the Tink 12-byte assumption)
        ivLengthDiagnostic();

        // 1. androidx AES256_GCM master key gen.
        //    NOTE: javax.crypto.KeyGenerator.getInstance(alg, provider) on a desktop JDK requires a
        //    JCE-CODE-SIGNED provider jar (NoSuchProviderException "cannot authenticate the provider"
        //    otherwise). That signing gate does NOT exist on ART/on-board. To exercise the REAL
        //    SoftwareAndroidKeyStore generation+persistence path without re-signing, drive its
        //    SecretKeyGenerator SPI directly (same engineInit/engineGenerateKey the KeyGenerator would
        //    call). KeyStore and Cipher below need no such authentication.
        KeyGenParameterSpec spec = new KeyGenParameterSpec.Builder(
                ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build();
        SecretKey generated = generateViaSpi("AES", spec);
        check("key gen: 256-bit AES (SoftwareAndroidKeyStore SPI)", generated != null
                && generated.getEncoded() != null && generated.getEncoded().length == 32,
                generated == null ? "null" : "algo=" + generated.getAlgorithm()
                        + " bytes=" + (generated.getEncoded() == null ? "opaque" : generated.getEncoded().length));

        // 2. Tink validateAead round-trip with the key fetched from the KeyStore (same process)
        byte[] ct = tinkValidateAead("same-process");

        // 3. persistence round-trip: drop the in-memory state, reload the key from the no_backup file,
        //    decrypt the earlier ciphertext (catches a serialize/reload mismatch = "exists but unusable")
        persistenceRoundTrip(ct);

        // Exercise the board probe's key-independent self-test on the desktop JVM (compile + smoke).
        System.out.println("\n-- KeystoreBoardProbe (board diagnostic, run on Mac for smoke) --");
        adapter.core.KeystoreBoardProbe.run(ALIAS);

        System.out.println("\n==== RESULT: " + pass + " passed, " + fail + " failed ====");
        System.out.println(fail == 0
                ? "KEYSTORE AES-GCM ROUND-TRIP OK on this JVM -> the keystore crypto is sound; an on-board "
                  + "AEADBadTag is NOT the key material (see localization notes in README)."
                : "KEYSTORE AES-GCM ROUND-TRIP FAILED on this JVM -> bug reproduced; see the failing sub-test.");
        System.exit(fail == 0 ? 0 : 1);
    }

    /** Tink AndroidKeystoreAesGcm encrypt -> decrypt with AAD; returns the ciphertext for reuse. */
    private static byte[] tinkValidateAead(String tag) throws Exception {
        KeyStore ks = KeyStore.getInstance(SoftwareAndroidKeyStore.NAME);
        ks.load(null);
        Key encKey = ks.getKey(ALIAS, null);
        Key decKey = ks.getKey(ALIAS, null);   // Tink fetches per-op; same alias must give the same key
        check(tag + ": getKey stable", encKey != null && decKey != null
                && Arrays.equals(encKey.getEncoded(), decKey.getEncoded()), "two getKey() calls equal");

        byte[] plaintext = "westlake-master-key-validate-aead".getBytes("UTF-8");
        byte[] aad = "androidx".getBytes("UTF-8");

        Cipher enc = Cipher.getInstance("AES/GCM/NoPadding");
        enc.init(Cipher.ENCRYPT_MODE, encKey);
        byte[] iv = enc.getIV();
        enc.updateAAD(aad);
        byte[] body = enc.doFinal(plaintext);
        byte[] out = new byte[IV + body.length];           // Tink framing: iv(12) || ciphertext
        System.arraycopy(iv, 0, out, 0, Math.min(iv.length, IV));
        System.arraycopy(body, 0, out, IV, body.length);
        check(tag + ": encrypt iv==12", iv.length == IV, "iv.length=" + iv.length
                + (iv.length == IV ? "" : " (Tink reads 12 -> wrong IV -> BadTag)"));

        try {
            Cipher dec = Cipher.getInstance("AES/GCM/NoPadding");
            dec.init(Cipher.DECRYPT_MODE, decKey, new GCMParameterSpec(TAG, out, 0, IV));
            dec.updateAAD(aad);
            byte[] round = dec.doFinal(out, IV, out.length - IV);
            check(tag + ": validateAead round-trip", Arrays.equals(plaintext, round), "decrypted==plaintext");
        } catch (javax.crypto.AEADBadTagException e) {
            check(tag + ": validateAead round-trip", false, "AEADBadTagException: mac check in GCM failed (THE on-board error)");
        }
        return out;
    }

    /** Simulate a fresh process: clear the static cache, reload from the persisted file, decrypt. */
    private static void persistenceRoundTrip(byte[] out) throws Exception {
        resetStatics();
        KeyStore ks = KeyStore.getInstance(SoftwareAndroidKeyStore.NAME);
        ks.load(null);                                     // triggers load() from the no_backup file
        Key reloaded = ks.getKey(ALIAS, null);
        check("persistence: key reloaded from file", reloaded != null && reloaded.getEncoded() != null
                && reloaded.getEncoded().length == 32, reloaded == null ? "null (not persisted!)"
                : "bytes=" + reloaded.getEncoded().length);
        if (reloaded == null) return;
        byte[] aad = "androidx".getBytes("UTF-8");
        try {
            Cipher dec = Cipher.getInstance("AES/GCM/NoPadding");
            dec.init(Cipher.DECRYPT_MODE, reloaded, new GCMParameterSpec(TAG, out, 0, IV));
            dec.updateAAD(aad);
            byte[] round = dec.doFinal(out, IV, out.length - IV);
            check("persistence: decrypt after reload", new String(round, "UTF-8").startsWith("westlake"), "ok");
        } catch (javax.crypto.AEADBadTagException e) {
            check("persistence: decrypt after reload", false, "AEADBadTag after reload = reloaded key != generated key");
        }
    }

    private static void ivLengthDiagnostic() throws Exception {
        KeyGenerator plain = KeyGenerator.getInstance("AES");
        plain.init(256);
        SecretKey k = plain.generateKey();
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.ENCRYPT_MODE, k);
        System.out.println("diag: default provider = " + c.getProvider().getName()
                + "; AES/GCM encrypt-without-params IV length = " + c.getIV().length + " bytes"
                + (c.getIV().length == IV ? " (matches Tink's 12)" : " (!= 12 -> Tink framing breaks)"));
    }

    @SuppressWarnings("unchecked")
    private static void resetStatics() throws Exception {
        Class<?> c = SoftwareAndroidKeyStore.class;
        Field entries = c.getDeclaredField("ENTRIES"); entries.setAccessible(true);
        ((Map<?, ?>) entries.get(null)).clear();
        Field loaded = c.getDeclaredField("sLoaded"); loaded.setAccessible(true);
        loaded.setBoolean(null, false);
    }

    /** Drive SoftwareAndroidKeyStore.SecretKeyGenerator's SPI directly (bypasses the desktop-only JCE
     *  provider-signing gate; identical engineInit/engineGenerateKey path the real KeyGenerator runs). */
    private static SecretKey generateViaSpi(String algorithm, KeyGenParameterSpec spec) throws Exception {
        Class<?> genCls = Class.forName("adapter.core.SoftwareAndroidKeyStore$SecretKeyGenerator");
        java.lang.reflect.Constructor<?> ctor = genCls.getDeclaredConstructor(String.class);
        ctor.setAccessible(true);
        Object g = ctor.newInstance(algorithm);
        java.lang.reflect.Method init = genCls.getDeclaredMethod("engineInit",
                java.security.spec.AlgorithmParameterSpec.class, java.security.SecureRandom.class);
        init.setAccessible(true);
        init.invoke(g, spec, null);
        java.lang.reflect.Method gen = genCls.getDeclaredMethod("engineGenerateKey");
        gen.setAccessible(true);
        return (SecretKey) gen.invoke(g);
    }

    private static void check(String name, boolean ok, String detail) {
        System.out.println((ok ? "  PASS " : "  FAIL ") + name + "  [" + detail + "]");
        if (ok) pass++; else fail++;
    }
}
