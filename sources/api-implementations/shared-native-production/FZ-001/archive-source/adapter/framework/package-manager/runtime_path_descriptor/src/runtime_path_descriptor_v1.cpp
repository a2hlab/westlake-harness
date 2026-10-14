#include "runtime_path_descriptor_v1.h"

#include "sha256.h"

#include <algorithm>
#include <array>
#include <cerrno>
#include <climits>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <set>
#include <sstream>
#include <string>
#include <string_view>
#include <sys/stat.h>
#include <unistd.h>
#include <utility>
#include <vector>

namespace oh_adapter::runtime_path_descriptor {
namespace {

using package_transaction::HostProjectionState;
using package_transaction::PackageManagementReadV1;
using package_transaction::PublicationState;

constexpr uint16_t kElfMachineAarch64 = 183;
constexpr size_t kElfIdentityBytes = 20;
constexpr size_t kMaxRequestIdBytes = 128;
constexpr size_t kMaxPackageNameBytes = 255;
constexpr size_t kMaxRoots = 32;
constexpr size_t kMaxNativeLibraries = 256;
constexpr uint64_t kMaxReadbackBytes = 1024ULL * 1024ULL * 1024ULL;

bool IsLowerHexDigest(const std::string& value)
{
    if (value.size() != 64) return false;
    return std::all_of(value.begin(), value.end(), [](char character) {
        return (character >= '0' && character <= '9') ||
            (character >= 'a' && character <= 'f');
    });
}

std::string Sha256Hex(const std::vector<uint8_t>& bytes)
{
    unsigned char digest[32]{};
    sha256(bytes.data(), bytes.size(), digest);
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        result[index * 2] = kHex[digest[index] >> 4];
        result[index * 2 + 1] = kHex[digest[index] & 0x0f];
    }
    return result;
}

std::optional<std::string> CanonicalPath(const std::string& path)
{
    if (path.empty() || path.front() != '/') return std::nullopt;
    std::array<char, PATH_MAX> buffer{};
    if (realpath(path.c_str(), buffer.data()) == nullptr) return std::nullopt;
    return std::string(buffer.data());
}

bool IsWithin(const std::string& path, const std::string& root)
{
    if (path == root) return true;
    return path.size() > root.size() &&
        path.compare(0, root.size(), root) == 0 && path[root.size()] == '/';
}

bool IsWithinAny(const std::string& path,
    const std::vector<std::string>& roots)
{
    return std::any_of(roots.begin(), roots.end(),
        [&path](const std::string& root) { return IsWithin(path, root); });
}

bool ReadRegularFile(const std::string& path, std::vector<uint8_t>* bytes,
    uint64_t* byteLength)
{
    if (bytes == nullptr || byteLength == nullptr) return false;
    const int fd = open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return false;
    struct stat status {};
    if (fstat(fd, &status) != 0 || !S_ISREG(status.st_mode) ||
        status.st_size < 0 ||
        static_cast<uint64_t>(status.st_size) > kMaxReadbackBytes) {
        close(fd);
        return false;
    }
    std::vector<uint8_t> readback;
    readback.reserve(static_cast<size_t>(status.st_size));
    std::array<uint8_t, 8192> buffer{};
    while (true) {
        const ssize_t count = read(fd, buffer.data(), buffer.size());
        if (count == 0) break;
        if (count < 0) {
            if (errno == EINTR) continue;
            close(fd);
            return false;
        }
        readback.insert(readback.end(), buffer.begin(),
            buffer.begin() + count);
    }
    close(fd);
    if (readback.size() != static_cast<uint64_t>(status.st_size)) return false;
    *byteLength = readback.size();
    *bytes = std::move(readback);
    return true;
}

bool ReadDirectory(const std::string& path)
{
    const int fd = open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW |
        O_DIRECTORY);
    if (fd < 0) return false;
    struct stat status {};
    const bool valid = fstat(fd, &status) == 0 && S_ISDIR(status.st_mode);
    close(fd);
    return valid;
}

std::optional<uint16_t> ReadElfMachine(
    const std::vector<uint8_t>& bytes)
{
    if (bytes.size() < kElfIdentityBytes ||
        bytes[0] != 0x7f || bytes[1] != 'E' || bytes[2] != 'L' ||
        bytes[3] != 'F' || bytes[4] != 2 || bytes[5] != 1) {
        return std::nullopt;
    }
    return static_cast<uint16_t>(bytes[18]) |
        (static_cast<uint16_t>(bytes[19]) << 8);
}

