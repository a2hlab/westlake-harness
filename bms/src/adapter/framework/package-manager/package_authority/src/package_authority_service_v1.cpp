#include "package_authority_service_v1.h"

#include <vector>

namespace oh_adapter::package_authority {
namespace {

AuthorityInstallReceiptV1 MakeInstallReceipt(
    const package_transaction::PackageLifecycleReceiptV1& canonical,
    AuthorityInstallVerdict verdict, const char* reason,
    bool consumerReady = false)
{
    AuthorityInstallReceiptV1 result;
    result.verdict = verdict;
    result.canonicalReceipt = canonical;
    result.consumerReady = consumerReady;
    result.reason = reason;
    return result;
}

LaunchResolutionResponseV1 MakeLaunchResponse(
    const LaunchResolutionRequestV1& request,
    LaunchResolutionVerdict verdict, const char* reason)
{
    LaunchResolutionResponseV1 response;
    response.requestId = request.requestId;
    response.verdict = verdict;
    response.reason = reason;
    return response;
}

bool IsExternallyReady(
    const package_transaction::PackageManagementReadV1& read)
{
    if (!read.canonical.has_value() ||
        !read.publicationToken.has_value() ||
        !read.projection.has_value()) {
        return false;
    }
    const auto& canonical = *read.canonical;
    const auto& token = *read.publicationToken;
    const auto& projection = *read.projection;
    return canonical.publicationState ==
            package_transaction::PublicationState::CANONICAL_SELECTED &&
        token.state == package_transaction::PublicationState::EXTERNAL_READY &&
        projection.state ==
            package_transaction::HostProjectionState::ACTIVE &&
        token.packageName == canonical.packageName &&
        token.userId == canonical.userId &&
        token.generation == canonical.generation &&
        token.canonicalDigest == canonical.canonicalDigest &&
        projection.packageName == canonical.packageName &&
        projection.userId == canonical.userId &&
        projection.generation == canonical.generation &&
        projection.canonicalDigest == canonical.canonicalDigest;
}

}  // namespace

PackageAuthorityServiceV1::PackageAuthorityServiceV1(
    package_transaction::FilePackageStore* store,
    package_transaction::PackageFileStager* stager,
    package_transaction::FaultInjector* faultInjector,
    BmsExecutionCarrierV1* carrier)
    : store_(store), coordinator_(store, stager, faultInjector),
      carrier_(carrier)
{
}

AuthorityInstallReceiptV1 PackageAuthorityServiceV1::Install(
    const package_transaction::InstallRequestV1& request)
{
    if (store_ == nullptr || carrier_ == nullptr) {
        return MakeInstallReceipt({}, AuthorityInstallVerdict::CANONICAL_REJECTED,
            "AUTHORITY_DEPENDENCY_MISSING");
    }

    const package_transaction::PackageLifecycleReceiptV1 canonical =
        coordinator_.Install(request);
    if (canonical.verdict !=
            package_transaction::InstallVerdict::COMMITTED ||
        !canonical.packageName.has_value() ||
        !canonical.generation.has_value() ||
        !canonical.durableRecordDigest.has_value()) {
        return MakeInstallReceipt(canonical,
            AuthorityInstallVerdict::CANONICAL_REJECTED,
            "CANONICAL_INSTALL_NOT_COMMITTED");
    }

    package_transaction::PackageManagementReadV1 before;
    std::string error;
    if (!store_->ReadPackageManagementState(request.userId,
            *canonical.packageName, &before, &error) ||
        !before.canonical.has_value()) {
        return MakeInstallReceipt(canonical,
            AuthorityInstallVerdict::AUTHORITY_STORE_FAILED,
            "CANONICAL_READBACK_FAILED");
    }
    if (IsExternallyReady(before)) {
        return MakeInstallReceipt(canonical, AuthorityInstallVerdict::READY,
            "IDEMPOTENT_READY_REPLAY", true);
    }

    const auto& snapshot = *before.canonical;
    if (snapshot.packageName != *canonical.packageName ||
        snapshot.userId != request.userId ||
        snapshot.generation != *canonical.generation ||
        snapshot.canonicalDigest != *canonical.durableRecordDigest) {
        return MakeInstallReceipt(canonical,
            AuthorityInstallVerdict::AUTHORITY_STORE_FAILED,
            "CANONICAL_IDENTITY_MISMATCH");
    }

    BmsProjectionCommandV1 command;
    command.idempotencyKey = canonical.transactionId;
    command.packageName = snapshot.packageName;
    command.userId = snapshot.userId;
    command.generation = snapshot.generation;
    command.canonicalDigest = snapshot.canonicalDigest;
    command.artifactSetDigest = snapshot.artifactSetDigest;
    command.baseCodePath = snapshot.managedFiles.baseCodePath;
    command.baseCodeDigest = snapshot.managedFiles.baseCodeDigest;
    if (snapshot.manifestFacts.has_value()) {
        command.manifest = *snapshot.manifestFacts;
    }
    BmsProjectionReadbackV1 readback;
    if (!carrier_->EnsureActive(command, &readback) || !readback.active) {
        return MakeInstallReceipt(canonical,
            AuthorityInstallVerdict::CARRIER_FAILED,
            "BMS_CARRIER_DID_NOT_ESTABLISH_ACTIVE");
    }
    if (readback.idempotencyKey != command.idempotencyKey ||
        readback.packageName != command.packageName ||
        readback.userId != command.userId ||
        readback.generation != command.generation ||
        readback.canonicalDigest != command.canonicalDigest) {
        return MakeInstallReceipt(canonical,
            AuthorityInstallVerdict::CARRIER_READBACK_MISMATCH,
            "BMS_CARRIER_READBACK_IDENTITY_MISMATCH");
    }

    if (!store_->CommitExternalReady(command.userId, command.packageName,
            command.generation, command.canonicalDigest, &error)) {
        return MakeInstallReceipt(canonical,
            AuthorityInstallVerdict::AUTHORITY_STORE_FAILED,
            "EXTERNAL_READY_COMMIT_FAILED");
    }
    package_transaction::PackageManagementReadV1 after;
    if (!store_->ReadPackageManagementState(command.userId,
            command.packageName, &after, &error) ||
        !IsExternallyReady(after)) {
        return MakeInstallReceipt(canonical,
            AuthorityInstallVerdict::AUTHORITY_STORE_FAILED,
            "EXTERNAL_READY_READBACK_FAILED");
    }
    return MakeInstallReceipt(canonical, AuthorityInstallVerdict::READY,
        "READY", true);
}

package_query::GetPackageResponseV1 PackageAuthorityServiceV1::Query(
    const package_query::GetPackageRequestV1& request) const
{
    package_query::NoQueryFaultInjector noFault;
    package_query::PackageQueryService query(store_, &noFault);
    return query.GetPackage(request);
}

LaunchResolutionResponseV1 PackageAuthorityServiceV1::ResolveLaunch(
    const LaunchResolutionRequestV1& request) const
{
    if (store_ == nullptr || request.schemaVersion != 1 ||
        request.requestId.empty() || request.packageName.empty() ||
        request.caller.callerId.empty() ||
        request.caller.visibilityScopeDigest.empty()) {
        return MakeLaunchResponse(request,
            LaunchResolutionVerdict::INVALID_REQUEST, "INVALID_REQUEST");
    }

    package_query::GetPackageRequestV1 queryRequest;
    queryRequest.requestId = request.requestId;
    queryRequest.packageName = request.packageName;
    queryRequest.userId = request.userId;
    queryRequest.caller = request.caller;
    const auto query = Query(queryRequest);
    if (query.verdict != package_query::PackageQueryVerdict::READY ||
        !query.package.has_value()) {
        return MakeLaunchResponse(request,
            LaunchResolutionVerdict::PACKAGE_NOT_READY,
            package_query::PackageQueryVerdictName(query.verdict));
    }

    package_transaction::PackageManagementReadV1 read;
    std::string error;
    if (!store_->ReadPackageManagementState(request.userId,
            request.packageName, &read, &error) ||
        !IsExternallyReady(read) || !read.canonical.has_value() ||
        !read.canonical->manifestFacts.has_value()) {
        return MakeLaunchResponse(request,
            LaunchResolutionVerdict::DATA_INCONSISTENT,
            "AUTHORITY_SNAPSHOT_INCONSISTENT");
    }

    std::vector<std::string> candidates;
    for (const auto& component :
        read.canonical->manifestFacts->components) {
        if ((component.kind == "activity" ||
                component.kind == "activity-alias") &&
            component.exported.value_or(false) &&
            (!request.activityName.has_value() ||
                component.name == *request.activityName)) {
            candidates.push_back(component.name);
        }
    }
    if (candidates.empty()) {
        return MakeLaunchResponse(request,
            LaunchResolutionVerdict::COMPONENT_NOT_FOUND,
            "EXPORTED_ACTIVITY_NOT_FOUND");
    }
    if (candidates.size() != 1) {
        return MakeLaunchResponse(request,
            LaunchResolutionVerdict::AMBIGUOUS_COMPONENT,
            "EXPORTED_ACTIVITY_AMBIGUOUS");
    }

    LaunchResolutionV1 resolution;
    resolution.packageName = request.packageName;
    resolution.activityName = candidates.front();
    resolution.userId = request.userId;
    resolution.generation = read.canonical->generation;
    resolution.canonicalDigest = read.canonical->canonicalDigest;
    LaunchResolutionResponseV1 response = MakeLaunchResponse(
        request, LaunchResolutionVerdict::READY, "READY");
    response.resolution = std::move(resolution);
    return response;
}

package_transaction::RestartRecoveryReceiptV1
PackageAuthorityServiceV1::Recover(
    const package_transaction::RestartRecoveryRequestV1& request)
{
    if (store_ == nullptr) {
        package_transaction::RestartRecoveryReceiptV1 result;
        result.requestId = request.requestId;
        result.transactionId = request.transactionId;
        result.verdict =
            package_transaction::RestartRecoveryVerdict::DATA_INCONSISTENT;
        result.terminalState = "FAIL_CLOSED";
        result.reason = "authority store missing";
        return result;
    }
    package_transaction::RestartRecoveryReceiptV1 result =
        store_->RecoverAfterRestart(request);
    if (result.verdict !=
            package_transaction::RestartRecoveryVerdict::RESTORED_COMMITTED ||
        result.consumerReady) {
        return result;
    }
    if (carrier_ == nullptr || !result.packageName.has_value() ||
        !result.generation.has_value() ||
        !result.canonicalDigest.has_value()) {
        result.verdict =
            package_transaction::RestartRecoveryVerdict::NON_READY;
        result.terminalState = "RECOVERING_FORWARD";
        result.reason = "BMS carrier unavailable for forward recovery";
        return result;
    }

    BmsProjectionCommandV1 command;
    command.idempotencyKey = result.transactionId;
    command.packageName = *result.packageName;
    command.userId = result.primaryUserState.has_value()
        ? result.primaryUserState->userId : 0;
    command.generation = *result.generation;
    command.canonicalDigest = *result.canonicalDigest;
    package_transaction::PackageManagementReadV1 read;
    std::string error;
    if (!store_->ReadPackageManagementState(command.userId,
            command.packageName, &read, &error) ||
        !read.canonical.has_value()) {
        result.verdict =
            package_transaction::RestartRecoveryVerdict::NON_READY;
        result.terminalState = "RECOVERING_FORWARD";
        result.reason = "canonical payload unavailable for forward recovery";
        return result;
    }
    command.artifactSetDigest = read.canonical->artifactSetDigest;
    command.baseCodePath = read.canonical->managedFiles.baseCodePath;
    command.baseCodeDigest = read.canonical->managedFiles.baseCodeDigest;
    if (read.canonical->manifestFacts.has_value()) {
        command.manifest = *read.canonical->manifestFacts;
    }
    BmsProjectionReadbackV1 readback;
    if (!carrier_->EnsureActive(command, &readback) || !readback.active ||
        readback.idempotencyKey != command.idempotencyKey ||
        readback.packageName != command.packageName ||
        readback.userId != command.userId ||
        readback.generation != command.generation ||
        readback.canonicalDigest != command.canonicalDigest) {
        result.verdict =
            package_transaction::RestartRecoveryVerdict::NON_READY;
        result.terminalState = "RECOVERING_FORWARD";
        result.reason = "BMS carrier forward recovery not established";
        return result;
    }
    if (!store_->CommitExternalReady(command.userId, command.packageName,
            command.generation, command.canonicalDigest, &error)) {
        result.verdict =
            package_transaction::RestartRecoveryVerdict::NON_READY;
        result.terminalState = "RECOVERING_FORWARD";
        result.reason = "external-ready forward recovery commit failed";
        return result;
    }
    result = store_->RecoverAfterRestart(request);
    if (!result.consumerReady) {
        result.verdict =
            package_transaction::RestartRecoveryVerdict::NON_READY;
        result.terminalState = "RECOVERING_FORWARD";
        result.reason = "external-ready forward recovery readback failed";
    }
    return result;
}

const char* AuthorityInstallVerdictName(AuthorityInstallVerdict verdict)
{
    switch (verdict) {
        case AuthorityInstallVerdict::READY: return "READY";
        case AuthorityInstallVerdict::CANONICAL_REJECTED:
            return "CANONICAL_REJECTED";
        case AuthorityInstallVerdict::CARRIER_FAILED:
            return "CARRIER_FAILED";
        case AuthorityInstallVerdict::CARRIER_READBACK_MISMATCH:
            return "CARRIER_READBACK_MISMATCH";
        case AuthorityInstallVerdict::AUTHORITY_STORE_FAILED:
            return "AUTHORITY_STORE_FAILED";
    }
    return "AUTHORITY_STORE_FAILED";
}

const char* LaunchResolutionVerdictName(LaunchResolutionVerdict verdict)
{
    switch (verdict) {
        case LaunchResolutionVerdict::READY: return "READY";
        case LaunchResolutionVerdict::INVALID_REQUEST:
            return "INVALID_REQUEST";
        case LaunchResolutionVerdict::PACKAGE_NOT_READY:
            return "PACKAGE_NOT_READY";
        case LaunchResolutionVerdict::COMPONENT_NOT_FOUND:
            return "COMPONENT_NOT_FOUND";
        case LaunchResolutionVerdict::AMBIGUOUS_COMPONENT:
            return "AMBIGUOUS_COMPONENT";
        case LaunchResolutionVerdict::DATA_INCONSISTENT:
            return "DATA_INCONSISTENT";
    }
    return "DATA_INCONSISTENT";
}

}  // namespace oh_adapter::package_authority
