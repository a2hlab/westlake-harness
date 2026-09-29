#ifndef OH_ADAPTER_MANIFEST_FACTS_V1_H
#define OH_ADAPTER_MANIFEST_FACTS_V1_H

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

#include "package_transaction_v1.h"
#include "manifest_version_v2.h"
#include "sdk_declaration_v2.h"

namespace oh_adapter::manifest_facts {

enum class ManifestParseVerdict {
    PARSED,
    INVALID_ENVELOPE,
    NOT_SUPPORTED,
    FD_NOT_SEALED,
    BYTE_LENGTH_MISMATCH,
    DIGEST_MISMATCH,
    ARTIFACT_SET_MISMATCH,
    ZIP_MALFORMED,
    MANIFEST_NOT_FOUND,
    MANIFEST_DUPLICATE,
    MANIFEST_MALFORMED,
    DECLARATION_CONFLICT,
    LIMIT_EXCEEDED,
    IO_ERROR,
    INTERRUPTED,
    INTERNAL_ERROR,
};

enum class ManifestParseFault {
    NONE,
    INTERRUPT_AFTER_IDENTITY_READ,
    FORCE_INTERNAL_ERROR,
};

struct ManifestParserLimitsV1 {
    uint64_t maxArtifactBytes = 256ULL * 1024ULL * 1024ULL;
    uint32_t maxZipMembers = 4096;
    uint64_t maxManifestCompressedBytes = 8ULL * 1024ULL * 1024ULL;
    uint64_t maxManifestBytes = 16ULL * 1024ULL * 1024ULL;
    uint32_t maxComponents = 65536;
};

using ManifestFactsOutputV1 = package_transaction::ManifestFactsV1;

struct ManifestParseRequestV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    uint32_t userId = 0;
    int artifactFd = -1;
    uint64_t byteLength = 0;
    std::string artifactSha256;
    package_transaction::PackageArtifactSetV1 artifactSet;
    bool requireLinuxSeals = true;
    std::optional<SdkProfileV2> sdkProfile;
    bool apkInApex = false;
};

struct ManifestParseReceiptV1 {
    std::string requestId;
    ManifestParseVerdict verdict = ManifestParseVerdict::INTERNAL_ERROR;
    std::string reason;
    std::string artifactSha256;
    std::string artifactSetDigest;
    std::string parserVersion;
    std::optional<ManifestFactsOutputV1> facts;
    ManifestVersionV2 versionV2;
    std::vector<UsesSdkDeclarationV2> sdkDeclarations;
    std::optional<SdkCompatibilityResultV2> sdkCompatibility;
};

class ManifestFactsParserV1 {
public:
    explicit ManifestFactsParserV1(
        ManifestParserLimitsV1 limits = ManifestParserLimitsV1 {});

    ManifestParseReceiptV1 Parse(const ManifestParseRequestV1& request,
        ManifestParseFault fault = ManifestParseFault::NONE) const;

private:
    ManifestParserLimitsV1 limits_;
};

const char* ManifestParseVerdictName(ManifestParseVerdict verdict);
std::string ManifestParseReceiptJson(const ManifestParseReceiptV1& receipt);

}  // namespace oh_adapter::manifest_facts

#endif  // OH_ADAPTER_MANIFEST_FACTS_V1_H
