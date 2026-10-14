#include "application_info_v1.h"

#include "sha256.h"

#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <cstring>
#include <sstream>
#include <utility>
#include <vector>

namespace oh_adapter::application_info {
namespace {

constexpr uint64_t kSupportedFlags = MATCH_DISABLED_COMPONENTS;
constexpr uint32_t kApplicationFlagHasCode = 0x00000004U;
constexpr uint32_t kApplicationFlagInstalled = 0x00800000U;

bool IsLowerHexDigest(const std::string& value)
{
    return value.size() == 64 &&
        std::all_of(value.begin(), value.end(), [](unsigned char c) {
            return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
        });
}

std::string Sha256Hex(const uint8_t* bytes, size_t size)
{
    uint8_t digest[32];
    sha256(bytes, size, digest);
    static constexpr char HEX[] = "0123456789abcdef";
    std::string result(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        result[index * 2] = HEX[digest[index] >> 4];
        result[index * 2 + 1] = HEX[digest[index] & 15];
    }
    return result;
}

std::string Sha256Hex(const std::string& value)
{
    return Sha256Hex(
        reinterpret_cast<const uint8_t*>(value.data()), value.size());
}

std::string Json(const std::string& value)
{
    std::string result = "\"";
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') {
            result.push_back('\\');
            result.push_back(static_cast<char>(c));
        } else if (c == '\n') result += "\\n";
        else if (c == '\r') result += "\\r";
        else if (c == '\t') result += "\\t";
        else if (c >= 0x20) result.push_back(static_cast<char>(c));
    }
    return result + "\"";
}

ApplicationInfoResponseV1 Response(const ApplicationInfoRequestV1& request,
    ApplicationInfoVerdict verdict, const char* reason)
{
    ApplicationInfoResponseV1 response;
    response.requestId = request.requestId;
    response.verdict = verdict;
    response.reason = reason;
    response.userId = request.userId;
    response.flags = request.flags;
    response.callerScopeDigest = request.caller.visibilityScopeDigest;
    return response;
}

ApplicationInfoResponseV1 MapQueryResponse(
    const ApplicationInfoRequestV1& request,
    const package_query::GetPackageResponseV1& query)
{
    using package_query::PackageQueryVerdict;
    switch (query.verdict) {
        case PackageQueryVerdict::INVALID_REQUEST:
            return Response(request, ApplicationInfoVerdict::INVALID_REQUEST,
                "INVALID_REQUEST");
        case PackageQueryVerdict::NOT_SUPPORTED:
            return Response(request, ApplicationInfoVerdict::NOT_SUPPORTED,
                "NOT_SUPPORTED");
        case PackageQueryVerdict::PACKAGE_NOT_FOUND:
            return Response(request, ApplicationInfoVerdict::PACKAGE_NOT_FOUND,
                "PACKAGE_NOT_FOUND");
        case PackageQueryVerdict::PACKAGE_NOT_VISIBLE:
            return Response(request,
                ApplicationInfoVerdict::PACKAGE_NOT_VISIBLE,
                "PACKAGE_NOT_VISIBLE");
        case PackageQueryVerdict::PACKAGE_REMOVING:
        case PackageQueryVerdict::PACKAGE_NOT_READY:
            return Response(request, ApplicationInfoVerdict::PACKAGE_NOT_READY,
                query.reason.c_str());
        case PackageQueryVerdict::DATA_INCONSISTENT:
            return Response(request, ApplicationInfoVerdict::DATA_INCONSISTENT,
                query.reason.c_str());
        case PackageQueryVerdict::READY:
            break;
    }
    return Response(request, ApplicationInfoVerdict::DATA_INCONSISTENT,
        "QUERY_RESULT_INCONSISTENT");
}

