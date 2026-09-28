#include "package_info_v1.h"

#include <algorithm>
#include <sstream>

namespace oh_adapter::package_info {
namespace {

constexpr uint64_t SUPPORTED_FLAGS = GET_ACTIVITIES | GET_RECEIVERS |
    GET_SERVICES | GET_PROVIDERS | GET_SIGNATURES | GET_PERMISSIONS |
    GET_SIGNING_CERTIFICATES;

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

PackageInfoResponseV1 Response(const PackageInfoRequestV1& request,
    PackageInfoVerdict verdict, const char* reason)
{
    PackageInfoResponseV1 response;
    response.requestId = request.requestId;
    response.verdict = verdict;
    response.reason = reason;
    response.userId = request.userId;
    response.flags = request.flags;
    response.callerScopeDigest = request.caller.visibilityScopeDigest;
    return response;
}

bool Visible(const PackageInfoRequestV1& request)
{
    return request.caller.canSeeAllPackages ||
        std::find(request.caller.visiblePackageNames.begin(),
            request.caller.visiblePackageNames.end(), request.packageName) !=
        request.caller.visiblePackageNames.end();
}

std::vector<package_transaction::ManifestComponentFactV1> Components(
    const package_transaction::ManifestFactsV1& facts,
    const char* firstKind, const char* secondKind = nullptr)
{
    std::vector<package_transaction::ManifestComponentFactV1> result;
    for (const auto& component : facts.components) {
        if (component.kind == firstKind ||
            (secondKind != nullptr && component.kind == secondKind)) {
            result.push_back(component);
        }
    }
    return result;
}

void StringArray(std::ostringstream* out,
    const std::vector<std::string>& values)
{
    *out << "[";
    for (size_t index = 0; index < values.size(); ++index) {
        if (index != 0) *out << ",";
        *out << Json(values[index]);
    }
    *out << "]";
}

void ComponentsJson(std::ostringstream* out,
    const std::vector<package_transaction::ManifestComponentFactV1>& values)
{
    *out << "[";
    for (size_t index = 0; index < values.size(); ++index) {
        if (index != 0) *out << ",";
        *out << "{\"exported\":";
        if (!values[index].exported.has_value()) *out << "null";
        else *out << (*values[index].exported ? "true" : "false");
        *out << ",\"kind\":" << Json(values[index].kind)
            << ",\"name\":" << Json(values[index].name) << "}";
    }
    *out << "]";
}

}  // namespace

PackageInfoServiceV1::PackageInfoServiceV1(
    package_transaction::FilePackageStore* store,
    PackageInfoFaultInjector* faultInjector)
    : store_(store), faultInjector_(faultInjector)
{
}

PackageInfoResponseV1 PackageInfoServiceV1::GetPackageInfo(
    const PackageInfoRequestV1& request) const
{
    if (store_ == nullptr || faultInjector_ == nullptr ||
        request.schemaVersion != 1 || request.requestId.empty() ||
        request.packageName.empty() || request.packageName.size() > 255 ||
        request.caller.callerId.empty() ||
        request.caller.visibilityScopeDigest.empty()) {
        return Response(request, PackageInfoVerdict::INVALID_REQUEST,
            "INVALID_REQUEST");
    }
    if (request.userId != 0 || (request.flags & ~SUPPORTED_FLAGS) != 0) {
        return Response(request, PackageInfoVerdict::NOT_SUPPORTED,
            "NOT_SUPPORTED");
    }

    package_transaction::PackageManagementReadV1 read;
    std::string error;
    if (!store_->ReadPackageManagementState(
            request.userId, request.packageName, &read, &error)) {
        return Response(request, PackageInfoVerdict::DATA_INCONSISTENT,
            "STORE_READ_FAILED");
    }
    if (faultInjector_->InterruptAfter(PackageInfoPhase::SNAPSHOT_FROZEN)) {
        return Response(request, PackageInfoVerdict::INTERRUPTED,
            "INTERRUPTED_AFTER_SNAPSHOT");
    }
    if (!Visible(request)) {
        return Response(request, PackageInfoVerdict::PACKAGE_NOT_VISIBLE,
            "PACKAGE_NOT_VISIBLE");
    }
    if (read.removing) {
        return Response(request, PackageInfoVerdict::PACKAGE_NOT_READY,
            "PACKAGE_REMOVING");
    }
    if (!read.canonical.has_value()) {
        return Response(request, PackageInfoVerdict::PACKAGE_NOT_FOUND,
            "PACKAGE_NOT_FOUND");
    }
    const auto& snapshot = *read.canonical;
    auto response = Response(request, PackageInfoVerdict::DATA_INCONSISTENT,
        "DATA_INCONSISTENT");
    response.catalogRevision = read.catalogRevision;
    response.generation = snapshot.generation;
    response.canonicalDigest = snapshot.canonicalDigest;
    if (snapshot.packageName != request.packageName ||
        snapshot.userId != request.userId || snapshot.generation == 0 ||
        snapshot.canonicalDigest.empty() ||
        snapshot.publicationState !=
            package_transaction::PublicationState::CANONICAL_SELECTED) {
        response.reason = "CANONICAL_STATE_INCONSISTENT";
        return response;
    }
    if (request.expectedGeneration.has_value() &&
        *request.expectedGeneration != snapshot.generation) {
        response.verdict = PackageInfoVerdict::STALE_GENERATION;
        response.reason = "EXPECTED_GENERATION_MISMATCH";
        return response;
    }
    if (request.expectedCanonicalDigest.has_value() &&
        *request.expectedCanonicalDigest != snapshot.canonicalDigest) {
        response.verdict = PackageInfoVerdict::STALE_GENERATION;
        response.reason = "EXPECTED_CANONICAL_DIGEST_MISMATCH";
        return response;
    }
    if (!read.publicationToken.has_value() || !read.projection.has_value()) {
        response.verdict = PackageInfoVerdict::PACKAGE_NOT_READY;
        response.reason = "EXTERNAL_READY_NOT_ESTABLISHED";
        return response;
    }
    const auto& token = *read.publicationToken;
    const auto& projection = *read.projection;
    if (token.generation != snapshot.generation ||
        token.canonicalDigest != snapshot.canonicalDigest ||
        projection.generation != snapshot.generation ||
        projection.canonicalDigest != snapshot.canonicalDigest) {
        response.reason = "GENERATION_DIGEST_JOIN_MISMATCH";
        return response;
    }
    if (token.state != package_transaction::PublicationState::EXTERNAL_READY ||
        projection.state !=
            package_transaction::HostProjectionState::ACTIVE) {
        response.verdict = PackageInfoVerdict::PACKAGE_NOT_READY;
        response.reason = "EXTERNAL_READY_NOT_ESTABLISHED";
        return response;
    }
    if (!snapshot.manifestFacts.has_value() ||
        !snapshot.signingFacts.has_value()) {
        response.reason = "CANONICAL_FACTS_MISSING";
        return response;
    }
    const auto& manifest = *snapshot.manifestFacts;
    const auto& signing = *snapshot.signingFacts;
    if (manifest.packageName != snapshot.packageName ||
        manifest.artifactSetDigest != snapshot.artifactSetDigest ||
        signing.artifactSetDigest != snapshot.artifactSetDigest ||
        !signing.verified) {
        response.reason = "CANONICAL_FACTS_JOIN_MISMATCH";
        return response;
    }

    PackageInfoViewV1 view;
    view.packageName = manifest.packageName;
    view.versionCode = manifest.versionCode;
    view.versionName = manifest.versionName;
    view.applicationInfo = {manifest.packageName,
        manifest.applicationClassName, manifest.applicationLabel,
        manifest.minSdk, manifest.targetSdk};
    if ((request.flags & GET_ACTIVITIES) != 0) {
        view.activities = Components(manifest, "activity", "activity-alias");
    }
    if ((request.flags & GET_RECEIVERS) != 0) {
        view.receivers = Components(manifest, "receiver");
    }
    if ((request.flags & GET_SERVICES) != 0) {
        view.services = Components(manifest, "service");
    }
    if ((request.flags & GET_PROVIDERS) != 0) {
        view.providers = Components(manifest, "provider");
    }
    if ((request.flags & GET_PERMISSIONS) != 0) {
        view.requestedPermissions = manifest.requestedPermissions;
    }
    if ((request.flags & GET_SIGNATURES) != 0) {
        if (signing.signerCertificateDerHex.empty()) {
            response.reason = "CANONICAL_SIGNER_BYTES_MISSING";
            return response;
        }
        view.signatures = signing.signerCertificateDigests;
        view.signerCertificateDerHex = signing.signerCertificateDerHex;
    }
    if ((request.flags & GET_SIGNING_CERTIFICATES) != 0) {
        if (signing.signerCertificateDerHex.empty()) {
            response.reason = "CANONICAL_SIGNER_BYTES_MISSING";
            return response;
        }
        view.signingCertificateDigests =
            signing.signerCertificateDigests;
        view.signerCertificateDerHex = signing.signerCertificateDerHex;
        view.signingSchemeVersion = *std::max_element(
            signing.schemeVersions.begin(), signing.schemeVersions.end());
    }
    if (faultInjector_->InterruptAfter(PackageInfoPhase::FIELDS_PROJECTED)) {
        response.verdict = PackageInfoVerdict::INTERRUPTED;
        response.reason = "INTERRUPTED_AFTER_PROJECTION";
        return response;
    }
    response.packageInfo = std::move(view);
    response.verdict = PackageInfoVerdict::READY;
    response.reason = "READY";
    if (faultInjector_->InterruptAfter(PackageInfoPhase::RESPONSE_SERIALIZED)) {
        response.packageInfo.reset();
        response.verdict = PackageInfoVerdict::INTERRUPTED;
        response.reason = "INTERRUPTED_AFTER_SERIALIZATION";
    }
    return response;
}

const char* PackageInfoVerdictName(PackageInfoVerdict verdict)
{
    switch (verdict) {
        case PackageInfoVerdict::READY: return "READY";
        case PackageInfoVerdict::INVALID_REQUEST: return "INVALID_REQUEST";
        case PackageInfoVerdict::NOT_SUPPORTED: return "NOT_SUPPORTED";
        case PackageInfoVerdict::PACKAGE_NOT_FOUND: return "PACKAGE_NOT_FOUND";
        case PackageInfoVerdict::PACKAGE_NOT_VISIBLE:
            return "PACKAGE_NOT_VISIBLE";
        case PackageInfoVerdict::PACKAGE_NOT_READY:
            return "PACKAGE_NOT_READY";
        case PackageInfoVerdict::STALE_GENERATION: return "STALE_GENERATION";
        case PackageInfoVerdict::DATA_INCONSISTENT: return "DATA_INCONSISTENT";
        case PackageInfoVerdict::INTERRUPTED: return "INTERRUPTED";
    }
    return "DATA_INCONSISTENT";
}

std::string PackageInfoResponseJson(const PackageInfoResponseV1& response)
{
    std::ostringstream out;
    out << "{\"callerScopeDigest\":" << Json(response.callerScopeDigest)
        << ",\"canonicalDigest\":" << Json(response.canonicalDigest)
        << ",\"catalogRevision\":" << response.catalogRevision
        << ",\"flags\":" << response.flags
        << ",\"generation\":" << response.generation
        << ",\"packageInfo\":";
    if (!response.packageInfo.has_value()) {
        out << "null";
    } else {
        const auto& view = *response.packageInfo;
        out << "{\"activities\":";
        if (view.activities.has_value()) ComponentsJson(&out, *view.activities);
        else out << "null";
        out << ",\"applicationInfo\":{\"className\":"
            << Json(view.applicationInfo.className)
            << ",\"label\":" << Json(view.applicationInfo.label)
            << ",\"minSdk\":" << view.applicationInfo.minSdk
            << ",\"packageName\":" << Json(view.applicationInfo.packageName)
            << ",\"targetSdk\":" << view.applicationInfo.targetSdk << "}"
            << ",\"packageName\":" << Json(view.packageName)
            << ",\"providers\":";
        if (view.providers.has_value()) ComponentsJson(&out, *view.providers);
        else out << "null";
        out << ",\"receivers\":";
        if (view.receivers.has_value()) ComponentsJson(&out, *view.receivers);
        else out << "null";
        out << ",\"requestedPermissions\":";
        if (view.requestedPermissions.has_value()) {
            StringArray(&out, *view.requestedPermissions);
        } else out << "null";
        out << ",\"services\":";
        if (view.services.has_value()) ComponentsJson(&out, *view.services);
        else out << "null";
        out << ",\"signatures\":";
        if (view.signatures.has_value()) StringArray(&out, *view.signatures);
        else out << "null";
        out << ",\"signingCertificateDigests\":";
        if (view.signingCertificateDigests.has_value()) {
            StringArray(&out, *view.signingCertificateDigests);
        } else out << "null";
        out << ",\"signerCertificateDerHex\":";
        if (view.signerCertificateDerHex.has_value()) {
            StringArray(&out, *view.signerCertificateDerHex);
        } else out << "null";
        out << ",\"signingSchemeVersion\":";
        if (view.signingSchemeVersion.has_value()) {
            out << *view.signingSchemeVersion;
        } else out << "null";
        out << ",\"versionCode\":" << view.versionCode
            << ",\"versionName\":" << Json(view.versionName) << "}";
    }
    out << ",\"reason\":" << Json(response.reason)
        << ",\"requestId\":" << Json(response.requestId)
        << ",\"userId\":" << response.userId
        << ",\"verdict\":" << Json(PackageInfoVerdictName(response.verdict))
        << "}";
    return out.str();
}

}  // namespace oh_adapter::package_info
