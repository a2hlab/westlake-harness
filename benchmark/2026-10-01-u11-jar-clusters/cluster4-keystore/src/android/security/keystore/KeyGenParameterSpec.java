package android.security.keystore;

import java.math.BigInteger;
import java.security.spec.AlgorithmParameterSpec;
import java.util.Date;
import javax.security.auth.x500.X500Principal;

/** Minimal desktop stub of android.security.keystore.KeyGenParameterSpec — the Builder surface
 *  androidx.security.crypto.MasterKey uses, and the getters SoftwareAndroidKeyStore reads.
 *  Faithful to the fields the AES path touches (keystoreAlias, keySize). On-board this is the
 *  real framework class; here it only needs to carry alias + keysize for the probe. */
public final class KeyGenParameterSpec implements AlgorithmParameterSpec {
    private final String alias;
    private final int purposes;
    private final int keySize;

    private KeyGenParameterSpec(Builder b) {
        this.alias = b.alias;
        this.purposes = b.purposes;
        this.keySize = b.keySize;
    }

    public String getKeystoreAlias() { return alias; }
    public int getKeySize() { return keySize; }               // <=0 means "not set" (SoftwareAndroidKeyStore defaults it)
    public int getPurposes() { return purposes; }
    public AlgorithmParameterSpec getAlgorithmParameterSpec() { return null; }
    public X500Principal getCertificateSubject() { return null; }
    public BigInteger getCertificateSerialNumber() { return null; }
    public Date getCertificateNotBefore() { return null; }
    public Date getCertificateNotAfter() { return null; }

    public static final class Builder {
        private final String alias;
        private final int purposes;
        private int keySize = -1;
        private String[] blockModes = new String[0];
        private String[] encryptionPaddings = new String[0];

        public Builder(String keystoreAlias, int purposes) {
            this.alias = keystoreAlias;
            this.purposes = purposes;
        }
        public Builder setKeySize(int keySize) { this.keySize = keySize; return this; }
        public Builder setBlockModes(String... modes) { this.blockModes = modes; return this; }
        public Builder setEncryptionPaddings(String... paddings) { this.encryptionPaddings = paddings; return this; }
        public Builder setRandomizedEncryptionRequired(boolean required) { return this; }
        public KeyGenParameterSpec build() { return new KeyGenParameterSpec(this); }
    }
}