bool ValidHostFacts(const HostApplicationRuntimeFactsV1& facts)
{
    return !facts.packageName.empty() && facts.generation != 0 &&
        IsLowerHexDigest(facts.canonicalDigest) &&
        IsLowerHexDigest(facts.projectionDigest) &&
        !facts.bundleName.empty() && !facts.appId.empty() && facts.uid >= 0 &&
        facts.accessTokenId != 0 && !facts.dataDirectory.path.empty() &&
        facts.dataDirectory.kind == ManagedPathKind::DATA_DIRECTORY &&
        IsLowerHexDigest(facts.dataDirectory.expectedDigest) &&
        !facts.deviceProtectedDataDirectory.path.empty() &&
        facts.deviceProtectedDataDirectory.kind ==
            ManagedPathKind::DATA_DIRECTORY &&
        IsLowerHexDigest(
            facts.deviceProtectedDataDirectory.expectedDigest) &&
        !facts.credentialProtectedDataDirectory.path.empty() &&
        facts.credentialProtectedDataDirectory.kind ==
            ManagedPathKind::DATA_DIRECTORY &&
        IsLowerHexDigest(
            facts.credentialProtectedDataDirectory.expectedDigest) &&
        (!facts.nativeLibraryDirectory.has_value() ||
            (facts.nativeLibraryDirectory->kind ==
                    ManagedPathKind::NATIVE_LIBRARY_DIRECTORY &&
                !facts.nativeLibraryDirectory->path.empty() &&
                IsLowerHexDigest(
                    facts.nativeLibraryDirectory->expectedDigest)));
}

}  // namespace

std::string ComputeManagedDirectoryDigestV1(const std::string& path)
{
    return Sha256Hex(std::string("managed-directory-v1\n") + path);
}

bool PosixManagedPathReaderV1::Read(
    const ManagedPathExpectationV1& expectation,
    ManagedPathReadbackV1* readback, std::string* error)
{
    if (readback == nullptr || expectation.path.empty() ||
        expectation.path.front() != '/' ||
        !IsLowerHexDigest(expectation.expectedDigest)) {
        if (error != nullptr) *error = "invalid path expectation";
        return false;
    }
    int openFlags = O_RDONLY | O_CLOEXEC | O_NOFOLLOW;
    if (expectation.kind != ManagedPathKind::BASE_CODE_FILE) {
        openFlags |= O_DIRECTORY;
    }
    const int descriptor = open(expectation.path.c_str(), openFlags);
    if (descriptor < 0) {
        if (error != nullptr) *error = std::strerror(errno);
        return false;
    }
    struct stat status {};
    if (fstat(descriptor, &status) != 0) {
        if (error != nullptr) *error = std::strerror(errno);
        close(descriptor);
        return false;
    }

    std::string observedDigest;
    if (expectation.kind == ManagedPathKind::BASE_CODE_FILE) {
        if (!S_ISREG(status.st_mode)) {
            if (error != nullptr) *error = "expected regular file";
            close(descriptor);
            return false;
        }
        std::vector<uint8_t> bytes;
        uint8_t buffer[16384];
        bool success = true;
        for (;;) {
            const ssize_t count = read(descriptor, buffer, sizeof(buffer));
            if (count == 0) break;
            if (count < 0) {
                if (errno == EINTR) continue;
                if (error != nullptr) *error = std::strerror(errno);
                success = false;
                break;
            }
            bytes.insert(bytes.end(), buffer, buffer + count);
        }
        close(descriptor);
        if (!success) return false;
        observedDigest = Sha256Hex(bytes.data(), bytes.size());
    } else {
        if (!S_ISDIR(status.st_mode)) {
            if (error != nullptr) *error = "expected directory";
            close(descriptor);
            return false;
        }
        close(descriptor);
        observedDigest = ComputeManagedDirectoryDigestV1(expectation.path);
    }
    if (observedDigest != expectation.expectedDigest) {
        if (error != nullptr) *error = "managed path digest mismatch";
        return false;
    }
    if (expectation.expectedOwnerUid.has_value() &&
        *expectation.expectedOwnerUid != static_cast<uint32_t>(status.st_uid)) {
        if (error != nullptr) *error = "managed path owner mismatch";
        return false;
    }
    readback->kind = expectation.kind;
    readback->path = expectation.path;
    readback->observedDigest = observedDigest;
    readback->ownerUid = static_cast<uint32_t>(status.st_uid);
    readback->mode = static_cast<uint32_t>(status.st_mode);
    if (error != nullptr) error->clear();
    return true;
}

ApplicationInfoServiceV1::ApplicationInfoServiceV1(
    package_transaction::FilePackageStore* store,
    HostApplicationRuntimeFactsResolverV1* hostFactsResolver,
    ManagedPathReaderV1* pathReader,
    ApplicationInfoFaultInjector* faultInjector)
    : store_(store),
      hostFactsResolver_(hostFactsResolver),
      pathReader_(pathReader),
      faultInjector_(faultInjector)
{
}

