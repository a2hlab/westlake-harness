package com.android.internal.os;

import android.util.apk.ApkSignatureSchemeV2Verifier;
import android.util.apk.ApkSignatureSchemeV3Verifier;
import android.util.apk.SignatureNotFoundException;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.FileDescriptor;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.security.MessageDigest;
import java.security.cert.X509Certificate;
import java.util.List;

/** Host+device verifier bridge: verify APK signatures on a sealed snapshot path. */
public final class ApkSignatureBridge {
    private static final int RESULT_MAGIC = 0x41535631; // "ASV1"
    private static final int RESULT_VERSION = 1;
    private static final int SCHEME_V2 = 2;
    private static final int SCHEME_V3 = 3;
    private static final int MAX_CERTIFICATES = 64;
    private static final int MAX_CERT_BYTES = 16 * 1024;
    private static final int MAX_RESULT_BYTES = 64 * 1024;

    private static volatile boolean sCryptoEnsured;

    /** NIST vector: SHA-256("abc"). */
    private static final String SHA256_ABC =
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";

    private ApkSignatureBridge() {
    }

    /** Native signature: (Ljava/lang/String;I)[B */
    public static byte[] verify(String immutableApkPath, int minSchemeVersion) throws Exception {
        ensureCryptoServices();
        if (immutableApkPath == null || immutableApkPath.isEmpty()) {
            throw new IllegalArgumentException("immutableApkPath empty");
        }
        if (minSchemeVersion < SCHEME_V2 || minSchemeVersion > SCHEME_V3) {
            throw new IllegalArgumentException("unsupported minimum signature scheme");
        }

        try {
            ApkSignatureSchemeV3Verifier.VerifiedSigner signer =
                    ApkSignatureSchemeV3Verifier.verify(immutableApkPath);
            return encodeV3(immutableApkPath, signer);
        } catch (SignatureNotFoundException e) {
            if (minSchemeVersion > SCHEME_V2) {
                throw e;
            }
        }

        X509Certificate[][] signerChains;
        try {
            signerChains = ApkSignatureSchemeV2Verifier.verify(immutableApkPath);
        } catch (Throwable t) {
            logCauseChain("V2 verify", t);
            throw t;
        }
        return encodeV2(immutableApkPath, signerChains);
    }

    /**
     * Log a throwable and every {@code getCause()} below it.
     *
     * <p>{@code ApkSignatureSchemeV2Verifier} wraps the real failure (a missing JCA
     * algorithm, a bad key, a digest mismatch…) inside a generic
     * {@code SecurityException: Failed to parse/verify signer #1 block}, so the top-level
     * message alone never says which of those it was.
     */
    private static void logCauseChain(String what, Throwable t) {
        Throwable c = t;
        for (int depth = 0; c != null && depth < 8; depth++) {
            log(what + " cause[" + depth + "] " + c.getClass().getName() + ": " + c.getMessage());
            StackTraceElement[] st = c.getStackTrace();
            if (st != null && st.length > 0) {
                log(what + "   at " + st[0]);
            }
            if (c.getCause() == c) {
                break;
            }
            c = c.getCause();
        }
    }

    /**
     * Re-assert the JCA registrations that APK V2 verification depends on.
     *
     * <p>OH has no Conscrypt, and the AOSP-repackaged BouncyCastle ships the RSA
     * implementation classes but comments out their JCA registrations
     * ("Android-removed: Unsupported algorithm") on the assumption that Conscrypt owns
     * them. Without the registration {@code ApkSignatureSchemeV2Verifier} fails with
     * {@code SecurityException: Failed to parse/verify signer #1 block}.
     *
     * <p>{@code AppSpawnXInit.overrideJcaProvidersForOH()} performs the same registration at
     * zygote init; doing it here as well is idempotent and keeps the fix at the exact point
     * of use, so a runtime whose init path predates that fix still verifies correctly.
     */
    private static void ensureCryptoServices() {
        if (sCryptoEnsured) {
            return;
        }
        sCryptoEnsured = true;
        try {
            java.security.Provider bc = java.security.Security.getProvider("BC");
            if (bc == null) {
                log("BC provider absent — leaving JCA untouched");
                return;
            }
            registerIfMissing(bc, "Signature", "SHA256withRSA",
                    "com.android.org.bouncycastle.jcajce.provider.asymmetric.rsa"
                            + ".DigestSignatureSpi$SHA256",
                    new String[] {
                        "Alg.Alias.Signature.SHA256/RSA",
                        "Alg.Alias.Signature.SHA256WITHRSAENCRYPTION",
                        "Alg.Alias.Signature.1.2.840.113549.1.1.11",
                        "Alg.Alias.Signature.OID.1.2.840.113549.1.1.11",
                    });
            registerIfMissing(bc, "KeyFactory", "RSA",
                    "com.android.org.bouncycastle.jcajce.provider.asymmetric.rsa.KeyFactorySpi",
                    new String[] {});
            logCryptoSelfTest();
        } catch (Throwable t) {
            log("ensureCryptoServices failed: " + t);
        }
    }

