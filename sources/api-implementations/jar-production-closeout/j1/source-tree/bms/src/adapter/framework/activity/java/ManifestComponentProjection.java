package adapter.activity;

import android.content.ComponentName;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.ActivityInfo;
import android.content.pm.ApplicationInfo;
import android.content.pm.ComponentInfo;
import android.content.pm.InstrumentationInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.ProviderInfo;
import android.content.pm.ResolveInfo;
import android.content.pm.ServiceInfo;
import android.content.res.Resources;
import android.content.res.TypedArray;
import android.content.res.XmlResourceParser;
import android.os.Bundle;
import android.util.TypedValue;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Static component facts for the already identity-checked, bound base APK.
 * Does not implement component dispatch, dynamic enable-state storage or grants.
 * Defaults follow Android 14 PackageParser; no fixture-specific component data.
 */
final class ManifestComponentProjection {
    private final ApplicationInfo owner;
    private final List<ActivityInfo> activities = new ArrayList<>();
    private final List<ActivityInfo> receivers = new ArrayList<>();
    private final List<ServiceInfo> services = new ArrayList<>();
    private final List<ProviderInfo> providers = new ArrayList<>();
    private final List<InstrumentationInfo> instrumentations = new ArrayList<>();
    /** Real declared &lt;intent-filter&gt; facts per activity/service component,
     * keyed by "kind#className". Populated only for the kinds resolveComponent
     * actually searches; not a general-purpose IntentFilter store. */
    private final Map<String, List<IntentFilter>> filtersByKey = new HashMap<>();
    private String applicationPermission;
    private String applicationProcess;
    private String applicationAffinity;
    private boolean applicationDirectBootAware;

    ManifestComponentProjection(ApplicationInfo owner) {
        this.owner = owner;
        applicationProcess = owner.processName;
        applicationAffinity = owner.packageName;
    }

    /** A per-call copy; applying dynamic state must never mutate the manifest cache. */
    ManifestComponentProjection withState(org.json.JSONObject snapshot) {
        try {
            ManifestComponentProjection copy = new ManifestComponentProjection(new ApplicationInfo(owner));
            copy.owner.enabled = snapshot.getBoolean("applicationEnabled");
            copy.applicationPermission = applicationPermission;
            copy.applicationProcess = applicationProcess;
            copy.applicationAffinity = applicationAffinity;
            copy.applicationDirectBootAware = applicationDirectBootAware;
            copy.filtersByKey.putAll(filtersByKey);
            copy.instrumentations.addAll(instrumentations);
            org.json.JSONObject states = snapshot.getJSONObject("components");
            for (ActivityInfo value : activities) copy.activities.add(applyState(new ActivityInfo(value), states, "activity"));
            for (ActivityInfo value : receivers) copy.receivers.add(applyState(new ActivityInfo(value), states, "receiver"));
            for (ServiceInfo value : services) copy.services.add(applyState(new ServiceInfo(value), states, "service"));
            for (ProviderInfo value : providers) copy.providers.add(applyState(new ProviderInfo(value), states, "provider"));
            return copy;
        } catch (org.json.JSONException error) {
            throw new IllegalStateException("Incomplete component authority snapshot", error);
        }
    }

    private static <T extends ComponentInfo> T applyState(T copy, org.json.JSONObject states, String kind)
            throws org.json.JSONException {
        org.json.JSONObject state = states.getJSONObject(copy.name);
        if (!kind.equals(state.getString("kind")) || copy.enabled != state.getBoolean("manifestEnabled"))
            throw new IllegalStateException("Manifest and authority component identity disagree");
        int value = state.getInt("state");
        if (value < 0 || value > 2) throw new IllegalStateException("Invalid component override");
        copy.enabled = value == 0 ? copy.enabled : value == 1;
        return copy;
    }

