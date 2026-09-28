/*
 * oh_adapter_install_apk_c_entry.cpp
 *
 * Stable, read-only C ABI that libbms dlsym()s after detecting one .apk.
 * It verifies and parses one immutable snapshot and materializes its prepass
 * into GameInstallPlanWire.
 *
 * Why a separate translation unit:
 *   The C++ class methods on ApkInstaller / ApkManifestParser are mangled
 *   (clang Itanium ABI). Across toolchain refreshes the mangled names can
 *   shift; libbms can't safely dlsym a mangled name. This one C entry stays
 *   shift. The current typed entry is:
 *     extern "C" int oh_adapter_prepare_install(...);
 *
 * Why not in apk_installer.cpp directly:
 *   Keeps the C bridge surface clean and isolated from the C++ implementation
 *   so future swaps of the implementation class don't risk touching ABI.
 */

#include "apk_installer.h"
#include "apk_label_resolver.h"
#include "apk_manifest_parser.h"
#include "apk_native_inventory.h"
#include "apk_verifier_client.h"
#include "apk_verified_session_c_api.h"
#include "app_data_dir_provisioner.h"
#include "launcher_activity.h"
#include "install_prepass_materializer.h"
#include "native_payload_inspector.h"
#include "permission_mapper.h"

#include <hilog/log.h>
#include <nlohmann/json.hpp>
#include <cstdio>
#include <cstring>
#include <string>
#include <unistd.h>

#undef LOG_DOMAIN
#define LOG_DOMAIN 0xD001150
#undef LOG_TAG
#define LOG_TAG "OH_AdapterApkEntry"

#if defined(HILOG_ERROR)
#define ENTRY_LOGI(...) HILOG_INFO(LOG_CORE, __VA_ARGS__)
#define ENTRY_LOGE(...) HILOG_ERROR(LOG_CORE, __VA_ARGS__)
#else
#define ENTRY_LOGI(...) OH_LOG_INFO(LOG_APP, __VA_ARGS__)
#define ENTRY_LOGE(...) OH_LOG_ERROR(LOG_APP, __VA_ARGS__)
#endif

namespace {

bool CopyPlanString(char* dst, size_t dstSize, const std::string& value)
{
    if (dst == nullptr || dstSize == 0 || value.empty() || value.size() >= dstSize) {
        return false;
    }
    memcpy(dst, value.data(), value.size());
    dst[value.size()] = '\0';
    return true;
}

}  // namespace

extern "C" uint64_t oh_adapter_game_install_plan_abi(void)
{
    return (static_cast<uint64_t>(GAME_INSTALL_PLAN_WIRE_ABI) << 32) |
        static_cast<uint64_t>(sizeof(GameInstallPlanWire));
}

extern "C" uint64_t oh_adapter_prepass_context_abi(void)
{
    return (static_cast<uint64_t>(PREPASS_CONTEXT_WIRE_ABI) << 32) |
        static_cast<uint64_t>(sizeof(PrepassContextWire));
}

