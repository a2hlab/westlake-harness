#include "apk_installer.h"
#include "apk_manifest_parser.h"
#include "apk_network_permissions.h"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>
#include <unzip.h>
int main(int argc, char** argv) {
    using oh_adapter::MapApkNetworkPermissions;
    assert(MapApkNetworkPermissions({}).empty());
    assert(MapApkNetworkPermissions({"android.permission.CAMERA", "ohos.permission.INTERNET", "android.permission.INTERNET "}).empty());
    assert(MapApkNetworkPermissions({"android.permission.INTERNET", "android.permission.INTERNET"}) == std::vector<std::string>{"ohos.permission.INTERNET"});
    assert(MapApkNetworkPermissions({"android.permission.ACCESS_NETWORK_STATE"}) == std::vector<std::string>{"ohos.permission.GET_NETWORK_INFO"});
    assert((MapApkNetworkPermissions({"android.permission.INTERNET", "android.permission.ACCESS_NETWORK_STATE"}) == std::vector<std::string>{"ohos.permission.INTERNET", "ohos.permission.GET_NETWORK_INFO"}));
    assert(argc == 3);
    oh_adapter::ApkManifestParser::ManifestData manifest;
    assert(oh_adapter::ApkManifestParser::Parse(argv[1], manifest));
    auto expected = MapApkNetworkPermissions(manifest.usesPermissions);
    const auto background = oh_adapter::AdapterBackgroundLaunchPermissions();
    assert(background == std::vector<std::string>{"ohos.permission.START_ABILITIES_FROM_BACKGROUND"});
    expected.insert(expected.end(),background.begin(),background.end());
    assert(oh_adapter::ApkInstaller::ExtractAndPackResourceHap(argv[1], argv[2]));
    auto zip = unzOpen(argv[2]); assert(zip);
    assert(unzLocateFile(zip, "module.json", 0) == UNZ_OK);
    unz_file_info info{}; assert(unzGetCurrentFileInfo(zip, &info, nullptr, 0, nullptr, 0, nullptr, 0) == UNZ_OK);
    assert(unzOpenCurrentFile(zip) == UNZ_OK);
    std::string text(info.uncompressed_size, '\0');
    assert(unzReadCurrentFile(zip, text.data(), text.size()) == static_cast<int>(text.size()));
    unzCloseCurrentFile(zip); unzClose(zip);
    const auto json = nlohmann::json::parse(text);
    std::vector<std::string> actual;
    for(const auto& permission : json.at("module").at("requestPermissions")) actual.push_back(permission.at("name").get<std::string>());
    assert(actual == expected);
    std::ofstream(std::string(argv[2]) + ".module.json") << json.dump(2) << '\n';
    std::cout << nlohmann::json({{"apk",argv[1]}, {"requested_android",manifest.usesPermissions}, {"expected_oh",expected}, {"actual_oh",actual}, {"result","pass"}}).dump() << '\n';
}
