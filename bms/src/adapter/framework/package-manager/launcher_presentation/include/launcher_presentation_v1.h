#ifndef OH_ADAPTER_LAUNCHER_PRESENTATION_V1_H
#define OH_ADAPTER_LAUNCHER_PRESENTATION_V1_H

#include <cstdint>
#include <string>
#include <vector>

namespace oh_adapter::launcher_presentation {

enum class CanonicalState {
    ABSENT,
    PREPARED,
    ACTIVE,
    REMOVING,
};

enum class HostProjectionState {
    NONE,
    PREPARED,
    ACTIVE,
    STALE,
    REMOVING,
};

enum class PublicationTokenState {
    NONE,
    PREPARED,
    CANONICAL_SELECTED,
    EXTERNAL_READY,
};

enum class ResourceRuntimeState {
    NONE,
    PREPARED,
    READY,
    STALE,
    REMOVING,
};

enum class LauncherAssetStatus {
    RESOLVED,
    MISSING,
};

enum class SnapshotReadVerdict {
    READY,
    NOT_FOUND,
    IO_ERROR,
};

enum class LauncherPresentationVerdict {
    READY,
    INVALID_REQUEST,
    NOT_SUPPORTED_USER,
    CALLER_SCOPE_MISMATCH,
    PACKAGE_NOT_READY,
    PACKAGE_REMOVING,
    RESOURCE_NOT_FOUND,
    PRESENTATION_DEGRADED,
    GENERATION_MISMATCH,
    DIGEST_MISMATCH,
    PROJECTION_STALE,
    PROJECTION_CORRUPT,
    RESOURCE_READBACK_MISMATCH,
    CACHE_INVALIDATION_FAILED,
    SNAPSHOT_READ_FAILED,
    INTERRUPTED_RETRY,
};

enum class QueryPhase {
    AFTER_GUARD_JOIN,
    BEFORE_RESOURCE_READBACK,
    AFTER_RESOURCE_READBACK,
    BEFORE_RESPONSE_SERIALIZATION,
    AFTER_RESPONSE_SERIALIZATION,
};

struct ConfigurationSelectorV1 {
    uint32_t schemaVersion = 1;
    std::string localeTag;
    uint32_t densityDpi = 0;
    bool nightMode = false;
    std::string configurationHash;
};

struct LauncherPresentationQueryV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    std::string callerScopeDigest;
    std::string packageName;
    std::string componentName;
    uint32_t userId = 0;
    uint64_t expectedGeneration = 0;
    std::string expectedCanonicalDigest;
    ConfigurationSelectorV1 configuration;
};

struct LauncherPresentationPolicyV1 {
    uint32_t schemaVersion = 1;
    std::string policyVersion;
    std::string expectedCallerScopeDigest;
    uint64_t maxLabelBytes = 4096;
    uint64_t maxIconBytes = 8 * 1024 * 1024;
};

struct PresentationGuardJoinV1 {
    uint32_t schemaVersion = 1;
    CanonicalState canonicalState = CanonicalState::ABSENT;
    uint64_t canonicalGeneration = 0;
    std::string canonicalDigest;

    HostProjectionState projectionState = HostProjectionState::NONE;
    uint64_t projectionGeneration = 0;
    std::string projectionCanonicalDigest;
    std::string projectionDigest;

    PublicationTokenState tokenState = PublicationTokenState::NONE;
    uint64_t tokenGeneration = 0;
    std::string tokenCanonicalDigest;
    std::string tokenProjectionDigest;

    ResourceRuntimeState resourceRuntimeState = ResourceRuntimeState::NONE;
    uint64_t resourceGeneration = 0;
    std::string resourceCanonicalDigest;
    std::string resourcePayloadDigest;
};

struct LauncherAssetV1 {
    uint32_t schemaVersion = 1;
    LauncherAssetStatus status = LauncherAssetStatus::MISSING;
    std::string componentName;
    ConfigurationSelectorV1 configuration;
    std::string label;
    std::vector<uint8_t> iconBytes;
    std::string iconContentType;
    std::string sourceArtifactSha256;
    std::string componentResourceRefsDigest;
    std::string renderedAssetHash;
};

