/*
 * Host negative/positive corpus for the native (AppSpawnX-free) verifier
 * client. Exercises ApkVerifierClient::OpenAndVerify end to end: sealed-fd
 * snapshot creation + in-process APK Signature Scheme v2/v3 verification.
 *
 * Usage: test_apk_verifier_client_native <canonical-signed.apk>
 *        [signature-digest-list-mismatch.apk]
 *        [v31-block-stripped.apk]
 *        [v31-target-sdk-positive.apk]
 */
#include "apk_verifier_client.h"
#include "apk_verified_session_c_api.h"
#include "apk_verify_result.h"

#include <cstdint>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <openssl/sha.h>
#include <string>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

using oh_adapter::ApkVerifierClient;
using oh_adapter::Sha256ToLowerHex;
using oh_adapter::VerifiedApkSession;

namespace {

int g_failures = 0;

void Expect(bool condition, const std::string& what)
{
    if (!condition) {
        std::cerr << "FAIL: " << what << std::endl;
        ++g_failures;
    } else {
        std::cout << "ok: " << what << std::endl;
    }
}

bool CopyFile(const std::string& src, const std::string& dst)
{
    std::ifstream in(src, std::ios::binary);
    std::ofstream out(dst, std::ios::binary | std::ios::trunc);
    if (!in || !out) return false;
    out << in.rdbuf();
    return in.good() || in.eof();
}

bool FlipByte(const std::string& path, off_t offset)
{
    int fd = open(path.c_str(), O_RDWR);
    if (fd < 0) return false;
    uint8_t b = 0;
    bool ok = pread(fd, &b, 1, offset) == 1;
    b ^= 0xff;
    ok = ok && pwrite(fd, &b, 1, offset) == 1;
    close(fd);
    return ok;
}

// A minimal, structurally-valid empty ZIP: just the 22-byte EOCD record,
// zero entries, zero comment. No APK Signing Block: exercises the "unsigned"
// and "empty package" negative cases without needing external zip tooling.
void WriteEmptyUnsignedZip(const std::string& path)
{
    std::vector<uint8_t> eocd(22, 0);
    eocd[0] = 0x50; eocd[1] = 0x4b; eocd[2] = 0x05; eocd[3] = 0x06;  // signature
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    out.write(reinterpret_cast<const char*>(eocd.data()), eocd.size());
}

int RunPositiveCase(const std::string& canonical)
{
    VerifiedApkSession session;
    std::string error;
    int rc = ApkVerifierClient::OpenAndVerify(canonical, 2, &session, &error);
    Expect(rc == OH_ADAPTER_APK_VERIFY_OK, "valid canonical APK verifies OK (rc=" +
        std::to_string(rc) + " error=" + error + ")");
    Expect(session.sealedFd >= 0, "valid canonical APK yields a sealed fd");
    Expect(!session.identity.currentSignerSha256.empty(), "valid canonical APK yields signer identity");
    Expect(session.identity.currentSignerCertificateDer.size() ==
            session.identity.currentSignerSha256.size(),
        "valid canonical APK yields one DER certificate per signer digest");
    for (size_t index = 0;
         index < session.identity.currentSignerCertificateDer.size() &&
             index < session.identity.currentSignerSha256.size();
         ++index) {
        const auto& certificate = session.identity.currentSignerCertificateDer[index];
        oh_adapter::Sha256Digest digest{};
        if (!certificate.empty()) {
            SHA256(certificate.data(), certificate.size(), digest.data());
        }
        Expect(!certificate.empty(),
            "verified current signer certificate DER is non-empty");
        Expect(digest == session.identity.currentSignerSha256[index],
            "SHA-256 of signer DER equals verified signer digest");
    }
    if (!session.identity.currentSignerSha256.empty()) {
        std::cout << "signer_sha256=" << Sha256ToLowerHex(session.identity.currentSignerSha256[0])
                  << std::endl;
    }
    std::cout << "apk_sha256=" << Sha256ToLowerHex(session.identity.apkSha256) << std::endl;
    std::cout << "scheme_version=" << session.identity.schemeVersion << std::endl;
    ApkVerifierClient::Close(&session);
    return rc;
}

void RunNegativeCase(const std::string& label, const std::string& path, uint32_t minScheme = 2)
{
    VerifiedApkSession session;
    std::string error;
    int rc = ApkVerifierClient::OpenAndVerify(path, minScheme, &session, &error);
    Expect(rc != OH_ADAPTER_APK_VERIFY_OK, label + " is rejected (rc=" + std::to_string(rc) + ")");
    Expect(session.sealedFd < 0, label + " leaves no dangling sealed fd on rejection");
    if (!error.empty()) std::cout << label << " reason=" << error << std::endl;
    ApkVerifierClient::Close(&session);
}

void RunV31PositiveCase(const std::string& path)
{
    VerifiedApkSession session;
    std::string error;
    const int rc =
        ApkVerifierClient::OpenAndVerify(path, 3, &session, &error);
    Expect(rc == OH_ADAPTER_APK_VERIFY_OK,
        "AOSP v3.1 target-SDK fixture verifies (rc=" +
            std::to_string(rc) + " error=" + error + ")");
    Expect(session.identity.schemeVersion == 3,
        "AOSP v3.1 target-SDK fixture yields scheme 3");
    Expect(session.identity.v3BlockId == 0x1b93ad61u,
        "AOSP v3.1 target-SDK fixture selects v3.1 block");
    Expect(!session.identity.currentSignerSha256.empty(),
        "AOSP v3.1 target-SDK fixture yields signer identity");
    ApkVerifierClient::Close(&session);
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc < 2) {
        std::cerr << "usage: test_apk_verifier_client_native "
                     "<canonical-signed.apk> "
                     "[signature-digest-list-mismatch.apk] "
                     "[v31-block-stripped.apk] "
                     "[v31-target-sdk-positive.apk]" << std::endl;
        return 2;
    }
    const std::string canonical = argv[1];
    const char* tmpdir = std::getenv("TMPDIR");
    const std::string work = std::string(
        tmpdir != nullptr && tmpdir[0] != '\0' ? tmpdir : "/tmp") +
        "/oh_adapter_native_verify_" + std::to_string(getpid());

