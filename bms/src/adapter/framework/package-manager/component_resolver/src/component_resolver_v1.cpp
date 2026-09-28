#include "component_resolver_v1.h"

#include "sha256.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <limits>
#include <set>
#include <sstream>
#include <string_view>

namespace oh_adapter::component_resolver {
namespace {

constexpr size_t MAX_STRING_BYTES = 64 * 1024;
constexpr size_t MAX_PACKAGES = 8192;
constexpr size_t MAX_COMPONENTS_PER_PACKAGE = 65536;
constexpr size_t MAX_FILTERS_PER_COMPONENT = 4096;
constexpr size_t MAX_FILTER_MEMBERS = 16384;
constexpr int32_t MATCH_EMPTY = 0x100000;
constexpr int32_t MATCH_SCHEME = 0x200000;
constexpr int32_t MATCH_HOST = 0x300000;
constexpr int32_t MATCH_PORT = 0x400000;
constexpr int32_t MATCH_PATH = 0x500000;
constexpr int32_t MATCH_TYPE = 0x600000;
constexpr int32_t MATCH_ADJUSTMENT_NORMAL = 0x8000;
constexpr uint64_t MATCH_DISABLED_COMPONENTS = 0x00000200ULL;
constexpr uint64_t MATCH_DEFAULT_ONLY = 0x00010000ULL;
constexpr uint64_t MATCH_SYSTEM_ONLY = 0x00100000ULL;
constexpr uint64_t SUPPORTED_FLAGS =
    MATCH_DISABLED_COMPONENTS | MATCH_DEFAULT_ONLY | MATCH_SYSTEM_ONLY;

bool IsBoundedToken(const std::string& value, bool allowEmpty = false)
{
    if ((!allowEmpty && value.empty()) || value.size() > 4096) return false;
    return value.find('\0') == std::string::npos &&
        value.find('\n') == std::string::npos &&
        value.find('\r') == std::string::npos;
}

bool IsPackageName(const std::string& value)
{
    if (!IsBoundedToken(value) || value.size() > 255 ||
        value.front() == '.' || value.back() == '.') {
        return false;
    }
    bool segmentStart = true;
    for (char c : value) {
        if (c == '.') {
            if (segmentStart) return false;
            segmentStart = true;
        } else if (std::isalnum(static_cast<unsigned char>(c)) || c == '_') {
            segmentStart = false;
        } else {
            return false;
        }
    }
    return !segmentStart;
}

bool Contains(const std::vector<std::string>& values,
    const std::string& value)
{
    return std::find(values.begin(), values.end(), value) != values.end();
}

bool EqualsIgnoreAsciiCase(const std::string& left,
    const std::string& right)
{
    if (left.size() != right.size()) return false;
    for (size_t index = 0; index < left.size(); ++index) {
        if (std::tolower(static_cast<unsigned char>(left[index])) !=
            std::tolower(static_cast<unsigned char>(right[index]))) {
            return false;
        }
    }
    return true;
}

bool CallerCanSee(const ComponentResolveRequestV1& request,
    const std::string& packageName)
{
    return request.caller.canSeeAllPackages ||
        request.caller.callerPackageName == packageName ||
        Contains(request.caller.visiblePackageNames, packageName);
}

bool CallerHasPermission(const ComponentResolveRequestV1& request,
    const std::string& permission)
{
    return permission.empty() ||
        Contains(request.caller.grantedPermissions, "*") ||
        Contains(request.caller.grantedPermissions, permission);
}

bool MimeMatches(const std::string& filterType,
    const std::string& resolvedType, int32_t* score)
{
    if (filterType == resolvedType) {
        *score = MATCH_TYPE;
        return true;
    }
    const auto filterSlash = filterType.find('/');
    const auto requestSlash = resolvedType.find('/');
    if (filterSlash == std::string::npos ||
        requestSlash == std::string::npos) {
        return false;
    }
    const auto filterMajor = filterType.substr(0, filterSlash);
    const auto filterMinor = filterType.substr(filterSlash + 1);
    const auto requestMajor = resolvedType.substr(0, requestSlash);
    const auto requestMinor = resolvedType.substr(requestSlash + 1);
    if ((filterMajor == "*" || requestMajor == "*" ||
            filterMajor == requestMajor) &&
        (filterMinor == "*" || requestMinor == "*" ||
            filterMinor == requestMinor)) {
        *score = MATCH_TYPE;
        return true;
    }
    return false;
}

bool FilterMatches(const IntentFilterDataV1& filter,
    const ComponentResolveRequestV1& request, int32_t* match)
{
    if (!request.intent.action.empty() &&
        !Contains(filter.actions, request.intent.action)) {
        return false;
    }
    if (request.intent.action.empty() && !filter.actions.empty()) return false;
    for (const auto& category : request.intent.categories) {
        if (!Contains(filter.categories, category)) return false;
    }
    if (request.defaultOnly && !filter.isDefault) return false;

    int32_t score = MATCH_EMPTY;
    if (!request.intent.resolvedType.empty()) {
        bool matched = false;
        for (const auto& type : filter.mimeTypes) {
            int32_t typeScore = 0;
            if (MimeMatches(type, request.intent.resolvedType, &typeScore)) {
                score = std::max(score, typeScore);
                matched = true;
            }
        }
        if (!matched) return false;
    } else if (!filter.mimeTypes.empty()) {
        return false;
    }

    const bool hasRequestData = !request.intent.scheme.empty() ||
        !request.intent.host.empty() || request.intent.port >= 0 ||
        !request.intent.path.empty();
    const bool hasFilterData = !filter.schemes.empty() ||
        !filter.hosts.empty() || !filter.ports.empty() ||
        !filter.pathPrefixes.empty();
    if (hasRequestData) {
        if (request.intent.scheme.empty()) {
            if (!filter.schemes.empty()) return false;
        } else if (filter.schemes.empty()) {
            // Android's type-only filters accept null/content/file schemes.
            if (filter.mimeTypes.empty() ||
                (request.intent.scheme != "content" &&
                    request.intent.scheme != "file")) {
                return false;
            }
        } else {
            if (!Contains(filter.schemes, request.intent.scheme)) return false;
            score = std::max(score, MATCH_SCHEME);
        }
        if (!filter.hosts.empty()) {
            bool hostMatched = false;
            for (const auto& host : filter.hosts) {
                if (EqualsIgnoreAsciiCase(host, request.intent.host)) {
                    hostMatched = true;
                    break;
                }
            }
            if (!hostMatched) return false;
            score = std::max(score, MATCH_HOST);
        }
        if (!filter.ports.empty()) {
            if (std::find(filter.ports.begin(), filter.ports.end(),
                    request.intent.port) == filter.ports.end()) {
                return false;
            }
            score = std::max(score, MATCH_PORT);
        }
        if (!filter.pathPrefixes.empty()) {
            bool matched = false;
            for (const auto& prefix : filter.pathPrefixes) {
                if (request.intent.path.rfind(prefix, 0) == 0) {
                    matched = true;
                    break;
                }
            }
            if (!matched) return false;
            score = std::max(score, MATCH_PATH);
        }
    } else if (hasFilterData) {
        return false;
    }
    *match = score + MATCH_ADJUSTMENT_NORMAL;
    return true;
}

ComponentResolveResponseV1 Response(
    const ComponentResolveRequestV1& request,
    ComponentResolveVerdict verdict, const char* reason,
    uint64_t revision = 0, std::string digest = {})
{
    ComponentResolveResponseV1 response;
    response.requestId = request.requestId;
    response.verdict = verdict;
    response.reason = reason;
    response.catalogRevision = revision;
    response.indexDigest = std::move(digest);
    return response;
}

PackageGuardEvidenceV1 GuardEvidence(const std::string& packageName,
    const PackageGuardV1& guard)
{
    PackageGuardEvidenceV1 evidence;
    evidence.packageName = packageName;
    evidence.generation = guard.generation;
    evidence.canonicalState =
        guard.hasCanonical ? "CANONICAL_SELECTED" : "NONE";
    evidence.canonicalDigest = guard.canonicalDigest;
    evidence.projectionState =
        guard.projectionActive ? "ACTIVE" : "NONE";
    evidence.projectionDigest = guard.projectionCanonicalDigest;
    evidence.tokenState =
        guard.tokenExternalReady ? "EXTERNAL_READY" : "NONE";
    evidence.tokenDigest = guard.tokenCanonicalDigest;
    return evidence;
}

ComponentResolveResponseV1 GuardResponse(
    const ComponentResolveRequestV1& request,
    ComponentResolveVerdict verdict, const char* reason,
    uint64_t revision, const std::string& digest,
    const std::string& packageName, const PackageGuardV1& guard)
{
    auto response = Response(
        request, verdict, reason, revision, digest);
    response.guardJoin.push_back(GuardEvidence(packageName, guard));
    return response;
}

bool ValidRequest(const ComponentResolveRequestV1& request)
{
    if (request.schemaVersion != 1 || request.requestId.empty() ||
        request.requestId.size() > 512 ||
        request.caller.callingUid < 0 ||
        request.caller.visibilityScopeDigest.empty()) {
        return false;
    }
    const auto& intent = request.intent;
    const std::array<const std::string*, 9> strings = {
        &intent.action, &intent.resolvedType, &intent.scheme, &intent.host,
        &intent.path, &intent.packageSelector, &intent.explicitPackage,
        &intent.explicitClass, &request.caller.callerPackageName,
    };
    for (const auto* value : strings) {
        if (!IsBoundedToken(*value, true)) return false;
    }
    for (const auto& value : intent.categories) {
        if (!IsBoundedToken(value)) return false;
    }
    const bool hasExplicitPackage = !intent.explicitPackage.empty();
    const bool hasExplicitClass = !intent.explicitClass.empty();
    if (hasExplicitPackage != hasExplicitClass) return false;
    if (hasExplicitPackage &&
        (!IsPackageName(intent.explicitPackage) ||
            intent.explicitClass.size() > 1024)) {
        return false;
    }
    if (!intent.packageSelector.empty() &&
        !IsPackageName(intent.packageSelector)) {
        return false;
    }
    if ((request.expectedGeneration.has_value() ||
            request.expectedCanonicalDigest.has_value()) &&
        intent.packageSelector.empty() && intent.explicitPackage.empty()) {
        return false;
    }
    return true;
}

std::string TargetPackage(const ComponentResolveRequestV1& request)
{
    return !request.intent.explicitPackage.empty()
        ? request.intent.explicitPackage : request.intent.packageSelector;
}

bool SameGenerationReady(const PackageComponentIndexV1& indexed,
    const PackageGuardV1& guard, ComponentResolveVerdict* verdict,
    const char** reason)
{
    if (indexed.removing || guard.removing) {
        *verdict = ComponentResolveVerdict::PACKAGE_REMOVING;
        *reason = "PACKAGE_REMOVING";
        return false;
    }
    if (!guard.hasCanonical || !guard.projectionActive ||
        !guard.tokenExternalReady) {
        *verdict = ComponentResolveVerdict::PACKAGE_NOT_READY;
        *reason = "EXTERNAL_READY_NOT_ESTABLISHED";
        return false;
    }
    if (indexed.generation == 0 || indexed.canonicalDigest.empty() ||
        indexed.generation != guard.generation ||
        indexed.canonicalDigest != guard.canonicalDigest ||
        guard.projectionGeneration != guard.generation ||
        guard.projectionCanonicalDigest != guard.canonicalDigest ||
        guard.tokenGeneration != guard.generation ||
        guard.tokenCanonicalDigest != guard.canonicalDigest) {
        *verdict = ComponentResolveVerdict::PACKAGE_NOT_READY;
        *reason = "GENERATION_DIGEST_JOIN_MISMATCH";
        return false;
    }
    return true;
}

class Writer {
public:
    explicit Writer(std::vector<uint8_t>* bytes) : bytes_(bytes) {}

