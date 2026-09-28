#ifndef OH_ADAPTER_SIGNING_METADATA_V1_H
#define OH_ADAPTER_SIGNING_METADATA_V1_H

#include "apk_verify_result.h"
#include "package_transaction_v1.h"

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace oh_adapter::signing_metadata {

enum class SigningMetadataVerdict {
    VERIFIED,
    INVALID_REQUEST,
    UNKNOWN_SCHEMA,
    POLICY_NOT_FOUND,
    POLICY_MISMATCH,
    NOT_SUPPORTED_ARTIFACT_PROFILE,
    NOT_SUPPORTED_SCHEME,
    ARTIFACT_DIGEST_MISMATCH,
    ARTIFACT_CHANGED_DURING_VERIFY,
    SIGNATURE_INVALID,
    BAD_LINEAGE,
    UPDATE_INCOMPATIBLE,
    PERSIST_FAILED,
    READBACK_FAILED,
    DATA_INCONSISTENT,
    INTERRUPTED,
};

enum class SigningMetadataFaultPoint {
    AFTER_ARTIFACT_FREEZE,
    AFTER_CRYPTOGRAPHIC_VERIFY,
    AFTER_RECEIPT_PERSIST,
    AFTER_RECEIPT_READBACK,
};

class SigningMetadataFaultInjector {
public:
    virtual ~SigningMetadataFaultInjector() = default;
    virtual bool InterruptAfter(SigningMetadataFaultPoint point) = 0;
};

class NoSigningMetadataFaultInjector final
    : public SigningMetadataFaultInjector {
public:
    bool InterruptAfter(SigningMetadataFaultPoint) override
    {
        return false;
    }
};

struct SigningMetadataPolicyV1 {
    uint32_t schemaVersion = 1;
    std::string policyVersion;
    std::string verifierVersion;
    uint32_t minimumSchemeVersion = 2;
    uint32_t targetPlatformSdk = 35;
};

class SigningMetadataPolicyProvider {
public:
    virtual ~SigningMetadataPolicyProvider() = default;
    virtual bool Resolve(const std::string& policyVersion,
        SigningMetadataPolicyV1* policy, std::string* error) const = 0;
};

struct PriorSigningFactsV1 {
    std::vector<Sha256Digest> currentSignerSha256;
    std::vector<ApkLineageCertificate> lineage;
};

struct SigningMetadataRequestV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    package_transaction::PackageArtifactSetV1 artifactSet;
    SigningMetadataPolicyV1 policy;
    std::optional<PriorSigningFactsV1> priorSigningFacts;
};

struct SigningContentDigestFactV1 {
    std::string algorithm;
    std::string sha256OrDigestHex;
};

struct SigningSignerFactV1 {
    std::string certificateSha256;
    std::string subject;
};

struct SigningLineageFactV1 {
    std::string certificateSha256;
    uint32_t capabilities = 0;
};

struct SigningContinuityDecisionV1 {
    std::string priorSigningFactsDigest;
    bool allowed = false;
    std::string capabilityPath;
    std::string decisionDigest;
};

// Durable verifier truth. requestId is intentionally excluded from this
// identity and is carried by SigningMetadataResponseV1 only.
struct SigningMetadataReceiptV1 {
    uint32_t schemaVersion = 1;
    std::string actionId = "Fn01.A13";
    std::string artifactSha256;
    std::string artifactSetDigest;
    std::string policyVersion;
    std::string verifierVersion;
    uint32_t schemeVersion = 0;
    std::vector<SigningSignerFactV1> signers;
    std::vector<SigningContentDigestFactV1> contentDigests;
    std::vector<SigningLineageFactV1> lineage;
    std::optional<std::string> lineageDigest;
    std::string verificationTranscriptSha256;
    std::string receiptDigest;
    // Request-specific attestation bound to receiptDigest. It is returned
    // after durable receipt readback but is not part of the durable logical
    // key, so multiple update checks cannot overwrite verifier truth.
    std::optional<SigningContinuityDecisionV1> continuityDecision;
};

struct SigningMetadataResponseV1 {
    std::string requestId;
    SigningMetadataVerdict verdict =
        SigningMetadataVerdict::DATA_INCONSISTENT;
    std::optional<SigningMetadataReceiptV1> receipt;
    std::string negativeReason;
    bool signerTruthVisible = false;
    bool replayed = false;
};

enum class SigningReceiptReadResult {
    FOUND,
    ABSENT,
    ERROR,
};

class SigningMetadataReceiptStore {
public:
    virtual ~SigningMetadataReceiptStore() = default;
    virtual SigningReceiptReadResult Read(const std::string& receiptKey,
        SigningMetadataReceiptV1* receipt, std::string* error) const = 0;
    virtual bool Persist(const std::string& receiptKey,
        const SigningMetadataReceiptV1& receipt, std::string* error) = 0;
};

class FileSigningMetadataReceiptStore final
    : public SigningMetadataReceiptStore {
public:
    explicit FileSigningMetadataReceiptStore(std::string root);

    bool Open(std::string* error);
    SigningReceiptReadResult Read(const std::string& receiptKey,
        SigningMetadataReceiptV1* receipt,
        std::string* error) const override;
    bool Persist(const std::string& receiptKey,
        const SigningMetadataReceiptV1& receipt,
        std::string* error) override;

private:
    std::string root_;
};

class SigningMetadataServiceV1 {
public:
    SigningMetadataServiceV1(SigningMetadataReceiptStore* store,
        const SigningMetadataPolicyProvider* policyProvider,
        SigningMetadataFaultInjector* faultInjector);

    SigningMetadataResponseV1 VerifyAndPersist(
        int sealedArtifactFd,
        const SigningMetadataRequestV1& request) const;

private:
    SigningMetadataReceiptStore* store_;
    const SigningMetadataPolicyProvider* policyProvider_;
    SigningMetadataFaultInjector* faultInjector_;
};

const char* SigningMetadataVerdictName(SigningMetadataVerdict verdict);
std::string SerializeSigningMetadataResponseJsonV1(
    const SigningMetadataResponseV1& response);

}  // namespace oh_adapter::signing_metadata

#endif  // OH_ADAPTER_SIGNING_METADATA_V1_H
