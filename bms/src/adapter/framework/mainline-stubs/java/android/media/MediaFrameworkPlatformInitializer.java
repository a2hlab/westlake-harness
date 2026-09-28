/*
 * Stub for android.media.MediaFrameworkPlatformInitializer.
 * Called from ActivityThread.initializeMainlineModules():
 *   MediaFrameworkPlatformInitializer.setMediaServiceManager(new MediaServiceManager());
 */
package android.media;

public class MediaFrameworkPlatformInitializer {
    public static void setMediaServiceManager(MediaServiceManager m) {
        // no-op
    }
    // Called from SystemServiceRegistry.<clinit>; no-op on OH.
    public static void registerServiceWrappers() {
        // no-op
    }
}
