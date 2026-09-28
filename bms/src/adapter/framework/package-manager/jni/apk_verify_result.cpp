#include "apk_verify_result.h"

#include <algorithm>
#include <cstring>
#include <openssl/sha.h>
#include <set>

namespace oh_adapter {
namespace {

constexpr uint32_t kResultMagic = 0x41535631u;  // ASV1
constexpr uint16_t kResultVersion = 1;
constexpr uint16_t kSchemeV2 = 2;
constexpr uint16_t kSchemeV3 = 3;
constexpr uint32_t kV3BlockId = 0xf05368c0u;
constexpr uint32_t kV31BlockId = 0x1b93ad61u;
constexpr uint32_t kKnownCapabilityMask = 0x1fu;
constexpr size_t kMaxCertificateBytes = 16 * 1024u;

class Reader {
public:
    Reader(const uint8_t* data, size_t size) : cursor_(data), remaining_(size) {}

    bool ReadU16(uint16_t* value)
    {
        if (remaining_ < 2) return false;
        *value = static_cast<uint16_t>((static_cast<uint16_t>(cursor_[0]) << 8) |
            static_cast<uint16_t>(cursor_[1]));
        cursor_ += 2;
        remaining_ -= 2;
        return true;
    }

    bool ReadU32(uint32_t* value)
    {
        if (remaining_ < 4) return false;
        *value = (static_cast<uint32_t>(cursor_[0]) << 24) |
            (static_cast<uint32_t>(cursor_[1]) << 16) |
            (static_cast<uint32_t>(cursor_[2]) << 8) |
            static_cast<uint32_t>(cursor_[3]);
        cursor_ += 4;
        remaining_ -= 4;
        return true;
    }

    bool ReadBlob(const uint8_t** data, size_t* size)
    {
        uint32_t length = 0;
        if (!ReadU32(&length) || length == 0 || length > kMaxCertificateBytes ||
            length > remaining_) {
            return false;
        }
        *data = cursor_;
        *size = length;
        cursor_ += length;
        remaining_ -= length;
        return true;
    }

