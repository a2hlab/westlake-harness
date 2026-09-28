/*
 * PackageInfoBuilder.java
 *
 * Converts OH BundleInfo (as JSON from JNI) to Android PackageInfo.
 *
 * Used by PackageManagerAdapter to return Android-compatible query results
 * when an app calls PackageManager.getPackageInfo() etc.
 *
 * Reverse conversion chain:
 *   BMS BundleInfo -> JSON (JNI) -> PackageInfoBuilder -> Android PackageInfo
 *
 * Key reverse mappings:
 *   - AbilityInfo.name (with "Ability" suffix) -> ActivityInfo.name (via IntentWantConverter)
 *   - ohos.permission.* -> android.permission.* (via PermissionMapper)
 *   - OH codePath/dataDir -> Android sourceDir/dataDir format
 */
package adapter.packagemanager;

import adapter.activity.IntentWantConverter;
import android.content.pm.ActivityInfo;
import adapter.activity.IntentWantConverter;
import android.content.pm.ApplicationInfo;
import adapter.activity.IntentWantConverter;
import android.content.pm.PackageInfo;
import adapter.activity.IntentWantConverter;
import android.content.pm.ProviderInfo;
import adapter.activity.IntentWantConverter;
import android.content.pm.ServiceInfo;
import android.content.pm.Signature;
import android.content.pm.SigningDetails;
import android.content.pm.SigningInfo;
import adapter.activity.IntentWantConverter;
import android.os.Bundle;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

public class PackageInfoBuilder {

    private static final String TAG = "OH_PkgInfoBuilder";

    /**
     * Typed Bridge result for the generation-bound ApplicationInfo query.
     *
     * Android's IPackageManager method can only return ApplicationInfo/null,
     * so callers that need the Bridge failure distinction use this envelope.
     * The standard Android entry delegates to the same decode path and keeps
     * Android's public DTO/null contract.
     */
    public static final class CanonicalApplicationInfoResult {
        public final String verdict;
        public final String reason;
        public final ApplicationInfo applicationInfo;

        private CanonicalApplicationInfoResult(
                String verdict, String reason, ApplicationInfo applicationInfo) {
            this.verdict = verdict;
            this.reason = reason;
            this.applicationInfo = applicationInfo;
        }

        public boolean isReady() {
            return "READY".equals(verdict) && applicationInfo != null;
        }
    }

    /**
     * Decode the complete typed response without collapsing absence, denied,
     * unsupported, not-ready and inconsistent outcomes into one Boolean/null.
     */
    public static CanonicalApplicationInfoResult
            decodeCanonicalApplicationInfo(String responseJson) {
        if (responseJson == null || responseJson.isEmpty()) {
            return new CanonicalApplicationInfoResult(
                    "DATA_INCONSISTENT", "JNI_EMPTY_RESPONSE", null);
        }
        try {
            JSONObject response = new JSONObject(responseJson);
            String verdict = response.getString("verdict");
            String reason = response.optString("reason", verdict);
            if (!"READY".equals(verdict)) {
                return new CanonicalApplicationInfoResult(
                        verdict, reason, null);
            }
            JSONObject view = response.getJSONObject("applicationInfo");
            ApplicationInfo ai = new ApplicationInfo();
            ai.packageName = view.getString("packageName");
            ai.className = view.getString("className");
            ai.processName = view.getString("processName");
            ai.nonLocalizedLabel = view.getString("label");
            ai.uid = view.getInt("uid");
            ai.sourceDir = view.getString("sourceDir");
            ai.publicSourceDir = view.getString("publicSourceDir");
            ai.dataDir = view.getString("dataDir");
            ai.deviceProtectedDataDir =
                    view.getString("deviceProtectedDataDir");
            ai.credentialProtectedDataDir =
                    view.getString("credentialProtectedDataDir");
            if (!view.isNull("nativeLibraryDir")) {
                ai.nativeLibraryDir = view.getString("nativeLibraryDir");
            }
            if (!view.isNull("primaryCpuAbi")) {
                ai.primaryCpuAbi = view.getString("primaryCpuAbi");
            }
            ai.minSdkVersion = view.getInt("minSdk");
            ai.targetSdkVersion = view.getInt("targetSdk");
            ai.flags = view.getInt("applicationFlags");
            ai.enabled = view.getBoolean("enabled");
            // The canonical projector does not carry Android manifest metadata
            // yet.  Keep the successful ApplicationInfo usable for callers
            // requesting GET_META_DATA; engine code legitimately reads default
            // values from this Bundle before loading any native library.
            ai.metaData = buildMetaData(view.optJSONArray("metaData"));
            return new CanonicalApplicationInfoResult(
                    verdict, reason, ai);
        } catch (Exception error) {
            Log.e(TAG, "Canonical ApplicationInfo response rejected", error);
            return new CanonicalApplicationInfoResult(
                    "DATA_INCONSISTENT", "JAVA_RESPONSE_DECODE_FAILED", null);
        }
    }

