package com.android.internal.org.bouncycastle.x509;

import java.math.BigInteger;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.cert.X509Certificate;
import java.util.Date;
import javax.security.auth.x500.X500Principal;

/** COMPILE-ONLY stub: SoftwareAndroidKeyStore's EC/RSA KeyPairGenerator path references this
 *  bouncycastle cert generator. The AES-GCM probe never exercises the key-pair path, so this
 *  only needs to let the class compile; generate() throws if ever called. */
public class X509V3CertificateGenerator {
    public void setSerialNumber(BigInteger serial) {}
    public void setSubjectDN(X500Principal subject) {}
    public void setIssuerDN(X500Principal issuer) {}
    public void setNotBefore(Date date) {}
    public void setNotAfter(Date date) {}
    public void setPublicKey(PublicKey key) {}
    public void setSignatureAlgorithm(String algorithm) {}
    public X509Certificate generate(PrivateKey key) throws Exception {
        throw new UnsupportedOperationException("stub: key-pair path not exercised by the AES-GCM probe");
    }
}
