#include "launcher_presentation_v1.h"

#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

using namespace oh_adapter::launcher_presentation;

namespace {

std::string JsonEscape(const std::string& value)
{
    std::string result;
    for (const unsigned char character : value) {
        switch (character) {
            case '"': result += "\\\""; break;
            case '\\': result += "\\\\"; break;
            case '\n': result += "\\n"; break;
            case '\r': result += "\\r"; break;
            case '\t': result += "\\t"; break;
            default: result.push_back(static_cast<char>(character));
        }
    }
    return result;
}

std::string Digest(const std::string& value)
{
    return LauncherPresentationServiceV1::ComputeSha256(value);
}

ConfigurationSelectorV1 Configuration(
    const std::string& locale, uint32_t densityDpi, bool nightMode)
{
    ConfigurationSelectorV1 configuration;
    configuration.localeTag = locale;
    configuration.densityDpi = densityDpi;
    configuration.nightMode = nightMode;
    configuration.configurationHash = Digest(
        "configuration|" + locale + "|" + std::to_string(densityDpi) +
        "|" + (nightMode ? "night" : "day"));
    return configuration;
}

LauncherAssetV1 Asset(const std::string& componentName,
    const ConfigurationSelectorV1& configuration,
    const std::string& label, const std::string& seed)
{
    LauncherAssetV1 asset;
    asset.status = LauncherAssetStatus::RESOLVED;
    asset.componentName = componentName;
    asset.configuration = configuration;
    asset.label = label;
    asset.iconBytes.assign(seed.begin(), seed.end());
    asset.iconContentType = "image/png";
    asset.sourceArtifactSha256 = Digest("apk|" + seed);
    asset.componentResourceRefsDigest =
        Digest("refs|" + componentName + "|" + seed);
    asset.renderedAssetHash =
        LauncherPresentationServiceV1::ComputeRenderedAssetHash(asset);
    return asset;
}

LauncherPresentationSnapshotV1 Snapshot(
    const std::string& packageName, uint64_t generation,
    const std::string& primaryComponent,
    const std::string& secondaryComponent,
    const ConfigurationSelectorV1& primaryConfiguration,
    const ConfigurationSelectorV1& secondaryConfiguration)
{
    LauncherPresentationSnapshotV1 snapshot;
    snapshot.packageName = packageName;
    snapshot.userId = 0;
    snapshot.canonicalReadbackBytes =
        "AndroidPackageGenerationV1|" + packageName + "|" +
        std::to_string(generation);
    snapshot.projectionReadbackBytes =
        "HostProjectionPayloadV1|" + packageName + "|" +
        std::to_string(generation);
    snapshot.resourcePayloadReadbackBytes =
        "ResourceProjectionPayloadV1|" + packageName + "|" +
        std::to_string(generation);

    snapshot.guard.canonicalState = CanonicalState::ACTIVE;
    snapshot.guard.canonicalGeneration = generation;
    snapshot.guard.canonicalDigest = Digest(snapshot.canonicalReadbackBytes);
    snapshot.guard.projectionState = HostProjectionState::ACTIVE;
    snapshot.guard.projectionGeneration = generation;
    snapshot.guard.projectionCanonicalDigest =
        snapshot.guard.canonicalDigest;
    snapshot.guard.projectionDigest =
        Digest(snapshot.projectionReadbackBytes);
    snapshot.guard.tokenState = PublicationTokenState::EXTERNAL_READY;
    snapshot.guard.tokenGeneration = generation;
    snapshot.guard.tokenCanonicalDigest = snapshot.guard.canonicalDigest;
    snapshot.guard.tokenProjectionDigest = snapshot.guard.projectionDigest;
    snapshot.guard.resourceRuntimeState = ResourceRuntimeState::READY;
    snapshot.guard.resourceGeneration = generation;
    snapshot.guard.resourceCanonicalDigest = snapshot.guard.canonicalDigest;
    snapshot.guard.resourcePayloadDigest =
        Digest(snapshot.resourcePayloadReadbackBytes);
    snapshot.assets.push_back(Asset(primaryComponent, primaryConfiguration,
        "label-" + packageName + "-" + primaryConfiguration.localeTag,
        "icon|" + packageName + "|primary"));
    snapshot.assets.push_back(Asset(primaryComponent, secondaryConfiguration,
        "label-" + packageName + "-" + secondaryConfiguration.localeTag,
        "icon|" + packageName + "|primary-secondary-config"));
    snapshot.assets.push_back(Asset(secondaryComponent, primaryConfiguration,
        "component-label-" + packageName,
        "icon|" + packageName + "|secondary-component"));
    return snapshot;
}

std::string CacheKeyBytes(const CacheInvalidationRequestV1& request)
{
    auto hex = [](const std::string& value) {
        static constexpr char kHex[] = "0123456789abcdef";
        std::string result(value.size() * 2, '0');
        for (size_t index = 0; index < value.size(); ++index) {
            const auto byte = static_cast<unsigned char>(value[index]);
            result[index * 2] = kHex[byte >> 4];
            result[index * 2 + 1] = kHex[byte & 0x0f];
        }
        return result;
    };
    std::ostringstream output;
    output << "LauncherPresentationCacheKeyV1\n"
           << "packageNameHex=" << hex(request.packageName)
           << "\nuserId=" << request.userId
           << "\ngeneration=" << request.generation
           << "\ncanonicalDigest=" << request.canonicalDigest
           << "\nprojectionDigest=" << request.projectionDigest
           << "\nresourcePayloadDigest=" << request.resourcePayloadDigest
           << "\n";
    return output.str();
}

class FakeSnapshotProvider final
    : public LauncherPresentationSnapshotProviderV1 {
public:
    explicit FakeSnapshotProvider(LauncherPresentationSnapshotV1 snapshot)
        : snapshot_(std::move(snapshot))
    {
    }

    SnapshotReadResultV1 ReadSnapshot(
        const LauncherPresentationQueryV1&) override
    {
        ++readCount;
        SnapshotReadResultV1 result;
        result.verdict = readVerdict;
        result.reason = readReason;
        result.snapshot = snapshot_;
        return result;
    }

    CacheInvalidationReceiptV1 InvalidateRebuildableCache(
        const CacheInvalidationRequestV1& request) override
    {
        ++invalidationCount;
        lastInvalidation = request;
        CacheInvalidationReceiptV1 receipt;
        receipt.invalidated = invalidationSucceeds;
        receipt.cacheKeyDigest = invalidationSucceeds
            ? Digest(CacheKeyBytes(request))
            : std::string();
        receipt.reason = invalidationSucceeds
            ? "rebuildable-cache-cleared"
            : "injected-cache-clear-failure";
        return receipt;
    }

    LauncherPresentationSnapshotV1& MutableSnapshot()
    {
        return snapshot_;
    }

    const LauncherPresentationSnapshotV1& CurrentSnapshot() const
    {
        return snapshot_;
    }

    SnapshotReadVerdict readVerdict = SnapshotReadVerdict::READY;
    std::string readReason;
    bool invalidationSucceeds = true;
    uint64_t readCount = 0;
    uint64_t invalidationCount = 0;
    uint64_t canonicalMutationCount = 0;
    CacheInvalidationRequestV1 lastInvalidation;

private:
    LauncherPresentationSnapshotV1 snapshot_;
};

class FaultOnce final : public LauncherPresentationFaultInjectorV1 {
public:
    explicit FaultOnce(QueryPhase phase) : phase_(phase) {}

