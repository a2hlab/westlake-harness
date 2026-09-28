/*
 * test_app_data_dir_provisioner.cpp
 *
 * Host-side developer test for the post-registration app data directory
 * provisioner (Fn01 install route, libapk_installer.so). Never issues a
 * formal PASS — exits non-zero on the first failed expectation.
 *
 * Coverage:
 *   P01  three data roots created with exact mode/owner (el2/base 0700,
 *        el2/log 0700, el1/database 0770, uid:gid = caller's own ids)
 *   P02  idempotent re-run (update path) re-asserts contract
 *   N01  invalid package names rejected, no directories created
 *   N02  missing system parent root -> APP_DATA_DIR_PARENT_MISSING
 *   F01  pre-existing regular file at target -> APP_DATA_DIR_NOT_A_DIRECTORY
 */

#include "app_data_dir_provisioner.h"

#include <cstdio>
#include <cstring>
#include <string>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

namespace {

int g_failures = 0;

void Check(bool condition, const char* caseId, const char* expectation)
{
    if (condition) {
        printf("OK   %s %s\n", caseId, expectation);
    } else {
        printf("FAIL %s %s\n", caseId, expectation);
        ++g_failures;
    }
}

bool MakeDir(const std::string& path, mode_t mode)
{
    return mkdir(path.c_str(), mode) == 0 || errno == EEXIST;
}

// Builds <root>/<el>/<userId>/<kind> parent chain (system-owned roots that
// production takes for granted) and returns the leaf path for <pkg>.
std::string MakeParents(const std::string& root, const char* el, int userId,
    const char* kind)
{
    std::string path = root + "/" + el;
    MakeDir(path, 0755);
    path += "/" + std::to_string(userId);
    MakeDir(path, 0755);
    path += "/" + std::string(kind);
    MakeDir(path, 0755);
    return path;
}

bool CheckDir(const std::string& path, mode_t wantMode, uid_t wantUid,
    gid_t wantGid)
{
    struct stat st {};
    return lstat(path.c_str(), &st) == 0 && S_ISDIR(st.st_mode) &&
        st.st_uid == wantUid && st.st_gid == wantGid &&
        (st.st_mode & 0777) == wantMode;
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s <scratch-dir>\n", argv[0]);
        return 2;
    }
    const std::string scratch = argv[1];
    const uid_t selfUid = getuid();
    const gid_t selfGid = getgid();
    const int32_t userId = 100;
    const std::string pkg = "com.example.provisioner_test";

    // ---- P01: positive — three roots with exact mode/owner ----
    {
        const std::string root = scratch + "/p01";
        MakeDir(root, 0755);
        MakeParents(root, "el2", userId, "base");
        MakeParents(root, "el2", userId, "log");
        MakeParents(root, "el1", userId, "database");
        std::string error;
        const oh_adapter::AppDataDirStatus status =
            oh_adapter::EnsureAppDataDirsUnder(root, pkg,
                static_cast<int32_t>(selfUid), static_cast<int32_t>(selfGid),
                userId, &error);
        Check(status == oh_adapter::APP_DATA_DIR_OK, "P01", "status==OK");
        Check(error.empty(), "P01", "no error detail on success");
        Check(CheckDir(root + "/el2/100/base/" + pkg, 0700, selfUid, selfGid),
            "P01", "el2/base mode 0700 owner self");
        Check(CheckDir(root + "/el2/100/log/" + pkg, 0700, selfUid, selfGid),
            "P01", "el2/log mode 0700 owner self");
        Check(CheckDir(root + "/el1/100/database/" + pkg, 0770, selfUid, selfGid),
            "P01", "el1/database mode 0770 owner self");
    }

    // ---- P02: update path — re-run over pre-existing dirs with a stale
    // mode re-asserts the contract instead of failing on EEXIST ----
    {
        const std::string root = scratch + "/p02";
        MakeDir(root, 0755);
        const std::string baseParent = MakeParents(root, "el2", userId, "base");
        MakeParents(root, "el2", userId, "log");
        MakeParents(root, "el1", userId, "database");
        const std::string stale = baseParent + "/" + pkg;
        if (!MakeDir(stale, 0755)) {
            Check(false, "P02", "fixture setup");
        } else {
            std::string error;
            Check(oh_adapter::EnsureAppDataDirsUnder(root, pkg,
                static_cast<int32_t>(selfUid), static_cast<int32_t>(selfGid),
                userId, &error) == oh_adapter::APP_DATA_DIR_OK,
                "P02", "status==OK over existing dir");
            Check(CheckDir(stale, 0700, selfUid, selfGid),
                "P02", "stale mode 0755 corrected to 0700");
        }
    }

    // ---- N01: invalid package names are rejected before any mutation ----
    {
        const std::string root = scratch + "/n01";
        MakeDir(root, 0755);
        MakeParents(root, "el2", userId, "base");
        MakeParents(root, "el2", userId, "log");
        MakeParents(root, "el1", userId, "database");
        const char* badNames[] = {"", "../evil", "a/b", ".."};
        for (int i = 0; i < 4; ++i) {
            std::string error;
            Check(oh_adapter::EnsureAppDataDirsUnder(root, badNames[i],
                static_cast<int32_t>(selfUid), static_cast<int32_t>(selfGid),
                userId, &error) == oh_adapter::APP_DATA_DIR_INVALID_PACKAGE_NAME,
                "N01", badNames[i][0] == '\0' ? "empty name rejected" : "illegal name rejected");
            Check(!error.empty(), "N01", "typed error carries detail");
        }
        struct stat st {};
        Check(lstat((root + "/el2/100/base/evil").c_str(), &st) != 0,
            "N01", "no directory created for rejected name");
    }

    // ---- N02: system parent root missing -> typed PARENT_MISSING ----
    {
        const std::string root = scratch + "/n02";
        MakeDir(root, 0755);  // deliberately no el2/100/base parents
        std::string error;
        Check(oh_adapter::EnsureAppDataDirsUnder(root, pkg,
            static_cast<int32_t>(selfUid), static_cast<int32_t>(selfGid),
            userId, &error) == oh_adapter::APP_DATA_DIR_PARENT_MISSING,
            "N02", "missing parent -> PARENT_MISSING");
        Check(error.find("errno") != std::string::npos,
            "N02", "detail carries errno");
    }

    // ---- F01: regular file squatting at target -> NOT_A_DIRECTORY ----
    {
        const std::string root = scratch + "/f01";
        MakeDir(root, 0755);
        const std::string baseParent = MakeParents(root, "el2", userId, "base");
        MakeParents(root, "el2", userId, "log");
        MakeParents(root, "el1", userId, "database");
        const std::string squatter = baseParent + "/" + pkg;
        FILE* file = fopen(squatter.c_str(), "w");
        if (file == nullptr) {
            Check(false, "F01", "fixture setup");
        } else {
            fputs("not a dir", file);
            fclose(file);
            std::string error;
            Check(oh_adapter::EnsureAppDataDirsUnder(root, pkg,
                static_cast<int32_t>(selfUid), static_cast<int32_t>(selfGid),
                userId, &error) == oh_adapter::APP_DATA_DIR_NOT_A_DIRECTORY,
                "F01", "squatting file -> NOT_A_DIRECTORY");
        }
    }

    if (g_failures != 0) {
        printf("DEVELOPER_TEST_FAILED failures=%d\n", g_failures);
        return 1;
    }
    printf("DEVELOPER_TEST_READY_FOR_HANDOFF module=app_data_dir_provisioner formal_verdict=NOT_ISSUED\n");
    return 0;
}
