/*
 * Android launcher-activity selection shared by the verified plan and the
 * legacy manifest projection.  Keep this header-only: it is pure manifest
 * semantics and must be testable without an OpenHarmony runtime.
 */
#ifndef OH_ADAPTER_LAUNCHER_ACTIVITY_H
#define OH_ADAPTER_LAUNCHER_ACTIVITY_H

#include "apk_manifest_parser.h"

namespace oh_adapter {

inline bool IsAndroidLauncherActivity(const ApkManifestParser::ActivityData& activity)
{
    if (!activity.enabled) return false;
    for (const auto& filter : activity.intentFilters) {
        bool hasMain = false;
        bool hasLauncher = false;
        for (const auto& action : filter.actions) {
            hasMain = hasMain || action == "android.intent.action.MAIN";
        }
        for (const auto& category : filter.categories) {
            hasLauncher = hasLauncher || category == "android.intent.category.LAUNCHER";
        }
        if (hasMain && hasLauncher) return true;
    }
    return false;
}

// Choose the single desktop launcher activity for a manifest that may declare more than one
// MAIN+LAUNCHER activity. A merged library can contribute its own launcher (e.g.
// leakcanary.internal.activity.LeakLauncherActivity) that sorts ahead of or behind the app's real
// launcher in manifest order; picking any such foreign launcher registers the diagnostic UI as the
// desktop icon (AnkiDroid's icon launched LeakCanary's "Leaks" screen). Prefer a launcher declared in
// the app's own package namespace, falling back to the first launcher of any package when none
// matches -- so single-launcher apps and apps whose launcher lives in a different package are
// unchanged. Returns nullptr when the manifest declares no launcher activity at all.
inline const ApkManifestParser::ActivityData* SelectLauncherActivity(
        const ApkManifestParser::ManifestData& manifest)
{
    const ApkManifestParser::ActivityData* firstLauncher = nullptr;
    const std::string ownPrefix = manifest.packageName + ".";
    for (const auto& activity : manifest.activities) {
        if (!IsAndroidLauncherActivity(activity)) {
            continue;
        }
        if (firstLauncher == nullptr) {
            firstLauncher = &activity;
        }
        if (activity.name.size() >= ownPrefix.size() &&
            activity.name.compare(0, ownPrefix.size(), ownPrefix) == 0) {
            return &activity;
        }
    }
    return firstLauncher;
}

}  // namespace oh_adapter

#endif  // OH_ADAPTER_LAUNCHER_ACTIVITY_H
