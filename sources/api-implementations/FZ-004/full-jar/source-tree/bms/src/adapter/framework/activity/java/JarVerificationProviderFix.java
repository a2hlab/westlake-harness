/* r17o (#conscrypt): single-purpose file (freeze unit) -- rewrite jarVerificationProviders[0] to BC. */
package adapter.activity;

/**
 * B8 (#93/r17o): route-A has no Conscrypt, so sun.security.jca.Providers.getSunProvider() --
 * Class.forName(jarVerificationProviders[0]) under BootClassLoader during JAR signature verification --
 * throws "Sun provider not found" and takes down the first app that verifies a signed JAR
 * (Droid-ify MainActivity.onCreate, Amaze AppConfig.<clinit>, NewPipe, Catima, AntennaPod). The array
 * reference is static final but its elements are writable, so rewrite element 0 to the boot-visible
 * BouncyCastle provider before any such verification. Process-global + idempotent.
 *
 * Extracted verbatim from B7BindFixes.fixJarVerificationProvider into its own file so it can be frozen
 * (AGENTS.md 做事方式 3) without locking the other B7BindFixes fixes. B7BindFixes.apply() calls apply().
 */
public final class JarVerificationProviderFix {

    private JarVerificationProviderFix() {}

    public static void apply() {
        final String BC = "com.android.org.bouncycastle.jce.provider.BouncyCastleProvider";
        try {
            Class<?> providers = Class.forName("sun.security.jca.Providers");
            java.lang.reflect.Field f = providers.getDeclaredField("jarVerificationProviders");
            f.setAccessible(true);
            Object arr = f.get(null);
            if (!(arr instanceof String[])) {
                System.err.println("[B8-JARVERIFY] jarVerificationProviders not String[]: " + arr);
                return;
            }
            String[] jvp = (String[]) arr;
            if (jvp.length == 0) { System.err.println("[B8-JARVERIFY] array empty"); return; }
            String was = jvp[0];
            if (BC.equals(was)) return;                    // already fixed this process
            jvp[0] = BC;
            System.err.println("[B8-JARVERIFY] jarVerificationProviders[0] " + was + " -> " + BC);
        } catch (Throwable t) {
            System.err.println("[B8-JARVERIFY] not applied: " + t);
        }
    }
}
