/**
 * Strict parser and policy helpers for ApkSignatureBridge ASV1 responses.
 */
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace oh_adapter {

constexpr size_t kApkSha256Bytes = 32;
constexpr size_t kMaxApkSignerCertificates = 64;
constexpr uint32_t kApkSignerCapabilityInstalledData = 1u;
constexpr uint32_t kApkSignerCapabilityRollback = 8u;

using Sha256Digest = std::array<uint8_t, kApkSha256Bytes>;

struct ApkLineageCertificate {
    Sha256Digest sha256{};
    uint32_t capabilities = 0;
};

struct ApkVerifiedContentDigest {
    uint32_t signatureAlgorithmId = 0;
    std::vector<uint8_t> digest;
};

struct ApkVerifiedIdentity {
    uint16_t schemeVersion = 0;
    uint32_t v3BlockId = 0;
    Sha256Digest apkSha256{};
    std::vector<Sha256Digest> currentSignerSha256;
    // Exact leaf X.509 DER bytes verified for each current signer. Digest-only
    // identity is insufficient for Android PackageInfo.Signature projection.
    std::vector<std::vector<uint8_t>> currentSignerCertificateDer;
    // Exact v2/v3 content digests that were recomputed from the APK bytes and
    // matched against the signed-data record. V1 verification instead proves
    // every non-META-INF entry against MANIFEST.MF.
    std::vector<ApkVerifiedContentDigest> verifiedContentDigests;
    std::vector<ApkLineageCertificate> lineage;
};

bool ParseApkVerifyResult(const uint8_t* data, size_t size,
                          ApkVerifiedIdentity* out, std::string* error);

bool IsApkUpdateAllowed(const ApkVerifiedIdentity& oldIdentity,
                        const ApkVerifiedIdentity& newIdentity);

std::string Sha256ToLowerHex(const Sha256Digest& digest);

}  // namespace oh_adapter
