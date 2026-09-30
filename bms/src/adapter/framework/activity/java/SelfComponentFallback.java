package adapter.activity;

import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.content.pm.ApplicationInfo;
import android.content.pm.ResolveInfo;
import android.content.pm.ComponentInfo;
import android.content.pm.ProviderInfo;
import android.content.pm.ServiceInfo;
import android.content.res.AssetManager;
import android.content.res.Resources;
import android.content.res.XmlResourceParser;
import android.os.Process;

import java.lang.reflect.Method;

/**
 * B8 (#65) INVENTORY items 1-2: self-package getProviderInfo / resolveContentProvider.
 *
 * The OH BMS bridge answers both with null for the app's own providers, so
 * androidx.startup.InitializationProvider (getProviderInfo(own, GET_META_DATA))
 * and androidx FileProvider (resolveContentProvider(authority, GET_META_DATA))
 * fail during bindApplication. The answer comes from the bound APK's own manifest
 * through 00.Workspace's ManifestComponentProjection (copied verbatim, cd5b32935);
 * the parse loop below is the component part of 00.Workspace
 * InstalledApkApplicationProjection's constructor. Only a null delegate answer for
 * this package is ever replaced, so any real BMS answer wins.
 */
public final class SelfComponentFallback {
    private static ApplicationInfo bound;
    private static ManifestComponentProjection components;
    private static boolean failed;

    private SelfComponentFallback() {}

    /** Record the bound self ApplicationInfo (called from ensureBindApplication). */
    public static synchronized void bind(ApplicationInfo application) {
        if (application == null || application.packageName == null || application.sourceDir == null) return;
        bound = new ApplicationInfo(application);
        components = null;
        failed = false;
    }

    /** IPackageManager proxy hook: returns the delegate result unless it is a null self-package answer.
     *  getActivityInfo is the one exception: its result is non-null but carries the wrong theme, so it is
     *  corrected in place (see below) before the null-answer short-circuit. */
    public static Object apply(Method method, Object[] args, Object result) {
        if (method == null || args == null) return result;
        try {
            String name = method.getName();
            // r17u (#vlc/#fd-api activity-theme-contract): the OH bridge projects a self-package
            // ActivityInfo with the APPLICATION theme, not the activity's own android:theme. An activity
            // whose layout reads a ?attr/ that only its declared theme defines then crashes in
            // setContentView (vlc OnboardingActivity ConstraintLayout "Failed to resolve attribute at
            // index 13", fd-api Theme.AppCompat ISE). getActivityInfo returns a NON-null wrong-theme info,
            // so correct its theme from the bound APK's manifest (activity's own android:theme).
            if ("getActivityInfo".equals(name) && result instanceof android.content.pm.ActivityInfo
                    && args.length >= 1 && args[0] instanceof ComponentName) {
                correctSelfActivityTheme((android.content.pm.ActivityInfo) result, (ComponentName) args[0]);
                return result;
            }
            if (result != null) return result;
            if ("getProviderInfo".equals(name) && args.length >= 3 && args[0] instanceof ComponentName
                    && args[1] instanceof Long) {
                ComponentName component = (ComponentName) args[0];
                ManifestComponentProjection projection = projection(component.getPackageName());
                if (projection == null) return null;
                ComponentInfo info = projection.component(component.getClassName(), "provider", bound, (Long) args[1]);
                if (info != null) {
                    System.err.println("[B8-PM] projected getProviderInfo " + component.flattenToShortString()
                            + " metaData=" + (info.metaData == null ? 0 : info.metaData.size()));
                }
                return info;
            }
            // r17u (#binaryeye): the OH BMS bridge returns null for the app's own <service>, so
            // ApplicationPackageManager.getServiceInfo throws NameNotFoundException. androidx.camera's
            // MetadataHolderService lookup (getServiceInfo(self, GET_META_DATA)) then makes CameraX
            // report "not configured properly" and the app System.exit(1)s in onResume. Answer from the
            // bound APK's own manifest with the service's <meta-data> (CameraXConfig$Provider is read
            // from it), exactly as getProviderInfo does for a self <provider>.
            if ("getServiceInfo".equals(name) && args.length >= 3 && args[0] instanceof ComponentName
                    && args[1] instanceof Long) {
                ComponentName component = (ComponentName) args[0];
                ManifestComponentProjection projection = projection(component.getPackageName());
                if (projection == null) return null;
                ComponentInfo info = projection.component(component.getClassName(), "service", bound, (Long) args[1]);
                if (info != null) {
                    System.err.println("[B8-PM] projected getServiceInfo " + component.flattenToShortString()
                            + " metaData=" + (info.metaData == null ? 0 : info.metaData.size()));
                }
                return info;
            }
            // r17u (#binaryeye): an explicit resolveService(new Intent(self, MetadataHolderService)) that
            // the bridge answers null with -- resolve it from this package's own manifest (never widens
            // to another package; a null match keeps the delegate's own answer).
            if ("resolveService".equals(name) && args.length >= 3 && args[0] instanceof Intent
                    && args[2] instanceof Long) {
                ManifestComponentProjection projection = projection(bound == null ? null : bound.packageName);
                if (projection == null) return null;
                String resolvedType = args[1] instanceof String ? (String) args[1] : null;
                ResolveInfo ri = projection.resolveComponent((Intent) args[0], resolvedType, "service", bound, (Long) args[2]);
                if (ri != null && ri.serviceInfo != null) {
                    System.err.println("[B8-PM] projected resolveService -> " + ri.serviceInfo.name
                            + " metaData=" + (ri.serviceInfo.metaData == null ? 0 : ri.serviceInfo.metaData.size()));
                }
                return ri;
            }
            if ("resolveContentProvider".equals(name) && args.length >= 3 && args[0] instanceof String
                    && args[1] instanceof Long) {
                ManifestComponentProjection projection = projection(bound == null ? null : bound.packageName);
                if (projection == null) return null;
                ProviderInfo info = projection.resolveProvider((String) args[0], bound, (Long) args[1]);
                if (info != null) {
                    System.err.println("[B8-PM] projected resolveContentProvider " + args[0] + " -> " + info.name
                            + " metaData=" + (info.metaData == null ? 0 : info.metaData.size()));
                }
                return info;
            }
        } catch (Throwable t) {
            System.err.println("[B8-PM] self-component fallback failed: " + t);
        }
        return null;
    }