    RunPositiveCase(canonical);

    {
        const std::string tampered = work + "_tampered.apk";
        Expect(CopyFile(canonical, tampered), "tamper fixture copy succeeds");
        Expect(FlipByte(tampered, 100), "tamper fixture byte flip succeeds");
        RunNegativeCase("one-byte tamper in v2-protected content", tampered);
        unlink(tampered.c_str());
    }

    {
        const std::string truncated = work + "_truncated.apk";
        std::ifstream in(canonical, std::ios::binary);
        std::vector<char> buf(4096);
        in.read(buf.data(), static_cast<std::streamsize>(buf.size()));
        std::ofstream out(truncated, std::ios::binary | std::ios::trunc);
        out.write(buf.data(), in.gcount());
        out.close();
        RunNegativeCase("truncated APK", truncated);
        unlink(truncated.c_str());
    }

    {
        const std::string zero = work + "_zero.apk";
        std::ofstream(zero, std::ios::binary | std::ios::trunc).close();
        RunNegativeCase("zero-length APK", zero);
        unlink(zero.c_str());
    }

    {
        const std::string oversized = work + "_oversized.apk";
        int fd = open(oversized.c_str(), O_RDWR | O_CREAT | O_TRUNC, 0600);
        Expect(fd >= 0, "oversized fixture create succeeds");
        if (fd >= 0) {
            Expect(ftruncate(fd, static_cast<off_t>(1024ull * 1024ull * 1024ull + 1)) == 0,
                "oversized fixture sparse-truncate succeeds");
            close(fd);
        }
        RunNegativeCase(">1GiB APK", oversized);
        unlink(oversized.c_str());
    }

    {
        const std::string unsignedZip = work + "_unsigned.apk";
        WriteEmptyUnsignedZip(unsignedZip);
        RunNegativeCase("unsigned/empty package", unsignedZip);
        unlink(unsignedZip.c_str());
    }

    {
        const std::string link = work + "_symlink.apk";
        unlink(link.c_str());
        Expect(symlink(canonical.c_str(), link.c_str()) == 0, "symlink fixture create succeeds");
        RunNegativeCase("symlink ingress", link);
        unlink(link.c_str());
    }

    RunNegativeCase("v2-only canonical APK does not satisfy minSchemeVersion=3", canonical, 3);
    if (argc >= 3) {
        RunNegativeCase(
            "AOSP signatures/digests algorithm-list mismatch", argv[2]);
    }
    if (argc >= 4) {
        RunNegativeCase(
            "AOSP v3.1 block stripping-protection violation", argv[3]);
    }
    if (argc >= 5) RunV31PositiveCase(argv[4]);

    if (g_failures != 0) {
        std::cerr << "FAIL apk_verifier_client_native (" << g_failures << " failures)" << std::endl;
        return 1;
    }
    std::cout << "PASS apk_verifier_client_native" << std::endl;
    return 0;
}