    void readApplication(Resources resources, XmlResourceParser xml) {
        applicationPermission = emptyToNull(string(resources, xml, android.R.attr.permission, null));
        applicationProcess = process(string(resources, xml, android.R.attr.process, owner.processName));
        applicationAffinity = affinity(string(resources, xml, android.R.attr.taskAffinity, owner.packageName));
        applicationDirectBootAware = bool(resources, xml, android.R.attr.directBootAware, false);
    }

    void readComponent(Resources resources, XmlResourceParser xml) throws Exception {
        String tag = xml.getName();
        boolean receiver = "receiver".equals(tag);
        boolean alias = "activity-alias".equals(tag);
        boolean activity = "activity".equals(tag) || alias;
        boolean service = "service".equals(tag);
        boolean provider = "provider".equals(tag);
        if (!activity && !receiver && !service && !provider) return;

        ComponentInfo info;
        if (activity || receiver) {
            ActivityInfo value;
            if (alias) {
                String target = className(string(resources, xml, android.R.attr.targetActivity, null));
                ActivityInfo found = null;
                for (ActivityInfo candidate : activities) if (target.equals(candidate.name)) found = candidate;
                if (found == null) throw new IllegalArgumentException("Alias target is absent: " + target);
                value = new ActivityInfo(found);
                value.targetActivity = target;
                value.metaData = null;
            } else {
                value = new ActivityInfo();
                value.taskAffinity = affinity(string(resources, xml, android.R.attr.taskAffinity, applicationAffinity));
                value.launchMode = integer(resources, xml, android.R.attr.launchMode, ActivityInfo.LAUNCH_MULTIPLE);
                value.screenOrientation = integer(resources, xml, android.R.attr.screenOrientation, ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED);
                value.configChanges = integer(resources, xml, android.R.attr.configChanges, 0);
                value.softInputMode = integer(resources, xml, android.R.attr.windowSoftInputMode, 0);
                value.theme = resource(resources, xml, android.R.attr.theme, 0);
            }
            value.permission = emptyToNull(string(resources, xml, android.R.attr.permission,
                    alias ? value.permission : applicationPermission));
            info = value;
        } else if (service) {
            ServiceInfo value = new ServiceInfo();
            value.permission = emptyToNull(string(resources, xml, android.R.attr.permission, applicationPermission));
            if (bool(resources, xml, android.R.attr.stopWithTask, false)) value.flags |= ServiceInfo.FLAG_STOP_WITH_TASK;
            if (bool(resources, xml, android.R.attr.isolatedProcess, false)) value.flags |= ServiceInfo.FLAG_ISOLATED_PROCESS;
            info = value;
        } else {
            ProviderInfo value = new ProviderInfo();
            value.authority = string(resources, xml, android.R.attr.authorities, null);
            if (value.authority == null || value.authority.isEmpty()) throw new IllegalArgumentException("Provider authority absent");
            String permission = string(resources, xml, android.R.attr.permission, applicationPermission);
            value.readPermission = emptyToNull(string(resources, xml, android.R.attr.readPermission, permission));
            value.writePermission = emptyToNull(string(resources, xml, android.R.attr.writePermission, permission));
            value.grantUriPermissions = bool(resources, xml, android.R.attr.grantUriPermissions, false);
            value.multiprocess = bool(resources, xml, android.R.attr.multiprocess, false);
            value.initOrder = integer(resources, xml, android.R.attr.initOrder, 0);
            info = value;
        }
        info.name = className(string(resources, xml, android.R.attr.name, null));
        info.packageName = owner.packageName;
        info.processName = alias ? info.processName : process(string(resources, xml, android.R.attr.process, applicationProcess));
        info.enabled = bool(resources, xml, android.R.attr.enabled, true);
        info.directBootAware = bool(resources, xml, android.R.attr.directBootAware, applicationDirectBootAware);
        info.icon = resource(resources, xml, android.R.attr.icon, info.icon);
        info.logo = resource(resources, xml, android.R.attr.logo, info.logo);
        info.banner = resource(resources, xml, android.R.attr.banner, info.banner);
        info.descriptionRes = resource(resources, xml, android.R.attr.description, info.descriptionRes);
        TypedArray label = resources.obtainAttributes(xml, new int[] {android.R.attr.label});
        try {
            TypedValue value = label.peekValue(0);
            if (value != null) {
                info.labelRes = value.resourceId;
                info.nonLocalizedLabel = value.resourceId == 0 ? value.coerceToString() : null;
            }
        } finally { label.recycle(); }
        boolean hasExported = has(resources, xml, android.R.attr.exported);
        info.exported = bool(resources, xml, android.R.attr.exported, provider && owner.targetSdkVersion < 17);
        int depth = xml.getDepth();
        boolean hasIntent = false;
        List<IntentFilter> componentFilters = new ArrayList<>();
        while (xml.next() != XmlResourceParser.END_DOCUMENT) {
            if (xml.getEventType() == XmlResourceParser.END_TAG && xml.getDepth() == depth) break;
            if (xml.getEventType() != XmlResourceParser.START_TAG || xml.getDepth() != depth + 1) continue;
            if ("intent-filter".equals(xml.getName())) {
                hasIntent = true;
                componentFilters.add(readIntentFilter(resources, xml));
            }
            if ("meta-data".equals(xml.getName())) {
                if (info.metaData == null) info.metaData = new Bundle();
                readMetadata(resources, xml, info.metaData);
            }
        }
        if (!provider && !hasExported) info.exported = hasIntent;
        String kind = activity ? "activity" : receiver ? "receiver" : service ? "service" : "provider";
        if (!componentFilters.isEmpty()) filtersByKey.put(kind + "#" + info.name, componentFilters);
        if (activity) activities.add((ActivityInfo) info);
        else if (receiver) receivers.add((ActivityInfo) info);
        else if (service) services.add((ServiceInfo) info);
        else providers.add((ProviderInfo) info);
    }