    void U8(uint8_t value) { bytes_->push_back(value); }
    void U32(uint32_t value)
    {
        for (unsigned i = 0; i < 4; ++i) U8((value >> (i * 8)) & 0xff);
    }
    void U64(uint64_t value)
    {
        for (unsigned i = 0; i < 8; ++i) U8((value >> (i * 8)) & 0xff);
    }
    void I32(int32_t value) { U32(static_cast<uint32_t>(value)); }
    bool String(const std::string& value)
    {
        if (value.size() > MAX_STRING_BYTES) return false;
        U32(static_cast<uint32_t>(value.size()));
        bytes_->insert(bytes_->end(), value.begin(), value.end());
        return true;
    }
    bool Strings(const std::vector<std::string>& values)
    {
        if (values.size() > MAX_FILTER_MEMBERS) return false;
        U32(static_cast<uint32_t>(values.size()));
        for (const auto& value : values) {
            if (!String(value)) return false;
        }
        return true;
    }
    bool Ints(const std::vector<int32_t>& values)
    {
        if (values.size() > MAX_FILTER_MEMBERS) return false;
        U32(static_cast<uint32_t>(values.size()));
        for (const auto value : values) I32(value);
        return true;
    }

private:
    std::vector<uint8_t>* bytes_;
};

class Reader {
public:
    explicit Reader(const std::vector<uint8_t>& bytes) : bytes_(bytes) {}

