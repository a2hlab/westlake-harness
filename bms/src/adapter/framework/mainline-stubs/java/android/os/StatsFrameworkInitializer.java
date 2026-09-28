/*
 * Stub for android.os.StatsFrameworkInitializer. Real impl in
 * com.android.os.statsd mainline module.
 *
 * Called from ActivityThread.initializeMainlineModules():
 *   StatsFrameworkInitializer.setStatsServiceManager(new StatsServiceManager());
 * StatsServiceManager is in framework.jar (probe confirmed).
 */
package android.os;

public class StatsFrameworkInitializer {
    public static void setStatsServiceManager(StatsServiceManager m) {
        // no-op
    }
    // Called from SystemServiceRegistry.<clinit>; no-op on OH.
    public static void registerServiceWrappers() {
        // no-op
    }
}
