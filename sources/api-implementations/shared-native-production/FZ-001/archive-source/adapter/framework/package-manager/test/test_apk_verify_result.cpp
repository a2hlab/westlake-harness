#include "apk_verify_result.h"

#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {

using oh_adapter::ApkVerifiedIdentity;

void PutU16(std::vector<uint8_t>& output, uint16_t value)
{
    output.push_back(static_cast<uint8_t>(value >> 8));
    output.push_back(static_cast<uint8_t>(value));
}

void PutU32(std::vector<uint8_t>& output, uint32_t value)
{
    output.push_back(static_cast<uint8_t>(value >> 24));
    output.push_back(static_cast<uint8_t>(value >> 16));
    output.push_back(static_cast<uint8_t>(value >> 8));
    output.push_back(static_cast<uint8_t>(value));
}

void PutBlob(std::vector<uint8_t>& output, const std::vector<uint8_t>& value)
{
    PutU32(output, static_cast<uint32_t>(value.size()));
    output.insert(output.end(), value.begin(), value.end());
}

struct LineageInput {
    std::vector<uint8_t> certificate;
    uint32_t capabilities;
};

std::vector<uint8_t> MakeResult(uint16_t scheme, uint32_t blockId,
    const std::vector<std::vector<std::vector<uint8_t>>>& signerChains,
    const std::vector<LineageInput>& lineage)
{
    std::vector<uint8_t> output;
    PutU32(output, 0x41535631u);
    PutU16(output, 1);
    PutU16(output, scheme);
    PutU32(output, blockId);
    PutBlob(output, std::vector<uint8_t>(32, 0x5a));
    PutU32(output, static_cast<uint32_t>(signerChains.size()));
    for (const auto& chain : signerChains) {
        PutU32(output, static_cast<uint32_t>(chain.size()));
        for (const auto& certificate : chain) PutBlob(output, certificate);
    }
    PutU32(output, static_cast<uint32_t>(lineage.size()));
    for (const auto& entry : lineage) {
        PutBlob(output, entry.certificate);
        PutU32(output, entry.capabilities);
    }
    return output;
}

ApkVerifiedIdentity ParseOrDie(const std::vector<uint8_t>& payload)
{
    ApkVerifiedIdentity identity;
    std::string error;
    if (!oh_adapter::ParseApkVerifyResult(payload.data(), payload.size(), &identity, &error)) {
        std::cerr << "unexpected parse failure: " << error << std::endl;
        std::exit(1);
    }
    return identity;
}

void ExpectRejected(const std::vector<uint8_t>& payload, const char* name)
{
    ApkVerifiedIdentity identity;
    std::string error;
    if (oh_adapter::ParseApkVerifyResult(payload.data(), payload.size(), &identity, &error)) {
        std::cerr << "expected rejection: " << name << std::endl;
        std::exit(1);
    }
}

}  // namespace

int main()
{
    const std::vector<uint8_t> oldCertificate{0x30, 0x03, 0x01, 0x02, 0x03};
    const std::vector<uint8_t> newCertificate{0x30, 0x03, 0x04, 0x05, 0x06};
    const std::vector<uint8_t> otherCertificate{0x30, 0x03, 0x07, 0x08, 0x09};

    const auto validV2 = MakeResult(2, 0, {{{oldCertificate}}}, {});
    const ApkVerifiedIdentity oldIdentity = ParseOrDie(validV2);
    if (oldIdentity.schemeVersion != 2 || oldIdentity.currentSignerSha256.size() != 1 ||
        oldIdentity.currentSignerCertificateDer !=
            std::vector<std::vector<uint8_t>>{oldCertificate} ||
        !oldIdentity.lineage.empty()) {
        std::cerr << "valid V2 shape mismatch" << std::endl;
        return 1;
    }

    const auto validV3 = MakeResult(3, 0xf05368c0u, {{{newCertificate}}}, {
        {oldCertificate, oh_adapter::kApkSignerCapabilityInstalledData},
        {newCertificate, 0},
    });
    const ApkVerifiedIdentity newIdentity = ParseOrDie(validV3);
    if (newIdentity.currentSignerCertificateDer !=
            std::vector<std::vector<uint8_t>>{newCertificate} ||
        !oh_adapter::IsApkUpdateAllowed(oldIdentity, newIdentity) ||
        oh_adapter::IsApkUpdateAllowed(newIdentity, oldIdentity)) {
        std::cerr << "proof-of-rotation update policy mismatch" << std::endl;
        return 1;
    }

    const auto validV2MultiA = MakeResult(2, 0, {{{oldCertificate}}, {{newCertificate}}}, {});
    const auto validV2MultiB = MakeResult(2, 0, {{{newCertificate}}, {{oldCertificate}}}, {});
    const auto validV2MultiC = MakeResult(2, 0, {{{newCertificate}}, {{otherCertificate}}}, {});
    if (!oh_adapter::IsApkUpdateAllowed(ParseOrDie(validV2MultiA), ParseOrDie(validV2MultiB)) ||
        oh_adapter::IsApkUpdateAllowed(ParseOrDie(validV2MultiA), ParseOrDie(validV2MultiC))) {
        std::cerr << "multi-signer exact-set policy mismatch" << std::endl;
        return 1;
    }

    auto malformed = validV2;
    malformed[0] = 0;
    ExpectRejected(malformed, "bad magic");
    malformed = validV2;
    malformed.pop_back();
    ExpectRejected(malformed, "truncated");
    malformed = validV2;
    malformed.push_back(0);
    ExpectRejected(malformed, "trailing byte");
    ExpectRejected(MakeResult(2, 0xf05368c0u, {{{oldCertificate}}}, {}), "V2 block ID");
    ExpectRejected(MakeResult(3, 0, {{{oldCertificate}}}, {}), "V3 block ID");
    ExpectRejected(MakeResult(3, 0xf05368c0u,
        {{{oldCertificate}}, {{newCertificate}}}, {}), "V3 multiple signer");
    ExpectRejected(MakeResult(2, 0, {{{oldCertificate}}},
        {{oldCertificate, 0}}), "V2 lineage");
    ExpectRejected(MakeResult(3, 0xf05368c0u, {{{newCertificate}}},
        {{oldCertificate, 0x20}, {newCertificate, 0}}), "unknown capability");
    ExpectRejected(MakeResult(3, 0xf05368c0u, {{{newCertificate}}},
        {{oldCertificate, 1}, {oldCertificate, 0}}), "duplicate lineage");
    ExpectRejected(MakeResult(3, 0xf05368c0u, {{{newCertificate}}},
        {{oldCertificate, 1}}), "terminal signer mismatch");
    ExpectRejected(MakeResult(2, 0, {{{oldCertificate}}, {{oldCertificate}}}, {}),
        "duplicate current signer");

    std::cout << "PASS apk_verify_result" << std::endl;
    return 0;
}
