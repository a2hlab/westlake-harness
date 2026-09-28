#include "launcher_activity.h"

#include <cstdio>

namespace {

int failures = 0;

void Expect(bool value, const char* message)
{
    if (value) {
        std::printf("PASS %s\n", message);
    } else {
        std::fprintf(stderr, "FAIL %s\n", message);
        ++failures;
    }
}

oh_adapter::ApkManifestParser::IntentFilterData Filter(
    std::initializer_list<const char*> actions,
    std::initializer_list<const char*> categories)
{
    oh_adapter::ApkManifestParser::IntentFilterData filter;
    for (const char* action : actions) filter.actions.emplace_back(action);
    for (const char* category : categories) filter.categories.emplace_back(category);
    return filter;
}

}  // namespace

int main()
{
    using Activity = oh_adapter::ApkManifestParser::ActivityData;

    Activity valid;
    valid.intentFilters.push_back(Filter(
        {"android.intent.action.MAIN"}, {"android.intent.category.LAUNCHER"}));
    Expect(oh_adapter::IsAndroidLauncherActivity(valid),
        "enabled activity with MAIN and LAUNCHER in one filter is selectable");

    Activity disabled = valid;
    disabled.enabled = false;
    Expect(!oh_adapter::IsAndroidLauncherActivity(disabled),
        "disabled activity is not selectable");

    Activity split;
    split.intentFilters.push_back(Filter({"android.intent.action.MAIN"}, {}));
    split.intentFilters.push_back(Filter({}, {"android.intent.category.LAUNCHER"}));
    Expect(!oh_adapter::IsAndroidLauncherActivity(split),
        "MAIN and LAUNCHER in different filters are not combined");

    return failures == 0 ? 0 : 1;
}
