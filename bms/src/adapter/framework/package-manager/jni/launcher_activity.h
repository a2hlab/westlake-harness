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

}  // namespace oh_adapter

#endif  // OH_ADAPTER_LAUNCHER_ACTIVITY_H
