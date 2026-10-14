#include "resource_projection_v1.h"

#include "sha256.h"

#include <cerrno>
#include <climits>
#include <cstddef>
#include <cstring>
#include <fcntl.h>
#include <limits>
#include <mutex>
#include <sstream>
#include <string_view>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>
#include <utility>
#include <vector>

namespace oh_adapter::resource_projection {
namespace {

constexpr mode_t kDirectoryMode = 0700;
constexpr mode_t kFileMode = 0600;
constexpr size_t kMaxMetadataBytes = 256 * 1024;
std::mutex gProjectionProcessMutex;

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

std::string Hex(const uint8_t* bytes, size_t length)
{
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(length * 2, '0');
    for (size_t index = 0; index < length; ++index) {
        result[index * 2] = kHex[bytes[index] >> 4];
        result[index * 2 + 1] = kHex[bytes[index] & 0x0f];
    }
    return result;
}

std::string Sha256Hex(const uint8_t* bytes, size_t length)
{
    unsigned char digest[32]{};
    sha256(bytes, length, digest);
    return Hex(digest, sizeof(digest));
}

std::string Sha256Hex(std::string_view value)
{
    return Sha256Hex(reinterpret_cast<const uint8_t*>(value.data()),
        value.size());
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

bool ReadAllAt(int fd, size_t maximum, std::vector<uint8_t>* bytes)
{
    struct stat status {};
    if (bytes == nullptr || fstat(fd, &status) != 0 ||
        !S_ISREG(status.st_mode) || status.st_size < 0 ||
        static_cast<uint64_t>(status.st_size) > maximum) {
        errno = EIO;
        return false;
    }
    bytes->assign(static_cast<size_t>(status.st_size), 0);
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
    return true;
}

bool ReadSmallFileAt(int directoryFd, const char* name, std::string* value)
{
    ScopedFd file(openat(directoryFd, name, O_RDONLY | O_CLOEXEC | O_NOFOLLOW));
    if (file.Get() < 0) return false;
    std::vector<uint8_t> bytes;
    if (!ReadAllAt(file.Get(), kMaxMetadataBytes, &bytes)) return false;
    value->assign(bytes.begin(), bytes.end());
    return true;
}

bool WriteDurableFileAt(int directoryFd, const std::string& temporaryName,
    const std::string& finalName, std::string_view value)
{
    unlinkat(directoryFd, temporaryName.c_str(), 0);
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

ResourceProjectionVerdict ErrnoVerdict(int error)
{
    if (error == ELOOP) return ResourceProjectionVerdict::SYMLINK_ESCAPE;
    if (error == EACCES || error == EPERM || error == EROFS) {
        return ResourceProjectionVerdict::PERMISSION_DENIED;
    }
    if (error == ENOSPC || error == EDQUOT || error == EFBIG) {
        return ResourceProjectionVerdict::NO_SPACE;
    }
    return ResourceProjectionVerdict::IO_ERROR;
}

ResourceProjectionVerdict FaultVerdict(
    ResourceProjectionFaultDecision decision)
{
    switch (decision) {
        case ResourceProjectionFaultDecision::FAIL_NO_SPACE:
            return ResourceProjectionVerdict::NO_SPACE;
        case ResourceProjectionFaultDecision::FAIL_PERMISSION:
            return ResourceProjectionVerdict::PERMISSION_DENIED;
        case ResourceProjectionFaultDecision::INTERRUPT:
            return ResourceProjectionVerdict::INTERRUPTED;
        case ResourceProjectionFaultDecision::FAIL_IO:
            return ResourceProjectionVerdict::IO_ERROR;
        case ResourceProjectionFaultDecision::CORRUPT_PAYLOAD:
            return ResourceProjectionVerdict::DATA_INCONSISTENT;
        case ResourceProjectionFaultDecision::NONE: break;
    }
    return ResourceProjectionVerdict::IO_ERROR;
}

ResourceProjectionFaultDecision Invoke(
    ResourceProjectionFaultInjector* injector,
    ResourceProjectionFaultPhase phase)
{
    return injector == nullptr
        ? ResourceProjectionFaultDecision::NONE
        : injector->At(phase);
}

ResourceProjectionReceiptV1 BaseReceipt(
    const ResourceProjectionRequestV1& request)
{
    ResourceProjectionReceiptV1 receipt;
    receipt.requestId = request.requestId;
    receipt.transactionId = request.transactionId;
    receipt.packageName = request.packageName;
    receipt.userId = request.userId;
    receipt.generation = request.generation;
    receipt.canonicalDigest = request.canonicalDigest;
    receipt.buildPolicyVersion = request.buildPolicyVersion;
    receipt.state = "NONE";
    return receipt;
}

ResourceProjectionReceiptV1 Reject(const ResourceProjectionRequestV1& request,
    ResourceProjectionVerdict verdict, std::string reason)
{
    ResourceProjectionReceiptV1 receipt = BaseReceipt(request);
    receipt.verdict = verdict;
    receipt.reason = std::move(reason);
    receipt.state =
        verdict == ResourceProjectionVerdict::INTERRUPTED
        ? "PREPARED"
        : "NONE";
    return receipt;
}

ResourceProjectionReceiptV1 RejectErrno(
    const ResourceProjectionRequestV1& request,
    const char* stage, int error)
{
    return Reject(request, ErrnoVerdict(error),
        std::string(stage) + ":errno-" + std::to_string(error));
}

std::string SerializePlan(const ResourceProjectionRequestV1& request,
    std::string_view payloadKind, std::string_view inputDigest,
    std::string_view iconDigest)
{
    std::ostringstream output;
    output << "{\"schemaVersion\":1,\"requestId\":\""
           << JsonEscape(request.requestId) << "\",\"transactionId\":\""
           << JsonEscape(request.transactionId) << "\",\"callerScopeDigest\":\""
           << JsonEscape(request.callerScopeDigest) << "\",\"packageName\":\""
           << JsonEscape(request.packageName) << "\",\"userId\":"
           << request.userId << ",\"generation\":" << request.generation
           << ",\"canonicalDigest\":\"" << request.canonicalDigest
           << "\",\"buildPolicyVersion\":\""
           << JsonEscape(request.buildPolicyVersion)
           << "\",\"presentationTarget\":\""
           << JsonEscape(request.presentationTarget)
           << "\",\"layoutArtifactSetDigest\":\""
           << request.layoutReceipt.artifactSetDigest
           << "\",\"layoutBaseSha256\":\""
           << request.layoutReceipt.baseCode.sha256
           << "\",\"presentationStatus\":\""
           << ResourceProjectionBuilderV1::PresentationStatusName(
                  request.resourceFacts.presentationStatus)
           << "\",\"payloadKind\":\"" << payloadKind
           << "\",\"resourceInputDigest\":\"" << inputDigest
           << "\",\"componentName\":\""
           << JsonEscape(request.resourceFacts.componentName)
           << "\",\"configurationHash\":\""
           << JsonEscape(request.resourceFacts.configurationHash)
           << "\",\"labelHex\":\""
           << Hex(reinterpret_cast<const uint8_t*>(
                      request.resourceFacts.label.data()),
                  request.resourceFacts.label.size())
           << "\",\"iconContentType\":\""
           << JsonEscape(request.resourceFacts.iconContentType)
           << "\",\"iconDigest\":\"" << iconDigest
           << "\",\"sourceArtifactSha256\":\""
           << request.resourceFacts.sourceArtifactSha256 << "\"}\n";
    return output.str();
}

std::string SerializePayload(const ResourceProjectionRequestV1& request,
    std::string_view payloadKind, std::string_view inputDigest,
    std::string_view iconDigest)
{
    std::ostringstream output;
    output << "ResourceProjectionPayloadV1\n"
           << "packageName=" << request.packageName << "\n"
           << "generation=" << request.generation << "\n"
           << "payloadKind=" << payloadKind << "\n"
           << "canonicalDigest=" << request.canonicalDigest << "\n"
           << "resourceInputDigest=" << inputDigest << "\n"
           << "artifactSetDigest="
           << request.layoutReceipt.artifactSetDigest << "\n"
           << "sourceArtifactSha256="
           << request.resourceFacts.sourceArtifactSha256 << "\n"
           << "componentNameHex="
           << Hex(reinterpret_cast<const uint8_t*>(
                      request.resourceFacts.componentName.data()),
                  request.resourceFacts.componentName.size()) << "\n"
           << "configurationHash="
           << request.resourceFacts.configurationHash << "\n"
           << "labelHex="
           << Hex(reinterpret_cast<const uint8_t*>(
                      request.resourceFacts.label.data()),
                  request.resourceFacts.label.size()) << "\n"
           << "iconContentTypeHex="
           << Hex(reinterpret_cast<const uint8_t*>(
                      request.resourceFacts.iconContentType.data()),
                  request.resourceFacts.iconContentType.size()) << "\n"
           << "iconDigest=" << iconDigest << "\n"
           << "iconHex="
           << Hex(request.resourceFacts.iconBytes.data(),
                  request.resourceFacts.iconBytes.size()) << "\n";
    return output.str();
}

std::string SerializeRuntime(const ResourceProjectionReceiptV1& receipt,
    std::string_view state)
{
    std::ostringstream output;
    output << "{\"schemaVersion\":1,\"packageName\":\""
           << JsonEscape(receipt.packageName) << "\",\"generation\":"
           << receipt.generation << ",\"payloadKind\":\""
           << receipt.payloadKind << "\",\"resourceInputDigest\":\""
           << receipt.resourceInputDigest
           << "\",\"resourcePayloadDigest\":\""
           << receipt.resourcePayloadDigest << "\",\"canonicalDigest\":\""
           << receipt.canonicalDigest << "\",\"buildPolicyVersion\":\""
           << JsonEscape(receipt.buildPolicyVersion)
           << "\",\"state\":\"" << state << "\"}\n";
    return output.str();
}

bool PlanOwnsCleanupObligation(std::string_view plan,
    const ResourceCleanupObligationV1& obligation)
{
    const auto stringMember = [&](std::string_view name,
                                  const std::string& value) {
        const std::string token = "\"" + std::string(name) + "\":\"" +
            JsonEscape(value) + "\"";
        return plan.find(token + ",") != std::string_view::npos ||
            plan.find(token + "}") != std::string_view::npos;
    };
    const auto unsignedMember = [&](std::string_view name, uint64_t value) {
        const std::string token = "\"" + std::string(name) + "\":" +
            std::to_string(value);
        return plan.find(token + ",") != std::string_view::npos ||
            plan.find(token + "}") != std::string_view::npos;
    };
    return stringMember("requestId", obligation.requestId) &&
        stringMember("transactionId", obligation.transactionId) &&
        stringMember("callerScopeDigest", obligation.callerScopeDigest) &&
        stringMember("packageName", obligation.packageName) &&
        unsignedMember("userId", obligation.userId) &&
        unsignedMember("generation", obligation.generation) &&
        stringMember("canonicalDigest", obligation.canonicalDigest);
}

void RemoveProjectionFiles(int generationFd)
{
    unlinkat(generationFd, "resource.payload", 0);
    unlinkat(generationFd, "resource-runtime.v1.json", 0);
    unlinkat(generationFd, "resource-receipt.v1.json", 0);
}

bool ValidateLayoutReceipt(const ResourceProjectionRequestV1& request)
{
    const auto& layout = request.layoutReceipt;
    return layout.schemaVersion == 1 && layout.actionId == "Fn01.A07" &&
        layout.verdict ==
            oh_adapter::package_layout::LayoutVerdict::FINALIZED &&
        layout.terminalState == "FINALIZED" &&
        layout.requestId == request.requestId &&
        layout.transactionId == request.transactionId &&
        layout.packageName == request.packageName &&
        layout.userId == request.userId &&
        layout.generation == request.generation &&
        IsLowerHexDigest(layout.artifactSetDigest) &&
        IsLowerHexDigest(layout.baseCode.sha256) &&
        layout.baseCode.byteLength > 0 && !layout.baseCode.path.empty() &&
        layout.baseCode.sha256 ==
            request.resourceFacts.sourceArtifactSha256;
}

}  // namespace

ResourceProjectionBuilderV1::ResourceProjectionBuilderV1(
    std::string managedRoot, ResourceProjectionPolicyV1 policy)
    : managedRoot_(std::move(managedRoot)), policy_(std::move(policy))
{
}

const char* ResourceProjectionBuilderV1::VerdictName(
    ResourceProjectionVerdict verdict)
{
    switch (verdict) {
        case ResourceProjectionVerdict::READY: return "READY";
        case ResourceProjectionVerdict::CLEANED: return "CLEANED";
        case ResourceProjectionVerdict::INVALID_REQUEST:
            return "INVALID_REQUEST";
        case ResourceProjectionVerdict::NOT_SUPPORTED_USER:
            return "NOT_SUPPORTED_USER";
        case ResourceProjectionVerdict::NOT_SUPPORTED_TARGET:
            return "NOT_SUPPORTED_TARGET";
        case ResourceProjectionVerdict::LAYOUT_RECEIPT_MISMATCH:
            return "LAYOUT_RECEIPT_MISMATCH";
        case ResourceProjectionVerdict::CALLER_SCOPE_MISMATCH:
            return "CALLER_SCOPE_MISMATCH";
        case ResourceProjectionVerdict::RESOURCE_NOT_FOUND:
            return "RESOURCE_NOT_FOUND";
        case ResourceProjectionVerdict::UNSUPPORTED_CONFIGURATION:
            return "UNSUPPORTED_CONFIGURATION";
        case ResourceProjectionVerdict::INVALID_RESOURCE_PAYLOAD:
            return "INVALID_RESOURCE_PAYLOAD";
        case ResourceProjectionVerdict::TRANSACTION_CONFLICT:
            return "TRANSACTION_CONFLICT";
        case ResourceProjectionVerdict::SYMLINK_ESCAPE:
            return "SYMLINK_ESCAPE";
        case ResourceProjectionVerdict::PERMISSION_DENIED:
            return "PERMISSION_DENIED";
        case ResourceProjectionVerdict::NO_SPACE: return "NO_SPACE";
        case ResourceProjectionVerdict::IO_ERROR: return "IO_ERROR";
        case ResourceProjectionVerdict::DATA_INCONSISTENT:
            return "DATA_INCONSISTENT";
        case ResourceProjectionVerdict::INTERRUPTED: return "INTERRUPTED";
    }
    return "DATA_INCONSISTENT";
}

const char* ResourceProjectionBuilderV1::PresentationStatusName(
    ResourcePresentationStatus status)
{
    switch (status) {
        case ResourcePresentationStatus::RESOLVED: return "RESOLVED";
        case ResourcePresentationStatus::NONE: return "NONE";
        case ResourcePresentationStatus::MISSING: return "MISSING";
        case ResourcePresentationStatus::UNSUPPORTED_CONFIGURATION:
            return "UNSUPPORTED_CONFIGURATION";
        case ResourcePresentationStatus::INVALID: return "INVALID";
    }
    return "INVALID";
}

std::string ResourceProjectionBuilderV1::SerializeReceipt(
    const ResourceProjectionReceiptV1& receipt)
{
    std::ostringstream output;
    output << "{\"schemaVersion\":1,\"actionId\":\"Fn01.A08\""
           << ",\"requestId\":\"" << JsonEscape(receipt.requestId)
           << "\",\"transactionId\":\"" << JsonEscape(receipt.transactionId)
           << "\",\"packageName\":\"" << JsonEscape(receipt.packageName)
           << "\",\"userId\":" << receipt.userId
           << ",\"generation\":" << receipt.generation
           << ",\"payloadKind\":\"" << receipt.payloadKind
           << "\",\"resourceInputDigest\":\""
           << receipt.resourceInputDigest
           << "\",\"resourcePayloadDigest\":\""
           << receipt.resourcePayloadDigest
           << "\",\"canonicalDigest\":\"" << receipt.canonicalDigest
           << "\",\"buildPolicyVersion\":\""
           << JsonEscape(receipt.buildPolicyVersion)
           << "\",\"state\":\"" << receipt.state
           << "\",\"payloadPath\":\"" << JsonEscape(receipt.payloadPath)
           << "\",\"componentName\":\""
           << JsonEscape(receipt.componentName)
           << "\",\"configurationHash\":\""
           << JsonEscape(receipt.configurationHash)
           << "\",\"label\":\"" << JsonEscape(receipt.label)
           << "\",\"verdict\":\"" << VerdictName(receipt.verdict)
           << "\",\"reason\":\"" << JsonEscape(receipt.reason) << "\"}\n";
    return output.str();
}

ResourceProjectionReceiptV1 ResourceProjectionBuilderV1::Build(
    const ResourceProjectionRequestV1& request,
    ResourceProjectionFaultInjector* faultInjector)
{
    if (request.schemaVersion != 1 || request.resourceFacts.schemaVersion != 1 ||
        policy_.schemaVersion != 1 || request.requestId.empty() ||
        !IsSafeIdentifier(request.transactionId, false) ||
        !IsSafeIdentifier(request.packageName, true) ||
        request.generation == 0 ||
        !IsLowerHexDigest(request.canonicalDigest) ||
        request.buildPolicyVersion.empty() ||
        request.buildPolicyVersion != policy_.policyVersion ||
        policy_.expectedCallerScopeDigest.empty()) {
        return Reject(request, ResourceProjectionVerdict::INVALID_REQUEST,
            "request-or-policy-schema");
    }
    if (request.userId != 0) {
        return Reject(request, ResourceProjectionVerdict::NOT_SUPPORTED_USER,
            "v1-primary-user-only");
    }
    if (request.presentationTarget != "LAUNCHER_PRESENTATION") {
        return Reject(request, ResourceProjectionVerdict::NOT_SUPPORTED_TARGET,
            "v1-launcher-presentation-only");
    }
    if (request.callerScopeDigest != policy_.expectedCallerScopeDigest) {
        return Reject(request,
            ResourceProjectionVerdict::CALLER_SCOPE_MISMATCH,
            "caller-scope-digest");
    }
    if (!ValidateLayoutReceipt(request)) {
        return Reject(request,
            ResourceProjectionVerdict::LAYOUT_RECEIPT_MISMATCH,
            "Fn01.A07-finalized-receipt");
    }

    const ResourceFactsV1& facts = request.resourceFacts;
    if (facts.presentationStatus == ResourcePresentationStatus::MISSING) {
        return Reject(request, ResourceProjectionVerdict::RESOURCE_NOT_FOUND,
            "typed-launcher-resource-missing");
    }
    if (facts.presentationStatus ==
        ResourcePresentationStatus::UNSUPPORTED_CONFIGURATION) {
        return Reject(request,
            ResourceProjectionVerdict::UNSUPPORTED_CONFIGURATION,
            "typed-configuration-unsupported");
    }
    if (facts.presentationStatus == ResourcePresentationStatus::INVALID) {
        return Reject(request,
            ResourceProjectionVerdict::INVALID_RESOURCE_PAYLOAD,
            "typed-resource-facts-invalid");
    }
    if (facts.presentationStatus == ResourcePresentationStatus::RESOLVED &&
        (facts.componentName.empty() || facts.configurationHash.empty() ||
         facts.label.empty() || facts.iconBytes.empty() ||
         facts.iconContentType.empty())) {
        return Reject(request,
            ResourceProjectionVerdict::INVALID_RESOURCE_PAYLOAD,
            "resolved-presentation-incomplete");
    }
    if (facts.presentationStatus == ResourcePresentationStatus::NONE &&
        (!facts.componentName.empty() || !facts.configurationHash.empty() ||
         !facts.label.empty() || !facts.iconBytes.empty() ||
         !facts.iconContentType.empty())) {
        return Reject(request,
            ResourceProjectionVerdict::INVALID_RESOURCE_PAYLOAD,
            "empty-presentation-has-placeholder-data");
    }
    if (facts.label.size() > policy_.maxLabelBytes ||
        facts.iconBytes.size() > policy_.maxIconBytes) {
        return Reject(request,
            ResourceProjectionVerdict::INVALID_RESOURCE_PAYLOAD,
            "resource-policy-limit");
    }
    if (!IsLowerHexDigest(facts.sourceArtifactSha256)) {
        return Reject(request,
            ResourceProjectionVerdict::INVALID_RESOURCE_PAYLOAD,
            "source-artifact-digest");
    }

    // flock supplies cross-process exclusion.  Some BSD hosts treat flock
    // ownership as process-scoped, so an in-process mutex is also required to
    // prevent two worker threads from entering the generation transaction.
    std::lock_guard<std::mutex> processLock(gProjectionProcessMutex);

    const std::string payloadKind =
        facts.presentationStatus == ResourcePresentationStatus::NONE
        ? "EMPTY"
        : "MATERIALIZED";
    const std::string iconDigest =
        Sha256Hex(facts.iconBytes.data(), facts.iconBytes.size());
    std::ostringstream inputIdentity;
    inputIdentity << "ResourceProjectionInputV1\n"
                  << request.packageName << '\n' << request.userId << '\n'
                  << request.generation << '\n' << request.canonicalDigest
                  << '\n' << request.buildPolicyVersion << '\n'
                  << request.presentationTarget << '\n'
                  << request.layoutReceipt.artifactSetDigest << '\n'
                  << request.layoutReceipt.baseCode.sha256 << '\n'
                  << PresentationStatusName(facts.presentationStatus) << '\n'
                  << facts.componentName.size() << ':' << facts.componentName
                  << '\n' << facts.configurationHash.size() << ':'
                  << facts.configurationHash << '\n' << facts.label.size()
                  << ':' << facts.label << '\n' << facts.iconContentType.size()
                  << ':' << facts.iconContentType << '\n' << iconDigest;
    const std::string inputDigest = Sha256Hex(inputIdentity.str());
    const std::string payload =
        SerializePayload(request, payloadKind, inputDigest, iconDigest);
    const std::string payloadDigest = Sha256Hex(payload);

    ResourceProjectionReceiptV1 ready = BaseReceipt(request);
    ready.payloadKind = payloadKind;
    ready.resourceInputDigest = inputDigest;
    ready.resourcePayloadDigest = payloadDigest;
    ready.state = "READY";
    ready.componentName = facts.componentName;
    ready.configurationHash = facts.configurationHash;
    ready.label = facts.label;
    ready.verdict = ResourceProjectionVerdict::READY;

    struct stat rootStatus {};
    if (lstat(managedRoot_.c_str(), &rootStatus) != 0) {
        return RejectErrno(request, "managed-root-lstat", errno);
    }
    if (S_ISLNK(rootStatus.st_mode)) {
        return Reject(request, ResourceProjectionVerdict::SYMLINK_ESCAPE,
            "managed-root-symlink");
    }
    if (!S_ISDIR(rootStatus.st_mode)) {
        return Reject(request, ResourceProjectionVerdict::INVALID_REQUEST,
            "managed-root-not-directory");
    }
    ScopedFd root(open(managedRoot_.c_str(),
        O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW));
    if (root.Get() < 0) return RejectErrno(request, "managed-root-open", errno);
    char canonicalRoot[PATH_MAX]{};
    if (realpath(managedRoot_.c_str(), canonicalRoot) == nullptr) {
        return RejectErrno(request, "managed-root-realpath", errno);
    }

    const std::string userName = "u" + std::to_string(request.userId);
    ScopedFd user(OpenOrCreateDirectoryAt(root.Get(), userName));
    if (user.Get() < 0) return RejectErrno(request, "user-directory", errno);
    ScopedFd package(OpenOrCreateDirectoryAt(user.Get(), request.packageName));
    if (package.Get() < 0) {
        return RejectErrno(request, "package-directory", errno);
    }
    const std::string generationName =
        "g" + std::to_string(request.generation);
    ScopedFd generation(
        OpenOrCreateDirectoryAt(package.Get(), generationName));
    if (generation.Get() < 0) {
        return RejectErrno(request, "generation-directory", errno);
    }
    ScopedFd lock(openat(generation.Get(), ".resource.lock",
        O_RDWR | O_CREAT | O_CLOEXEC | O_NOFOLLOW, kFileMode));
    if (lock.Get() < 0) return RejectErrno(request, "lock-open", errno);
    while (flock(lock.Get(), LOCK_EX) != 0) {
        if (errno == EINTR) continue;
        return RejectErrno(request, "lock-acquire", errno);
    }
    ScopedFileLock projectionLock(lock.Get());

    ready.payloadPath = std::string(canonicalRoot) + "/" + userName + "/" +
        request.packageName + "/" + generationName + "/resource.payload";
    const std::string plan =
        SerializePlan(request, payloadKind, inputDigest, iconDigest);
    std::string priorPlan;
    errno = 0;
    if (ReadSmallFileAt(generation.Get(), "resource-plan.v1.json",
            &priorPlan)) {
        if (priorPlan != plan) {
            const std::string ownTransaction =
                "\"transactionId\":\"" +
                JsonEscape(request.transactionId) + "\"";
            return Reject(request,
                priorPlan.find(ownTransaction) == std::string::npos
                    ? ResourceProjectionVerdict::TRANSACTION_CONFLICT
                    : ResourceProjectionVerdict::DATA_INCONSISTENT,
                "generation-has-different-resource-plan");
        }
    } else {
        const int readError = errno;
        if (readError != ENOENT) {
            return RejectErrno(request, "plan-read", readError);
        }
        if (!WriteDurableFileAt(generation.Get(),
                ".resource-plan.tmp." + request.transactionId,
                "resource-plan.v1.json", plan)) {
            return RejectErrno(request, "plan-write", errno);
        }
    }

    const std::string preparedRuntime = SerializeRuntime(ready, "PREPARED");
    const std::string readyRuntime = SerializeRuntime(ready, "READY");
    std::string runtime;
    errno = 0;
    if (ReadSmallFileAt(generation.Get(), "resource-runtime.v1.json",
            &runtime)) {
        if (runtime == preparedRuntime) {
            RemoveProjectionFiles(generation.Get());
            if (fsync(generation.Get()) != 0) {
                return RejectErrno(request, "prepared-recovery", errno);
            }
        } else if (runtime != readyRuntime) {
            return Reject(request,
                ResourceProjectionVerdict::DATA_INCONSISTENT,
                "runtime-does-not-match-frozen-plan");
        }
    } else if (errno != ENOENT) {
        return RejectErrno(request, "runtime-read", errno);
    }

    if (runtime == readyRuntime) {
        ScopedFd existing(openat(generation.Get(), "resource.payload",
            O_RDONLY | O_CLOEXEC | O_NOFOLLOW));
        std::vector<uint8_t> existingBytes;
        if (existing.Get() < 0 ||
            !ReadAllAt(existing.Get(),
                payload.size(), &existingBytes) ||
            Sha256Hex(existingBytes.data(), existingBytes.size()) !=
                payloadDigest) {
            return Reject(request,
                ResourceProjectionVerdict::DATA_INCONSISTENT,
                "ready-payload-readback");
        }
        const std::string receiptJson = SerializeReceipt(ready);
        std::string priorReceipt;
        errno = 0;
        if (ReadSmallFileAt(generation.Get(), "resource-receipt.v1.json",
                &priorReceipt)) {
            if (priorReceipt != receiptJson) {
                return Reject(request,
                    ResourceProjectionVerdict::DATA_INCONSISTENT,
                    "ready-receipt-mismatch");
            }
        } else if (errno == ENOENT) {
            if (!WriteDurableFileAt(generation.Get(),
                    ".resource-receipt.tmp." + request.transactionId,
                    "resource-receipt.v1.json", receiptJson)) {
                return RejectErrno(request, "receipt-recovery-write", errno);
            }
        } else {
            return RejectErrno(request, "receipt-recovery-read", errno);
        }
        return ready;
    }

    if (!WriteDurableFileAt(generation.Get(),
            ".resource-runtime.tmp." + request.transactionId,
            "resource-runtime.v1.json", preparedRuntime)) {
        return RejectErrno(request, "prepared-write", errno);
    }
    const auto failAt = [&](ResourceProjectionFaultPhase phase,
                            bool payloadMayExist,
                            ResourceProjectionFaultDecision decision) {
        if (decision == ResourceProjectionFaultDecision::NONE) {
            ResourceProjectionReceiptV1 noFault;
            noFault.actionId.clear();
            return noFault;
        }
        if (decision == ResourceProjectionFaultDecision::CORRUPT_PAYLOAD) {
            if (phase != ResourceProjectionFaultPhase::BEFORE_READBACK) {
                return Reject(request,
                    ResourceProjectionVerdict::INVALID_REQUEST,
                    "corrupt-payload-fault-requires-before-readback");
            }
            ResourceProjectionReceiptV1 noFault;
            noFault.actionId.clear();
            return noFault;
        }
        if (decision != ResourceProjectionFaultDecision::INTERRUPT) {
            if (payloadMayExist) unlinkat(generation.Get(), "resource.payload", 0);
            unlinkat(generation.Get(), "resource-runtime.v1.json", 0);
            fsync(generation.Get());
        }
        ResourceProjectionReceiptV1 rejected =
            Reject(request, FaultVerdict(decision),
            std::string("fault:") + std::to_string(static_cast<int>(phase)));
        if (decision == ResourceProjectionFaultDecision::INTERRUPT &&
            (phase == ResourceProjectionFaultPhase::AFTER_READY_DURABLE ||
             phase == ResourceProjectionFaultPhase::BEFORE_READBACK ||
             phase == ResourceProjectionFaultPhase::AFTER_RECEIPT_DURABLE)) {
            rejected.state = "READY";
        }
        return rejected;
    };
    ResourceProjectionReceiptV1 fault =
        failAt(ResourceProjectionFaultPhase::AFTER_PREPARED_DURABLE, false,
            Invoke(faultInjector,
                ResourceProjectionFaultPhase::AFTER_PREPARED_DURABLE));
    if (!fault.actionId.empty()) return fault;

    const std::string temporaryName =
        ".resource.payload.stage." + request.transactionId;
    unlinkat(generation.Get(), temporaryName.c_str(), 0);
    ScopedFd temporary(openat(generation.Get(), temporaryName.c_str(),
        O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, kFileMode));
    if (temporary.Get() < 0) {
        unlinkat(generation.Get(), "resource-runtime.v1.json", 0);
        return RejectErrno(request, "payload-stage-open", errno);
    }
    fault = failAt(ResourceProjectionFaultPhase::DURING_PAYLOAD_WRITE, false,
        Invoke(faultInjector,
            ResourceProjectionFaultPhase::DURING_PAYLOAD_WRITE));
    if (!fault.actionId.empty()) {
        unlinkat(generation.Get(), temporaryName.c_str(), 0);
        return fault;
    }
    if (!WriteAll(temporary.Get(),
            reinterpret_cast<const uint8_t*>(payload.data()), payload.size()) ||
        fsync(temporary.Get()) != 0) {
        const int saved = errno;
        unlinkat(generation.Get(), temporaryName.c_str(), 0);
        unlinkat(generation.Get(), "resource-runtime.v1.json", 0);
        return RejectErrno(request, "payload-stage-write", saved);
    }
    fault = failAt(ResourceProjectionFaultPhase::AFTER_PAYLOAD_FSYNC, false,
        Invoke(faultInjector,
            ResourceProjectionFaultPhase::AFTER_PAYLOAD_FSYNC));
    if (!fault.actionId.empty()) {
        unlinkat(generation.Get(), temporaryName.c_str(), 0);
        return fault;
    }
    if (renameat(generation.Get(), temporaryName.c_str(),
            generation.Get(), "resource.payload") != 0 ||
        fsync(generation.Get()) != 0) {
        const int saved = errno;
        unlinkat(generation.Get(), temporaryName.c_str(), 0);
        RemoveProjectionFiles(generation.Get());
        return RejectErrno(request, "payload-publish", saved);
    }
    fault = failAt(ResourceProjectionFaultPhase::BEFORE_READY_DURABLE, true,
        Invoke(faultInjector,
            ResourceProjectionFaultPhase::BEFORE_READY_DURABLE));
    if (!fault.actionId.empty()) return fault;

    if (!WriteDurableFileAt(generation.Get(),
            ".resource-runtime.tmp." + request.transactionId,
            "resource-runtime.v1.json", readyRuntime)) {
        const int saved = errno;
        RemoveProjectionFiles(generation.Get());
        return RejectErrno(request, "ready-write", saved);
    }
    fault = failAt(ResourceProjectionFaultPhase::AFTER_READY_DURABLE, true,
        Invoke(faultInjector,
            ResourceProjectionFaultPhase::AFTER_READY_DURABLE));
    if (!fault.actionId.empty()) return fault;
    const ResourceProjectionFaultDecision beforeReadback =
        Invoke(faultInjector, ResourceProjectionFaultPhase::BEFORE_READBACK);
    if (beforeReadback == ResourceProjectionFaultDecision::CORRUPT_PAYLOAD) {
        ScopedFd corrupt(openat(generation.Get(), "resource.payload",
            O_WRONLY | O_CLOEXEC | O_NOFOLLOW));
        const uint8_t corruptedByte = 0;
        if (corrupt.Get() < 0 ||
            pwrite(corrupt.Get(), &corruptedByte, 1, 0) != 1 ||
            fsync(corrupt.Get()) != 0) {
            RemoveProjectionFiles(generation.Get());
            return RejectErrno(request, "payload-corrupt-inject", errno);
        }
    }
    fault = failAt(ResourceProjectionFaultPhase::BEFORE_READBACK, true,
        beforeReadback);
    if (!fault.actionId.empty()) return fault;

    ScopedFd readback(openat(generation.Get(), "resource.payload",
        O_RDONLY | O_CLOEXEC | O_NOFOLLOW));
    std::vector<uint8_t> readbackBytes;
    if (readback.Get() < 0 ||
        !ReadAllAt(readback.Get(),
            payload.size(), &readbackBytes) ||
        Sha256Hex(readbackBytes.data(), readbackBytes.size()) != payloadDigest) {
        RemoveProjectionFiles(generation.Get());
        return Reject(request, ResourceProjectionVerdict::DATA_INCONSISTENT,
            "payload-readback-digest");
    }
    if (!WriteDurableFileAt(generation.Get(),
            ".resource-receipt.tmp." + request.transactionId,
            "resource-receipt.v1.json", SerializeReceipt(ready))) {
        return RejectErrno(request, "receipt-write", errno);
    }
    fault = failAt(ResourceProjectionFaultPhase::AFTER_RECEIPT_DURABLE, true,
        Invoke(faultInjector,
            ResourceProjectionFaultPhase::AFTER_RECEIPT_DURABLE));
    if (!fault.actionId.empty()) return fault;
    return ready;
}

ResourceProjectionReceiptV1 ResourceProjectionBuilderV1::Cleanup(
    const ResourceCleanupObligationV1& obligation)
{
    ResourceProjectionRequestV1 request;
    request.requestId = obligation.requestId;
    request.transactionId = obligation.transactionId;
    request.callerScopeDigest = obligation.callerScopeDigest;
    request.packageName = obligation.packageName;
    request.userId = obligation.userId;
    request.generation = obligation.generation;
    request.canonicalDigest = obligation.canonicalDigest;
    request.buildPolicyVersion = policy_.policyVersion;
    if (obligation.schemaVersion != 1 ||
        !IsSafeIdentifier(obligation.transactionId, false) ||
        obligation.requestId.empty() ||
        !IsSafeIdentifier(obligation.packageName, true) ||
        obligation.userId != 0 || obligation.generation == 0 ||
        !IsLowerHexDigest(obligation.canonicalDigest) ||
        !IsLowerHexDigest(obligation.resourcePayloadDigest) ||
        (obligation.cause != "ROLLBACK_BEFORE_P5" &&
         obligation.cause != "GENERATION_RETIREMENT")) {
        return Reject(request, ResourceProjectionVerdict::INVALID_REQUEST,
            "cleanup-obligation-invalid");
    }
    if (obligation.callerScopeDigest !=
        policy_.expectedCallerScopeDigest) {
        return Reject(request,
            ResourceProjectionVerdict::CALLER_SCOPE_MISMATCH,
            "cleanup-caller-scope-digest");
    }

    std::lock_guard<std::mutex> processLock(gProjectionProcessMutex);

    ScopedFd root(open(managedRoot_.c_str(),
        O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW));
    if (root.Get() < 0) return RejectErrno(request, "cleanup-root", errno);
    const std::string userName = "u" + std::to_string(obligation.userId);
    ScopedFd user(openat(root.Get(), userName.c_str(),
        O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW));
    if (user.Get() < 0) return RejectErrno(request, "cleanup-user", errno);
    ScopedFd package(openat(user.Get(), obligation.packageName.c_str(),
        O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW));
    if (package.Get() < 0) return RejectErrno(request, "cleanup-package", errno);
    const std::string generationName =
        "g" + std::to_string(obligation.generation);
    ScopedFd generation(openat(package.Get(), generationName.c_str(),
        O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW));
    if (generation.Get() < 0) {
        return RejectErrno(request, "cleanup-generation", errno);
    }
    ScopedFd lock(openat(generation.Get(), ".resource.lock",
        O_RDWR | O_CLOEXEC | O_NOFOLLOW));
    if (lock.Get() < 0) return RejectErrno(request, "cleanup-lock", errno);
    while (flock(lock.Get(), LOCK_EX) != 0) {
        if (errno == EINTR) continue;
        return RejectErrno(request, "cleanup-lock-acquire", errno);
    }
    ScopedFileLock cleanupLock(lock.Get());

    std::string plan;
    if (!ReadSmallFileAt(generation.Get(), "resource-plan.v1.json", &plan)) {
        return Reject(request, ResourceProjectionVerdict::DATA_INCONSISTENT,
            "cleanup-resource-plan-unavailable");
    }
    if (!PlanOwnsCleanupObligation(plan, obligation)) {
        return Reject(request,
            ResourceProjectionVerdict::TRANSACTION_CONFLICT,
            "cleanup-obligation-not-owned-by-current-resource-plan");
    }

    std::string runtime;
    if (!ReadSmallFileAt(generation.Get(), "resource-runtime.v1.json",
            &runtime) ||
        runtime.find("\"canonicalDigest\":\"" +
                obligation.canonicalDigest + "\"") == std::string::npos ||
        runtime.find("\"resourcePayloadDigest\":\"" +
                obligation.resourcePayloadDigest + "\"") ==
            std::string::npos) {
        return Reject(request, ResourceProjectionVerdict::DATA_INCONSISTENT,
            "cleanup-obligation-does-not-match-runtime");
    }
    RemoveProjectionFiles(generation.Get());
    unlinkat(generation.Get(), "resource-plan.v1.json", 0);
    if (fsync(generation.Get()) != 0) {
        return RejectErrno(request, "cleanup-fsync", errno);
    }

    ResourceProjectionReceiptV1 cleaned = BaseReceipt(request);
    cleaned.resourcePayloadDigest = obligation.resourcePayloadDigest;
    cleaned.state = "NONE";
    cleaned.verdict = ResourceProjectionVerdict::CLEANED;
    cleaned.reason = obligation.cause;
    const std::string cleanupName =
        "resource-cleanup-g" + std::to_string(obligation.generation) +
        "-" + obligation.transactionId + ".v1.json";
    if (!WriteDurableFileAt(package.Get(),
            "." + cleanupName + ".tmp", cleanupName,
            SerializeReceipt(cleaned))) {
        return RejectErrno(request, "cleanup-receipt-write", errno);
    }
    return cleaned;
}

}  // namespace oh_adapter::resource_projection
