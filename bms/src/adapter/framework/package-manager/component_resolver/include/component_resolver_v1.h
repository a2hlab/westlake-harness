#ifndef OH_ADAPTER_COMPONENT_RESOLVER_V1_H
#define OH_ADAPTER_COMPONENT_RESOLVER_V1_H

#include "package_transaction_v1.h"

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace oh_adapter::component_resolver {

enum class ComponentKind : uint8_t {
    ACTIVITY = 1,
    SERVICE = 2,
    RECEIVER = 3,
    PROVIDER = 4,
};

enum class ComponentResolveVerdict {
    READY,
    INVALID_REQUEST,
    NOT_SUPPORTED,
    INVALID_COMPONENT_KIND,
    NOT_SUPPORTED_FILTER,
    PACKAGE_REMOVING,
    PACKAGE_NOT_READY,
    DATA_INCONSISTENT,
};

enum class ResolvePhase {
    SNAPSHOT_FROZEN,
    CANDIDATES_FILTERED,
    RESPONSE_SERIALIZED,
};

struct IntentDataV1 {
    std::string action;
    std::vector<std::string> categories;
    std::string resolvedType;
    std::string scheme;
    std::string host;
    int32_t port = -1;
    std::string path;
    std::string packageSelector;
    std::string explicitPackage;
    std::string explicitClass;
};

struct CallerResolveContextV1 {
    int32_t callingUid = -1;
    std::string callerPackageName;
    std::string visibilityScopeDigest;
    bool canSeeAllPackages = false;
    std::vector<std::string> visiblePackageNames;
    std::vector<std::string> grantedPermissions;
};

struct IntentFilterDataV1 {
    std::vector<std::string> actions;
    std::vector<std::string> categories;
    std::vector<std::string> mimeTypes;
    std::vector<std::string> schemes;
    std::vector<std::string> hosts;
    std::vector<int32_t> ports;
    std::vector<std::string> pathPrefixes;
    bool isDefault = false;
    bool hasUnsupportedPattern = false;
    int32_t priority = 0;
};

struct ComponentFactV1 {
    ComponentKind kind = ComponentKind::ACTIVITY;
    std::string name;
    bool enabled = true;
    bool exported = false;
    std::string requiredPermission;
    int32_t preferredOrder = 0;
    bool system = false;
    std::vector<IntentFilterDataV1> filters;
};

struct PackageComponentIndexV1 {
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    bool removing = false;
    std::vector<ComponentFactV1> components;
};

struct ComponentCatalogV1 {
    uint32_t schemaVersion = 1;
    uint64_t catalogRevision = 0;
    std::vector<PackageComponentIndexV1> packages;
};

struct ComponentResolveRequestV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    ComponentKind kind = ComponentKind::ACTIVITY;
    bool kindWasRecognized = true;
    IntentDataV1 intent;
    uint64_t flags = 0;
    bool defaultOnly = false;
    uint32_t userId = 0;
    CallerResolveContextV1 caller;
    std::optional<uint64_t> expectedCatalogRevision;
    std::optional<std::string> expectedIndexDigest;
    std::optional<uint64_t> expectedGeneration;
    std::optional<std::string> expectedCanonicalDigest;
};

struct PackageGuardV1 {
    uint64_t catalogRevision = 0;
    bool removing = false;
    bool hasCanonical = false;
    uint64_t generation = 0;
    std::string canonicalDigest;
    bool projectionActive = false;
    bool tokenExternalReady = false;
    uint64_t projectionGeneration = 0;
    std::string projectionCanonicalDigest;
    uint64_t tokenGeneration = 0;
    std::string tokenCanonicalDigest;
};

struct ResolveCandidateV1 {
    std::string packageName;
    std::string componentName;
    ComponentKind kind = ComponentKind::ACTIVITY;
    bool exported = false;
    std::string requiredPermission;
    int32_t priority = 0;
    int32_t preferredOrder = 0;
    bool isDefault = false;
    int32_t match = 0;
    bool system = false;
    uint64_t generation = 0;
    uint64_t stableOrdinal = 0;
};

struct ResolveTraceEventV1 {
    uint64_t ordinal = 0;
    std::string packageName;
    std::string componentName;
    std::string decision;
};

struct PackageGuardEvidenceV1 {
    std::string packageName;
    uint64_t generation = 0;
    std::string canonicalState;
    std::string canonicalDigest;
    std::string projectionState;
    std::string projectionDigest;
    std::string tokenState;
    std::string tokenDigest;
};

struct ComponentResolveResponseV1 {
    std::string requestId;
    ComponentResolveVerdict verdict =
        ComponentResolveVerdict::DATA_INCONSISTENT;
    std::string reason;
    uint64_t catalogRevision = 0;
    std::string indexDigest;
    std::vector<ResolveCandidateV1> results;
    std::vector<ResolveTraceEventV1> trace;
    std::vector<PackageGuardEvidenceV1> guardJoin;
};

class ComponentCatalogProviderV1 {
public:
    virtual ~ComponentCatalogProviderV1() = default;
    virtual bool Read(ComponentCatalogV1* catalog, std::string* indexDigest,
        std::string* error) = 0;
};

class PackageGuardReaderV1 {
public:
    virtual ~PackageGuardReaderV1() = default;
    virtual bool Read(uint32_t userId, const std::string& packageName,
        PackageGuardV1* guard, std::string* error) = 0;
};

class ResolveFaultInjectorV1 {
public:
    virtual ~ResolveFaultInjectorV1() = default;
    virtual bool InterruptAfter(ResolvePhase phase) = 0;
};

class NoResolveFaultInjectorV1 final : public ResolveFaultInjectorV1 {
public:
    bool InterruptAfter(ResolvePhase) override
    {
        return false;
    }
};

class ComponentResolverServiceV1 {
public:
    ComponentResolverServiceV1(ComponentCatalogProviderV1* catalogProvider,
        PackageGuardReaderV1* guardReader,
        ResolveFaultInjectorV1* faultInjector);

    ComponentResolveResponseV1 Resolve(
        const ComponentResolveRequestV1& request) const;

private:
    ComponentCatalogProviderV1* catalogProvider_;
    PackageGuardReaderV1* guardReader_;
    ResolveFaultInjectorV1* faultInjector_;
};

bool SerializeComponentCatalogV1(const ComponentCatalogV1& catalog,
    std::vector<uint8_t>* bytes, std::string* error);
bool ParseComponentCatalogV1(const std::vector<uint8_t>& bytes,
    ComponentCatalogV1* catalog, std::string* error);
std::string ComponentCatalogDigestV1(const std::vector<uint8_t>& bytes);
std::string ComponentResolveResponseJsonV1(
    const ComponentResolveResponseV1& response);

bool ParseComponentKindV1(const std::string& value, ComponentKind* kind);
const char* ComponentKindNameV1(ComponentKind kind);
const char* ComponentResolveVerdictNameV1(ComponentResolveVerdict verdict);

}  // namespace oh_adapter::component_resolver

#endif  // OH_ADAPTER_COMPONENT_RESOLVER_V1_H