    /** Real declared action/category/data/priority facts for one
     * &lt;intent-filter&gt; element; consumes its full subtree. Not a general
     * IntentFilter parser (e.g. no mimeGroup) - only what this task's real
     * manifest facts require. */
    private static IntentFilter readIntentFilter(Resources resources, XmlResourceParser xml) throws Exception {
        IntentFilter filter = new IntentFilter();
        filter.setPriority(integer(resources, xml, android.R.attr.priority, 0));
        int depth = xml.getDepth();
        while (xml.next() != XmlResourceParser.END_DOCUMENT) {
            if (xml.getEventType() == XmlResourceParser.END_TAG && xml.getDepth() == depth) break;
            if (xml.getEventType() != XmlResourceParser.START_TAG || xml.getDepth() != depth + 1) continue;
            String tag = xml.getName();
            if ("action".equals(tag)) {
                String name = string(resources, xml, android.R.attr.name, null);
                if (name != null) filter.addAction(name);
            } else if ("category".equals(tag)) {
                String name = string(resources, xml, android.R.attr.name, null);
                if (name != null) filter.addCategory(name);
            } else if ("data".equals(tag)) {
                String scheme = string(resources, xml, android.R.attr.scheme, null);
                if (scheme != null) filter.addDataScheme(scheme);
                String mimeType = string(resources, xml, android.R.attr.mimeType, null);
                if (mimeType != null) filter.addDataType(mimeType);
            }
        }
        return filter;
    }

    /** Real declared &lt;instrumentation&gt; facts (a manifest sibling of
     * &lt;application&gt;, not a component inside it - readComponent() never
     * sees these). sourceDir/publicSourceDir/dataDir come from the owning
     * self package, matching real Android instrumentation identity. */
    void readInstrumentation(Resources resources, XmlResourceParser xml) {
        InstrumentationInfo info = new InstrumentationInfo();
        info.name = className(string(resources, xml, android.R.attr.name, null));
        info.packageName = owner.packageName;
        info.targetPackage = string(resources, xml, android.R.attr.targetPackage, null);
        info.functionalTest = bool(resources, xml, android.R.attr.functionalTest, false);
        info.handleProfiling = bool(resources, xml, android.R.attr.handleProfiling, false);
        info.sourceDir = owner.sourceDir;
        info.publicSourceDir = owner.publicSourceDir;
        info.dataDir = owner.dataDir;
        instrumentations.add(info);
    }

