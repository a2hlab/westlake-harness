/* r17g (#93): a minimal "AndroidOpenSSL" provider so BC's AndroidDigestFactory init passes. */
package adapter.security;

import java.lang.reflect.Method;
import java.security.MessageDigestSpi;
import java.security.Provider;

/**
 * B8 (#93/r17g): route-A's boot image ships the UNPATCHED AOSP Bouncy Castle, whose
 * com.android.org.bouncycastle.crypto.digests.AndroidDigestFactory.&lt;clinit&gt; asserts "Provider
 * AndroidOpenSSL must exist" (it expects Conscrypt). Westlake ships a patched AndroidDigestFactory
 * that honours WESTLAKE_USE_BC_DIGESTS=1 instead; route-A does not, so setenv is a no-op and the
 * assertion fires from OhTrustBridge.initializeBouncyCastleDigests.
 *
 * Publish a small provider literally named "AndroidOpenSSL" that satisfies the assertion AND answers
 * the six standard MessageDigests by driving BC's LOW-LEVEL digest engines
 * (com.android.org.bouncycastle.crypto.digests.SHA256Digest, ...) directly. Using the low-level
 * engines -- not the jcajce MessageDigest SPIs -- is essential: the jcajce SPIs route back through
 * AndroidDigestFactory and would recurse. Every BC class is reached by reflection (absent from the
 * compile android.jar, present in the runtime BCP).
 */
public class WestlakeAndroidOpenSsl extends Provider {   // non-final: OpenSSLProvider extends it
    private static final long serialVersionUID = 1L;

    public WestlakeAndroidOpenSsl() {
        super("AndroidOpenSSL", 1.0d,
                "Westlake BC-backed digests so AndroidDigestFactory init passes on route-A");
        put("MessageDigest.MD5", Md5.class.getName());
        put("MessageDigest.SHA-1", Sha1.class.getName());
        put("MessageDigest.SHA-224", Sha224.class.getName());
        put("MessageDigest.SHA-256", Sha256.class.getName());
        put("MessageDigest.SHA-384", Sha384.class.getName());
        put("MessageDigest.SHA-512", Sha512.class.getName());
        put("Alg.Alias.MessageDigest.SHA", "SHA-1");
        put("Alg.Alias.MessageDigest.SHA1", "SHA-1");
    }

    /** MessageDigestSpi that reflectively drives a BC low-level org.bouncycastle.crypto.Digest. */
    public static class BcDigest extends MessageDigestSpi {
        private final Object engine;
        private final Method update1;
        private final Method updateN;
        private final Method doFinal;
        private final Method getSize;
        private final Method reset;

        protected BcDigest(String bcClassName) {
            try {
                Class<?> c = Class.forName(bcClassName);
                engine = c.getDeclaredConstructor().newInstance();
                update1 = c.getMethod("update", byte.class);
                updateN = c.getMethod("update", byte[].class, int.class, int.class);
                doFinal = c.getMethod("doFinal", byte[].class, int.class);
                getSize = c.getMethod("getDigestSize");
                reset = c.getMethod("reset");
            } catch (Throwable t) {
                throw new IllegalStateException("BC low-level digest unavailable: " + bcClassName, t);
            }
        }

        @Override protected void engineUpdate(byte input) {
            try { update1.invoke(engine, input); } catch (Throwable t) { throw runtime(t); }
        }

        @Override protected void engineUpdate(byte[] input, int offset, int len) {
            try { updateN.invoke(engine, input, offset, len); } catch (Throwable t) { throw runtime(t); }
        }

        @Override protected byte[] engineDigest() {
            try {
                int n = (Integer) getSize.invoke(engine);
                byte[] out = new byte[n];
                doFinal.invoke(engine, out, 0);   // BC doFinal already resets the engine
                return out;
            } catch (Throwable t) {
                throw runtime(t);
            }
        }

        @Override protected void engineReset() {
            try { reset.invoke(engine); } catch (Throwable t) { throw runtime(t); }
        }

        @Override protected int engineGetDigestLength() {
            try { return (Integer) getSize.invoke(engine); } catch (Throwable t) { return 0; }
        }

        private static RuntimeException runtime(Throwable t) {
            Throwable c = t.getCause() != null ? t.getCause() : t;
            return c instanceof RuntimeException ? (RuntimeException) c : new RuntimeException(c);
        }
    }

    public static final class Md5 extends BcDigest {
        public Md5() { super("com.android.org.bouncycastle.crypto.digests.MD5Digest"); }
    }
    public static final class Sha1 extends BcDigest {
        public Sha1() { super("com.android.org.bouncycastle.crypto.digests.SHA1Digest"); }
    }
    public static final class Sha224 extends BcDigest {
        public Sha224() { super("com.android.org.bouncycastle.crypto.digests.SHA224Digest"); }
    }
    public static final class Sha256 extends BcDigest {
        public Sha256() { super("com.android.org.bouncycastle.crypto.digests.SHA256Digest"); }
    }
    public static final class Sha384 extends BcDigest {
        public Sha384() { super("com.android.org.bouncycastle.crypto.digests.SHA384Digest"); }
    }
    public static final class Sha512 extends BcDigest {
        public Sha512() { super("com.android.org.bouncycastle.crypto.digests.SHA512Digest"); }
    }
}