struct LauncherPresentationSnapshotV1 {
    uint32_t schemaVersion = 1;
    std::string packageName;
    uint32_t userId = 0;
    PresentationGuardJoinV1 guard;
    std::string canonicalReadbackBytes;
    std::string projectionReadbackBytes;
    std::string resourcePayloadReadbackBytes;
    std::vector<LauncherAssetV1> assets;
};

struct SnapshotReadResultV1 {
    SnapshotReadVerdict verdict = SnapshotReadVerdict::IO_ERROR;
    LauncherPresentationSnapshotV1 snapshot;
    std::string reason;
};

struct CacheInvalidationRequestV1 {
    uint32_t schemaVersion = 1;
    std::string actionId = "Fn01.A09";
    std::string requestId;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    std::string projectionDigest;
    std::string resourcePayloadDigest;
    std::string reason;
};

struct CacheInvalidationReceiptV1 {
    uint32_t schemaVersion = 1;
    bool invalidated = false;
    std::string cacheKeyDigest;
    std::string reason;
};

struct LauncherPresentationResponseV1 {
    uint32_t schemaVersion = 1;
    std::string actionId = "Fn01.A09";
    std::string requestId;
    std::string packageName;
    std::string componentName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    std::string projectionDigest;
    std::string resourcePayloadDigest;
    std::string sourceArtifactSha256;
    std::string componentResourceRefsDigest;
    std::string renderedAssetHash;
    ConfigurationSelectorV1 configuration;
    std::string label;
    std::vector<uint8_t> iconBytes;
    std::string iconContentType;
    LauncherPresentationVerdict verdict =
        LauncherPresentationVerdict::INVALID_REQUEST;
    std::string reason;
    bool cacheInvalidated = false;
    std::string cacheInvalidationKeyDigest;
};

class LauncherPresentationSnapshotProviderV1 {
public:
    virtual ~LauncherPresentationSnapshotProviderV1() = default;
    virtual SnapshotReadResultV1 ReadSnapshot(
        const LauncherPresentationQueryV1& query) = 0;
    virtual CacheInvalidationReceiptV1 InvalidateRebuildableCache(
        const CacheInvalidationRequestV1& request) = 0;
};

class LauncherPresentationFaultInjectorV1 {
public:
    virtual ~LauncherPresentationFaultInjectorV1() = default;
    virtual bool InterruptAt(QueryPhase phase) = 0;
};

class NoLauncherPresentationFaultInjectorV1 final
    : public LauncherPresentationFaultInjectorV1 {
public:
    bool InterruptAt(QueryPhase) override
    {
        return false;
    }
};

class LauncherPresentationServiceV1 final {
public:
    LauncherPresentationServiceV1(
        LauncherPresentationPolicyV1 policy,
        LauncherPresentationSnapshotProviderV1* provider);

    LauncherPresentationResponseV1 Query(
        const LauncherPresentationQueryV1& query,
        LauncherPresentationFaultInjectorV1* faultInjector);

    static const char* VerdictName(LauncherPresentationVerdict verdict);
    static const char* CanonicalStateName(CanonicalState state);
    static const char* ProjectionStateName(HostProjectionState state);
    static const char* TokenStateName(PublicationTokenState state);
    static const char* ResourceStateName(ResourceRuntimeState state);
    static std::string ComputeSha256(const std::string& bytes);
    static std::string ComputeRenderedAssetHash(
        const LauncherAssetV1& asset);
    static std::string SerializeResponse(
        const LauncherPresentationResponseV1& response);

private:
    LauncherPresentationPolicyV1 policy_;
    LauncherPresentationSnapshotProviderV1* provider_;
};

}  // namespace oh_adapter::launcher_presentation

#endif  // OH_ADAPTER_LAUNCHER_PRESENTATION_V1_H