    /** Self-package instrumentation lookup, mirroring {@link #component}: real
     * declared facts only, no target launch, absence stays absence for the
     * delegate's own outcome. */
    InstrumentationInfo instrumentation(String className) {
        if (className == null) return null;
        for (InstrumentationInfo value : instrumentations) {
            if (value.name.equals(className)) return new InstrumentationInfo(value);
        }
        return null;
    }

    /** Self-package explicit/implicit resolveActivity/resolveService fallback.
     * Explicit intents reuse {@link #component} directly (no filter needed).
     * Implicit intents use the real {@link IntentFilter#match} algorithm
     * against this package's own declared filters only - never widens
     * visibility to another package, and an absent match returns null so the
     * delegate's own (possibly cross-package) answer is what the caller keeps
     * when this returns null. */
    ResolveInfo resolveComponent(Intent intent, String resolvedType, String kind, ApplicationInfo app, long flags) {
        if (intent == null || app == null) return null;
        ComponentName explicit = intent.getComponent();
        if (explicit != null) {
            if (!owner.packageName.equals(explicit.getPackageName())) return null;
            ComponentInfo found = component(explicit.getClassName(), kind, app, flags);
            return found == null ? null : wrap(found, kind, null);
        }
        String restrictToPackage = intent.getPackage();
        if (restrictToPackage != null && !owner.packageName.equals(restrictToPackage)) return null;
        List<? extends ComponentInfo> values = "activity".equals(kind) ? activities
                : "service".equals(kind) ? services : null;
        if (values == null) return null;
        ComponentInfo best = null;
        IntentFilter bestFilter = null;
        int bestPriority = Integer.MIN_VALUE;
        for (ComponentInfo value : values) {
            if (!matches(value, app, flags)) continue;
            List<IntentFilter> filters = filtersByKey.get(kind + "#" + value.name);
            if (filters == null) continue;
            for (IntentFilter filter : filters) {
                // Real Android semantics: MATCH_DEFAULT_ONLY additionally
                // requires the candidate filter to declare CATEGORY_DEFAULT;
                // IntentFilter.match() alone does not enforce this (it only
                // requires the intent's OWN categories to be a subset).
                if ((flags & PackageManager.MATCH_DEFAULT_ONLY) != 0
                        && !filter.hasCategory(Intent.CATEGORY_DEFAULT)) continue;
                int match = filter.match(intent.getAction(), resolvedType, intent.getScheme(),
                        intent.getData(), intent.getCategories(), "ManifestComponentProjection");
                if (match >= 0 && filter.getPriority() >= bestPriority) {
                    bestPriority = filter.getPriority();
                    best = value;
                    bestFilter = filter;
                }
            }
        }
        if (best == null) return null;
        ComponentInfo copy = best instanceof ActivityInfo ? new ActivityInfo((ActivityInfo) best)
                : new ServiceInfo((ServiceInfo) best);
        finish(copy, app, flags);
        // Defensive copy: bestFilter is the cached filter instance in
        // filtersByKey. Handing it out directly would let a caller mutation
        // of ResolveInfo.filter poison every future query against this
        // component (peer prebuild review, SHA f125b669).
        IntentFilter exposed = (flags & PackageManager.GET_RESOLVED_FILTER) == 0 ? null : new IntentFilter(bestFilter);
        return wrap(copy, kind, exposed);
    }