extern "C" int oh_adapter_prepare_install(const char* apkPath, int32_t userId,
    const PrepassContextWire* context, GameInstallPlanWire* plan)
{
    if (apkPath == nullptr || apkPath[0] == '\0' || plan == nullptr ||
        PrepassContextWire_Validate(context) != PREPASS_CONTEXT_WIRE_OK ||
        plan->abiVersion != GAME_INSTALL_PLAN_WIRE_ABI ||
        plan->structSize != sizeof(GameInstallPlanWire)) {
        return OH_ADAPTER_APK_VERIFY_BAD_ARGUMENT;
    }

    const uint32_t requestedAbi = plan->abiVersion;
    const uint32_t requestedSize = plan->structSize;
    memset(plan, 0, sizeof(*plan));
    plan->abiVersion = requestedAbi;
    plan->structSize = requestedSize;
    plan->apkFd = -1;
    plan->prepassFd = -1;

    oh_adapter::VerifiedApkSession session;
    std::string error;
    const int verifyResult = oh_adapter::ApkVerifierClient::OpenAndVerify(
        apkPath, 2, &session, &error);
    if (verifyResult != OH_ADAPTER_APK_VERIFY_OK) {
        ENTRY_LOGE("trusted APK verification failed: rc=%{public}d error=%{public}s",
            verifyResult, error.c_str());
        return verifyResult;
    }

    char immutablePath[64]{};
    const int pathLength = snprintf(immutablePath, sizeof(immutablePath),
        "/proc/self/fd/%d", session.sealedFd);
    if (pathLength <= 0 || static_cast<size_t>(pathLength) >= sizeof(immutablePath)) {
        oh_adapter::ApkVerifierClient::Close(&session);
        return OH_ADAPTER_APK_VERIFY_MANIFEST_FAILED;
    }
    oh_adapter::ApkManifestParser::ManifestData manifest;
    const oh_adapter::NativePayloadInfo nativePayload =
        oh_adapter::InspectApkNativePayload(immutablePath);
    if (!oh_adapter::ApkManifestParser::Parse(immutablePath, manifest) ||
        manifest.versionCode < 0 ||
        (nativePayload.state != oh_adapter::NativePayloadState::NONE &&
        (nativePayload.state != oh_adapter::NativePayloadState::SUPPORTED ||
        nativePayload.primaryAbi != "arm64-v8a")) ||
        PrepassContextWire_MatchPackageUser(context, manifest.packageName.c_str(),
            userId) != PREPASS_CONTEXT_WIRE_OK) {
        ENTRY_LOGE("manifest parse from sealed APK snapshot failed");
        oh_adapter::ApkVerifierClient::Close(&session);
        return OH_ADAPTER_APK_VERIFY_MANIFEST_FAILED;
    }

    const auto& identity = session.identity;
    if (identity.currentSignerSha256.empty() ||
        identity.currentSignerSha256.size() > GAME_INSTALL_PLAN_MAX_SIGNERS) {
        oh_adapter::ApkVerifierClient::Close(&session);
        return OH_ADAPTER_APK_VERIFY_RESPONSE_REJECTED;
    }

    const oh_adapter::ApkManifestParser::ActivityData* launcher = nullptr;
    for (const auto& activity : manifest.activities) {
        if (oh_adapter::IsAndroidLauncherActivity(activity)) {
            launcher = &activity;
            break;
        }
    }
    if (launcher == nullptr ||
        !CopyPlanString(plan->packageName, sizeof(plan->packageName), manifest.packageName) ||
        !CopyPlanString(plan->versionName, sizeof(plan->versionName), manifest.versionName) ||
        !CopyPlanString(plan->launcherActivity, sizeof(plan->launcherActivity), launcher->name) ||
        !CopyPlanString(plan->primaryAbi, sizeof(plan->primaryAbi), "arm64-v8a")) {
        oh_adapter::ApkVerifierClient::Close(&session);
        return OH_ADAPTER_APK_VERIFY_MANIFEST_FAILED;
    }

    plan->schemeVersion = identity.schemeVersion;
    plan->versionCode = static_cast<uint32_t>(manifest.versionCode);
    plan->debuggable = manifest.debuggable ? 1u : 0u;
    const std::string apkSha256 = oh_adapter::Sha256ToLowerHex(identity.apkSha256);
    memcpy(plan->apkSha256Hex, apkSha256.c_str(), apkSha256.size() + 1);

    plan->signerCount =
        static_cast<uint32_t>(identity.currentSignerSha256.size());
    for (size_t i = 0; i < identity.currentSignerSha256.size(); ++i) {
        const std::string signerSha256 =
            oh_adapter::Sha256ToLowerHex(identity.currentSignerSha256[i]);
        memcpy(plan->signerSha256Hex[i], signerSha256.c_str(),
            signerSha256.size() + 1);
    }

    std::vector<oh_adapter::ApkNativeArtifact> artifacts;
    oh_adapter::ApkNativeInventoryLimits inventoryLimits;
    if (!oh_adapter::ReadApkNativeInventory(immutablePath, "arm64-v8a",
        inventoryLimits, &artifacts, &error)) {
        oh_adapter::ApkVerifierClient::Close(&session);
        return OH_ADAPTER_APK_VERIFY_PREPASS_FAILED;
    }
    oh_adapter::package_transaction::wire::PrepassBundleRecord prepass;
    if (!oh_adapter::BuildInstallPrepass(*context, apkSha256, artifacts,
        &prepass, &error) || !oh_adapter::WriteCanonicalPrepassFd(
        prepass.canonicalPayload, &plan->prepassFd)) {
        oh_adapter::ApkVerifierClient::Close(&session);
        oh_adapter_close_game_install_plan(plan);
        return OH_ADAPTER_APK_VERIFY_PREPASS_FAILED;
    }
    plan->prepassByteLength = prepass.canonicalPayload.size();
    memcpy(plan->prepassSha256Hex, prepass.payloadSha256.c_str(),
        prepass.payloadSha256.size() + 1);
    plan->apkFd = session.sealedFd;
    session.sealedFd = -1;
    if (GameInstallPlanWire_Validate(plan) != GAME_INSTALL_PLAN_WIRE_OK) {
        oh_adapter_close_game_install_plan(plan);
        return OH_ADAPTER_APK_VERIFY_RESPONSE_REJECTED;
    }
    return OH_ADAPTER_APK_VERIFY_OK;
}

