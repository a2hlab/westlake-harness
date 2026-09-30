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
}
