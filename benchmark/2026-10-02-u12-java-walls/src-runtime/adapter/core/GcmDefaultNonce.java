package adapter.core;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.security.AlgorithmParameters;
import java.security.GeneralSecurityException;
import java.security.InvalidAlgorithmParameterException;
import java.security.InvalidKeyException;
import java.security.Key;
import java.security.NoSuchAlgorithmException;
import java.security.Provider;
import java.security.SecureRandom;
import java.security.Security;
import java.security.spec.AlgorithmParameterSpec;
import java.security.spec.InvalidParameterSpecException;
import javax.crypto.BadPaddingException;
import javax.crypto.Cipher;
import javax.crypto.CipherSpi;
import javax.crypto.IllegalBlockSizeException;
import javax.crypto.NoSuchPaddingException;
import javax.crypto.ShortBufferException;
import javax.crypto.spec.GCMParameterSpec;

/**
 * "AES/GCM/NoPadding" with Android's default nonce: 12 random bytes when an encrypting init passes no parameters.
 *
 * On Android the default AES/GCM provider is Conscrypt (and AndroidKeyStore for keystore keys); both generate a
 * 12-byte IV. Route-A has no Conscrypt cipher, so Cipher.getInstance("AES/GCM/NoPadding") reaches Bouncy Castle,
 * whose parameterless GCM init generates a 16-byte IV. Tink (androidx.security EncryptedSharedPreferences) writes
 * iv || ciphertext and decrypts with the first 12 bytes as the IV, so its master-key self-test fails with
 * AEADBadTagException and the app aborts ("the master key ... exists but is unusable", moodcairns; the
 * [WL-KS-PROBE] self-test reproduces it). This provider sits first and delegates every call to the next provider's
 * AES/GCM implementation; the only behavioural difference is that parameterless ENCRYPT/WRAP init gets a 12-byte
 * nonce and a 128-bit tag, as Conscrypt's does. Decryption and explicit parameters pass through unchanged.
 */
public final class GcmDefaultNonce extends Provider {
    static final String NAME = "WestlakeGcmNonce";
    private static final String TRANSFORMATION = "AES/GCM/NoPadding";

    private GcmDefaultNonce() {
        super(NAME, 1.0, "AES/GCM/NoPadding with a 12-byte default nonce (Conscrypt behaviour)");
        putService(new Service(this, "Cipher", TRANSFORMATION, Spi.class.getName(), null, null) {
            @Override
            public Object newInstance(Object constructorParameter) {
                return new Spi();
            }
        });
    }

    public static synchronized void install() {
        try {
            if (Security.getProvider(NAME) != null) return;
            Provider below = newDelegate().getProvider();
            int position = Security.insertProviderAt(new GcmDefaultNonce(), 1);
            System.err.println("[B8-GCM] " + NAME + " installed at " + position + "; AES/GCM delegate "
                    + below.getName() + ", parameterless encrypt nonce 12 bytes");
        } catch (Throwable t) {
            System.err.println("[B8-GCM] skipped: " + t);
        }
    }

    /** JCE's own lookup order for a transformation: full name, then mode/padding set on a broader service. */
    private static final String[][] FORMS = {
        {"AES/GCM/NoPadding", null, null}, {"AES/GCM", null, "NoPadding"}, {"AES//NoPadding", "GCM", null},
        {"AES", "GCM", "NoPadding"},
    };

    /**
     * AES/GCM/NoPadding from the first provider below this one (Bouncy Castle on route-A, which registers "AES" and
     * takes the mode and padding afterwards). Built from the service directly, as Cipher.getInstance does, so an
     * explicit-provider lookup and its Bouncy Castle deprecation check are not involved.
     */
    static Cipher newDelegate() throws GeneralSecurityException {
        for (Provider provider : Security.getProviders()) {
            if (provider instanceof GcmDefaultNonce) continue;
            for (String[] form : FORMS) {
                Provider.Service service = provider.getService("Cipher", form[0]);
                if (service == null) continue;
                CipherSpi spi = (CipherSpi) service.newInstance(null);
                if (form[1] != null) call(spi, "engineSetMode", form[1]);
                if (form[2] != null) call(spi, "engineSetPadding", form[2]);
                return new Cipher(spi, provider, TRANSFORMATION) {};
            }
        }
        throw new NoSuchAlgorithmException("no " + TRANSFORMATION + " provider below " + NAME);
    }

