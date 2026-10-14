/* r17u/J1 (#binaryeye): single-purpose file (freeze unit) -- self-package getServiceInfo/resolveService. */
package adapter.activity;

import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.ComponentInfo;
import android.content.pm.ResolveInfo;

/**
 * B8 (#binaryeye, J1): the OH BMS bridge returns null for the app's own &lt;service&gt;, so
 * ApplicationPackageManager.getServiceInfo throws NameNotFoundException. androidx.camera's
 * MetadataHolderService lookup (getServiceInfo(self, GET_META_DATA)) then makes CameraX report
 * "not configured properly" and the app System.exit(1)s in onResume (fd-binaryeye CameraActivity).
 * Answer getServiceInfo / an explicit resolveService for THIS package from the bound APK's own manifest
 * with the service's &lt;meta-data&gt; (CameraXConfig$Provider is read from it), exactly as
 * SelfComponentFallback does for a self &lt;provider&gt;.
 *
 * Split out of SelfComponentFallback into its own file so it can be frozen (AGENTS.md 做事方式 3)
 * without locking the sibling provider / activity-theme projections. SelfComponentFallback.apply()
 * delegates the two service methods here; the manifest projection + bound self ApplicationInfo are the
 * ones SelfComponentFallback already loaded.
 */
public final class SelfServiceFallback {

    /** Returned when this is not a service method this file handles (getServiceInfo can legitimately
     *  return null, so null is a real answer and cannot double as "not handled"). */
    static final Object NOT_HANDLED = new Object();

    private SelfServiceFallback() {}

    /** Called from SelfComponentFallback.apply() only for a null self-package delegate answer. */
    static Object apply(String name, Object[] args) {
        try {
            if ("getServiceInfo".equals(name) && args.length >= 3 && args[0] instanceof ComponentName
                    && args[1] instanceof Long) {
                ComponentName component = (ComponentName) args[0];
                ManifestComponentProjection projection = SelfComponentFallback.projectionFor(component.getPackageName());
                if (projection == null) return null;
                ApplicationInfo bound = SelfComponentFallback.boundInfo();
                ComponentInfo info = projection.component(component.getClassName(), "service", bound, (Long) args[1]);
                if (info != null) {
                    System.err.println("[B8-PM] projected getServiceInfo " + component.flattenToShortString()
                            + " metaData=" + (info.metaData == null ? 0 : info.metaData.size()));
                }
                return info;
            }
            if ("resolveService".equals(name) && args.length >= 3 && args[0] instanceof Intent
                    && args[2] instanceof Long) {
                ApplicationInfo bound = SelfComponentFallback.boundInfo();
                ManifestComponentProjection projection =
                        SelfComponentFallback.projectionFor(bound == null ? null : bound.packageName);
                if (projection == null) return null;
                String resolvedType = args[1] instanceof String ? (String) args[1] : null;
                ResolveInfo ri = projection.resolveComponent((Intent) args[0], resolvedType, "service", bound, (Long) args[2]);
                if (ri != null && ri.serviceInfo != null) {
                    System.err.println("[B8-PM] projected resolveService -> " + ri.serviceInfo.name
                            + " metaData=" + (ri.serviceInfo.metaData == null ? 0 : ri.serviceInfo.metaData.size()));
                }
                return ri;
            }
        } catch (Throwable t) {
            System.err.println("[B8-PM] self-service fallback failed: " + t);
        }
        return NOT_HANDLED;
    }

    /**
     * J6 (#fd-musicplayer): queryIntentServices for a self-package action. The OH bridge returns a
     * non-null EMPTY ParceledListSlice (the app's own &lt;service&gt; is not projected into query
     * results), so androidx.media3's SessionToken(context, PlaybackService) -> isInterfaceDeclared ->
     * queryIntentServices(new Intent("androidx.media3.session.MediaSessionService").setPackage(self))
     * finds nothing and throws "Failed to resolve SessionToken ... Manifest doesn't declare
     * MediaSessionService/...". Answer from the manifest's per-service &lt;intent-filter&gt; actions
     * (projection.queryComponents), merged with whatever the delegate already found. Only for the self
     * package (the intent's setPackage / component); other queries pass through (NOT_HANDLED).
     * Called from SelfComponentFallback for a non-null (possibly empty) queryIntentServices result.
     */
    static Object applyQuery(Object[] args, Object result) {
        try {
            if (args.length < 1 || !(args[0] instanceof Intent)) return NOT_HANDLED;
            Intent intent = (Intent) args[0];
            ApplicationInfo bound = SelfComponentFallback.boundInfo();
            String selfPkg = bound == null ? null : bound.packageName;
            if (selfPkg == null) return NOT_HANDLED;
            String want = intent.getPackage();
            if (want == null && intent.getComponent() != null) want = intent.getComponent().getPackageName();
            if (!selfPkg.equals(want)) return NOT_HANDLED;                 // only augment self-package queries
            ManifestComponentProjection projection = SelfComponentFallback.projectionFor(selfPkg);
            if (projection == null) return NOT_HANDLED;
            String resolvedType = args.length >= 2 && args[1] instanceof String ? (String) args[1] : null;
            long flags = longArg(args);
            java.util.List<ResolveInfo> mine = projection.queryComponents(intent, resolvedType, "service", bound, flags);
            if (mine == null || mine.isEmpty()) return NOT_HANDLED;
            java.util.List<ResolveInfo> merged = new java.util.ArrayList<ResolveInfo>(mine);
            java.util.List<ResolveInfo> existing = unwrapList(result);
            if (existing != null) merged.addAll(existing);
            System.err.println("[B8-PM] projected queryIntentServices " + intent.getAction()
                    + " -> " + mine.size() + " self service(s)");
            return wrapList(result, merged);
        } catch (Throwable t) {
            System.err.println("[B8-PM] self queryIntentServices fallback failed: " + t);
        }
        return NOT_HANDLED;
    }

    /** The long flags argument of queryIntentServices (Intent, String resolvedType, long flags, int userId). */
    private static long longArg(Object[] args) {
        for (Object a : args) if (a instanceof Long) return (Long) a;
        for (Object a : args) if (a instanceof Integer) return ((Integer) a).longValue();
        return 0L;
    }

    /** ParceledListSlice.getList() via reflection (its concrete type is hidden). */
    @SuppressWarnings("unchecked")
    private static java.util.List<ResolveInfo> unwrapList(Object slice) {
        try {
            if (slice == null) return null;
            Object list = slice.getClass().getMethod("getList").invoke(slice);
            return list instanceof java.util.List ? (java.util.List<ResolveInfo>) list : null;
        } catch (Throwable t) {
            return null;
        }
    }

    /** Wrap a List<ResolveInfo> as the same ParceledListSlice type the caller expects (new ParceledListSlice(List)). */
    private static Object wrapList(Object original, java.util.List<ResolveInfo> list) throws Throwable {
        Class<?> sliceType = original != null ? original.getClass()
                : Class.forName("android.content.pm.ParceledListSlice");
        return sliceType.getConstructor(java.util.List.class).newInstance(list);
    }
}