    bool InterruptAt(QueryPhase phase) override
    {
        if (!used_ && phase == phase_) {
            used_ = true;
            return true;
        }
        return false;
    }

private:
    QueryPhase phase_;
    bool used_ = false;
};

LauncherPresentationQueryV1 QueryFor(
    const LauncherPresentationSnapshotV1& snapshot,
    const std::string& requestId, const std::string& componentName,
    const ConfigurationSelectorV1& configuration,
    const std::string& callerScopeDigest)
{
    LauncherPresentationQueryV1 query;
    query.requestId = requestId;
    query.callerScopeDigest = callerScopeDigest;
    query.packageName = snapshot.packageName;
    query.componentName = componentName;
    query.expectedGeneration = snapshot.guard.canonicalGeneration;
    query.expectedCanonicalDigest = snapshot.guard.canonicalDigest;
    query.configuration = configuration;
    return query;
}

LauncherPresentationPolicyV1 Policy(const std::string& callerScopeDigest)
{
    LauncherPresentationPolicyV1 policy;
    policy.policyVersion = "launcher-presentation-policy-v1";
    policy.expectedCallerScopeDigest = callerScopeDigest;
    return policy;
}

class TestContext final {
public:
    explicit TestContext(const std::string& resultsPath)
        : results_(resultsPath, std::ios::binary | std::ios::trunc)
    {
        if (!results_) {
            std::cerr << "cannot open results path\n";
            std::exit(2);
        }
    }

