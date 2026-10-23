/*
 * Copyright (c) 2022-2026 Huawei Device Co., Ltd.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "module_profile.h"

#include <sstream>
#include <unordered_set>

#include "app_log_tag_wrapper.h"
#include "parameter.h"
#include "parameters.h"

namespace OHOS {
namespace AppExecFwk {
namespace {
constexpr uint8_t MAX_MODULE_NAME = 128;
}

namespace Profile {
int32_t g_parseResult = ERR_OK;
std::mutex g_mutex;

const std::unordered_set<std::string> MODULE_TYPE_SET = {
    "entry",
    "feature",
    "shared"
};

const std::unordered_set<std::string> VIRTUAL_MACHINE_SET = {
    "ark",
    "default"
};

constexpr const char* BACKGROUND_MODES_MAP_KEY[] = {
    ProfileReader::KEY_DATA_TRANSFER,
    ProfileReader::KEY_AUDIO_PLAYBACK,
    ProfileReader::KEY_AUDIO_RECORDING,
    ProfileReader::KEY_LOCATION,
    ProfileReader::KEY_BLUETOOTH_INTERACTION,
    ProfileReader::KEY_MULTI_DEVICE_CONNECTION,
    ProfileReader::KEY_WIFI_INTERACTION,
    ProfileReader::KEY_VOIP,
    ProfileReader::KEY_TASK_KEEPING,
    ProfileReader::KEY_PICTURE_IN_PICTURE,
    ProfileReader::KEY_SCREEN_FETCH,
    ProfileReader::KEY_AV_PLAYBACK_AND_RECORD,
    ProfileReader::KEY_SPECIAL_SCENARIO_PROCESSING
};
const uint32_t BACKGROUND_MODES_MAP_VALUE[] = {
    ProfileReader::VALUE_DATA_TRANSFER,
    ProfileReader::VALUE_AUDIO_PLAYBACK,
    ProfileReader::VALUE_AUDIO_RECORDING,
    ProfileReader::VALUE_LOCATION,
    ProfileReader::VALUE_BLUETOOTH_INTERACTION,
    ProfileReader::VALUE_MULTI_DEVICE_CONNECTION,
    ProfileReader::VALUE_WIFI_INTERACTION,
    ProfileReader::VALUE_VOIP,
    ProfileReader::VALUE_TASK_KEEPING,
    ProfileReader::VALUE_PICTURE_IN_PICTURE,
    ProfileReader::VALUE_SCREEN_FETCH,
    ProfileReader::VALUE_AV_PLAYBACK_AND_RECORD,
    ProfileReader::VALUE_SPECIAL_SCENARIO_PROCESSING
};

const std::unordered_set<std::string> GRANT_MODE_SET = {
    "system_grant",
    "user_grant",
    "manual_settings"
};

const std::unordered_set<std::string> AVAILABLE_LEVEL_SET = {
    "system_core",
    "system_basic",
    "normal"
};

const std::unordered_map<std::string, LaunchMode> LAUNCH_MODE_MAP = {
    {"singleton", LaunchMode::SINGLETON},
    {"standard", LaunchMode::STANDARD},
    {"multiton", LaunchMode::STANDARD},
    {"specified", LaunchMode::SPECIFIED}
};
constexpr const char* DISPLAY_ORIENTATION_MAP_KEY[] = {
    "unspecified",
    "landscape",
    "portrait",
    "follow_recent",
    "landscape_inverted",
    "portrait_inverted",
    "auto_rotation",
    "auto_rotation_landscape",
    "auto_rotation_portrait",
    "auto_rotation_restricted",
    "auto_rotation_landscape_restricted",
    "auto_rotation_portrait_restricted",
    "locked",
    "auto_rotation_unspecified",
    "follow_desktop"
};
const DisplayOrientation DISPLAY_ORIENTATION_MAP_VALUE[] = {
    DisplayOrientation::UNSPECIFIED,
    DisplayOrientation::LANDSCAPE,
    DisplayOrientation::PORTRAIT,
    DisplayOrientation::FOLLOWRECENT,
    DisplayOrientation::LANDSCAPE_INVERTED,
    DisplayOrientation::PORTRAIT_INVERTED,
    DisplayOrientation::AUTO_ROTATION,
    DisplayOrientation::AUTO_ROTATION_LANDSCAPE,
    DisplayOrientation::AUTO_ROTATION_PORTRAIT,
    DisplayOrientation::AUTO_ROTATION_RESTRICTED,
    DisplayOrientation::AUTO_ROTATION_LANDSCAPE_RESTRICTED,
    DisplayOrientation::AUTO_ROTATION_PORTRAIT_RESTRICTED,
    DisplayOrientation::LOCKED,
    DisplayOrientation::AUTO_ROTATION_UNSPECIFIED,
    DisplayOrientation::FOLLOW_DESKTOP
};
const std::unordered_map<std::string, SupportWindowMode> WINDOW_MODE_MAP = {
    {"fullscreen", SupportWindowMode::FULLSCREEN},
    {"split", SupportWindowMode::SPLIT},
    {"floating", SupportWindowMode::FLOATING}
};
const std::unordered_map<std::string, BundleType> BUNDLE_TYPE_MAP = {
    {"app", BundleType::APP},
    {"atomicService", BundleType::ATOMIC_SERVICE},
    {"shared", BundleType::SHARED},
    {"appService", BundleType::APP_SERVICE_FWK}
};
const size_t MAX_QUERYSCHEMES_LENGTH = 200;

const std::unordered_map<std::string, MultiAppModeType> MULTI_APP_MODE_MAP = {
    {"multiInstance", MultiAppModeType::MULTI_INSTANCE},
    {"appClone", MultiAppModeType::APP_CLONE}
};

const std::unordered_map<std::string, AppPreloadPhase> APP_PRELOAD_PHASE_MAP = {
    {"processCreated", AppPreloadPhase::PROCESS_CREATED},
    {"abilityStageCreated", AppPreloadPhase::ABILITY_STAGE_CREATED},
    {"windowStageCreated", AppPreloadPhase::WINDOW_STAGE_CREATED}
};

struct DeviceConfig {
    // pair first : if exist in module.json then true, otherwise false
    // pair second : actual value
    std::pair<bool, int32_t> minAPIVersion = std::make_pair<>(false, 0);
    std::pair<bool, bool> keepAlive = std::make_pair<>(false, false);
    std::pair<bool, bool> removable = std::make_pair<>(false, true);
    std::pair<bool, bool> singleton = std::make_pair<>(false, false);
    std::pair<bool, bool> userDataClearable = std::make_pair<>(false, true);
    std::pair<bool, bool> accessible = std::make_pair<>(false, true);
};

struct Metadata {
    uint32_t valueId = 0;
    std::string name;
    std::string value;
    std::string resource;
};

struct HnpPackage {
    std::string package;
    std::string type;
    bool independentSign = false;
};

struct Ability {
    bool visible = false;
    bool continuable = false;
    bool removeMissionAfterTerminate = false;
    bool allowSelfRedirect = true;
    bool excludeFromMissions = false;
    bool recoverable = false;
    bool unclearableMission = false;
    bool excludeFromDock = false;
    bool isolationProcess = false;
    uint32_t descriptionId = 0;
    uint32_t iconId = 0;
    uint32_t labelId = 0;
    int32_t priority = 0;
    uint32_t startWindowId = 0;
    uint32_t startWindowIconId = 0;
    uint32_t startWindowBackgroundId = 0;
    uint32_t maxWindowWidth = 0;
    uint32_t minWindowWidth = 0;
    uint32_t maxWindowHeight = 0;
    uint32_t minWindowHeight = 0;
    uint32_t orientationId = 0;
    double maxWindowRatio = 0;
    double minWindowRatio = 0;
    std::string name;
    std::string srcEntrance;
    std::string launchType = ABILITY_LAUNCH_TYPE_DEFAULT_VALUE;
    std::string description;
    std::string icon;
    std::string label;
    std::vector<std::string> permissions;
    std::vector<Metadata> metadata;
    std::vector<Skill> skills;
    std::vector<std::string> backgroundModes;
    std::string startWindow;
    std::string startWindowIcon;
    std::string startWindowBackground;
    std::string orientation = "unspecified";
    std::vector<std::string> windowModes;
    std::string preferMultiWindowOrientation = "default";
    std::vector<std::string> continueType;
    std::vector<std::string> continueBundleNames;
    std::string process;
    std::string arkTSMode = Constants::ARKTS_MODE_DYNAMIC;
};

struct Extension {
    bool visible = false;
    bool isolationProcess = false;
    uint32_t iconId = 0;
    uint32_t labelId = 0;
    uint32_t descriptionId = 0;
    int32_t priority = 0;
    std::string name;
    std::string srcEntrance;
    std::string icon;
    std::string label;
    std::string description;
    std::string type;
    std::string readPermission;
    std::string writePermission;
    std::string uri;
    std::vector<std::string> permissions;
    std::vector<std::string> appIdentifierAllowList;
    std::vector<Skill> skills;
    std::vector<Metadata> metadata;
    std::string extensionProcessMode;
    std::vector<std::string> dataGroupIds;
    std::string customProcess;
    std::string arkTSMode = Constants::ARKTS_MODE_DYNAMIC;
};

struct MultiAppMode {
    std::string multiAppModeType;
    int32_t maxCount = 0;
};

struct TestRunner {
    std::string name;
    std::string srcPath;
    std::string arkTSMode;
};

struct App {
    bool debug = false;
    bool keepAlive = false;
    bool singleton = false;
    bool userDataClearable = true;
    bool accessible = false;
    bool multiProjects = false;
    bool asanEnabled = false;
    bool gwpAsanEnabled = false;
    bool hwasanEnabled = false;
    bool tsanEnabled = false;
    bool ubsanEnabled = false;
    bool cloudFileSyncEnabled = false;
    bool cloudStructuredDataSyncEnabled = false;
    uint32_t iconId = 0;
    uint32_t labelId = 0;
    uint32_t descriptionId = 0;
    int32_t versionCode = 0;
    int32_t minCompatibleVersionCode = -1;
    uint32_t minAPIVersion = 0;
    int32_t targetAPIVersion = 0;
    int32_t targetMinorApiVersion = 0;
    int32_t targetPatchApiVersion = 0;
    int32_t targetPriority = 0;
    int32_t maxChildProcess = OHOS::system::GetIntParameter(MAX_CHILD_PROCESS, 1);
    std::string bundleName;
    std::string icon;
    std::string label;
    std::string description;
    std::string vendor;
    std::string versionName;
    std::string buildVersion;
    std::string apiReleaseType = APP_API_RELEASETYPE_DEFAULT_VALUE;
    std::pair<bool, bool> removable = std::make_pair<>(false, true);
    std::vector<std::string> targetBundleList;
    std::map<std::string, DeviceConfig> deviceConfigs;
    std::string targetBundle;
    std::string bundleType = Profile::BUNDLE_TYPE_APP;
    std::string compileSdkVersion;
    std::string compileSdkType = Profile::COMPILE_SDK_TYPE_OPEN_HARMONY;
    std::vector<ApplicationEnvironment> appEnvironments;
    MultiAppMode multiAppMode;
    std::string configuration;
    std::string appPreloadPhase;
    std::vector<std::string> assetAccessGroups;
    std::string startMode = Profile::START_MODE_MAIN_TASK;
};

struct Module {
    bool deliveryWithInstall = false;
    bool installationFree = false;
    bool isLibIsolated = false;
    bool compressNativeLibs = true;
    bool extractNativeLibs = true;
    bool hasInsightIntent = false;
    bool deduplicateHar = false;
    uint32_t descriptionId = 0;
    int32_t targetPriority = 0;
    std::string name;
    std::string type;
    std::string srcEntrance;
    std::string abilitySrcEntryDelegator;
    std::string abilityStageSrcEntryDelegator;
    std::string description;
    std::string process;
    std::string mainElement;
    std::vector<std::string> deviceTypes;
    std::map<std::string, std::vector<std::string>> requiredDeviceFeatures;
    std::string virtualMachine = MODULE_VIRTUAL_MACHINE_DEFAULT_VALUE;
    std::string pages;
    std::string systemTheme;
    std::vector<Metadata> metadata;
    std::vector<HnpPackage> hnpPackages;
    std::vector<Ability> abilities;
    std::vector<Extension> extensionAbilities;
    std::vector<RequestPermission> requestPermissions;
    std::vector<DefinePermission> definePermissions;
    std::vector<Dependency> dependencies;
    std::string compileMode;
    std::string targetModule;
    std::vector<ProxyData> proxyDatas;
    std::vector<ProxyData> proxyData;
    std::string buildHash;
    std::string isolationMode;
    std::string fileContextMenu;
    std::string easyGo;
    std::string shareFiles;
    std::vector<std::string> querySchemes;
    std::string routerMap;
    std::vector<AppEnvironment> appEnvironments;
    std::string packageName;
    std::string crossAppSharedConfig;
    std::string appStartup;
    std::string moduleArkTSMode = Constants::ARKTS_MODE_DYNAMIC;
    std::string arkTSMode = Constants::ARKTS_MODE_DYNAMIC;
    std::string formExtensionModule;
    std::string formWidgetModule;
};

struct ModuleJson {
    App app;
    Module module;
};

void from_json(const nlohmann::json &jsonObject, TestRunner &testRunner)
{
    APP_LOGD("read testRunnerfrom module.json");
    int32_t parseResult = ERR_OK;
    const auto &jsonObjectEnd = jsonObject.end();
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        TEST_RUNNER_NAME,
        testRunner.name,
        false,
        parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        TEST_RUNNER_SRC_PATH,
        testRunner.srcPath,
        false,
        parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        TEST_RUNNER_ARKTS_MODE,
        testRunner.arkTSMode,
        false,
        parseResult);
    if (parseResult != ERR_OK) {
        APP_LOGE("read testRunner error %{public}d", parseResult);
    }
}

void from_json(const nlohmann::json &jsonObject, Metadata &metadata)
{
    APP_LOGD("read metadata tag from module.json");
    const auto &jsonObjectEnd = jsonObject.end();
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        META_DATA_VALUEID,
        metadata.valueId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        META_DATA_NAME,
        metadata.name,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        META_DATA_VALUE,
        metadata.value,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        META_DATA_RESOURCE,
        metadata.resource,
        false,
        g_parseResult);
}

void from_json(const nlohmann::json &jsonObject, HnpPackage &hnpPackage)
{
    APP_LOGD("read hnppackage tag from module.json");
    const auto &jsonObjectEnd = jsonObject.end();
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        HNP_PACKAGE,
        hnpPackage.package,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        HNP_TYPE,
        hnpPackage.type,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        HNP_INDEPENDENT_SIGN,
        hnpPackage.independentSign,
        false,
        g_parseResult);
}

void from_json(const nlohmann::json &jsonObject, Ability &ability)
{
    APP_LOGD("read ability tag from module.json");
    const auto &jsonObjectEnd = jsonObject.end();
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_NAME,
        ability.name,
        true,
        g_parseResult);
    // both srcEntry and srcEntrance can be configured, but srcEntry has higher priority
    if (jsonObject.find(SRC_ENTRY) != jsonObject.end()) {
        BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
            jsonObjectEnd,
            SRC_ENTRY,
            ability.srcEntrance,
            true,
            g_parseResult);
    } else {
        BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
            jsonObjectEnd,
            SRC_ENTRANCE,
            ability.srcEntrance,
            true,
            g_parseResult);
    }
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_LAUNCH_TYPE,
        ability.launchType,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        DESCRIPTION,
        ability.description,
        false,
        g_parseResult);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        DESCRIPTION_ID,
        ability.descriptionId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ICON,
        ability.icon,
        false,
        g_parseResult);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        ICON_ID,
        ability.iconId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        LABEL,
        ability.label,
        false,
        g_parseResult);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        LABEL_ID,
        ability.labelId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<int32_t>(jsonObject,
        jsonObjectEnd,
        PRIORITY,
        ability.priority,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<std::vector<std::string>>(jsonObject,
        jsonObjectEnd,
        PERMISSIONS,
        ability.permissions,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::STRING);
    GetValueIfFindKey<std::vector<Metadata>>(jsonObject,
        jsonObjectEnd,
        META_DATA,
        ability.metadata,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    // both exported and visible can be configured, but exported has higher priority
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        VISIBLE,
        ability.visible,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        EXPORTED,
        ability.visible,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_CONTINUABLE,
        ability.continuable,
        false,
        g_parseResult);
    GetValueIfFindKey<std::vector<Skill>>(jsonObject,
        jsonObjectEnd,
        SKILLS,
        ability.skills,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    GetValueIfFindKey<std::vector<std::string>>(jsonObject,
        jsonObjectEnd,
        ABILITY_BACKGROUNDMODES,
        ability.backgroundModes,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::STRING);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_START_WINDOW_ICON,
        ability.startWindowIcon,
        false,
        g_parseResult);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        ABILITY_START_WINDOW_ICON_ID,
        ability.startWindowIconId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_START_WINDOW_BACKGROUND,
        ability.startWindowBackground,
        false,
        g_parseResult);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        ABILITY_START_WINDOW_BACKGROUND_ID,
        ability.startWindowBackgroundId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_REMOVE_MISSION_AFTER_TERMINATE,
        ability.removeMissionAfterTerminate,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_ALLOW_SELF_REDIRECT,
        ability.allowSelfRedirect,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_ORIENTATION,
        ability.orientation,
        false,
        g_parseResult);
    GetValueIfFindKey<std::vector<std::string>>(jsonObject,
        jsonObjectEnd,
        ABILITY_SUPPORT_WINDOW_MODE,
        ability.windowModes,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::STRING);
    GetValueIfFindKey<double>(jsonObject,
        jsonObjectEnd,
        ABILITY_MAX_WINDOW_RATIO,
        ability.maxWindowRatio,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<double>(jsonObject,
        jsonObjectEnd,
        ABILITY_MIN_WINDOW_RATIO,
        ability.minWindowRatio,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        ABILITY_MAX_WINDOW_WIDTH,
        ability.maxWindowWidth,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        ABILITY_MIN_WINDOW_WIDTH,
        ability.minWindowWidth,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        ABILITY_MAX_WINDOW_HEIGHT,
        ability.maxWindowHeight,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        ABILITY_MIN_WINDOW_HEIGHT,
        ability.minWindowHeight,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_EXCLUDE_FROM_MISSIONS,
        ability.excludeFromMissions,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_RECOVERABLE,
        ability.recoverable,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_UNCLEARABLE_MISSION,
        ability.unclearableMission,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_EXCLUDEFROMDOCK_MISSION,
        ability.excludeFromDock,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_PREFER_MULTI_WINDOW_ORIENTATION_MISSION,
        ability.preferMultiWindowOrientation,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_ISOLATION_PROCESS,
        ability.isolationProcess,
        false,
        g_parseResult);
    GetValueIfFindKey<std::vector<std::string>>(jsonObject,
        jsonObjectEnd,
        ABILITY_CONTINUE_TYPE,
        ability.continueType,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::STRING);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        ABILITY_ORIENTATION_ID,
        ability.orientationId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<std::vector<std::string>>(jsonObject,
        jsonObjectEnd,
        ABILITY_CONTINUE_BUNDLE_NAME,
        ability.continueBundleNames,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::STRING);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_PROCESS,
        ability.process,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        Constants::ARKTS_MODE,
        ability.arkTSMode,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_START_WINDOW,
        ability.startWindow,
        false,
        g_parseResult);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        ABILITY_START_WINDOW_ID,
        ability.startWindowId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
}

void from_json(const nlohmann::json &jsonObject, Extension &extension)
{
    APP_LOGD("read extension tag from module.json");
    const auto &jsonObjectEnd = jsonObject.end();
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        EXTENSION_ABILITY_NAME,
        extension.name,
        true,
        g_parseResult);
    // both srcEntry and srcEntrance can be configured, but srcEntry has higher priority
    if (jsonObject.find(SRC_ENTRY) != jsonObject.end()) {
        BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
            jsonObjectEnd,
            SRC_ENTRY,
            extension.srcEntrance,
            true,
            g_parseResult);
    } else {
        BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
            jsonObjectEnd,
            SRC_ENTRANCE,
            extension.srcEntrance,
            true,
            g_parseResult);
    }
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ICON,
        extension.icon,
        false,
        g_parseResult);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        ICON_ID,
        extension.iconId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        LABEL,
        extension.label,
        false,
        g_parseResult);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        LABEL_ID,
        extension.labelId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        DESCRIPTION,
        extension.description,
        false,
        g_parseResult);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        DESCRIPTION_ID,
        extension.descriptionId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<int32_t>(jsonObject,
        jsonObjectEnd,
        PRIORITY,
        extension.priority,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        EXTENSION_ABILITY_TYPE,
        extension.type,
        true,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        EXTENSION_ABILITY_READ_PERMISSION,
        extension.readPermission,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        EXTENSION_ABILITY_WRITE_PERMISSION,
        extension.writePermission,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        EXTENSION_URI,
        extension.uri,
        false,
        g_parseResult);
    GetValueIfFindKey<std::vector<std::string>>(jsonObject,
        jsonObjectEnd,
        PERMISSIONS,
        extension.permissions,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::STRING);
    GetValueIfFindKey<std::vector<std::string>>(jsonObject,
        jsonObjectEnd,
        APPIDENTIFIER_ALLOW_LIST,
        extension.appIdentifierAllowList,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::STRING);
    // both exported and visible can be configured, but exported has higher priority
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        VISIBLE,
        extension.visible,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        EXPORTED,
        extension.visible,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ABILITY_ISOLATION_PROCESS,
        extension.isolationProcess,
        false,
        g_parseResult);
    GetValueIfFindKey<std::vector<Skill>>(jsonObject,
        jsonObjectEnd,
        SKILLS,
        extension.skills,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    GetValueIfFindKey<std::vector<Metadata>>(jsonObject,
        jsonObjectEnd,
        META_DATA,
        extension.metadata,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        EXTENSION_PROCESS_MODE,
        extension.extensionProcessMode,
        false,
        g_parseResult);
    GetValueIfFindKey<std::vector<std::string>>(jsonObject,
        jsonObjectEnd,
        DATA_GROUP_IDS,
        extension.dataGroupIds,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::STRING);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_PROCESS,
        extension.customProcess,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        Constants::ARKTS_MODE,
        extension.arkTSMode,
        false,
        g_parseResult);
}

void from_json(const nlohmann::json &jsonObject, DeviceConfig &deviceConfig)
{
    const auto &jsonObjectEnd = jsonObject.end();
    if (jsonObject.find(MIN_API_VERSION) != jsonObjectEnd) {
        deviceConfig.minAPIVersion.first = true;
        GetValueIfFindKey<int32_t>(jsonObject,
            jsonObjectEnd,
            MIN_API_VERSION,
            deviceConfig.minAPIVersion.second,
            JsonType::NUMBER,
            false,
            g_parseResult,
            ArrayType::NOT_ARRAY);
    }
    if (jsonObject.find(DEVICE_CONFIG_KEEP_ALIVE) != jsonObjectEnd) {
        deviceConfig.keepAlive.first = true;
        BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
            jsonObjectEnd,
            DEVICE_CONFIG_KEEP_ALIVE,
            deviceConfig.keepAlive.second,
            false,
            g_parseResult);
    }
    if (jsonObject.find(DEVICE_CONFIG_REMOVABLE) != jsonObjectEnd) {
        deviceConfig.removable.first = true;
        BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
            jsonObjectEnd,
            DEVICE_CONFIG_REMOVABLE,
            deviceConfig.removable.second,
            false,
            g_parseResult);
    }
    if (jsonObject.find(DEVICE_CONFIG_SINGLETON) != jsonObjectEnd) {
        deviceConfig.singleton.first = true;
        BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
            jsonObjectEnd,
            DEVICE_CONFIG_SINGLETON,
            deviceConfig.singleton.second,
            false,
            g_parseResult);
    }
    if (jsonObject.find(DEVICE_CONFIG_USER_DATA_CLEARABLE) != jsonObjectEnd) {
        deviceConfig.userDataClearable.first = true;
        BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
            jsonObjectEnd,
            DEVICE_CONFIG_USER_DATA_CLEARABLE,
            deviceConfig.userDataClearable.second,
            false,
            g_parseResult);
    }
    if (jsonObject.find(DEVICE_CONFIG_ACCESSIBLE) != jsonObjectEnd) {
        deviceConfig.accessible.first = true;
        BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
            jsonObjectEnd,
            DEVICE_CONFIG_ACCESSIBLE,
            deviceConfig.accessible.second,
            false,
            g_parseResult);
    }
}

void from_json(const nlohmann::json &jsonObject, MultiAppMode &multiAppMode)
{
    // these are required fields.
    const auto &jsonObjectEnd = jsonObject.end();
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MULTI_APP_MODE_TYPE,
        multiAppMode.multiAppModeType,
        false,
        g_parseResult);
    GetValueIfFindKey<int32_t>(jsonObject,
        jsonObjectEnd,
        MULTI_APP_MODE_MAX_ADDITIONAL_NUMBER,
        multiAppMode.maxCount,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
}

void from_json(const nlohmann::json &jsonObject, App &app)
{
    APP_LOGD("read app tag from module.json");
    const auto &jsonObjectEnd = jsonObject.end();
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_BUNDLE_NAME,
        app.bundleName,
        true,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        ICON,
        app.icon,
        true,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        LABEL,
        app.label,
        true,
        g_parseResult);
    GetValueIfFindKey<int32_t>(jsonObject,
        jsonObjectEnd,
        APP_VERSION_CODE,
        app.versionCode,
        JsonType::NUMBER,
        true,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_VERSION_NAME,
        app.versionName,
        true,
        g_parseResult);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        APP_MIN_API_VERSION,
        app.minAPIVersion,
        JsonType::NUMBER,
        true,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<int32_t>(jsonObject,
        jsonObjectEnd,
        APP_TARGET_API_VERSION,
        app.targetAPIVersion,
        JsonType::NUMBER,
        true,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<int32_t>(jsonObject,
        jsonObjectEnd,
        APP_TARGET_MINOR_API_VERSION,
        app.targetMinorApiVersion,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<int32_t>(jsonObject,
        jsonObjectEnd,
        APP_TARGET_PATCH_API_VERSION,
        app.targetPatchApiVersion,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_DEBUG,
        app.debug,
        false,
        g_parseResult);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        ICON_ID,
        app.iconId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        LABEL_ID,
        app.labelId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        DESCRIPTION,
        app.description,
        false,
        g_parseResult);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        DESCRIPTION_ID,
        app.descriptionId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_VENDOR,
        app.vendor,
        false,
        g_parseResult);
    GetValueIfFindKey<int32_t>(jsonObject,
        jsonObjectEnd,
        APP_MIN_COMPATIBLE_VERSION_CODE,
        app.minCompatibleVersionCode,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_API_RELEASETYPE,
        app.apiReleaseType,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_KEEP_ALIVE,
        app.keepAlive,
        false,
        g_parseResult);
    GetValueIfFindKey<std::vector<std::string>>(jsonObject,
        jsonObjectEnd,
        APP_TARGETBUNDLELIST,
        app.targetBundleList,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::STRING);
    if (jsonObject.find(APP_REMOVABLE) != jsonObject.end()) {
        app.removable.first = true;
        BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
            jsonObjectEnd,
            APP_REMOVABLE,
            app.removable.second,
            false,
            g_parseResult);
    }
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_SINGLETON,
        app.singleton,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_USER_DATA_CLEARABLE,
        app.userDataClearable,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_ACCESSIBLE,
        app.accessible,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_ASAN_ENABLED,
        app.asanEnabled,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        BUNDLE_TYPE,
        app.bundleType,
        false,
        g_parseResult);
    if (jsonObject.find(APP_PHONE) != jsonObjectEnd) {
        DeviceConfig deviceConfig;
        GetValueIfFindKey<DeviceConfig>(jsonObject,
            jsonObjectEnd,
            APP_PHONE,
            deviceConfig,
            JsonType::OBJECT,
            false,
            g_parseResult,
            ArrayType::NOT_ARRAY);
        app.deviceConfigs[APP_PHONE] = deviceConfig;
    }
    if (jsonObject.find(APP_TABLET) != jsonObjectEnd) {
        DeviceConfig deviceConfig;
        GetValueIfFindKey<DeviceConfig>(jsonObject,
            jsonObjectEnd,
            APP_TABLET,
            deviceConfig,
            JsonType::OBJECT,
            false,
            g_parseResult,
            ArrayType::NOT_ARRAY);
        app.deviceConfigs[APP_TABLET] = deviceConfig;
    }
    if (jsonObject.find(APP_TV) != jsonObjectEnd) {
        DeviceConfig deviceConfig;
        GetValueIfFindKey<DeviceConfig>(jsonObject,
            jsonObjectEnd,
            APP_TV,
            deviceConfig,
            JsonType::OBJECT,
            false,
            g_parseResult,
            ArrayType::NOT_ARRAY);
        app.deviceConfigs[APP_TV] = deviceConfig;
    }
    if (jsonObject.find(APP_WEARABLE) != jsonObjectEnd) {
        DeviceConfig deviceConfig;
        GetValueIfFindKey<DeviceConfig>(jsonObject,
            jsonObjectEnd,
            APP_WEARABLE,
            deviceConfig,
            JsonType::OBJECT,
            false,
            g_parseResult,
            ArrayType::NOT_ARRAY);
        app.deviceConfigs[APP_WEARABLE] = deviceConfig;
    }
    if (jsonObject.find(APP_LITE_WEARABLE) != jsonObjectEnd) {
        DeviceConfig deviceConfig;
        GetValueIfFindKey<DeviceConfig>(jsonObject,
            jsonObjectEnd,
            APP_LITE_WEARABLE,
            deviceConfig,
            JsonType::OBJECT,
            false,
            g_parseResult,
            ArrayType::NOT_ARRAY);
        app.deviceConfigs[APP_LITE_WEARABLE] = deviceConfig;
    }
    if (jsonObject.find(APP_CAR) != jsonObjectEnd) {
        DeviceConfig deviceConfig;
        GetValueIfFindKey<DeviceConfig>(jsonObject,
            jsonObjectEnd,
            APP_CAR,
            deviceConfig,
            JsonType::OBJECT,
            false,
            g_parseResult,
            ArrayType::NOT_ARRAY);
        app.deviceConfigs[APP_CAR] = deviceConfig;
    }
    if (jsonObject.find(APP_SMART_VISION) != jsonObjectEnd) {
        DeviceConfig deviceConfig;
        GetValueIfFindKey<DeviceConfig>(jsonObject,
            jsonObjectEnd,
            APP_SMART_VISION,
            deviceConfig,
            JsonType::OBJECT,
            false,
            g_parseResult,
            ArrayType::NOT_ARRAY);
        app.deviceConfigs[APP_SMART_VISION] = deviceConfig;
    }
    if (jsonObject.find(APP_ROUTER) != jsonObjectEnd) {
        DeviceConfig deviceConfig;
        GetValueIfFindKey<DeviceConfig>(jsonObject,
            jsonObjectEnd,
            APP_ROUTER,
            deviceConfig,
            JsonType::OBJECT,
            false,
            g_parseResult,
            ArrayType::NOT_ARRAY);
        app.deviceConfigs[APP_ROUTER] = deviceConfig;
    }
    if (jsonObject.find(APP_TWO_IN_ONE) != jsonObjectEnd) {
        DeviceConfig deviceConfig;
        GetValueIfFindKey<DeviceConfig>(jsonObject,
            jsonObjectEnd,
            APP_TWO_IN_ONE,
            deviceConfig,
            JsonType::OBJECT,
            false,
            g_parseResult,
            ArrayType::NOT_ARRAY);
        app.deviceConfigs[APP_TWO_IN_ONE] = deviceConfig;
    }
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_MULTI_PROJECTS,
        app.multiProjects,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_TARGET_BUNDLE_NAME,
        app.targetBundle,
        false,
        g_parseResult);
    GetValueIfFindKey<int32_t>(jsonObject,
        jsonObjectEnd,
        APP_TARGET_PRIORITY,
        app.targetPriority,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        COMPILE_SDK_VERSION,
        app.compileSdkVersion,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        COMPILE_SDK_TYPE,
        app.compileSdkType,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_GWP_ASAN_ENABLED,
        app.gwpAsanEnabled,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_TSAN_ENABLED,
        app.tsanEnabled,
        false,
        g_parseResult);
    GetValueIfFindKey<std::vector<ApplicationEnvironment>>(jsonObject,
        jsonObjectEnd,
        MODULE_APP_ENVIRONMENTS,
        app.appEnvironments,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    GetValueIfFindKey<MultiAppMode>(jsonObject,
        jsonObjectEnd,
        APP_MULTI_APP_MODE,
        app.multiAppMode,
        JsonType::OBJECT,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<int32_t>(jsonObject,
        jsonObjectEnd,
        APP_MAX_CHILD_PROCESS,
        app.maxChildProcess,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_HWASAN_ENABLED,
        app.hwasanEnabled,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_CONFIGURATION,
        app.configuration,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_CLOUD_FILE_SYNC_ENABLED,
        app.cloudFileSyncEnabled,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_CLOUD_STRUCTURED_DATA_SYNC_ENABLED,
        app.cloudStructuredDataSyncEnabled,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_UBSAN_ENABLED,
        app.ubsanEnabled,
        false,
        g_parseResult);
    GetValueIfFindKey<std::vector<std::string>>(jsonObject,
        jsonObjectEnd,
        APP_ASSET_ACCESS_GROUPS,
        app.assetAccessGroups,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::STRING);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        START_MODE,
        app.startMode,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        APP_PRELOAD_PHASE,
        app.appPreloadPhase,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        Constants::BUILD_VERSION,
        app.buildVersion,
        false,
        g_parseResult);
}

void from_json(const nlohmann::json &jsonObject, Module &module)
{
    APP_LOGD("read module tag from module.json");
    const auto &jsonObjectEnd = jsonObject.end();
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_NAME,
        module.name,
        true,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_TYPE,
        module.type,
        true,
        g_parseResult);
    GetValueIfFindKey<std::vector<std::string>>(jsonObject,
        jsonObjectEnd,
        MODULE_DEVICE_TYPES,
        module.deviceTypes,
        JsonType::ARRAY,
        true,
        g_parseResult,
        ArrayType::STRING);
    GetMapValueIfFindKey<std::map<std::string, std::vector<std::string>>>(jsonObject,
        jsonObjectEnd,
        MODULE_REQUIRED_DEVICE_FEATURES,
        module.requiredDeviceFeatures,
        false,
        g_parseResult,
        JsonType::ARRAY,
        ArrayType::STRING);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_DELIVERY_WITH_INSTALL,
        module.deliveryWithInstall,
        true,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_PAGES,
        module.pages,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_APP_SYSTEM_THEME,
        module.systemTheme,
        false,
        g_parseResult);
    // both srcEntry and srcEntrance can be configured, but srcEntry has higher priority
    if (jsonObject.find(SRC_ENTRY) != jsonObject.end()) {
        BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
            jsonObjectEnd,
            SRC_ENTRY,
            module.srcEntrance,
            false,
            g_parseResult);
    } else {
        BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
            jsonObjectEnd,
            SRC_ENTRANCE,
            module.srcEntrance,
            false,
            g_parseResult);
    }
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_ABILITY_SRC_ENTRY_DELEGATOR,
        module.abilitySrcEntryDelegator,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_ABILITY_STAGE_SRC_ENTRY_DELEGATOR,
        module.abilityStageSrcEntryDelegator,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        DESCRIPTION,
        module.description,
        false,
        g_parseResult);
    GetValueIfFindKey<uint32_t>(jsonObject,
        jsonObjectEnd,
        DESCRIPTION_ID,
        module.descriptionId,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_PROCESS,
        module.process,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_MAIN_ELEMENT,
        module.mainElement,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_INSTALLATION_FREE,
        module.installationFree,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_VIRTUAL_MACHINE,
        module.virtualMachine,
        false,
        g_parseResult);
    GetValueIfFindKey<std::vector<Metadata>>(jsonObject,
        jsonObjectEnd,
        META_DATA,
        module.metadata,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    GetValueIfFindKey<std::vector<HnpPackage>>(jsonObject,
        jsonObjectEnd,
        MODULE_HNP_PACKAGE,
        module.hnpPackages,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    GetValueIfFindKey<std::vector<Ability>>(jsonObject,
        jsonObjectEnd,
        MODULE_ABILITIES,
        module.abilities,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    GetValueIfFindKey<std::vector<Extension>>(jsonObject,
        jsonObjectEnd,
        MODULE_EXTENSION_ABILITIES,
        module.extensionAbilities,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    GetValueIfFindKey<std::vector<RequestPermission>>(jsonObject,
        jsonObjectEnd,
        MODULE_REQUEST_PERMISSIONS,
        module.requestPermissions,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    GetValueIfFindKey<std::vector<DefinePermission>>(jsonObject,
        jsonObjectEnd,
        MODULE_DEFINE_PERMISSIONS,
        module.definePermissions,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    GetValueIfFindKey<std::vector<Dependency>>(jsonObject,
        jsonObjectEnd,
        MODULE_DEPENDENCIES,
        module.dependencies,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_COMPILE_MODE,
        module.compileMode,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_IS_LIB_ISOLATED,
        module.isLibIsolated,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_TARGET_MODULE_NAME,
        module.targetModule,
        false,
        g_parseResult);
    GetValueIfFindKey<int32_t>(jsonObject,
        jsonObjectEnd,
        MODULE_TARGET_PRIORITY,
        module.targetPriority,
        JsonType::NUMBER,
        false,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<std::vector<ProxyData>>(jsonObject,
        jsonObjectEnd,
        MODULE_PROXY_DATAS,
        module.proxyDatas,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    GetValueIfFindKey<std::vector<ProxyData>>(jsonObject,
        jsonObjectEnd,
        MODULE_PROXY_DATA,
        module.proxyData,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_BUILD_HASH,
        module.buildHash,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_ISOLATION_MODE,
        module.isolationMode,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_COMPRESS_NATIVE_LIBS,
        module.compressNativeLibs,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_EXTRACT_NATIVE_LIBS,
        module.extractNativeLibs,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_FILE_CONTEXT_MENU,
        module.fileContextMenu,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_EASY_GO,
        module.easyGo,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_SHARE_FILES,
        module.shareFiles,
        false,
        g_parseResult);
    GetValueIfFindKey<std::vector<std::string>>(jsonObject,
        jsonObjectEnd,
        MODULE_QUERY_SCHEMES,
        module.querySchemes,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::STRING);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_ROUTER_MAP,
        module.routerMap,
        false,
        g_parseResult);
    GetValueIfFindKey<std::vector<AppEnvironment>>(jsonObject,
        jsonObjectEnd,
        MODULE_APP_ENVIRONMENTS,
        module.appEnvironments,
        JsonType::ARRAY,
        false,
        g_parseResult,
        ArrayType::OBJECT);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_PACKAGE_NAME,
        module.packageName,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_CROS_APP_SHARED_CONFIG,
        module.crossAppSharedConfig,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_APP_STARTUP,
        module.appStartup,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_FORM_EXTENSION_MODULE,
        module.formExtensionModule,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_FORM_WIDGET_MODULE,
        module.formWidgetModule,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_HAS_INTENT,
        module.hasInsightIntent,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        Constants::MODULE_ARKTS_MODE,
        module.moduleArkTSMode,
        false,
        g_parseResult);
    BMSJsonUtil::GetStrValueIfFindKey(jsonObject,
        jsonObjectEnd,
        Constants::ARKTS_MODE,
        module.arkTSMode,
        false,
        g_parseResult);
    BMSJsonUtil::GetBoolValueIfFindKey(jsonObject,
        jsonObjectEnd,
        MODULE_DEDUPLICATE_HAR,
        module.deduplicateHar,
        false,
        g_parseResult);
}

void from_json(const nlohmann::json &jsonObject, ModuleJson &moduleJson)
{
    const auto &jsonObjectEnd = jsonObject.end();
    GetValueIfFindKey<App>(jsonObject,
        jsonObjectEnd,
        APP,
        moduleJson.app,
        JsonType::OBJECT,
        true,
        g_parseResult,
        ArrayType::NOT_ARRAY);
    GetValueIfFindKey<Module>(jsonObject,
        jsonObjectEnd,
        MODULE,
        moduleJson.module,
        JsonType::OBJECT,
        true,
        g_parseResult,
        ArrayType::NOT_ARRAY);
}
} // namespace Profile

namespace {
struct TransformParam {
    bool isSystemApp = false;
    bool isPreInstallApp = false;
};

void GetMetadata(std::vector<Metadata> &metadata, const std::vector<Profile::Metadata> &profileMetadata)
{
    for (const Profile::Metadata &item : profileMetadata) {
        Metadata tmpMetadata;
        tmpMetadata.valueId = item.valueId;
        tmpMetadata.name = item.name;
        tmpMetadata.value = item.value;
        tmpMetadata.resource = item.resource;
        metadata.emplace_back(tmpMetadata);
    }
}

void GetHnpPackage(std::vector<HnpPackage> &hnpPackage, const std::vector<Profile::HnpPackage> &profileHnpPackage)
{
    for (const Profile::HnpPackage &item : profileHnpPackage) {
        HnpPackage tmpHnpPackage;
        tmpHnpPackage.package = item.package;
        tmpHnpPackage.type = item.type;
        tmpHnpPackage.independentSign = item.independentSign;
        hnpPackage.emplace_back(tmpHnpPackage);
    }
}

bool CheckBundleNameIsValid(const std::string &bundleName)
{
    if (bundleName.empty()) {
        APP_LOGE("bundleName is empty");
        return false;
    }
    if (bundleName.size() < Constants::MIN_BUNDLE_NAME || bundleName.size() > Constants::MAX_BUNDLE_NAME) {
        APP_LOGE("bundleName size too long or too short");
        return false;
    }
    char head = bundleName.at(0);
    if (!isalpha(head)) {
        return false;
    }
    for (const auto &c : bundleName) {
        if (!isalnum(c) && (c != '.') && (c != '_')) {
            return false;
        }
    }
    return true;
}

bool CheckModuleNameIsValid(const std::string &moduleName)
{
    if (moduleName.empty()) {
        APP_LOGE("module name is empty");
        return false;
    }
    if (moduleName.size() > MAX_MODULE_NAME) {
        APP_LOGE("module name size too long");
        return false;
    }
    if (moduleName.find(ServiceConstants::RELATIVE_PATH_NAME) != std::string::npos) {
        return false;
    }
    if (moduleName.find(ServiceConstants::MODULE_NAME_SEPARATOR) != std::string::npos) {
        APP_LOGE("module name should not contain ,");
        return false;
    }
    return true;
}

void UpdateNativeSoAttrs(
    const std::string &cpuAbi,
    const std::string &soRelativePath,
    bool isLibIsolated,
    InnerBundleInfo &innerBundleInfo)
{
    APP_LOGD("cpuAbi %{public}s, soRelativePath : %{public}s, isLibIsolated : %{public}d",
        cpuAbi.c_str(), soRelativePath.c_str(), isLibIsolated);
    innerBundleInfo.SetCpuAbi(cpuAbi);
    if (!innerBundleInfo.IsCompressNativeLibs(innerBundleInfo.GetCurModuleName())) {
        APP_LOGD("UpdateNativeSoAttrs compressNativeLibs is false, no need to decompress so");
        if (!isLibIsolated) {
            innerBundleInfo.SetNativeLibraryPath(soRelativePath);
        }
        if (!soRelativePath.empty()) {
            innerBundleInfo.SetModuleNativeLibraryPath(ServiceConstants::LIBS + cpuAbi);
            innerBundleInfo.SetSharedModuleNativeLibraryPath(ServiceConstants::LIBS + cpuAbi);
        }
        innerBundleInfo.SetModuleCpuAbi(cpuAbi);
        return;
    }
    if (!isLibIsolated) {
        innerBundleInfo.SetNativeLibraryPath(soRelativePath);
        return;
    }

    innerBundleInfo.SetModuleNativeLibraryPath(
        innerBundleInfo.GetCurModuleName() + ServiceConstants::PATH_SEPARATOR + soRelativePath);
    innerBundleInfo.SetSharedModuleNativeLibraryPath(
        innerBundleInfo.GetCurModuleName() + ServiceConstants::PATH_SEPARATOR + soRelativePath);
    innerBundleInfo.SetModuleCpuAbi(cpuAbi);
}

bool ParserNativeSo(
    const Profile::ModuleJson &moduleJson,
    const BundleExtractor &bundleExtractor,
    InnerBundleInfo &innerBundleInfo)
{
    std::string abis = GetAbiList();
    std::vector<std::string> abiList;
    SplitStr(abis, ServiceConstants::ABI_SEPARATOR, abiList, false, false);
    if (abiList.empty()) {
        APP_LOGD("Abi is empty");
        return false;
    }

    bool isDefault =
        std::find(abiList.begin(), abiList.end(), ServiceConstants::ABI_DEFAULT) != abiList.end();
    bool isSystemLib64Exist = BundleUtil::IsExistDir(ServiceConstants::SYSTEM_LIB64);
    APP_LOGD("abi list : %{public}s, isDefault : %{public}d", abis.c_str(), isDefault);
    std::string cpuAbi;
    std::string soRelativePath;
    bool soExist = bundleExtractor.IsDirExist(ServiceConstants::LIBS);
    if (!soExist) {
        APP_LOGD("so not exist");
        if (isDefault) {
            cpuAbi = isSystemLib64Exist ? ServiceConstants::ARM64_V8A : ServiceConstants::ARM_EABI_V7A;
            UpdateNativeSoAttrs(cpuAbi, soRelativePath, false, innerBundleInfo);
            return true;
        }

        for (const auto &abi : abiList) {
            if (ServiceConstants::ABI_MAP.find(abi) != ServiceConstants::ABI_MAP.end()) {
                cpuAbi = abi;
                UpdateNativeSoAttrs(cpuAbi, soRelativePath, false, innerBundleInfo);
                return true;
            }
        }

        return false;
    }

    APP_LOGD("so exist");
    bool isLibIsolated = moduleJson.module.isLibIsolated;
    if (isDefault) {
        if (isSystemLib64Exist) {
            if (bundleExtractor.IsDirExist(std::string(ServiceConstants::LIBS) + ServiceConstants::ARM64_V8A)) {
                cpuAbi = ServiceConstants::ARM64_V8A;
                soRelativePath = ServiceConstants::LIBS + ServiceConstants::ABI_MAP.at(ServiceConstants::ARM64_V8A);
                UpdateNativeSoAttrs(cpuAbi, soRelativePath, isLibIsolated, innerBundleInfo);
                return true;
            }

            return false;
        }

        if (bundleExtractor.IsDirExist(std::string(ServiceConstants::LIBS) + ServiceConstants::ARM_EABI_V7A)) {
            cpuAbi = ServiceConstants::ARM_EABI_V7A;
            soRelativePath = ServiceConstants::LIBS + ServiceConstants::ABI_MAP.at(ServiceConstants::ARM_EABI_V7A);
            UpdateNativeSoAttrs(cpuAbi, soRelativePath, isLibIsolated, innerBundleInfo);
            return true;
        }

        if (bundleExtractor.IsDirExist(std::string(ServiceConstants::LIBS) + ServiceConstants::ARM_EABI)) {
            cpuAbi = ServiceConstants::ARM_EABI;
            soRelativePath = ServiceConstants::LIBS + ServiceConstants::ABI_MAP.at(ServiceConstants::ARM_EABI);
            UpdateNativeSoAttrs(cpuAbi, soRelativePath, isLibIsolated, innerBundleInfo);
            return true;
        }

        return false;
    }

    for (const auto &abi : abiList) {
        std::string libsPath;
        libsPath.append(ServiceConstants::LIBS).append(abi).append(ServiceConstants::PATH_SEPARATOR);
        if (ServiceConstants::ABI_MAP.find(abi) != ServiceConstants::ABI_MAP.end() &&
            bundleExtractor.IsDirExist(libsPath)) {
            cpuAbi = abi;
            soRelativePath = ServiceConstants::LIBS + ServiceConstants::ABI_MAP.at(abi);
            UpdateNativeSoAttrs(cpuAbi, soRelativePath, isLibIsolated, innerBundleInfo);
            return true;
        }
    }

    return false;
}

bool ParserAtomicModuleResizeableConfig(const nlohmann::json &moduleAtomicObj, const std::string &moduleName,
    InnerBundleInfo &innerBundleInfo)
{
    bool resizeable = false;
    if (!moduleAtomicObj.is_object()) {
        APP_LOGE("moduleAtomicObj is not object");
        return false;
    }
    if (moduleAtomicObj.contains(Profile::MODULE_ATOMIC_SERVICE_RESIZEABLE)) {
        nlohmann::json resizeableObj = moduleAtomicObj.at(Profile::MODULE_ATOMIC_SERVICE_RESIZEABLE);
        if (!resizeableObj.is_boolean()) {
            APP_LOGE("resizeable config in module.json is not boolean");
            return false;
        }
        resizeable = resizeableObj;
    }
    innerBundleInfo.SetInnerModuleAtomicResizeable(moduleName, resizeable);
    return true;
}

bool ParserAtomicModuleConfig(const nlohmann::json &jsonObject, InnerBundleInfo &innerBundleInfo)
{
    nlohmann::json moduleJson = jsonObject.at(Profile::MODULE);
    std::vector<std::string> preloads;
    std::string moduleName = moduleJson.at(Profile::MODULE_NAME);
    if (moduleJson.contains(Profile::ATOMIC_SERVICE)) {
        nlohmann::json moduleAtomicObj = moduleJson.at(Profile::ATOMIC_SERVICE);
        if (!ParserAtomicModuleResizeableConfig(moduleAtomicObj, moduleName, innerBundleInfo)) {
            APP_LOGE("parser resizeable failed");
            return false;
        }
        if (moduleAtomicObj.contains(Profile::MODULE_ATOMIC_SERVICE_PRELOADS)) {
            nlohmann::json preloadObj = moduleAtomicObj.at(Profile::MODULE_ATOMIC_SERVICE_PRELOADS);
            if (preloadObj.empty()) {
                APP_LOGD("preloadObj is empty");
                return true;
            }
            if (preloadObj.size() > Constants::MAX_JSON_ARRAY_LENGTH) {
                APP_LOGE("preloads config in module.json is oversize");
                return false;
            }
            for (const auto &preload : preloadObj) {
                if (preload.contains(Profile::PRELOADS_MODULE_NAME)) {
                    std::string preloadName = preload.at(Profile::PRELOADS_MODULE_NAME);
                    preloads.emplace_back(preloadName);
                } else {
                    APP_LOGE("preloads must have moduleName");
                    return false;
                }
            }
        }
    }
    innerBundleInfo.SetInnerModuleAtomicPreload(moduleName, preloads);
    return true;
}

bool ParserAtomicConfig(const nlohmann::json &jsonObject, InnerBundleInfo &innerBundleInfo)
{
    if (!jsonObject.contains(Profile::MODULE) || !jsonObject.contains(Profile::APP)) {
        APP_LOGE("ParserAtomicConfig failed due to bad module.json");
        return false;
    }
    nlohmann::json appJson = jsonObject.at(Profile::APP);
    nlohmann::json moduleJson = jsonObject.at(Profile::MODULE);
    if (!moduleJson.is_object() || !appJson.is_object()) {
        APP_LOGE("module.json file lacks of invalid module or app properties");
        return false;
    }
    BundleType bundleType = BundleType::APP;
    if (appJson.contains(Profile::BUNDLE_TYPE)) {
        if (appJson.at(Profile::BUNDLE_TYPE) == Profile::BUNDLE_TYPE_ATOMIC_SERVICE) {
            bundleType = BundleType::ATOMIC_SERVICE;
        } else if (appJson.at(Profile::BUNDLE_TYPE) == Profile::BUNDLE_TYPE_SHARED) {
            bundleType = BundleType::SHARED;
        } else if (appJson.at(Profile::BUNDLE_TYPE) == Profile::BUNDLE_TYPE_APP_SERVICE_FWK) {
            bundleType = BundleType::APP_SERVICE_FWK;
        } else if (appJson.at(Profile::BUNDLE_TYPE) == Profile::BUNDLE_TYPE_PLUGIN) {
            bundleType = BundleType::APP_PLUGIN;
        }
    }

    innerBundleInfo.SetApplicationBundleType(bundleType);
    if (!ParserAtomicModuleConfig(jsonObject, innerBundleInfo)) {
        APP_LOGE("parse module atomicService failed");
        return false;
    }
    return true;
}

bool ParserArkNativeFilePath(
    const Profile::ModuleJson &moduleJson,
    const BundleExtractor &bundleExtractor,
    InnerBundleInfo &innerBundleInfo)
{
    std::string abis = GetAbiList();
    std::vector<std::string> abiList;
    SplitStr(abis, ServiceConstants::ABI_SEPARATOR, abiList, false, false);
    if (abiList.empty()) {
        APP_LOGD("Abi is empty");
        return false;
    }

    bool isDefault =
        std::find(abiList.begin(), abiList.end(), ServiceConstants::ABI_DEFAULT) != abiList.end();
    bool isSystemLib64Exist = BundleUtil::IsExistDir(ServiceConstants::SYSTEM_LIB64);
    APP_LOGD("abi list : %{public}s, isDefault : %{public}d", abis.c_str(), isDefault);
    bool anExist = bundleExtractor.IsDirExist(ServiceConstants::AN);
    if (!anExist) {
        APP_LOGD("an not exist");
        return true;
    }

    APP_LOGD("an exist");
    if (isDefault) {
        if (isSystemLib64Exist) {
            if (bundleExtractor.IsDirExist(std::string(ServiceConstants::AN) + ServiceConstants::ARM64_V8A)) {
                innerBundleInfo.SetArkNativeFileAbi(ServiceConstants::ARM64_V8A);
                return true;
            }

            return false;
        }

        if (bundleExtractor.IsDirExist(std::string(ServiceConstants::AN) + ServiceConstants::ARM_EABI_V7A)) {
            innerBundleInfo.SetArkNativeFileAbi(ServiceConstants::ARM_EABI_V7A);
            return true;
        }

        if (bundleExtractor.IsDirExist(std::string(ServiceConstants::AN) + ServiceConstants::ARM_EABI)) {
            innerBundleInfo.SetArkNativeFileAbi(ServiceConstants::ARM_EABI);
            return true;
        }

        return false;
    }

    for (const auto &abi : abiList) {
        std::string libsPath;
        libsPath.append(ServiceConstants::AN).append(abi).append(ServiceConstants::PATH_SEPARATOR);
        if (ServiceConstants::ABI_MAP.find(abi) != ServiceConstants::ABI_MAP.end() &&
            bundleExtractor.IsDirExist(libsPath)) {
            innerBundleInfo.SetArkNativeFileAbi(abi);
            return true;
        }
    }

    return false;
}

MultiAppModeType ToMultiAppModeType(const std::string &type)
{
    auto iter = Profile::MULTI_APP_MODE_MAP.find(type);
    if (iter != Profile::MULTI_APP_MODE_MAP.end()) {
        return iter->second;
    }
    return MultiAppModeType::UNSPECIFIED;
}

AppPreloadPhase ToAppPreloadPhase(const std::string &type)
{
    auto iter = Profile::APP_PRELOAD_PHASE_MAP.find(type);
    if (iter != Profile::APP_PRELOAD_PHASE_MAP.end()) {
        return iter->second;
    }
    return AppPreloadPhase::DEFAULT;
}

void ToInnerProfileConfiguration(
    const BundleExtractor &bundleExtractor,
    const std::string &configuration,
    std::string &result)
{
    constexpr const char* PROFILE_PATH = "resources/base/profile/";
    constexpr const char* PROFILE_PREFIX = "$profile:";
    constexpr const char* JSON_SUFFIX = ".json";
    auto pos = configuration.find(PROFILE_PREFIX);
    if (pos == std::string::npos) {
        APP_LOGE("invalid profile configuration");
        return;
    }
    std::string profileConfiguration = configuration.substr(pos + strlen(PROFILE_PREFIX));
    std::string profilePath = PROFILE_PATH + profileConfiguration + JSON_SUFFIX;

    if (!bundleExtractor.HasEntry(profilePath)) {
        APP_LOGI("profile not exist");
        return;
    }
    std::stringstream profileStream;
    if (!bundleExtractor.ExtractByName(profilePath, profileStream)) {
        APP_LOGE("extract profile failed");
        return;
    }
    result = profileStream.str();
}

void ToAbilityStartWindow(
    const BundleExtractor &bundleExtractor,
    const std::string &startWindow,
    StartWindowResource &startWindowResource)
{
    auto pos = startWindow.find(ServiceConstants::PROFILE_PREFIX);
    if (pos == std::string::npos) {
        APP_LOGE("invalid profile configuration");
        return;
    }
    std::string startWindowName = startWindow.substr(pos + strlen(ServiceConstants::PROFILE_PREFIX));
    std::string profilePath = ServiceConstants::PROFILE_PATH + startWindowName + ServiceConstants::JSON_SUFFIX;
    if (!bundleExtractor.HasEntry(profilePath)) {
        APP_LOGI("profile not exist");
        return;
    }
    std::stringstream profileStream;
    if (!bundleExtractor.ExtractByName(profilePath, profileStream)) {
        APP_LOGE("extract profile failed");
        return;
    }
    nlohmann::json profileJson = nlohmann::json::parse(profileStream.str(), nullptr, false);
    if (profileJson.is_discarded()) {
        APP_LOGE("bad profile file");
        return;
    }
    startWindowResource.startWindowAppIconId = BundleUtil::ExtractNumberFromString(
        profileJson, Profile::START_WINDOW_APP_ICON);
    startWindowResource.startWindowIllustrationId = BundleUtil::ExtractNumberFromString(
        profileJson, Profile::START_WINDOW_ILLUSTRATION);
    startWindowResource.startWindowBrandingImageId = BundleUtil::ExtractNumberFromString(
        profileJson, Profile::START_WINDOW_BRANDING_IMAGE);
    startWindowResource.startWindowBackgroundColorId = BundleUtil::ExtractNumberFromString(
        profileJson, Profile::START_WINDOW_BACKGROUND_COLOR);
    startWindowResource.startWindowBackgroundImageId = BundleUtil::ExtractNumberFromString(
        profileJson, Profile::START_WINDOW_BACKGROUND_IMAGE);
    startWindowResource.startWindowBackgroundImageFit = BundleUtil::ExtractStringFromJson(
        profileJson, Profile::START_WINDOW_BACKGROUND_IMAGE_FIT);
}

bool ToApplicationInfo(
    const Profile::ModuleJson &moduleJson,
    const BundleExtractor &bundleExtractor,
    const TransformParam &transformParam,
    ApplicationInfo &applicationInfo)
{
    APP_LOGD("transform ModuleJson to ApplicationInfo");
    auto app = moduleJson.app;
    applicationInfo.name = app.bundleName;
    applicationInfo.bundleName = app.bundleName;

    applicationInfo.versionCode = static_cast<uint32_t>(app.versionCode);
    applicationInfo.versionName = app.versionName;
    if (app.minCompatibleVersionCode != -1) {
        applicationInfo.minCompatibleVersionCode = app.minCompatibleVersionCode;
    } else {
        applicationInfo.minCompatibleVersionCode = static_cast<int32_t>(applicationInfo.versionCode);
    }

    applicationInfo.apiCompatibleVersion = app.minAPIVersion;
    applicationInfo.apiTargetVersion = app.targetAPIVersion;
    applicationInfo.targetMinorApiVersion = app.targetMinorApiVersion;
    applicationInfo.targetPatchApiVersion = app.targetPatchApiVersion;

    applicationInfo.iconPath = app.icon;
    applicationInfo.iconId = app.iconId;
    applicationInfo.label = app.label;
    applicationInfo.labelId = app.labelId;
    applicationInfo.description = app.description;
    applicationInfo.descriptionId = app.descriptionId;
    applicationInfo.iconResource =
        BundleUtil::GetResource(app.bundleName, moduleJson.module.name, app.iconId);
    applicationInfo.labelResource =
        BundleUtil::GetResource(app.bundleName, moduleJson.module.name, app.labelId);
    applicationInfo.descriptionResource =
        BundleUtil::GetResource(app.bundleName, moduleJson.module.name, app.descriptionId);
    applicationInfo.targetBundleList = app.targetBundleList;

    if (transformParam.isSystemApp && transformParam.isPreInstallApp) {
        applicationInfo.keepAlive = app.keepAlive;
        applicationInfo.singleton = app.singleton;
        applicationInfo.userDataClearable = app.userDataClearable;
        if (app.removable.first) {
            applicationInfo.removable = app.removable.second;
        } else {
            applicationInfo.removable = false;
        }
        applicationInfo.accessible = app.accessible;
    }

    applicationInfo.apiReleaseType = app.apiReleaseType;
    applicationInfo.debug = app.debug;
    applicationInfo.deviceId = ServiceConstants::CURRENT_DEVICE_ID;
    applicationInfo.distributedNotificationEnabled = true;
    applicationInfo.entityType = Profile::APP_ENTITY_TYPE_DEFAULT_VALUE;
    applicationInfo.vendor = app.vendor;
    applicationInfo.asanEnabled = app.asanEnabled;
    if (app.bundleType == Profile::BUNDLE_TYPE_ATOMIC_SERVICE) {
        applicationInfo.bundleType = BundleType::ATOMIC_SERVICE;
    }
    if (app.startMode == Profile::START_MODE_RECENT_TASK) {
        applicationInfo.startMode = StartMode::RECENT_TASK;
    }

    // device adapt
    std::string deviceType = GetDeviceType();
    APP_LOGD("deviceType : %{public}s", deviceType.c_str());
    if (app.deviceConfigs.find(deviceType) != app.deviceConfigs.end()) {
        Profile::DeviceConfig deviceConfig = app.deviceConfigs.at(deviceType);
        if (deviceConfig.minAPIVersion.first) {
            applicationInfo.apiCompatibleVersion = static_cast<uint32_t>(deviceConfig.minAPIVersion.second);
        }
        if (applicationInfo.isSystemApp && transformParam.isPreInstallApp) {
            if (deviceConfig.keepAlive.first) {
                applicationInfo.keepAlive = deviceConfig.keepAlive.second;
            }
            if (deviceConfig.singleton.first) {
                applicationInfo.singleton = deviceConfig.singleton.second;
            }
            if (deviceConfig.userDataClearable.first) {
                applicationInfo.userDataClearable = deviceConfig.userDataClearable.second;
            }
            if (deviceConfig.removable.first) {
                applicationInfo.removable = deviceConfig.removable.second;
            }
            if (deviceConfig.accessible.first) {
                applicationInfo.accessible = deviceConfig.accessible.second;
            }
        }
    }

    applicationInfo.enabled = true;
    applicationInfo.multiProjects = app.multiProjects;
    applicationInfo.process = app.bundleName;
    applicationInfo.targetBundleName = app.targetBundle;
    applicationInfo.targetPriority = app.targetPriority;

    auto iterBundleType = std::find_if(std::begin(Profile::BUNDLE_TYPE_MAP),
        std::end(Profile::BUNDLE_TYPE_MAP),
        [&app](const auto &item) { return item.first == app.bundleType; });
    if (iterBundleType != Profile::BUNDLE_TYPE_MAP.end()) {
        applicationInfo.bundleType = iterBundleType->second;
    }
    applicationInfo.compileSdkVersion = app.compileSdkVersion;
    applicationInfo.compileSdkType = app.compileSdkType;
    applicationInfo.gwpAsanEnabled = app.gwpAsanEnabled;
    applicationInfo.tsanEnabled = app.tsanEnabled;
    applicationInfo.hwasanEnabled = app.hwasanEnabled;
    applicationInfo.ubsanEnabled = app.ubsanEnabled;
    applicationInfo.appEnvironments = app.appEnvironments;
    if (moduleJson.module.type == Profile::MODULE_TYPE_ENTRY) {
        applicationInfo.assetAccessGroups = app.assetAccessGroups;
    }
    if (applicationInfo.bundleType == BundleType::APP &&
        moduleJson.module.type == Profile::MODULE_TYPE_ENTRY) {
        applicationInfo.appPreloadPhase = ToAppPreloadPhase(app.appPreloadPhase);
    }
    // bundleType is app && moduleType is entry or feature
    if (applicationInfo.bundleType == BundleType::APP &&
        (moduleJson.module.type == Profile::MODULE_TYPE_ENTRY ||
        moduleJson.module.type == Profile::MODULE_TYPE_FEATURE)) {
        applicationInfo.multiAppMode.multiAppModeType = ToMultiAppModeType(app.multiAppMode.multiAppModeType);
        applicationInfo.multiAppMode.maxCount = app.multiAppMode.maxCount;
        if (applicationInfo.multiAppMode.multiAppModeType == MultiAppModeType::APP_CLONE) {
            int32_t maxNumber = applicationInfo.multiAppMode.maxCount;
            if (maxNumber <= Constants::INITIAL_APP_INDEX || maxNumber > ServiceConstants::CLONE_APP_INDEX_MAX) {
                return false;
            }
        }
    }
    applicationInfo.maxChildProcess = app.maxChildProcess;
    if (app.configuration != "") {
        ToInnerProfileConfiguration(bundleExtractor, app.configuration, applicationInfo.configuration);
    }
    applicationInfo.cloudFileSyncEnabled = app.cloudFileSyncEnabled;
    applicationInfo.cloudStructuredDataSyncEnabled = app.cloudStructuredDataSyncEnabled;
    return true;
}

bool ToBundleInfo(
    const ApplicationInfo &applicationInfo,
    const InnerModuleInfo &innerModuleInfo,
    const TransformParam &transformParam,
    BundleInfo &bundleInfo)
{
    bundleInfo.name = applicationInfo.bundleName;

    bundleInfo.versionCode = static_cast<uint32_t>(applicationInfo.versionCode);
    bundleInfo.versionName = applicationInfo.versionName;
    bundleInfo.minCompatibleVersionCode = static_cast<uint32_t>(applicationInfo.minCompatibleVersionCode);

    bundleInfo.compatibleVersion = static_cast<uint32_t>(applicationInfo.apiCompatibleVersion);
    bundleInfo.targetVersion = static_cast<uint32_t>(applicationInfo.apiTargetVersion);
    bundleInfo.targetMinorApiVersion = applicationInfo.targetMinorApiVersion;
    bundleInfo.targetPatchApiVersion = applicationInfo.targetPatchApiVersion;

    bundleInfo.isKeepAlive = applicationInfo.keepAlive;
    bundleInfo.singleton = applicationInfo.singleton;
    bundleInfo.isPreInstallApp = transformParam.isPreInstallApp;

    bundleInfo.vendor = applicationInfo.vendor;
    bundleInfo.releaseType = applicationInfo.apiReleaseType;
    bundleInfo.isNativeApp = false;

    if (innerModuleInfo.isEntry) {
        bundleInfo.mainEntry = innerModuleInfo.moduleName;
        bundleInfo.entryModuleName = innerModuleInfo.moduleName;
    }

    return true;
}

uint32_t GetBackgroundModes(const std::vector<std::string> &backgroundModes)
{
    uint32_t backgroundMode = 0;
    size_t len = sizeof(Profile::BACKGROUND_MODES_MAP_KEY) /
            sizeof(Profile::BACKGROUND_MODES_MAP_KEY[0]);
    for (const std::string &item : backgroundModes) {
        for (size_t i = 0; i < len; i++) {
            if (item == Profile::BACKGROUND_MODES_MAP_KEY[i]) {
                backgroundMode |= Profile::BACKGROUND_MODES_MAP_VALUE[i];
                break;
            }
        }
    }
    return backgroundMode;
}

inline CompileMode ConvertCompileMode(const std::string& compileMode)
{
    if (compileMode == Profile::COMPILE_MODE_ES_MODULE) {
        return CompileMode::ES_MODULE;
    } else {
        return CompileMode::JS_BUNDLE;
    }
}

std::set<SupportWindowMode> ConvertToAbilityWindowMode(const std::vector<std::string> &windowModes,
    const std::unordered_map<std::string, SupportWindowMode> &windowMap)
{
    std::set<SupportWindowMode> modes;
    for_each(windowModes.begin(), windowModes.end(),
        [&windowMap, &modes](const auto &mode)->decltype(auto) {
        if (windowMap.find(mode) != windowMap.end()) {
            modes.emplace(windowMap.at(mode));
        }
    });
    if (modes.empty()) {
        modes.insert(SupportWindowMode::FULLSCREEN);
        modes.insert(SupportWindowMode::SPLIT);
        modes.insert(SupportWindowMode::FLOATING);
    }
    return modes;
}

bool ToAbilityInfo(
    const Profile::ModuleJson &moduleJson,
    const Profile::Ability &ability,
    const TransformParam &transformParam,
    InnerAbilityInfo &abilityInfo)
{
    APP_LOGD("transform ModuleJson to AbilityInfo");
    abilityInfo.name = ability.name;
    abilityInfo.srcEntrance = ability.srcEntrance;
    abilityInfo.description = ability.description;
    abilityInfo.descriptionId = ability.descriptionId;
    abilityInfo.iconPath = ability.icon;
    abilityInfo.iconId = ability.iconId;
    abilityInfo.label = ability.label;
    abilityInfo.labelId = ability.labelId;
    abilityInfo.priority = ability.priority;
    abilityInfo.excludeFromMissions = ability.excludeFromMissions;
    abilityInfo.unclearableMission = ability.unclearableMission;
    abilityInfo.excludeFromDock = ability.excludeFromDock;
    abilityInfo.preferMultiWindowOrientation = ability.preferMultiWindowOrientation;
    abilityInfo.recoverable = ability.recoverable;
    abilityInfo.permissions = ability.permissions;
    abilityInfo.visible = ability.visible;
    abilityInfo.continuable = ability.continuable;
    abilityInfo.isolationProcess = ability.isolationProcess;
    abilityInfo.backgroundModes = GetBackgroundModes(ability.backgroundModes);
    GetMetadata(abilityInfo.metadata, ability.metadata);
    abilityInfo.package = moduleJson.module.name;
    abilityInfo.bundleName = moduleJson.app.bundleName;
    abilityInfo.moduleName = moduleJson.module.name;
    abilityInfo.applicationName = moduleJson.app.bundleName;
    auto iterLaunch = std::find_if(std::begin(Profile::LAUNCH_MODE_MAP),
        std::end(Profile::LAUNCH_MODE_MAP),
        [&ability](const auto &item) { return item.first == ability.launchType; });
    if (iterLaunch != Profile::LAUNCH_MODE_MAP.end()) {
        abilityInfo.launchMode = iterLaunch->second;
    }
    abilityInfo.enabled = true;
    abilityInfo.isModuleJson = true;
    abilityInfo.isStageBasedModel = true;
    abilityInfo.type = AbilityType::PAGE;
    for (const std::string &deviceType : moduleJson.module.deviceTypes) {
        abilityInfo.deviceTypes.emplace_back(deviceType);
    }
    abilityInfo.startWindowIcon = ability.startWindowIcon;
    abilityInfo.startWindowIconId = ability.startWindowIconId;
    abilityInfo.startWindowBackground = ability.startWindowBackground;
    abilityInfo.startWindowBackgroundId = ability.startWindowBackgroundId;
    abilityInfo.startWindow = ability.startWindow;
    abilityInfo.startWindowId = ability.startWindowId;
    abilityInfo.removeMissionAfterTerminate = ability.removeMissionAfterTerminate;
    abilityInfo.allowSelfRedirect  = ability.allowSelfRedirect ;
    abilityInfo.compileMode = ConvertCompileMode(moduleJson.module.compileMode);
    size_t len = sizeof(Profile::DISPLAY_ORIENTATION_MAP_KEY) /
            sizeof(Profile::DISPLAY_ORIENTATION_MAP_KEY[0]);
    for (size_t i = 0; i < len; i++) {
        if (ability.orientation == Profile::DISPLAY_ORIENTATION_MAP_KEY[i]) {
            abilityInfo.orientation = Profile::DISPLAY_ORIENTATION_MAP_VALUE[i];
            break;
        }
    }

    auto modesSet = ConvertToAbilityWindowMode(ability.windowModes, Profile::WINDOW_MODE_MAP);
    abilityInfo.windowModes.assign(modesSet.begin(), modesSet.end());

    if (!ability.continueBundleNames.empty()) {
        abilityInfo.continueBundleNames.insert(ability.continueBundleNames.begin(), ability.continueBundleNames.end());
    }

    abilityInfo.maxWindowRatio = ability.maxWindowRatio;
    abilityInfo.minWindowRatio = ability.minWindowRatio;
    abilityInfo.maxWindowWidth = ability.maxWindowWidth;
    abilityInfo.minWindowWidth = ability.minWindowWidth;
    abilityInfo.maxWindowHeight = ability.maxWindowHeight;
    abilityInfo.minWindowHeight = ability.minWindowHeight;
    if (ability.continueType.empty()) {
        abilityInfo.continueType.emplace_back(ability.name);
    } else {
        abilityInfo.continueType = ability.continueType;
    }
    abilityInfo.orientationId = ability.orientationId;
    abilityInfo.process = ability.process;
    abilityInfo.arkTSMode = ability.arkTSMode;
    return true;
}

void ToAbilitySkills(const std::vector<Skill> &skills, InnerAbilityInfo &abilityInfo)
{
    for (const Skill &skill : skills) {
        abilityInfo.skills.push_back(skill);
    }
}

void ToExtensionAbilitySkills(const std::vector<Skill> &skills, InnerExtensionInfo &extensionInfo)
{
    for (const Skill &skill : skills) {
        extensionInfo.skills.push_back(skill);
    }
}

void ToExtensionInfo(
    const Profile::ModuleJson &moduleJson,
    const Profile::Extension &extension,
    const TransformParam &transformParam,
    InnerExtensionInfo &extensionInfo)
{
    APP_LOGD("transform ModuleJson to InnerExtensionInfo");
    extensionInfo.type = ConvertToExtensionAbilityType(extension.type);
    extensionInfo.extensionTypeName = extension.type;
    extensionInfo.name = extension.name;
    extensionInfo.srcEntrance = extension.srcEntrance;
    extensionInfo.icon = extension.icon;
    extensionInfo.iconId = extension.iconId;
    extensionInfo.label = extension.label;
    extensionInfo.labelId = extension.labelId;
    extensionInfo.description = extension.description;
    extensionInfo.descriptionId = extension.descriptionId;
    if (transformParam.isSystemApp && transformParam.isPreInstallApp) {
        extensionInfo.readPermission = extension.readPermission;
        extensionInfo.writePermission = extension.writePermission;
    }
    extensionInfo.priority = extension.priority;
    extensionInfo.uri = extension.uri;
    extensionInfo.permissions = extension.permissions;
    extensionInfo.appIdentifierAllowList = extension.appIdentifierAllowList;
    extensionInfo.visible = extension.visible;
    extensionInfo.isolationProcess = extension.isolationProcess;
    GetMetadata(extensionInfo.metadata, extension.metadata);
    extensionInfo.bundleName = moduleJson.app.bundleName;
    extensionInfo.moduleName = moduleJson.module.name;

    if (extensionInfo.type != ExtensionAbilityType::SERVICE &&
        extensionInfo.type != ExtensionAbilityType::DATASHARE) {
        extensionInfo.process = extensionInfo.bundleName;
        extensionInfo.process.append(":");
        extensionInfo.process.append(extensionInfo.extensionTypeName);
    }

    extensionInfo.compileMode = ConvertCompileMode(moduleJson.module.compileMode);
    extensionInfo.extensionProcessMode = ConvertToExtensionProcessMode(extension.extensionProcessMode);
    for (const std::string &dataGroup : extension.dataGroupIds) {
        extensionInfo.dataGroupIds.emplace_back(dataGroup);
    }
    extensionInfo.customProcess = extension.customProcess;
    extensionInfo.arkTSMode = extension.arkTSMode;
}

bool GetPermissions(
    const Profile::ModuleJson &moduleJson,
    const TransformParam &transformParam,
    InnerModuleInfo &innerModuleInfo)
{
    if (moduleJson.app.bundleName == Profile::SYSTEM_RESOURCES_APP) {
        for (const DefinePermission &definePermission : moduleJson.module.definePermissions) {
            if (definePermission.name.empty()) {
                continue;
            }
            if (Profile::GRANT_MODE_SET.find(definePermission.grantMode) == Profile::GRANT_MODE_SET.end()) {
                continue;
            }
            if (Profile::AVAILABLE_LEVEL_SET.find(definePermission.availableLevel)
                == Profile::AVAILABLE_LEVEL_SET.end()) {
                continue;
            }
            if (!definePermission.availableType.empty() &&
                definePermission.availableType != Profile::DEFINEPERMISSION_AVAILABLE_TYPE_MDM) {
                APP_LOGE("availableType(%{public}s) invalid", definePermission.availableType.c_str());
                return false;
            }
            innerModuleInfo.definePermissions.emplace_back(definePermission);
        }
    }
    for (const RequestPermission &requestPermission : moduleJson.module.requestPermissions) {
        if (requestPermission.name.empty()) {
            continue;
        }
        innerModuleInfo.requestPermissions.emplace_back(requestPermission);
    }
    return true;
}

bool ToInnerModuleInfo(
    const Profile::ModuleJson &moduleJson,
    const TransformParam &transformParam,
    const OverlayMsg &overlayMsg,
    InnerModuleInfo &innerModuleInfo)
{
    APP_LOGD("transform ModuleJson to InnerModuleInfo");
    innerModuleInfo.name = moduleJson.module.name;
    innerModuleInfo.modulePackage = moduleJson.module.name;
    innerModuleInfo.moduleName = moduleJson.module.name;
    innerModuleInfo.description = moduleJson.module.description;
    innerModuleInfo.descriptionId = moduleJson.module.descriptionId;
    GetMetadata(innerModuleInfo.metadata, moduleJson.module.metadata);
    innerModuleInfo.distro.deliveryWithInstall = moduleJson.module.deliveryWithInstall;
    innerModuleInfo.distro.installationFree = moduleJson.module.installationFree;
    innerModuleInfo.distro.moduleName = moduleJson.module.name;
    innerModuleInfo.installationFree = moduleJson.module.installationFree;
    if (Profile::MODULE_TYPE_SET.find(moduleJson.module.type) != Profile::MODULE_TYPE_SET.end()) {
        innerModuleInfo.distro.moduleType = moduleJson.module.type;
        if (moduleJson.module.type == Profile::MODULE_TYPE_ENTRY) {
            innerModuleInfo.isEntry = true;
            GetHnpPackage(innerModuleInfo.hnpPackages, moduleJson.module.hnpPackages);
        } else if (moduleJson.module.hnpPackages.size() > 0) {
            APP_LOGW("Only entry module can have hnpPackages, ignore hnpPackages for module %{public}s",
                moduleJson.module.name.c_str());
        }
    }

    innerModuleInfo.mainAbility = moduleJson.module.mainElement;
    innerModuleInfo.srcEntrance = moduleJson.module.srcEntrance;
    innerModuleInfo.process = moduleJson.module.process;

    for (const std::string &deviceType : moduleJson.module.deviceTypes) {
        innerModuleInfo.deviceTypes.emplace_back(deviceType);
    }
    for (const auto &deviceFeature : moduleJson.module.requiredDeviceFeatures) {
        innerModuleInfo.requiredDeviceFeatures.insert(deviceFeature);
    }

    if (Profile::VIRTUAL_MACHINE_SET.find(moduleJson.module.virtualMachine) != Profile::VIRTUAL_MACHINE_SET.end()) {
        innerModuleInfo.virtualMachine = moduleJson.module.virtualMachine;
    }

    innerModuleInfo.uiSyntax = Profile::MODULE_UI_SYNTAX_DEFAULT_VALUE;
    innerModuleInfo.pages = moduleJson.module.pages;
    innerModuleInfo.systemTheme = moduleJson.module.systemTheme;
    if (!GetPermissions(moduleJson, transformParam, innerModuleInfo)) {
        APP_LOGE("GetPermissions failed");
        return false;
    }
    innerModuleInfo.dependencies = moduleJson.module.dependencies;
    innerModuleInfo.compileMode = moduleJson.module.compileMode;
    innerModuleInfo.isModuleJson = true;
    innerModuleInfo.isStageBasedModel = true;
    innerModuleInfo.isLibIsolated = moduleJson.module.isLibIsolated;
    innerModuleInfo.targetModuleName = moduleJson.module.targetModule;
    if (overlayMsg.type != NON_OVERLAY_TYPE && !overlayMsg.isModulePriorityExisted) {
        innerModuleInfo.targetPriority = ServiceConstants::OVERLAY_MINIMUM_PRIORITY;
    } else {
        innerModuleInfo.targetPriority = moduleJson.module.targetPriority;
    }
    if (moduleJson.module.proxyDatas.empty()) {
        innerModuleInfo.proxyDatas = moduleJson.module.proxyData;
    } else {
        innerModuleInfo.proxyDatas = moduleJson.module.proxyDatas;
    }
    innerModuleInfo.buildHash = moduleJson.module.buildHash;
    innerModuleInfo.isolationMode = moduleJson.module.isolationMode;
    innerModuleInfo.compressNativeLibs = moduleJson.module.compressNativeLibs || moduleJson.module.extractNativeLibs;
    innerModuleInfo.fileContextMenu = moduleJson.module.fileContextMenu;
    innerModuleInfo.easyGo = moduleJson.module.easyGo;
    innerModuleInfo.shareFiles = moduleJson.module.shareFiles;

    if (moduleJson.module.querySchemes.size() > Profile::MAX_QUERYSCHEMES_LENGTH) {
        APP_LOGE("The length of the querySchemes exceeds the limit");
        return false;
    }
    for (const std::string &queryScheme : moduleJson.module.querySchemes) {
        innerModuleInfo.querySchemes.emplace_back(queryScheme);
    }

    innerModuleInfo.routerMap = moduleJson.module.routerMap;
    // abilities and fileContextMenu store in InnerBundleInfo
    innerModuleInfo.appEnvironments = moduleJson.module.appEnvironments;
    innerModuleInfo.packageName = moduleJson.module.packageName;
    innerModuleInfo.crossAppSharedConfig = moduleJson.module.crossAppSharedConfig;
    innerModuleInfo.appStartup = moduleJson.module.appStartup;
    innerModuleInfo.moduleArkTSMode = moduleJson.module.moduleArkTSMode;
    innerModuleInfo.arkTSMode = moduleJson.module.arkTSMode;
    innerModuleInfo.formExtensionModule = moduleJson.module.formExtensionModule;
    innerModuleInfo.formWidgetModule = moduleJson.module.formWidgetModule;
    innerModuleInfo.debug = moduleJson.app.debug;
    innerModuleInfo.abilitySrcEntryDelegator = moduleJson.module.abilitySrcEntryDelegator;
    innerModuleInfo.abilityStageSrcEntryDelegator = moduleJson.module.abilityStageSrcEntryDelegator;
    if (moduleJson.module.hasInsightIntent) {
        BundleUtil::SetBit(InnerModuleInfoBoolFlag::HAS_INTENT, innerModuleInfo.boolSet);
    }
    if (moduleJson.module.deduplicateHar) {
        BundleUtil::SetBit(InnerModuleInfoBoolFlag::HAS_DEDUPLICATE_HAR, innerModuleInfo.boolSet);
    }
    return true;
}

void SetInstallationFree(InnerModuleInfo &innerModuleInfo, BundleType bundleType)
{
    if (bundleType == BundleType::ATOMIC_SERVICE) {
        innerModuleInfo.distro.installationFree = true;
        innerModuleInfo.installationFree = true;
    } else {
        innerModuleInfo.distro.installationFree = false;
        innerModuleInfo.installationFree = false;
    }
}

bool ToInnerBundleInfo(
    const Profile::ModuleJson &moduleJson,
    const BundleExtractor &bundleExtractor,
    const OverlayMsg &overlayMsg,
    InnerBundleInfo &innerBundleInfo)
{
    APP_LOGD("transform ModuleJson to InnerBundleInfo");
    if (!CheckBundleNameIsValid(moduleJson.app.bundleName) || !CheckModuleNameIsValid(moduleJson.module.name)) {
        APP_LOGE("bundle name or module name is invalid");
        return false;
    }

    if (overlayMsg.type != NON_OVERLAY_TYPE && !CheckModuleNameIsValid(moduleJson.module.targetModule)) {
        APP_LOGE("target moduleName is invalid");
    }

    if ((overlayMsg.type == OVERLAY_EXTERNAL_BUNDLE) && !CheckBundleNameIsValid(moduleJson.app.targetBundle)) {
        APP_LOGE("targetBundleName of the overlay hap is invalid");
        return false;
    }

    TransformParam transformParam;
    transformParam.isPreInstallApp = innerBundleInfo.IsPreInstallApp();

    ApplicationInfo applicationInfo;
    applicationInfo.isSystemApp = innerBundleInfo.GetAppType() == Constants::AppType::SYSTEM_APP;
    transformParam.isSystemApp = applicationInfo.isSystemApp;
    applicationInfo.isCompressNativeLibs = moduleJson.module.compressNativeLibs || moduleJson.module.extractNativeLibs;
    if (!ToApplicationInfo(moduleJson, bundleExtractor, transformParam, applicationInfo)) {
        APP_LOGE("To applicationInfo failed");
        return false;
    }

    InnerModuleInfo innerModuleInfo;
    if (!ToInnerModuleInfo(moduleJson, transformParam, overlayMsg, innerModuleInfo)) {
        APP_LOGE("To innerModuleInfo failed");
        return false;
    }
    innerModuleInfo.versionCode = applicationInfo.versionCode;
    innerModuleInfo.asanEnabled = applicationInfo.asanEnabled;
    innerModuleInfo.gwpAsanEnabled = applicationInfo.gwpAsanEnabled;
    innerModuleInfo.tsanEnabled = applicationInfo.tsanEnabled;
    innerModuleInfo.innerModuleInfoFlag = applicationInfo.hwasanEnabled ? innerModuleInfo.innerModuleInfoFlag |
        innerBundleInfo.GetSanitizerFlag(GetInnerModuleInfoFlag::GET_INNER_MODULE_INFO_WITH_HWASANENABLED) :
        innerModuleInfo.innerModuleInfoFlag &
        (~innerBundleInfo.GetSanitizerFlag(GetInnerModuleInfoFlag::GET_INNER_MODULE_INFO_WITH_HWASANENABLED));
    innerModuleInfo.innerModuleInfoFlag = applicationInfo.ubsanEnabled ? innerModuleInfo.innerModuleInfoFlag |
        innerBundleInfo.GetSanitizerFlag(GetInnerModuleInfoFlag::GET_INNER_MODULE_INFO_WITH_UBSANENABLED) :
        innerModuleInfo.innerModuleInfoFlag &
        (~innerBundleInfo.GetSanitizerFlag(GetInnerModuleInfoFlag::GET_INNER_MODULE_INFO_WITH_UBSANENABLED));
    SetInstallationFree(innerModuleInfo, applicationInfo.bundleType);

    BundleInfo bundleInfo;
    bundleInfo.buildVersion = moduleJson.app.buildVersion;
    ToBundleInfo(applicationInfo, innerModuleInfo, transformParam, bundleInfo);

    // handle abilities
    auto entryActionMatcher = [] (const std::string &action) {
        return action == Constants::ACTION_HOME || action == Constants::WANT_ACTION_HOME;
    };
    bool findEntry = false;
    for (const Profile::Ability &ability : moduleJson.module.abilities) {
        InnerAbilityInfo abilityInfo;
        bool isMainElement = false;
        ToAbilityInfo(moduleJson, ability, transformParam, abilityInfo);
        if (innerModuleInfo.mainAbility == abilityInfo.name) {
            innerModuleInfo.icon = abilityInfo.iconPath;
            innerModuleInfo.iconId = abilityInfo.iconId;
            innerModuleInfo.label = abilityInfo.label;
            innerModuleInfo.labelId = abilityInfo.labelId;
            isMainElement = true;
        }
        std::string key;
        key.append(moduleJson.app.bundleName).append(".")
            .append(moduleJson.module.name).append(".").append(abilityInfo.name);
        innerModuleInfo.abilityKeys.emplace_back(key);
        innerModuleInfo.skillKeys.emplace_back(key);
        innerBundleInfo.InsertSkillInfo(key, ability.skills);
        ToAbilitySkills(ability.skills, abilityInfo);
        if (abilityInfo.startWindow != Constants::EMPTY_STRING) {
            ToAbilityStartWindow(bundleExtractor, abilityInfo.startWindow, abilityInfo.startWindowResource);
        }
        innerBundleInfo.InsertAbilitiesInfo(key, abilityInfo);
        if (findEntry && !isMainElement) {
            continue;
        }
        // get entry ability
        for (const auto &skill : ability.skills) {
            bool isEntryAction = std::find_if(skill.actions.begin(), skill.actions.end(),
                entryActionMatcher) != skill.actions.end();
            bool isEntryEntity = std::find(skill.entities.begin(), skill.entities.end(),
                Constants::ENTITY_HOME) != skill.entities.end();
            if (isEntryAction && isEntryEntity) {
                innerModuleInfo.entryAbilityKey = key;
                innerModuleInfo.label = ability.label;
                innerModuleInfo.labelId = ability.labelId;
                // get launcher application and ability
                bool isLauncherEntity = std::find(skill.entities.begin(), skill.entities.end(),
                    ServiceConstants::FLAG_HOME_INTENT_FROM_SYSTEM) != skill.entities.end();
                if (isLauncherEntity && transformParam.isPreInstallApp && transformParam.isSystemApp) {
                    applicationInfo.isLauncherApp = true;
                    abilityInfo.isLauncherAbility = true;
                    APP_LOGI_NOFUNC("startWindowIconId %{public}s_%{public}s_%{public}s_%{public}d",
                        abilityInfo.bundleName.c_str(), abilityInfo.moduleName.c_str(), abilityInfo.name.c_str(),
                        abilityInfo.startWindowIconId);
                }
                findEntry = true;
                break;
            }
        }
    }

    // handle extensionAbilities
    for (const Profile::Extension &extension : moduleJson.module.extensionAbilities) {
        InnerExtensionInfo extensionInfo;
        ToExtensionInfo(moduleJson, extension, transformParam, extensionInfo);

        if (innerModuleInfo.mainAbility == extensionInfo.name) {
            innerModuleInfo.icon = extensionInfo.icon;
            innerModuleInfo.iconId = extensionInfo.iconId;
            innerModuleInfo.label = extensionInfo.label;
            innerModuleInfo.labelId = extensionInfo.labelId;
        }

        if (transformParam.isPreInstallApp && !applicationInfo.isLauncherApp) {
            for (const auto &skill : extension.skills) {
                bool isEntryAction = std::find_if(skill.actions.cbegin(), skill.actions.cend(),
                    entryActionMatcher) != skill.actions.cend();
                bool isEntryEntity = std::find(skill.entities.cbegin(), skill.entities.cend(),
                    Constants::ENTITY_HOME) != skill.entities.cend();
                bool isLauncherEntity = std::find(skill.entities.cbegin(), skill.entities.cend(),
                    ServiceConstants::FLAG_HOME_INTENT_FROM_SYSTEM) != skill.entities.cend();
                if (isEntryAction && isEntryEntity && isLauncherEntity) {
                    applicationInfo.isLauncherApp = true;
                    break;
                }
            }
        }

        std::string key;
        key.append(moduleJson.app.bundleName).append(".")
            .append(moduleJson.module.name).append(".").append(extension.name);
        innerModuleInfo.extensionKeys.emplace_back(key);
        innerModuleInfo.extensionSkillKeys.emplace_back(key);
        innerBundleInfo.InsertExtensionSkillInfo(key, extension.skills);
        ToExtensionAbilitySkills(extension.skills, extensionInfo);
        innerBundleInfo.InsertExtensionInfo(key, extensionInfo);
    }
    if (!findEntry && !transformParam.isPreInstallApp) {
        applicationInfo.needAppDetail = true;
        if (BundleUtil::IsExistDir(ServiceConstants::SYSTEM_LIB64)) {
            applicationInfo.appDetailAbilityLibraryPath = Profile::APP_DETAIL_ABILITY_LIBRARY_PATH_64;
        } else {
            applicationInfo.appDetailAbilityLibraryPath = Profile::APP_DETAIL_ABILITY_LIBRARY_PATH;
        }
        if ((applicationInfo.labelId == 0) && (applicationInfo.label.empty())) {
            applicationInfo.label = applicationInfo.bundleName;
        }
    }
    innerBundleInfo.SetCurrentModulePackage(moduleJson.module.name);
    innerBundleInfo.SetBaseApplicationInfo(applicationInfo);
    innerBundleInfo.SetBaseBundleInfo(bundleInfo);

    // Here also need verify module type is shared.
    if (applicationInfo.bundleType == BundleType::SHARED) {
        innerModuleInfo.bundleType = applicationInfo.bundleType;
        innerModuleInfo.versionCode = applicationInfo.versionCode;
        innerModuleInfo.versionName = applicationInfo.versionName;
        innerBundleInfo.InsertInnerSharedModuleInfo(moduleJson.module.name, innerModuleInfo);
    }

    innerBundleInfo.InsertInnerModuleInfo(moduleJson.module.name, innerModuleInfo);
    innerBundleInfo.SetOverlayType(overlayMsg.type);

    if (overlayMsg.type == OVERLAY_EXTERNAL_BUNDLE && !overlayMsg.isAppPriorityExisted) {
        innerBundleInfo.SetTargetPriority(ServiceConstants::OVERLAY_MINIMUM_PRIORITY);
    } else {
        innerBundleInfo.SetTargetPriority(moduleJson.app.targetPriority);
    }
    int32_t overlayState = overlayMsg.type == OVERLAY_EXTERNAL_BUNDLE ?
        ServiceConstants::DEFAULT_OVERLAY_ENABLE_STATUS :
        ServiceConstants::DEFAULT_OVERLAY_DISABLE_STATUS;
    innerBundleInfo.SetOverlayState(overlayState);
    return true;
}
}  // namespace

OverlayMsg ModuleProfile::ObtainOverlayType(const nlohmann::json &jsonObject) const
{
    APP_LOGD("check if overlay installation");
    OverlayMsg overlayMsg;
#ifdef BUNDLE_FRAMEWORK_OVERLAY_INSTALLATION
    if (!jsonObject.contains(Profile::MODULE) || !jsonObject.contains(Profile::APP)) {
        APP_LOGE("ObtainOverlayType failed due to bad module.json");
        Profile::g_parseResult = ERR_APPEXECFWK_INSTALL_FAILED_PROFILE_PARSE_FAIL;
        return overlayMsg;
    }
    nlohmann::json moduleJson = jsonObject.at(Profile::MODULE);
    nlohmann::json appJson = jsonObject.at(Profile::APP);
    if (!moduleJson.is_object() || !appJson.is_object()) {
        APP_LOGE("module.json file lacks of invalid module or app properties");
        Profile::g_parseResult = ERR_APPEXECFWK_PARSE_PROFILE_PROP_TYPE_ERROR;
        return overlayMsg;
    }

    auto isTargetBundleExisted = appJson.contains(Profile::APP_TARGET_BUNDLE_NAME);
    auto isAppPriorityExisted = appJson.contains(Profile::APP_TARGET_PRIORITY);
    auto isTargetModuleNameExisted = moduleJson.contains(Profile::MODULE_TARGET_MODULE_NAME);
    auto isModulePriorityExisted = moduleJson.contains(Profile::MODULE_TARGET_PRIORITY);
    if (!isTargetBundleExisted && !isAppPriorityExisted && !isTargetModuleNameExisted &&
        !isModulePriorityExisted) {
        APP_LOGD("not overlayed hap");
        return overlayMsg;
    }
    if (!isTargetModuleNameExisted) {
        Profile::g_parseResult = ERR_BUNDLEMANAGER_OVERLAY_INSTALLATION_FAILED_TARGET_MODULE_NAME_MISSED;
        APP_LOGE("overlay hap with invalid configuration file");
        return overlayMsg;
    }
    if (!isTargetBundleExisted && isAppPriorityExisted) {
        Profile::g_parseResult = ERR_BUNDLEMANAGER_OVERLAY_INSTALLATION_FAILED_TARGET_BUNDLE_NAME_MISSED;
        APP_LOGE("overlay hap with invalid configuration file");
        return overlayMsg;
    }

    APP_LOGI("overlay configuration file is about to parse");
    overlayMsg.type = isTargetBundleExisted ? OVERLAY_EXTERNAL_BUNDLE : OVERLAY_INTERNAL_BUNDLE;
    overlayMsg.isAppPriorityExisted = isAppPriorityExisted;
    overlayMsg.isModulePriorityExisted = isModulePriorityExisted;
    return overlayMsg;
#else
    return overlayMsg;
#endif
}

ErrCode ModuleProfile::TransformTo(
    const std::ostringstream &source,
    const BundleExtractor &bundleExtractor,
    InnerBundleInfo &innerBundleInfo) const
{
    APP_LOGD("transform module.json stream to InnerBundleInfo");
    nlohmann::json jsonObject = nlohmann::json::parse(source.str(), nullptr, false);
    if (jsonObject.is_discarded()) {
        APP_LOGE("bad profile");
        return ERR_APPEXECFWK_PARSE_BAD_PROFILE;
    }
    OverlayMsg overlayMsg;
    Profile::ModuleJson moduleJson;
    {
        std::lock_guard<std::mutex> lock(Profile::g_mutex);
        Profile::g_parseResult = ERR_OK;
        overlayMsg = ObtainOverlayType(jsonObject);
        if ((overlayMsg.type == NON_OVERLAY_TYPE) && (Profile::g_parseResult != ERR_OK)) {
            int32_t ret = Profile::g_parseResult;
            Profile::g_parseResult = ERR_OK;
            APP_LOGE("ObtainOverlayType g_parseResult %{public}d", ret);
            return ret;
        }
        APP_LOGD("overlay type of the hap is %{public}d", overlayMsg.type);
        Profile::g_parseResult = ERR_OK;
        moduleJson = jsonObject.get<Profile::ModuleJson>();
        if (Profile::g_parseResult != ERR_OK) {
            APP_LOGE("g_parseResult %{public}d", Profile::g_parseResult);
            int32_t ret = Profile::g_parseResult;
            // need recover parse result to ERR_OK
            Profile::g_parseResult = ERR_OK;
            return ret;
        }
    }
    if (!ToInnerBundleInfo(
        moduleJson, bundleExtractor, overlayMsg, innerBundleInfo)) {
        return ERR_APPEXECFWK_PARSE_PROFILE_PROP_CHECK_ERROR;
    }
    if (!ParserAtomicConfig(jsonObject, innerBundleInfo)) {
        APP_LOGE("Parser atomicService config failed");
        return ERR_APPEXECFWK_PARSE_PROFILE_PROP_CHECK_ERROR;
    }
    if (!ParserNativeSo(moduleJson, bundleExtractor, innerBundleInfo)) {
#ifdef X86_EMULATOR_MODE
        APP_LOGE("Parser native so failed");
        return ERR_APPEXECFWK_PARSE_NATIVE_SO_FAILED;
#endif
        APP_LOGW("Parser native so failed");
    }
    if (!ParserArkNativeFilePath(moduleJson, bundleExtractor, innerBundleInfo)) {
#ifdef X86_EMULATOR_MODE
        APP_LOGE("Parser ark native file failed");
        return ERR_APPEXECFWK_PARSE_AN_FAILED;
#endif
        APP_LOGW("Parser ark native file failed");
    }
    return ERR_OK;
}

ErrCode ModuleProfile::TransformToTestRunner(
    const std::ostringstream &source,
    ModuleTestRunner &moduleTestRunner) const
{
    APP_LOGD("transform module.json stream to TestRunner");
    nlohmann::json jsonObject = nlohmann::json::parse(source.str(), nullptr, false);
    if (jsonObject.is_discarded()) {
        APP_LOGE("bad profile");
        return ERR_APPEXECFWK_PARSE_BAD_PROFILE;
    }
    if (!jsonObject.contains(Profile::MODULE)) {
        APP_LOGE("TransformToTestRunner failed due to bad module.json");
        return ERR_APPEXECFWK_PARSE_BAD_PROFILE;
    }
    nlohmann::json moduleJson = jsonObject.at(Profile::MODULE);
    if (!moduleJson.contains(Profile::TEST_RUNNER)) {
        APP_LOGE("module.json not have testRunner");
        return ERR_APPEXECFWK_PARSE_BAD_PROFILE;
    }
    nlohmann::json testRunnerObj = moduleJson.at(Profile::TEST_RUNNER);
    if (!testRunnerObj.is_object()) {
        APP_LOGE("testRunnerObj is not object");
        return ERR_APPEXECFWK_PARSE_BAD_PROFILE;
    }
    if (testRunnerObj.contains(Profile::TEST_RUNNER_NAME)) {
        if (testRunnerObj.at(Profile::TEST_RUNNER_NAME).is_string()) {
            moduleTestRunner.name = testRunnerObj.at(Profile::TEST_RUNNER_NAME);
        }
        APP_LOGW("name is not string");
    }
    if (testRunnerObj.contains(Profile::TEST_RUNNER_SRC_PATH)) {
        if (testRunnerObj.at(Profile::TEST_RUNNER_SRC_PATH).is_string()) {
            moduleTestRunner.srcPath = testRunnerObj.at(Profile::TEST_RUNNER_SRC_PATH);
        }
        APP_LOGW("srcPath is not string");
    }
    if (testRunnerObj.contains(Profile::TEST_RUNNER_ARKTS_MODE)) {
        if (testRunnerObj.at(Profile::TEST_RUNNER_ARKTS_MODE).is_string()) {
            moduleTestRunner.arkTSMode = testRunnerObj.at(Profile::TEST_RUNNER_ARKTS_MODE);
        }
        APP_LOGW("arkTSMode is not string");
    }
    return ERR_OK;
}
}  // namespace AppExecFwk
}  // namespace OHOS