    /**
     * Decode only the complete generation-bound A05 DTO. Required identity
     * and path fields use strict getters: no BMS fallback, path synthesis or
     * corpus-specific defaults are permitted at this boundary.
     */
    public static ApplicationInfo fromCanonicalApplicationInfo(
            String responseJson) {
        return decodeCanonicalApplicationInfo(responseJson).applicationInfo;
    }

    /**
     * Build the Android DTO only from the generation-bound Bridge response.
     * Missing/negative/partial responses return null; this method never falls
     * back to BundleInfo or synthesizes package facts.
     */
    public static PackageInfo fromCanonicalPackageInfo(String responseJson) {
        if (responseJson == null || responseJson.isEmpty()) return null;
        try {
            JSONObject response = new JSONObject(responseJson);
            if (!"READY".equals(response.optString("verdict"))) return null;
            JSONObject view = response.optJSONObject("packageInfo");
            if (view == null) return null;

            PackageInfo pi = new PackageInfo();
            pi.packageName = view.getString("packageName");
            pi.versionCode = view.optInt("versionCode", 0);
            pi.versionName = view.optString("versionName", "");

            JSONObject app = view.getJSONObject("applicationInfo");
            ApplicationInfo ai = new ApplicationInfo();
            ai.packageName = app.getString("packageName");
            ai.className = app.optString("className", "");
            ai.nonLocalizedLabel = app.optString("label", "");
            ai.minSdkVersion = app.optInt("minSdk", 0);
            ai.targetSdkVersion = app.optInt("targetSdk", 0);
            ai.longVersionCode = pi.getLongVersionCode();
            ai.metaData = buildMetaData(app.optJSONArray("metaData"));
            pi.applicationInfo = ai;

            if (!view.isNull("activities")) {
                pi.activities = canonicalActivities(
                        view.getJSONArray("activities"), pi.packageName);
            }
            if (!view.isNull("receivers")) {
                pi.receivers = canonicalActivities(
                        view.getJSONArray("receivers"), pi.packageName);
            }
            if (!view.isNull("services")) {
                pi.services = canonicalServices(
                        view.getJSONArray("services"), pi.packageName);
            }
            if (!view.isNull("providers")) {
                pi.providers = canonicalProviders(
                        view.getJSONArray("providers"), pi.packageName);
            }
            if (!view.isNull("requestedPermissions")) {
                pi.requestedPermissions = stringArray(
                        view.getJSONArray("requestedPermissions"));
            }

            if (!view.isNull("signerCertificateDerHex")) {
                JSONArray certificates =
                        view.getJSONArray("signerCertificateDerHex");
                Signature[] signatures = new Signature[certificates.length()];
                for (int i = 0; i < certificates.length(); ++i) {
                    signatures[i] = new Signature(certificates.getString(i));
                }
                if (!view.isNull("signatures")) {
                    pi.signatures = signatures;
                }
                if (!view.isNull("signingCertificateDigests")) {
                    int scheme = view.optInt("signingSchemeVersion",
                            SigningDetails.SignatureSchemeVersion.UNKNOWN);
                    SigningDetails details = new SigningDetails.Builder()
                            .setSignatures(signatures)
                            .setSignatureSchemeVersion(scheme)
                            .build();
                    pi.signingInfo = new SigningInfo(details);
                }
            }
            return pi;
        } catch (Exception error) {
            Log.e(TAG, "Canonical PackageInfo response rejected", error);
            return null;
        }
    }

    private static String[] stringArray(JSONArray array) throws JSONException {
        String[] values = new String[array.length()];
        for (int i = 0; i < array.length(); ++i) values[i] = array.getString(i);
        return values;
    }

    private static ActivityInfo[] canonicalActivities(
            JSONArray array, String packageName) throws JSONException {
        ActivityInfo[] values = new ActivityInfo[array.length()];
        for (int i = 0; i < array.length(); ++i) {
            JSONObject source = array.getJSONObject(i);
            ActivityInfo value = new ActivityInfo();
            value.packageName = packageName;
            value.name = source.getString("name");
            value.exported = source.optBoolean("exported", false);
            values[i] = value;
        }
        return values;
    }