    /**
     * Known-answer test for the primitives V2 verification is built on.
     *
     * <p>With {@code Signature.SHA256withRSA} registered, {@code verifySigner} still reports
     * "signature did not verify" — {@code Signature.verify()} returns false rather than
     * throwing. That can only mean a primitive underneath computes the wrong bytes, so pin
     * down which: report the serving provider for each service and check SHA-256 against the
     * NIST vector for "abc".
     */
    private static void logCryptoSelfTest() {
        try {
            StringBuilder providers = new StringBuilder();
            java.security.Provider[] all = java.security.Security.getProviders();
            for (int i = 0; all != null && i < all.length; i++) {
                if (i > 0) {
                    providers.append(", ");
                }
                providers.append(all[i].getName());
            }
            log("providers: " + providers);
        } catch (Throwable t) {
            log("provider enumeration threw: " + t);
        }
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] input = new byte[] {(byte) 'a', (byte) 'b', (byte) 'c'};
            String got = hex(md.digest(input));
            log("SHA-256 provider=" + md.getProvider().getName() + " sha256(abc)=" + got);
            log("SHA-256 known-answer " + (SHA256_ABC.equals(got) ? "MATCH" : "MISMATCH expected=" + SHA256_ABC));
        } catch (Throwable t) {
            log("SHA-256 self-test threw: " + t);
        }
        try {
            java.security.Signature sig = java.security.Signature.getInstance("SHA256withRSA");
            log("SHA256withRSA provider=" + sig.getProvider().getName());
        } catch (Throwable t) {
            log("SHA256withRSA lookup threw: " + t);
        }
    }

    private static String hex(byte[] bytes) {
        char[] digits = {'0', '1', '2', '3', '4', '5', '6', '7',
                         '8', '9', 'a', 'b', 'c', 'd', 'e', 'f'};
        char[] out = new char[bytes.length * 2];
        for (int i = 0; i < bytes.length; i++) {
            out[i * 2] = digits[(bytes[i] >> 4) & 0xf];
            out[i * 2 + 1] = digits[bytes[i] & 0xf];
        }
        return new String(out);
    }

    /**
     * Register {@code service.algorithm} on {@code provider} only if no provider already
     * offers it. If the entry does not take effect it is removed again, so a bad mapping can
     * never shadow a provider that would otherwise have served the algorithm.
     */
    private static void registerIfMissing(java.security.Provider provider, String service,
            String algorithm, String implClass, String[] aliases) {
        String key = service + "." + algorithm;
        if (isAvailable(service, algorithm)) {
            log(key + " already available");
            return;
        }
        try {
            provider.put(key, implClass);
            for (String alias : aliases) {
                provider.put(alias, algorithm);
            }
        } catch (Throwable t) {
            log("registering " + key + " threw: " + t);
            return;
        }
        if (isAvailable(service, algorithm)) {
            log("registered " + key + " = " + implClass);
            return;
        }
        try {
            provider.remove(key);
            for (String alias : aliases) {
                provider.remove(alias);
            }
        } catch (Throwable ignored) {
            // Best effort — the probe below is what callers actually depend on.
        }
        log("registering " + key + " had no effect — rolled back");
    }

    private static boolean isAvailable(String service, String algorithm) {
        try {
            if ("Signature".equals(service)) {
                return java.security.Signature.getInstance(algorithm) != null;
            }
            if ("KeyFactory".equals(service)) {
                return java.security.KeyFactory.getInstance(algorithm) != null;
            }
            return false;
        } catch (Throwable t) {
            return false;
        }
    }

    /**
     * Diagnostics that can never break verification, written straight to fd 2.
     *
     * <p>Neither {@code System.err.println} nor {@code android.util.Log} works in this
     * runtime (both observed silent-or-throwing on D600-C 5ce2dcee, 2026-07-27): appspawn-x
     * brings ART up imageless with a trimmed ICU, so anything that turns a {@code String}
     * into bytes goes through a null default {@code Charset} and dies with
     * {@code NullPointerException: Charset.newEncoder() on a null object reference}.
     *
     * <p>So encode to ASCII by hand and write the bytes to {@link FileDescriptor#err}, which
     * needs no path resolution and no charset. The appspawn-x wrapper points fd 2 at
     * {@code /data/local/tmp/appspawn-verifier-stderr.log}, so these land next to the native
     * {@code [AppSpawnX]} lines. The stream is deliberately never closed — closing it would
     * close fd 2 for the whole process.
     */
    private static void log(String message) {
        try {
            String line = "[ApkSignatureBridge] " + message + "\n";
            byte[] bytes = new byte[line.length()];
            for (int i = 0; i < line.length(); i++) {
                char ch = line.charAt(i);
                bytes[i] = (byte) (ch < 128 ? ch : '?');
            }
            FileOutputStream err = new FileOutputStream(FileDescriptor.err);
            err.write(bytes);
            err.flush();
        } catch (Throwable ignored) {
            // Diagnostics are best-effort — never let logging fail a verify.
        }
    }

    private static byte[] encodeV2(String immutableApkPath, X509Certificate[][] signerChains)
            throws Exception {
        return encode(immutableApkPath, SCHEME_V2, 0, signerChains, null, null);
    }

    private static byte[] encodeV3(
            String immutableApkPath, ApkSignatureSchemeV3Verifier.VerifiedSigner signer)
            throws Exception {
        X509Certificate[][] signerChains = new X509Certificate[][]{signer.certs};
        List<X509Certificate> lineage = signer.por == null ? null : signer.por.certs;
        List<Integer> lineageFlags = signer.por == null ? null : signer.por.flagsList;
        return encode(
                immutableApkPath, SCHEME_V3, signer.blockId, signerChains, lineage, lineageFlags);
    }

    private static byte[] encode(
            String immutableApkPath,
            int scheme,
            int blockId,
            X509Certificate[][] signerChains,
            List<X509Certificate> lineage,
            List<Integer> lineageFlags)
            throws Exception {
        if (signerChains == null || signerChains.length == 0 || signerChains.length > MAX_CERTIFICATES) {
            throw new SecurityException("invalid signer count");
        }
        if ((lineage == null) != (lineageFlags == null)
                || (lineage != null && lineage.size() != lineageFlags.size())) {
            throw new SecurityException("invalid proof-of-rotation shape");
        }

        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (DataOutputStream out = new DataOutputStream(bytes)) {
            out.writeInt(RESULT_MAGIC);
            out.writeShort(RESULT_VERSION);
            out.writeShort(scheme);
            out.writeInt(blockId);
            writeBlob(out, sha256(immutableApkPath));
            out.writeInt(signerChains.length);

            int totalCount = 0;
            for (X509Certificate[] chain : signerChains) {
                if (chain == null || chain.length == 0) {
                    throw new SecurityException("empty signer chain");
                }
                totalCount += chain.length;
                if (totalCount > MAX_CERTIFICATES) {
                    throw new SecurityException("too many signer certificates");
                }
                out.writeInt(chain.length);
                for (X509Certificate cert : chain) {
                    writeBlob(out, cert.getEncoded());
                }
            }

            int lineageCount = lineage == null ? 0 : lineage.size();
            if (totalCount + lineageCount > MAX_CERTIFICATES) {
                throw new SecurityException("too many lineage certificates");
            }
            out.writeInt(lineageCount);
            for (int i = 0; i < lineageCount; i++) {
                writeBlob(out, lineage.get(i).getEncoded());
                out.writeInt(lineageFlags.get(i));
            }
            out.flush();
        }

        byte[] result = bytes.toByteArray();
        if (result.length > MAX_RESULT_BYTES) {
            throw new SecurityException("signature result exceeds protocol limit");
        }
        return result;
    }

    private static byte[] sha256(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[64 * 1024];
        try (FileInputStream in = new FileInputStream(path)) {
            int count;
            while ((count = in.read(buffer)) != -1) {
                digest.update(buffer, 0, count);
            }
        }
        return digest.digest();
    }

    private static void writeBlob(DataOutputStream out, byte[] value) throws IOException {
        if (value == null || value.length == 0 || value.length > MAX_CERT_BYTES) {
            throw new SecurityException("invalid blob length");
        }
        out.writeInt(value.length);
        out.write(value);
    }
}
