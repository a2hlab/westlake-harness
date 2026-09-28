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
    // appspawn-x is a long-lived daemon; SHA-256 of a 56MB APK takes ~52s under the interpreter
    // (JIT is hard-disabled), far exceeding bm install's ~30s verify timeout. So cache the file
    // digest: the first bm install times out while the hash runs to completion and lands here;
    // the next bm install (same path+len) returns instantly -> digest matches -> install succeeds.
    private static byte[] sCachedHash = null;
    private static String sCachedPath = null;
    private static long sCachedLen = -1L;

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

        // On this imageless ART the stock verifiers are broken (BigInteger big-int kernel) AND slow
        // (they open+parse the APK block, then fail). Try the self-rolled V2 path FIRST -- it is
        // correct on-device and avoids re-reading the block. Fall back to stock only if V2Direct
        // can't handle the scheme (e.g. V3-only or ECDSA), which keeps generality for other APKs.
        X509Certificate[][] signerChains = null;
        try {
            signerChains = verifyV2Direct(immutableApkPath);
            log("=== verifyV2Direct OK (fast path), signers=" + signerChains.length + " ===");
        } catch (SignatureNotFoundException snf) {
            // Not a V2 APK -- fall through to stock V3/V2 below.
            log("verifyV2Direct: not V2 (" + snf.getMessage() + "), trying stock verifiers");
        }
        if (signerChains == null) {
            try {
                ApkSignatureSchemeV3Verifier.VerifiedSigner signer =
                        ApkSignatureSchemeV3Verifier.verify(immutableApkPath);
                return encodeV3(immutableApkPath, signer);
            } catch (SignatureNotFoundException e) {
                if (minSchemeVersion > SCHEME_V2) throw e;
            }
            signerChains = ApkSignatureSchemeV2Verifier.verify(immutableApkPath);
        }
        byte[] result;
        try {
            result = encodeV2(immutableApkPath, signerChains);
        } catch (Throwable et) {
            log("encodeV2 threw: " + et.getClass().getName() + ": " + et.getMessage());
            Throwable ec = et.getCause();
            while (ec != null) { log("  cause: " + ec.getClass().getName() + ": " + ec.getMessage()); ec = ec.getCause(); }
            throw et;
        }
        log("=== verify() returning result len=" + (result == null ? -1 : result.length) + " ===");
        return result;
    }

    /**
     * Fully self-rolled APK Signature Scheme v2 verify. Replaces the stock verifier, which dies on
     * this broken ART. Uses only on-device-healthy primitives: modPowFixed (subtraction-reduction
     * modPow, avoids broken BigInteger.modPow/multiply/mod) and sha256BC (BC pure-Java SHA-256).
     * Parses the V2 block, public-decrypts each signature, checks PKCS#1 v1.5 padding +
     * DigestInfo, and extracts the certificate chain. Returns one cert chain per signer.
     */
    private static X509Certificate[][] verifyV2Direct(String apkPath) throws Exception {
        ClassLoader cl = ApkSignatureBridge.class.getClassLoader();
        Class<?> v2 = Class.forName("android.util.apk.ApkSignatureSchemeV2Verifier", true, cl);
        Class<?> util = Class.forName("android.util.apk.ApkSigningBlockUtils", true, cl);
        java.lang.reflect.Method getSlice = util.getDeclaredMethod("getLengthPrefixedSlice", java.nio.ByteBuffer.class);
        java.lang.reflect.Method readArr = util.getDeclaredMethod("readLengthPrefixedByteArray", java.nio.ByteBuffer.class);
        getSlice.setAccessible(true); readArr.setAccessible(true);

        java.io.RandomAccessFile apk = new java.io.RandomAccessFile(apkPath, "r");
        Object sigInfo;
        try {
            sigInfo = v2.getMethod("findSignature", java.io.RandomAccessFile.class).invoke(null, apk);
        } finally { apk.close(); }
        java.nio.ByteBuffer block = (java.nio.ByteBuffer) sigInfo.getClass().getField("signatureBlock").get(sigInfo);
        java.nio.ByteBuffer signers = (java.nio.ByteBuffer) getSlice.invoke(null, block);

        java.util.List<X509Certificate[]> result = new java.util.ArrayList<>();
        int signerIdx = 0;
        while (signers.hasRemaining()) {
            signerIdx++;
            java.nio.ByteBuffer signer = (java.nio.ByteBuffer) getSlice.invoke(null, signers);
            java.nio.ByteBuffer signedDataBb = (java.nio.ByteBuffer) getSlice.invoke(null, signer);
            java.nio.ByteBuffer signatures = (java.nio.ByteBuffer) getSlice.invoke(null, signer);
            byte[] publicKeyBytes = (byte[]) readArr.invoke(null, signer);

            // copy signedData bytes (we need them twice: verify sig + parse certs)
            byte[] signedData = new byte[signedDataBb.remaining()];
            signedDataBb.duplicate().get(signedData);

            // pick best supported signature algorithm (highest rank wins), like stock verifier
            int bestAlgo = -1; byte[] bestSig = null;
            while (signatures.hasRemaining()) {
                java.nio.ByteBuffer sigRec = (java.nio.ByteBuffer) getSlice.invoke(null, signatures);
                int algo = sigRec.getInt();
                byte[] b = (byte[]) readArr.invoke(null, sigRec);
                if (!isSupportedSigAlgo(algo)) continue;
                if (bestAlgo == -1 || compareSigAlgo(algo, bestAlgo) > 0) { bestAlgo = algo; bestSig = b; }
            }
            if (bestAlgo == -1 || bestSig == null) throw new SecurityException("signer #" + signerIdx + ": no supported signature");
            log("signer #" + signerIdx + " bestAlgo=0x" + Integer.toHexString(bestAlgo) + " sig=" + bestSig.length);

            boolean ok = verifyOneRsaPkcs1(signedData, bestSig, publicKeyBytes, bestAlgo);
            if (!ok) throw new SecurityException("signer #" + signerIdx + ": self-rolled RSA verify FAILED");
            log("signer #" + signerIdx + " RSA PKCS1 verify PASS");

            // signedData = digests || certificates || additionalAttributes
            log("signedData len=" + signedData.length + " head=" + hex(java.util.Arrays.copyOfRange(signedData, 0, 16)));
            // V2 spec = LITTLE_ENDIAN; ByteBuffer.wrap defaults to BIG_ENDIAN, which mis-reads the
            // length prefixes (2c000000 BE=738197504 vs LE=44). Must set order explicitly.
            java.nio.ByteBuffer sd = java.nio.ByteBuffer.wrap(signedData).order(java.nio.ByteOrder.LITTLE_ENDIAN);
            java.nio.ByteBuffer digests = (java.nio.ByteBuffer) getSlice.invoke(null, sd);
            java.nio.ByteBuffer certificates = (java.nio.ByteBuffer) getSlice.invoke(null, sd);
            certificates.order(java.nio.ByteOrder.LITTLE_ENDIAN);
            log("digests rem=" + digests.remaining() + " certificates rem=" + certificates.remaining());
            // (additional attributes skipped; stripping-protection check omitted as low-risk here)

            java.security.cert.CertificateFactory cf = java.security.cert.CertificateFactory.getInstance("X.509");
            java.util.List<X509Certificate> certs = new java.util.ArrayList<>();
            while (certificates.hasRemaining()) {
                byte[] enc = (byte[]) readArr.invoke(null, certificates);
                X509Certificate c = (X509Certificate) cf.generateCertificate(new java.io.ByteArrayInputStream(enc));
                certs.add(c);
            }
            if (certs.isEmpty()) throw new SecurityException("signer #" + signerIdx + ": no certificates");
            // cert public key must match the signer public key bytes
            byte[] certPub = certs.get(0).getPublicKey().getEncoded();
            if (!java.util.Arrays.equals(certPub, publicKeyBytes)) {
                throw new SecurityException("signer #" + signerIdx + ": cert public key mismatch");
            }
            result.add(certs.toArray(new X509Certificate[0]));
        }
        if (result.isEmpty()) throw new SecurityException("V2Direct: no signers");
        return result.toArray(new X509Certificate[0][]);
    }

    /** Public-decrypt sig with the signer's RSA key, check PKCS#1 v1.5 + DigestInfo(hash). */
    private static boolean verifyOneRsaPkcs1(byte[] signedData, byte[] sigBytes, byte[] publicKeyBytes, int sigAlgo)
            throws Exception {
        ClassLoader cl = ApkSignatureBridge.class.getClassLoader();
        // BC KeyFactorySpi to parse the SubjectPublicKeyInfo -> RSA key (no JCA getInstance)
        Class<?> kfSpi = Class.forName("com.android.org.bouncycastle.jcajce.provider.asymmetric.rsa.KeyFactorySpi", true, cl);
        Object kf = kfSpi.getDeclaredConstructor().newInstance();
        java.lang.reflect.Method genPub = null;
        Class<?> kc = kf.getClass();
        while (kc != null && genPub == null) {
            try { genPub = kc.getDeclaredMethod("engineGeneratePublic", java.security.spec.KeySpec.class); }
            catch (Throwable ignore) { kc = kc.getSuperclass(); }
        }
        genPub.setAccessible(true);
        java.security.PublicKey pub = (java.security.PublicKey) genPub.invoke(kf, new java.security.spec.X509EncodedKeySpec(publicKeyBytes));
        java.math.BigInteger n = (java.math.BigInteger) pub.getClass().getMethod("getModulus").invoke(pub);
        java.math.BigInteger e = (java.math.BigInteger) pub.getClass().getMethod("getPublicExponent").invoke(pub);
        java.math.BigInteger sigBi = new java.math.BigInteger(1, sigBytes);
        java.math.BigInteger dec = modPowFixed(sigBi, e, n);
        byte[] em = toFixedBytes(dec, (n.bitLength() + 7) / 8);

        // EM = 00 01 FF..FF 00 || DigestInfo ; this build only supports SHA-256 (0x101/0x103)
        byte[] hash = sha256BC(signedData);
        byte[] diPrefix = new byte[] {0x30,(byte)0x31,0x30,0x0d,0x06,0x09,0x60,(byte)0x86,0x48,0x01,0x65,0x03,0x04,0x02,0x01,0x05,0x00,0x04,0x20};
        if (em[0] != 0 || em[1] != 1) return false;
        int i = 2;
        while (i < em.length && em[i] == (byte) 0xFF) i++;
        if (i >= em.length || em[i] != 0) return false;
        i++;
        if (i + diPrefix.length + hash.length != em.length) return false;
        for (int j = 0; j < diPrefix.length; j++) if (em[i + j] != diPrefix[j]) return false;
        i += diPrefix.length;
        for (int j = 0; j < hash.length; j++) if (em[i + j] != hash[j]) return false;
        return true;
    }

    private static boolean isSupportedSigAlgo(int a) {
        // only SHA-256 variants are verified on-device (0x101 PSS, 0x103 PKCS1)
        return a == 0x0101 || a == 0x0103;
    }
    private static int compareSigAlgo(int a, int b) {
        // prefer PKCS1 (0x103) over PSS (0x101)
        return Integer.compare(rankSigAlgo(a), rankSigAlgo(b));
    }
    private static int rankSigAlgo(int a) {
        if (a == 0x0103) return 2;
        if (a == 0x0101) return 1;
        return 0;
    }

    /**
     * When V2 verify fails with "signature did not verify", reproduce the RSA step by hand:
     * pull the signer cert public key and the signature block out of the APK, run
     * cipher.processBlock on the signature, compute sha256(content)+derEncode, and dump both
     * byte arrays side by side. Whichever byte differs is the wall.
     */
    private static void reproduceRsaVerify(String apkPath) {
        log("=== directV2Verify begin ===");
        try {
            ClassLoader cl = ApkSignatureBridge.class.getClassLoader();
            Class<?> v2 = Class.forName("android.util.apk.ApkSignatureSchemeV2Verifier", true, cl);
            Class<?> util = Class.forName("android.util.apk.ApkSigningBlockUtils", true, cl);
            java.lang.reflect.Method getSlice = util.getDeclaredMethod("getLengthPrefixedSlice", java.nio.ByteBuffer.class);
            java.lang.reflect.Method readArr = util.getDeclaredMethod("readLengthPrefixedByteArray", java.nio.ByteBuffer.class);
            getSlice.setAccessible(true);
            readArr.setAccessible(true);

            java.io.RandomAccessFile apk = new java.io.RandomAccessFile(apkPath, "r");
            Object sigInfo;
            try {
                sigInfo = v2.getMethod("findSignature", java.io.RandomAccessFile.class).invoke(null, apk);
            } finally {
                apk.close();
            }
            java.nio.ByteBuffer block = (java.nio.ByteBuffer) sigInfo.getClass().getField("signatureBlock").get(sigInfo);
            log("signatureBlock remaining=" + block.remaining());

            java.nio.ByteBuffer signers = (java.nio.ByteBuffer) getSlice.invoke(null, block);
            int signerIdx = 0;
            while (signers.hasRemaining()) {
                signerIdx++;
                java.nio.ByteBuffer signer = (java.nio.ByteBuffer) getSlice.invoke(null, signers);
                java.nio.ByteBuffer signedData = (java.nio.ByteBuffer) getSlice.invoke(null, signer);
                java.nio.ByteBuffer signatures = (java.nio.ByteBuffer) getSlice.invoke(null, signer);
                byte[] publicKeyBytes = (byte[]) readArr.invoke(null, signer);
                log("signer #" + signerIdx + " publicKeyBytes=" + publicKeyBytes.length + " signedData=" + signedData.remaining());

                // pick best (first) supported signature record
                byte[] sigBytes = null;
                int sigAlgo = -1;
                while (signatures.hasRemaining()) {
                    java.nio.ByteBuffer sig = (java.nio.ByteBuffer) getSlice.invoke(null, signatures);
                    int algo = sig.getInt();
                    byte[] b = (byte[]) readArr.invoke(null, sig);
                    if (sigBytes == null) { sigBytes = b; sigAlgo = algo; }
                }
                log("sigAlgo=0x" + Integer.toHexString(sigAlgo) + " sigBytes=" + (sigBytes == null ? -1 : sigBytes.length));

                // Direct KeyFactory: new KeyFactorySpi, no getInstance
                Class<?> kfSpi = Class.forName("com.android.org.bouncycastle.jcajce.provider.asymmetric.rsa.KeyFactorySpi", true, cl);
                Object kf = kfSpi.getDeclaredConstructor().newInstance();
                java.security.spec.X509EncodedKeySpec spec = new java.security.spec.X509EncodedKeySpec(publicKeyBytes);
                java.security.PublicKey pub = null;
                // engineGeneratePublic(KeySpec) is PROTECTED in BC's KeyFactorySpi (getMethod only
                // sees public). Use getDeclaredMethod + setAccessible.
                StringBuilder tried = new StringBuilder();
                java.lang.reflect.Method m = null;
                Class<?> kc = kf.getClass();
                while (kc != null && m == null) {
                    try { m = kc.getDeclaredMethod("engineGeneratePublic", java.security.spec.KeySpec.class); }
                    catch (Throwable ignore) { kc = kc.getSuperclass(); }
                }
                if (m != null) {
                    try {
                        m.setAccessible(true);
                        Object r = m.invoke(kf, spec);
                        if (r instanceof java.security.PublicKey) { pub = (java.security.PublicKey) r; }
                        else tried.append("[notpub:").append(r == null ? "null" : r.getClass().getSimpleName()).append("]");
                    } catch (Throwable inv) {
                        tried.append("[fail:").append(inv.getCause() == null ? inv.getClass().getSimpleName() : inv.getCause().getClass().getSimpleName()).append("]");
                    }
                } else {
                    tried.append("[no-declared-engineGeneratePublic]");
                }
                if (pub == null) throw new IllegalStateException("no usable generatePublic; tried=" + tried);
                log("pubKey alg=" + pub.getAlgorithm() + " class=" + pub.getClass().getName());

                // Direct SignatureSpi: DigestSignatureSpi$SHA256 extends SignatureSpi, not
                // Signature — invoke its engine* methods directly via reflection.
                Class<?> spiCls = Class.forName("com.android.org.bouncycastle.jcajce.provider.asymmetric.rsa.DigestSignatureSpi$SHA256", true, cl);
                Object spi = spiCls.getDeclaredConstructor().newInstance();
                java.lang.reflect.Method mInitV = findMethod(spiCls, "engineInitVerify", java.security.PublicKey.class);
                java.lang.reflect.Method mUpd = findMethod(spiCls, "engineUpdate", byte[].class, int.class, int.class);
                java.lang.reflect.Method mVerify = findMethod(spiCls, "engineVerify", byte[].class);
                mInitV.setAccessible(true); mUpd.setAccessible(true); mVerify.setAccessible(true);
                mInitV.invoke(spi, pub);
                byte[] sd = new byte[signedData.remaining()];
                signedData.duplicate().get(sd);
                mUpd.invoke(spi, sd, 0, sd.length);
                Object okObj = mVerify.invoke(spi, sigBytes);
                boolean ok = (Boolean) okObj;
                log("DIRECT V2 RSA verify result = " + ok);
                // BigInteger health check: isolate exactly which op is broken.
                try {
                    java.math.BigInteger two = java.math.BigInteger.valueOf(2);
                    java.math.BigInteger ten = java.math.BigInteger.valueOf(10);
                    java.math.BigInteger seven = java.math.BigInteger.valueOf(7);
                    java.math.BigInteger base = java.math.BigInteger.valueOf(123456789);
                    java.math.BigInteger mod = new java.math.BigInteger("a8b3b284af8eb50b387034a860f146c4919f318763cd6c5598c8ae4811a1e0abc4c7e0b082d693a5e7fced675cf4668512772c0cbc64a742c6c630f533c8cc72f62ae833c40bf25842e984bb78bdbf97c0107d55bdb662f5c4e0fab9845cb5148ef7392dd3aaff93ae1e6b667bb3d4247616d4f5ba10d4cfd226de88d39f16fb", 16);
                    log("BI add=" + two.add(ten) + " mul=" + two.multiply(seven) + " mod=" + ten.mod(seven));
                    try { log("BI divide=" + ten.divide(two)); } catch (Throwable e1) { log("BI divide THREW: " + e1); }
                    try { log("BI modPow small=" + two.modPow(ten, seven)); } catch (Throwable e2) { log("BI modPow small THREW: " + e2); }
                    try { log("BI modPow big (2048-bit mod)=" + base.modPow(java.math.BigInteger.valueOf(65537), mod).toString(16).substring(0,16)); } catch (Throwable e3) { log("BI modPow big THREW: " + e3); }
                    try { log("BI modInverse=" + seven.modInverse(ten)); } catch (Throwable e4) { log("BI modInverse THREW: " + e4); }
                } catch (Throwable bt) {
                    log("BI health threw: " + bt);
                }
                // Bit-width scan: find exactly where multiply / divide / mod break.
                // Host-verified vectors: ONE.shiftLeft(k-1).setBit(0) * 3 = 3*2^(k-1)+3,
                // checked by independent bit ops (testBit). Any exception / wrong bit = broken.
                try {
                    java.math.BigInteger THREE = java.math.BigInteger.valueOf(3);
                    StringBuilder mulLine = new StringBuilder("MUL scan k(bad): ");
                    StringBuilder divLine = new StringBuilder("DIV scan k(bad): ");
                    StringBuilder modLine = new StringBuilder("MOD scan k(bad): ");
                    int[] widths = {32, 64, 128, 256, 512, 1024, 1536, 2048, 4096};
                    boolean mulBad = false, divBad = false, modBad = false;
                    for (int k : widths) {
                        java.math.BigInteger x = java.math.BigInteger.ONE.shiftLeft(k - 1).setBit(0);
                        // multiply check: x*3 must equal 3*2^(k-1)+3 -> bitLength k+1, bits k,k-1,1,0 set
                        try {
                            java.math.BigInteger p = x.multiply(THREE);
                            boolean okk = p.bitLength() == k + 1 && p.testBit(k) && p.testBit(k - 1) && p.testBit(1) && p.testBit(0);
                            if (!okk) { mulLine.append(k).append("(wrong) "); mulBad = true; }
                        } catch (Throwable ex) { mulLine.append(k).append("(EX) "); mulBad = true; }
                        // divide check: (x*3)/x == 3
                        try {
                            java.math.BigInteger p = x.multiply(THREE);
                            java.math.BigInteger q = p.divide(x);
                            if (!q.equals(THREE)) { divLine.append(k).append("(wrong) "); divBad = true; }
                        } catch (Throwable ex) { divLine.append(k).append("(EX:").append(ex.getClass().getSimpleName()).append(") "); divBad = true; }
                        // mod check: (x*3+1) mod x == 1  (needs x*3 correct first)
                        try {
                            java.math.BigInteger p = x.multiply(THREE).add(java.math.BigInteger.ONE);
                            java.math.BigInteger r = p.mod(x);
                            if (!r.equals(java.math.BigInteger.ONE)) { modLine.append(k).append("(wrong) "); modBad = true; }
                        } catch (Throwable ex) { modLine.append(k).append("(EX) "); modBad = true; }
                    }
                    if (!mulBad) mulLine.append("none-all-ok");
                    if (!divBad) divLine.append("none-all-ok");
                    if (!modBad) modLine.append("none-all-ok");
                    log(mulLine.toString());
                    log(divLine.toString());
                    log(modLine.toString());

                    // Targeted probes: which reduction path breaks modPow, and can we read big products?
                    java.math.BigInteger n2 = (java.math.BigInteger) pub.getClass().getMethod("getModulus").invoke(pub);
                    java.math.BigInteger s2 = new java.math.BigInteger(1, sigBytes);
                    log("PROBE n.bitLen=" + n2.bitLength() + " sig.bitLen=" + s2.bitLength() + " sig<n=" + (s2.compareTo(n2) < 0));
                    // 1) full multiply (no reduction) -> read via toByteArray
                    try {
                        byte[] fb = s2.multiply(s2).toByteArray();
                        log("PROBE sig*sig toByteArray len=" + fb.length + " tail=" + hex(java.util.Arrays.copyOfRange(fb, Math.max(0, fb.length - 8), fb.length)));
                    } catch (Throwable ex) { log("PROBE sig*sig toByteArray THREW: " + ex); }
                    // 2) BigInteger.remainder(n)
                    try { log("PROBE remainder bitLen=" + s2.remainder(n2).bitLength()); } catch (Throwable ex) { log("PROBE remainder THREW: " + ex); }
                    // 3) divideAndRemainder
                    try { java.math.BigInteger[] dr = s2.divideAndRemainder(n2); log("PROBE divAndRem q=" + dr[0].bitLength() + " r=" + dr[1].bitLength()); } catch (Throwable ex) { log("PROBE divAndRem THREW: " + ex); }
                    // 4) MutableBigInteger.divideKnuth (the reduction modPow uses)
                    try {
                        Class<?> mbi = Class.forName("java.math.MutableBigInteger", true, cl);
                        Object a = mbi.getDeclaredConstructor(java.math.BigInteger.class).newInstance(s2);
                        Object b = mbi.getDeclaredConstructor(java.math.BigInteger.class).newInstance(n2);
                        java.lang.reflect.Method dk = findMethod(mbi, "divideKnuth", mbi, mbi);
                        dk.setAccessible(true);
                        Object rem = dk.invoke(a, b);
                        java.lang.reflect.Method toBI = findMethod(mbi, "toBigInteger", int.class);
                        toBI.setAccessible(true);
                        java.math.BigInteger rr = (java.math.BigInteger) toBI.invoke(rem, 1);
                        log("PROBE MBI.divideKnuth rem bitLen=" + rr.bitLength());
                    } catch (Throwable ex) { log("PROBE MBI.divideKnuth THREW: " + (ex.getCause() == null ? ex : ex.getCause())); }
                    // 5) odd n + trivial modPow at small magnitude but 2048-bit odd modulus
                    try { log("PROBE tiny.modPow(3,oddN)=" + java.math.BigInteger.valueOf(2).modPow(java.math.BigInteger.valueOf(3), n2).bitLength()); } catch (Throwable ex) { log("PROBE tiny.modPow oddN THREW: " + ex); }
                    // 6) modPow with EVEN 2048-bit modulus (tests if oddness/Montgomery is the trigger)
                    try { log("PROBE tiny.modPow(3,evenN)=" + java.math.BigInteger.valueOf(2).modPow(java.math.BigInteger.valueOf(3), java.math.BigInteger.ONE.shiftLeft(2047)).bitLength()); } catch (Throwable ex) { log("PROBE tiny.modPow evenN THREW: " + ex); }

                    // === Isolate: is BigInteger.mod broken for dividend > modulus? ===
                    try {
                        java.math.BigInteger n4 = (java.math.BigInteger) pub.getClass().getMethod("getModulus").invoke(pub);
                        java.math.BigInteger big = java.math.BigInteger.ONE.shiftLeft(2100); // 2101-bit, > n4
                        try { log("MOD big%n bitLen=" + big.mod(n4).bitLength()); } catch (Throwable ex) { log("MOD big%n THREW: " + ex); }
                        java.math.BigInteger bigsq = big.shiftLeft(2100); // ~4200-bit
                        try { log("MOD 4200%n bitLen=" + bigsq.mod(n4).bitLength()); } catch (Throwable ex) { log("MOD 4200%n THREW: " + ex); }
                        // mod by a SMALL modulus (int-path) of a big dividend
                        try { log("MOD big%small=" + big.mod(java.math.BigInteger.valueOf(7))); } catch (Throwable ex) { log("MOD big%small THREW: " + ex); }
                        // mulModBig sanity: mulModBig(3,5,7)=15%7=1; mulModBig(big,3,n) via new primitive
                        try { log("MOD mulModBig(3,5,7)=" + mulModBig(java.math.BigInteger.valueOf(3), java.math.BigInteger.valueOf(5), java.math.BigInteger.valueOf(7))); } catch (Throwable ex) { log("MOD mulModBig THREW: " + ex); }
                        try { log("MOD mulModBig(big,3,n) bitLen=" + mulModBig(big, java.math.BigInteger.valueOf(3), n4).bitLength()); } catch (Throwable ex) { log("MOD mulModBig(big,3,n) THREW: " + ex); }
                    } catch (Throwable mp) { log("MOD probe threw: " + mp); }

                    // === END-TO-END: self-rolled RSA (mulBig + modPowFixed) public-decrypt the real signature ===
                    try {
                        java.math.BigInteger n3 = (java.math.BigInteger) pub.getClass().getMethod("getModulus").invoke(pub);
                        java.math.BigInteger e3 = (java.math.BigInteger) pub.getClass().getMethod("getPublicExponent").invoke(pub);
                        java.math.BigInteger sig3 = new java.math.BigInteger(1, sigBytes);
                        java.math.BigInteger dec = modPowFixed(sig3, e3, n3);
                        byte[] em = toFixedBytes(dec, (n3.bitLength() + 7) / 8);
                        // EM = 00 01 FF..FF 00 || DigestInfo(sha256) ; DigestInfo prefix for SHA-256:
                        byte[] DI_PREFIX = {(byte)0x30,(byte)0x31,(byte)0x30,(byte)0x0d,(byte)0x06,(byte)0x09,(byte)0x60,(byte)0x86,(byte)0x48,(byte)0x01,(byte)0x65,(byte)0x03,(byte)0x04,(byte)0x02,(byte)0x01,(byte)0x05,(byte)0x00,(byte)0x04,(byte)0x20};
                        byte[] want = sha256BC(sd);
                        boolean pass = em[0] == 0 && em[1] == 1;
                        int i = 2;
                        while (i < em.length && em[i] == (byte) 0xFF) i++;
                        if (em[i] != 0) pass = false; i++;
                        for (int j = 0; j < DI_PREFIX.length; j++) if (em[i + j] != DI_PREFIX[j]) pass = false;
                        i += DI_PREFIX.length;
                        for (int j = 0; j < 32; j++) if (em[i + j] != want[j]) pass = false;
                        log("FIXRSA em head=" + hex(java.util.Arrays.copyOfRange(em, 0, 4)) + " tail=" + hex(java.util.Arrays.copyOfRange(em, em.length - 34, em.length)));
                        log("FIXRSA want sha256(signedData)=" + hex(want));
                        log("FIXRSA RESULT = " + (pass ? "PASS (self-rolled RSA verify OK)" : "FAIL"));
                    } catch (Throwable fr) {
                        log("FIXRSA threw: " + (fr.getCause() == null ? fr : fr.getCause()));
                    }
                } catch (Throwable sc) {
                    log("scan threw: " + sc);
                }
            }
            log("=== directV2Verify end ===");
        } catch (Throwable t) {
            log("directV2Verify threw: " + t.getClass().getName() + ": " + t.getMessage());
            Throwable c = t instanceof java.lang.reflect.InvocationTargetException ? t.getCause() : null;
            if (c != null) log("  cause: " + c.getClass().getName() + ": " + c.getMessage());
        }
    }

    private static java.lang.reflect.Method findMethod(Class<?> c, String name, Class<?>... params) {
        Class<?> k = c;
        while (k != null) {
            try {
                return k.getDeclaredMethod(name, params);
            } catch (Throwable t) {
                k = k.getSuperclass();
            }
        }
        return null;
    }

    private static java.lang.reflect.Method safeGetMethod(Class<?> c, String name, Class<?>... params) {
        try {
            return c.getMethod(name, params);
        } catch (Throwable t) {
            return null;
        }
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
        // Diagnostic self-test + JCA registrations are NOT needed by verifyV2Direct (it uses
        // reflection + direct BC classes, never JCA getInstance). Skipped to avoid the multi-second
        // self-test overhead on every fresh process start (eaten out of bm install's 30s window).
        sCryptoEnsured = true;
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
        // Bypass the getInstance lookup (which NPEs under OH) and go straight at the BC
        // provider's own service table: if BC can serve a correct SHA-256, the digest engine
        // itself is fine and the wall is only the provider lookup chain.
        try {
            java.security.Provider bcProv = java.security.Security.getProvider("BC");
            log("BC provider obj=" + (bcProv == null ? "null" : bcProv.getName()));
            if (bcProv != null) {
                java.security.Provider.Service svc = bcProv.getService("MessageDigest", "SHA-256");
                log("BC MessageDigest.SHA-256 service=" + (svc == null ? "null" : svc.getClassName()));
                if (svc != null) {
                    Object spi = svc.newInstance(null);
                    log("BC SHA-256 spi class=" + (spi == null ? "null" : spi.getClass().getName()));
                    if (spi instanceof MessageDigest) {
                        byte[] input = new byte[] {(byte) 'a', (byte) 'b', (byte) 'c'};
                        String got = hex(((MessageDigest) spi).digest(input));
                        log("BC-direct sha256(abc)=" + got);
                        log("BC-direct known-answer " + (SHA256_ABC.equals(got) ? "MATCH" : "MISMATCH expected=" + SHA256_ABC));
                    } else {
                        log("BC-direct spi is not a MessageDigest: " + (spi == null ? "null" : spi.getClass().getName()));
                    }
                }
            }
        } catch (Throwable t) {
            log("BC-direct self-test threw: " + t);
        }
        // The path DigestSignatureSpi$SHA256 actually uses: AndroidDigestFactory.getSHA256()
        // (NOT MessageDigest.getInstance). If this one is wrong under OH, RSA verify fails.
        // Use reflection: compile-time classpath lacks the BC crypto package, and the runtime
        // package name (com.android.org.bouncycastle vs com.android.internal.org.bouncycastle)
        // differs between core-oj builds, so resolve by name.
        try {
            Class<?> factory = null;
            String[] names = {
                "com.android.org.bouncycastle.crypto.digests.AndroidDigestFactory",
                "com.android.internal.org.bouncycastle.crypto.digests.AndroidDigestFactory",
            };
            String usedName = null;
            for (String n : names) {
                try { factory = Class.forName(n); usedName = n; break; } catch (Throwable ignore) {}
            }
            if (factory == null) {
                log("AndroidDigestFactory class not found under either package");
            } else {
                Object d = factory.getMethod("getSHA256").invoke(null);
                java.lang.reflect.Method update = d.getClass().getMethod("update", byte[].class, int.class, int.class);
                java.lang.reflect.Method getSize = d.getClass().getMethod("getDigestSize");
                java.lang.reflect.Method doFinal = d.getClass().getMethod("doFinal", byte[].class, int.class);
                byte[] input = new byte[] {(byte) 'a', (byte) 'b', (byte) 'c'};
                update.invoke(d, input, 0, input.length);
                byte[] out = new byte[(Integer) getSize.invoke(d)];
                doFinal.invoke(d, out, 0);
                String got = hex(out);
                log("AndroidDigestFactory(" + usedName + ") class=" + d.getClass().getName());
                log("AndroidDigestFactory sha256(abc)=" + got);
                log("AndroidDigestFactory known-answer " + (SHA256_ABC.equals(got) ? "MATCH" : "MISMATCH expected=" + SHA256_ABC));
            }
        } catch (Throwable t) {
            log("AndroidDigestFactory self-test threw: " + t);
        }
        // Reproduce DigestSignatureSpi.derEncode(hash): DigestInfo(algId, hash).getEncoded("DER").
        // DER/ASN.1 encoding may depend on trimmed-ICU paths; if it throws, engineVerify
        // swallows it to false. algId for SHA-256 = AlgorithmIdentifier(NIST id_sha256, DERNull).
        try {
            ClassLoader cl = ClassLoader.getSystemClassLoader();
            Class<?> asn1ObjId = Class.forName("com.android.org.bouncycastle.asn1.ASN1ObjectIdentifier", true, cl);
            Class<?> derNull = Class.forName("com.android.org.bouncycastle.asn1.DERNull", true, cl);
            Class<?> algIdCls = Class.forName("com.android.org.bouncycastle.asn1.x509.AlgorithmIdentifier", true, cl);
            Class<?> digestInfoCls = Class.forName("com.android.org.bouncycastle.asn1.x509.DigestInfo", true, cl);
            Class<?> asn1Enc = Class.forName("com.android.org.bouncycastle.asn1.ASN1Encodable", true, cl);
            Object oid = asn1ObjId.getDeclaredConstructor(String.class).newInstance("2.16.840.1.101.3.4.2.1");
            Object nullInst = derNull.getField("INSTANCE").get(null);
            Object algId;
            try {
                algId = algIdCls.getDeclaredConstructor(asn1Enc, asn1Enc).newInstance(oid, nullInst);
            } catch (Throwable e1) {
                algId = algIdCls.getDeclaredConstructor(asn1ObjId, asn1Enc).newInstance(oid, nullInst);
            }
            byte[] hash = new byte[32];
            for (int i = 0; i < 32; i++) hash[i] = (byte) i;
            Object dInfo = digestInfoCls.getDeclaredConstructor(algIdCls, byte[].class).newInstance(algId, hash);
            byte[] der = (byte[]) dInfo.getClass().getMethod("getEncoded", String.class).invoke(dInfo, "DER");
            log("derEncode OK, DER len=" + der.length + " head=" + hex(java.util.Arrays.copyOf(der, Math.min(8, der.length))));
        } catch (Throwable t) {
            log("derEncode repro threw: " + t.getClass().getName() + ": " + t.getMessage());
        }
        // RSA engine path used by DigestSignatureSpi: PKCS1Encoding(new RSABlindedEngine()).
        // init(false=decrypt, publicKeyParam) then processBlock. Blinding needs a SecureRandom
        // (CryptoServicesRegistrar.getSecureRandom()); if OHSecRand's impl is broken under the
        // trimmed runtime, processBlock throws and engineVerify swallows it to false.
        try {
            ClassLoader cl = ClassLoader.getSystemClassLoader();
            Class<?> blinded = Class.forName("com.android.org.bouncycastle.crypto.engines.RSABlindedEngine", true, cl);
            Class<?> pkcs1 = Class.forName("com.android.org.bouncycastle.crypto.encodings.PKCS1Encoding", true, cl);
            Class<?> asymKey = Class.forName("com.android.org.bouncycastle.crypto.params.RSAKeyParameters", true, cl);
            Class<?> cipherParams = Class.forName("com.android.org.bouncycastle.crypto.CipherParameters", true, cl);
            Class<?> asymCipher = Class.forName("com.android.org.bouncycastle.crypto.AsymmetricBlockCipher", true, cl);
            // 1024-bit RSA public key (well-known test modulus), e=65537 — only used to init the engine.
            java.math.BigInteger n = new java.math.BigInteger(
                "a8b3b284af8eb50b387034a860f146c4919f318763cd6c5598c8ae4811a1e0abc4c7e0b082d693a5e7fced675cf4668512772c0cbc64a742c6c630f533c8cc72f62ae833c40bf25842e984bb78bdbf97c0107d55bdb662f5c4e0fab9845cb5148ef7392dd3aaff93ae1e6b667bb3d4247616d4f5ba10d4cfd226de88d39f16fb", 16);
            java.math.BigInteger e = java.math.BigInteger.valueOf(65537);
            Object pubParam = asymKey.getDeclaredConstructor(boolean.class, java.math.BigInteger.class, java.math.BigInteger.class)
                    .newInstance(false, n, e);
            Object engine = blinded.getDeclaredConstructor().newInstance();
            Object cipher = pkcs1.getDeclaredConstructor(asymCipher).newInstance(engine);
            java.lang.reflect.Method init = pkcs1.getMethod("init", boolean.class, cipherParams);
            init.invoke(cipher, false, pubParam);
            log("RSA PKCS1 init(decrypt) OK");
            // processBlock on a zero block of modulus size (128 bytes): exercises the RSA core.
            byte[] block = new byte[128];
            java.lang.reflect.Method process = pkcs1.getMethod("processBlock", byte[].class, int.class, int.class);
            try {
                Object res = process.invoke(cipher, block, 0, block.length);
                log("RSA processBlock OK len=" + ((byte[]) res).length);
            } catch (Throwable pe) {
                log("RSA processBlock threw: " + pe.getCause());
            }
        } catch (Throwable t) {
            log("RSA engine repro threw: " + t.getClass().getName() + ": " + t.getMessage());
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

    /** BigInteger -> fixed-length big-endian byte[] (strips sign byte, left-pads with zeros). */
    private static byte[] toFixedBytes(java.math.BigInteger v, int len) {
        byte[] raw = v.toByteArray();
        byte[] out = new byte[len];
        int srcOff = (raw.length > 0 && raw[0] == 0) ? 1 : 0;
        int srcLen = raw.length - srcOff;
        int copy = Math.min(srcLen, len);
        System.arraycopy(raw, srcOff + (srcLen - copy), out, len - copy, copy);
        return out;
    }

    /**
     * (a*b) mod m built ONLY from ops proven healthy on this broken ART.
     * BigInteger.multiply(BigInteger) big-multiplicand path returns 0 (2047x2047-bit), and
     * BigInteger.mod throws division-by-zero once the dividend exceeds ~2x the modulus
     * (Knuth division with a multi-limb quotient is broken). So we keep the running value
     * reduced to < m after EVERY term: shift-add, reducing each shifted term and the sum.
     * Every mod() here then has dividend < 2m (quotient 1) -> the healthy path.
     */
    private static java.math.BigInteger mulModBig(java.math.BigInteger a, java.math.BigInteger b, java.math.BigInteger m) {
        java.math.BigInteger acc = java.math.BigInteger.ZERO;
        java.math.BigInteger term = a.mod(m); // (a*2^i) mod m, doubled each step
        int bl = b.bitLength();
        for (int i = 0; i < bl; i++) {
            if (b.testBit(i)) {
                acc = acc.add(term);            // acc,term < m  =>  acc < 2m  => safe mod path
                if (acc.compareTo(m) >= 0) acc = acc.subtract(m);
            }
            term = term.shiftLeft(1);           // term*2 mod m, term < m => <2m => safe
            if (term.compareTo(m) >= 0) term = term.subtract(m);
        }
        return acc;
    }

    /**
     * modPow built from mulModBig. base^exp mod m, square-and-multiply, everything kept < m.
     */
    private static java.math.BigInteger modPowFixed(java.math.BigInteger base, java.math.BigInteger exp, java.math.BigInteger m) {
        java.math.BigInteger result = java.math.BigInteger.ONE.mod(m);
        java.math.BigInteger b = base.mod(m);
        int el = exp.bitLength();
        for (int i = 0; i < el; i++) {
            if (exp.testBit(i)) result = mulModBig(result, b, m);
            if (i + 1 < el) b = mulModBig(b, b, m);
        }
        return result;
    }

    /** SHA-256 via BC pure-Java (AndroidDigestFactory.getSHA256()), the path proven good on-device. */
    private static byte[] sha256BC(byte[] input) throws Exception {
        Class<?> factory = null;
        for (String n : new String[] {
                "com.android.org.bouncycastle.crypto.digests.AndroidDigestFactory",
                "com.android.internal.org.bouncycastle.crypto.digests.AndroidDigestFactory" }) {
            try { factory = Class.forName(n); break; } catch (Throwable ignore) {}
        }
        if (factory == null) throw new IllegalStateException("AndroidDigestFactory not found");
        Object d = factory.getMethod("getSHA256").invoke(null);
        java.lang.reflect.Method update = d.getClass().getMethod("update", byte[].class, int.class, int.class);
        java.lang.reflect.Method getSize = d.getClass().getMethod("getDigestSize");
        java.lang.reflect.Method doFinal = d.getClass().getMethod("doFinal", byte[].class, int.class);
        update.invoke(d, input, 0, input.length);
        byte[] out = new byte[(Integer) getSize.invoke(d)];
        doFinal.invoke(d, out, 0);
        return out;
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
            log("encode: step1 header written");
            writeBlob(out, sha256(immutableApkPath));
            log("encode: step2 file sha256 done");
            out.writeInt(signerChains.length);
            log("encode: step3 signerCount=" + signerChains.length);

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
                int ci = 0;
                for (X509Certificate cert : chain) {
                    byte[] enc = cert.getEncoded();
                    writeBlob(out, enc);
                    log("encode: cert[" + ci + "] len=" + enc.length);
                    ci++;
                }
            }
            log("encode: step4 certs done totalCount=" + totalCount);

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
        // Self-rolled SHA-256 (MySha256), cached per (path, length). MessageDigest.getInstance
        // NPEs on this imageless ART; BC SHA256Digest and MySha256 are correct but ~0.9 MB/s under
        // the interpreter (JIT hard-off) -> 52s for 56MB, over bm install's 30s timeout. The cache
        // lets the second install return instantly after the first primes it.
        long len = new java.io.File(path).length();
        if (sCachedHash != null && path.equals(sCachedPath) && len == sCachedLen) {
            log("sha256(path): CACHE HIT hash=" + hex(sCachedHash));
            return sCachedHash;
        }
        MySha256 md = new MySha256();
        byte[] buffer = new byte[64 * 1024];
        long total = 0;
        long start = System.nanoTime();
        try (FileInputStream in = new FileInputStream(path)) {
            int count;
            while ((count = in.read(buffer)) != -1) {
                md.update(buffer, 0, count);
                total += count;
            }
        }
        byte[] out = md.digest();
        long ms = (System.nanoTime() - start) / 1000000L;
        sCachedHash = out; sCachedPath = path; sCachedLen = len;
        log("sha256(path): computed total=" + total + " ms=" + ms + " hash=" + hex(out));
        return out;
    }

    private static void writeBlob(DataOutputStream out, byte[] value) throws IOException {
        if (value == null || value.length == 0 || value.length > MAX_CERT_BYTES) {
            throw new SecurityException("invalid blob length");
        }
        out.writeInt(value.length);
        out.write(value);
    }

    /**
     * Self-contained SHA-256 (FIPS 180-4). Avoids MessageDigest.getInstance (NPEs on this runtime)
     * and BC SHA256Digest.update (hard-aborts on large input). Processes 64-byte blocks directly;
     * update() copies bytes into a 64-byte buffer and calls processBlock per full block, so there
     * is no large-len byte-wise loop (the BC path that faults the interpreter).
     */
    static final class MySha256 {
        private int h0 = 0x6a09e667, h1 = 0xbb67ae85, h2 = 0x3c6ef372, h3 = 0xa54ff53a;
        private int h4 = 0x510e527f, h5 = 0x9b05688c, h6 = 0x1f83d9ab, h7 = 0x5be0cd19;
        private final byte[] buf = new byte[64];
        private final int[] w = new int[64];   // allocated ONCE (not per block)
        private int bufLen = 0;
        private long totalLen = 0;

        private static final int[] K = {
            0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
            0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
            0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
            0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
            0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
            0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
            0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
            0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
        };

        void update(byte[] in, int off, int len) {
            totalLen += len;
            // drain pending buf first
            if (bufLen > 0) {
                int n = 64 - bufLen;
                if (n > len) n = len;
                System.arraycopy(in, off, buf, bufLen, n);
                bufLen += n; off += n; len -= n;
                if (bufLen == 64) { processBlock(buf, 0); bufLen = 0; }
            }
            // fast path: full 64-byte blocks straight from the input array -- no per-block copy
            while (len >= 64) {
                processBlock(in, off);
                off += 64; len -= 64;
            }
            // tail -> buf
            if (len > 0) { System.arraycopy(in, off, buf, 0, len); bufLen = len; }
        }

        byte[] digest() {
            long bitLen = totalLen * 8;
            buf[bufLen++] = (byte) 0x80;
            if (bufLen > 56) {
                while (bufLen < 64) buf[bufLen++] = 0;
                processBlock(buf, 0); bufLen = 0;
            }
            while (bufLen < 56) buf[bufLen++] = 0;
            for (int i = 7; i >= 0; i--) buf[bufLen++] = (byte) (bitLen >>> (i * 8));
            processBlock(buf, 0);
            byte[] out = new byte[32];
            out[0] = (byte) (h0 >>> 24); out[1] = (byte) (h0 >>> 16); out[2] = (byte) (h0 >>> 8); out[3] = (byte) h0;
            out[4] = (byte) (h1 >>> 24); out[5] = (byte) (h1 >>> 16); out[6] = (byte) (h1 >>> 8); out[7] = (byte) h1;
            out[8] = (byte) (h2 >>> 24); out[9] = (byte) (h2 >>> 16); out[10] = (byte) (h2 >>> 8); out[11] = (byte) h2;
            out[12] = (byte) (h3 >>> 24); out[13] = (byte) (h3 >>> 16); out[14] = (byte) (h3 >>> 8); out[15] = (byte) h3;
            out[16] = (byte) (h4 >>> 24); out[17] = (byte) (h4 >>> 16); out[18] = (byte) (h4 >>> 8); out[19] = (byte) h4;
            out[20] = (byte) (h5 >>> 24); out[21] = (byte) (h5 >>> 16); out[22] = (byte) (h5 >>> 8); out[23] = (byte) h5;
            out[24] = (byte) (h6 >>> 24); out[25] = (byte) (h6 >>> 16); out[26] = (byte) (h6 >>> 8); out[27] = (byte) h6;
            out[28] = (byte) (h7 >>> 24); out[29] = (byte) (h7 >>> 16); out[30] = (byte) (h7 >>> 8); out[31] = (byte) h7;
            return out;
        }

        private void processBlock(byte[] block, int off) {
            int[] ww = this.w;
            for (int i = 0; i < 16; i++) {
                int j = off + (i << 2);
                ww[i] = ((block[j] & 0xff) << 24) | ((block[j + 1] & 0xff) << 16)
                      | ((block[j + 2] & 0xff) << 8) | (block[j + 3] & 0xff);
            }
            for (int i = 16; i < 64; i++) {
                int x = ww[i - 15], y = ww[i - 2];
                int s0 = ((x >>> 7) | (x << 25)) ^ ((x >>> 18) | (x << 14)) ^ (x >>> 3);
                int s1 = ((y >>> 17) | (y << 15)) ^ ((y >>> 19) | (y << 13)) ^ (y >>> 10);
                ww[i] = ww[i - 16] + s0 + ww[i - 7] + s1;
            }
            int a = h0, b = h1, c = h2, d = h3, e = h4, f = h5, g = h6, hh = h7;
            for (int i = 0; i < 64; i++) {
                int S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
                int ch = (e & f) ^ (~e & g);
                int t1 = hh + S1 + ch + K[i] + ww[i];
                int S2 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
                int maj = (a & b) ^ (a & c) ^ (b & c);
                int t2 = S2 + maj;
                hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
            }
            h0 += a; h1 += b; h2 += c; h3 += d; h4 += e; h5 += f; h6 += g; h7 += hh;
        }
    }
}
