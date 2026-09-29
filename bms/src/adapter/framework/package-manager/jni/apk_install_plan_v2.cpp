#include "apk_install_plan_v2.h"
#include "prepass_bundle.h"
#include "package_transaction_v1.h"
#include "sha256.h"
#include <nlohmann/json.hpp>
#include <array>
#include <charconv>
#include <cstring>
#include <limits>
#include <new>
#include <set>
#include <string>
#if defined(__linux__) || defined(__OHOS__)
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

namespace {
using namespace oh_adapter::package_transaction;
using Json = nlohmann::json;
constexpr uint64_t MAX_APK_BYTES = 2ULL * 1024 * 1024 * 1024;
constexpr uint64_t MAX_PAYLOAD_BYTES = PrepassBundleCodec::MAX_PAYLOAD_BYTES;
static_assert(sizeof(ApkInstallPlanV2) == 21032 && alignof(ApkInstallPlanV2) == 8);
void Require(bool pass, ApkInstallPlanStatusV2 status) { if (!pass) throw status; }
bool Zero(const void* data, size_t length)
{
    const auto* bytes = static_cast<const unsigned char*>(data);
    for (size_t i = 0; i < length; ++i) if (bytes[i] != 0) return false;
    return true;
}
bool Digest(const std::string& value)
{
    if (value.size() != 64) return false;
    for (char c : value) if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
    return true;
}
std::string Text(const char* value, size_t capacity, ApkInstallPlanStatusV2 error)
{
    size_t length = 0; while (length < capacity && value[length] != 0) ++length;
    Require(length > 0 && length < capacity && Zero(value + length, capacity - length), error);
    return std::string(value, length);
}
std::string Hash(const char* data, size_t length)
{
    unsigned char digest[32]; sha256(reinterpret_cast<const unsigned char*>(data), length, digest);
    constexpr char hex[] = "0123456789abcdef"; std::string result; result.reserve(64);
    for (auto byte : digest) { result += hex[byte >> 4]; result += hex[byte & 15]; } return result;
}
void SpanShape(const ApkInstallFdV2& span, uint64_t limit, std::set<int>& descriptors)
{
    Require(span.reservedZero == 0 && Zero(span.reservedTail, sizeof(span.reservedTail)), APK_INSTALL_PLAN_V2_BAD_RESERVED);
    Require(span.fd >= 0, APK_INSTALL_PLAN_V2_BAD_FD);
    Require(descriptors.insert(span.fd).second, APK_INSTALL_PLAN_V2_BAD_ARTIFACT_SET);
    Require(span.byteLength > 0 && span.byteLength <= limit, APK_INSTALL_PLAN_V2_BAD_LENGTH);
    Require(Digest(Text(span.sha256Hex, sizeof(span.sha256Hex), APK_INSTALL_PLAN_V2_BAD_DIGEST)), APK_INSTALL_PLAN_V2_BAD_DIGEST);
}
std::string ReadSealed(const ApkInstallFdV2& span, bool retainBytes)
{
#if defined(__linux__) || defined(__OHOS__)
    const int fd = fcntl(span.fd, F_DUPFD_CLOEXEC, 0);
    Require(fd >= 0, APK_INSTALL_PLAN_V2_BAD_FD);
    struct Close { int fd; ~Close() { close(fd); } } owned{fd};
    struct stat st{}; Require(fstat(fd, &st) == 0 && S_ISREG(st.st_mode), APK_INSTALL_PLAN_V2_BAD_FD);
    Require(st.st_size >= 0 && static_cast<uint64_t>(st.st_size) == span.byteLength, APK_INSTALL_PLAN_V2_BAD_LENGTH);
    constexpr int seals = F_SEAL_WRITE | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL;
    const int actual = fcntl(fd, F_GET_SEALS);
    Require(actual >= 0 && (actual & seals) == seals, APK_INSTALL_PLAN_V2_UNSEALED_FD);
    void* data = mmap(nullptr, static_cast<size_t>(span.byteLength), PROT_READ, MAP_PRIVATE, fd, 0);
    Require(data != MAP_FAILED, APK_INSTALL_PLAN_V2_RESOURCE_ERROR);
    struct Unmap { void* data; size_t length; ~Unmap() { munmap(data, length); } } view{data, static_cast<size_t>(span.byteLength)};
    const auto* bytes = static_cast<const char*>(data);
    Require(Hash(bytes, view.length) == span.sha256Hex, APK_INSTALL_PLAN_V2_BAD_DIGEST);
    return retainBytes ? std::string(bytes, view.length) : std::string{};
#else
    (void)span; (void)retainBytes; throw APK_INSTALL_PLAN_V2_UNSUPPORTED_PLATFORM;
#endif
}
PrepassBinding Binding(const PrepassContextWire& context, const char* apkDigest)
{
    PrepassBinding binding; binding.requestId = context.requestId; binding.packageName = context.packageName;
    binding.userId = context.userId; binding.packageGeneration = context.candidateGeneration; binding.apkDigest = apkDigest;
    binding.contractDigest = context.contractSha256Hex; binding.policyDigest = context.policySha256Hex;
    binding.toolDigest = context.toolSha256Hex; binding.topologyDigest = context.topologySha256Hex;
    binding.runtimeGenerationSealDigest = context.runtimeGenerationSealSha256Hex; return binding;
}
uint32_t Decimal(const Json& value)
{
    Require(value.is_string(), APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    const auto& text = value.get_ref<const std::string&>(); uint32_t number = 0;
    const auto result = std::from_chars(text.data(), text.data() + text.size(), number);
    Require(result.ec == std::errc{} && result.ptr == text.data() + text.size() && std::to_string(number) == text, APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    return number;
}
bool TextEqual(const Json& value, const char* expected)
{
    return value.is_string() && value.get_ref<const std::string&>() == expected;
}
void Metadata(const std::string& bytes, const ApkInstallPlanV2& plan, const ApkInstallArtifactV2& base)
{
    Json json;
    // nlohmann's ordinary structured destructor allocates a flattening stack.
    // Empty children first, using the already bounded depth, so OOM cleanup
    // never needs that allocation. SAX builds directly into this guarded root.
    struct Clear {
        Json& value;
        static void Children(Json& node) noexcept
        {
            if (node.is_structured()) for (auto& child : node) Children(child);
            node.clear();
        }
        ~Clear() { Children(value); }
    } clear{json};
    constexpr int MAX_CONTAINER_DEPTH = 64;
    std::array<std::string, MAX_CONTAINER_DEPTH> lastKey;
    std::array<bool, MAX_CONTAINER_DEPTH> hasKey{};
    Json::parser_callback_t callback = [&](int depth, Json::parse_event_t event, Json& value) {
        if (event == Json::parse_event_t::object_start || event == Json::parse_event_t::array_start) {
            Require(depth < MAX_CONTAINER_DEPTH, APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
            hasKey[depth] = false;
        } else if (event == Json::parse_event_t::key) {
            const auto& key = value.get_ref<const std::string&>();
            // Canonical sorted keys also prevent replacement of an existing
            // nested value, whose library destructor could allocate on OOM.
            Require(!hasKey[depth - 1] || lastKey[depth - 1] < key, APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
            lastKey[depth - 1] = key; hasKey[depth - 1] = true;
        }
        return true;
    };
    nlohmann::detail::json_sax_dom_callback_parser<Json> sax(json, callback, true);
    Require(Json::sax_parse(bytes, &sax), APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    // Canonical serialization also rejects whitespace, duplicate object keys,
    // alternate number spellings and unknown non-finite JSON representations.
    Require(json.is_object() && json.dump() == bytes, APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    Require(json.at("schemaVersion").is_number_unsigned() && json.at("schemaVersion") == 2 &&
        TextEqual(json.at("kind"), "apk-install-metadata") && TextEqual(json.at("artifactSetDigest"), plan.artifactSetSha256Hex), APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    const auto& manifest = json.at("manifest");
    Require(TextEqual(manifest.at("verdict"), "PARSED") && TextEqual(manifest.at("requestId"), plan.context.requestId) &&
        TextEqual(manifest.at("artifactSha256"), base.apk.sha256Hex) && TextEqual(manifest.at("artifactSetDigest"), plan.artifactSetSha256Hex) &&
        TextEqual(manifest.at("facts").at("artifactSetDigest"), plan.artifactSetSha256Hex) &&
        TextEqual(manifest.at("facts").at("packageName"), plan.context.packageName), APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    const auto& version = manifest.at("versionV2");
    Require(version.at("schemaVersion").is_number_unsigned() && version.at("schemaVersion") == 2 &&
        Decimal(version.at("major")) == plan.versionMajorBits && Decimal(version.at("minor")) == plan.versionMinorBits,
        APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    Require(version.at("majorPresent").is_boolean() && version.at("minorPresent").is_boolean() &&
        version.at("majorPresent") == ((plan.versionPresenceBits & APK_INSTALL_VERSION_MAJOR_PRESENT) != 0) &&
        version.at("minorPresent") == ((plan.versionPresenceBits & APK_INSTALL_VERSION_MINOR_PRESENT) != 0) &&
        TextEqual(version.at("majorSource"), plan.majorSource == APK_INSTALL_VERSION_SOURCE_EXPLICIT ? "explicit" : "default") &&
        TextEqual(version.at("minorSource"), plan.minorSource == APK_INSTALL_VERSION_SOURCE_EXPLICIT ? "explicit" : "default"), APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    const auto& signing = json.at("signing");
    Require(signing.at("verified").is_boolean() && signing.at("verified") == true &&
        TextEqual(signing.at("artifactSetDigest"), plan.artifactSetSha256Hex), APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    const auto& verifier = signing.at("verifierVersion").get_ref<const std::string&>();
    Require(!verifier.empty() && verifier.size() <= 4096 && verifier.find('\0') == std::string::npos, APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    const auto& schemes = signing.at("schemeVersions");
    Require(schemes.is_array() && !schemes.empty() && schemes.size() <= APK_INSTALL_PLAN_V2_MAX_ARTIFACTS, APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    for (const auto& scheme : schemes) Require(scheme.is_number_unsigned() && (scheme == 2 || scheme == 3), APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    const auto& signers = signing.at("signerCertificateDigests");
    Require(signers.is_array() && !signers.empty() && signers.size() <= 64, APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    std::set<std::string> unique;
    for (const auto& signer : signers) {
        const auto& digest = signer.get_ref<const std::string&>();
        Require(Digest(digest) && unique.insert(digest).second, APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    }
}
bool KnownVersion(uint32_t bits, uint32_t source, bool present)
{
    return (source == APK_INSTALL_VERSION_SOURCE_DEFAULT && bits == 0) ||
        (source == APK_INSTALL_VERSION_SOURCE_EXPLICIT && present);
}
int Validate(const ApkInstallPlanV2& plan)
{
    Require(plan.capabilities == APK_INSTALL_PLAN_V2_CAPABILITIES, APK_INSTALL_PLAN_V2_BAD_CAPABILITIES);
    Require(plan.reservedZero == 0 && Zero(plan.reservedTail, sizeof(plan.reservedTail)), APK_INSTALL_PLAN_V2_BAD_RESERVED);
    Require(plan.payloadSchemaVersion == APK_INSTALL_PAYLOAD_SCHEMA_V2, APK_INSTALL_PLAN_V2_BAD_PAYLOAD);
    Require(PrepassContextWire_Validate(&plan.context) == PREPASS_CONTEXT_WIRE_OK, APK_INSTALL_PLAN_V2_BAD_CONTEXT);
    Require((plan.versionPresenceBits & ~3u) == 0 &&
        KnownVersion(plan.versionMajorBits, plan.majorSource, (plan.versionPresenceBits & APK_INSTALL_VERSION_MAJOR_PRESENT) != 0) &&
        KnownVersion(plan.versionMinorBits, plan.minorSource, (plan.versionPresenceBits & APK_INSTALL_VERSION_MINOR_PRESENT) != 0), APK_INSTALL_PLAN_V2_BAD_VERSION);
    Require(plan.artifactCount > 0 && plan.artifactCount <= APK_INSTALL_PLAN_V2_MAX_ARTIFACTS, APK_INSTALL_PLAN_V2_BAD_ARTIFACT_SET);
    Require(Digest(Text(plan.artifactSetSha256Hex, sizeof(plan.artifactSetSha256Hex), APK_INSTALL_PLAN_V2_BAD_DIGEST)), APK_INSTALL_PLAN_V2_BAD_DIGEST);
    std::set<int> descriptors; SpanShape(plan.manifestSigning, MAX_PAYLOAD_BYTES, descriptors);
    std::set<std::string> identities; uint64_t total = 0; const ApkInstallArtifactV2* base = nullptr;
    PackageArtifactSetV1 set;
    for (uint32_t i = 0; i < plan.artifactCount; ++i) {
        const auto& artifact = plan.artifacts[i];
        Require(artifact.reservedZero == 0, APK_INSTALL_PLAN_V2_BAD_RESERVED);
        Require(artifact.role <= APK_INSTALL_ARTIFACT_SPLIT_FEATURE, APK_INSTALL_PLAN_V2_BAD_ARTIFACT_SET);
        const auto id = Text(artifact.artifactId, sizeof(artifact.artifactId), APK_INSTALL_PLAN_V2_BAD_ARTIFACT_SET);
        Require(identities.insert(id).second, APK_INSTALL_PLAN_V2_BAD_ARTIFACT_SET);
        if (artifact.role == APK_INSTALL_ARTIFACT_BASE) { Require(!base, APK_INSTALL_PLAN_V2_BAD_ARTIFACT_SET); base = &artifact; }
        SpanShape(artifact.apk, MAX_APK_BYTES, descriptors); SpanShape(artifact.prepass, MAX_PAYLOAD_BYTES, descriptors);
        Require(artifact.apk.byteLength <= MAX_APK_BYTES - total, APK_INSTALL_PLAN_V2_BAD_LENGTH); total += artifact.apk.byteLength;
        ArtifactDescriptorV1 item; item.artifactId = id; item.role = static_cast<ArtifactRole>(artifact.role);
        item.byteLength = artifact.apk.byteLength; item.sha256 = artifact.apk.sha256Hex; set.artifacts.push_back(std::move(item));
    }
    Require(base != nullptr && ComputeArtifactSetDigest(set) == plan.artifactSetSha256Hex, APK_INSTALL_PLAN_V2_BAD_ARTIFACT_SET);
    ApkInstallArtifactV2 unused{}; unused.apk.fd = -1; unused.prepass.fd = -1;
    for (uint32_t i = plan.artifactCount; i < APK_INSTALL_PLAN_V2_MAX_ARTIFACTS; ++i)
        Require(std::memcmp(&plan.artifacts[i], &unused, sizeof(unused)) == 0, APK_INSTALL_PLAN_V2_BAD_RESERVED);
    for (uint32_t i = 0; i < plan.artifactCount; ++i) {
        const auto& artifact = plan.artifacts[i]; ReadSealed(artifact.apk, false);
        const auto bytes = ReadSealed(artifact.prepass, true); PrepassBundle decoded; std::string error;
        Require(PrepassBundleCodec::DecodePayload(bytes, artifact.prepass.sha256Hex, Binding(plan.context, artifact.apk.sha256Hex), &decoded, &error), APK_INSTALL_PLAN_V2_BAD_PREPASS);
    }
    Metadata(ReadSealed(plan.manifestSigning, true), plan, *base);
    return APK_INSTALL_PLAN_V2_OK;
}
}

extern "C" uint64_t oh_adapter_apk_install_plan_abi_v2()
{ return (static_cast<uint64_t>(APK_INSTALL_PLAN_ABI_V2) << 32) | sizeof(ApkInstallPlanV2); }
extern "C" void ApkInstallPlanV2_Init(ApkInstallPlanV2* plan)
{
    if (!plan) return;
    std::memset(plan, 0, sizeof(*plan)); plan->abiVersion = APK_INSTALL_PLAN_ABI_V2; plan->structSize = sizeof(*plan);
    plan->capabilities = APK_INSTALL_PLAN_V2_CAPABILITIES; plan->payloadSchemaVersion = APK_INSTALL_PAYLOAD_SCHEMA_V2;
    plan->context.userId = -1; plan->manifestSigning.fd = -1;
    for (auto& artifact : plan->artifacts) { artifact.apk.fd = -1; artifact.prepass.fd = -1; }
}
extern "C" int ApkInstallPlanV2_Validate(const ApkInstallPlanV2* plan)
{
    if (!plan) return APK_INSTALL_PLAN_V2_BAD_ARGUMENT;
    uint32_t header[2]; std::memcpy(header, plan, sizeof(header));
    if (header[0] != APK_INSTALL_PLAN_ABI_V2) return APK_INSTALL_PLAN_V2_BAD_ABI;
    if (header[1] != sizeof(*plan)) return APK_INSTALL_PLAN_V2_BAD_SIZE;
    try { return Validate(*plan); }
    catch (ApkInstallPlanStatusV2 status) { return status; }
    catch (const std::bad_alloc&) { return APK_INSTALL_PLAN_V2_RESOURCE_ERROR; }
    catch (const Json::exception&) { return APK_INSTALL_PLAN_V2_BAD_PAYLOAD; }
    catch (...) { return APK_INSTALL_PLAN_V2_RESOURCE_ERROR; }
}
extern "C" int ApkInstallPlanV2_ValidateBytes(const void* bytes, size_t byteLength)
{
    if (!bytes) return APK_INSTALL_PLAN_V2_BAD_ARGUMENT;
    if (byteLength != sizeof(ApkInstallPlanV2)) return APK_INSTALL_PLAN_V2_BAD_SIZE;
    ApkInstallPlanV2 copy; std::memcpy(&copy, bytes, sizeof(copy)); return ApkInstallPlanV2_Validate(&copy);
}
extern "C" void ApkInstallPlanV2_Release(ApkInstallPlanV2* plan)
{
    if (!plan) return;
    uint32_t header[2]; std::memcpy(header, plan, sizeof(header));
    if (header[0] != APK_INSTALL_PLAN_ABI_V2 || header[1] != sizeof(*plan)) return;
    // No allocation/exception during cleanup, including invalid artifactCount.
    std::array<int, APK_INSTALL_PLAN_V2_MAX_ARTIFACTS * 2 + 1> closed{}; size_t count = 0;
    const auto release = [&](int32_t& fd) {
        const int value = fd; fd = -1;
        if (value < 0) return;
        for (size_t i = 0; i < count; ++i) if (closed[i] == value) return;
        closed[count++] = value;
#if defined(__linux__) || defined(__OHOS__)
        close(value);
#endif
    };
    release(plan->manifestSigning.fd);
    for (auto& artifact : plan->artifacts) { release(artifact.apk.fd); release(artifact.prepass.fd); }
    ApkInstallPlanV2_Init(plan);
}
