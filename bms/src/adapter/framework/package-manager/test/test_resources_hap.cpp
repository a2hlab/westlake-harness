/*
 * test_resources_hap.cpp
 *
 * Host-side developer test for ApkInstaller::ExtractAndPackResourceHap
 * icon-less APK handling (2026-08-05 G1 install wall). Never issues a
 * formal PASS — exits non-zero on the first failed expectation.
 *
 * Fixtures (built by make_resources_hap_fixtures.py):
 *   g1.apk            real G1 HelloWorld.apk — provably icon-less
 *   truncated.apk     g1.apk cut short — tampered package
 *   corrupt_icon.apk  g1.apk + res/mipmap-xxxhdpi-v4/ic_launcher.png whose
 *                     deflate stream is destroyed — icon present but unreadable
 *
 * Expectations:
 *   P01 g1.apk          -> success, output hap carries the template's own
 *                          placeholder icon (post-normalization), no template
 *                          label for icon
 *   N01 truncated.apk   -> fail-closed, no output hap
 *   N02 corrupt_icon.apk-> fail-closed (present-but-unreadable icon entry is
 *                          tampering evidence), no output hap
 *
 * The typed alarm tokens (ICONLESS_APK_TEMPLATE_PLACEHOLDER etc.) go to
 * stderr via the host hilog shim and are asserted by the runner script.
 */

#include "apk_installer.h"
#include "icon_normalize.h"

#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <sys/stat.h>
#include <unzip.h>
#include <vector>

// template_entry_hap.h defines these as non-static globals; apk_installer.cpp
// already instantiates them, so the test references that single definition
// instead of including the header again (duplicate symbol at link).
extern unsigned char ohos_adapter_template_resources_hap[];
extern unsigned int ohos_adapter_template_resources_hap_len;

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

bool ReadZipEntryLocal(const std::string& zipPath, const std::string& entry,
    std::vector<uint8_t>& out)
{
    unzFile zf = unzOpen(zipPath.c_str());
    if (zf == nullptr) {
        return false;
    }
    bool ok = false;
    if (unzLocateFile(zf, entry.c_str(), 0) == UNZ_OK) {
        unz_file_info info {};
        if (unzGetCurrentFileInfo(zf, &info, nullptr, 0, nullptr, 0, nullptr, 0) == UNZ_OK &&
            unzOpenCurrentFile(zf) == UNZ_OK) {
            out.resize(info.uncompressed_size);
            int n = out.empty() ? 0
                : unzReadCurrentFile(zf, out.data(), info.uncompressed_size);
            unzCloseCurrentFile(zf);
            ok = (n == static_cast<int>(info.uncompressed_size));
        }
    }
    unzClose(zf);
    return ok;
}

bool FileExists(const std::string& path)
{
    struct stat st {};
    return ::stat(path.c_str(), &st) == 0;
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 3) {
        fprintf(stderr, "usage: %s <fixture-dir> <scratch-dir>\n", argv[0]);
        return 2;
    }
    const std::string fixtures = argv[1];
    const std::string scratch = argv[2];

    // The production caller (BuildApkResourcesHap via base_bundle_installer)
    // always creates <dirname(outHap)>/android before ExtractFiles; the
    // side-written icon.png depends on it, so the test mirrors that contract.
    for (const char* sub : {"p01", "n01", "n02"}) {
        std::filesystem::create_directories(
            scratch + "/" + sub + "/android");
    }

    // Expected placeholder: the template's own icon bytes, after the same
    // cosmetic normalization the production path applies.
    std::vector<uint8_t> expectedIcon;
    {
        const std::string templatePath = scratch + "/template.bin";
        std::ofstream f(templatePath, std::ios::binary | std::ios::trunc);
        f.write(reinterpret_cast<const char*>(ohos_adapter_template_resources_hap),
                ohos_adapter_template_resources_hap_len);
        f.close();
        Check(ReadZipEntryLocal(templatePath, "resources/base/media/icon.png", expectedIcon),
            "SETUP", "template placeholder icon readable");
        oh_adapter::NormalizeLauncherIconPng(expectedIcon);
    }

    // ---- P01: provably icon-less G1 -> template placeholder, install proceeds
    {
        const std::string outHap = scratch + "/p01/entry.hap";
        const bool rc = oh_adapter::ApkInstaller::ExtractAndPackResourceHap(
            fixtures + "/g1.apk", outHap);
        Check(rc, "P01", "icon-less G1 packs resources hap");
        std::vector<uint8_t> packedIcon;
        Check(FileExists(outHap) &&
                ReadZipEntryLocal(outHap, "resources/base/media/icon.png", packedIcon),
            "P01", "output hap icon entry readable");
        Check(packedIcon == expectedIcon,
            "P01", "packed icon == template's own placeholder (normalized)");
        std::vector<uint8_t> packedAppIcon;
        Check(ReadZipEntryLocal(outHap, "resources/base/media/app_icon.png", packedAppIcon) &&
                packedAppIcon == expectedIcon,
            "P01", "app_icon entry also == placeholder");
    }

    // ---- N01: truncated package -> fail-closed
    {
        const std::string outHap = scratch + "/n01/entry.hap";
        const bool rc = oh_adapter::ApkInstaller::ExtractAndPackResourceHap(
            fixtures + "/truncated.apk", outHap);
        Check(!rc, "N01", "truncated package refused");
        Check(!FileExists(outHap), "N01", "no output hap left behind");
    }

    // ---- N02: icon entry present but unreadable -> fail-closed (tampering)
    {
        const std::string outHap = scratch + "/n02/entry.hap";
        const bool rc = oh_adapter::ApkInstaller::ExtractAndPackResourceHap(
            fixtures + "/corrupt_icon.apk", outHap);
        Check(!rc, "N02", "present-but-unreadable icon refused");
        Check(!FileExists(outHap), "N02", "no output hap left behind");
    }

    if (g_failures != 0) {
        printf("DEVELOPER_TEST_FAILED failures=%d\n", g_failures);
        return 1;
    }
    printf("DEVELOPER_TEST_READY_FOR_HANDOFF module=resources_hap_iconless formal_verdict=NOT_ISSUED\n");
    return 0;
}
