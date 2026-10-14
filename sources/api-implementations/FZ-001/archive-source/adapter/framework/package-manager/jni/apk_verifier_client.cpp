#include "apk_verifier_client.h"

#include "apk_signature_verifier.h"
#include "apk_verified_session_c_api.h"

#include <array>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <openssl/evp.h>
#include <openssl/sha.h>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

#if defined(__linux__) || defined(__OHOS__)
#include <sys/mman.h>
#endif

namespace oh_adapter {
namespace {

constexpr uint64_t kMaxApkBytes = 1024ull * 1024ull * 1024ull;

void SetError(std::string* error, const std::string& value)
{
    if (error != nullptr) *error = value;
}

// Opens the ingress as one caller-owned fd for every downstream reader
// (verifier, manifest parser, install metadata). On OHOS foundation/BMS,
// sealed memfd snapshots can be blocked by SELinux at fstat(), so the package
// install route keeps the BMS-owned stream_install regular file open instead.
bool OpenIngressVerifierFd(const std::string& path, int* outFd, std::string* error)
{
#if !defined(__linux__) && !defined(__OHOS__)
    (void)path;
    (void)outFd;
    SetError(error, "verifier fd ingress is unavailable on this host");
    return false;
#else
    int sourceFd = open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (sourceFd < 0) {
        SetError(error, "cannot open APK ingress: " + std::string(strerror(errno)));
        return false;
    }

    struct stat before{};
    if (fstat(sourceFd, &before) != 0 || !S_ISREG(before.st_mode) ||
        before.st_size <= 0 || static_cast<uint64_t>(before.st_size) > kMaxApkBytes) {
        close(sourceFd);
        SetError(error, "APK ingress is not a bounded regular file");
        return false;
    }

#if defined(__OHOS__)
    *outFd = sourceFd;
    return true;
#else
    constexpr int kRequiredSeals =
        F_SEAL_WRITE | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL;
    int snapshotFd = memfd_create("oh-adapter-apk", MFD_CLOEXEC | MFD_ALLOW_SEALING);
    if (snapshotFd < 0 || ftruncate(snapshotFd, before.st_size) != 0) {
        const int savedErrno = errno;
        if (snapshotFd >= 0) close(snapshotFd);
        close(sourceFd);
        SetError(error, "cannot create APK snapshot: " + std::string(strerror(savedErrno)));
        return false;
    }

    std::array<uint8_t, 64 * 1024> buffer{};
    off_t offset = 0;
    bool copied = true;
    while (offset < before.st_size) {
        const size_t wanted = static_cast<size_t>(
            std::min<off_t>(static_cast<off_t>(buffer.size()), before.st_size - offset));
        ssize_t count = pread(sourceFd, buffer.data(), wanted, offset);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) {
            copied = false;
            break;
        }
        size_t written = 0;
        while (written < static_cast<size_t>(count)) {
            ssize_t writeCount = pwrite(snapshotFd, buffer.data() + written,
                                        static_cast<size_t>(count) - written,
                                        offset + static_cast<off_t>(written));
            if (writeCount < 0 && errno == EINTR) continue;
            if (writeCount <= 0) {
                copied = false;
                break;
            }
            written += static_cast<size_t>(writeCount);
        }
        if (!copied) break;
        offset += count;
    }

    struct stat after{};
    if (!copied || offset != before.st_size || fstat(sourceFd, &after) != 0 ||
        after.st_dev != before.st_dev || after.st_ino != before.st_ino ||
        after.st_size != before.st_size || fsync(snapshotFd) != 0 ||
        fcntl(snapshotFd, F_ADD_SEALS, kRequiredSeals) != 0 ||
        (fcntl(snapshotFd, F_GET_SEALS) & kRequiredSeals) != kRequiredSeals ||
        lseek(snapshotFd, 0, SEEK_SET) != 0) {
        const int savedErrno = errno;
        close(snapshotFd);
        close(sourceFd);
        SetError(error, "cannot finalize sealed APK snapshot: " +
            std::string(strerror(savedErrno)));
        return false;
    }

    close(sourceFd);
    *outFd = snapshotFd;
    return true;
#endif
#endif
}

bool ComputeFdSha256(int fd, Sha256Digest* digest)
{
    EVP_MD_CTX* context = EVP_MD_CTX_new();
    if (context == nullptr || EVP_DigestInit_ex(context, EVP_sha256(), nullptr) != 1) {
        EVP_MD_CTX_free(context);
        return false;
    }
    std::array<uint8_t, 64 * 1024> buffer{};
    off_t offset = 0;
    while (true) {
        ssize_t count = pread(fd, buffer.data(), buffer.size(), offset);
        if (count < 0 && errno == EINTR) continue;
        if (count < 0) {
            EVP_MD_CTX_free(context);
            return false;
        }
        if (count == 0) break;
        if (EVP_DigestUpdate(context, buffer.data(), static_cast<size_t>(count)) != 1) {
            EVP_MD_CTX_free(context);
            return false;
        }
        offset += count;
    }
    unsigned int digestLength = 0;
    const bool ok = EVP_DigestFinal_ex(context, digest->data(), &digestLength) == 1 &&
        digestLength == digest->size();
    EVP_MD_CTX_free(context);
    return ok;
}

}  // namespace

int ApkVerifierClient::OpenAndVerify(const std::string& apkPath, uint32_t minSchemeVersion,
                                     VerifiedApkSession* out, std::string* error)
{
    if (out == nullptr || apkPath.empty() ||
        (minSchemeVersion != 1 && minSchemeVersion != 2 && minSchemeVersion != 3)) {
        SetError(error, "invalid verifier client arguments");
        return OH_ADAPTER_APK_VERIFY_BAD_ARGUMENT;
    }
    ApkVerifierClient::Close(out);

    int snapshotFd = -1;
    if (!OpenIngressVerifierFd(apkPath, &snapshotFd, error)) {
        return OH_ADAPTER_APK_VERIFY_SNAPSHOT_FAILED;
    }

    // Package-boundary native verification. No AppSpawnX socket, no ART/Java
    // bridge: the same process that owns the sealed fd verifies it in-place.
    ApkVerifiedIdentity identity;
    if (!ApkSignatureVerifier::VerifyFd(snapshotFd, minSchemeVersion, &identity, error)) {
        close(snapshotFd);
        return OH_ADAPTER_APK_VERIFY_RESPONSE_REJECTED;
    }

    if (!ComputeFdSha256(snapshotFd, &identity.apkSha256) ||
        lseek(snapshotFd, 0, SEEK_SET) != 0) {
        close(snapshotFd);
        SetError(error, "cannot compute whole-APK digest from sealed snapshot");
        return OH_ADAPTER_APK_VERIFY_RESPONSE_REJECTED;
    }

    out->sealedFd = snapshotFd;
    out->identity = std::move(identity);
    if (error != nullptr) error->clear();
    return OH_ADAPTER_APK_VERIFY_OK;
}

void ApkVerifierClient::Close(VerifiedApkSession* session)
{
    if (session == nullptr) return;
    if (session->sealedFd >= 0) close(session->sealedFd);
    session->sealedFd = -1;
    session->identity = ApkVerifiedIdentity{};
}

}  // namespace oh_adapter