extern "C" int oh_adapter_verify_and_parse_apk(
    const char* apkPath, int32_t userId, GameInstallPlanWire* plan)
{
    (void)apkPath;
    (void)userId;
    (void)plan;
    return OH_ADAPTER_APK_VERIFY_RESPONSE_REJECTED;
}

extern "C" void oh_adapter_close_game_install_plan(GameInstallPlanWire* plan)
{
    if (plan == nullptr) return;
    if (plan->apkFd >= 0) close(plan->apkFd);
    if (plan->prepassFd >= 0) close(plan->prepassFd);
    const uint32_t abiVersion = plan->abiVersion;
    const uint32_t structSize = plan->structSize;
    memset(plan, 0, sizeof(*plan));
    plan->abiVersion = abiVersion;
    plan->structSize = structSize;
    plan->apkFd = -1;
    plan->prepassFd = -1;
}

extern "C" int oh_adapter_install_apk(const char* apkPath, int userId)
{
    (void)apkPath;
    (void)userId;
    ENTRY_LOGE("legacy pathname APK install route is disabled");
    return OH_ADAPTER_APK_VERIFY_RESPONSE_REJECTED;
}

// HanBing-compatible manifest bridge used by the minimal HelloWorld bring-up
// route. It verifies and parses an immutable snapshot before returning
// registration metadata; filesystem mutation remains in BMS/installd.
extern "C" int oh_adapter_install_apk_with_manifest(
    const char* apkPath, int userId, char* outJsonBuf, int outJsonBufSize)
{
    if (apkPath == nullptr || apkPath[0] == '\0') {
        ENTRY_LOGE("oh_adapter_install_apk_with_manifest: null/empty apkPath");
        return -1;
    }
    const std::string path(apkPath);
    ENTRY_LOGI("oh_adapter_install_apk_with_manifest: path=%{public}s userId=%{public}d",
        path.c_str(), userId);

    oh_adapter::VerifiedApkSession session;
    std::string verifyError;
    const int verifyResult = oh_adapter::ApkVerifierClient::OpenAndVerify(
        path, 1, &session, &verifyError);
    if (verifyResult != OH_ADAPTER_APK_VERIFY_OK) {
        ENTRY_LOGE("APK verification failed before manifest projection: rc=%{public}d error=%{public}s",
            verifyResult, verifyError.c_str());
        return verifyResult;
    }
    char immutablePath[64]{};
    const int immutablePathLength = snprintf(immutablePath, sizeof(immutablePath),
        "/proc/self/fd/%d", session.sealedFd);
    if (immutablePathLength <= 0 ||
        static_cast<size_t>(immutablePathLength) >= sizeof(immutablePath)) {
        oh_adapter::ApkVerifierClient::Close(&session);
        return OH_ADAPTER_APK_VERIFY_MANIFEST_FAILED;
    }

    oh_adapter::ApkManifestParser::ManifestData manifest;
    if (!oh_adapter::ApkManifestParser::Parse(immutablePath, manifest)) {
        ENTRY_LOGE("ApkManifestParser::Parse failed for sealed APK snapshot");
        oh_adapter::ApkVerifierClient::Close(&session);
        return OH_ADAPTER_APK_VERIFY_MANIFEST_FAILED;
    }
    if (manifest.packageName.empty()) {
        ENTRY_LOGE("empty packageName from manifest");
        oh_adapter::ApkVerifierClient::Close(&session);
        return OH_ADAPTER_APK_VERIFY_MANIFEST_FAILED;
    }

    auto hashUid = [](const std::string& value) -> int32_t {
        uint32_t hash = 5381;
        for (char character : value) {
            hash = ((hash << 5) + hash) + static_cast<unsigned char>(character);
        }
        return 10000 + static_cast<int32_t>(hash % 10000);
    };
    const int32_t uid = hashUid(manifest.packageName);
    const int32_t gid = uid;
    const std::string bundleRoot =
        std::string("/data/app/el1/bundle/public/") + manifest.packageName;
    const std::string deployedDir = bundleRoot + "/android";
    const std::string deployedApk = deployedDir + "/base.apk";
    const oh_adapter::NativePayloadInfo nativePayload =
        oh_adapter::InspectApkNativePayload(immutablePath);
    const std::string primaryAbi = nativePayload.primaryAbi;

    if (outJsonBuf == nullptr || outJsonBufSize <= 0) {
        ENTRY_LOGI("Skipping JSON serialization (outJsonBuf nullptr)");
        oh_adapter::ApkVerifierClient::Close(&session);
        (void)userId;
        return 0;
    }

    const std::string appLabel = oh_adapter::ResolveApkLabel(immutablePath,
        manifest.appLabel, manifest.appLabelResId, manifest.packageName);

    nlohmann::json json;
    json["bundleName"] = manifest.packageName;
    json["versionCode"] = manifest.versionCode;
    json["versionName"] = manifest.versionName;
    json["appLabel"] = appLabel;
    json["appClassName"] = manifest.appClassName;
    json["srcApkPath"] = path;
    json["deployedApkPath"] = deployedApk;
    json["deployedDir"] = deployedDir;
    json["bundleRoot"] = bundleRoot;
    json["entryHapPath"] = bundleRoot + "/entry.hap";
    json["primaryAbi"] = primaryAbi;
    json["nativePayloadState"] =
        oh_adapter::NativePayloadStateName(nativePayload.state);
    json["hasNativeLibraries"] =
        nativePayload.state == oh_adapter::NativePayloadState::SUPPORTED;
    json["uid"] = uid;
    json["gid"] = gid;
    json["minSdkVersion"] = manifest.minSdkVersion;
    json["targetSdkVersion"] = manifest.targetSdkVersion;
    json["debuggable"] = manifest.debuggable;

    nlohmann::json abilities = nlohmann::json::array();
    for (const auto& activity : manifest.activities) {
        nlohmann::json ability;
        ability["name"] = activity.name;
        ability["label"] = oh_adapter::ResolveApkLabel(immutablePath,
            activity.label, activity.labelResId, appLabel);
        ability["launchMode"] = activity.launchMode;
        ability["screenOrientation"] = activity.screenOrientation;
        ability["exported"] = activity.exported;
        nlohmann::json actions = nlohmann::json::array();
        nlohmann::json categories = nlohmann::json::array();
        const bool isMain = oh_adapter::IsAndroidLauncherActivity(activity);
        for (const auto& filter : activity.intentFilters) {
            for (const auto& action : filter.actions) {
                actions.push_back(action);
            }
            for (const auto& category : filter.categories) {
                categories.push_back(category);
            }
        }
        ability["actions"] = actions;
        ability["categories"] = categories;
        ability["isMainAbility"] = isMain;
        abilities.push_back(ability);
    }
    json["abilities"] = abilities;

    nlohmann::json services = nlohmann::json::array();
    for (const auto& service : manifest.services) {
        nlohmann::json serviceJson;
        serviceJson["name"] = service.name;
        serviceJson["exported"] = service.exported;
        serviceJson["permission"] = service.permission;
        serviceJson["mappedPermission"] = service.permission.empty()
            ? std::string()
            : oh_adapter::PermissionMapper::MapToOH(service.permission);
        std::string processName = service.processName;
        if (processName.empty()) {
            processName = manifest.appProcessName.empty()
                ? manifest.packageName
                : manifest.appProcessName;
        }
        if (!processName.empty() && processName.front() == ':') {
            processName = manifest.packageName + processName;
        }
        serviceJson["process"] = processName;
        services.push_back(serviceJson);
    }
    json["services"] = services;

    const std::string jsonText = json.dump();
    if (static_cast<int>(jsonText.size()) + 1 > outJsonBufSize) {
        ENTRY_LOGE("JSON output (%{public}zu bytes) exceeds buffer (%{public}d bytes)",
            jsonText.size(), outJsonBufSize);
        oh_adapter::ApkVerifierClient::Close(&session);
        return OH_ADAPTER_APK_VERIFY_MANIFEST_FAILED;
    }
    memcpy(outJsonBuf, jsonText.c_str(), jsonText.size() + 1);
    oh_adapter::ApkVerifierClient::Close(&session);
    ENTRY_LOGI("oh_adapter_install_apk_with_manifest: parsed pkg=%{public}s uid=%{public}d, "
               "json=%{public}zu bytes, abilities=%{public}zu services=%{public}zu",
        manifest.packageName.c_str(), uid, jsonText.size(), manifest.activities.size(),
        manifest.services.size());
    return 0;
}