RuntimePathResponseV1 Reject(const RuntimePathRequestV1& request,
    RuntimePathVerdict verdict)
{
    RuntimePathResponseV1 response;
    response.requestId = request.requestId;
    response.verdict = verdict;
    response.descriptor.reset();
    response.observations.clear();
    response.classLoaderCreated = false;
    return response;
}

bool IdentityMatches(const PackageManagementReadV1& state,
    const RuntimePathFactsV1& facts, const RuntimePathRequestV1& request)
{
    if (!state.canonical.has_value()) return false;
    const auto& canonical = *state.canonical;
    return facts.schemaVersion == 1 &&
        facts.packageName == request.packageName &&
        facts.userId == request.userId &&
        facts.generation == canonical.generation &&
        facts.canonicalDigest == canonical.canonicalDigest &&
        facts.artifactSetDigest == canonical.artifactSetDigest &&
        facts.abi == request.abi;
}

std::string JsonEscape(std::string_view value)
{
    std::ostringstream output;
    for (const unsigned char character : value) {
        switch (character) {
            case '"': output << "\\\""; break;
            case '\\': output << "\\\\"; break;
            case '\b': output << "\\b"; break;
            case '\f': output << "\\f"; break;
            case '\n': output << "\\n"; break;
            case '\r': output << "\\r"; break;
            case '\t': output << "\\t"; break;
            default:
                if (character < 0x20) {
                    static constexpr char kHex[] = "0123456789abcdef";
                    output << "\\u00" << kHex[character >> 4]
                           << kHex[character & 0x0f];
                } else {
                    output << character;
                }
        }
    }
    return output.str();
}

void AppendStringArray(std::ostringstream* output,
    const std::vector<std::string>& values)
{
    *output << "[";
    for (size_t index = 0; index < values.size(); ++index) {
        if (index != 0) *output << ",";
        *output << "\"" << JsonEscape(values[index]) << "\"";
    }
    *output << "]";
}

}  // namespace

RuntimePathDescriptorServiceV1::RuntimePathDescriptorServiceV1(
    package_transaction::FilePackageStore* store,
    const RuntimePathFactsProvider* factsProvider,
    RuntimePathFaultInjector* faultInjector)
    : store_(store), factsProvider_(factsProvider), faultInjector_(faultInjector)
{
}