    private static void call(CipherSpi spi, String method, String argument) throws GeneralSecurityException {
        try {
            Method m = CipherSpi.class.getDeclaredMethod(method, String.class);
            m.setAccessible(true);
            m.invoke(spi, argument);
        } catch (InvocationTargetException e) {
            if (e.getCause() instanceof GeneralSecurityException) throw (GeneralSecurityException) e.getCause();
            throw new NoSuchAlgorithmException(method + "(" + argument + ")", e.getCause());
        } catch (ReflectiveOperationException e) {
            throw new NoSuchAlgorithmException(method + "(" + argument + ")", e);
        }
    }

    public static final class Spi extends CipherSpi {
        private Cipher delegate;

        private Cipher delegate() throws GeneralSecurityException {
            if (delegate == null) delegate = newDelegate();
            return delegate;
        }

        private void init(int opmode, Key key, AlgorithmParameterSpec spec, SecureRandom random)
                throws InvalidKeyException, InvalidAlgorithmParameterException {
            Cipher cipher;
            try {
                cipher = delegate();
            } catch (GeneralSecurityException e) {
                throw new InvalidKeyException("AES/GCM delegate unavailable", e);
            }
            if (spec == null && (opmode == Cipher.ENCRYPT_MODE || opmode == Cipher.WRAP_MODE)) {
                byte[] nonce = new byte[12];
                (random != null ? random : new SecureRandom()).nextBytes(nonce);
                spec = new GCMParameterSpec(128, nonce);
            }
            if (spec == null) {
                cipher.init(opmode, key, random);
            } else {
                cipher.init(opmode, key, spec, random);
            }
        }

        @Override
        protected void engineSetMode(String mode) throws NoSuchAlgorithmException {
            if (!"GCM".equalsIgnoreCase(mode)) throw new NoSuchAlgorithmException(mode);
        }

        @Override
        protected void engineSetPadding(String padding) throws NoSuchPaddingException {
            if (!"NoPadding".equalsIgnoreCase(padding)) throw new NoSuchPaddingException(padding);
        }

        @Override
        protected int engineGetBlockSize() {
            return 16;
        }

        @Override
        protected int engineGetOutputSize(int inputLen) {
            return delegate == null ? inputLen + 16 : delegate.getOutputSize(inputLen);
        }

        @Override
        protected byte[] engineGetIV() {
            return delegate == null ? null : delegate.getIV();
        }

        @Override
        protected AlgorithmParameters engineGetParameters() {
            return delegate == null ? null : delegate.getParameters();
        }

        @Override
        protected void engineInit(int opmode, Key key, SecureRandom random) throws InvalidKeyException {
            try {
                init(opmode, key, null, random);
            } catch (InvalidAlgorithmParameterException e) {
                throw new InvalidKeyException(e);
            }
        }

        @Override
        protected void engineInit(int opmode, Key key, AlgorithmParameterSpec params, SecureRandom random)
                throws InvalidKeyException, InvalidAlgorithmParameterException {
            init(opmode, key, params, random);
        }

        @Override
        protected void engineInit(int opmode, Key key, AlgorithmParameters params, SecureRandom random)
                throws InvalidKeyException, InvalidAlgorithmParameterException {
            AlgorithmParameterSpec spec = null;
            if (params != null) {
                try {
                    spec = params.getParameterSpec(GCMParameterSpec.class);
                } catch (InvalidParameterSpecException e) {
                    throw new InvalidAlgorithmParameterException(e);
                }
            }
            init(opmode, key, spec, random);
        }

        @Override
        protected byte[] engineUpdate(byte[] input, int offset, int len) {
            return delegate.update(input, offset, len);
        }

        @Override
        protected int engineUpdate(byte[] input, int offset, int len, byte[] output, int outputOffset)
                throws ShortBufferException {
            return delegate.update(input, offset, len, output, outputOffset);
        }

        @Override
        protected byte[] engineDoFinal(byte[] input, int offset, int len)
                throws IllegalBlockSizeException, BadPaddingException {
            return delegate.doFinal(input, offset, len);
        }

        @Override
        protected int engineDoFinal(byte[] input, int offset, int len, byte[] output, int outputOffset)
                throws ShortBufferException, IllegalBlockSizeException, BadPaddingException {
            return delegate.doFinal(input, offset, len, output, outputOffset);
        }

        @Override
        protected void engineUpdateAAD(byte[] src, int offset, int len) {
            delegate.updateAAD(src, offset, len);
        }

        @Override
        protected void engineUpdateAAD(ByteBuffer src) {
            delegate.updateAAD(src);
        }

        @Override
        protected int engineGetKeySize(Key key) throws InvalidKeyException {
            byte[] encoded = key.getEncoded();
            if (encoded == null) throw new InvalidKeyException("key has no encoding");
            return encoded.length * 8;
        }
    }
}