    List<ResolveInfo> queryComponents(Intent intent, String resolvedType, String kind, ApplicationInfo app, long flags) {
        List<ResolveInfo> result = new ArrayList<>();
        if (intent == null || app == null) return result;
        ComponentName explicit = intent.getComponent();
        if (explicit != null) {
            if (!owner.packageName.equals(explicit.getPackageName())) return result;
            ComponentInfo found = component(explicit.getClassName(), kind, app, flags);
            if (found != null) result.add(wrap(found, kind, null));
            return result;
        }
        if (intent.getPackage() != null && !owner.packageName.equals(intent.getPackage())) return result;
        List<? extends ComponentInfo> values = "activity".equals(kind) ? activities
                : "receiver".equals(kind) ? receivers : "service".equals(kind) ? services : providers;
        for (ComponentInfo value : values) {
            if (!matches(value, app, flags)) continue;
            List<IntentFilter> filters = filtersByKey.get(kind + "#" + value.name);
            if (filters == null) continue;
            IntentFilter best = null;
            int bestMatch = -1;
            for (IntentFilter filter : filters) {
                if ((flags & PackageManager.MATCH_DEFAULT_ONLY) != 0 && !filter.hasCategory(Intent.CATEGORY_DEFAULT)) continue;
                int match = filter.match(intent.getAction(), resolvedType, intent.getScheme(), intent.getData(),
                        intent.getCategories(), "ManifestComponentProjection");
                if (match >= 0 && (best == null || filter.getPriority() > best.getPriority())) {
                    best = filter; bestMatch = match;
                }
            }
            if (best == null) continue;
            ComponentInfo copy = value instanceof ActivityInfo ? new ActivityInfo((ActivityInfo) value)
                    : value instanceof ServiceInfo ? new ServiceInfo((ServiceInfo) value) : new ProviderInfo((ProviderInfo) value);
            finish(copy, app, flags);
            ResolveInfo resolved = wrap(copy, kind,
                    (flags & PackageManager.GET_RESOLVED_FILTER) == 0 ? null : new IntentFilter(best));
            resolved.priority = best.getPriority(); resolved.match = bestMatch;
            resolved.isDefault = best.hasCategory(Intent.CATEGORY_DEFAULT);
            result.add(resolved);
        }
        result.sort((left, right) -> Integer.compare(right.priority, left.priority));
        return result;
    }

    private static ResolveInfo wrap(ComponentInfo info, String kind, IntentFilter filter) {
        ResolveInfo resolveInfo = new ResolveInfo();
        if ("activity".equals(kind) || "receiver".equals(kind)) resolveInfo.activityInfo = (ActivityInfo) info;
        else if ("service".equals(kind)) resolveInfo.serviceInfo = (ServiceInfo) info;
        else if ("provider".equals(kind)) resolveInfo.providerInfo = (ProviderInfo) info;
        resolveInfo.filter = filter;
        return resolveInfo;
    }

    void project(PackageInfo result, long flags) {
        result.activities = (flags & PackageManager.GET_ACTIVITIES) == 0 ? null : activities(activities, result.applicationInfo, flags);
        result.receivers = (flags & PackageManager.GET_RECEIVERS) == 0 ? null : activities(receivers, result.applicationInfo, flags);
        if ((flags & PackageManager.GET_SERVICES) == 0) result.services = null;
        else {
            List<ServiceInfo> selected = new ArrayList<>();
            for (ServiceInfo value : services) if (matches(value, result.applicationInfo, flags)) {
                ServiceInfo copy = new ServiceInfo(value);
                finish(copy, result.applicationInfo, flags);
                selected.add(copy);
            }
            result.services = selected.isEmpty() ? null : selected.toArray(new ServiceInfo[0]);
        }
        if ((flags & PackageManager.GET_PROVIDERS) == 0) result.providers = null;
        else {
            List<ProviderInfo> selected = new ArrayList<>();
            for (ProviderInfo value : providers) if (matches(value, result.applicationInfo, flags)) {
                ProviderInfo copy = new ProviderInfo(value);
                finish(copy, result.applicationInfo, flags);
                selected.add(copy);
            }
            result.providers = selected.isEmpty() ? null : selected.toArray(new ProviderInfo[0]);
        }
    }

