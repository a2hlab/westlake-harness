package adapter.core;

import java.security.Key;
import java.security.KeyStore;
import java.util.Arrays;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * ON-BOARD diagnostic for cluster-4 keystore (moodcairns AEADBadTag). The Mac probe (KeystoreProbe)
 * passes 6/6, so the AES-GCM crypto + persistence are sound in isolation; the on-board BadTag is a
 * default-Cipher-provider / integration divergence that only a board run can show. Call
 * {@code KeystoreBoardProbe.run(alias)} once after the master key is created (or from a one-shot) and
 * read the [WL-KS-PROBE] lines from hilog: they print the DEFAULT provider name, the AES/GCM
 * encrypt-without-params IV length (Tink assumes 12), whether two getKey() calls return equal bytes,
 * and whether Tink's validateAead round-trip succeeds. This names the root before any fix.
 *
 * This is DIAGNOSTIC-ONLY (reads, logs; makes no persistent change). Not wired by default — cc-t3/cx
 * invokes it in the U11 window, or drop the body into SoftwareAndroidKeyStore.install() behind a flag.
 */
public final class KeystoreBoardProbe {
    private static final String T = "[WL-KS-PROBE] ";

    /**
     * KEY-INDEPENDENT self-test — call this at BIND time (post-bind, before any app key exists).
     * Generates a random 256-bit AES SecretKeySpec in-process and runs Tink's exact framing through
     * the DEFAULT AES/GCM/NoPadding provider (encrypt WITHOUT params -> getIV() -> iv||ct + AAD ->
     * decrypt). This directly tests the leading hypothesis (the on-board default Cipher provider's
     * GCM for a plain SecretKeySpec diverges from Tink's iv(12)||ct) without depending on the app's
     * master key, which post-bind usually does not exist yet. Logs provider name, IV length, round-trip.
     */
    public static void selfTest() {
        try {
            byte[] material = new byte[32];               // 256-bit, same as androidx AES256_GCM master key
            new java.security.SecureRandom().nextBytes(material);
            SecretKey key = new javax.crypto.spec.SecretKeySpec(material, "AES");  // plain key, like Store.engineGetKey returns
            byte[] pt = "wl-ks-selftest".getBytes("UTF-8");
            byte[] aad = "androidx".getBytes("UTF-8");

            Cipher enc = Cipher.getInstance("AES/GCM/NoPadding");
            enc.init(Cipher.ENCRYPT_MODE, key);           // no params: provider must auto-generate the IV
            byte[] iv = enc.getIV();
            enc.updateAAD(aad);
            byte[] body = enc.doFinal(pt);
            System.err.println(T + "selftest cipher provider=" + enc.getProvider().getName()
                    + " keyBits=256 ivLen=" + iv.length + " (Tink reads 12)"
                    + (iv.length == 12 ? "" : " <-- ivLen != 12: Tink iv(12)||ct framing breaks -> BadTag"));

            byte[] out = new byte[12 + body.length];      // Tink framing: iv(12) || ciphertext
            System.arraycopy(iv, 0, out, 0, Math.min(iv.length, 12));
            System.arraycopy(body, 0, out, 12, body.length);
            try {
                Cipher dec = Cipher.getInstance("AES/GCM/NoPadding");
                dec.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, out, 0, 12));
                dec.updateAAD(aad);
                boolean ok = Arrays.equals(pt, dec.doFinal(out, 12, out.length - 12));
                System.err.println(T + "selftest validateAead(random 256-bit SecretKeySpec)="
                        + (ok ? "OK -> default provider GCM is NOT the root (look elsewhere: key routing / dual provider)"
                              : "MISMATCH -> default provider GCM diverges (leading hypothesis confirmed)"));
            } catch (javax.crypto.AEADBadTagException e) {
                System.err.println(T + "selftest AEADBadTagException via default provider " + enc.getProvider().getName()
                        + " (ivLen=" + iv.length + ") -> REPRODUCES the on-board root WITHOUT the app master key");
            }
        } catch (Throwable t) {
            System.err.println(T + "selftest error (default provider cannot do AES/GCM for a plain SecretKeySpec?): " + t);
        }
    }

    /** App-master-key check (kept): runs the key-independent selfTest() first, then — only if the app
     *  master key already exists (post-bind it usually does not) — the per-key check below. */
    public static void run(String alias) {
        selfTest();                                       // always runs; does not need the app key
        try {
            KeyStore ks = KeyStore.getInstance(SoftwareAndroidKeyStore.NAME);
            ks.load(null);
            Key k1 = ks.getKey(alias, null);
            Key k2 = ks.getKey(alias, null);
            System.err.println(T + "alias=" + alias + " present=" + (k1 != null)
                    + " keyClass=" + (k1 == null ? "null" : k1.getClass().getName())
                    + " encodedLen=" + (k1 == null || k1.getEncoded() == null ? -1 : k1.getEncoded().length));
            if (k1 == null) { System.err.println(T + "key absent -> not the BadTag path"); return; }
            System.err.println(T + "getKey stable=" + Arrays.equals(k1.getEncoded(), k2.getEncoded()));

            byte[] pt = "wl-ks-probe".getBytes("UTF-8");
            byte[] aad = "androidx".getBytes("UTF-8");
            Cipher enc = Cipher.getInstance("AES/GCM/NoPadding");
            enc.init(Cipher.ENCRYPT_MODE, (SecretKey) k1);
            byte[] iv = enc.getIV();
            enc.updateAAD(aad);
            byte[] body = enc.doFinal(pt);
            System.err.println(T + "cipher provider=" + enc.getProvider().getName()
                    + " ivLen=" + iv.length + " (Tink reads 12)"
                    + (iv.length == 12 ? "" : " <-- != 12: Tink framing breaks -> BadTag"));

            byte[] out = new byte[12 + body.length];
            System.arraycopy(iv, 0, out, 0, Math.min(iv.length, 12));
            System.arraycopy(body, 0, out, 12, body.length);
            try {
                Cipher dec = Cipher.getInstance("AES/GCM/NoPadding");
                dec.init(Cipher.DECRYPT_MODE, (SecretKey) k2, new GCMParameterSpec(128, out, 0, 12));
                dec.updateAAD(aad);
                boolean ok = Arrays.equals(pt, dec.doFinal(out, 12, out.length - 12));
                System.err.println(T + "validateAead round-trip=" + (ok ? "OK (keystore usable here)"
                        : "MISMATCH (same error family as on-board)"));
            } catch (javax.crypto.AEADBadTagException e) {
                System.err.println(T + "validateAead AEADBadTagException -> REPRODUCED the on-board root "
                        + "(provider=" + enc.getProvider().getName() + ", ivLen=" + iv.length + ")");
            }
        } catch (Throwable t) {
            System.err.println(T + "probe error: " + t);
        }
    }

    private KeystoreBoardProbe() {}
}
