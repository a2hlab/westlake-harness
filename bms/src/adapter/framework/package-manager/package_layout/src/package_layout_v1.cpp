#include "package_layout_v1.h"

#include "sha256.h"

#include <cerrno>
#include <climits>
#include <cstddef>
#include <cstring>
#include <fcntl.h>
#include <limits>
#include <sstream>
#include <string_view>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>
#include <utility>
#include <vector>

namespace oh_adapter::package_layout {
namespace {

constexpr mode_t kDirectoryMode = 0700;
constexpr mode_t kFileMode = 0600;

class ScopedFd final {
public:
    explicit ScopedFd(int fd = -1) : fd_(fd) {}
    ~ScopedFd()
    {
        if (fd_ >= 0) close(fd_);
    }
    ScopedFd(const ScopedFd&) = delete;
    ScopedFd& operator=(const ScopedFd&) = delete;
    int Get() const { return fd_; }

private:
    int fd_;
};

class ScopedFileLock final {
public:
    explicit ScopedFileLock(int fd) : fd_(fd) {}
    ~ScopedFileLock()
    {
        if (fd_ >= 0) flock(fd_, LOCK_UN);
    }
    ScopedFileLock(const ScopedFileLock&) = delete;
    ScopedFileLock& operator=(const ScopedFileLock&) = delete;

private:
    int fd_;
};

std::string JsonEscape(std::string_view value)
{
    std::string result;
    result.reserve(value.size() + 8);
    for (const unsigned char character : value) {
        switch (character) {
            case '"': result += "\\\""; break;
            case '\\': result += "\\\\"; break;
            case '\b': result += "\\b"; break;
            case '\f': result += "\\f"; break;
            case '\n': result += "\\n"; break;
            case '\r': result += "\\r"; break;
            case '\t': result += "\\t"; break;
            default:
                if (character < 0x20) {
                    static constexpr char kHex[] = "0123456789abcdef";
                    result += "\\u00";
                    result.push_back(kHex[character >> 4]);
                    result.push_back(kHex[character & 0x0f]);
                } else {
                    result.push_back(static_cast<char>(character));
                }
        }
    }
    return result;
}

std::string Sha256Hex(const uint8_t* bytes, size_t length)
{
    unsigned char digest[32]{};
    sha256(bytes, length, digest);
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        result[index * 2] = kHex[digest[index] >> 4];
        result[index * 2 + 1] = kHex[digest[index] & 0x0f];
    }
    return result;
}

bool IsLowerHexDigest(const std::string& value)
{
    if (value.size() != 64) return false;
    for (const char character : value) {
        if (!((character >= '0' && character <= '9') ||
              (character >= 'a' && character <= 'f'))) {
            return false;
        }
    }
    return true;
}

bool IsSafeIdentifier(const std::string& value, bool packageName)
{
    if (value.empty() || value.size() > 255 || value == "." || value == "..") {
        return false;
    }
    bool hasPackageSeparator = false;
    for (const unsigned char character : value) {
        const bool accepted =
            (character >= 'a' && character <= 'z') ||
            (character >= 'A' && character <= 'Z') ||
            (character >= '0' && character <= '9') ||
            character == '_' || character == '-' ||
            (packageName && character == '.');
        if (!accepted) return false;
        if (character == '.') hasPackageSeparator = true;
    }
    return !packageName || hasPackageSeparator;
}

LayoutVerdict ErrnoVerdict(int error)
{
    if (error == ELOOP) return LayoutVerdict::SYMLINK_ESCAPE;
    if (error == ENOTDIR) return LayoutVerdict::PATH_REJECTED;
    if (error == EACCES || error == EPERM || error == EROFS) {
        return LayoutVerdict::PERMISSION_DENIED;
    }
    if (error == ENOSPC || error == EDQUOT || error == EFBIG) {
        return LayoutVerdict::NO_SPACE;
    }
    return LayoutVerdict::IO_ERROR;
}

PackageLayoutReceiptV1 BaseReceipt(const FilePlanV1& plan)
{
    PackageLayoutReceiptV1 receipt;
    receipt.requestId = plan.requestId;
    receipt.transactionId = plan.transactionId;
    receipt.packageName = plan.packageName;
    receipt.userId = plan.userId;
    receipt.generation = plan.generation;
    receipt.artifactSetDigest = plan.artifactSetDigest;
    receipt.managedRootPolicyId = plan.managedRootPolicyId;
    receipt.terminalState = "REJECTED";
    return receipt;
}

PackageLayoutReceiptV1 Reject(const FilePlanV1& plan, LayoutVerdict verdict,
    std::string reason = {})
{
    PackageLayoutReceiptV1 receipt = BaseReceipt(plan);
    receipt.verdict = verdict;
    receipt.reason = std::move(reason);
    receipt.terminalState =
        verdict == LayoutVerdict::INTERRUPTED ? "INTERRUPTED" : "REJECTED";
    return receipt;
}

PackageLayoutReceiptV1 RejectErrno(
    const FilePlanV1& plan, const char* stage, int error)
{
    return Reject(plan, ErrnoVerdict(error),
        std::string(stage) + ":errno-" + std::to_string(error));
}

LayoutVerdict FaultVerdict(LayoutFaultDecision decision)
{
    switch (decision) {
        case LayoutFaultDecision::FAIL_NO_SPACE: return LayoutVerdict::NO_SPACE;
        case LayoutFaultDecision::FAIL_PERMISSION:
            return LayoutVerdict::PERMISSION_DENIED;
        case LayoutFaultDecision::INTERRUPT: return LayoutVerdict::INTERRUPTED;
        case LayoutFaultDecision::FAIL_IO: return LayoutVerdict::IO_ERROR;
        case LayoutFaultDecision::NONE: break;
    }
    return LayoutVerdict::IO_ERROR;
}

LayoutFaultDecision Invoke(LayoutFaultInjector* injector, LayoutFaultPhase phase)
{
    return injector == nullptr ? LayoutFaultDecision::NONE : injector->At(phase);
}

bool WriteAll(int fd, const uint8_t* bytes, size_t length)
{
    size_t written = 0;
    while (written < length) {
        const ssize_t count = write(fd, bytes + written, length - written);
        if (count < 0) {
            if (errno == EINTR) continue;
            return false;
        }
        if (count == 0) {
            errno = EIO;
            return false;
        }
        written += static_cast<size_t>(count);
    }
    return true;
}

bool ReadAllAt(int fd, uint64_t expectedLength, std::vector<uint8_t>* bytes)
{
    if (bytes == nullptr ||
        expectedLength > static_cast<uint64_t>(std::numeric_limits<size_t>::max())) {
        errno = EOVERFLOW;
        return false;
    }
    bytes->assign(static_cast<size_t>(expectedLength), 0);
    size_t offset = 0;
    while (offset < bytes->size()) {
        const ssize_t count = pread(fd, bytes->data() + offset,
            bytes->size() - offset, static_cast<off_t>(offset));
        if (count < 0) {
            if (errno == EINTR) continue;
            return false;
        }
        if (count == 0) {
            errno = EIO;
            return false;
        }
        offset += static_cast<size_t>(count);
    }
    uint8_t trailing = 0;
    const ssize_t trailingCount =
        pread(fd, &trailing, 1, static_cast<off_t>(offset));
    if (trailingCount < 0 && errno == EINTR) {
        return ReadAllAt(fd, expectedLength, bytes);
    }
    if (trailingCount != 0) {
        errno = trailingCount > 0 ? EOVERFLOW : errno;
        return false;
    }
    return true;
}

bool ReadSmallFileAt(int directoryFd, const char* name, std::string* value)
{
    ScopedFd file(openat(directoryFd, name, O_RDONLY | O_CLOEXEC | O_NOFOLLOW));
    if (file.Get() < 0) return false;
    struct stat status {};
    if (fstat(file.Get(), &status) != 0 || !S_ISREG(status.st_mode) ||
        status.st_size < 0 || status.st_size > 64 * 1024) {
        errno = EIO;
        return false;
    }
    std::vector<uint8_t> bytes;
    if (!ReadAllAt(file.Get(), static_cast<uint64_t>(status.st_size), &bytes)) {
        return false;
    }
    value->assign(bytes.begin(), bytes.end());
    return true;
}

bool WriteDurableFileAt(int directoryFd, const std::string& temporaryName,
    const std::string& finalName, std::string_view value)
{
    ScopedFd file(openat(directoryFd, temporaryName.c_str(),
        O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, kFileMode));
    if (file.Get() < 0) return false;
    if (!WriteAll(file.Get(), reinterpret_cast<const uint8_t*>(value.data()),
            value.size()) ||
        fsync(file.Get()) != 0) {
        const int saved = errno;
        unlinkat(directoryFd, temporaryName.c_str(), 0);
        errno = saved;
        return false;
    }
    if (renameat(directoryFd, temporaryName.c_str(),
            directoryFd, finalName.c_str()) != 0) {
        const int saved = errno;
        unlinkat(directoryFd, temporaryName.c_str(), 0);
        errno = saved;
        return false;
    }
    return fsync(directoryFd) == 0;
}

int OpenOrCreateDirectoryAt(int parentFd, const std::string& name)
{
    bool created = false;
    if (mkdirat(parentFd, name.c_str(), kDirectoryMode) == 0) {
        created = true;
    } else if (errno != EEXIST) {
        return -1;
    }
    const int directory = openat(parentFd, name.c_str(),
        O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (directory < 0) {
        const int openError = errno;
        struct stat candidate {};
        if ((openError == ENOTDIR || openError == ELOOP) &&
            fstatat(parentFd, name.c_str(), &candidate,
                AT_SYMLINK_NOFOLLOW) == 0 &&
            S_ISLNK(candidate.st_mode)) {
            errno = ELOOP;
        } else {
            errno = openError;
        }
        return -1;
    }
    if (created && fsync(parentFd) != 0) {
        const int saved = errno;
        close(directory);
        errno = saved;
        return -1;
    }
    return directory;
}

std::string SerializePlan(const FilePlanV1& plan,
    const VerifiedArtifactReceiptV1& verified)
{
    std::ostringstream output;
    output << "{\"schemaVersion\":1,\"requestId\":\""
           << JsonEscape(plan.requestId) << "\",\"transactionId\":\""
           << JsonEscape(plan.transactionId) << "\",\"callerScopeDigest\":\""
           << JsonEscape(plan.callerScopeDigest) << "\",\"userId\":"
           << plan.userId << ",\"packageName\":\""
           << JsonEscape(plan.packageName) << "\",\"generation\":"
           << plan.generation << ",\"artifactSetDigest\":\""
           << JsonEscape(plan.artifactSetDigest)
           << "\",\"managedRootPolicyId\":\""
           << JsonEscape(plan.managedRootPolicyId)
           << "\",\"artifactSha256\":\""
           << JsonEscape(verified.artifactSha256)
           << "\",\"byteLength\":" << verified.byteLength
           << ",\"policyVersion\":\"" << JsonEscape(verified.policyVersion)
           << "\",\"verifierVersion\":\""
           << JsonEscape(verified.verifierVersion) << "\",\"nativeAbis\":[";
    for (size_t index = 0; index < plan.nativeAbis.size(); ++index) {
        if (index != 0) output << ',';
        output << '"' << JsonEscape(plan.nativeAbis[index]) << '"';
    }
    output << "]}\n";
    return output.str();
}

}  // namespace

PackageLayoutV1::PackageLayoutV1(
    std::string managedRoot, ManagedRootPolicyV1 managedRootPolicy)
    : managedRoot_(std::move(managedRoot)),
      managedRootPolicy_(std::move(managedRootPolicy))
{
}

const char* PackageLayoutV1::VerdictName(LayoutVerdict verdict)
{
    switch (verdict) {
        case LayoutVerdict::FINALIZED: return "FINALIZED";
        case LayoutVerdict::INVALID_REQUEST: return "INVALID_REQUEST";
        case LayoutVerdict::NOT_SUPPORTED_USER: return "NOT_SUPPORTED_USER";
        case LayoutVerdict::NOT_SUPPORTED_ABI: return "NOT_SUPPORTED_ABI";
        case LayoutVerdict::VERIFIED_RECEIPT_MISMATCH:
            return "VERIFIED_RECEIPT_MISMATCH";
        case LayoutVerdict::MANAGED_ROOT_POLICY_MISMATCH:
            return "MANAGED_ROOT_POLICY_MISMATCH";
        case LayoutVerdict::PATH_REJECTED: return "PATH_REJECTED";
        case LayoutVerdict::SYMLINK_ESCAPE: return "SYMLINK_ESCAPE";
        case LayoutVerdict::PERMISSION_DENIED: return "PERMISSION_DENIED";
        case LayoutVerdict::NO_SPACE: return "NO_SPACE";
        case LayoutVerdict::TRANSACTION_CONFLICT:
            return "TRANSACTION_CONFLICT";
        case LayoutVerdict::IO_ERROR: return "IO_ERROR";
        case LayoutVerdict::DATA_INCONSISTENT: return "DATA_INCONSISTENT";
        case LayoutVerdict::INTERRUPTED: return "INTERRUPTED";
    }
    return "DATA_INCONSISTENT";
}

std::string PackageLayoutV1::SerializeReceipt(
    const PackageLayoutReceiptV1& receipt)
{
    std::ostringstream output;
    output << "{\"schemaVersion\":1,\"actionId\":\"Fn01.A07\""
           << ",\"requestId\":\"" << JsonEscape(receipt.requestId)
           << "\",\"transactionId\":\"" << JsonEscape(receipt.transactionId)
           << "\",\"packageName\":\"" << JsonEscape(receipt.packageName)
           << "\",\"userId\":" << receipt.userId
           << ",\"generation\":" << receipt.generation
           << ",\"artifactSetDigest\":\""
           << JsonEscape(receipt.artifactSetDigest)
           << "\",\"managedRootPolicyId\":\""
           << JsonEscape(receipt.managedRootPolicyId)
           << "\",\"terminalState\":\""
           << JsonEscape(receipt.terminalState)
           << "\",\"verdict\":\"" << VerdictName(receipt.verdict)
           << "\",\"reason\":\"" << JsonEscape(receipt.reason)
           << "\",\"baseCode\":{\"path\":\""
           << JsonEscape(receipt.baseCode.path)
           << "\",\"sha256\":\"" << JsonEscape(receipt.baseCode.sha256)
           << "\",\"byteLength\":" << receipt.baseCode.byteLength << "}}\n";
    return output.str();
}

PackageLayoutReceiptV1 PackageLayoutV1::Finalize(const FilePlanV1& plan,
    const VerifiedArtifactReceiptV1& verified, int artifactFd,
    LayoutFaultInjector* faultInjector)
{
    if (plan.schemaVersion != 1 || verified.schemaVersion != 1 ||
        plan.requestId.empty() || plan.transactionId.empty() ||
        plan.callerScopeDigest.empty() || plan.generation == 0 ||
        !IsLowerHexDigest(plan.artifactSetDigest) ||
        !IsSafeIdentifier(plan.transactionId, false)) {
        return Reject(plan, LayoutVerdict::INVALID_REQUEST);
    }
    if (!IsSafeIdentifier(plan.packageName, true)) {
        return Reject(plan, LayoutVerdict::PATH_REJECTED);
    }
    if (plan.userId != 0) {
        return Reject(plan, LayoutVerdict::NOT_SUPPORTED_USER);
    }
    for (const std::string& abi : plan.nativeAbis) {
        if (abi != "arm64-v8a") {
            return Reject(plan, LayoutVerdict::NOT_SUPPORTED_ABI);
        }
    }
    if (managedRoot_.empty() || managedRootPolicy_.schemaVersion != 1 ||
        managedRootPolicy_.policyId.empty() ||
        plan.managedRootPolicyId != managedRootPolicy_.policyId) {
        return Reject(plan, LayoutVerdict::MANAGED_ROOT_POLICY_MISMATCH);
    }
    if (!verified.verified || verified.requestId != plan.requestId ||
        verified.transactionId != plan.transactionId ||
        verified.packageName != plan.packageName ||
        verified.artifactSetDigest != plan.artifactSetDigest ||
        !IsLowerHexDigest(verified.artifactSha256) ||
        verified.byteLength == 0 || verified.policyVersion.empty() ||
        verified.verifierVersion.empty() || artifactFd < 0) {
        return Reject(plan, LayoutVerdict::VERIFIED_RECEIPT_MISMATCH);
    }

    struct stat rootStatus {};
    if (lstat(managedRoot_.c_str(), &rootStatus) != 0) {
        return RejectErrno(plan, "managed-root-lstat", errno);
    }
    if (S_ISLNK(rootStatus.st_mode)) {
        return Reject(plan, LayoutVerdict::SYMLINK_ESCAPE);
    }
    if (!S_ISDIR(rootStatus.st_mode)) {
        return Reject(plan, LayoutVerdict::PATH_REJECTED);
    }
    ScopedFd root(open(managedRoot_.c_str(),
        O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW));
    if (root.Get() < 0) return RejectErrno(plan, "managed-root-open", errno);
    char canonicalRoot[PATH_MAX]{};
    if (realpath(managedRoot_.c_str(), canonicalRoot) == nullptr) {
        return RejectErrno(plan, "managed-root-realpath", errno);
    }
    bool permittedRoot = false;
    for (const std::string& permitted :
        managedRootPolicy_.permittedCanonicalRoots) {
        if (permitted == canonicalRoot) {
            permittedRoot = true;
            break;
        }
    }
    if (!permittedRoot) {
        return Reject(plan, LayoutVerdict::MANAGED_ROOT_POLICY_MISMATCH);
    }
    const std::string canonicalRootPath(canonicalRoot);

    const std::string userDirectory = "u" + std::to_string(plan.userId);
    ScopedFd user(OpenOrCreateDirectoryAt(root.Get(), userDirectory));
    if (user.Get() < 0) return RejectErrno(plan, "user-directory", errno);
    ScopedFd package(OpenOrCreateDirectoryAt(user.Get(), plan.packageName));
    if (package.Get() < 0) return RejectErrno(plan, "package-directory", errno);
    const std::string generationName = "g" + std::to_string(plan.generation);
    ScopedFd generation(OpenOrCreateDirectoryAt(package.Get(), generationName));
    if (generation.Get() < 0) {
        return RejectErrno(plan, "generation-directory", errno);
    }
    int lockFileDescriptor = -1;
    for (int attempt = 0; attempt < 3; ++attempt) {
        lockFileDescriptor = openat(generation.Get(), ".layout.lock",
            O_RDWR | O_CREAT | O_CLOEXEC | O_NOFOLLOW, kFileMode);
        if (lockFileDescriptor >= 0 || errno != ENOENT) break;
    }
    ScopedFd lockFile(lockFileDescriptor);
    if (lockFile.Get() < 0) return RejectErrno(plan, "lock-open", errno);
    while (flock(lockFile.Get(), LOCK_EX) != 0) {
        if (errno == EINTR) continue;
        return RejectErrno(plan, "lock-acquire", errno);
    }
    ScopedFileLock transactionLock(lockFile.Get());

    const std::string planJson = SerializePlan(plan, verified);
    std::string priorPlan;
    errno = 0;
    if (ReadSmallFileAt(generation.Get(), "file-plan.v1.json", &priorPlan)) {
        if (priorPlan != planJson) {
            const std::string ownTransaction =
                "\"transactionId\":\"" + JsonEscape(plan.transactionId) + "\"";
            return Reject(plan, priorPlan.find(ownTransaction) ==
                    std::string::npos
                ? LayoutVerdict::TRANSACTION_CONFLICT
                : LayoutVerdict::DATA_INCONSISTENT);
        }
    } else {
        const int readPlanError = errno;
        if (readPlanError != ENOENT) {
            return RejectErrno(plan, "plan-read", readPlanError);
        }
        if (!WriteDurableFileAt(generation.Get(),
                ".file-plan.v1.tmp." + plan.transactionId,
                "file-plan.v1.json", planJson)) {
            return RejectErrno(plan, "plan-write", errno);
        }
    }

    const LayoutFaultDecision afterPlan =
        Invoke(faultInjector, LayoutFaultPhase::AFTER_PLAN_DURABLE);
    if (afterPlan != LayoutFaultDecision::NONE) {
        return Reject(plan, FaultVerdict(afterPlan));
    }

    PackageLayoutReceiptV1 finalized = BaseReceipt(plan);
    finalized.verdict = LayoutVerdict::FINALIZED;
    finalized.terminalState = "FINALIZED";
    finalized.baseCode.path = canonicalRootPath + "/" + userDirectory + "/" +
        plan.packageName + "/" + generationName + "/base.apk";
    finalized.baseCode.sha256 = verified.artifactSha256;
    finalized.baseCode.byteLength = verified.byteLength;
    const std::string receiptJson = SerializeReceipt(finalized);

    std::string existingReceipt;
    errno = 0;
    if (ReadSmallFileAt(generation.Get(), "file-receipt.v1.json",
            &existingReceipt)) {
        if (existingReceipt != receiptJson) {
            return Reject(plan, LayoutVerdict::DATA_INCONSISTENT);
        }
        ScopedFd existing(openat(generation.Get(), "base.apk",
            O_RDONLY | O_CLOEXEC | O_NOFOLLOW));
        if (existing.Get() < 0) {
            return RejectErrno(plan, "replay-base-open", errno);
        }
        struct stat existingStatus {};
        std::vector<uint8_t> existingBytes;
        if (fstat(existing.Get(), &existingStatus) != 0 ||
            !S_ISREG(existingStatus.st_mode) ||
            existingStatus.st_size < 0 ||
            !ReadAllAt(existing.Get(),
                static_cast<uint64_t>(existingStatus.st_size), &existingBytes) ||
            existingBytes.size() != verified.byteLength ||
            Sha256Hex(existingBytes.data(), existingBytes.size()) !=
                verified.artifactSha256) {
            return Reject(plan, LayoutVerdict::DATA_INCONSISTENT);
        }
        return finalized;
    } else {
        const int readReceiptError = errno;
        if (readReceiptError != ENOENT) {
            return RejectErrno(plan, "receipt-read", readReceiptError);
        }
    }

    struct stat inputBefore {};
    std::vector<uint8_t> inputBytes;
    if (fstat(artifactFd, &inputBefore) != 0 ||
        !S_ISREG(inputBefore.st_mode) || inputBefore.st_size < 0 ||
        static_cast<uint64_t>(inputBefore.st_size) != verified.byteLength ||
        !ReadAllAt(artifactFd, verified.byteLength, &inputBytes) ||
        Sha256Hex(inputBytes.data(), inputBytes.size()) !=
            verified.artifactSha256) {
        return Reject(plan, LayoutVerdict::VERIFIED_RECEIPT_MISMATCH);
    }

    const std::string temporaryName = ".base.apk.stage." + plan.transactionId;
    unlinkat(generation.Get(), temporaryName.c_str(), 0);
    ScopedFd temporary(openat(generation.Get(), temporaryName.c_str(),
        O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, kFileMode));
    if (temporary.Get() < 0) return RejectErrno(plan, "staging-open", errno);

    const LayoutFaultDecision duringCopy =
        Invoke(faultInjector, LayoutFaultPhase::DURING_COPY);
    if (duringCopy != LayoutFaultDecision::NONE) {
        unlinkat(generation.Get(), temporaryName.c_str(), 0);
        return Reject(plan, FaultVerdict(duringCopy));
    }
    if (!WriteAll(temporary.Get(), inputBytes.data(), inputBytes.size())) {
        const int saved = errno;
        unlinkat(generation.Get(), temporaryName.c_str(), 0);
        return RejectErrno(plan, "staging-write", saved);
    }
    if (fsync(temporary.Get()) != 0) {
        const int saved = errno;
        unlinkat(generation.Get(), temporaryName.c_str(), 0);
        return RejectErrno(plan, "staging-fsync", saved);
    }
    const LayoutFaultDecision afterFileFsync =
        Invoke(faultInjector, LayoutFaultPhase::AFTER_FILE_FSYNC);
    if (afterFileFsync != LayoutFaultDecision::NONE) {
        unlinkat(generation.Get(), temporaryName.c_str(), 0);
        return Reject(plan, FaultVerdict(afterFileFsync));
    }
    const LayoutFaultDecision beforeRename =
        Invoke(faultInjector, LayoutFaultPhase::BEFORE_RENAME);
    if (beforeRename != LayoutFaultDecision::NONE) {
        unlinkat(generation.Get(), temporaryName.c_str(), 0);
        return Reject(plan, FaultVerdict(beforeRename));
    }
    if (renameat(generation.Get(), temporaryName.c_str(),
            generation.Get(), "base.apk") != 0) {
        const int saved = errno;
        unlinkat(generation.Get(), temporaryName.c_str(), 0);
        return RejectErrno(plan, "staging-rename", saved);
    }
    if (fsync(generation.Get()) != 0) {
        return RejectErrno(plan, "generation-fsync", errno);
    }

    const LayoutFaultDecision afterRename =
        Invoke(faultInjector, LayoutFaultPhase::AFTER_RENAME);
    if (afterRename != LayoutFaultDecision::NONE) {
        return Reject(plan, FaultVerdict(afterRename));
    }
    const LayoutFaultDecision beforeReadback =
        Invoke(faultInjector, LayoutFaultPhase::BEFORE_READBACK);
    if (beforeReadback != LayoutFaultDecision::NONE) {
        return Reject(plan, FaultVerdict(beforeReadback));
    }

    ScopedFd readback(openat(generation.Get(), "base.apk",
        O_RDONLY | O_CLOEXEC | O_NOFOLLOW));
    struct stat outputStatus {};
    std::vector<uint8_t> outputBytes;
    if (readback.Get() < 0 || fstat(readback.Get(), &outputStatus) != 0) {
        return RejectErrno(plan, "readback-open-stat", errno);
    }
    if (!S_ISREG(outputStatus.st_mode) || outputStatus.st_size < 0) {
        return Reject(plan, LayoutVerdict::DATA_INCONSISTENT);
    }
    if (!ReadAllAt(readback.Get(), static_cast<uint64_t>(outputStatus.st_size),
            &outputBytes)) {
        return RejectErrno(plan, "readback-read", errno);
    }
    struct stat inputAfter {};
    if (fstat(artifactFd, &inputAfter) != 0 ||
        inputBefore.st_dev != inputAfter.st_dev ||
        inputBefore.st_ino != inputAfter.st_ino ||
        inputBefore.st_size != inputAfter.st_size ||
        outputBytes.size() != verified.byteLength ||
        Sha256Hex(outputBytes.data(), outputBytes.size()) !=
            verified.artifactSha256) {
        return Reject(plan, LayoutVerdict::DATA_INCONSISTENT);
    }

    if (!WriteDurableFileAt(generation.Get(),
            ".file-receipt.v1.tmp." + plan.transactionId,
            "file-receipt.v1.json", receiptJson)) {
        return RejectErrno(plan, "receipt-write", errno);
    }
    const LayoutFaultDecision afterReceipt =
        Invoke(faultInjector, LayoutFaultPhase::AFTER_RECEIPT_DURABLE);
    if (afterReceipt != LayoutFaultDecision::NONE) {
        return Reject(plan, FaultVerdict(afterReceipt));
    }
    return finalized;
}

}  // namespace oh_adapter::package_layout