ApplicationInfoResponseV1 ApplicationInfoServiceV1::GetApplicationInfo(
    const ApplicationInfoRequestV1& request) const
{
    if (store_ == nullptr || hostFactsResolver_ == nullptr ||
        pathReader_ == nullptr || faultInjector_ == nullptr ||
        request.schemaVersion != 1 || request.requestId.empty() ||
        request.packageName.empty() || request.packageName.size() > 255 ||
        request.caller.callerId.empty() ||
        request.caller.visibilityScopeDigest.empty()) {
        return Response(request, ApplicationInfoVerdict::INVALID_REQUEST,
            "INVALID_REQUEST");
    }
    if (request.userId != 0 || (request.flags & ~kSupportedFlags) != 0) {
        return Response(request, ApplicationInfoVerdict::NOT_SUPPORTED,
            "NOT_SUPPORTED");
    }

    package_query::GetPackageRequestV1 queryRequest;
    queryRequest.requestId = request.requestId + ":snapshot";
    queryRequest.packageName = request.packageName;
    queryRequest.userId = request.userId;
    queryRequest.caller = request.caller;
    queryRequest.expectedGeneration = request.expectedGeneration;
    queryRequest.expectedCanonicalDigest = request.expectedCanonicalDigest;
    package_query::NoQueryFaultInjector noQueryFault;
    package_query::PackageQueryService queryService(store_, &noQueryFault);
    const auto query = queryService.GetPackage(queryRequest);
    if (query.verdict != package_query::PackageQueryVerdict::READY ||
        !query.package.has_value()) {
        return MapQueryResponse(request, query);
    }

    package_transaction::PackageManagementReadV1 read;
    std::string error;
    if (!store_->ReadPackageManagementState(
            request.userId, request.packageName, &read, &error) ||
        !read.canonical.has_value()) {
        return Response(request, ApplicationInfoVerdict::DATA_INCONSISTENT,
            "STORE_READ_FAILED");
    }
    const auto& querySnapshot = *query.package;
    const auto& canonical = *read.canonical;
    auto response = Response(request, ApplicationInfoVerdict::DATA_INCONSISTENT,
        "DATA_INCONSISTENT");
    response.catalogRevision = read.catalogRevision;
    response.generation = canonical.generation;
    response.canonicalDigest = canonical.canonicalDigest;
    response.artifactSetDigest = canonical.artifactSetDigest;
    if (read.catalogRevision != query.catalogRevision ||
        canonical.packageName != querySnapshot.packageName ||
        canonical.userId != querySnapshot.userId ||
        canonical.generation != querySnapshot.generation ||
        canonical.canonicalDigest != querySnapshot.canonicalDigest ||
        canonical.publicationState !=
            package_transaction::PublicationState::CANONICAL_SELECTED) {
        response.reason = "SNAPSHOT_JOIN_MISMATCH";
        return response;
    }
    if (faultInjector_->InterruptAfter(
            ApplicationInfoPhase::SNAPSHOT_FROZEN)) {
        response.verdict = ApplicationInfoVerdict::INTERRUPTED;
        response.reason = "INTERRUPTED_AFTER_SNAPSHOT";
        return response;
    }
    if (!canonical.manifestFacts.has_value()) {
        response.reason = "MANIFEST_FACTS_MISSING";
        return response;
    }
    const auto& manifest = *canonical.manifestFacts;
    if (manifest.packageName != canonical.packageName ||
        manifest.artifactSetDigest != canonical.artifactSetDigest ||
        canonical.managedFiles.baseCodePath.empty() ||
        !IsLowerHexDigest(canonical.managedFiles.baseCodeDigest)) {
        response.reason = "CANONICAL_FACTS_JOIN_MISMATCH";
        return response;
    }

    HostApplicationRuntimeFactsV1 host;
    const auto hostVerdict = hostFactsResolver_->Resolve(
        canonical.packageName, canonical.userId, canonical.generation,
        canonical.canonicalDigest, &host, &error);
    if (hostVerdict == HostApplicationFactsVerdict::PACKAGE_NOT_READY) {
        response.verdict = ApplicationInfoVerdict::PACKAGE_NOT_READY;
        response.reason = "HOST_APPLICATION_FACTS_NOT_READY";
        return response;
    }
    if (hostVerdict != HostApplicationFactsVerdict::READY ||
        !ValidHostFacts(host) ||
        host.packageName != canonical.packageName ||
        host.userId != canonical.userId ||
        host.generation != canonical.generation ||
        host.canonicalDigest != canonical.canonicalDigest) {
        response.reason = "HOST_APPLICATION_FACTS_MISMATCH";
        return response;
    }
    response.projectionDigest = host.projectionDigest;
    if (!host.projectionActive || !host.tokenExternalReady) {
        response.verdict = ApplicationInfoVerdict::PACKAGE_NOT_READY;
        response.reason = "EXTERNAL_READY_NOT_ESTABLISHED";
        return response;
    }
    if (!host.installed) {
        response.verdict = ApplicationInfoVerdict::PACKAGE_NOT_FOUND;
        response.reason = "PACKAGE_NOT_INSTALLED";
        return response;
    }
    if (host.hidden ||
        (!host.enabled &&
            (request.flags & MATCH_DISABLED_COMPONENTS) == 0)) {
        response.verdict = ApplicationInfoVerdict::PACKAGE_NOT_VISIBLE;
        response.reason = host.hidden ? "PACKAGE_HIDDEN" : "PACKAGE_DISABLED";
        return response;
    }

    std::vector<ManagedPathExpectationV1> expectations;
    expectations.push_back({ManagedPathKind::BASE_CODE_FILE,
        canonical.managedFiles.baseCodePath,
        canonical.managedFiles.baseCodeDigest, std::nullopt});
    expectations.push_back(host.dataDirectory);
    expectations.push_back(host.deviceProtectedDataDirectory);
    expectations.push_back(host.credentialProtectedDataDirectory);
    if (host.nativeLibraryDirectory.has_value()) {
        expectations.push_back(*host.nativeLibraryDirectory);
    }
    for (const auto& expectation : expectations) {
        ManagedPathReadbackV1 pathReadback;
        if (!pathReader_->Read(expectation, &pathReadback, &error)) {
            response.pathReadbacks.clear();
            response.verdict =
                ApplicationInfoVerdict::PATH_READBACK_FAILED;
            response.reason = "PATH_READBACK_FAILED";
            return response;
        }
        response.pathReadbacks.push_back(std::move(pathReadback));
    }
    if (faultInjector_->InterruptAfter(
            ApplicationInfoPhase::PATHS_READ_BACK)) {
        response.pathReadbacks.clear();
        response.verdict = ApplicationInfoVerdict::INTERRUPTED;
        response.reason = "INTERRUPTED_AFTER_PATH_READBACK";
        return response;
    }

    package_transaction::PackageManagementReadV1 afterRead;
    if (!store_->ReadPackageManagementState(
            request.userId, request.packageName, &afterRead, &error) ||
        afterRead.catalogRevision != read.catalogRevision ||
        !afterRead.canonical.has_value() ||
        afterRead.canonical->generation != canonical.generation ||
        afterRead.canonical->canonicalDigest != canonical.canonicalDigest) {
        response.pathReadbacks.clear();
        response.reason = "SNAPSHOT_CHANGED_DURING_READBACK";
        return response;
    }

    ApplicationInfoViewV1 view;
    view.packageName = canonical.packageName;
    view.className = manifest.applicationClassName;
    view.processName = canonical.packageName;
    view.label = manifest.applicationLabel;
    view.uid = host.uid;
    view.sourceDir = canonical.managedFiles.baseCodePath;
    view.publicSourceDir = canonical.managedFiles.baseCodePath;
    view.dataDir = host.dataDirectory.path;
    view.deviceProtectedDataDir =
        host.deviceProtectedDataDirectory.path;
    view.credentialProtectedDataDir =
        host.credentialProtectedDataDirectory.path;
    if (host.nativeLibraryDirectory.has_value()) {
        view.nativeLibraryDir = host.nativeLibraryDirectory->path;
    }
    view.primaryCpuAbi = host.primaryCpuAbi;
    view.minSdk = manifest.minSdk;
    view.targetSdk = manifest.targetSdk;
    view.applicationFlags =
        kApplicationFlagHasCode | kApplicationFlagInstalled;
    view.enabled = host.enabled;
    if (faultInjector_->InterruptAfter(
            ApplicationInfoPhase::FIELDS_PROJECTED)) {
        response.pathReadbacks.clear();
        response.verdict = ApplicationInfoVerdict::INTERRUPTED;
        response.reason = "INTERRUPTED_AFTER_PROJECTION";
        return response;
    }
    response.applicationInfo = std::move(view);
    response.verdict = ApplicationInfoVerdict::READY;
    response.reason = "READY";
    if (faultInjector_->InterruptAfter(
            ApplicationInfoPhase::RESPONSE_SERIALIZED)) {
        response.applicationInfo.reset();
        response.pathReadbacks.clear();
        response.verdict = ApplicationInfoVerdict::INTERRUPTED;
        response.reason = "INTERRUPTED_AFTER_SERIALIZATION";
    }
    return response;
}

