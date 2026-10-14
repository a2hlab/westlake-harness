/* J6 (#fd-im-vector/B10): single-purpose file (freeze unit) -- self-package application <meta-data> projection. */
package adapter.activity;

import android.content.pm.ApplicationInfo;
import android.content.res.AssetManager;
import android.content.res.XmlResourceParser;
import android.os.Bundle;

/**
 * B8/B10 (#fd-im-vector, J6): the OH bridge returns the app's own ApplicationInfo with a null/empty
 * metaData even for getApplicationInfo(self, GET_META_DATA). A library that reads its config from an
 * application-level &lt;meta-data&gt; at bind then misbehaves. Confirmed: im.vector.app declares
 * &lt;meta-data android:name="io.sentry.auto-init" android:value="false"/&gt;; with the metaData absent,
 * SentryInitProvider.onCreate defaults auto-init to true, calls SentryAndroid.init, and throws
 * "DSN is required" out of handleBindApplication (hilog j3-5ea fd-im-vector-app:39831). Projecting the
 * application meta-data makes Sentry read auto-init=false and skip init entirely.
 *
 * 32 of 47 corpus apps declare application-level meta-data (io.sentry.*, com.google.android.geo.API_KEY,
 * firebase_*, *GlideModule, com.google.android.gms.*, ...), so this is a potential common-API surface
 * (B10); im.vector is the only one that hits a bind-time metaData crash in the current sweeps.
 *
 * Parses the bound APK's &lt;application&gt;-direct &lt;meta-data&gt; (same AssetManager + XmlResourceParser
 * idiom as ManifestJsonFallback, read by android.R.attr resource id) into a Bundle and fills it in ONLY
 * for the self package, ONLY when GET_META_DATA is set and the projected metaData is empty. Its own file
 * (freeze unit); SelfComponentFallback keeps just a thin getApplicationInfo hook, so no existing method
 * behaviour changes.
 */
public final class SelfApplicationMetaData {
    private static final long GET_META_DATA = 0x00000080L;   // PackageManager.GET_META_DATA

    private SelfApplicationMetaData() {}

    /** Fill self-package application metaData for getApplicationInfo(GET_META_DATA); returns result unchanged otherwise. */
    static ApplicationInfo apply(Object[] args, ApplicationInfo result) {
        try {
            if (result == null || result.packageName == null) return result;
            if ((longArg(args) & GET_META_DATA) == 0) return result;
            if (result.metaData != null && !result.metaData.isEmpty()) return result;
            ApplicationInfo bound = SelfComponentFallback.boundInfo();
            if (bound == null || !result.packageName.equals(bound.packageName)) return result;
            String apkPath = result.sourceDir != null ? result.sourceDir : bound.sourceDir;
            if (apkPath == null) return result;
            Bundle md = applicationMetaData(apkPath);
            if (md != null && !md.isEmpty()) {
                result.metaData = md;
                System.err.println("[B8-PM] projected getApplicationInfo metaData=" + md.size()
                        + " for " + result.packageName);
            }
        } catch (Throwable t) {
            System.err.println("[B8-PM] self applicationMetaData failed: " + t);
        }
        return result;
    }

    private static long longArg(Object[] args) {
        if (args == null) return 0L;
        for (Object a : args) if (a instanceof Long) return (Long) a;
        for (Object a : args) if (a instanceof Integer) return ((Integer) a).longValue();
        return 0L;
    }

    /** The APK's &lt;application&gt;-direct &lt;meta-data&gt; as a typed Bundle (resource -> int, else value). */
    private static Bundle applicationMetaData(String apkPath) throws Exception {
        Bundle bundle = new Bundle();
        AssetManager assets = AssetManager.class.getDeclaredConstructor().newInstance();
        try {
            int cookie = (Integer) AssetManager.class.getMethod("addAssetPath", String.class).invoke(assets, apkPath);
            if (cookie == 0) return bundle;
            boolean inApplication = false;
            try (XmlResourceParser xml = assets.openXmlResourceParser(cookie, "AndroidManifest.xml")) {
                for (int event = xml.next(); event != XmlResourceParser.END_DOCUMENT; event = xml.next()) {
                    if (event == XmlResourceParser.END_TAG && xml.getDepth() == 2
                            && "application".equals(xml.getName())) {
                        break;                                        // left <application>; done
                    }
                    if (event != XmlResourceParser.START_TAG) continue;
                    String tag = xml.getName();
                    int depth = xml.getDepth();
                    if (depth == 2 && "application".equals(tag)) {
                        inApplication = true;
                    } else if (inApplication && depth == 3 && "meta-data".equals(tag)) {
                        putMeta(bundle, xml);
                    }
                }
            }
        } finally {
            assets.close();
        }
        return bundle;
    }

    private static void putMeta(Bundle bundle, XmlResourceParser xml) {
        String name = strAttr(xml, android.R.attr.name);
        if (name == null) return;
        int ri = attrIndex(xml, android.R.attr.resource);
        if (ri >= 0) { bundle.putInt(name, xml.getAttributeResourceValue(ri, 0)); return; }
        int vi = attrIndex(xml, android.R.attr.value);
        if (vi < 0) return;
        String s = xml.getAttributeValue(vi);
        if (s == null) return;
        if ("true".equals(s) || "false".equals(s)) {
            bundle.putBoolean(name, xml.getAttributeBooleanValue(vi, false));   // io.sentry.auto-init etc.
            return;
        }
        try { bundle.putInt(name, Integer.parseInt(s)); return; } catch (NumberFormatException ignore) { }
        try { bundle.putFloat(name, Float.parseFloat(s)); return; } catch (NumberFormatException ignore) { }
        bundle.putString(name, s);
    }

    // android.R.attr resource-id reads (AOSP PackageParser idiom; pooled name strings may be absent).
    private static int attrIndex(XmlResourceParser xml, int attrRes) {
        int n = xml.getAttributeCount();
        for (int i = 0; i < n; i++) if (xml.getAttributeNameResource(i) == attrRes) return i;
        return -1;
    }

    private static String strAttr(XmlResourceParser xml, int attrRes) {
        int i = attrIndex(xml, attrRes);
        return i < 0 ? null : xml.getAttributeValue(i);
    }
}
