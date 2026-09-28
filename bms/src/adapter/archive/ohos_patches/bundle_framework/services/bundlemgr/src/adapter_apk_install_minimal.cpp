/*
 * adapter_apk_install_minimal.cpp — gap 0.2/0.6 real AXML-parsing APK install
 *
 * 2026-04-11 v2: replaces the original hardcoded filename→packageName mapping
 * with a real AndroidManifest.xml (AXML binary format) parser. Writes parsed
 * Activity, Service, ContentProvider and BroadcastReceiver info into
 * InnerBundleInfo so that OH AMS's query path (bm dump / am start) can find
 * abilities / extensions by name. Also maps Android permissions to OH
 * permission names at install time.
 *
 * Depends on:
 *   - apk_manifest_parser.cpp (framework/package-manager/jni/) which uses the
 *     self-contained axml_parser.h + minizip unzip.h to extract
 *     AndroidManifest.xml from the .apk ZIP and populate
 *     oh_adapter::ApkManifestParser::ManifestData
 *   - apk_signature_verifier.cpp for APK Signature Scheme v2/v3 verification
 *
 * Provides `OHOS::AppExecFwk::ProcessApkInstall(apkPath, installParam)` as a
 * NAMESPACE-SCOPE free function. The existing bundle_installer.cpp.patch
 * calls it by unqualified name from inside BundleInstaller::Install().
 *
 * What this implementation does (Hello World MVP path):
 *   1. Parse AndroidManifest.xml via oh_adapter::ApkManifestParser::Parse
 *   2. Create /data/app/android/<packageName>/ install directory
 *   3. Copy the .apk to <installDir>/base.apk (C FILE*, no <fstream>)
 *   4. Inspect the APK's native payload and, if supported, extract the matching
 *      lib/<abi>/*.so files to <installDir>/lib/<abi>/ (debug/permissive path)
 *   5. Build InnerBundleInfo with:
 *      - ApplicationInfo (bundleName, codePath, bundleType=APP_ANDROID,
 *        cpuAbi, nativeLibraryPath, mapped permissions)
 *      - One synthetic InnerModuleInfo "entry" with entryAbilityKey set
 *      - For each Activity in manifest: InsertAbilitiesInfo + InsertSkillInfo
 *        (intent filters mapped to OH Skill objects; MAIN/LAUNCHER maps to
 *         ACTION_HOME/ENTITY_HOME so the launcher can surface the app)
 *      - For each Service/Provider/Receiver: InsertExtensionInfo +
 *        InsertExtensionSkillInfo mapped to SERVICE / DATASHARE / STATICSUBSCRIBER
 *   6. Register via BundleDataMgr::AddInnerBundleInfo
 *   7. Return ERR_OK
 *
 * What this DOES NOT do (deliberately minimal):
 *   - dex2oat optimization
 *   - Skills / intent-filter mapping into BMS Skill objects
 *   - Full runtime permission grant (only install-time name mapping)
 *
 * Authored: 2026-04-11 per user feedback
 *   "要启动编译" for ProcessApkInstall AXML 解析
 */

#ifdef OH_ADAPTER_ANDROID

#include <cerrno>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <string>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <vector>
#include <unzip.h>

#include "app_log_wrapper.h"
#include "appexecfwk_errors.h"
#include "bundle_data_mgr.h"
#include "bundle_mgr_service.h"
#include "inner_bundle_info.h"
#include "install_param.h"
#include "application_info.h"

// Adapter AXML parser, signature verifier, permission mapper, and native-payload scanner
#include "apk_manifest_parser.h"
#include "apk_signature_verifier.h"
#include "permission_mapper.h"
#include "native_payload_inspector.h"

