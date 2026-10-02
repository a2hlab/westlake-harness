package android.app;

/** Compile-only stand-in for the hidden API WlSettingsProvider calls; never packed into the jar. */
public final class ActivityThread {
    public static Application currentApplication() { return null; }
}