    bool U8(uint8_t* value)
    {
        if (offset_ >= bytes_.size()) return false;
        *value = bytes_[offset_++];
        return true;
    }
    bool U32(uint32_t* value)
    {
        uint32_t result = 0;
        for (unsigned i = 0; i < 4; ++i) {
            uint8_t byte = 0;
            if (!U8(&byte)) return false;
            result |= static_cast<uint32_t>(byte) << (i * 8);
        }
        *value = result;
        return true;
    }
    bool U64(uint64_t* value)
    {
        uint64_t result = 0;
        for (unsigned i = 0; i < 8; ++i) {
            uint8_t byte = 0;
            if (!U8(&byte)) return false;
            result |= static_cast<uint64_t>(byte) << (i * 8);
        }
        *value = result;
        return true;
    }
    bool I32(int32_t* value)
    {
        uint32_t result = 0;
        if (!U32(&result)) return false;
        *value = static_cast<int32_t>(result);
        return true;
    }
    bool String(std::string* value)
    {
        uint32_t size = 0;
        if (!U32(&size) || size > MAX_STRING_BYTES ||
            size > bytes_.size() - offset_) {
            return false;
        }
        value->assign(reinterpret_cast<const char*>(bytes_.data() + offset_),
            size);
        offset_ += size;
        return true;
    }
    bool Strings(std::vector<std::string>* values)
    {
        uint32_t count = 0;
        if (!U32(&count) || count > MAX_FILTER_MEMBERS) return false;
        values->clear();
        values->reserve(count);
        for (uint32_t index = 0; index < count; ++index) {
            std::string value;
            if (!String(&value)) return false;
            values->push_back(std::move(value));
        }
        return true;
    }
    bool Ints(std::vector<int32_t>* values)
    {
        uint32_t count = 0;
        if (!U32(&count) || count > MAX_FILTER_MEMBERS) return false;
        values->clear();
        values->reserve(count);
        for (uint32_t index = 0; index < count; ++index) {
            int32_t value = 0;
            if (!I32(&value)) return false;
            values->push_back(value);
        }
        return true;
    }
    bool Done() const { return offset_ == bytes_.size(); }

private:
    const std::vector<uint8_t>& bytes_;
    size_t offset_ = 0;
};

std::string JsonEscape(const std::string& value)
{
    std::ostringstream out;
    for (const unsigned char c : value) {
        switch (c) {
            case '"': out << "\\\""; break;
            case '\\': out << "\\\\"; break;
            case '\b': out << "\\b"; break;
            case '\f': out << "\\f"; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default:
                if (c < 0x20) {
                    static constexpr char HEX[] = "0123456789abcdef";
                    out << "\\u00" << HEX[c >> 4] << HEX[c & 15];
                } else {
                    out << static_cast<char>(c);
                }
        }
    }
    return out.str();
}

}  // namespace

ComponentResolverServiceV1::ComponentResolverServiceV1(
    ComponentCatalogProviderV1* catalogProvider,
    PackageGuardReaderV1* guardReader,
    ResolveFaultInjectorV1* faultInjector)
    : catalogProvider_(catalogProvider),
      guardReader_(guardReader),
      faultInjector_(faultInjector)
{
}

ComponentResolveResponseV1 ComponentResolverServiceV1::Resolve(
    const ComponentResolveRequestV1& request) const
{
    if (catalogProvider_ == nullptr || guardReader_ == nullptr ||
        faultInjector_ == nullptr || !ValidRequest(request)) {
        return Response(request, ComponentResolveVerdict::INVALID_REQUEST,
            "INVALID_REQUEST");
    }
    if (request.userId != 0) {
        return Response(request, ComponentResolveVerdict::NOT_SUPPORTED,
            "USER_NOT_SUPPORTED");
    }
    if (!request.kindWasRecognized) {
        return Response(request,
            ComponentResolveVerdict::INVALID_COMPONENT_KIND,
            "INVALID_COMPONENT_KIND");
    }
    if ((request.flags & ~SUPPORTED_FLAGS) != 0) {
        return Response(request, ComponentResolveVerdict::NOT_SUPPORTED,
            "FLAGS_NOT_SUPPORTED");
    }

    ComponentCatalogV1 catalog;
    std::string indexDigest;
    std::string error;
    if (!catalogProvider_->Read(&catalog, &indexDigest, &error) ||
        catalog.schemaVersion != 1 || catalog.catalogRevision == 0 ||
        indexDigest.empty()) {
        return Response(request, ComponentResolveVerdict::PACKAGE_NOT_READY,
            "COMPONENT_INDEX_UNAVAILABLE");
    }
    if (request.expectedCatalogRevision.has_value() &&
        *request.expectedCatalogRevision != catalog.catalogRevision) {
        return Response(request, ComponentResolveVerdict::PACKAGE_NOT_READY,
            "CATALOG_REVISION_STALE", catalog.catalogRevision, indexDigest);
    }
    if (request.expectedIndexDigest.has_value() &&
        *request.expectedIndexDigest != indexDigest) {
        return Response(request, ComponentResolveVerdict::PACKAGE_NOT_READY,
            "COMPONENT_INDEX_DIGEST_MISMATCH", catalog.catalogRevision,
            indexDigest);
    }
    if (faultInjector_->InterruptAfter(ResolvePhase::SNAPSHOT_FROZEN)) {
        return Response(request, ComponentResolveVerdict::PACKAGE_NOT_READY,
            "RESOLVE_INTERRUPTED_RETRY", catalog.catalogRevision, indexDigest);
    }

    ComponentResolveResponseV1 response = Response(request,
        ComponentResolveVerdict::READY, "READY", catalog.catalogRevision,
        indexDigest);
    const std::string targetPackage = TargetPackage(request);
    uint64_t ordinal = 0;
    bool sawTargetPackage = false;
    for (const auto& package : catalog.packages) {
        if (package.userId != request.userId ||
            (!targetPackage.empty() &&
                package.packageName != targetPackage)) {
            continue;
        }
        sawTargetPackage = true;
        if (!CallerCanSee(request, package.packageName)) {
            ++ordinal;
            continue;
        }
        if (!IsPackageName(package.packageName)) {
            return Response(request,
                ComponentResolveVerdict::DATA_INCONSISTENT,
                "COMPONENT_INDEX_CORRUPT", catalog.catalogRevision,
                indexDigest);
        }
        PackageGuardV1 guard;
        if (!guardReader_->Read(
                request.userId, package.packageName, &guard, &error)) {
            return Response(request,
                ComponentResolveVerdict::PACKAGE_NOT_READY,
                "PACKAGE_GUARD_UNAVAILABLE", catalog.catalogRevision,
                indexDigest);
        }
        ComponentResolveVerdict guardVerdict =
            ComponentResolveVerdict::PACKAGE_NOT_READY;
        const char* guardReason = "PACKAGE_NOT_READY";
        if (!SameGenerationReady(
                package, guard, &guardVerdict, &guardReason)) {
            return GuardResponse(request, guardVerdict, guardReason,
                catalog.catalogRevision, indexDigest,
                package.packageName, guard);
        }
        if (guard.catalogRevision != catalog.catalogRevision) {
            return GuardResponse(request,
                ComponentResolveVerdict::PACKAGE_NOT_READY,
                "CATALOG_REVISION_JOIN_MISMATCH",
                catalog.catalogRevision, indexDigest,
                package.packageName, guard);
        }
        if (request.expectedGeneration.has_value() &&
            *request.expectedGeneration != package.generation) {
            return GuardResponse(request,
                ComponentResolveVerdict::PACKAGE_NOT_READY,
                "EXPECTED_GENERATION_MISMATCH", catalog.catalogRevision,
                indexDigest, package.packageName, guard);
        }
        if (request.expectedCanonicalDigest.has_value() &&
            *request.expectedCanonicalDigest != package.canonicalDigest) {
            return GuardResponse(request,
                ComponentResolveVerdict::PACKAGE_NOT_READY,
                "EXPECTED_CANONICAL_DIGEST_MISMATCH",
                catalog.catalogRevision, indexDigest,
                package.packageName, guard);
        }
        response.guardJoin.push_back(
            GuardEvidence(package.packageName, guard));

        for (const auto& component : package.components) {
            const uint64_t componentOrdinal = ordinal++;
            auto trace = [&](const char* decision, bool disclose) {
                response.trace.push_back({componentOrdinal,
                    disclose ? package.packageName : "",
                    disclose ? component.name : "", decision});
            };
            if (component.kind != request.kind) continue;
            if (!component.enabled &&
                (request.flags & MATCH_DISABLED_COMPONENTS) == 0) {
                trace("FILTERED_DISABLED", true);
                continue;
            }
            if ((request.flags & MATCH_SYSTEM_ONLY) != 0 &&
                !component.system) {
                trace("FILTERED_NOT_SYSTEM", true);
                continue;
            }
            const bool samePackage =
                request.caller.callerPackageName == package.packageName;
            if (!component.exported && !samePackage) {
                trace("FILTERED_NOT_EXPORTED", false);
                continue;
            }
            if (!CallerHasPermission(
                    request, component.requiredPermission)) {
                trace("FILTERED_PERMISSION", false);
                continue;
            }
            const bool explicitIntent =
                !request.intent.explicitPackage.empty();
            if (explicitIntent) {
                if (component.name != request.intent.explicitClass) continue;
                ResolveCandidateV1 candidate;
                candidate.packageName = package.packageName;
                candidate.componentName = component.name;
                candidate.kind = component.kind;
                candidate.exported = component.exported;
                candidate.requiredPermission = component.requiredPermission;
                candidate.preferredOrder = component.preferredOrder;
                candidate.system = component.system;
                candidate.generation = package.generation;
                candidate.match = MATCH_EMPTY;
                candidate.stableOrdinal = componentOrdinal;
                response.results.push_back(std::move(candidate));
                trace("ACCEPTED_EXPLICIT", true);
                continue;
            }
            bool matched = false;
            for (const auto& filter : component.filters) {
                if (filter.hasUnsupportedPattern) {
                    return Response(request,
                        ComponentResolveVerdict::NOT_SUPPORTED_FILTER,
                        "NOT_SUPPORTED_FILTER", catalog.catalogRevision,
                        indexDigest);
                }
                int32_t match = 0;
                if (!FilterMatches(filter, request, &match)) continue;
                ResolveCandidateV1 candidate;
                candidate.packageName = package.packageName;
                candidate.componentName = component.name;
                candidate.kind = component.kind;
                candidate.exported = component.exported;
                candidate.requiredPermission = component.requiredPermission;
                candidate.priority = filter.priority;
                candidate.preferredOrder = component.preferredOrder;
                candidate.isDefault = filter.isDefault;
                candidate.match = match;
                candidate.system = component.system;
                candidate.generation = package.generation;
                candidate.stableOrdinal = componentOrdinal;
                response.results.push_back(std::move(candidate));
                matched = true;
                break;
            }
            trace(matched ? "ACCEPTED_FILTER" : "FILTERED_NO_MATCH", true);
        }
    }
    if (!targetPackage.empty() && !sawTargetPackage) {
        PackageGuardV1 guard;
        if (!guardReader_->Read(
                request.userId, targetPackage, &guard, &error)) {
            return Response(request,
                ComponentResolveVerdict::PACKAGE_NOT_READY,
                "PACKAGE_GUARD_UNAVAILABLE",
                catalog.catalogRevision, indexDigest);
        }
        if (guard.removing) {
            return GuardResponse(request,
                ComponentResolveVerdict::PACKAGE_REMOVING,
                "PACKAGE_REMOVING", catalog.catalogRevision, indexDigest,
                targetPackage, guard);
        }
        if (guard.hasCanonical ||
            guard.catalogRevision != catalog.catalogRevision) {
            return GuardResponse(request,
                ComponentResolveVerdict::PACKAGE_NOT_READY,
                "COMPONENT_INDEX_STALE",
                catalog.catalogRevision, indexDigest, targetPackage, guard);
        }
        response.trace.push_back({ordinal, "", "", "FILTERED_ABSENT"});
    }
    if (faultInjector_->InterruptAfter(ResolvePhase::CANDIDATES_FILTERED)) {
        return Response(request, ComponentResolveVerdict::PACKAGE_NOT_READY,
            "RESOLVE_INTERRUPTED_RETRY", catalog.catalogRevision, indexDigest);
    }

    std::stable_sort(response.results.begin(), response.results.end(),
        [](const ResolveCandidateV1& left,
           const ResolveCandidateV1& right) {
            if (left.priority != right.priority)
                return left.priority > right.priority;
            if (left.preferredOrder != right.preferredOrder)
                return left.preferredOrder > right.preferredOrder;
            if (left.isDefault != right.isDefault)
                return left.isDefault > right.isDefault;
            if (left.match != right.match) return left.match > right.match;
            if (left.system != right.system) return left.system > right.system;
            if (left.packageName != right.packageName)
                return left.packageName < right.packageName;
            return false;
        });
    if (faultInjector_->InterruptAfter(ResolvePhase::RESPONSE_SERIALIZED)) {
        return Response(request, ComponentResolveVerdict::PACKAGE_NOT_READY,
            "RESOLVE_INTERRUPTED_RETRY", catalog.catalogRevision, indexDigest);
    }
    return response;
}

bool SerializeComponentCatalogV1(const ComponentCatalogV1& catalog,
    std::vector<uint8_t>* bytes, std::string* error)
{
    if (bytes == nullptr || catalog.schemaVersion != 1 ||
        catalog.catalogRevision == 0 ||
        catalog.packages.size() > MAX_PACKAGES) {
        if (error != nullptr) *error = "invalid component catalog";
        return false;
    }
    bytes->clear();
    static constexpr uint8_t MAGIC[] =
        {'F', 'N', 'C', 'I', 'D', 'X', '1', '\0'};
    bytes->insert(bytes->end(), std::begin(MAGIC), std::end(MAGIC));
    Writer writer(bytes);
    writer.U32(catalog.schemaVersion);
    writer.U64(catalog.catalogRevision);
    writer.U32(static_cast<uint32_t>(catalog.packages.size()));
    std::set<std::pair<uint32_t, std::string>> packageKeys;
    for (const auto& package : catalog.packages) {
        if (!IsPackageName(package.packageName) ||
            package.generation == 0 || package.canonicalDigest.empty() ||
            package.components.size() > MAX_COMPONENTS_PER_PACKAGE ||
            !packageKeys.emplace(package.userId, package.packageName).second ||
            !writer.String(package.packageName)) {
            if (error != nullptr) *error = "invalid package index";
            bytes->clear();
            return false;
        }
        writer.U32(package.userId);
        writer.U64(package.generation);
        if (!writer.String(package.canonicalDigest)) return false;
        writer.U8(package.removing ? 1 : 0);
        writer.U32(static_cast<uint32_t>(package.components.size()));
        for (const auto& component : package.components) {
            if (!IsBoundedToken(component.name) ||
                component.filters.size() > MAX_FILTERS_PER_COMPONENT) {
                if (error != nullptr) *error = "invalid component";
                bytes->clear();
                return false;
            }
            writer.U8(static_cast<uint8_t>(component.kind));
            if (!writer.String(component.name)) return false;
            writer.U8(component.enabled ? 1 : 0);
            writer.U8(component.exported ? 1 : 0);
            if (!writer.String(component.requiredPermission)) return false;
            writer.I32(component.preferredOrder);
            writer.U8(component.system ? 1 : 0);
            writer.U32(static_cast<uint32_t>(component.filters.size()));
            for (const auto& filter : component.filters) {
                if (!writer.Strings(filter.actions) ||
                    !writer.Strings(filter.categories) ||
                    !writer.Strings(filter.mimeTypes) ||
                    !writer.Strings(filter.schemes) ||
                    !writer.Strings(filter.hosts) ||
                    !writer.Ints(filter.ports) ||
                    !writer.Strings(filter.pathPrefixes)) {
                    if (error != nullptr) *error = "invalid filter members";
                    bytes->clear();
                    return false;
                }
                writer.U8(filter.isDefault ? 1 : 0);
                writer.U8(filter.hasUnsupportedPattern ? 1 : 0);
                writer.I32(filter.priority);
            }
        }
    }
    if (error != nullptr) error->clear();
    return true;
}

bool ParseComponentCatalogV1(const std::vector<uint8_t>& bytes,
    ComponentCatalogV1* catalog, std::string* error)
{
    if (catalog == nullptr || bytes.size() < 24) {
        if (error != nullptr) *error = "component index is truncated";
        return false;
    }
    static constexpr uint8_t MAGIC[] =
        {'F', 'N', 'C', 'I', 'D', 'X', '1', '\0'};
    if (!std::equal(std::begin(MAGIC), std::end(MAGIC), bytes.begin())) {
        if (error != nullptr) *error = "component index magic mismatch";
        return false;
    }
    const std::vector<uint8_t> payload(bytes.begin() + 8, bytes.end());
    Reader reader(payload);
    ComponentCatalogV1 parsed;
    uint32_t packageCount = 0;
    if (!reader.U32(&parsed.schemaVersion) ||
        !reader.U64(&parsed.catalogRevision) ||
        !reader.U32(&packageCount) || parsed.schemaVersion != 1 ||
        parsed.catalogRevision == 0 || packageCount > MAX_PACKAGES) {
        if (error != nullptr) *error = "component index header invalid";
        return false;
    }
    parsed.packages.reserve(packageCount);
    std::set<std::pair<uint32_t, std::string>> packageKeys;
    for (uint32_t packageIndex = 0; packageIndex < packageCount;
         ++packageIndex) {
        PackageComponentIndexV1 package;
        uint8_t removing = 0;
        uint32_t componentCount = 0;
        if (!reader.String(&package.packageName) ||
            !reader.U32(&package.userId) ||
            !reader.U64(&package.generation) ||
            !reader.String(&package.canonicalDigest) ||
            !reader.U8(&removing) || removing > 1 ||
            !reader.U32(&componentCount) ||
            !IsPackageName(package.packageName) ||
            package.generation == 0 || package.canonicalDigest.empty() ||
            componentCount > MAX_COMPONENTS_PER_PACKAGE ||
            !packageKeys.emplace(
                package.userId, package.packageName).second) {
            if (error != nullptr) *error = "package index invalid";
            return false;
        }
        package.removing = removing == 1;
        package.components.reserve(componentCount);
        for (uint32_t componentIndex = 0;
             componentIndex < componentCount; ++componentIndex) {
            ComponentFactV1 component;
            uint8_t kind = 0;
            uint8_t enabled = 0;
            uint8_t exported = 0;
            uint8_t system = 0;
            uint32_t filterCount = 0;
            if (!reader.U8(&kind) || kind < 1 || kind > 4 ||
                !reader.String(&component.name) ||
                !reader.U8(&enabled) || enabled > 1 ||
                !reader.U8(&exported) || exported > 1 ||
                !reader.String(&component.requiredPermission) ||
                !reader.I32(&component.preferredOrder) ||
                !reader.U8(&system) || system > 1 ||
                !reader.U32(&filterCount) ||
                !IsBoundedToken(component.name) ||
                filterCount > MAX_FILTERS_PER_COMPONENT) {
                if (error != nullptr) *error = "component record invalid";
                return false;
            }
            component.kind = static_cast<ComponentKind>(kind);
            component.enabled = enabled == 1;
            component.exported = exported == 1;
            component.system = system == 1;
            component.filters.reserve(filterCount);
            for (uint32_t filterIndex = 0; filterIndex < filterCount;
                 ++filterIndex) {
                IntentFilterDataV1 filter;
                uint8_t isDefault = 0;
                uint8_t unsupported = 0;
                if (!reader.Strings(&filter.actions) ||
                    !reader.Strings(&filter.categories) ||
                    !reader.Strings(&filter.mimeTypes) ||
                    !reader.Strings(&filter.schemes) ||
                    !reader.Strings(&filter.hosts) ||
                    !reader.Ints(&filter.ports) ||
                    !reader.Strings(&filter.pathPrefixes) ||
                    !reader.U8(&isDefault) || isDefault > 1 ||
                    !reader.U8(&unsupported) || unsupported > 1 ||
                    !reader.I32(&filter.priority)) {
                    if (error != nullptr) *error = "filter record invalid";
                    return false;
                }
                filter.isDefault = isDefault == 1;
                filter.hasUnsupportedPattern = unsupported == 1;
                component.filters.push_back(std::move(filter));
            }
            package.components.push_back(std::move(component));
        }
        parsed.packages.push_back(std::move(package));
    }
    if (!reader.Done()) {
        if (error != nullptr) *error = "component index has trailing bytes";
        return false;
    }
    *catalog = std::move(parsed);
    if (error != nullptr) error->clear();
    return true;
}

std::string ComponentCatalogDigestV1(const std::vector<uint8_t>& bytes)
{
    uint8_t digest[32];
    sha256(bytes.data(), bytes.size(), digest);
    static constexpr char HEX[] = "0123456789abcdef";
    std::string result(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        result[index * 2] = HEX[digest[index] >> 4];
        result[index * 2 + 1] = HEX[digest[index] & 15];
    }
    return result;
}

std::string ComponentResolveResponseJsonV1(
    const ComponentResolveResponseV1& response)
{
    std::ostringstream out;
    out << "{\"schemaVersion\":1,\"actionId\":\"Fn01.A06\",\"requestId\":\""
        << JsonEscape(response.requestId) << "\",\"verdict\":\""
        << ComponentResolveVerdictNameV1(response.verdict)
        << "\",\"reason\":\"" << JsonEscape(response.reason)
        << "\",\"catalogRevision\":" << response.catalogRevision
        << ",\"indexDigest\":\"" << JsonEscape(response.indexDigest)
        << "\",\"results\":[";
    for (size_t index = 0; index < response.results.size(); ++index) {
        if (index != 0) out << ',';
        const auto& candidate = response.results[index];
        out << "{\"packageName\":\"" << JsonEscape(candidate.packageName)
            << "\",\"componentName\":\""
            << JsonEscape(candidate.componentName)
            << "\",\"kind\":\"" << ComponentKindNameV1(candidate.kind)
            << "\",\"exported\":"
            << (candidate.exported ? "true" : "false")
            << ",\"requiredPermission\":\""
            << JsonEscape(candidate.requiredPermission)
            << "\",\"priority\":" << candidate.priority
            << ",\"preferredOrder\":" << candidate.preferredOrder
            << ",\"isDefault\":"
            << (candidate.isDefault ? "true" : "false")
            << ",\"match\":" << candidate.match
            << ",\"system\":" << (candidate.system ? "true" : "false")
            << ",\"generation\":" << candidate.generation
            << ",\"stableOrdinal\":" << candidate.stableOrdinal << '}';
    }
    out << "],\"guardJoin\":[";
    for (size_t index = 0; index < response.guardJoin.size(); ++index) {
        if (index != 0) out << ',';
        const auto& guard = response.guardJoin[index];
        out << "{\"packageName\":\"" << JsonEscape(guard.packageName)
            << "\",\"generation\":" << guard.generation
            << ",\"canonicalState\":\""
            << JsonEscape(guard.canonicalState)
            << "\",\"canonicalDigest\":\""
            << JsonEscape(guard.canonicalDigest)
            << "\",\"projectionState\":\""
            << JsonEscape(guard.projectionState)
            << "\",\"projectionDigest\":\""
            << JsonEscape(guard.projectionDigest)
            << "\",\"tokenState\":\""
            << JsonEscape(guard.tokenState)
            << "\",\"tokenDigest\":\""
            << JsonEscape(guard.tokenDigest) << "\"}";
    }
    out << "],\"trace\":[";
    for (size_t index = 0; index < response.trace.size(); ++index) {
        if (index != 0) out << ',';
        const auto& event = response.trace[index];
        out << "{\"ordinal\":" << event.ordinal << ",\"packageName\":\""
            << JsonEscape(event.packageName) << "\",\"componentName\":\""
            << JsonEscape(event.componentName) << "\",\"decision\":\""
            << JsonEscape(event.decision) << "\"}";
    }
    out << "]}";
    return out.str();
}

bool ParseComponentKindV1(const std::string& value, ComponentKind* kind)
{
    if (kind == nullptr) return false;
    if (value == "ACTIVITY") *kind = ComponentKind::ACTIVITY;
    else if (value == "SERVICE") *kind = ComponentKind::SERVICE;
    else if (value == "RECEIVER") *kind = ComponentKind::RECEIVER;
    else if (value == "PROVIDER") *kind = ComponentKind::PROVIDER;
    else return false;
    return true;
}

const char* ComponentKindNameV1(ComponentKind kind)
{
    switch (kind) {
        case ComponentKind::ACTIVITY: return "ACTIVITY";
        case ComponentKind::SERVICE: return "SERVICE";
        case ComponentKind::RECEIVER: return "RECEIVER";
        case ComponentKind::PROVIDER: return "PROVIDER";
    }
    return "INVALID";
}

const char* ComponentResolveVerdictNameV1(
    ComponentResolveVerdict verdict)
{
    switch (verdict) {
        case ComponentResolveVerdict::READY: return "READY";
        case ComponentResolveVerdict::INVALID_REQUEST:
            return "INVALID_REQUEST";
        case ComponentResolveVerdict::NOT_SUPPORTED:
            return "NOT_SUPPORTED";
        case ComponentResolveVerdict::INVALID_COMPONENT_KIND:
            return "INVALID_COMPONENT_KIND";
        case ComponentResolveVerdict::NOT_SUPPORTED_FILTER:
            return "NOT_SUPPORTED_FILTER";
        case ComponentResolveVerdict::PACKAGE_REMOVING:
            return "PACKAGE_REMOVING";
        case ComponentResolveVerdict::PACKAGE_NOT_READY:
            return "PACKAGE_NOT_READY";
        case ComponentResolveVerdict::DATA_INCONSISTENT:
            return "DATA_INCONSISTENT";
    }
    return "DATA_INCONSISTENT";
}

}  // namespace oh_adapter::component_resolver