    private static ActivityInfo[] activities(List<ActivityInfo> values, ApplicationInfo app, long flags) {
        List<ActivityInfo> selected = new ArrayList<>();
        for (ActivityInfo value : values) if (matches(value, app, flags)) {
            ActivityInfo copy = new ActivityInfo(value);
            finish(copy, app, flags);
            selected.add(copy);
        }
        return selected.isEmpty() ? null : selected.toArray(new ActivityInfo[0]);
    }

    private static boolean matches(ComponentInfo value, ApplicationInfo app, long flags) {
        if ((!value.enabled || !app.enabled) && (flags & PackageManager.MATCH_DISABLED_COMPONENTS) == 0) return false;
        long bootFlags = flags & (PackageManager.MATCH_DIRECT_BOOT_AWARE | PackageManager.MATCH_DIRECT_BOOT_UNAWARE);
        return bootFlags == 0 || (value.directBootAware
                ? (bootFlags & PackageManager.MATCH_DIRECT_BOOT_AWARE) != 0
                : (bootFlags & PackageManager.MATCH_DIRECT_BOOT_UNAWARE) != 0);
    }

    private static void finish(ComponentInfo copy, ApplicationInfo app, long flags) {
        // Android semantics: every component of one PackageInfo shares the
        // SAME ApplicationInfo object as the package's top-level field
        // (PackageInfoTest#testApplicationInfoSame asserts identity, not
        // equality). Cross-query isolation is preserved because project()
        // builds a fresh top-level ApplicationInfo per PackageInfo result.
        copy.applicationInfo = app;
        copy.metaData = (flags & PackageManager.GET_META_DATA) == 0 || copy.metaData == null
                ? null : new Bundle(copy.metaData);
    }

    /** Self-package component resolution for independent component queries
     * (getActivityInfo/getServiceInfo/...). Returns null when the component is
     * absent, disabled under the requested flags, or direct-boot filtered;
     * the caller keeps the delegate's real NameNotFoundException in that case.
     * The copy shares the provided applicationInfo reference, matching the
     * same-object semantics of a full package query. */
    ComponentInfo component(String className, String kind, ApplicationInfo app, long flags) {
        if (className == null || app == null) return null;
        List<? extends ComponentInfo> values;
        if ("activity".equals(kind)) values = activities;
        else if ("receiver".equals(kind)) values = receivers;
        else if ("service".equals(kind)) values = services;
        else if ("provider".equals(kind)) values = providers;
        else return null;
        for (ComponentInfo value : values) {
            if (!value.name.equals(className)) continue;
            if (!matches(value, app, flags)) return null;
            ComponentInfo copy;
            if (value instanceof ActivityInfo) copy = new ActivityInfo((ActivityInfo) value);
            else if (value instanceof ServiceInfo) copy = new ServiceInfo((ServiceInfo) value);
            else copy = new ProviderInfo((ProviderInfo) value);
            finish(copy, app, flags);
            return copy;
        }
        return null;
    }

    /** Self-package projection for queryContentProviders: real process
     * filtering against this package's own declared providers, not a vacuous
     * empty answer regardless of input. UID authorization is the caller's
     * responsibility (same split as resolveComponent/component above); this
     * only matches manifest facts once the caller has proven it is asking
     * about its own authorized package. */
    List<ProviderInfo> queryProviders(String processName, ApplicationInfo app, long flags, String metaDataKey) {
        List<ProviderInfo> result = new ArrayList<>();
        if (app == null) return result;
        for (ProviderInfo provider : providers) {
            if (!matches(provider, app, flags)) continue;
            if (processName != null && !processName.equals(provider.processName)) continue;
            // AOSP ComponentResolverBase.java:210-216: process, then metaDataKey are
            // filtered against the ORIGINAL declared metaData; the flags-based output
            // shape (whether metaData is even returned) is a separate later step
            // (:223) and must not gate the filter itself.
            if (metaDataKey != null && (provider.metaData == null || !provider.metaData.containsKey(metaDataKey))) continue;
            ProviderInfo copy = new ProviderInfo(provider);
            finish(copy, app, flags);
            result.add(copy);
        }
        return result;
    }

