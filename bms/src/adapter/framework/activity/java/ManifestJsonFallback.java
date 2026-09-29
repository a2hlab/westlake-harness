package adapter.activity;

import android.content.res.AssetManager;
import android.content.res.XmlResourceParser;

import java.io.File;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * B8 (#65) r8b: Java replacement for the missing native
 * {@code AppSchedulerBridge.nativeParseManifestJson} on generation 6cb40cd6.
 *
 * The bridge library on this generation does not export
 * {@code Java_adapter_activity_AppSchedulerBridge_nativeParseManifestJson}, so the
 * native call throws {@code UnsatisfiedLinkError} and {@code manifestJson} stays
 * empty. Downstream that means {@code AppBindData.providers} is empty (androidx.startup
 * never runs) and {@code <application android:name>} / {@code android:theme} are never
 * applied — a bare {@code android.app.Application} is instantiated (ClassCast /
 * "KoinApplication has not been started") and AppCompat activities fail the theme check.
 *
 * This produces the SAME JSON the native side would have. Schema is copied from the
 * native producer {@code bms/.../package-manager/jni/apk_manifest_jni.cpp} (keys
 * appClassName / appTheme / providers[] with name/authorities/... ), consumed unchanged
 * by {@code AppSchedulerBridge.buildProvidersFromManifest} and
 * {@code applyManifestFieldsToAppInfoLocal}. The JSON is fed back through
 * AppSchedulerBridge's own path (one call at the manifestJson assignment); nothing here
 * sets AppBindData fields directly. Attributes are read straight off the binary
 * AndroidManifest.xml by android.R.attr resource id (the AOSP PackageParser idiom), so no
 * Resources/Theme is needed; the APK is resolved with the same candidate order as the
 * native {@code ResolveApkPath}.
 */
public final class ManifestJsonFallback {
    private ManifestJsonFallback() {}

    /** current if the native parse already produced JSON, else the Java-parsed JSON. */
    public static String orFallback(String current, String bundleName) {
        if (current != null && !current.isEmpty()) return current;
        try {
            String json = manifestJson(bundleName);
            System.err.println("[B8-MANIFEST] java fallback produced len=" + json.length()
                    + " bundle=" + bundleName);
            return json;
        } catch (Throwable t) {
            System.err.println("[B8-MANIFEST] java fallback failed bundle=" + bundleName + ": " + t);
            return current == null ? "" : current;
        }
    }

    /** ResolveApkPath mirror (apk_manifest_jni.cpp): the candidate order the native side probes. */
    private static String resolveApkPath(String pkg) {
        String[] candidates = {
            "/system/app/" + pkg + "/" + pkg + ".apk",
            "/data/app/el1/bundle/public/" + pkg + "/android/base.apk",
            "/data/app/android/" + pkg + "/base.apk",
        };
        for (String p : candidates) if (new File(p).isFile()) return p;
        return null;
    }

    static String manifestJson(String bundleName) throws Exception {
        if (bundleName == null || bundleName.isEmpty()) return "";
        String apkPath = resolveApkPath(bundleName);
        if (apkPath == null) {
            System.err.println("[B8-MANIFEST] APK not found for " + bundleName);
            return "";
        }
        AssetManager assets = AssetManager.class.getDeclaredConstructor().newInstance();
        try {
            int cookie = (Integer) AssetManager.class.getMethod("addAssetPath", String.class)
                    .invoke(assets, apkPath);
            if (cookie == 0) throw new IllegalArgumentException("APK unreadable: " + apkPath);
            JSONObject j = new JSONObject();
            JSONArray providers = new JSONArray();
            boolean inApplication = false;
            try (XmlResourceParser xml = assets.openXmlResourceParser(cookie, "AndroidManifest.xml")) {
                for (int event = xml.next(); event != XmlResourceParser.END_DOCUMENT; event = xml.next()) {
                    if (event == XmlResourceParser.END_TAG && xml.getDepth() == 2
                            && "application".equals(xml.getName())) {
                        inApplication = false;
                        continue;
                    }
                    if (event != XmlResourceParser.START_TAG) continue;
                    String tag = xml.getName();
                    int depth = xml.getDepth();
                    if (depth == 1 && "manifest".equals(tag)) {
                        String pkg = xml.getAttributeValue(null, "package");
                        if (pkg != null && !pkg.isEmpty() && !pkg.equals(bundleName)) {
                            throw new SecurityException("APK manifest identity mismatch: " + pkg);
                        }
                    } else if (depth == 2 && "uses-sdk".equals(tag)) {
                        int min = intAttr(xml, android.R.attr.minSdkVersion, 0);
                        int tgt = intAttr(xml, android.R.attr.targetSdkVersion, 0);
                        if (min > 0) j.put("minSdkVersion", min);
                        if (tgt > 0) j.put("targetSdkVersion", tgt);
                    } else if (depth == 2 && "application".equals(tag)) {
                        inApplication = true;
                        readApplication(xml, j, bundleName);
                    } else if (inApplication && depth == 3 && "provider".equals(tag)) {
                        JSONObject p = readProvider(xml, bundleName);
                        if (p != null) providers.put(p);
                    }
                }
            }
            j.put("providers", providers);
            return j.toString();
        } finally {
            assets.close();
        }
    }

    private static void readApplication(XmlResourceParser xml, JSONObject j, String pkg) throws Exception {
        String cls = resolveClass(pkg, strAttr(xml, android.R.attr.name, ""));
        if (cls != null && !cls.isEmpty()) j.put("appClassName", cls);
        int theme = resAttr(xml, android.R.attr.theme, 0);
        if (theme != 0) j.put("appTheme", theme);
        int netSec = resAttr(xml, android.R.attr.networkSecurityConfig, 0);
        if (netSec != 0) j.put("networkSecurityConfigRes", netSec);
        String proc = resolveProcess(pkg, strAttr(xml, android.R.attr.process, ""));
        if (!proc.isEmpty()) j.put("appProcessName", proc);
        j.put("largeHeap", boolAttr(xml, android.R.attr.largeHeap, false));
        j.put("persistent", boolAttr(xml, android.R.attr.persistent, false));
        j.put("allowBackup", boolAttr(xml, android.R.attr.allowBackup, true));
        j.put("hardwareAccelerated", boolAttr(xml, android.R.attr.hardwareAccelerated, true));
        j.put("extractNativeLibs", boolAttr(xml, android.R.attr.extractNativeLibs, true));
    }

    private static JSONObject readProvider(XmlResourceParser xml, String pkg) throws Exception {
        String name = resolveClass(pkg, strAttr(xml, android.R.attr.name, ""));
        String authorities = strAttr(xml, android.R.attr.authorities, "");
        if (name == null || name.isEmpty()) return null;
        JSONObject p = new JSONObject();
        p.put("name", name);
        p.put("authorities", authorities == null ? "" : authorities);
        p.put("exported", boolAttr(xml, android.R.attr.exported, false));
        String read = strAttr(xml, android.R.attr.readPermission, "");
        p.put("readPermission", read == null ? "" : read);
        String write = strAttr(xml, android.R.attr.writePermission, "");
        p.put("writePermission", write == null ? "" : write);
        p.put("grantUriPermissions", boolAttr(xml, android.R.attr.grantUriPermissions, false));
        p.put("multiprocess", boolAttr(xml, android.R.attr.multiprocess, false));
        p.put("initOrder", intAttr(xml, android.R.attr.initOrder, 0));
        String proc = resolveProcess(pkg, strAttr(xml, android.R.attr.process, ""));
        p.put("processName", proc.isEmpty() ? pkg : proc);
        return p;
    }

    private static String resolveClass(String pkg, String name) {
        if (name == null || name.isEmpty()) return name;
        if (name.startsWith(".")) return pkg + name;
        if (name.indexOf('.') < 0) return pkg + "." + name;
        return name;
    }

    private static String resolveProcess(String pkg, String name) {
        if (name == null || name.isEmpty()) return "";
        return name.startsWith(":") ? pkg + name : name;
    }

    // Binary-manifest attribute reads by android.R.attr resource id (AOSP PackageParser idiom):
    // the pooled attribute name strings can be absent, but the resource id is always present.
    private static int attrIndex(XmlResourceParser xml, int attrRes) {
        int n = xml.getAttributeCount();
        for (int i = 0; i < n; i++) if (xml.getAttributeNameResource(i) == attrRes) return i;
        return -1;
    }

    private static String strAttr(XmlResourceParser xml, int attrRes, String def) {
        int i = attrIndex(xml, attrRes);
        return i < 0 ? def : xml.getAttributeValue(i);
    }

    private static int resAttr(XmlResourceParser xml, int attrRes, int def) {
        int i = attrIndex(xml, attrRes);
        return i < 0 ? def : xml.getAttributeResourceValue(i, def);
    }

    private static int intAttr(XmlResourceParser xml, int attrRes, int def) {
        int i = attrIndex(xml, attrRes);
        return i < 0 ? def : xml.getAttributeIntValue(i, def);
    }

    private static boolean boolAttr(XmlResourceParser xml, int attrRes, boolean def) {
        int i = attrIndex(xml, attrRes);
        return i < 0 ? def : xml.getAttributeBooleanValue(i, def);
    }
}