const char* ApplicationInfoVerdictName(ApplicationInfoVerdict verdict)
{
    switch (verdict) {
        case ApplicationInfoVerdict::READY: return "READY";
        case ApplicationInfoVerdict::INVALID_REQUEST: return "INVALID_REQUEST";
        case ApplicationInfoVerdict::NOT_SUPPORTED: return "NOT_SUPPORTED";
        case ApplicationInfoVerdict::PACKAGE_NOT_FOUND:
            return "PACKAGE_NOT_FOUND";
        case ApplicationInfoVerdict::PACKAGE_NOT_VISIBLE:
            return "PACKAGE_NOT_VISIBLE";
        case ApplicationInfoVerdict::PACKAGE_NOT_READY:
            return "PACKAGE_NOT_READY";
        case ApplicationInfoVerdict::DATA_INCONSISTENT:
            return "DATA_INCONSISTENT";
        case ApplicationInfoVerdict::PATH_READBACK_FAILED:
            return "PATH_READBACK_FAILED";
        case ApplicationInfoVerdict::INTERRUPTED: return "INTERRUPTED";
    }
    return "DATA_INCONSISTENT";
}

const char* ManagedPathKindName(ManagedPathKind kind)
{
    switch (kind) {
        case ManagedPathKind::BASE_CODE_FILE: return "BASE_CODE_FILE";
        case ManagedPathKind::DATA_DIRECTORY: return "DATA_DIRECTORY";
        case ManagedPathKind::NATIVE_LIBRARY_DIRECTORY:
            return "NATIVE_LIBRARY_DIRECTORY";
    }
    return "UNKNOWN";
}