// Post-registration app data directory provisioning. The BMS-side adapter
// dispatch (base_bundle_installer) calls this AFTER InnerBundleInfo got its
// real uid/gid, because oh_adapter_install_apk_with_manifest runs before
// registration and its hash uid is not the sandbox uid. Returns
// AppDataDirStatus (0 = OK); failures are typed and logged, never silent.
extern "C" int oh_adapter_create_app_data_dirs(
    const char* packageName, int32_t uid, int32_t gid, int32_t userId)
{
    if (packageName == nullptr || packageName[0] == '\0') {
        ENTRY_LOGE("oh_adapter_create_app_data_dirs: null/empty packageName");
        return oh_adapter::APP_DATA_DIR_INVALID_PACKAGE_NAME;
    }
    std::string errorDetail;
    const oh_adapter::AppDataDirStatus status = oh_adapter::EnsureAppDataDirs(
        packageName, uid, gid, userId, &errorDetail);
    if (status != oh_adapter::APP_DATA_DIR_OK) {
        ENTRY_LOGE("oh_adapter_create_app_data_dirs failed: pkg=%{public}s "
            "uid=%{public}d gid=%{public}d userId=%{public}d status=%{public}s detail=%{public}s",
            packageName, uid, gid, userId,
            oh_adapter::AppDataDirStatusName(status), errorDetail.c_str());
        return static_cast<int>(status);
    }
    ENTRY_LOGI("oh_adapter_create_app_data_dirs: pkg=%{public}s uid=%{public}d "
        "gid=%{public}d userId=%{public}d provisioned el2/base el2/log el1/database",
        packageName, uid, gid, userId);
    return 0;
}

// HanBing-compatible presentation transform. The caller is libinstalls, so
// output creation remains in the installs domain rather than foundation.
extern "C" int oh_adapter_build_resources_hap(const char* apkPath, const char* outHapPath)
{
    if (apkPath == nullptr || apkPath[0] == '\0') {
        ENTRY_LOGE("oh_adapter_build_resources_hap: null/empty apkPath");
        return -1;
    }
    if (outHapPath == nullptr || outHapPath[0] == '\0') {
        ENTRY_LOGE("oh_adapter_build_resources_hap: null/empty outHapPath");
        return -2;
    }
    ENTRY_LOGI("oh_adapter_build_resources_hap: apk=%{public}s out=%{public}s",
        apkPath, outHapPath);
    if (!oh_adapter::ApkInstaller::ExtractAndPackResourceHap(
            std::string(apkPath), std::string(outHapPath))) {
        ENTRY_LOGE("oh_adapter_build_resources_hap: ExtractAndPackResourceHap failed");
        return -3;
    }
    return 0;
}
