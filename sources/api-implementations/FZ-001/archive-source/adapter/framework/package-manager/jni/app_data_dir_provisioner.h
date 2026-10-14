/*
 * app_data_dir_provisioner.h
 *
 * Post-registration app data directory provisioner for the APK install
 * route (libapk_installer.so).
 *
 * Background:
 *   Android APKs enter BMS through the adapter fast path
 *   (oh_adapter_install_apk_with_manifest), which never reaches the stock
 *   CreateBundleUserData flow. On D600 the appspawn-x child then died in
 *   DoAppSandboxMountOnce ("section app-base failed", errno=2) because the
 *   sandbox bind-mount source directories did not exist.
 *
 *   This module creates the three OH-conventional app data roots after a
 *   successful install, following the conventions observed on D600 for
 *   already-installed apps (e.g. com.ohos.amsdialog, uid 20010007):
 *     /data/app/el2/<userId>/base/<pkg>     owner uid:gid  mode 0700
 *     /data/app/el2/<userId>/log/<pkg>      owner uid:gid  mode 0700
 *     /data/app/el1/<userId>/database/<pkg> owner uid:gid  mode 0770
 *   (Cross-checked against OH 6.1 InstalldHostImpl::CreateBundleDataDir /
 *   CreateEl2DataDir: base=S_IRWXU, log=el2 log root, database=S_IRWXU|S_IRWXG.)
 *
 *   SELinux labels (u:object_r:data_app_el2_file:s0 / data_app_el1_file:s0)
 *   are NOT set explicitly: on-device observation shows directories created
 *   under /data/app/el{1,2}/ inherit the correct label from SELinux policy
 *   (the manual datadir-fix on D600 produced exactly those labels via plain
 *   mkdir/chown/chmod). No libselinux dependency is introduced.
 *
 * Call contract:
 *   Must be invoked AFTER BMS registration assigned the real uid/gid
 *   (InnerBundleInfo::GetUid(userId)); the hash uid inside
 *   oh_adapter_install_apk_with_manifest is NOT the sandbox uid.
 *   Idempotent: re-install / update over existing directories succeeds and
 *   re-asserts owner/mode. Failures are typed, never silently swallowed.
 */
#ifndef APP_DATA_DIR_PROVISIONER_H
#define APP_DATA_DIR_PROVISIONER_H

#include <cstdint>
#include <string>

namespace oh_adapter {

// Typed failure codes. 0 is success; every non-zero value identifies the
// failing stage so callers can fail-closed with an actionable log.
enum AppDataDirStatus : int32_t {
    APP_DATA_DIR_OK = 0,
    APP_DATA_DIR_INVALID_PACKAGE_NAME = 1,  // empty / too long / illegal chars / ".."
    APP_DATA_DIR_INVALID_IDS = 2,           // uid/gid/userId out of range
    APP_DATA_DIR_PATH_TOO_LONG = 3,         // composed path exceeds PATH_MAX
    APP_DATA_DIR_PARENT_MISSING = 4,        // /data/app/<el>/<userId>/<kind> absent
    APP_DATA_DIR_MKDIR_FAILED = 5,          // mkdir() failed (see errno in detail)
    APP_DATA_DIR_NOT_A_DIRECTORY = 6,       // target exists but is not a directory
    APP_DATA_DIR_CHOWN_FAILED = 7,          // chown() failed
    APP_DATA_DIR_CHMOD_FAILED = 8,          // chmod() failed
    APP_DATA_DIR_VERIFY_FAILED = 9,         // post-write readback mismatch
};

// Creates (or re-asserts) the three app data directories for |packageName|
// under the OH data root "/data/app". |uid|/|gid| are the BMS-assigned app
// ids, |userId| the OH user (e.g. 100). On failure returns a typed status
// and, when |errorDetail| is non-null, a human-readable message including
// the failing path and errno.
AppDataDirStatus EnsureAppDataDirs(const std::string& packageName,
    int32_t uid, int32_t gid, int32_t userId, std::string* errorDetail);

// Same as EnsureAppDataDirs but rooted at |dataAppRoot| instead of
// "/data/app". Exists so host tests can run against a temporary root with
// the caller's own uid/gid; production code must use EnsureAppDataDirs.
AppDataDirStatus EnsureAppDataDirsUnder(const std::string& dataAppRoot,
    const std::string& packageName, int32_t uid, int32_t gid, int32_t userId,
    std::string* errorDetail);

// Stable name for a status code, for typed logging ("CHOWN_FAILED" etc.).
const char* AppDataDirStatusName(AppDataDirStatus status);

}  // namespace oh_adapter

#endif  // APP_DATA_DIR_PROVISIONER_H
