/*
 * directory_ex.h — HOST-TEST SHIM (not for device/target builds).
 *
 * Provides the two OHOS:: directory helpers apk_installer.cpp uses,
 * implemented on std::filesystem for host tests.
 */
#ifndef HOST_SHIM_DIRECTORY_EX_H
#define HOST_SHIM_DIRECTORY_EX_H

#include <filesystem>
#include <string>

namespace OHOS {

inline bool ForceCreateDirectory(const std::string& path)
{
    std::error_code ec;
    if (std::filesystem::create_directories(path, ec)) {
        return true;
    }
    return !ec && std::filesystem::is_directory(path);
}

inline bool ForceRemoveDirectory(const std::string& path)
{
    std::error_code ec;
    std::filesystem::remove_all(path, ec);
    return !ec;
}

}  // namespace OHOS

#endif  // HOST_SHIM_DIRECTORY_EX_H
