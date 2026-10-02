import android.net.nsd.NsdManager;
import android.net.nsd.NsdServiceInfo;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.net.InetAddress;
import java.util.Map;

/**
 * Host-ART check on the boards' boot class path (benchmark/2026-10-03-u15-stubs-nsd): the immich shape.
 *   Base     = b7.a  (abstract, public boolean D)
 *   Disc     = d7.c  (extends b7.a implements NsdManager$DiscoveryListener)
 *   Reg/Res  = c7.a / d7.a (the RegistrationListener / ResolveListener implementors)
 *   Handler  = A2.b  (reads b7.a.D through a register typed d7.c -> the board's VerifyError when d7.c is unresolvable)
 * Every case runs in its own class, loaded by name, so a verify failure is reported per case.
 */
public class NsdTest {
    static int failures;

    public abstract static class Base { public boolean D = true; }

    public static final class Disc extends Base implements NsdManager.DiscoveryListener {
        int calls;
        public void onStartDiscoveryFailed(String t, int e) { calls++; }
        public void onStopDiscoveryFailed(String t, int e) { calls++; }
        public void onDiscoveryStarted(String t) { calls++; }
        public void onDiscoveryStopped(String t) { calls++; }
        public void onServiceFound(NsdServiceInfo i) { calls++; }
        public void onServiceLost(NsdServiceInfo i) { calls++; }
    }

    public static final class Reg extends Base implements NsdManager.RegistrationListener {
        public void onRegistrationFailed(NsdServiceInfo i, int e) { }
        public void onUnregistrationFailed(NsdServiceInfo i, int e) { }
        public void onServiceRegistered(NsdServiceInfo i) { }
        public void onServiceUnregistered(NsdServiceInfo i) { }
    }

    public static final class Res extends Base implements NsdManager.ResolveListener {
        int calls;
        public void onResolveFailed(NsdServiceInfo i, int e) { calls++; }
        public void onServiceResolved(NsdServiceInfo i) { calls++; }
    }

    /** A2.b stand-in: the field is read through Base from a register whose type is Disc. */
    public static final class Handler {
        public static boolean read(Disc d) { Base b = d; return b.D; }
    }

    public static final class Case0 implements Runnable {   // the board event: linking (verifying) A2.b alone
        public void run() {
            try {
                Class<?> h = Class.forName("NsdTest$Handler");
                check("0 A2.b-shape class links (verifier accepts the b7.a.D read on a d7.c-typed register)", true,
                        h.getName());
            } catch (Throwable t) {
                check("0 A2.b-shape class links (verifier accepts the b7.a.D read on a d7.c-typed register)", false,
                        t.getClass().getName() + ": " + t.getMessage());
            }
        }
    }

    public static final class Case1 implements Runnable {   // A2.b verifies and runs
        public void run() {
            boolean d = Handler.read(new Disc());
            check("1 A2.b-shape class (reads b7.a.D via a d7.c-typed register) verifies and runs", d, "D=" + d);
        }
    }

    public static final class Case2 implements Runnable {   // the three listener shapes
        public void run() {
            Disc disc = new Disc();
            NsdManager.DiscoveryListener l = disc;
            l.onDiscoveryStarted("_immich._tcp"); l.onServiceFound(null); l.onServiceLost(null);
            Res res = new Res();
            NsdManager.ResolveListener r = res;
            r.onServiceResolved(null);
            r.onResolutionStopped(new NsdServiceInfo());       // AOSP 14 default method: no-op
            r.onStopResolutionFailed(new NsdServiceInfo(), NsdManager.FAILURE_OPERATION_NOT_RUNNING);
            NsdManager.RegistrationListener g = new Reg();
            g.onServiceRegistered(null);
            check("2 d7.c / c7.a / d7.a shapes load; listener calls dispatch; ResolveListener defaults are no-ops",
                    disc.calls == 3 && res.calls == 1, "disc=" + disc.calls + " res=" + res.calls);
        }
    }

    public static final class Case3 implements Runnable {   // NsdServiceInfo (AOSP verbatim)
        public void run() {
            NsdServiceInfo i = new NsdServiceInfo();
            i.setServiceName("immich"); i.setServiceType("_immich._tcp"); i.setPort(2283);
            i.setHost(InetAddress.getLoopbackAddress());
            i.setAttribute("version", "1.0");
            Map<String, byte[]> a = i.getAttributes();
            boolean ok = "immich".equals(i.getServiceName()) && "_immich._tcp".equals(i.getServiceType())
                    && i.getPort() == 2283 && i.getHost() != null && a.containsKey("version")
                    && "1.0".equals(new String(a.get("version"))) && i.getNetwork() == null && i.toString() != null;
            check("3 NsdServiceInfo getters/setters as AOSP 14 (immich's B.C.a / d7.c.onServiceFound calls)", ok,
                    i.toString());
        }
    }

    public static final class Case4 implements Runnable {   // NsdManager surface
        public void run() {
            Class<?> c = NsdManager.class;
            boolean noPublicCtor = true;
            for (Constructor<?> k : c.getDeclaredConstructors()) noPublicCtor &= !Modifier.isPublic(k.getModifiers());
            boolean methods = true;
            try {
                c.getMethod("discoverServices", String.class, int.class, NsdManager.DiscoveryListener.class);
                c.getMethod("registerService", NsdServiceInfo.class, int.class, NsdManager.RegistrationListener.class);
                c.getMethod("resolveService", NsdServiceInfo.class, NsdManager.ResolveListener.class);
                c.getMethod("stopServiceDiscovery", NsdManager.DiscoveryListener.class);
                c.getMethod("unregisterService", NsdManager.RegistrationListener.class);
            } catch (NoSuchMethodException e) { methods = false; }
            boolean consts = NsdManager.PROTOCOL_DNS_SD == 1 && NsdManager.FAILURE_INTERNAL_ERROR == 0
                    && NsdManager.FAILURE_ALREADY_ACTIVE == 3 && NsdManager.FAILURE_MAX_LIMIT == 4
                    && NsdManager.FAILURE_OPERATION_NOT_RUNNING == 5 && NsdManager.FAILURE_BAD_PARAMETERS == 6
                    && NsdManager.NSD_STATE_DISABLED == 1 && NsdManager.NSD_STATE_ENABLED == 2;
            check("4 NsdManager public final, no public constructor, immich's 5 methods present, AOSP 14 constants",
                    Modifier.isFinal(c.getModifiers()) && noPublicCtor && methods && consts,
                    "final=" + Modifier.isFinal(c.getModifiers()) + " noPublicCtor=" + noPublicCtor + " methods=" + methods + " consts=" + consts);
        }
    }

    static void check(String name, boolean ok, String detail) {
        System.out.println("CASE " + name + ": " + (ok ? "PASS" : "FAIL") + " " + detail);
        if (!ok) failures++;
    }

    public static void main(String[] args) {
        for (String n : new String[] {"NsdTest$Case0", "NsdTest$Case1", "NsdTest$Case2", "NsdTest$Case3", "NsdTest$Case4"}) {
            try {
                ((Runnable) Class.forName(n).getDeclaredConstructor().newInstance()).run();
            } catch (Throwable t) {
                Throwable root = t;
                while (root.getCause() != null) root = root.getCause();
                check(n, false, root.getClass().getName() + ": " + root.getMessage());
            }
        }
        System.out.println("FAILURES " + failures);
        System.exit(failures == 0 ? 0 : 1);
    }
}
