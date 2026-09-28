/*
 * Stub for android.media.MediaFrameworkInitializer. Real impl in
 * com.android.media mainline.
 *
 * Called from ActivityThread.initializeMainlineModules():
 *   MediaFrameworkInitializer.setMediaServiceManager(new MediaServiceManager());
 * MediaServiceManager is in framework.jar (android.media.MediaServiceManager).
 */
package android.media;

public class MediaFrameworkInitializer {
    public static void setMediaServiceManager(MediaServiceManager m) {
        // no-op
    }
    // Called from SystemServiceRegistry.<clinit>; no-op on OH.
    public static void registerServiceWrappers() {
        // no-op
    }
}
