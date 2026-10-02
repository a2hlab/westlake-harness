/** Which configured security provider fails to instantiate on this BCP (runs before sun.security.jca.Providers). */
public final class ProviderDiag {
    public static void main(String[] args) {
        for (int i = 1; i < 20; i++) {
            String name = java.security.Security.getProperty("security.provider." + i);
            if (name == null) continue;
            try {
                Object p = Class.forName(name.trim().split(" ")[0]).getDeclaredConstructor().newInstance();
                System.out.println("provider." + i + " " + name + " OK " + p);
            } catch (Throwable t) {
                System.out.println("provider." + i + " " + name + " FAIL " + t);
                Throwable c = t.getCause();
                while (c != null) { System.out.println("   cause " + c); c = c.getCause(); }
            }
        }
    }
}
