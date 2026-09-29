#ifndef INSTALL_PACKET_FIXTURE_H
#define INSTALL_PACKET_FIXTURE_H
#include "apk_install_plan_v2.h"
#include "manifest_facts_v1.h"
#include "prepass_bundle.h"
#include "manifest_fixture.h"
#include <nlohmann/json.hpp>
#include <cstring>
#include <dirent.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
namespace install_packet_fixture {
using namespace oh_adapter::package_transaction;
using namespace oh_adapter::manifest_facts;
using namespace manifest_fixture;
using Json = nlohmann::json;
inline std::string Hash(const std::string& bytes) { return Sha(std::vector<uint8_t>(bytes.begin(), bytes.end())); }
inline size_t FdCount()
{
    DIR* d = opendir("/proc/self/fd"); Require(d != nullptr, "FD count fixture"); size_t count = 0;
    while (auto* e = readdir(d)) if (e->d_name[0] != '.') ++count;
    closedir(d); return count;
}
inline ApkInstallFdV2 Seal(const std::string& bytes, int seals = F_SEAL_WRITE | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL)
{
    ApkInstallFdV2 span{}; span.fd = memfd_create("spc50-input", MFD_CLOEXEC | MFD_ALLOW_SEALING);
    Require(span.fd >= 0, "real fixture memfd");
    size_t at = 0;
    while (at < bytes.size()) { const auto n = write(span.fd, bytes.data()+at, bytes.size()-at); if (n <= 0) { close(span.fd); throw std::runtime_error("fixture write"); } at += n; }
    if (fcntl(span.fd, F_ADD_SEALS, seals) != 0) { close(span.fd); throw std::runtime_error("fixture seal"); }
    span.byteLength = bytes.size(); std::strcpy(span.sha256Hex, Hash(bytes).c_str()); return span;
}
struct TemporaryFd { ApkInstallFdV2 span; ~TemporaryFd() { close(span.fd); } };
struct Packet {
    ApkInstallPlanV2 plan; Json metadata; ManifestParseReceiptV1 receipt;
    Packet(uint32_t major = 3, uint32_t minor = 17)
    {
        ApkInstallPlanV2_Init(&plan);
        auto& context = plan.context; context.abiVersion = PREPASS_CONTEXT_WIRE_ABI; context.structSize = sizeof(context); context.userId = 27;
        std::strcpy(context.requestId, "wire-request"); std::strcpy(context.packageName, "org.example.version"); std::strcpy(context.candidateGeneration, "generation-8");
        for (auto* d : {context.contractSha256Hex,context.policySha256Hex,context.toolSha256Hex,context.topologySha256Hex,context.runtimeGenerationSealSha256Hex}) { std::memset(d,'a',64); d[64]=0; }
        const auto apkBytes = MakeZip({{"AndroidManifest.xml", MakeAxml({{"versionCodeMajor",0x10,major,{}},{"versionCode",0x10,minor,{}}})}});
        plan.artifactCount=1; auto& artifact = plan.artifacts[0]; artifact.role = APK_INSTALL_ARTIFACT_BASE; std::strcpy(artifact.artifactId,"base");
        artifact.apk = Seal(std::string(apkBytes.begin(),apkBytes.end()));
        ManifestParseRequestV1 request; request.requestId = context.requestId; request.userId = 0; // Existing V1 parser fixture profile; manifest bytes are user-independent.
        request.artifactFd = artifact.apk.fd; request.byteLength = artifact.apk.byteLength; request.artifactSha256 = artifact.apk.sha256Hex;
        ArtifactDescriptorV1 descriptor; descriptor.artifactId="base"; descriptor.role=ArtifactRole::BASE; descriptor.byteLength=request.byteLength; descriptor.sha256=request.artifactSha256;
        request.artifactSet.artifacts.push_back(descriptor); request.artifactSet.artifactSetDigest=ComputeArtifactSetDigest(request.artifactSet);
        receipt = ManifestFactsParserV1().Parse(request); Require(receipt.verdict == ManifestParseVerdict::PARSED, receipt.reason);
        plan.versionMajorBits=receipt.versionV2.major.bits; plan.versionMinorBits=receipt.versionV2.minor.bits;
        plan.versionPresenceBits=APK_INSTALL_VERSION_MAJOR_PRESENT|APK_INSTALL_VERSION_MINOR_PRESENT;
        plan.majorSource=APK_INSTALL_VERSION_SOURCE_EXPLICIT; plan.minorSource=APK_INSTALL_VERSION_SOURCE_EXPLICIT;
        std::strcpy(plan.artifactSetSha256Hex,request.artifactSet.artifactSetDigest.c_str());
        PrepassBundle bundle; bundle.requestId=context.requestId; bundle.packageName=context.packageName; bundle.userId=context.userId;
        bundle.packageGeneration=context.candidateGeneration; bundle.apkDigest=request.artifactSha256;
        bundle.contractDigest=context.contractSha256Hex; bundle.policyDigest=context.policySha256Hex; bundle.toolDigest=context.toolSha256Hex;
        bundle.topologyDigest=context.topologySha256Hex; bundle.runtimeGenerationSealDigest=context.runtimeGenerationSealSha256Hex;
        wire::PrepassBundleRecord record; std::string error; Require(PrepassBundleCodec::Encode(bundle,&record,&error), error);
        artifact.prepass = Seal(record.canonicalPayload);
        // Signing is an external verified-owner fixture at this wire boundary;
        // no test claims a cryptographic verification or an install result.
        metadata = {{"schemaVersion", 2}, {"kind", "apk-install-metadata"},
            {"artifactSetDigest", request.artifactSet.artifactSetDigest},
            {"manifest", Json::parse(ManifestParseReceiptJson(receipt))}};
        metadata["signing"] = {{"verified", true}, {"artifactSetDigest", request.artifactSet.artifactSetDigest},
            {"verifierVersion", "fixture-verified-owner"}, {"schemeVersions", {2}},
            {"signerCertificateDigests", {std::string(64, 'b')}}};
        plan.manifestSigning = Seal(metadata.dump());
    }
    ~Packet() { ApkInstallPlanV2_Release(&plan); }
    Packet(const Packet&) = delete;
};
}
#endif