RuntimePathResponseV1 RuntimePathDescriptorServiceV1::Query(
    const RuntimePathRequestV1& request) const
{
    if (request.schemaVersion != 1) {
        return Reject(request, RuntimePathVerdict::UNKNOWN_SCHEMA);
    }
    if (store_ == nullptr || factsProvider_ == nullptr ||
        faultInjector_ == nullptr || request.requestId.empty() ||
        request.packageName.empty() || request.expectedGeneration == 0 ||
        request.requestId.size() > kMaxRequestIdBytes ||
        request.packageName.size() > kMaxPackageNameBytes ||
        !IsLowerHexDigest(request.callerScopeDigest) ||
        (request.expectedCanonicalDigest.has_value() &&
            !IsLowerHexDigest(*request.expectedCanonicalDigest))) {
        return Reject(request, RuntimePathVerdict::INVALID_REQUEST);
    }
    if (!request.callerAuthorized) {
        return Reject(request, RuntimePathVerdict::NOT_AUTHORIZED);
    }
    if (request.userId != 0) {
        return Reject(request, RuntimePathVerdict::NOT_SUPPORTED_USER);
    }
    if (request.splitProfileRequested) {
        return Reject(request,
            RuntimePathVerdict::NOT_SUPPORTED_ARTIFACT_PROFILE);
    }
    if (request.abi != "arm64-v8a") {
        return Reject(request, RuntimePathVerdict::NOT_SUPPORTED_ABI);
    }

    PackageManagementReadV1 state;
    std::string readError;
    if (!store_->ReadPackageManagementState(
            request.userId, request.packageName, &state, &readError)) {
        return Reject(request, RuntimePathVerdict::PATH_READBACK_FAILED);
    }
    if (!state.canonical.has_value()) {
        return Reject(request, RuntimePathVerdict::PACKAGE_NOT_FOUND);
    }
    const auto& canonical = *state.canonical;
    if (request.expectedGeneration != canonical.generation) {
        return Reject(request, RuntimePathVerdict::STALE_GENERATION);
    }
    if (request.expectedCanonicalDigest.has_value() &&
        *request.expectedCanonicalDigest != canonical.canonicalDigest) {
        return Reject(request, RuntimePathVerdict::STALE_GENERATION);
    }
    if (state.removing || !state.projection.has_value() ||
        !state.publicationToken.has_value() ||
        canonical.publicationState != PublicationState::CANONICAL_SELECTED ||
        state.projection->state != HostProjectionState::ACTIVE ||
        state.publicationToken->state != PublicationState::EXTERNAL_READY ||
        state.projection->packageName != canonical.packageName ||
        state.projection->userId != canonical.userId ||
        state.projection->generation != canonical.generation ||
        state.projection->canonicalDigest != canonical.canonicalDigest ||
        state.publicationToken->packageName != canonical.packageName ||
        state.publicationToken->userId != canonical.userId ||
        state.publicationToken->generation != canonical.generation ||
        state.publicationToken->canonicalDigest != canonical.canonicalDigest) {
        return Reject(request, RuntimePathVerdict::PACKAGE_NOT_READY);
    }
    if (faultInjector_->InterruptAfter(
            RuntimePathFaultPoint::AFTER_GENERATION_SNAPSHOT)) {
        return Reject(request, RuntimePathVerdict::INTERRUPTED);
    }

    RuntimePathFactsV1 facts;
    if (!factsProvider_->Read(request.packageName, request.userId,
            request.expectedGeneration, request.abi, &facts, &readError)) {
        return Reject(request, RuntimePathVerdict::PATH_READBACK_FAILED);
    }
    if (!IdentityMatches(state, facts, request) ||
        !IsLowerHexDigest(canonical.managedFiles.baseCodeDigest) ||
        facts.permittedRoots.empty() ||
        facts.permittedRoots.size() > kMaxRoots ||
        facts.nativeSearchRoots.size() > kMaxRoots ||
        facts.nativeLibraries.size() > kMaxNativeLibraries) {
        return Reject(request, RuntimePathVerdict::DATA_INCONSISTENT);
    }

    std::vector<std::string> permittedRoots;
    std::set<std::string> uniqueRoots;
    for (const auto& root : facts.permittedRoots) {
        const auto canonicalRoot = CanonicalPath(root);
        if (!canonicalRoot.has_value() || !ReadDirectory(*canonicalRoot) ||
            !uniqueRoots.insert(*canonicalRoot).second) {
            return Reject(request,
                RuntimePathVerdict::PATH_OUTSIDE_PERMITTED_ROOT);
        }
        permittedRoots.push_back(*canonicalRoot);
    }

    const auto basePath =
        CanonicalPath(canonical.managedFiles.baseCodePath);
    if (!basePath.has_value() || !IsWithinAny(*basePath, permittedRoots)) {
        return Reject(request,
            RuntimePathVerdict::PATH_OUTSIDE_PERMITTED_ROOT);
    }
    std::vector<uint8_t> baseBytes;
    uint64_t baseLength = 0;
    if (!ReadRegularFile(*basePath, &baseBytes, &baseLength)) {
        return Reject(request, RuntimePathVerdict::PATH_READBACK_FAILED);
    }
    const std::string baseDigest = Sha256Hex(baseBytes);
    if (baseDigest != canonical.managedFiles.baseCodeDigest) {
        return Reject(request, RuntimePathVerdict::DIGEST_MISMATCH);
    }

    RuntimePathResponseV1 response;
    response.requestId = request.requestId;
    response.verdict = RuntimePathVerdict::READY;
    response.classLoaderCreated = false;
    response.observations.push_back(
        {"BASE_APK", *basePath, baseLength, baseDigest, std::nullopt});
    if (faultInjector_->InterruptAfter(
            RuntimePathFaultPoint::AFTER_FILE_READBACK)) {
        return Reject(request, RuntimePathVerdict::INTERRUPTED);
    }

    std::vector<std::string> nativeSearchRoots;
    uniqueRoots.clear();
    for (const auto& root : facts.nativeSearchRoots) {
        const auto canonicalRoot = CanonicalPath(root);
        if (!canonicalRoot.has_value() ||
            !IsWithinAny(*canonicalRoot, permittedRoots) ||
            !ReadDirectory(*canonicalRoot) ||
            !uniqueRoots.insert(*canonicalRoot).second) {
            return Reject(request,
                RuntimePathVerdict::PATH_OUTSIDE_PERMITTED_ROOT);
        }
        nativeSearchRoots.push_back(*canonicalRoot);
    }

    std::vector<NativeLibraryFactV1> nativeLibraries;
    std::set<std::string> uniqueLibraries;
    for (const auto& library : facts.nativeLibraries) {
        const auto libraryPath = CanonicalPath(library.path);
        if (!libraryPath.has_value() ||
            !IsWithinAny(*libraryPath, permittedRoots) ||
            !IsWithinAny(*libraryPath, nativeSearchRoots) ||
            !uniqueLibraries.insert(*libraryPath).second ||
            !IsLowerHexDigest(library.sha256)) {
            return Reject(request,
                RuntimePathVerdict::PATH_OUTSIDE_PERMITTED_ROOT);
        }
        std::vector<uint8_t> libraryBytes;
        uint64_t libraryLength = 0;
        if (!ReadRegularFile(
                *libraryPath, &libraryBytes, &libraryLength)) {
            return Reject(request, RuntimePathVerdict::PATH_READBACK_FAILED);
        }
        const std::string libraryDigest = Sha256Hex(libraryBytes);
        if (libraryDigest != library.sha256) {
            return Reject(request, RuntimePathVerdict::DIGEST_MISMATCH);
        }
        const auto elfMachine = ReadElfMachine(libraryBytes);
        if (!elfMachine.has_value() ||
            *elfMachine != kElfMachineAarch64) {
            return Reject(request,
                RuntimePathVerdict::ELF_IDENTITY_MISMATCH);
        }
        nativeLibraries.push_back({*libraryPath, libraryDigest});
        response.observations.push_back(
            {"NATIVE_LIBRARY", *libraryPath, libraryLength, libraryDigest,
                *elfMachine});
    }
    if (faultInjector_->InterruptAfter(
            RuntimePathFaultPoint::AFTER_ELF_READBACK)) {
        return Reject(request, RuntimePathVerdict::INTERRUPTED);
    }

    RuntimePathDescriptorV1 descriptor;
    descriptor.requestId = request.requestId;
    descriptor.packageName = canonical.packageName;
    descriptor.userId = canonical.userId;
    descriptor.generation = canonical.generation;
    descriptor.canonicalDigest = canonical.canonicalDigest;
    descriptor.artifactSetDigest = canonical.artifactSetDigest;
    descriptor.abi = request.abi;
    descriptor.baseCodePath = *basePath;
    descriptor.baseCodeSha256 = baseDigest;
    descriptor.splitCodePaths = {};
    descriptor.permittedRoots = std::move(permittedRoots);
    descriptor.nativeSearchRoots = std::move(nativeSearchRoots);
    descriptor.nativeLibraries = std::move(nativeLibraries);
    response.descriptor = std::move(descriptor);

    // Force deterministic materialization before the serialization fault seam.
    (void)SerializeRuntimePathResponseJsonV1(response);
    if (faultInjector_->InterruptAfter(
            RuntimePathFaultPoint::AFTER_SERIALIZATION)) {
        return Reject(request, RuntimePathVerdict::INTERRUPTED);
    }
    return response;
}