    private static ServiceInfo[] canonicalServices(
            JSONArray array, String packageName) throws JSONException {
        ServiceInfo[] values = new ServiceInfo[array.length()];
        for (int i = 0; i < array.length(); ++i) {
            JSONObject source = array.getJSONObject(i);
            ServiceInfo value = new ServiceInfo();
            value.packageName = packageName;
            value.name = source.getString("name");
            value.exported = source.optBoolean("exported", false);
            values[i] = value;
        }
        return values;
    }

    private static ProviderInfo[] canonicalProviders(
            JSONArray array, String packageName) throws JSONException {
        ProviderInfo[] values = new ProviderInfo[array.length()];
        for (int i = 0; i < array.length(); ++i) {
            JSONObject source = array.getJSONObject(i);
            ProviderInfo value = new ProviderInfo();
            value.packageName = packageName;
            value.name = source.getString("name");
            value.exported = source.optBoolean("exported", false);
            values[i] = value;
        }
        return values;
    }

    /**
     * Convert OH BundleInfo JSON to Android PackageInfo.
     *
     * Expected JSON format (from BMS via JNI):
     * {
     *   "name": "com.example.app",
     *   "versionCode": 1,
     *   "versionName": "1.0",
     *   "uid": 10086,
     *   "maxSdkVersion": 33,
     *   "abilityInfos": [{"name":"MainActivityAbility","visible":true,...}],
     *   "extensionAbilityInfos": [{"name":"MyService","type":"SERVICE",...}],
     *   "reqPermissions": ["ohos.permission.INTERNET",...]
     * }
     */
    public static PackageInfo fromBundleInfo(String bundleInfoJson) {
        PackageInfo pi = new PackageInfo();

        if (bundleInfoJson == null || bundleInfoJson.isEmpty()) {
            Log.w(TAG, "Empty bundleInfoJson");
            return pi;
        }

        try {
            JSONObject json = new JSONObject(bundleInfoJson);
            return fromBundleInfoJson(json);
        } catch (JSONException e) {
            Log.e(TAG, "Failed to parse BundleInfo JSON", e);
            return pi;
        }
    }

    /**
     * Convert OH BundleInfo JSONObject to Android PackageInfo.
     */
    public static PackageInfo fromBundleInfoJson(JSONObject json) throws JSONException {
        PackageInfo pi = new PackageInfo();

        // Basic package info
        pi.packageName = json.getString("name");
        pi.versionCode = json.optInt("versionCode", 0);
        pi.versionName = json.optString("versionName", "");

        // ApplicationInfo
        pi.applicationInfo = buildApplicationInfo(json, pi.packageName);

        // AbilityInfos -> ActivityInfo[] (reverse Ability suffix)
        JSONArray abilities = json.optJSONArray("abilityInfos");
        if (abilities != null && abilities.length() > 0) {
            pi.activities = new ActivityInfo[abilities.length()];
            for (int i = 0; i < abilities.length(); i++) {
                pi.activities[i] = buildActivityInfo(
                    abilities.getJSONObject(i), pi.packageName);
            }
        }

        // ExtensionAbilityInfos -> ServiceInfo[] + ProviderInfo[]
        JSONArray extensions = json.optJSONArray("extensionAbilityInfos");
        if (extensions != null && extensions.length() > 0) {
            buildExtensionInfos(extensions, pi);
        }

        // Permission reverse mapping (ohos.permission.* -> android.permission.*)
        JSONArray perms = json.optJSONArray("reqPermissions");
        if (perms != null && perms.length() > 0) {
            pi.requestedPermissions = new String[perms.length()];
            for (int i = 0; i < perms.length(); i++) {
                pi.requestedPermissions[i] =
                    PermissionMapper.mapToAndroid(perms.getString(i));
            }
        }

        return pi;
    }

