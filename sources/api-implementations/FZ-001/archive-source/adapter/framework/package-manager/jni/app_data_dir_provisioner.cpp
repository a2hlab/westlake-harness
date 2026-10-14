/*
 * app_data_dir_provisioner.cpp
 *
 * See app_data_dir_provisioner.h for the contract. Implementation notes:
 *   - Only the leaf <pkg> directory is created; the parent
 *     /data/app/<el>/<userId>/<kind> is a system-owned root that must already
 *     exist (matching stock installd, which refuses to improvise parents).
 *   - mkdir is followed by an unconditional chown+chmod so updates over
 *     pre-existing directories re-assert the exact owner/mode contract.
 *   - Every mutation is verified by a fresh lstat() readback; a mismatch is
 *     APP_DATA_DIR_VERIFY_FAILED, never silently accepted.
 */

#include "app_data_dir_provisioner.h"

#include <cerrno>
#include <cstdio>
#include <cstring>
#include <limits.h>
#include <string>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

namespace oh_adapter {
namespace {

// OH-conventional per-app data roots (D600 observation, cross-checked
// against InstalldHostImpl::CreateBundleDataDir/CreateEl2DataDir):
//   el2 base 0700, el2 log 0700, el1 database 0770 — all owner uid:gid.
struct DirSpec {
    const char* el;    // "el1" / "el2"
    const char* kind;  // "base" / "log" / "database"
    mode_t mode;
};

constexpr DirSpec kDirSpecs[] = {
    {"el2", "base", S_IRWXU},                 // 0700
    {"el2", "log", S_IRWXU},                  // 0700
    {"el1", "database", S_IRWXU | S_IRWXG},   // 0770
};

constexpr size_t kMaxPackageNameLength = 256;

bool IsValidPackageName(const std::string& packageName)
{
    if (packageName.empty() || packageName.size() > kMaxPackageNameLength) {
        return false;
    }
    // Reject path traversal and separators outright.
    if (packageName.find("..") != std::string::npos) {
        return false;
    }
    for (char c : packageName) {
        const bool ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
            (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-';
        if (!ok) {
            return false;
        }
    }
    return true;
}

void SetDetail(std::string* errorDetail, const char* stage,
    const std::string& path, int errorNumber)
{
    if (errorDetail == nullptr) {
        return;
    }
    char buffer[PATH_MAX + 128];
    snprintf(buffer, sizeof(buffer), "%s failed for %s: errno=%d (%s)",
        stage, path.c_str(), errorNumber, strerror(errorNumber));
    *errorDetail = buffer;
}

AppDataDirStatus EnsureOneDir(const std::string& path, mode_t mode,
    int32_t uid, int32_t gid, std::string* errorDetail)
{
    if (mkdir(path.c_str(), mode) != 0) {
        if (errno == ENOENT) {
            SetDetail(errorDetail, "mkdir(parent missing)", path, errno);
            return APP_DATA_DIR_PARENT_MISSING;
        }
        if (errno != EEXIST) {
            SetDetail(errorDetail, "mkdir", path, errno);
            return APP_DATA_DIR_MKDIR_FAILED;
        }
    }
    struct stat st {};
    if (lstat(path.c_str(), &st) != 0) {
        SetDetail(errorDetail, "lstat", path, errno);
        return APP_DATA_DIR_MKDIR_FAILED;
    }
    if (!S_ISDIR(st.st_mode)) {
        SetDetail(errorDetail, "lstat(not a directory)", path, 0);
        return APP_DATA_DIR_NOT_A_DIRECTORY;
    }
    if (chown(path.c_str(), static_cast<uid_t>(uid), static_cast<gid_t>(gid)) != 0) {
        SetDetail(errorDetail, "chown", path, errno);
        return APP_DATA_DIR_CHOWN_FAILED;
    }
    // chmod is unconditional: mkdir applies umask and an EEXIST directory
    // may carry a stale mode, so the contract is re-asserted every time.
    if (chmod(path.c_str(), mode) != 0) {
        SetDetail(errorDetail, "chmod", path, errno);
        return APP_DATA_DIR_CHMOD_FAILED;
    }
    struct stat verify {};
    if (lstat(path.c_str(), &verify) != 0) {
        SetDetail(errorDetail, "lstat(verify)", path, errno);
        return APP_DATA_DIR_VERIFY_FAILED;
    }
    if (!S_ISDIR(verify.st_mode) ||
        verify.st_uid != static_cast<uid_t>(uid) ||
        verify.st_gid != static_cast<gid_t>(gid) ||
        (verify.st_mode & 0777) != mode) {
        if (errorDetail != nullptr) {
            char buffer[PATH_MAX + 160];
            snprintf(buffer, sizeof(buffer),
                "readback mismatch for %s: uid=%d gid=%d mode=%04o (want uid=%d gid=%d mode=%04o)",
                path.c_str(), static_cast<int>(verify.st_uid),
                static_cast<int>(verify.st_gid),
                static_cast<unsigned>(verify.st_mode & 0777),
                uid, gid, static_cast<unsigned>(mode));
            *errorDetail = buffer;
        }
        return APP_DATA_DIR_VERIFY_FAILED;
    }
    return APP_DATA_DIR_OK;
}

}  // namespace

AppDataDirStatus EnsureAppDataDirsUnder(const std::string& dataAppRoot,
    const std::string& packageName, int32_t uid, int32_t gid, int32_t userId,
    std::string* errorDetail)
{
    if (!IsValidPackageName(packageName)) {
        if (errorDetail != nullptr) {
            *errorDetail = "invalid package name: " + packageName;
        }
        return APP_DATA_DIR_INVALID_PACKAGE_NAME;
    }
    if (uid <= 0 || gid <= 0 || userId < 0) {
        if (errorDetail != nullptr) {
            char buffer[128];
            snprintf(buffer, sizeof(buffer),
                "invalid ids: uid=%d gid=%d userId=%d", uid, gid, userId);
            *errorDetail = buffer;
        }
        return APP_DATA_DIR_INVALID_IDS;
    }
    if (dataAppRoot.empty() || dataAppRoot.front() != '/') {
        if (errorDetail != nullptr) {
            *errorDetail = "invalid data app root: " + dataAppRoot;
        }
        return APP_DATA_DIR_INVALID_PACKAGE_NAME;
    }

    const std::string userSegment = std::to_string(userId);
    for (const DirSpec& spec : kDirSpecs) {
        const std::string path = dataAppRoot + "/" + spec.el + "/" +
            userSegment + "/" + spec.kind + "/" + packageName;
        if (path.size() >= PATH_MAX) {
            if (errorDetail != nullptr) {
                *errorDetail = "path too long: " + path;
            }
            return APP_DATA_DIR_PATH_TOO_LONG;
        }
        const AppDataDirStatus status =
            EnsureOneDir(path, spec.mode, uid, gid, errorDetail);
        if (status != APP_DATA_DIR_OK) {
            return status;
        }
    }
    return APP_DATA_DIR_OK;
}

AppDataDirStatus EnsureAppDataDirs(const std::string& packageName,
    int32_t uid, int32_t gid, int32_t userId, std::string* errorDetail)
{
    return EnsureAppDataDirsUnder("/data/app", packageName, uid, gid, userId,
        errorDetail);
}

const char* AppDataDirStatusName(AppDataDirStatus status)
{
    switch (status) {
        case APP_DATA_DIR_OK: return "OK";
        case APP_DATA_DIR_INVALID_PACKAGE_NAME: return "INVALID_PACKAGE_NAME";
        case APP_DATA_DIR_INVALID_IDS: return "INVALID_IDS";
        case APP_DATA_DIR_PATH_TOO_LONG: return "PATH_TOO_LONG";
        case APP_DATA_DIR_PARENT_MISSING: return "PARENT_MISSING";
        case APP_DATA_DIR_MKDIR_FAILED: return "MKDIR_FAILED";
        case APP_DATA_DIR_NOT_A_DIRECTORY: return "NOT_A_DIRECTORY";
        case APP_DATA_DIR_CHOWN_FAILED: return "CHOWN_FAILED";
        case APP_DATA_DIR_CHMOD_FAILED: return "CHMOD_FAILED";
        case APP_DATA_DIR_VERIFY_FAILED: return "VERIFY_FAILED";
    }
    return "UNKNOWN";
}

}  // namespace oh_adapter