    size_t Remaining() const { return remaining_; }

private:
    const uint8_t* cursor_;
    size_t remaining_;
};

void SetError(std::string* error, const char* value)
{
    if (error != nullptr) *error = value;
}

Sha256Digest DigestCertificate(const uint8_t* data, size_t size)
{
    Sha256Digest result{};
    SHA256(data, size, result.data());
    return result;
}

bool ContainsDuplicate(const std::vector<Sha256Digest>& digests)
{
    return std::set<Sha256Digest>(digests.begin(), digests.end()).size() != digests.size();
}

bool SameSignerSet(const std::vector<Sha256Digest>& left,
                   const std::vector<Sha256Digest>& right)
{
    if (left.size() != right.size()) return false;
    std::vector<Sha256Digest> sortedLeft = left;
    std::vector<Sha256Digest> sortedRight = right;
    std::sort(sortedLeft.begin(), sortedLeft.end());
    std::sort(sortedRight.begin(), sortedRight.end());
    return sortedLeft == sortedRight;
}

bool HasLineageCapability(const ApkVerifiedIdentity& identity,
                          const Sha256Digest& signer, uint32_t capability)
{
    if (identity.currentSignerSha256.size() != 1) return false;
    if (identity.currentSignerSha256[0] == signer) return true;
    for (const auto& entry : identity.lineage) {
        if (entry.sha256 == signer && (entry.capabilities & capability) == capability) {
            return true;
        }
    }
    return false;
}

}  // namespace

bool ParseApkVerifyResult(const uint8_t* data, size_t size,
                          ApkVerifiedIdentity* out, std::string* error)
{
    if (data == nullptr || out == nullptr) {
        SetError(error, "null parser input");
        return false;
    }

    Reader reader(data, size);
    uint32_t magic = 0;
    uint16_t version = 0;
    uint16_t scheme = 0;
    uint32_t blockId = 0;
    if (!reader.ReadU32(&magic) || !reader.ReadU16(&version) ||
        !reader.ReadU16(&scheme) || !reader.ReadU32(&blockId)) {
        SetError(error, "truncated ASV1 header");
        return false;
    }
    if (magic != kResultMagic || version != kResultVersion) {
        SetError(error, "unsupported ASV1 header");
        return false;
    }
    if (scheme != kSchemeV2 && scheme != kSchemeV3) {
        SetError(error, "unsupported APK signature scheme");
        return false;
    }
    if ((scheme == kSchemeV2 && blockId != 0) ||
        (scheme == kSchemeV3 && blockId != kV3BlockId && blockId != kV31BlockId)) {
        SetError(error, "signature block ID does not match scheme");
        return false;
    }

    const uint8_t* apkDigest = nullptr;
    size_t apkDigestSize = 0;
    if (!reader.ReadBlob(&apkDigest, &apkDigestSize) || apkDigestSize != kApkSha256Bytes) {
        SetError(error, "invalid whole-APK SHA-256 field");
        return false;
    }

    uint32_t signerCount = 0;
    if (!reader.ReadU32(&signerCount) || signerCount == 0 ||
        signerCount > kMaxApkSignerCertificates ||
        (scheme == kSchemeV3 && signerCount != 1)) {
        SetError(error, "invalid current signer count");
        return false;
    }

    ApkVerifiedIdentity parsed;
    parsed.schemeVersion = scheme;
    parsed.v3BlockId = blockId;
    std::copy(apkDigest, apkDigest + apkDigestSize, parsed.apkSha256.begin());

    size_t totalCertificates = 0;
    for (uint32_t signerIndex = 0; signerIndex < signerCount; ++signerIndex) {
        uint32_t chainCount = 0;
        if (!reader.ReadU32(&chainCount) || chainCount == 0 ||
            chainCount > kMaxApkSignerCertificates ||
            totalCertificates + chainCount > kMaxApkSignerCertificates) {
            SetError(error, "invalid signer certificate chain count");
            return false;
        }
        for (uint32_t chainIndex = 0; chainIndex < chainCount; ++chainIndex) {
            const uint8_t* certificate = nullptr;
            size_t certificateSize = 0;
            if (!reader.ReadBlob(&certificate, &certificateSize)) {
                SetError(error, "invalid signer certificate blob");
                return false;
            }
            if (chainIndex == 0) {
                parsed.currentSignerSha256.push_back(
                    DigestCertificate(certificate, certificateSize));
                parsed.currentSignerCertificateDer.emplace_back(
                    certificate, certificate + certificateSize);
            }
        }
        totalCertificates += chainCount;
    }
    if (parsed.currentSignerCertificateDer.size() !=
            parsed.currentSignerSha256.size() ||
        ContainsDuplicate(parsed.currentSignerSha256)) {
        SetError(error, "duplicate current signer certificate");
        return false;
    }

    uint32_t lineageCount = 0;
    if (!reader.ReadU32(&lineageCount) || lineageCount > kMaxApkSignerCertificates ||
        totalCertificates + lineageCount > kMaxApkSignerCertificates ||
        (scheme == kSchemeV2 && lineageCount != 0)) {
        SetError(error, "invalid proof-of-rotation count");
        return false;
    }

    std::set<Sha256Digest> lineageDigests;
    for (uint32_t i = 0; i < lineageCount; ++i) {
        const uint8_t* certificate = nullptr;
        size_t certificateSize = 0;
        uint32_t capabilities = 0;
        if (!reader.ReadBlob(&certificate, &certificateSize) ||
            !reader.ReadU32(&capabilities) || (capabilities & ~kKnownCapabilityMask) != 0) {
            SetError(error, "invalid proof-of-rotation entry");
            return false;
        }
        ApkLineageCertificate entry;
        entry.sha256 = DigestCertificate(certificate, certificateSize);
        entry.capabilities = capabilities;
        if (!lineageDigests.insert(entry.sha256).second) {
            SetError(error, "duplicate proof-of-rotation certificate");
            return false;
        }
        parsed.lineage.push_back(entry);
    }
    if (!parsed.lineage.empty() &&
        parsed.lineage.back().sha256 != parsed.currentSignerSha256.front()) {
        SetError(error, "proof-of-rotation terminal signer mismatch");
        return false;
    }
    if (reader.Remaining() != 0) {
        SetError(error, "trailing bytes in ASV1 result");
        return false;
    }

    *out = std::move(parsed);
    if (error != nullptr) error->clear();
    return true;
}

bool IsApkUpdateAllowed(const ApkVerifiedIdentity& oldIdentity,
                        const ApkVerifiedIdentity& newIdentity)
{
    if (oldIdentity.currentSignerSha256.empty() || newIdentity.currentSignerSha256.empty()) {
        return false;
    }
    if (oldIdentity.currentSignerSha256.size() > 1 ||
        newIdentity.currentSignerSha256.size() > 1) {
        return SameSignerSet(oldIdentity.currentSignerSha256,
                             newIdentity.currentSignerSha256);
    }
    return HasLineageCapability(newIdentity, oldIdentity.currentSignerSha256[0],
                                kApkSignerCapabilityInstalledData) ||
        HasLineageCapability(oldIdentity, newIdentity.currentSignerSha256[0],
                             kApkSignerCapabilityRollback);
}

std::string Sha256ToLowerHex(const Sha256Digest& digest)
{
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(digest.size() * 2, '0');
    for (size_t i = 0; i < digest.size(); ++i) {
        result[i * 2] = kHex[digest[i] >> 4];
        result[i * 2 + 1] = kHex[digest[i] & 0x0f];
    }
    return result;
}

}  // namespace oh_adapter