    private static ApplicationInfo buildApplicationInfo(JSONObject json, String packageName) {
        // P1 inline: 与 OhApplicationInfoConverter 同样字段，但 PackageInfoBuilder
        // 在 BCP framework jar 中，不能引用 PathClassLoader 里的 OhApplicationInfoConverter。
        // 字段映射权威：doc/ability_manager_ipc_adapter_design.html §1.1.4
        ApplicationInfo ai = new ApplicationInfo();
        ai.packageName = packageName;

        JSONObject ohApp = json.optJSONObject("applicationInfo");
        if (ohApp == null) ohApp = new JSONObject();

        // Android guarantees a usable Bundle when callers request
        // PackageManager.GET_META_DATA.  Leaving this null crashes engines such
        // as Tuanjie/Unity before their native library is loaded.  OH metadata
        // values arrive as JSON scalars (and commonly as strings), so restore
        // the Android value type while keeping unknown values as strings.
        ai.metaData = buildMetaData(ohApp.optJSONArray("metaData"));

        // §1.1.4.1 identity & code location
        String process = ohApp.optString("process", "");
        ai.processName = process.isEmpty() ? packageName : process;

        String dataDir = ohApp.optString("dataDir", "");
        ai.dataDir = dataDir.isEmpty() ? "/data/data/" + packageName : dataDir;
        ai.deviceProtectedDataDir = ai.dataDir;
        ai.credentialProtectedDataDir = ai.dataDir;

        String codePath = ohApp.optString("codePath", "");
        if (!codePath.isEmpty() && !codePath.endsWith(".apk")) {
            ai.sourceDir = codePath + "/" + packageName + ".apk";
        } else if (!codePath.isEmpty()) {
            ai.sourceDir = codePath;
        } else {
            ai.sourceDir = "/system/app/" + packageName + "/" + packageName + ".apk";
        }
        ai.publicSourceDir = ai.sourceDir;

        String ohCpuAbi = ohApp.optString("cpuAbi", "");
        ai.primaryCpuAbi = mapAbi(ohCpuAbi);
        String nativeLibPath = ohApp.optString("nativeLibraryPath", "");
        ai.nativeLibraryDir = !nativeLibPath.isEmpty()
                ? nativeLibPath
                : "/system/app/" + packageName + "/lib/" + ai.primaryCpuAbi;

        // §1.1.4.2 process & uid
        int uid = ohApp.optInt("uid", json.optInt("uid", -1));
        ai.uid = uid;

        // §1.1.4.3 SDK version & flags
        ai.versionCode = json.optInt("versionCode", 0);
        ai.longVersionCode = ai.versionCode;
        int targetVer = ohApp.optInt("apiTargetVersion", json.optInt("maxSdkVersion", 34));
        ai.targetSdkVersion = (targetVer >= 21 && targetVer <= 36) ? targetVer : 34;
        int compatVer = ohApp.optInt("apiCompatibleVersion", 24);
        ai.minSdkVersion = (compatVer >= 21 && compatVer <= 36) ? compatVer : 24;
        ai.compileSdkVersion = ai.targetSdkVersion;

        // G2.5 (2026-04-30): OH iconId/labelId/descriptionId have type byte=0x00
        // which is invalid as Android resource ID → NotFoundException at
        // PhoneWindow.setDefaultIcon during setContentView.  Until OH→Android
        // resource ID translation is built (P3), zero out so platform default
        // icon/label fallback applies.  Both PackageItemInfo.icon (inherited)
        // AND ApplicationInfo.iconRes are zeroed because ActivityInfo.getIconResource()
        // checks `applicationInfo.icon` first (PackageItemInfo field).
        ai.icon = 0;          // PackageItemInfo.icon (inherited)
        ai.iconRes = 0;       // ApplicationInfo.iconRes
        ai.banner = 0;        // PackageItemInfo.banner (inherited)
        ai.logo = 0;          // PackageItemInfo.logo (inherited)
        ai.labelRes = 0;      // PackageItemInfo.labelRes (inherited)
        ai.descriptionRes = 0;
        ai.theme = 0;
        System.err.println("[G2.5-PIB] ApplicationInfo " + packageName
                + " icon/iconRes/labelRes/theme zeroed");

        int flags = ApplicationInfo.FLAG_HAS_CODE
                | ApplicationInfo.FLAG_INSTALLED
                | ApplicationInfo.FLAG_SUPPORTS_SCREEN_DENSITIES
                | ApplicationInfo.FLAG_ALLOW_CLEAR_USER_DATA;
        if (ohApp.optBoolean("debug", false)) flags |= ApplicationInfo.FLAG_DEBUGGABLE;
        if (ohApp.optBoolean("systemApp", false)) flags |= ApplicationInfo.FLAG_SYSTEM;
        ai.flags = flags;
        ai.enabled = ohApp.optBoolean("enabled", true);

        return ai;
    }

