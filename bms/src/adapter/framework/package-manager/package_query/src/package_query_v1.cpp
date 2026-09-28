#include "package_query_v1.h"

#include <algorithm>

namespace oh_adapter::package_query {
namespace {

constexpr uint32_t kPrimaryUserId = 0;
constexpr size_t kMaxPackageNameBytes = 255;

GetPackageResponseV1 MakeResponse(const GetPackageRequestV1& request,
    PackageQueryVerdict verdict, const char* reason,
    uint64_t catalogRevision = 0)
{
    GetPackageResponseV1 response;
    response.requestId = request.requestId;
    response.verdict = verdict;
    response.reason = reason;
    response.catalogRevision = catalogRevision;
    return response;
}

bool IsVisible(const GetPackageRequestV1& request)
{
    if (request.caller.canSeeAllPackages) return true;
    return std::find(request.caller.visiblePackageNames.begin(),
               request.caller.visiblePackageNames.end(),
               request.packageName) != request.caller.visiblePackageNames.end();
}

}  // namespace

PackageQueryService::PackageQueryService(
    package_transaction::FilePackageStore* store,
    QueryFaultInjector* faultInjector)
    : store_(store), faultInjector_(faultInjector)
{
}

GetPackageResponseV1 PackageQueryService::GetPackage(
    const GetPackageRequestV1& request) const
{
    if (store_ == nullptr || faultInjector_ == nullptr ||
        request.schemaVersion != 1 || request.requestId.empty() ||
        request.packageName.empty() ||
        request.packageName.size() > kMaxPackageNameBytes ||
        request.caller.callerId.empty() ||
        request.caller.visibilityScopeDigest.empty()) {
        return MakeResponse(
            request, PackageQueryVerdict::INVALID_REQUEST, "INVALID_REQUEST");
    }
    if (request.userId != kPrimaryUserId || request.flags != 0) {
        return MakeResponse(
            request, PackageQueryVerdict::NOT_SUPPORTED, "NOT_SUPPORTED");
    }

    package_transaction::PackageManagementReadV1 read;
    std::string error;
    if (!store_->ReadPackageManagementState(
            request.userId, request.packageName, &read, &error)) {
        return MakeResponse(request, PackageQueryVerdict::DATA_INCONSISTENT,
            "STORE_READ_FAILED");
    }
    if (faultInjector_->InterruptAfter(QueryPhase::SNAPSHOT_FROZEN)) {
        return MakeResponse(request, PackageQueryVerdict::PACKAGE_NOT_READY,
            "QUERY_INTERRUPTED_RETRY", read.catalogRevision);
    }
    if (!IsVisible(request)) {
        return MakeResponse(request, PackageQueryVerdict::PACKAGE_NOT_VISIBLE,
            "PACKAGE_NOT_VISIBLE");
    }
    if (faultInjector_->InterruptAfter(QueryPhase::VISIBILITY_CHECKED)) {
        return MakeResponse(request, PackageQueryVerdict::PACKAGE_NOT_READY,
            "QUERY_INTERRUPTED_RETRY", read.catalogRevision);
    }
    if (read.removing) {
        return MakeResponse(request, PackageQueryVerdict::PACKAGE_REMOVING,
            "PACKAGE_REMOVING", read.catalogRevision);
    }
    if (!read.canonical.has_value()) {
        return MakeResponse(request, PackageQueryVerdict::PACKAGE_NOT_FOUND,
            "PACKAGE_NOT_FOUND", read.catalogRevision);
    }

    const auto& canonical = *read.canonical;
    if (canonical.packageName != request.packageName ||
        canonical.userId != request.userId ||
        canonical.generation == 0 ||
        canonical.canonicalDigest.empty() ||
        canonical.publicationState !=
            package_transaction::PublicationState::CANONICAL_SELECTED) {
        return MakeResponse(request, PackageQueryVerdict::DATA_INCONSISTENT,
            "CANONICAL_STATE_INCONSISTENT", read.catalogRevision);
    }
    if (request.expectedGeneration.has_value() &&
        *request.expectedGeneration != canonical.generation) {
        return MakeResponse(request, PackageQueryVerdict::DATA_INCONSISTENT,
            "EXPECTED_GENERATION_MISMATCH", read.catalogRevision);
    }
    if (request.expectedCanonicalDigest.has_value() &&
        *request.expectedCanonicalDigest != canonical.canonicalDigest) {
        return MakeResponse(request, PackageQueryVerdict::DATA_INCONSISTENT,
            "EXPECTED_DIGEST_MISMATCH", read.catalogRevision);
    }
    if (!read.projection.has_value() ||
        !read.publicationToken.has_value()) {
        return MakeResponse(request, PackageQueryVerdict::PACKAGE_NOT_READY,
            "EXTERNAL_READY_NOT_ESTABLISHED", read.catalogRevision);
    }
    const auto& projection = *read.projection;
    const auto& token = *read.publicationToken;
    if (projection.state !=
            package_transaction::HostProjectionState::ACTIVE ||
        token.state !=
            package_transaction::PublicationState::EXTERNAL_READY) {
        return MakeResponse(request,
            PackageQueryVerdict::PACKAGE_NOT_READY,
            "EXTERNAL_READY_NOT_ESTABLISHED", read.catalogRevision);
    }
    if (projection.packageName != canonical.packageName ||
        projection.userId != canonical.userId ||
        projection.generation != canonical.generation ||
        projection.canonicalDigest != canonical.canonicalDigest ||
        token.packageName != canonical.packageName ||
        token.userId != canonical.userId ||
        token.generation != canonical.generation ||
        token.canonicalDigest != canonical.canonicalDigest) {
        return MakeResponse(request, PackageQueryVerdict::DATA_INCONSISTENT,
            "GENERATION_DIGEST_JOIN_MISMATCH", read.catalogRevision);
    }

    PackageManagementSnapshotV1 package;
    package.packageName = canonical.packageName;
    package.userId = canonical.userId;
    package.userState = "INSTALLED";
    package.lifecycle = "ACTIVE";
    package.generation = canonical.generation;
    package.canonicalDigest = canonical.canonicalDigest;
    package.readiness = "READY";
    GetPackageResponseV1 response = MakeResponse(
        request, PackageQueryVerdict::READY, "READY", read.catalogRevision);
    response.package = std::move(package);
    if (faultInjector_->InterruptAfter(QueryPhase::RESPONSE_SERIALIZED)) {
        response.package.reset();
        response.verdict = PackageQueryVerdict::PACKAGE_NOT_READY;
        response.reason = "QUERY_INTERRUPTED_RETRY";
    }
    return response;
}

const char* PackageQueryVerdictName(PackageQueryVerdict verdict)
{
    switch (verdict) {
        case PackageQueryVerdict::READY: return "READY";
        case PackageQueryVerdict::INVALID_REQUEST: return "INVALID_REQUEST";
        case PackageQueryVerdict::NOT_SUPPORTED: return "NOT_SUPPORTED";
        case PackageQueryVerdict::PACKAGE_NOT_FOUND: return "PACKAGE_NOT_FOUND";
        case PackageQueryVerdict::PACKAGE_NOT_VISIBLE:
            return "PACKAGE_NOT_VISIBLE";
        case PackageQueryVerdict::PACKAGE_REMOVING: return "PACKAGE_REMOVING";
        case PackageQueryVerdict::PACKAGE_NOT_READY:
            return "PACKAGE_NOT_READY";
        case PackageQueryVerdict::DATA_INCONSISTENT: return "DATA_INCONSISTENT";
    }
    return "DATA_INCONSISTENT";
}

}  // namespace oh_adapter::package_query