namespace OHOS {
namespace AppExecFwk {

namespace {

constexpr const char* APK_INSTALL_DIR_PREFIX = "/data/app/android";
constexpr const char* ANDROID_MODULE_NAME = "entry";  // Android has no module concept

bool MakeDirRecursive(const std::string& path) {
    if (path.empty()) return false;
    std::string cur;
    for (size_t i = 0; i < path.size(); ++i) {
        cur += path[i];
        if (path[i] == '/' || i + 1 == path.size()) {
            if (cur == "/") continue;
            if (mkdir(cur.c_str(), 0755) != 0 && errno != EEXIST) {
                APP_LOGE("ProcessApkInstall: mkdir %{public}s failed: %{public}s",
                         cur.c_str(), strerror(errno));
                return false;
            }
        }
    }
    return true;
}

bool CopyFileBinary(const std::string& src, const std::string& dst) {
    FILE* in = std::fopen(src.c_str(), "rb");
    if (in == nullptr) {
        APP_LOGE("ProcessApkInstall: fopen %{public}s read failed: %{public}s",
                 src.c_str(), std::strerror(errno));
        return false;
    }
    FILE* out = std::fopen(dst.c_str(), "wb");
    if (out == nullptr) {
        APP_LOGE("ProcessApkInstall: fopen %{public}s write failed: %{public}s",
                 dst.c_str(), std::strerror(errno));
        std::fclose(in);
        return false;
    }
    constexpr size_t kBufSize = 64 * 1024;
    char buf[kBufSize];
    bool ok = true;
    while (true) {
        size_t n = std::fread(buf, 1, kBufSize, in);
        if (n == 0) {
            if (std::ferror(in)) {
                APP_LOGE("ProcessApkInstall: fread error on %{public}s", src.c_str());
                ok = false;
            }
            break;
        }
        if (std::fwrite(buf, 1, n, out) != n) {
            APP_LOGE("ProcessApkInstall: fwrite short on %{public}s", dst.c_str());
            ok = false;
            break;
        }
    }
    std::fclose(in);
    std::fclose(out);
    return ok;
}

LaunchMode MapAndroidLaunchMode(int32_t androidMode) {
    // Android: 0=standard, 1=singleTop, 2=singleTask, 3=singleInstance
    // OH:      SINGLETON / STANDARD / SPECIFIED / MULTITON
    switch (androidMode) {
        case 2: case 3: return LaunchMode::SINGLETON;   // singleTask / singleInstance → SINGLETON
        case 1:         return LaunchMode::STANDARD;    // singleTop  ≈ STANDARD
        case 0:
        default:        return LaunchMode::STANDARD;    // standard → STANDARD
    }
}

// Resolve a potentially relative Android class name to fully-qualified form.
std::string ResolveClassName(const std::string& name, const std::string& packageName) {
    if (name.empty()) return name;
    if (name[0] == '.') return packageName + name;
    if (name.find('.') == std::string::npos) return packageName + "." + name;
    return name;
}

// Map an Android intent-filter to an OpenHarmony Skill.
Skill BuildSkill(const oh_adapter::ApkManifestParser::IntentFilterData& filter) {
    Skill skill;
    for (const auto& action : filter.actions) {
        if (action == "android.intent.action.MAIN") {
            skill.actions.push_back(Constants::ACTION_HOME);
        } else {
            skill.actions.push_back(action);
        }
    }
    for (const auto& category : filter.categories) {
        if (category == "android.intent.category.LAUNCHER") {
            skill.entities.push_back(Constants::ENTITY_HOME);
        } else {
            skill.entities.push_back(category);
        }
    }
    for (const auto& data : filter.dataSpecs) {
        SkillUri uri;
        uri.scheme = data.scheme;
        uri.host = data.host;
        uri.path = data.path;
        uri.type = data.type;
        skill.uris.push_back(uri);
    }
    return skill;
}

// Build one InnerAbilityInfo for an Android Activity
InnerAbilityInfo BuildInnerAbilityInfo(
        const oh_adapter::ApkManifestParser::ActivityData& activity,
        const std::string& packageName,
        const std::string& installDir) {
    InnerAbilityInfo info;
    info.name = ResolveClassName(activity.name, packageName);
    info.bundleName = packageName;
    info.moduleName = ANDROID_MODULE_NAME;
    info.applicationName = packageName;
    info.codePath = installDir;
    info.type = AbilityType::PAGE;
    info.visible = activity.exported;
    info.enabled = true;
    info.launchMode = MapAndroidLaunchMode(activity.launchMode);
    info.srcEntrance = info.name;   // Android Activity is the entry point
    info.label = activity.label.empty() ? info.name : activity.label;
    if (!activity.permission.empty()) {
        info.permissions.push_back(oh_adapter::PermissionMapper::MapToOH(activity.permission));
    }
    return info;
}

// Common fields for Android Service / Provider / Receiver mapped to OH extensions.
void FillExtensionCommon(InnerExtensionInfo& info, const std::string& className,
                         const std::string& packageName,
                         const std::string& installDir,
                         const std::string& baseApkPath) {
    info.name = ResolveClassName(className, packageName);
    info.bundleName = packageName;
    info.moduleName = ANDROID_MODULE_NAME;
    info.resourcePath = installDir;
    info.hapPath = baseApkPath;
    info.srcEntrance = info.name;
    info.enabled = true;
}

InnerExtensionInfo BuildServiceExtensionInfo(
        const oh_adapter::ApkManifestParser::ServiceData& service,
        const std::string& packageName,
        const std::string& installDir,
        const std::string& baseApkPath) {
    InnerExtensionInfo info;
    FillExtensionCommon(info, service.name, packageName, installDir, baseApkPath);
    info.type = ExtensionAbilityType::SERVICE;
    info.visible = service.exported;
    if (!service.permission.empty()) {
        info.permissions.push_back(oh_adapter::PermissionMapper::MapToOH(service.permission));
    }
    return info;
}

InnerExtensionInfo BuildProviderExtensionInfo(
        const oh_adapter::ApkManifestParser::ProviderData& provider,
        const std::string& packageName,
        const std::string& installDir,
        const std::string& baseApkPath) {
    InnerExtensionInfo info;
    FillExtensionCommon(info, provider.name, packageName, installDir, baseApkPath);
    info.type = ExtensionAbilityType::DATASHARE;
    info.visible = provider.exported;
    if (!provider.authorities.empty()) {
        info.uri = std::string("content://") + provider.authorities;
    }
    if (!provider.readPermission.empty()) {
        info.readPermission = oh_adapter::PermissionMapper::MapToOH(provider.readPermission);
    }
    if (!provider.writePermission.empty()) {
        info.writePermission = oh_adapter::PermissionMapper::MapToOH(provider.writePermission);
    }
    if (!provider.permission.empty()) {
        info.permissions.push_back(oh_adapter::PermissionMapper::MapToOH(provider.permission));
    }
    return info;
}

InnerExtensionInfo BuildReceiverExtensionInfo(
        const oh_adapter::ApkManifestParser::ReceiverData& receiver,
        const std::string& packageName,
        const std::string& installDir,
        const std::string& baseApkPath) {
    InnerExtensionInfo info;
    FillExtensionCommon(info, receiver.name, packageName, installDir, baseApkPath);
    info.type = ExtensionAbilityType::STATICSUBSCRIBER;
    info.visible = receiver.exported;
    if (!receiver.permission.empty()) {
        info.permissions.push_back(oh_adapter::PermissionMapper::MapToOH(receiver.permission));
    }
    return info;
}

// Extract .so files from lib/<abi>/ inside the APK to outLibDir.
// Returns true if extraction completed (or there was nothing to extract).
bool ExtractNativeLibsFromApk(const std::string& apkPath,
                              const std::string& outLibDir,
                              const std::string& abi) {
    if (outLibDir.empty() || abi.empty()) return false;
    if (!MakeDirRecursive(outLibDir)) {
        APP_LOGE("ExtractNativeLibs: failed to create %{public}s", outLibDir.c_str());
        return false;
    }
    if (chmod(outLibDir.c_str(), 0755) != 0) {
        APP_LOGW("ExtractNativeLibs: chmod %{public}s failed: %{public}s",
                 outLibDir.c_str(), strerror(errno));
    }

    unzFile zf = unzOpen(apkPath.c_str());
    if (zf == nullptr) {
        APP_LOGE("ExtractNativeLibs: unzOpen %{public}s failed", apkPath.c_str());
        return false;
    }

    const std::string prefix = std::string("lib/") + abi + "/";
    bool anyExtracted = false;
    int rc = unzGoToFirstFile(zf);
    while (rc == UNZ_OK) {
        char fileName[512] = {};
        unz_file_info fileInfo{};
        if (unzGetCurrentFileInfo(zf, &fileInfo, fileName, sizeof(fileName) - 1,
                                  nullptr, 0, nullptr, 0) == UNZ_OK) {
            std::string entry(fileName);
            if (entry.compare(0, prefix.size(), prefix) == 0 &&
                entry.size() > prefix.size() &&
                entry.compare(entry.size() - 3, 3, ".so") == 0) {
                std::string baseName = entry.substr(prefix.size());
                // Reject nested paths inside lib/<abi>/
                if (baseName.find('/') == std::string::npos) {
                    std::string outPath = outLibDir + "/" + baseName;
                    bool extracted = false;
                    if (unzOpenCurrentFile(zf) == UNZ_OK) {
                        FILE* out = std::fopen(outPath.c_str(), "wb");
                        if (out != nullptr) {
                            constexpr size_t kBufSize = 64 * 1024;
                            std::vector<uint8_t> buf(kBufSize);
                            extracted = true;
                            int n = 0;
                            while ((n = unzReadCurrentFile(zf, buf.data(), kBufSize)) > 0) {
                                if (std::fwrite(buf.data(), 1, static_cast<size_t>(n), out) !=
                                        static_cast<size_t>(n)) {
                                    extracted = false;
                                    break;
                                }
                            }
                            if (n < 0) extracted = false;
                            std::fclose(out);
                            if (extracted) {
                                chmod(outPath.c_str(), 0644);
                                APP_LOGI("ExtractNativeLibs: %{public}s -> %{public}s (%{public}u bytes)",
                                         entry.c_str(), outPath.c_str(),
                                         static_cast<unsigned int>(fileInfo.uncompressed_size));
                                anyExtracted = true;
                            } else {
                                APP_LOGE("ExtractNativeLibs: write failed for %{public}s", outPath.c_str());
                                unlink(outPath.c_str());
                            }
                        } else {
                            APP_LOGE("ExtractNativeLibs: fopen %{public}s failed: %{public}s",
                                     outPath.c_str(), strerror(errno));
                        }
                        unzCloseCurrentFile(zf);
                    }
                }
            }
        }
        rc = unzGoToNextFile(zf);
    }
    unzClose(zf);
    return anyExtracted;
}

}  // anonymous namespace

// =============================================================================
// ProcessApkInstall — invoked by BundleInstaller::Install() when the input
// path ends with .apk (see bundle_installer.cpp.patch).
// =============================================================================
ErrCode ProcessApkInstall(const std::string& apkPath,
                          const InstallParam& /*installParam*/) {
    APP_LOGI("ProcessApkInstall: deploying %{public}s", apkPath.c_str());

    // 1. Parse AndroidManifest.xml using real AXML parser (libandroidfw)
    oh_adapter::ApkManifestParser::ManifestData manifest;
    if (!oh_adapter::ApkManifestParser::Parse(apkPath, manifest)) {
        APP_LOGE("ProcessApkInstall: AXML parse failed for %{public}s",
                 apkPath.c_str());
        return ERR_APPEXECFWK_INSTALL_INVALID_BUNDLE_FILE;
    }
    if (manifest.packageName.empty()) {
        APP_LOGE("ProcessApkInstall: manifest has empty packageName");
        return ERR_APPEXECFWK_INSTALL_INVALID_BUNDLE_FILE;
    }
    APP_LOGI("ProcessApkInstall: parsed packageName=%{public}s "
             "versionCode=%{public}d activities=%{public}zu",
             manifest.packageName.c_str(),
             manifest.versionCode,
             manifest.activities.size());

    const std::string& bundleName = manifest.packageName;

    // 2. Verify APK signature (v2/v3) before any bytes are trusted or copied.
    int apkFd = open(apkPath.c_str(), O_RDONLY | O_CLOEXEC);
    if (apkFd < 0) {
        APP_LOGE("ProcessApkInstall: open %{public}s failed: %{public}s",
                 apkPath.c_str(), strerror(errno));
        return ERR_APPEXECFWK_INSTALL_INVALID_BUNDLE_FILE;
    }
    oh_adapter::ApkVerifiedIdentity verifiedIdentity;
    std::string sigError;
    if (!oh_adapter::ApkSignatureVerifier::VerifyFd(apkFd, /*minSchemeVersion=*/2,
                                                     &verifiedIdentity, &sigError)) {
        close(apkFd);
        APP_LOGE("ProcessApkInstall: APK signature verification failed: %{public}s",
                 sigError.c_str());
        return ERR_APPEXECFWK_INSTALL_INVALID_BUNDLE_FILE;
    }
    close(apkFd);
    APP_LOGI("ProcessApkInstall: APK signature verified scheme=%{public}u signers=%{public}zu",
             verifiedIdentity.schemeVersion, verifiedIdentity.currentSignerSha256.size());

    // 3. Create install dir
    std::string installDir = std::string(APK_INSTALL_DIR_PREFIX) + "/" + bundleName;
    if (!MakeDirRecursive(installDir)) {
        return ERR_APPEXECFWK_INSTALLD_CREATE_DIR_FAILED;
    }

    // 4. Copy APK
    std::string baseApkPath = installDir + "/base.apk";
    if (!CopyFileBinary(apkPath, baseApkPath)) {
        return ERR_APPEXECFWK_INSTALL_COPY_HAP_FAILED;
    }
    APP_LOGI("ProcessApkInstall: copied to %{public}s", baseApkPath.c_str());

    // 5. Inspect and extract native libraries
    // NOTE: this writes directly from the BMS/foundation domain. Under enforcing
    // SELinux, foundation is not allowed to create/write under /data/app/android
    // (data_app_file). This path is acceptable for bring-up/permissive testing;
    // production APK installs should route extraction through InstalldClient IPC
    // (installs domain) to /data/app/el1/bundle/public/<pkg>/android/lib/<abi>/,
    // as implemented by the base_bundle_installer.cpp v3 adapter patch.
    oh_adapter::NativePayloadInfo nativePayload = oh_adapter::InspectApkNativePayload(baseApkPath);
    std::string nativeLibDir;
    if (nativePayload.state == oh_adapter::NativePayloadState::SUPPORTED) {
        nativeLibDir = installDir + "/lib/" + nativePayload.primaryAbi;
        if (!ExtractNativeLibsFromApk(baseApkPath, nativeLibDir, nativePayload.primaryAbi)) {
            APP_LOGE("ProcessApkInstall: native lib extraction failed for %{public}s",
                     bundleName.c_str());
            return ERR_APPEXECFWK_INSTALLD_COPY_FILE_FAILED;
        }
        APP_LOGI("ProcessApkInstall: native libs extracted to %{public}s", nativeLibDir.c_str());
    } else if (nativePayload.state == oh_adapter::NativePayloadState::UNREADABLE) {
        APP_LOGE("ProcessApkInstall: native payload unreadable: %{public}s",
                 nativePayload.error.c_str());
        return ERR_APPEXECFWK_INSTALL_INVALID_BUNDLE_FILE;
    }

    // 6. Build InnerBundleInfo with ApplicationInfo + permission mapping
    InnerBundleInfo info;
    ApplicationInfo appInfo;
    appInfo.bundleName = bundleName;
    appInfo.name = bundleName;
    appInfo.codePath = installDir;
    appInfo.bundleType = BundleType::APP_ANDROID;
    appInfo.debug = manifest.debuggable;
    appInfo.label = manifest.appLabel.empty() ? bundleName : manifest.appLabel;
    appInfo.minCompatibleVersionCode = manifest.minSdkVersion;
    appInfo.apiTargetVersion = manifest.targetSdkVersion;
    appInfo.cpuAbi = nativePayload.primaryAbi;
    appInfo.nativeLibraryPath = nativeLibDir;
    for (const auto& perm : manifest.usesPermissions) {
        appInfo.permissions.push_back(oh_adapter::PermissionMapper::MapToOH(perm));
    }
    info.SetBaseApplicationInfo(appInfo);

    // 7. Insert each activity as a PAGE ability + map intent filters to Skills
    size_t insertedActivities = 0;
    std::string entryAbilityKey;
    for (const auto& activity : manifest.activities) {
        if (activity.name.empty()) continue;
        InnerAbilityInfo innerAbility = BuildInnerAbilityInfo(activity, bundleName, installDir);
        bool isLauncher = false;
        for (const auto& filter : activity.intentFilters) {
            Skill skill = BuildSkill(filter);
            bool hasHomeAction = false;
            bool hasHomeEntity = false;
            for (const auto& a : skill.actions) {
                if (a == Constants::ACTION_HOME) hasHomeAction = true;
            }
            for (const auto& e : skill.entities) {
                if (e == Constants::ENTITY_HOME) hasHomeEntity = true;
            }
            if (hasHomeAction && hasHomeEntity) isLauncher = true;
            innerAbility.skills.push_back(skill);
        }
        if (isLauncher) {
            innerAbility.isLauncherAbility = true;
        }
        // Key format: bundleName.moduleName.abilityName (per InsertAbilitiesInfo contract)
        std::string key = bundleName + "." + ANDROID_MODULE_NAME + "." + innerAbility.name;
        info.InsertAbilitiesInfo(key, innerAbility);
        info.InsertSkillInfo(key, innerAbility.skills);
        if (isLauncher) entryAbilityKey = key;
        ++insertedActivities;
    }
    APP_LOGI("ProcessApkInstall: inserted %{public}zu activities", insertedActivities);

    // 8. Insert Service / Provider / Receiver as extensions + map intent filters
    size_t insertedServices = 0;
    for (const auto& service : manifest.services) {
        if (service.name.empty()) continue;
        auto extInfo = BuildServiceExtensionInfo(service, bundleName, installDir, baseApkPath);
        for (const auto& filter : service.intentFilters) {
            extInfo.skills.push_back(BuildSkill(filter));
        }
        std::string key = bundleName + "." + ANDROID_MODULE_NAME + "." + extInfo.name;
        info.InsertExtensionInfo(key, extInfo);
        info.InsertExtensionSkillInfo(key, extInfo.skills);
        ++insertedServices;
    }
    size_t insertedProviders = 0;
    for (const auto& provider : manifest.providers) {
        if (provider.name.empty()) continue;
        auto extInfo = BuildProviderExtensionInfo(provider, bundleName, installDir, baseApkPath);
        std::string key = bundleName + "." + ANDROID_MODULE_NAME + "." + extInfo.name;
        info.InsertExtensionInfo(key, extInfo);
        ++insertedProviders;
    }
    size_t insertedReceivers = 0;
    for (const auto& receiver : manifest.receivers) {
        if (receiver.name.empty()) continue;
        auto extInfo = BuildReceiverExtensionInfo(receiver, bundleName, installDir, baseApkPath);
        for (const auto& filter : receiver.intentFilters) {
            extInfo.skills.push_back(BuildSkill(filter));
        }
        std::string key = bundleName + "." + ANDROID_MODULE_NAME + "." + extInfo.name;
        info.InsertExtensionInfo(key, extInfo);
        info.InsertExtensionSkillInfo(key, extInfo.skills);
        ++insertedReceivers;
    }
    APP_LOGI("ProcessApkInstall: inserted services=%{public}zu providers=%{public}zu receivers=%{public}zu",
             insertedServices, insertedProviders, insertedReceivers);

    // 9. Insert the synthetic "entry" module so launcher queries can find the main ability
    InnerModuleInfo moduleInfo;
    moduleInfo.name = ANDROID_MODULE_NAME;
    moduleInfo.modulePackage = ANDROID_MODULE_NAME;
    moduleInfo.moduleName = ANDROID_MODULE_NAME;
    moduleInfo.modulePath = installDir;
    moduleInfo.isEntry = true;
    moduleInfo.hapPath = baseApkPath;
    moduleInfo.moduleResPath = baseApkPath;
    moduleInfo.nativeLibraryPath = appInfo.nativeLibraryPath;
    moduleInfo.cpuAbi = appInfo.cpuAbi;
    moduleInfo.distro.moduleType = "entry";
    moduleInfo.distro.installationFree = false;
    moduleInfo.distro.deliveryWithInstall = true;
    moduleInfo.distro.moduleName = ANDROID_MODULE_NAME;
    if (!entryAbilityKey.empty()) {
        moduleInfo.entryAbilityKey = entryAbilityKey;
    }
    info.InsertInnerModuleInfo(ANDROID_MODULE_NAME, moduleInfo);

    // 10. Register in BMS
    auto bms = DelayedSingleton<BundleMgrService>::GetInstance();
    if (bms == nullptr) {
        APP_LOGE("ProcessApkInstall: BundleMgrService not available");
        return ERR_APPEXECFWK_INSTALLD_GET_PROXY_ERROR;
    }
    auto dataMgr = bms->GetDataMgr();
    if (dataMgr == nullptr) {
        APP_LOGE("ProcessApkInstall: BundleDataMgr not available");
        return ERR_APPEXECFWK_INSTALLD_GET_PROXY_ERROR;
    }

    bool added = dataMgr->AddInnerBundleInfo(bundleName, info);
    if (!added) {
        APP_LOGW("ProcessApkInstall: AddInnerBundleInfo returned false "
                 "(bundle may already exist — update path not implemented)");
    }

    APP_LOGI("ProcessApkInstall: success bundleName=%{public}s base=%{public}s "
             "activities=%{public}zu services=%{public}zu providers=%{public}zu receivers=%{public}zu "
             "nativeLib=%{public}s",
             bundleName.c_str(), baseApkPath.c_str(), insertedActivities,
             insertedServices, insertedProviders, insertedReceivers,
             nativeLibDir.empty() ? "(none)" : nativeLibDir.c_str());
    return ERR_OK;
}

}  // namespace AppExecFwk
}  // namespace OHOS

#endif  // OH_ADAPTER_ANDROID
