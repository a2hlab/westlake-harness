#include "apk_label_resolver.h"
#include "apk_manifest_parser.h"
#include "launcher_activity.h"

#include <iostream>
#include <string>

int main(int argc, char** argv)
{
    if (argc < 4 || (argc - 1) % 3 != 0) {
        std::cerr << "usage: test_apk_label_resolver <apk> <package> <label> [...]\n";
        return 2;
    }

    for (int i = 1; i < argc; i += 3) {
        const std::string apkPath = argv[i];
        const std::string expectedPackage = argv[i + 1];
        const std::string expectedLabel = argv[i + 2];
        oh_adapter::ApkManifestParser::ManifestData manifest;
        if (!oh_adapter::ApkManifestParser::Parse(apkPath, manifest)) {
            std::cerr << "manifest parse failed: " << apkPath << '\n';
            return 1;
        }
        const std::string appLabel = oh_adapter::ResolveApkLabel(apkPath, manifest.appLabel,
            manifest.appLabelResId, manifest.packageName);
        if (manifest.packageName != expectedPackage || appLabel != expectedLabel) {
            std::cerr << "application label mismatch: " << apkPath
                      << " package=" << manifest.packageName
                      << " label=" << appLabel << '\n';
            return 1;
        }

        bool launcherFound = false;
        for (const auto& activity : manifest.activities) {
            if (!oh_adapter::IsAndroidLauncherActivity(activity)) {
                continue;
            }
            launcherFound = true;
            const std::string launcherLabel = oh_adapter::ResolveApkLabel(apkPath, activity.label,
                activity.labelResId, appLabel);
            if (launcherLabel != expectedLabel) {
                std::cerr << "launcher label mismatch: " << apkPath
                          << " label=" << launcherLabel << '\n';
                return 1;
            }
            break;
        }
        if (!launcherFound) {
            std::cerr << "launcher activity missing: " << apkPath << '\n';
            return 1;
        }
    }

    std::cout << "APK_LABEL_RESOLVER=PASS\n";
    return 0;
}
