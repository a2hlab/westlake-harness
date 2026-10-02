import java.lang.reflect.Method;
import java.security.Provider;
import java.security.SecureRandom;
import java.security.Security;
import java.util.Arrays;
import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * AES/GCM through adapter.core.GcmDefaultNonce, on Android's javax.crypto (run on ART with the deployed boot jars).
 * First the board's JCA setup: com.android.internal.os.AppSpawnXInit.overrideJcaProvidersForOH() from the runtime jar
 * (route A replaces the provider list with BC + CertPath before anything uses JCA; without it Android's Providers
 * <clinit> asserts on the missing com.android.org.conscrypt.JSSEProvider). If that method dies after rewriting the
 * properties (it logs through android.util.Log, which has no native backend on host ART), the rewrite it made is
 * checked and kept; the test refuses to run on any other provider list.
 * Prints one CASE line per check and exits 1 if any fails.
 *   1 no-parameter encrypt init -> doFinal -> decrypt with getIV() round trip (IV must be 12 bytes)
 *   2 explicit 12-byte IV + AAD round trip
 *   3 Tink framing: iv(12) || ct written from a parameterless encrypt, decrypted by reading the first 12 bytes
 *   4 adapter.core.KeystoreBoardProbe.selfTest() (the in-process [WL-KS-PROBE] self-test), output inspected by the caller
 */
public final class GcmAndroidTest {
    static int failures;

    static void report(String name, boolean ok, String detail) {
        System.out.println("CASE " + name + " " + (ok ? "PASS" : "FAIL") + " " + detail);
        if (!ok) failures++;
    }

    public static void main(String[] args) throws Exception {
        System.out.println("java.vm.name=" + System.getProperty("java.vm.name") + " java.vendor="
                + System.getProperty("java.vendor") + " Cipher from " + Cipher.class.getProtectionDomain());
        try {
            Method o = Class.forName("com.android.internal.os.AppSpawnXInit").getDeclaredMethod("overrideJcaProvidersForOH");
            o.setAccessible(true);
            o.invoke(null);
            System.out.println("overrideJcaProvidersForOH: returned");
        } catch (Throwable t) {
            System.out.println("overrideJcaProvidersForOH: threw " + (t.getCause() != null ? t.getCause() : t));
        }
        System.out.println("security.provider.1=" + Security.getProperty("security.provider.1")
                + " security.provider.2=" + Security.getProperty("security.provider.2")
                + " security.provider.3=" + Security.getProperty("security.provider.3"));
        if (!"com.android.org.bouncycastle.jce.provider.BouncyCastleProvider".equals(Security.getProperty("security.provider.1"))
                || Security.getProperty("security.provider.3") != null) {
            System.out.println("ABORT: provider list is not route A's (BC + CertPath)");
            System.exit(2);
        }
        Class.forName("adapter.core.GcmDefaultNonce").getMethod("install").invoke(null);
        StringBuilder sb = new StringBuilder();
        for (Provider p : Security.getProviders()) sb.append(p.getName()).append(' ');
        System.out.println("providers: " + sb);
        byte[] keyBytes = new byte[32];
        new SecureRandom().nextBytes(keyBytes);
        SecretKeySpec key = new SecretKeySpec(keyBytes, "AES");
        byte[] plain = "westlake gcm android semantics".getBytes("UTF-8");
        byte[] aad = "androidx".getBytes("UTF-8");

        try {
            Cipher enc = Cipher.getInstance("AES/GCM/NoPadding");
            enc.init(Cipher.ENCRYPT_MODE, key);
            byte[] ct = enc.doFinal(plain);
            byte[] iv = enc.getIV();
            Cipher dec = Cipher.getInstance("AES/GCM/NoPadding");
            dec.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, iv));
            byte[] back = dec.doFinal(ct);
            report("1-noparam-roundtrip", Arrays.equals(back, plain) && iv.length == 12,
                    "provider=" + enc.getProvider().getName() + " ivLen=" + iv.length + " ctLen=" + ct.length);
        } catch (Throwable t) {
            report("1-noparam-roundtrip", false, t.toString());
        }

        try {
            byte[] iv = new byte[12];
            new SecureRandom().nextBytes(iv);
            Cipher enc = Cipher.getInstance("AES/GCM/NoPadding");
            enc.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(128, iv));
            enc.updateAAD(aad);
            byte[] ct = enc.doFinal(plain);
            Cipher dec = Cipher.getInstance("AES/GCM/NoPadding");
            dec.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, iv));
            dec.updateAAD(aad);
            byte[] back = dec.doFinal(ct);
            report("2-explicit-iv-aad-roundtrip", Arrays.equals(back, plain), "ctLen=" + ct.length);
        } catch (Throwable t) {
            report("2-explicit-iv-aad-roundtrip", false, t.toString());
        }

        try {
            Cipher enc = Cipher.getInstance("AES/GCM/NoPadding");
            enc.init(Cipher.ENCRYPT_MODE, key);
            enc.updateAAD(aad);
            byte[] ct = enc.doFinal(plain);
            byte[] iv = enc.getIV();
            byte[] framed = new byte[iv.length + ct.length];
            System.arraycopy(iv, 0, framed, 0, iv.length);
            System.arraycopy(ct, 0, framed, iv.length, ct.length);
            Cipher dec = Cipher.getInstance("AES/GCM/NoPadding");
            dec.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, framed, 0, 12));
            dec.updateAAD(aad);
            byte[] back = dec.doFinal(framed, 12, framed.length - 12);
            report("3-tink-12-byte-nonce", Arrays.equals(back, plain), "ivLen=" + iv.length);
        } catch (Throwable t) {
            report("3-tink-12-byte-nonce", false, t.toString());
        }

        try {
            Method m = Class.forName("adapter.core.KeystoreBoardProbe").getDeclaredMethod("selfTest");
            m.setAccessible(true);
            System.out.flush();
            m.invoke(null);
            System.out.flush();
            System.out.println("CASE 4-wl-ks-probe-selftest RAN (verdict from its [WL-KS-PROBE] lines)");
        } catch (Throwable t) {
            report("4-wl-ks-probe-selftest", false, t.toString());
        }
        System.out.println("FAILURES " + failures);
        System.exit(failures == 0 ? 0 : 1);
    }
}