    /** Self-package projection for resolveContentProvider: real authority
     * lookup (including semicolon-separated multi-authority declarations)
     * against this package's own declared providers. */
    ProviderInfo resolveProvider(String authority, ApplicationInfo app, long flags) {
        if (authority == null || app == null) return null;
        for (ProviderInfo provider : providers) {
            if (!matches(provider, app, flags)) continue;
            for (String declared : provider.authority.split(";")) {
                if (!authority.equals(declared)) continue;
                ProviderInfo copy = new ProviderInfo(provider);
                finish(copy, app, flags);
                return copy;
            }
        }
        return null;
    }

    private String className(String name) {
        if (name == null || name.isEmpty()) throw new IllegalArgumentException("Component class name absent");
        return name.startsWith(".") ? owner.packageName + name : name.indexOf('.') < 0 ? owner.packageName + "." + name : name;
    }

    private String process(String name) {
        if (name == null || name.isEmpty()) return owner.packageName;
        return name.startsWith(":") ? owner.packageName + name : name;
    }

    private String affinity(String name) {
        if (name == null || name.isEmpty()) return null;
        return name.startsWith(":") ? owner.packageName + name : name;
    }

    private static String emptyToNull(String value) { return value == null || value.isEmpty() ? null : value; }

    private static String string(Resources resources, XmlResourceParser xml, int attr, String fallback) {
        TypedArray values = resources.obtainAttributes(xml, new int[] {attr});
        try { return values.hasValue(0) ? values.getString(0) : fallback; }
        finally { values.recycle(); }
    }

    private static int integer(Resources resources, XmlResourceParser xml, int attr, int fallback) {
        TypedArray values = resources.obtainAttributes(xml, new int[] {attr});
        try { return values.getInt(0, fallback); } finally { values.recycle(); }
    }

    private static int resource(Resources resources, XmlResourceParser xml, int attr, int fallback) {
        TypedArray values = resources.obtainAttributes(xml, new int[] {attr});
        try { return values.getResourceId(0, fallback); } finally { values.recycle(); }
    }

    private static boolean bool(Resources resources, XmlResourceParser xml, int attr, boolean fallback) {
        TypedArray values = resources.obtainAttributes(xml, new int[] {attr});
        try { return values.getBoolean(0, fallback); } finally { values.recycle(); }
    }

    private static boolean has(Resources resources, XmlResourceParser xml, int attr) {
        TypedArray values = resources.obtainAttributes(xml, new int[] {attr});
        try { return values.hasValue(0); } finally { values.recycle(); }
    }

    static void readMetadata(Resources resources, XmlResourceParser xml, Bundle data) {
        TypedArray values = resources.obtainAttributes(xml,
                new int[] {android.R.attr.name, android.R.attr.value, android.R.attr.resource});
        try {
            String name = values.getString(0);
            if (name == null) throw new IllegalArgumentException("Metadata name absent");
            int resource = values.getResourceId(2, 0);
            if (resource != 0) { data.putInt(name, resource); return; }
            TypedValue value = values.peekValue(1);
            if (value == null) throw new IllegalArgumentException("Metadata value absent: " + name);
            if (value.type == TypedValue.TYPE_STRING) data.putString(name, values.getString(1));
            else if (value.type == TypedValue.TYPE_INT_BOOLEAN) data.putBoolean(name, values.getBoolean(1, false));
            else if (value.type >= TypedValue.TYPE_FIRST_INT && value.type <= TypedValue.TYPE_LAST_INT) data.putInt(name, values.getInt(1, 0));
            else if (value.type == TypedValue.TYPE_FLOAT) data.putFloat(name, values.getFloat(1, 0));
            else throw new UnsupportedOperationException("Metadata type unsupported: " + name);
        } finally { values.recycle(); }
    }
}
