#ifndef OH_ADAPTER_PACKAGE_AUTHORITY_SERVICE_V1_H
#define OH_ADAPTER_PACKAGE_AUTHORITY_SERVICE_V1_H

#include "package_query_v1.h"
#include "package_transaction_v1.h"

#include <cstdint>
#include <optional>
#include <string>

namespace oh_adapter::package_authority {

struct BmsProjectionCommandV1 {
    std::string idempotencyKey;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    std::string artifactSetDigest;
    std::string baseCodePath;
    std::string baseCodeDigest;
    package_transaction::ManifestFactsV1 manifest;
};

struct BmsProjectionReadbackV1 {
    std::string idempotencyKey;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    bool active = false;
    std::string reason;
};

class BmsExecutionCarrierV1 {
public:
    virtual ~BmsExecutionCarrierV1() = default;

    // BMS executes a generation-bound projection and returns readback only.
    // It has no authority-store handle and cannot publish semantic readiness.
    virtual bool EnsureActive(const BmsProjectionCommandV1& command,
        BmsProjectionReadbackV1* readback) = 0;
};

enum class AuthorityInstallVerdict {
    READY,
    CANONICAL_REJECTED,
    CARRIER_FAILED,
    CARRIER_READBACK_MISMATCH,
    AUTHORITY_STORE_FAILED,
};

struct AuthorityInstallReceiptV1 {
    AuthorityInstallVerdict verdict =
        AuthorityInstallVerdict::AUTHORITY_STORE_FAILED;
    package_transaction::PackageLifecycleReceiptV1 canonicalReceipt;
    bool consumerReady = false;
    std::string reason;
};

enum class LaunchResolutionVerdict {
    READY,
    INVALID_REQUEST,
    PACKAGE_NOT_READY,
    COMPONENT_NOT_FOUND,
    AMBIGUOUS_COMPONENT,
    DATA_INCONSISTENT,
};

struct LaunchResolutionRequestV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    std::string packageName;
    uint32_t userId = 0;
    package_query::CallerContextV1 caller;
    std::optional<std::string> activityName;
};

struct LaunchResolutionV1 {
    std::string packageName;
    std::string activityName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
};

struct LaunchResolutionResponseV1 {
    std::string requestId;
    LaunchResolutionVerdict verdict =
        LaunchResolutionVerdict::DATA_INCONSISTENT;
    std::string reason;
    std::optional<LaunchResolutionV1> resolution;
};

class PackageAuthorityServiceV1 {
public:
    PackageAuthorityServiceV1(
        package_transaction::FilePackageStore* store,
        package_transaction::PackageFileStager* stager,
        package_transaction::FaultInjector* faultInjector,
        BmsExecutionCarrierV1* carrier);

    AuthorityInstallReceiptV1 Install(
        const package_transaction::InstallRequestV1& request);
    package_query::GetPackageResponseV1 Query(
        const package_query::GetPackageRequestV1& request) const;
    LaunchResolutionResponseV1 ResolveLaunch(
        const LaunchResolutionRequestV1& request) const;
    package_transaction::RestartRecoveryReceiptV1 Recover(
        const package_transaction::RestartRecoveryRequestV1& request);

private:
    package_transaction::FilePackageStore* store_;
    package_transaction::PackageTransactionCoordinator coordinator_;
    BmsExecutionCarrierV1* carrier_;
};

const char* AuthorityInstallVerdictName(AuthorityInstallVerdict verdict);
const char* LaunchResolutionVerdictName(LaunchResolutionVerdict verdict);

}  // namespace oh_adapter::package_authority

#endif  // OH_ADAPTER_PACKAGE_AUTHORITY_SERVICE_V1_H