RuntimePathVerdict ValidateDescriptorForConsumerV1(
    const RuntimePathDescriptorV1& descriptor)
{
    if (descriptor.schemaVersion != 1 || descriptor.requestId.empty() ||
        descriptor.packageName.empty() || descriptor.userId != 0 ||
        descriptor.generation == 0 ||
        !IsLowerHexDigest(descriptor.canonicalDigest) ||
        !IsLowerHexDigest(descriptor.artifactSetDigest) ||
        descriptor.abi != "arm64-v8a" ||
        descriptor.baseCodePath.empty() ||
        !IsLowerHexDigest(descriptor.baseCodeSha256) ||
        !descriptor.splitCodePaths.empty() ||
        descriptor.permittedRoots.empty()) {
        return RuntimePathVerdict::DATA_INCONSISTENT;
    }
    if (!IsWithinAny(descriptor.baseCodePath, descriptor.permittedRoots)) {
        return RuntimePathVerdict::PATH_OUTSIDE_PERMITTED_ROOT;
    }
    for (const auto& root : descriptor.nativeSearchRoots) {
        if (!IsWithinAny(root, descriptor.permittedRoots)) {
            return RuntimePathVerdict::PATH_OUTSIDE_PERMITTED_ROOT;
        }
    }
    for (const auto& library : descriptor.nativeLibraries) {
        if (!IsLowerHexDigest(library.sha256) ||
            !IsWithinAny(library.path, descriptor.nativeSearchRoots)) {
            return RuntimePathVerdict::DATA_INCONSISTENT;
        }
    }
    return RuntimePathVerdict::READY;
}