    private static Bundle buildMetaData(JSONArray entries) {
        Bundle result = new Bundle();
        if (entries == null) return result;

        for (int i = 0; i < entries.length(); i++) {
            JSONObject entry = entries.optJSONObject(i);
            if (entry == null) continue;

            String name = entry.optString("name", "");
            if (name.isEmpty()) continue;

            Object value = entry.opt("value");
            if (value == null || value == JSONObject.NULL) continue;
            if (value instanceof Boolean) {
                result.putBoolean(name, (Boolean) value);
            } else if (value instanceof Integer) {
                result.putInt(name, (Integer) value);
            } else if (value instanceof Long) {
                result.putLong(name, (Long) value);
            } else if (value instanceof Double) {
                result.putDouble(name, (Double) value);
            } else {
                putStringMetadata(result, name, String.valueOf(value));
            }
        }
        return result;
    }

    private static void putStringMetadata(Bundle result, String name, String value) {
        if ("true".equalsIgnoreCase(value) || "false".equalsIgnoreCase(value)) {
            result.putBoolean(name, Boolean.parseBoolean(value));
            return;
        }
        try {
            result.putInt(name, Integer.parseInt(value));
        } catch (NumberFormatException ignored) {
            result.putString(name, value);
        }
    }

    private static String mapAbi(String ohAbi) {
        if (ohAbi == null || ohAbi.isEmpty()) return "armeabi-v7a";
        switch (ohAbi) {
            case "arm": case "armeabi": case "armeabi-v7a": return "armeabi-v7a";
            case "arm64": case "arm64-v8a": return "arm64-v8a";
            case "x86": return "x86";
            case "x86_64": return "x86_64";
            default: return ohAbi;
        }
    }

    private static ActivityInfo buildActivityInfo(JSONObject abilityJson,
                                                   String packageName) throws JSONException {
        ActivityInfo ai = new ActivityInfo();
        String abilityName = abilityJson.getString("name");

        // Reverse the Ability suffix to get Android class name
        ai.name = IntentWantConverter.abilityNameToClassName(packageName, abilityName);
        ai.packageName = packageName;
        ai.exported = abilityJson.optBoolean("visible", false);

        // Launch mode reverse mapping
        String launchMode = abilityJson.optString("launchMode", "STANDARD");
        if ("SINGLETON".equals(launchMode)) {
            ai.launchMode = ActivityInfo.LAUNCH_SINGLE_TASK;
        } else {
            ai.launchMode = ActivityInfo.LAUNCH_MULTIPLE;
        }

        // Orientation reverse mapping
        String orientation = abilityJson.optString("orientation", "UNSPECIFIED");
        switch (orientation) {
            case "LANDSCAPE":
                ai.screenOrientation = ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE;
                break;
            case "PORTRAIT":
                ai.screenOrientation = ActivityInfo.SCREEN_ORIENTATION_PORTRAIT;
                break;
            default:
                ai.screenOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED;
                break;
        }

        return ai;
    }

    private static void buildExtensionInfos(JSONArray extensions,
                                              PackageInfo pi) throws JSONException {
        int serviceCount = 0;
        int providerCount = 0;

        // Count types first
        for (int i = 0; i < extensions.length(); i++) {
            JSONObject ext = extensions.getJSONObject(i);
            String type = ext.optString("type", "");
            if ("SERVICE".equals(type)) {
                serviceCount++;
            } else if ("DATASHARE".equals(type)) {
                providerCount++;
            }
            // STATICSUBSCRIBER -> Android BroadcastReceiver (handled differently, not in PackageInfo arrays)
        }

        if (serviceCount > 0) {
            pi.services = new ServiceInfo[serviceCount];
            int idx = 0;
            for (int i = 0; i < extensions.length(); i++) {
                JSONObject ext = extensions.getJSONObject(i);
                if ("SERVICE".equals(ext.optString("type", ""))) {
                    ServiceInfo si = new ServiceInfo();
                    si.name = ext.getString("name");
                    si.packageName = pi.packageName;
                    si.exported = ext.optBoolean("visible", false);
                    pi.services[idx++] = si;
                }
            }
        }

        if (providerCount > 0) {
            pi.providers = new ProviderInfo[providerCount];
            int idx = 0;
            for (int i = 0; i < extensions.length(); i++) {
                JSONObject ext = extensions.getJSONObject(i);
                if ("DATASHARE".equals(ext.optString("type", ""))) {
                    ProviderInfo pri = new ProviderInfo();
                    pri.name = ext.getString("name");
                    pri.packageName = pi.packageName;
                    pri.exported = ext.optBoolean("visible", false);
                    String uri = ext.optString("uri", "");
                    if (uri.startsWith("datashare:///")) {
                        pri.authority = uri.substring("datashare:///".length());
                    }
                    pi.providers[idx++] = pri;
                }
            }
        }
    }
}
