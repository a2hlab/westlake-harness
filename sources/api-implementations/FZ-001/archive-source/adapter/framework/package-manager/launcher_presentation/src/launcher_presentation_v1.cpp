#include "launcher_presentation_v1.h"

#include "sha256.h"

#include <algorithm>
#include <cctype>
#include <cstddef>
#include <limits>
#include <sstream>
#include <string_view>
#include <utility>

namespace oh_adapter::launcher_presentation {
namespace {

std::string JsonEscape(std::string_view value)
{
    std::string result;
    result.reserve(value.size() + 8);
    for (const unsigned char character : value) {
        switch (character) {
            case '"': result += "\\\""; break;
            case '\\': result += "\\\\"; break;
            case '\b': result += "\\b"; break;
            case '\f': result += "\\f"; break;
            case '\n': result += "\\n"; break;
            case '\r': result += "\\r"; break;
            case '\t': result += "\\t"; break;
            default:
                if (character < 0x20) {
                    static constexpr char kHex[] = "0123456789abcdef";
                    result += "\\u00";
                    result.push_back(kHex[character >> 4]);
                    result.push_back(kHex[character & 0x0f]);
                } else {
                    result.push_back(static_cast<char>(character));
                }
        }
    }
    return result;
}

std::string Hex(const uint8_t* bytes, size_t length)
{
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(length * 2, '0');
    for (size_t index = 0; index < length; ++index) {
        result[index * 2] = kHex[bytes[index] >> 4];
        result[index * 2 + 1] = kHex[bytes[index] & 0x0f];
    }
    return result;
}

std::string Sha256Hex(const uint8_t* bytes, size_t length)
{
    unsigned char digest[32]{};
    sha256(bytes, length, digest);
    return Hex(digest, sizeof(digest));
}

bool IsLowerHexDigest(const std::string& value)
{
    if (value.size() != 64) return false;
    return std::all_of(value.begin(), value.end(), [](char character) {
        return (character >= '0' && character <= '9') ||
            (character >= 'a' && character <= 'f');
    });
}

bool IsSafeIdentifier(
    const std::string& value, bool allowDot, bool allowDollar)
{
    if (value.empty() || value.size() > 255 || value == "." ||
        value == "..") {
        return false;
    }
    for (const unsigned char character : value) {
        const bool accepted =
            (character >= 'a' && character <= 'z') ||
            (character >= 'A' && character <= 'Z') ||
            (character >= '0' && character <= '9') ||
            character == '_' || character == '-' ||
            (allowDot && character == '.') ||
            (allowDollar && character == '$');
        if (!accepted) return false;
    }
    return true;
}

bool IsLocaleTag(const std::string& value)
{
    if (value.empty() || value.size() > 64) return false;
    return std::all_of(value.begin(), value.end(), [](unsigned char ch) {
        return std::isalnum(ch) != 0 || ch == '-' || ch == '_';
    });
}

bool IsValidConfiguration(const ConfigurationSelectorV1& configuration)
{
    return configuration.schemaVersion == 1 &&
        IsLocaleTag(configuration.localeTag) &&
        configuration.densityDpi >= 72 &&
        configuration.densityDpi <= 1280 &&
        IsLowerHexDigest(configuration.configurationHash);
}

bool SameConfiguration(const ConfigurationSelectorV1& left,
    const ConfigurationSelectorV1& right)
{
    return left.schemaVersion == right.schemaVersion &&
        left.localeTag == right.localeTag &&
        left.densityDpi == right.densityDpi &&
        left.nightMode == right.nightMode &&
        left.configurationHash == right.configurationHash;
}

LauncherPresentationResponseV1 BaseResponse(
    const LauncherPresentationQueryV1& query)
{
    LauncherPresentationResponseV1 response;
    response.requestId = query.requestId;
    response.packageName = query.packageName;
    response.componentName = query.componentName;
    response.userId = query.userId;
    response.generation = query.expectedGeneration;
    response.canonicalDigest = query.expectedCanonicalDigest;
    response.configuration = query.configuration;
    return response;
}

LauncherPresentationResponseV1 Reject(
    const LauncherPresentationQueryV1& query,
    LauncherPresentationVerdict verdict, std::string reason)
{
    LauncherPresentationResponseV1 response = BaseResponse(query);
    response.verdict = verdict;
    response.reason = std::move(reason);
    return response;
}

bool Interrupted(LauncherPresentationFaultInjectorV1* faultInjector,
    QueryPhase phase)
{
    return faultInjector != nullptr && faultInjector->InterruptAt(phase);
}

std::string CacheKeyBytes(const CacheInvalidationRequestV1& request)
{
    std::ostringstream output;
    output << "LauncherPresentationCacheKeyV1\n"
           << "packageNameHex="
           << Hex(reinterpret_cast<const uint8_t*>(request.packageName.data()),
                  request.packageName.size())
           << "\nuserId=" << request.userId
           << "\ngeneration=" << request.generation
           << "\ncanonicalDigest=" << request.canonicalDigest
           << "\nprojectionDigest=" << request.projectionDigest
           << "\nresourcePayloadDigest=" << request.resourcePayloadDigest
           << "\n";
    return output.str();
}

}  // namespace

LauncherPresentationServiceV1::LauncherPresentationServiceV1(
    LauncherPresentationPolicyV1 policy,
    LauncherPresentationSnapshotProviderV1* provider)
    : policy_(std::move(policy)), provider_(provider)
{
}

std::string LauncherPresentationServiceV1::ComputeSha256(
    const std::string& bytes)
{
    return Sha256Hex(reinterpret_cast<const uint8_t*>(bytes.data()),
        bytes.size());
}

std::string LauncherPresentationServiceV1::ComputeRenderedAssetHash(
    const LauncherAssetV1& asset)
{
    std::ostringstream output;
    output << "LauncherRenderedAssetV1\n"
           << "componentNameHex="
           << Hex(reinterpret_cast<const uint8_t*>(asset.componentName.data()),
                  asset.componentName.size())
           << "\nlocaleTagHex="
           << Hex(reinterpret_cast<const uint8_t*>(
                      asset.configuration.localeTag.data()),
                  asset.configuration.localeTag.size())
           << "\ndensityDpi=" << asset.configuration.densityDpi
           << "\nnightMode="
           << (asset.configuration.nightMode ? "true" : "false")
           << "\nconfigurationHash="
           << asset.configuration.configurationHash
           << "\nlabelHex="
           << Hex(reinterpret_cast<const uint8_t*>(asset.label.data()),
                  asset.label.size())
           << "\niconContentTypeHex="
           << Hex(reinterpret_cast<const uint8_t*>(
                      asset.iconContentType.data()),
                  asset.iconContentType.size())
           << "\niconHex="
           << Hex(asset.iconBytes.data(), asset.iconBytes.size())
           << "\nsourceArtifactSha256=" << asset.sourceArtifactSha256
           << "\ncomponentResourceRefsDigest="
           << asset.componentResourceRefsDigest << "\n";
    return ComputeSha256(output.str());
}

LauncherPresentationResponseV1 LauncherPresentationServiceV1::Query(
    const LauncherPresentationQueryV1& query,
    LauncherPresentationFaultInjectorV1* faultInjector)
{
    if (policy_.schemaVersion != 1 || query.schemaVersion != 1 ||
        query.configuration.schemaVersion != 1) {
        return Reject(query, LauncherPresentationVerdict::INVALID_REQUEST,
            "admission:unknown-schema-major");
    }
    if (provider_ == nullptr || query.requestId.empty() ||
        query.requestId.size() > 255 ||
        !IsSafeIdentifier(query.packageName, true, false) ||
        !IsSafeIdentifier(query.componentName, true, true) ||
        query.expectedGeneration == 0 ||
        !IsLowerHexDigest(query.callerScopeDigest) ||
        !IsLowerHexDigest(query.expectedCanonicalDigest) ||
        !IsLowerHexDigest(policy_.expectedCallerScopeDigest) ||
        policy_.policyVersion.empty() ||
        policy_.maxLabelBytes == 0 || policy_.maxIconBytes == 0 ||
        policy_.maxIconBytes >
            static_cast<uint64_t>(std::numeric_limits<size_t>::max()) ||
        !IsValidConfiguration(query.configuration)) {
        return Reject(query, LauncherPresentationVerdict::INVALID_REQUEST,
            "admission:invalid-or-unbounded-request");
    }
    if (query.userId != 0) {
        return Reject(query, LauncherPresentationVerdict::NOT_SUPPORTED_USER,
            "admission:v1-primary-user-only");
    }
    if (query.callerScopeDigest != policy_.expectedCallerScopeDigest) {
        return Reject(query,
            LauncherPresentationVerdict::CALLER_SCOPE_MISMATCH,
            "authorization:caller-scope-mismatch");
    }

    const SnapshotReadResultV1 read = provider_->ReadSnapshot(query);
    if (read.verdict == SnapshotReadVerdict::IO_ERROR) {
        return Reject(query,
            LauncherPresentationVerdict::SNAPSHOT_READ_FAILED,
            "snapshot:read-io-failed:" + read.reason);
    }
    if (read.verdict == SnapshotReadVerdict::NOT_FOUND) {
        return Reject(query, LauncherPresentationVerdict::PACKAGE_NOT_READY,
            "snapshot:package-generation-not-ready");
    }

    const LauncherPresentationSnapshotV1& snapshot = read.snapshot;
    const PresentationGuardJoinV1& guard = snapshot.guard;
    LauncherPresentationResponseV1 response = BaseResponse(query);
    response.generation = guard.canonicalGeneration;
    response.canonicalDigest = guard.canonicalDigest;
    response.projectionDigest = guard.projectionDigest;
    response.resourcePayloadDigest = guard.resourcePayloadDigest;

    if (snapshot.schemaVersion != 1 || guard.schemaVersion != 1 ||
        snapshot.packageName != query.packageName ||
        snapshot.userId != query.userId) {
        response.verdict = LauncherPresentationVerdict::DIGEST_MISMATCH;
        response.reason = "snapshot:identity-readback-mismatch";
        return response;
    }
    if (guard.canonicalState == CanonicalState::REMOVING ||
        guard.projectionState == HostProjectionState::REMOVING ||
        guard.resourceRuntimeState == ResourceRuntimeState::REMOVING) {
        response.verdict = LauncherPresentationVerdict::PACKAGE_REMOVING;
        response.reason = "guard:open-removal-tombstone";
        return response;
    }
    if (guard.canonicalState != CanonicalState::ACTIVE ||
        guard.projectionState == HostProjectionState::NONE ||
        guard.projectionState == HostProjectionState::PREPARED ||
        guard.tokenState != PublicationTokenState::EXTERNAL_READY ||
        guard.resourceRuntimeState == ResourceRuntimeState::NONE ||
        guard.resourceRuntimeState == ResourceRuntimeState::PREPARED) {
        response.verdict = LauncherPresentationVerdict::PACKAGE_NOT_READY;
        response.reason =
            "guard:requires-active-external-ready-resource-ready";
        return response;
    }
    if (guard.canonicalGeneration != query.expectedGeneration ||
        guard.projectionGeneration != query.expectedGeneration ||
        guard.tokenGeneration != query.expectedGeneration ||
        guard.resourceGeneration != query.expectedGeneration) {
        response.verdict = LauncherPresentationVerdict::GENERATION_MISMATCH;
        response.reason = "guard:generation-join-mismatch";
        return response;
    }
    if (guard.canonicalDigest != query.expectedCanonicalDigest ||
        guard.projectionCanonicalDigest != guard.canonicalDigest ||
        guard.tokenCanonicalDigest != guard.canonicalDigest ||
        guard.resourceCanonicalDigest != guard.canonicalDigest ||
        guard.tokenProjectionDigest != guard.projectionDigest) {
        response.verdict = LauncherPresentationVerdict::DIGEST_MISMATCH;
        response.reason = "guard:canonical-or-projection-digest-mismatch";
        return response;
    }

    if (Interrupted(faultInjector, QueryPhase::AFTER_GUARD_JOIN)) {
        response.verdict = LauncherPresentationVerdict::INTERRUPTED_RETRY;
        response.reason = "fault:after-guard-join";
        return response;
    }

    const auto invalidate = [&](LauncherPresentationVerdict verdict,
                                const std::string& reason) {
        CacheInvalidationRequestV1 invalidation;
        invalidation.requestId = query.requestId;
        invalidation.packageName = snapshot.packageName;
        invalidation.userId = snapshot.userId;
        invalidation.generation = guard.canonicalGeneration;
        invalidation.canonicalDigest = guard.canonicalDigest;
        invalidation.projectionDigest = guard.projectionDigest;
        invalidation.resourcePayloadDigest = guard.resourcePayloadDigest;
        invalidation.reason = reason;
        const CacheInvalidationReceiptV1 receipt =
            provider_->InvalidateRebuildableCache(invalidation);
        response.cacheInvalidated = receipt.invalidated;
        response.cacheInvalidationKeyDigest = receipt.cacheKeyDigest;
        if (!receipt.invalidated ||
            receipt.cacheKeyDigest != ComputeSha256(CacheKeyBytes(invalidation))) {
            response.verdict =
                LauncherPresentationVerdict::CACHE_INVALIDATION_FAILED;
            response.reason = "cache:invalidation-failed:" + receipt.reason;
            return response;
        }
        response.verdict = verdict;
        response.reason = reason;
        return response;
    };

    if (guard.projectionState == HostProjectionState::STALE ||
        guard.resourceRuntimeState == ResourceRuntimeState::STALE) {
        return invalidate(LauncherPresentationVerdict::PROJECTION_STALE,
            "readback:stale-projection-or-resource-runtime");
    }
    if (guard.projectionState != HostProjectionState::ACTIVE ||
        guard.resourceRuntimeState != ResourceRuntimeState::READY ||
        !IsLowerHexDigest(guard.canonicalDigest) ||
        !IsLowerHexDigest(guard.projectionDigest) ||
        !IsLowerHexDigest(guard.resourcePayloadDigest)) {
        return invalidate(LauncherPresentationVerdict::PROJECTION_CORRUPT,
            "readback:invalid-active-guard");
    }
    if (Interrupted(faultInjector, QueryPhase::BEFORE_RESOURCE_READBACK)) {
        response.verdict = LauncherPresentationVerdict::INTERRUPTED_RETRY;
        response.reason = "fault:before-resource-readback";
        return response;
    }
    if (ComputeSha256(snapshot.canonicalReadbackBytes) !=
            guard.canonicalDigest ||
        ComputeSha256(snapshot.projectionReadbackBytes) !=
            guard.projectionDigest ||
        ComputeSha256(snapshot.resourcePayloadReadbackBytes) !=
            guard.resourcePayloadDigest) {
        return invalidate(
            LauncherPresentationVerdict::RESOURCE_READBACK_MISMATCH,
            "readback:canonical-projection-resource-digest-mismatch");
    }
    if (Interrupted(faultInjector, QueryPhase::AFTER_RESOURCE_READBACK)) {
        response.verdict = LauncherPresentationVerdict::INTERRUPTED_RETRY;
        response.reason = "fault:after-resource-readback";
        return response;
    }

    const auto componentBegin = std::find_if(snapshot.assets.begin(),
        snapshot.assets.end(), [&](const LauncherAssetV1& asset) {
            return asset.componentName == query.componentName;
        });
    if (componentBegin == snapshot.assets.end()) {
        response.verdict = LauncherPresentationVerdict::RESOURCE_NOT_FOUND;
        response.reason = "selector:launcher-component-not-found";
        return response;
    }
    const auto assetIt = std::find_if(snapshot.assets.begin(),
        snapshot.assets.end(), [&](const LauncherAssetV1& asset) {
            return asset.componentName == query.componentName &&
                SameConfiguration(
                    asset.configuration, query.configuration);
        });
    if (assetIt == snapshot.assets.end()) {
        response.verdict =
            LauncherPresentationVerdict::PRESENTATION_DEGRADED;
        response.reason = "selector:configuration-not-supported";
        return response;
    }
    const size_t exactMatches = static_cast<size_t>(std::count_if(
        snapshot.assets.begin(), snapshot.assets.end(),
        [&](const LauncherAssetV1& asset) {
            return asset.componentName == query.componentName &&
                SameConfiguration(
                    asset.configuration, query.configuration);
        }));
    if (exactMatches != 1) {
        return invalidate(LauncherPresentationVerdict::PROJECTION_CORRUPT,
            "selector:ambiguous-component-configuration");
    }
    const LauncherAssetV1& asset = *assetIt;
    if (asset.status == LauncherAssetStatus::MISSING) {
        response.verdict = LauncherPresentationVerdict::RESOURCE_NOT_FOUND;
        response.reason = "selector:component-resource-missing";
        return response;
    }
    if (asset.schemaVersion != 1 ||
        asset.status != LauncherAssetStatus::RESOLVED ||
        !IsValidConfiguration(asset.configuration) ||
        asset.label.empty() ||
        asset.label.size() > policy_.maxLabelBytes ||
        asset.iconBytes.empty() ||
        asset.iconBytes.size() > policy_.maxIconBytes ||
        asset.iconContentType.empty() ||
        !IsLowerHexDigest(asset.sourceArtifactSha256) ||
        !IsLowerHexDigest(asset.componentResourceRefsDigest) ||
        !IsLowerHexDigest(asset.renderedAssetHash)) {
        return invalidate(LauncherPresentationVerdict::PROJECTION_CORRUPT,
            "asset:invalid-or-unbounded-presentation");
    }
    if (ComputeRenderedAssetHash(asset) != asset.renderedAssetHash) {
        return invalidate(LauncherPresentationVerdict::PROJECTION_CORRUPT,
            "asset:rendered-hash-mismatch");
    }

    response.sourceArtifactSha256 = asset.sourceArtifactSha256;
    response.componentResourceRefsDigest =
        asset.componentResourceRefsDigest;
    response.renderedAssetHash = asset.renderedAssetHash;
    response.configuration = asset.configuration;
    response.label = asset.label;
    response.iconBytes = asset.iconBytes;
    response.iconContentType = asset.iconContentType;
    response.verdict = LauncherPresentationVerdict::READY;
    response.reason = "presentation:generation-bound-readback-ready";

    if (Interrupted(
            faultInjector, QueryPhase::BEFORE_RESPONSE_SERIALIZATION)) {
        response = BaseResponse(query);
        response.verdict = LauncherPresentationVerdict::INTERRUPTED_RETRY;
        response.reason = "fault:before-response-serialization";
        return response;
    }
    const std::string serialized = SerializeResponse(response);
    if (serialized.empty()) {
        response = BaseResponse(query);
        response.verdict = LauncherPresentationVerdict::PROJECTION_CORRUPT;
        response.reason = "response:serialization-failed";
        return response;
    }
    if (Interrupted(
            faultInjector, QueryPhase::AFTER_RESPONSE_SERIALIZATION)) {
        response = BaseResponse(query);
        response.verdict = LauncherPresentationVerdict::INTERRUPTED_RETRY;
        response.reason = "fault:after-response-serialization";
        return response;
    }
    return response;
}

const char* LauncherPresentationServiceV1::VerdictName(
    LauncherPresentationVerdict verdict)
{
    switch (verdict) {
        case LauncherPresentationVerdict::READY: return "READY";
        case LauncherPresentationVerdict::INVALID_REQUEST:
            return "INVALID_REQUEST";
        case LauncherPresentationVerdict::NOT_SUPPORTED_USER:
            return "NOT_SUPPORTED_USER";
        case LauncherPresentationVerdict::CALLER_SCOPE_MISMATCH:
            return "CALLER_SCOPE_MISMATCH";
        case LauncherPresentationVerdict::PACKAGE_NOT_READY:
            return "PACKAGE_NOT_READY";
        case LauncherPresentationVerdict::PACKAGE_REMOVING:
            return "PACKAGE_REMOVING";
        case LauncherPresentationVerdict::RESOURCE_NOT_FOUND:
            return "RESOURCE_NOT_FOUND";
        case LauncherPresentationVerdict::PRESENTATION_DEGRADED:
            return "PRESENTATION_DEGRADED";
        case LauncherPresentationVerdict::GENERATION_MISMATCH:
            return "GENERATION_MISMATCH";
        case LauncherPresentationVerdict::DIGEST_MISMATCH:
            return "DIGEST_MISMATCH";
        case LauncherPresentationVerdict::PROJECTION_STALE:
            return "PROJECTION_STALE";
        case LauncherPresentationVerdict::PROJECTION_CORRUPT:
            return "PROJECTION_CORRUPT";
        case LauncherPresentationVerdict::RESOURCE_READBACK_MISMATCH:
            return "RESOURCE_READBACK_MISMATCH";
        case LauncherPresentationVerdict::CACHE_INVALIDATION_FAILED:
            return "CACHE_INVALIDATION_FAILED";
        case LauncherPresentationVerdict::SNAPSHOT_READ_FAILED:
            return "SNAPSHOT_READ_FAILED";
        case LauncherPresentationVerdict::INTERRUPTED_RETRY:
            return "INTERRUPTED_RETRY";
    }
    return "INVALID_REQUEST";
}

const char* LauncherPresentationServiceV1::CanonicalStateName(
    CanonicalState state)
{
    switch (state) {
        case CanonicalState::ABSENT: return "ABSENT";
        case CanonicalState::PREPARED: return "PREPARED";
        case CanonicalState::ACTIVE: return "ACTIVE";
        case CanonicalState::REMOVING: return "REMOVING";
    }
    return "ABSENT";
}

const char* LauncherPresentationServiceV1::ProjectionStateName(
    HostProjectionState state)
{
    switch (state) {
        case HostProjectionState::NONE: return "NONE";
        case HostProjectionState::PREPARED: return "PREPARED";
        case HostProjectionState::ACTIVE: return "ACTIVE";
        case HostProjectionState::STALE: return "STALE";
        case HostProjectionState::REMOVING: return "REMOVING";
    }
    return "NONE";
}

const char* LauncherPresentationServiceV1::TokenStateName(
    PublicationTokenState state)
{
    switch (state) {
        case PublicationTokenState::NONE: return "NONE";
        case PublicationTokenState::PREPARED: return "PREPARED";
        case PublicationTokenState::CANONICAL_SELECTED:
            return "CANONICAL_SELECTED";
        case PublicationTokenState::EXTERNAL_READY:
            return "EXTERNAL_READY";
    }
    return "NONE";
}

const char* LauncherPresentationServiceV1::ResourceStateName(
    ResourceRuntimeState state)
{
    switch (state) {
        case ResourceRuntimeState::NONE: return "NONE";
        case ResourceRuntimeState::PREPARED: return "PREPARED";
        case ResourceRuntimeState::READY: return "READY";
        case ResourceRuntimeState::STALE: return "STALE";
        case ResourceRuntimeState::REMOVING: return "REMOVING";
    }
    return "NONE";
}

std::string LauncherPresentationServiceV1::SerializeResponse(
    const LauncherPresentationResponseV1& response)
{
    std::ostringstream output;
    output << "{\"schemaVersion\":1,\"actionId\":\""
           << response.actionId << "\",\"requestId\":\""
           << JsonEscape(response.requestId) << "\",\"packageName\":\""
           << JsonEscape(response.packageName)
           << "\",\"componentName\":\""
           << JsonEscape(response.componentName) << "\",\"userId\":"
           << response.userId << ",\"generation\":" << response.generation
           << ",\"canonicalDigest\":\"" << response.canonicalDigest
           << "\",\"projectionDigest\":\"" << response.projectionDigest
           << "\",\"resourcePayloadDigest\":\""
           << response.resourcePayloadDigest
           << "\",\"sourceArtifactSha256\":\""
           << response.sourceArtifactSha256
           << "\",\"componentResourceRefsDigest\":\""
           << response.componentResourceRefsDigest
           << "\",\"renderedAssetHash\":\""
           << response.renderedAssetHash << "\",\"configuration\":{"
           << "\"schemaVersion\":1,\"localeTag\":\""
           << JsonEscape(response.configuration.localeTag)
           << "\",\"densityDpi\":" << response.configuration.densityDpi
           << ",\"nightMode\":"
           << (response.configuration.nightMode ? "true" : "false")
           << ",\"configurationHash\":\""
           << response.configuration.configurationHash
           << "\"},\"label\":\"" << JsonEscape(response.label)
           << "\",\"iconContentType\":\""
           << JsonEscape(response.iconContentType)
           << "\",\"iconBytesSha256\":\""
           << Sha256Hex(response.iconBytes.data(), response.iconBytes.size())
           << "\",\"verdict\":\"" << VerdictName(response.verdict)
           << "\",\"reason\":\"" << JsonEscape(response.reason)
           << "\",\"cacheInvalidated\":"
           << (response.cacheInvalidated ? "true" : "false")
           << ",\"cacheInvalidationKeyDigest\":\""
           << response.cacheInvalidationKeyDigest << "\"}\n";
    return output.str();
}

}  // namespace oh_adapter::launcher_presentation
