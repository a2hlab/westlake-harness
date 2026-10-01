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

    public static void run(String alias) {
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
