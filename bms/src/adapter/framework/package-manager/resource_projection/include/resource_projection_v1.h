#ifndef OH_ADAPTER_RESOURCE_PROJECTION_V1_H
#define OH_ADAPTER_RESOURCE_PROJECTION_V1_H

#include "package_layout_v1.h"

#include <cstdint>
#include <string>
#include <vector>

namespace oh_adapter::resource_projection {

enum class ResourceProjectionVerdict {
    READY,
    CLEANED,
    INVALID_REQUEST,
    NOT_SUPPORTED_USER,
    NOT_SUPPORTED_TARGET,
    LAYOUT_RECEIPT_MISMATCH,
    CALLER_SCOPE_MISMATCH,
    RESOURCE_NOT_FOUND,
    UNSUPPORTED_CONFIGURATION,
    INVALID_RESOURCE_PAYLOAD,
    TRANSACTION_CONFLICT,
    SYMLINK_ESCAPE,
    PERMISSION_DENIED,
    NO_SPACE,
    IO_ERROR,
    DATA_INCONSISTENT,
    INTERRUPTED,
};

enum class ResourcePresentationStatus {
    RESOLVED,
    NONE,
    MISSING,
    UNSUPPORTED_CONFIGURATION,
    INVALID,
};

enum class ResourceProjectionFaultPhase {
    AFTER_PREPARED_DURABLE,
    DURING_PAYLOAD_WRITE,
    AFTER_PAYLOAD_FSYNC,
    BEFORE_READY_DURABLE,
    AFTER_READY_DURABLE,
    BEFORE_READBACK,
    AFTER_RECEIPT_DURABLE,
};

enum class ResourceProjectionFaultDecision {
    NONE,
    FAIL_IO,
    FAIL_NO_SPACE,
    FAIL_PERMISSION,
    INTERRUPT,
    CORRUPT_PAYLOAD,
};

struct ResourceFactsV1 {
    uint32_t schemaVersion = 1;
    ResourcePresentationStatus presentationStatus =
        ResourcePresentationStatus::INVALID;
    std::string componentName;
    std::string configurationHash;
    std::string label;
    std::vector<uint8_t> iconBytes;
    std::string iconContentType;
    std::string sourceArtifactSha256;
};

struct ResourceProjectionPolicyV1 {
    uint32_t schemaVersion = 1;
    std::string policyVersion;
    std::string expectedCallerScopeDigest;
    uint64_t maxLabelBytes = 4096;
    uint64_t maxIconBytes = 8 * 1024 * 1024;
};

struct ResourceProjectionRequestV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    std::string transactionId;
    std::string callerScopeDigest;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    std::string buildPolicyVersion;
    std::string presentationTarget;
    oh_adapter::package_layout::PackageLayoutReceiptV1 layoutReceipt;
    ResourceFactsV1 resourceFacts;
};

struct ResourceProjectionReceiptV1 {
    uint32_t schemaVersion = 1;
    std::string actionId = "Fn01.A08";
    std::string requestId;
    std::string transactionId;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string payloadKind;
    std::string resourceInputDigest;
    std::string resourcePayloadDigest;
    std::string canonicalDigest;
    std::string buildPolicyVersion;
    std::string state;
    std::string payloadPath;
    std::string componentName;
    std::string configurationHash;
    std::string label;
    ResourceProjectionVerdict verdict =
        ResourceProjectionVerdict::DATA_INCONSISTENT;
    std::string reason;
};

struct ResourceCleanupObligationV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    std::string transactionId;
    std::string callerScopeDigest;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    std::string resourcePayloadDigest;
    std::string cause;
};

class ResourceProjectionFaultInjector {
public:
    virtual ~ResourceProjectionFaultInjector() = default;
    virtual ResourceProjectionFaultDecision At(
        ResourceProjectionFaultPhase phase) = 0;
};

class NoResourceProjectionFaultInjector final
    : public ResourceProjectionFaultInjector {
public:
    ResourceProjectionFaultDecision At(
        ResourceProjectionFaultPhase) override
    {
        return ResourceProjectionFaultDecision::NONE;
    }
};

class ResourceProjectionBuilderV1 final {
public:
    ResourceProjectionBuilderV1(
        std::string managedRoot, ResourceProjectionPolicyV1 policy);

    ResourceProjectionReceiptV1 Build(
        const ResourceProjectionRequestV1& request,
        ResourceProjectionFaultInjector* faultInjector);

    ResourceProjectionReceiptV1 Cleanup(
        const ResourceCleanupObligationV1& obligation);

    static const char* VerdictName(ResourceProjectionVerdict verdict);
    static const char* PresentationStatusName(
        ResourcePresentationStatus status);
    static std::string SerializeReceipt(
        const ResourceProjectionReceiptV1& receipt);

private:
    std::string managedRoot_;
    ResourceProjectionPolicyV1 policy_;
};

}  // namespace oh_adapter::resource_projection

#endif  // OH_ADAPTER_RESOURCE_PROJECTION_V1_H