    void Check(bool condition, const std::string& caseId,
        const std::string& category, const std::string& detail,
        const LauncherPresentationResponseV1& response)
    {
        if (condition) {
            ++passed;
        } else {
            ++failed;
        }
        std::string serialized =
            LauncherPresentationServiceV1::SerializeResponse(response);
        if (!serialized.empty() && serialized.back() == '\n') {
            serialized.pop_back();
        }
        results_ << "{\"caseId\":\"" << JsonEscape(caseId)
                 << "\",\"category\":\"" << JsonEscape(category)
                 << "\",\"passed\":" << (condition ? "true" : "false")
                 << ",\"detail\":\"" << JsonEscape(detail)
                 << "\",\"response\":" << serialized << "}\n";
        if (!condition) {
            std::cerr << "FAIL " << caseId << ": " << detail << "\n";
        }
    }

    uint64_t passed = 0;
    uint64_t failed = 0;

private:
    std::ofstream results_;
};

void RunPositiveCases(TestContext* test,
    const LauncherPresentationSnapshotV1& alphaSnapshot,
    const LauncherPresentationSnapshotV1& betaSnapshot,
    const std::string& primaryComponent,
    const std::string& secondaryComponent,
    const ConfigurationSelectorV1& primaryConfiguration,
    const ConfigurationSelectorV1& secondaryConfiguration,
    const std::string& caller)
{
    FakeSnapshotProvider alpha(alphaSnapshot);
    LauncherPresentationServiceV1 alphaService(Policy(caller), &alpha);
    const auto alphaQuery = QueryFor(alpha.CurrentSnapshot(),
        "p01-alpha", primaryComponent, primaryConfiguration, caller);
    const auto alphaResponse = alphaService.Query(alphaQuery, nullptr);
    test->Check(
        alphaResponse.verdict == LauncherPresentationVerdict::READY &&
            alphaResponse.label.find(alphaSnapshot.packageName) !=
                std::string::npos &&
            alphaResponse.generation ==
                alphaSnapshot.guard.canonicalGeneration &&
            alphaResponse.canonicalDigest ==
                alphaSnapshot.guard.canonicalDigest &&
            alphaResponse.projectionDigest ==
                alphaSnapshot.guard.projectionDigest &&
            alphaResponse.resourcePayloadDigest ==
                alphaSnapshot.guard.resourcePayloadDigest &&
            alphaResponse.renderedAssetHash ==
                alphaSnapshot.assets[0].renderedAssetHash,
        "P01_ALPHA_GENERATION_BOUND", "P",
        "alpha 返回同代 guard join、provenance 与 rendered hash",
        alphaResponse);

    FakeSnapshotProvider beta(betaSnapshot);
    LauncherPresentationServiceV1 betaService(Policy(caller), &beta);
    const auto betaQuery = QueryFor(beta.CurrentSnapshot(),
        "p01-beta", primaryComponent, primaryConfiguration, caller);
    const auto betaResponse = betaService.Query(betaQuery, nullptr);
    test->Check(
        betaResponse.verdict == LauncherPresentationVerdict::READY &&
            betaResponse.label != alphaResponse.label &&
            betaResponse.renderedAssetHash !=
                alphaResponse.renderedAssetHash,
        "P01_MULTI_APK_DISTINCT", "P",
        "外部输入的第二 APK 走同一代码路径且不串资源", betaResponse);

    auto componentQuery = alphaQuery;
    componentQuery.requestId = "p01-component-override";
    componentQuery.componentName = secondaryComponent;
    const auto componentResponse =
        alphaService.Query(componentQuery, nullptr);
    test->Check(
        componentResponse.verdict == LauncherPresentationVerdict::READY &&
            componentResponse.label ==
                alphaSnapshot.assets[2].label &&
            componentResponse.renderedAssetHash ==
                alphaSnapshot.assets[2].renderedAssetHash,
        "P01_COMPONENT_OVERRIDE", "P",
        "launcher component 自有 label/icon 覆盖按 component 精确选择",
        componentResponse);

    auto localeQuery = alphaQuery;
    localeQuery.requestId = "p01-alternate-configuration";
    localeQuery.configuration = secondaryConfiguration;
    const auto localeResponse = alphaService.Query(localeQuery, nullptr);
    test->Check(
        localeResponse.verdict == LauncherPresentationVerdict::READY &&
            localeResponse.label == alphaSnapshot.assets[1].label &&
            localeResponse.configuration.localeTag ==
                secondaryConfiguration.localeTag,
        "P01_CONFIGURATION_SELECTOR", "P",
        "locale/density/night/config hash 完整参与精确选择",
        localeResponse);

    const uint64_t readsBeforeReplay = alpha.readCount;
    const auto replayResponse = alphaService.Query(alphaQuery, nullptr);
    test->Check(
        replayResponse.verdict == LauncherPresentationVerdict::READY &&
            replayResponse.renderedAssetHash ==
                alphaResponse.renderedAssetHash &&
            alpha.invalidationCount == 0 &&
            alpha.canonicalMutationCount == 0 &&
            alpha.readCount == readsBeforeReplay + 1,
        "P02_IDEMPOTENT_REPLAY", "P",
        "重放重新执行 readback，不创建权威状态或缓存写者",
        replayResponse);

    FakeSnapshotProvider nextGeneration(Snapshot(alphaSnapshot.packageName,
        alphaSnapshot.guard.canonicalGeneration + 1, primaryComponent,
        secondaryComponent, primaryConfiguration, secondaryConfiguration));
    LauncherPresentationServiceV1 nextGenerationService(
        Policy(caller), &nextGeneration);
    const auto nextGenerationQuery = QueryFor(
        nextGeneration.CurrentSnapshot(), "p02-next-generation",
        primaryComponent, primaryConfiguration, caller);
    const auto nextGenerationResponse =
        nextGenerationService.Query(nextGenerationQuery, nullptr);
    test->Check(
        nextGenerationResponse.verdict ==
                LauncherPresentationVerdict::READY &&
            nextGenerationResponse.generation ==
                alphaSnapshot.guard.canonicalGeneration + 1 &&
            nextGenerationResponse.canonicalDigest !=
                alphaResponse.canonicalDigest,
        "P02_NEXT_GENERATION_SAME_CONTRACT", "P",
        "新 generation 仍使用同一 contract 且不继承旧代 digest",
        nextGenerationResponse);
}

void RunNegativeCases(TestContext* test,
    const LauncherPresentationSnapshotV1& baseSnapshot,
    const std::string& primaryComponent,
    const ConfigurationSelectorV1& primaryConfiguration,
    const std::string& alternateLocale,
    const std::string& caller)
{
    auto runGuardCase = [&](const std::string& caseId,
                            LauncherPresentationSnapshotV1 snapshot,
                            LauncherPresentationVerdict expected,
                            const std::string& detail) {
        FakeSnapshotProvider provider(std::move(snapshot));
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        const auto query = QueryFor(provider.CurrentSnapshot(), caseId,
            primaryComponent, primaryConfiguration, caller);
        const auto response = service.Query(query, nullptr);
        test->Check(response.verdict == expected &&
                provider.canonicalMutationCount == 0,
            caseId, "N", detail, response);
    };

    auto canonicalPrepared = baseSnapshot;
    canonicalPrepared.guard.canonicalState = CanonicalState::PREPARED;
    runGuardCase("N01_CANONICAL_PREPARED", canonicalPrepared,
        LauncherPresentationVerdict::PACKAGE_NOT_READY,
        "PREPARED canonical 不可消费");

    auto partialPrepared = baseSnapshot;
    partialPrepared.guard.canonicalState = CanonicalState::PREPARED;
    partialPrepared.guard.projectionState = HostProjectionState::NONE;
    partialPrepared.guard.projectionGeneration = 0;
    partialPrepared.guard.projectionCanonicalDigest.clear();
    partialPrepared.guard.projectionDigest.clear();
    partialPrepared.guard.tokenState = PublicationTokenState::NONE;
    partialPrepared.guard.tokenGeneration = 0;
    partialPrepared.guard.tokenCanonicalDigest.clear();
    partialPrepared.guard.tokenProjectionDigest.clear();
    partialPrepared.guard.resourceRuntimeState = ResourceRuntimeState::NONE;
    partialPrepared.guard.resourceGeneration = 0;
    partialPrepared.guard.resourceCanonicalDigest.clear();
    partialPrepared.guard.resourcePayloadDigest.clear();
    runGuardCase("N01_PARTIAL_PREPARED", partialPrepared,
        LauncherPresentationVerdict::PACKAGE_NOT_READY,
        "未组装完整 join 的 PREPARED 前态仍统一 PACKAGE_NOT_READY");

    auto projectionPrepared = baseSnapshot;
    projectionPrepared.guard.projectionState =
        HostProjectionState::PREPARED;
    runGuardCase("N01_PROJECTION_PREPARED", projectionPrepared,
        LauncherPresentationVerdict::PACKAGE_NOT_READY,
        "PREPARED host projection 不可消费");

    auto tokenPrepared = baseSnapshot;
    tokenPrepared.guard.tokenState = PublicationTokenState::PREPARED;
    runGuardCase("N01_TOKEN_NOT_EXTERNAL_READY", tokenPrepared,
        LauncherPresentationVerdict::PACKAGE_NOT_READY,
        "非 EXTERNAL_READY token 不可消费");

    auto resourcePrepared = baseSnapshot;
    resourcePrepared.guard.resourceRuntimeState =
        ResourceRuntimeState::PREPARED;
    runGuardCase("N01_RESOURCE_PREPARED", resourcePrepared,
        LauncherPresentationVerdict::PACKAGE_NOT_READY,
        "A08 PREPARED runtime 不可消费");

    auto removing = baseSnapshot;
    removing.guard.canonicalState = CanonicalState::REMOVING;
    runGuardCase("N01_REMOVING_TOMBSTONE", removing,
        LauncherPresentationVerdict::PACKAGE_REMOVING,
        "OPEN removal tombstone 优先返回 PACKAGE_REMOVING");

    {
        FakeSnapshotProvider provider(baseSnapshot);
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        auto query = QueryFor(provider.CurrentSnapshot(),
            "n01-component-missing",
            primaryComponent + ".Absent", primaryConfiguration, caller);
        const auto response = service.Query(query, nullptr);
        test->Check(
            response.verdict ==
                    LauncherPresentationVerdict::RESOURCE_NOT_FOUND &&
                response.iconBytes.empty() && response.label.empty(),
            "N01_COMPONENT_NOT_FOUND", "N",
            "无 launcher component 不静默返回 package 默认资源", response);
    }

    {
        auto missing = baseSnapshot;
        missing.assets[0].status = LauncherAssetStatus::MISSING;
        missing.assets[0].label.clear();
        missing.assets[0].iconBytes.clear();
        FakeSnapshotProvider provider(std::move(missing));
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        const auto query = QueryFor(provider.CurrentSnapshot(),
            "n01-resource-missing", primaryComponent,
            primaryConfiguration, caller);
        const auto response = service.Query(query, nullptr);
        test->Check(
            response.verdict ==
                    LauncherPresentationVerdict::RESOURCE_NOT_FOUND &&
                provider.invalidationCount == 0,
            "N01_RESOURCE_NOT_FOUND", "N",
            "typed MISSING 资源返回 RESOURCE_NOT_FOUND，不误判 corrupt",
            response);
    }

    {
        FakeSnapshotProvider provider(baseSnapshot);
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        const auto unsupported =
            Configuration(alternateLocale, 480, true);
        const auto query = QueryFor(provider.CurrentSnapshot(),
            "n01-config-degraded", primaryComponent, unsupported, caller);
        const auto response = service.Query(query, nullptr);
        test->Check(
            response.verdict ==
                    LauncherPresentationVerdict::PRESENTATION_DEGRADED &&
                response.label.empty() && response.iconBytes.empty(),
            "N01_CONFIGURATION_DEGRADED", "N",
            "不支持 configuration 返回 PRESENTATION_DEGRADED，不偷 host default",
            response);
    }

    {
        FakeSnapshotProvider provider(baseSnapshot);
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        auto query = QueryFor(provider.CurrentSnapshot(),
            "n02-caller", primaryComponent, primaryConfiguration,
            Digest("unauthorized-caller"));
        const auto response = service.Query(query, nullptr);
        test->Check(
            response.verdict ==
                    LauncherPresentationVerdict::CALLER_SCOPE_MISMATCH &&
                provider.readCount == 0 && response.label.empty() &&
                response.iconBytes.empty(),
            "N02_CALLER_SCOPE", "N",
            "caller guard 在读取 snapshot 前拒绝并保持零数据泄漏",
            response);
    }

    {
        FakeSnapshotProvider provider(baseSnapshot);
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        auto query = QueryFor(provider.CurrentSnapshot(),
            "n02-user", primaryComponent, primaryConfiguration, caller);
        query.userId = 10;
        const auto response = service.Query(query, nullptr);
        test->Check(
            response.verdict ==
                    LauncherPresentationVerdict::NOT_SUPPORTED_USER &&
                provider.readCount == 0,
            "N02_USER_SCOPE", "N",
            "secondary user typed not-supported 且不读取 snapshot", response);
    }

    {
        FakeSnapshotProvider provider(baseSnapshot);
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        auto query = QueryFor(provider.CurrentSnapshot(),
            "n02-generation", primaryComponent,
            primaryConfiguration, caller);
        ++query.expectedGeneration;
        const auto response = service.Query(query, nullptr);
        test->Check(
            response.verdict ==
                    LauncherPresentationVerdict::GENERATION_MISMATCH &&
                response.label.empty() && response.iconBytes.empty(),
            "N02_GENERATION_MISMATCH", "N",
            "generation 错配不得返回跨代 presentation", response);
    }

    auto projectionGenerationMismatch = baseSnapshot;
    ++projectionGenerationMismatch.guard.projectionGeneration;
    runGuardCase("N02_PROJECTION_GENERATION_MISMATCH",
        projectionGenerationMismatch,
        LauncherPresentationVerdict::GENERATION_MISMATCH,
        "projection generation 不得与 canonical 拼接");

    auto tokenDigestMismatch = baseSnapshot;
    tokenDigestMismatch.guard.tokenCanonicalDigest =
        Digest("foreign-canonical");
    runGuardCase("N02_TOKEN_DIGEST_MISMATCH", tokenDigestMismatch,
        LauncherPresentationVerdict::DIGEST_MISMATCH,
        "token canonical digest 不得与当前代拼接");

    auto resourceDigestMismatch = baseSnapshot;
    resourceDigestMismatch.guard.resourceCanonicalDigest =
        Digest("foreign-resource-canonical");
    runGuardCase("N02_RESOURCE_DIGEST_MISMATCH", resourceDigestMismatch,
        LauncherPresentationVerdict::DIGEST_MISMATCH,
        "A08 resource runtime canonical digest 必须同代");

    {
        FakeSnapshotProvider provider(baseSnapshot);
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        auto query = QueryFor(provider.CurrentSnapshot(),
            "n02-request-digest", primaryComponent,
            primaryConfiguration, caller);
        query.expectedCanonicalDigest = Digest("foreign-query-generation");
        const auto response = service.Query(query, nullptr);
        test->Check(
            response.verdict ==
                LauncherPresentationVerdict::DIGEST_MISMATCH,
            "N02_REQUEST_DIGEST_MISMATCH", "N",
            "request expectedCanonicalDigest 错配 fail closed", response);
    }

    {
        FakeSnapshotProvider provider(baseSnapshot);
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        auto query = QueryFor(provider.CurrentSnapshot(),
            "n02-schema", primaryComponent, primaryConfiguration, caller);
        query.schemaVersion = 2;
        const auto response = service.Query(query, nullptr);
        test->Check(
            response.verdict ==
                    LauncherPresentationVerdict::INVALID_REQUEST &&
                provider.readCount == 0,
            "N02_UNKNOWN_MAJOR", "N",
            "unknown schema major 在 admission typed reject", response);
    }
}

void RunFailureCases(TestContext* test,
    const LauncherPresentationSnapshotV1& baseSnapshot,
    const std::string& primaryComponent,
    const ConfigurationSelectorV1& primaryConfiguration,
    const std::string& caller)
{
    auto queryFor = [&](const FakeSnapshotProvider& provider,
                        const std::string& requestId) {
        return QueryFor(provider.CurrentSnapshot(), requestId,
            primaryComponent, primaryConfiguration, caller);
    };

    {
        auto stale = baseSnapshot;
        stale.guard.projectionState = HostProjectionState::STALE;
        FakeSnapshotProvider provider(std::move(stale));
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        const auto response =
            service.Query(queryFor(provider, "f01-stale"), nullptr);
        test->Check(
            response.verdict ==
                    LauncherPresentationVerdict::PROJECTION_STALE &&
                response.cacheInvalidated &&
                provider.invalidationCount == 1 &&
                provider.canonicalMutationCount == 0 &&
                provider.lastInvalidation.generation ==
                    baseSnapshot.guard.canonicalGeneration,
            "F01_STALE_INVALIDATES_CACHE", "F",
            "stale projection 只清当前代可重建 cache，不改 package truth",
            response);
    }

    {
        auto corrupt = baseSnapshot;
        corrupt.assets[0].renderedAssetHash = Digest("corrupt-rendered");
        FakeSnapshotProvider provider(std::move(corrupt));
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        const auto response =
            service.Query(queryFor(provider, "f01-corrupt"), nullptr);
        test->Check(
            response.verdict ==
                    LauncherPresentationVerdict::PROJECTION_CORRUPT &&
                response.cacheInvalidated &&
                provider.invalidationCount == 1 &&
                provider.canonicalMutationCount == 0,
            "F01_RENDERED_HASH_CORRUPT", "F",
            "rendered asset hash corrupt 清 cache 并 fail closed", response);
    }

    {
        auto ambiguous = baseSnapshot;
        auto duplicate = ambiguous.assets[0];
        duplicate.label += "-conflict";
        duplicate.renderedAssetHash =
            LauncherPresentationServiceV1::ComputeRenderedAssetHash(
                duplicate);
        ambiguous.assets.push_back(std::move(duplicate));
        FakeSnapshotProvider provider(std::move(ambiguous));
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        const auto response =
            service.Query(queryFor(provider, "f01-ambiguous"), nullptr);
        test->Check(
            response.verdict ==
                    LauncherPresentationVerdict::PROJECTION_CORRUPT &&
                response.cacheInvalidated &&
                provider.invalidationCount == 1,
            "F01_AMBIGUOUS_EXACT_ASSET", "F",
            "同 component/configuration 多份资源不得依赖 vector 顺序选第一份",
            response);
    }

    {
        auto mismatch = baseSnapshot;
        mismatch.resourcePayloadReadbackBytes += "|tampered";
        FakeSnapshotProvider provider(std::move(mismatch));
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        const auto response =
            service.Query(queryFor(provider, "f01-readback"), nullptr);
        test->Check(
            response.verdict ==
                    LauncherPresentationVerdict::
                        RESOURCE_READBACK_MISMATCH &&
                response.cacheInvalidated &&
                provider.invalidationCount == 1 &&
                provider.canonicalMutationCount == 0,
            "F01_RESOURCE_READBACK_MISMATCH", "F",
            "resource readback digest mismatch 清 cache，不返回旧 view",
            response);
    }

    {
        FakeSnapshotProvider provider(baseSnapshot);
        provider.invalidationSucceeds = false;
        provider.MutableSnapshot().guard.resourceRuntimeState =
            ResourceRuntimeState::STALE;
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        const auto response = service.Query(
            queryFor(provider, "f01-cache-clear-fails"), nullptr);
        test->Check(
            response.verdict ==
                    LauncherPresentationVerdict::
                        CACHE_INVALIDATION_FAILED &&
                !response.cacheInvalidated &&
                provider.canonicalMutationCount == 0,
            "F01_CACHE_INVALIDATION_FAILURE", "F",
            "cache 无法清除时保持 fail closed，不能声称 stale 已处理",
            response);
    }

    {
        FakeSnapshotProvider provider(baseSnapshot);
        provider.readVerdict = SnapshotReadVerdict::IO_ERROR;
        provider.readReason = "injected-durable-readback-error";
        LauncherPresentationServiceV1 service(Policy(caller), &provider);
        const auto response =
            service.Query(queryFor(provider, "f01-io"), nullptr);
        test->Check(
            response.verdict ==
                    LauncherPresentationVerdict::SNAPSHOT_READ_FAILED &&
                provider.invalidationCount == 0 &&
                provider.canonicalMutationCount == 0,
            "F01_SNAPSHOT_IO", "F",
            "durable snapshot I/O 与 absence 分离并 typed fail closed",
            response);
    }

    for (const auto phase : {
             QueryPhase::AFTER_GUARD_JOIN,
             QueryPhase::BEFORE_RESOURCE_READBACK,
             QueryPhase::AFTER_RESOURCE_READBACK,
             QueryPhase::BEFORE_RESPONSE_SERIALIZATION,
             QueryPhase::AFTER_RESPONSE_SERIALIZATION,
         }) {
        FakeSnapshotProvider provider(baseSnapshot);
        LauncherPresentationServiceV1 firstService(Policy(caller), &provider);
        FaultOnce fault(phase);
        auto query = queryFor(provider,
            "f02-phase-" + std::to_string(static_cast<int>(phase)));
        const auto interrupted = firstService.Query(query, &fault);
        LauncherPresentationServiceV1 restartedService(
            Policy(caller), &provider);
        query.requestId += "-replay";
        const auto recovered = restartedService.Query(query, nullptr);
        test->Check(
            interrupted.verdict ==
                    LauncherPresentationVerdict::INTERRUPTED_RETRY &&
                interrupted.label.empty() &&
                interrupted.iconBytes.empty() &&
                recovered.verdict ==
                    LauncherPresentationVerdict::READY &&
                recovered.renderedAssetHash ==
                    baseSnapshot.assets[0].renderedAssetHash &&
                provider.canonicalMutationCount == 0,
            "F02_RESTART_PHASE_" +
                std::to_string(static_cast<int>(phase)),
            "F",
            "中断后新 service 完整重做 guard/readback 并只返回同代完整 view",
            recovered);
    }
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 7) {
        std::cerr << "usage: launcher_presentation_host_test RESULTS_JSONL "
                     "PACKAGE_PREFIX PRIMARY_COMPONENT SECONDARY_COMPONENT "
                     "PRIMARY_LOCALE SECONDARY_LOCALE\n";
        return 2;
    }
    const std::string resultsPath = argv[1];
    const std::string packagePrefix = argv[2];
    const std::string primaryComponent = argv[3];
    const std::string secondaryComponent = argv[4];
    const std::string primaryLocale = argv[5];
    const std::string secondaryLocale = argv[6];
    if (packagePrefix.empty() || primaryComponent.empty() ||
        secondaryComponent.empty() ||
        primaryComponent == secondaryComponent ||
        primaryLocale.empty() || secondaryLocale.empty() ||
        primaryLocale == secondaryLocale) {
        std::cerr << "fixture inputs must be non-empty and distinguishable\n";
        return 2;
    }

    const std::string caller = Digest(
        "caller|" + packagePrefix + "|" + primaryLocale);
    const auto primaryConfiguration =
        Configuration(primaryLocale, 420, false);
    const auto secondaryConfiguration =
        Configuration(secondaryLocale, 560, true);
    const auto alphaSnapshot = Snapshot(packagePrefix + ".alpha", 7,
        primaryComponent, secondaryComponent, primaryConfiguration,
        secondaryConfiguration);
    const auto betaSnapshot = Snapshot(packagePrefix + ".beta", 19,
        primaryComponent, secondaryComponent, primaryConfiguration,
        secondaryConfiguration);

    TestContext test(resultsPath);
    RunPositiveCases(&test, alphaSnapshot, betaSnapshot,
        primaryComponent, secondaryComponent, primaryConfiguration,
        secondaryConfiguration, caller);
    RunNegativeCases(&test, alphaSnapshot, primaryComponent,
        primaryConfiguration, secondaryLocale + "-variant", caller);
    RunFailureCases(&test, alphaSnapshot, primaryComponent,
        primaryConfiguration, caller);
    std::cout << "SUMMARY passed=" << test.passed
              << " failed=" << test.failed << "\n";
    return test.failed == 0 ? 0 : 1;
}
