/*
 * COMPILE-ONLY stub for the runtime BCP class
 * com.android.internal.org.bouncycastle.x509.X509V3CertificateGenerator, which is absent from the
 * compile android.jar but present in the OH boot class path at runtime. SoftwareAndroidKeyStore
 * compiles against this stub; only SoftwareAndroidKeyStore* classes go into the dex, so at runtime
 * the real BCP class resolves (same shape as the OnlineConnectivityManager android.net route).
 *
 * The method signatures match the members SoftwareAndroidKeyStore.selfSigned() uses.
 */
package com.android.internal.org.bouncycastle.x509;

import java.math.BigInteger;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.cert.X509Certificate;
import java.util.Date;

import javax.security.auth.x500.X500Principal;

public class X509V3CertificateGenerator {
    public X509V3CertificateGenerator() {}

    public void setSerialNumber(BigInteger serialNumber) {}
    public void setSubjectDN(X500Principal subject) {}
    public void setIssuerDN(X500Principal issuer) {}
    public void setNotBefore(Date date) {}
    public void setNotAfter(Date date) {}
    public void setPublicKey(PublicKey publicKey) {}
    public void setSignatureAlgorithm(String signatureAlgorithm) {}

    public X509Certificate generate(PrivateKey key) throws Exception {
        throw new UnsupportedOperationException("compile-only stub");
    }
}
