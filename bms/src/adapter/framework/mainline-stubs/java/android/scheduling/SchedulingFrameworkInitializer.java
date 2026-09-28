/*
 * Stub for android.scheduling.SchedulingFrameworkInitializer.
 * Real impl in com.android.scheduling mainline. Currently no known ActivityThread
 * call path hits its methods during Hello World cold start, but ART verifier
 * resolves class reference at method-level and NCDFE's if class absent.
 */
package android.scheduling;

public class SchedulingFrameworkInitializer {
    // Called from SystemServiceRegistry.<clinit>; no-op on OH.
    public static void registerServiceWrappers() {
        // no-op
    }
}