std::string SerializeRuntimePathResponseJsonV1(
    const RuntimePathResponseV1& response)
{
    std::ostringstream output;
    output << "{\"schemaVersion\":1,\"requestId\":\""
           << JsonEscape(response.requestId) << "\",\"verdict\":\""
           << RuntimePathVerdictName(response.verdict)
           << "\",\"classLoaderCreated\":"
           << (response.classLoaderCreated ? "true" : "false")
           << ",\"descriptor\":";
    if (!response.descriptor.has_value()) {
        output << "null,\"observations\":[]}";
        return output.str();
    }
    const auto& descriptor = *response.descriptor;
    output << "{\"schemaVersion\":" << descriptor.schemaVersion
           << ",\"requestId\":\"" << JsonEscape(descriptor.requestId)
           << "\",\"packageName\":\"" << JsonEscape(descriptor.packageName)
           << "\",\"userId\":" << descriptor.userId
           << ",\"generation\":" << descriptor.generation
           << ",\"canonicalDigest\":\""
           << JsonEscape(descriptor.canonicalDigest)
           << "\",\"artifactSetDigest\":\""
           << JsonEscape(descriptor.artifactSetDigest)
           << "\",\"abi\":\"" << JsonEscape(descriptor.abi)
           << "\",\"baseCodePath\":\""
           << JsonEscape(descriptor.baseCodePath)
           << "\",\"baseCodeSha256\":\""
           << JsonEscape(descriptor.baseCodeSha256)
           << "\",\"splitCodePaths\":";
    AppendStringArray(&output, descriptor.splitCodePaths);
    output << ",\"permittedRoots\":";
    AppendStringArray(&output, descriptor.permittedRoots);
    output << ",\"nativeSearchRoots\":";
    AppendStringArray(&output, descriptor.nativeSearchRoots);
    output << ",\"nativeLibraries\":[";
    for (size_t index = 0; index < descriptor.nativeLibraries.size();
         ++index) {
        if (index != 0) output << ",";
        output << "{\"path\":\""
               << JsonEscape(descriptor.nativeLibraries[index].path)
               << "\",\"sha256\":\""
               << JsonEscape(descriptor.nativeLibraries[index].sha256)
               << "\"}";
    }
    output << "]},\"observations\":[";
    for (size_t index = 0; index < response.observations.size(); ++index) {
        if (index != 0) output << ",";
        const auto& observation = response.observations[index];
        output << "{\"role\":\"" << JsonEscape(observation.role)
               << "\",\"path\":\"" << JsonEscape(observation.path)
               << "\",\"byteLength\":" << observation.byteLength
               << ",\"sha256\":\"" << JsonEscape(observation.sha256)
               << "\",\"elfMachine\":";
        if (observation.elfMachine.has_value()) {
            output << *observation.elfMachine;
        } else {
            output << "null";
        }
        output << "}";
    }
    output << "]}";
    return output.str();
}

const char* RuntimePathVerdictName(RuntimePathVerdict verdict)
{
    switch (verdict) {
        case RuntimePathVerdict::READY: return "READY";
        case RuntimePathVerdict::INVALID_REQUEST: return "INVALID_REQUEST";
        case RuntimePathVerdict::UNKNOWN_SCHEMA: return "UNKNOWN_SCHEMA";
        case RuntimePathVerdict::NOT_AUTHORIZED: return "NOT_AUTHORIZED";
        case RuntimePathVerdict::NOT_SUPPORTED_ARTIFACT_PROFILE:
            return "NOT_SUPPORTED_ARTIFACT_PROFILE";
        case RuntimePathVerdict::NOT_SUPPORTED_USER:
            return "NOT_SUPPORTED_USER";
        case RuntimePathVerdict::NOT_SUPPORTED_ABI:
            return "NOT_SUPPORTED_ABI";
        case RuntimePathVerdict::PACKAGE_NOT_FOUND:
            return "PACKAGE_NOT_FOUND";
        case RuntimePathVerdict::PACKAGE_NOT_READY:
            return "PACKAGE_NOT_READY";
        case RuntimePathVerdict::STALE_GENERATION:
            return "STALE_GENERATION";
        case RuntimePathVerdict::DATA_INCONSISTENT:
            return "DATA_INCONSISTENT";
        case RuntimePathVerdict::PATH_OUTSIDE_PERMITTED_ROOT:
            return "PATH_OUTSIDE_PERMITTED_ROOT";
        case RuntimePathVerdict::PATH_READBACK_FAILED:
            return "PATH_READBACK_FAILED";
        case RuntimePathVerdict::DIGEST_MISMATCH:
            return "DIGEST_MISMATCH";
        case RuntimePathVerdict::ELF_IDENTITY_MISMATCH:
            return "ELF_IDENTITY_MISMATCH";
        case RuntimePathVerdict::INTERRUPTED:
            return "INTERRUPTED";
    }
    return "DATA_INCONSISTENT";
}

}  // namespace oh_adapter::runtime_path_descriptor