std::string ApplicationInfoResponseJson(
    const ApplicationInfoResponseV1& response)
{
    std::ostringstream out;
    out << "{\"applicationInfo\":";
    if (!response.applicationInfo.has_value()) {
        out << "null";
    } else {
        const auto& view = *response.applicationInfo;
        out << "{\"applicationFlags\":" << view.applicationFlags
            << ",\"className\":" << Json(view.className)
            << ",\"credentialProtectedDataDir\":"
            << Json(view.credentialProtectedDataDir)
            << ",\"dataDir\":" << Json(view.dataDir)
            << ",\"deviceProtectedDataDir\":"
            << Json(view.deviceProtectedDataDir)
            << ",\"enabled\":" << (view.enabled ? "true" : "false")
            << ",\"label\":" << Json(view.label)
            << ",\"minSdk\":" << view.minSdk
            << ",\"nativeLibraryDir\":"
            << (view.nativeLibraryDir.has_value()
                    ? Json(*view.nativeLibraryDir) : "null")
            << ",\"packageName\":" << Json(view.packageName)
            << ",\"primaryCpuAbi\":"
            << (view.primaryCpuAbi.has_value()
                    ? Json(*view.primaryCpuAbi) : "null")
            << ",\"processName\":" << Json(view.processName)
            << ",\"publicSourceDir\":" << Json(view.publicSourceDir)
            << ",\"sourceDir\":" << Json(view.sourceDir)
            << ",\"targetSdk\":" << view.targetSdk
            << ",\"uid\":" << view.uid << "}";
    }
    out << ",\"artifactSetDigest\":" << Json(response.artifactSetDigest)
        << ",\"callerScopeDigest\":" << Json(response.callerScopeDigest)
        << ",\"canonicalDigest\":" << Json(response.canonicalDigest)
        << ",\"catalogRevision\":" << response.catalogRevision
        << ",\"flags\":" << response.flags
        << ",\"generation\":" << response.generation
        << ",\"pathReadbacks\":[";
    for (size_t index = 0; index < response.pathReadbacks.size(); ++index) {
        if (index != 0) out << ",";
        const auto& path = response.pathReadbacks[index];
        out << "{\"kind\":" << Json(ManagedPathKindName(path.kind))
            << ",\"mode\":" << path.mode
            << ",\"observedDigest\":" << Json(path.observedDigest)
            << ",\"ownerUid\":" << path.ownerUid
            << ",\"path\":" << Json(path.path) << "}";
    }
    out << "],\"projectionDigest\":" << Json(response.projectionDigest)
        << ",\"reason\":" << Json(response.reason)
        << ",\"requestId\":" << Json(response.requestId)
        << ",\"userId\":" << response.userId
        << ",\"verdict\":" << Json(ApplicationInfoVerdictName(response.verdict))
        << "}";
    return out.str();
}

}  // namespace oh_adapter::application_info
