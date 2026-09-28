#ifndef OH_ADAPTER_PACKAGE_LAYOUT_V1_H
#define OH_ADAPTER_PACKAGE_LAYOUT_V1_H

#include <cstdint>
#include <string>
#include <vector>

namespace oh_adapter::package_layout {

enum class LayoutVerdict {
    FINALIZED,
    INVALID_REQUEST,
    NOT_SUPPORTED_USER,
    NOT_SUPPORTED_ABI,
    VERIFIED_RECEIPT_MISMATCH,
    MANAGED_ROOT_POLICY_MISMATCH,
    PATH_REJECTED,
    SYMLINK_ESCAPE,
    PERMISSION_DENIED,
    NO_SPACE,
    TRANSACTION_CONFLICT,
    IO_ERROR,
    DATA_INCONSISTENT,
    INTERRUPTED,
};

enum class LayoutFaultPhase {
    AFTER_PLAN_DURABLE,
    DURING_COPY,
    AFTER_FILE_FSYNC,
    BEFORE_RENAME,
    AFTER_RENAME,
    BEFORE_READBACK,
    AFTER_RECEIPT_DURABLE,
};

enum class LayoutFaultDecision {
    NONE,
    FAIL_IO,
    FAIL_NO_SPACE,
    FAIL_PERMISSION,
    INTERRUPT,
};

struct VerifiedArtifactReceiptV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    std::string transactionId;
    std::string packageName;
    std::string artifactSetDigest;
    std::string artifactSha256;
    uint64_t byteLength = 0;
    std::string policyVersion;
    std::string verifierVersion;
    bool verified = false;
};

struct FilePlanV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    std::string transactionId;
    std::string callerScopeDigest;
    uint32_t userId = 0;
    std::string packageName;
    uint64_t generation = 0;
    std::string artifactSetDigest;
    std::string managedRootPolicyId;
    std::vector<std::string> nativeAbis;
};

struct ManagedRootPolicyV1 {
    uint32_t schemaVersion = 1;
    std::string policyId;
    std::vector<std::string> permittedCanonicalRoots;
};

struct FinalizedFileV1 {
    std::string path;
    std::string sha256;
    uint64_t byteLength = 0;
};

struct PackageLayoutReceiptV1 {
    uint32_t schemaVersion = 1;
    std::string actionId = "Fn01.A07";
    std::string requestId;
    std::string transactionId;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string artifactSetDigest;
    std::string managedRootPolicyId;
    std::string terminalState;
    std::string reason;
    LayoutVerdict verdict = LayoutVerdict::DATA_INCONSISTENT;
    FinalizedFileV1 baseCode;
};

class LayoutFaultInjector {
public:
    virtual ~LayoutFaultInjector() = default;
    virtual LayoutFaultDecision At(LayoutFaultPhase phase) = 0;
};

class NoLayoutFaultInjector final : public LayoutFaultInjector {
public:
    LayoutFaultDecision At(LayoutFaultPhase) override
    {
        return LayoutFaultDecision::NONE;
    }
};

class PackageLayoutV1 final {
public:
    PackageLayoutV1(
        std::string managedRoot, ManagedRootPolicyV1 managedRootPolicy);

    PackageLayoutReceiptV1 Finalize(const FilePlanV1& plan,
        const VerifiedArtifactReceiptV1& verifiedArtifact, int artifactFd,
        LayoutFaultInjector* faultInjector);

    static const char* VerdictName(LayoutVerdict verdict);
    static std::string SerializeReceipt(const PackageLayoutReceiptV1& receipt);

private:
    std::string managedRoot_;
    ManagedRootPolicyV1 managedRootPolicy_;
};

}  // namespace oh_adapter::package_layout

#endif  // OH_ADAPTER_PACKAGE_LAYOUT_V1_H
