package adapter.activity;

import android.content.pm.ProviderInfo;
import java.lang.reflect.Field;
import java.util.List;

/**
 * Bind-data provider authorities that are resource references, replaced by the authority the manifest projection
 * resolves for the same provider class.
 *
 * The bind list comes from the native manifest JSON (AppSchedulerBridge.buildProvidersFromManifest), which keeps an
 * {@code android:authorities="@string/..."} reference as the raw id ("@2131755008"). ActivityThread then publishes
 * the provider under that id, and the app's own lookups by the real authority miss it and reach the OH DataShare
 * bridge (notepad MyContentProvider, Nextcloud FileContentProvider: null Cursor). The PackageManager projection
 * (ManifestComponentProjection, read through Resources.obtainAttributes) already resolves the reference; this copies
 * its authority, by provider class name, through the same SelfComponentFallback.manifestProvider lookup
 * B8BindExtras.afterProviders uses for metaData. Literal authorities are never touched.
 */
public final class ProviderAuthorityRefs {
    private ProviderAuthorityRefs() {}

    public static void resolve(Object appBindData) {
        try {
            Field field = appBindData.getClass().getDeclaredField("providers");
            field.setAccessible(true);
            List<?> providers = (List<?>) field.get(appBindData);
            if (providers == null) return;
            int fixed = 0;
            for (Object item : providers) {
                if (!(item instanceof ProviderInfo)) continue;
                ProviderInfo info = (ProviderInfo) item;
                if (!isReference(info.authority)) continue;
                ProviderInfo projected = SelfComponentFallback.manifestProvider(info.name, 0L);
                String resolved = projected == null ? null : projected.authority;
                if (resolved == null || isReference(resolved)) {
                    log(info.name + " authority " + info.authority + " left: no projected authority");
                    continue;
                }
                log(info.name + " authority " + info.authority + " -> " + resolved);
                info.authority = resolved;
                fixed++;
            }
            if (fixed > 0) log("resolved " + fixed + " resource-reference authorit" + (fixed == 1 ? "y" : "ies"));
        } catch (Throwable t) {
            log("skipped: " + t);
        }
    }

    /** True when any ';'-separated part of the authority list is a raw resource id ("@123" or "@0x7f..."). */
    static boolean isReference(String authorities) {
        if (authorities == null) return false;
        for (String part : authorities.split(";")) {
            if (part.trim().startsWith("@")) return true;
        }
        return false;
    }

    private static void log(String message) {
        System.err.println("[B8-PROV-AUTH] " + message);
    }
}