    /** Manifest facts for one of this package's own providers (bind-time provider list, item 3). */
    static ProviderInfo manifestProvider(String className, long flags) {
        try {
            ManifestComponentProjection projection = projection(bound == null ? null : bound.packageName);
            if (projection == null) return null;
            return (ProviderInfo) projection.component(className, "provider", bound, flags);
        } catch (Throwable t) {
            System.err.println("[B8-PM] manifest provider lookup failed: " + t);
            return null;
        }
    }

    /** r17u (#vlc/#fd-api): set a self-package activity's theme to its own android:theme from the manifest
     *  when the bridge handed back the application theme. Read via ManifestJsonFallback.activityTheme
     *  (activity's own theme, else the app theme), same source resolveActivityTheme uses at launch. */
    private static void correctSelfActivityTheme(ActivityInfo ai, ComponentName component) {
        try {
            if (ai == null || component == null || bound == null || bound.packageName == null) return;
            if (!bound.packageName.equals(component.getPackageName()) || bound.uid != Process.myUid()) return;
            int manifestTheme = ManifestJsonFallback.activityTheme(component.getPackageName(), component.getClassName());
            if (manifestTheme != 0 && manifestTheme != ai.theme) {
                int prev = ai.theme;
                ai.theme = manifestTheme;
                System.err.println("[B8-PM] corrected getActivityInfo theme " + component.flattenToShortString()
                        + " -> 0x" + Integer.toHexString(manifestTheme) + " (was 0x" + Integer.toHexString(prev) + ")");
            }
        } catch (Throwable t) {
            System.err.println("[B8-PM] activity theme correction failed: " + t);
        }
    }

    private static synchronized ManifestComponentProjection projection(String packageName) throws Exception {
        if (bound == null || packageName == null || !packageName.equals(bound.packageName)) return null;
        if (bound.uid != Process.myUid()) return null;
        if (components != null || failed) return components;
        try {
            components = load(bound);
            return components;
        } catch (Exception e) {
            failed = true;
            throw e;
        }
    }

    private static ManifestComponentProjection load(ApplicationInfo application) throws Exception {
        ManifestComponentProjection loaded = new ManifestComponentProjection(new ApplicationInfo(application));
        boolean foundApplication = false;
        boolean matchedManifest = false;
        AssetManager assets = AssetManager.class.getDeclaredConstructor().newInstance();
        try {
            int cookie = (Integer) AssetManager.class.getMethod("addAssetPath", String.class)
                    .invoke(assets, application.sourceDir);
            if (cookie == 0) throw new IllegalArgumentException("Bound APK is unreadable");
            Resources resources = new Resources(assets, Resources.getSystem().getDisplayMetrics(),
                    Resources.getSystem().getConfiguration());
            try (XmlResourceParser xml = assets.openXmlResourceParser(cookie, "AndroidManifest.xml")) {
                for (int event = xml.next(); event != XmlResourceParser.END_DOCUMENT; event = xml.next()) {
                    if (event != XmlResourceParser.START_TAG) continue;
                    if (xml.getDepth() == 1 && "manifest".equals(xml.getName())) {
                        matchedManifest = application.packageName.equals(xml.getAttributeValue(null, "package"));
                        if (!matchedManifest) throw new SecurityException("Bound APK identity mismatch");
                    }
                    if (foundApplication && xml.getDepth() == 3) {
                        loaded.readComponent(resources, xml);
                        continue;
                    }
                    if (xml.getDepth() == 2 && "instrumentation".equals(xml.getName())) {
                        loaded.readInstrumentation(resources, xml);
                        continue;
                    }
                    if (xml.getDepth() != 2 || !"application".equals(xml.getName())) continue;
                    if (!matchedManifest || foundApplication) throw new IllegalArgumentException("Invalid application declaration");
                    foundApplication = true;
                    loaded.readApplication(resources, xml);
                }
            }
        } finally {
            assets.close();
        }
        if (!foundApplication) throw new IllegalStateException("Application declaration absent");
        System.err.println("[B8-PM] self manifest components loaded package=" + application.packageName);
        return loaded;
    }
}
