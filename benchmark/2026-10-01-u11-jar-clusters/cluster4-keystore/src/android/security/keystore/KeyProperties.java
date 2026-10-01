package android.security.keystore;

/** Minimal desktop stub of android.security.keystore.KeyProperties — only the constants
 *  SoftwareAndroidKeyStore and the probe reference. On-board these come from the boot image. */
public final class KeyProperties {
    public static final String KEY_ALGORITHM_AES = "AES";
    public static final String KEY_ALGORITHM_HMAC_SHA1 = "HmacSHA1";
    public static final String KEY_ALGORITHM_HMAC_SHA224 = "HmacSHA224";
    public static final String KEY_ALGORITHM_HMAC_SHA256 = "HmacSHA256";
    public static final String KEY_ALGORITHM_HMAC_SHA384 = "HmacSHA384";
    public static final String KEY_ALGORITHM_HMAC_SHA512 = "HmacSHA512";
    public static final String KEY_ALGORITHM_EC = "EC";
    public static final String KEY_ALGORITHM_RSA = "RSA";

    public static final int PURPOSE_ENCRYPT = 1;
    public static final int PURPOSE_DECRYPT = 2;

    public static final String BLOCK_MODE_GCM = "GCM";
    public static final String ENCRYPTION_PADDING_NONE = "NoPadding";

    private KeyProperties() {}
}
