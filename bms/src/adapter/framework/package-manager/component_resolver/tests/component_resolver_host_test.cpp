#include "component_resolver_runtime_v1.h"
#include "component_resolver_v1.h"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <string>
#include <vector>

using namespace oh_adapter::component_resolver;

namespace {

int failures = 0;
#define EXPECT(x) do { if (!(x)) { std::cerr << "FAIL line=" << __LINE__ \
    << " expression=" << #x << "\n"; ++failures; } } while (0)
#define EQUAL(a,b) do { const auto av=(a); const auto bv=(b); \
    if (!(av == bv)) { std::cerr << "FAIL line=" << __LINE__ \
    << " expression=" << #a << " == " << #b << "\n"; ++failures; } } while (0)

IntentFilterDataV1 Filter(const std::string& action, int32_t priority,
    bool isDefault = true)
{
    IntentFilterDataV1 filter;
    filter.actions = {action};
    filter.categories = {"android.intent.category.DEFAULT"};
    filter.isDefault = isDefault;
    filter.priority = priority;
    return filter;
}

ComponentFactV1 Component(ComponentKind kind, const std::string& name,
    IntentFilterDataV1 filter)
{
    ComponentFactV1 component;
    component.kind = kind;
    component.name = name;
    component.exported = true;
    component.filters = {std::move(filter)};
    return component;
}

ComponentCatalogV1 Catalog()
{
    ComponentCatalogV1 catalog;
    catalog.catalogRevision = 42;

    PackageComponentIndexV1 alpha;
    alpha.packageName = "dev.fixture.alpha";
    alpha.generation = 7;
    alpha.canonicalDigest = std::string(64, 'a');
    auto view = Component(ComponentKind::ACTIVITY,
        "dev.fixture.alpha.ViewActivity",
        Filter("dev.fixture.VIEW", 5));
    view.filters[0].mimeTypes = {"image/*"};
    view.filters[0].schemes = {"content"};
    view.filters[0].hosts = {"fixture.test"};
    view.filters[0].pathPrefixes = {"/images/"};
    view.preferredOrder = 2;
    alpha.components.push_back(view);
    auto stableOne = Component(ComponentKind::ACTIVITY,
        "dev.fixture.alpha.StableOne",
        Filter("dev.fixture.STABLE", 3));
    auto stableTwo = Component(ComponentKind::ACTIVITY,
        "dev.fixture.alpha.StableTwo",
        Filter("dev.fixture.STABLE", 3));
    alpha.components.push_back(stableOne);
    alpha.components.push_back(stableTwo);
    auto privateService = Component(ComponentKind::SERVICE,
        "dev.fixture.alpha.PrivateService",
        Filter("dev.fixture.SERVICE", 0));
    privateService.exported = false;
    alpha.components.push_back(privateService);
    auto permissionReceiver = Component(ComponentKind::RECEIVER,
        "dev.fixture.alpha.PermissionReceiver",
        Filter("dev.fixture.RECEIVE", 0));
    permissionReceiver.requiredPermission = "dev.fixture.permission.SEND";
    alpha.components.push_back(permissionReceiver);

    PackageComponentIndexV1 beta;
    beta.packageName = "dev.fixture.beta";
    beta.generation = 11;
    beta.canonicalDigest = std::string(64, 'b');
    auto betaView = Component(ComponentKind::ACTIVITY,
        "dev.fixture.beta.ViewActivity",
        Filter("dev.fixture.VIEW", 8));
    betaView.filters[0].mimeTypes = {"image/png"};
    betaView.filters[0].schemes = {"content"};
    betaView.filters[0].hosts = {"fixture.test"};
    betaView.filters[0].pathPrefixes = {"/images/"};
    betaView.system = true;
    beta.components.push_back(betaView);

    catalog.packages = {alpha, beta};
    return catalog;
}

PackageGuardV1 Guard(const PackageComponentIndexV1& package)
{
    PackageGuardV1 guard;
    guard.catalogRevision = 42;
    guard.hasCanonical = true;
    guard.generation = package.generation;
    guard.canonicalDigest = package.canonicalDigest;
    guard.projectionActive = true;
    guard.tokenExternalReady = true;
    guard.projectionGeneration = package.generation;
    guard.projectionCanonicalDigest = package.canonicalDigest;
    guard.tokenGeneration = package.generation;
    guard.tokenCanonicalDigest = package.canonicalDigest;
    return guard;
}

class FixtureCatalog final : public ComponentCatalogProviderV1 {
public:
    bool Read(ComponentCatalogV1* output, std::string* digest,
        std::string* error) override
    {
        if (fail) {
            if (error != nullptr) *error = "fixture index failure";
            return false;
        }
        *output = catalog;
        *digest = indexDigest;
        return true;
    }
    ComponentCatalogV1 catalog = Catalog();
    std::string indexDigest = std::string(64, 'c');
    bool fail = false;
};

class FixtureGuards final : public PackageGuardReaderV1 {
public:
    FixtureGuards()
    {
        for (const auto& package : Catalog().packages) {
            guards[package.packageName] = Guard(package);
        }
    }
    bool Read(uint32_t userId, const std::string& packageName,
        PackageGuardV1* guard, std::string* error) override
    {
        if (userId != 0 || fail || guards.count(packageName) == 0) {
            if (error != nullptr) *error = "fixture guard failure";
            return false;
        }
        *guard = guards[packageName];
        return true;
    }
    std::map<std::string, PackageGuardV1> guards;
    bool fail = false;
};

class OneShotFault final : public ResolveFaultInjectorV1 {
public:
    explicit OneShotFault(std::optional<ResolvePhase> phase)
        : phase_(phase) {}
    bool InterruptAfter(ResolvePhase phase) override
    {
        if (!fired_ && phase_ == phase) {
            fired_ = true;
            return true;
        }
        return false;
    }
private:
    std::optional<ResolvePhase> phase_;
    bool fired_ = false;
};

class FixtureCallerProvider final : public CallerResolveContextProviderV1 {
public:
    bool Resolve(int32_t callingUid, uint32_t userId,
        CallerResolveContextV1* caller, std::string* error) override
    {
        if (callingUid != 12001 || userId != 0 || caller == nullptr) {
            if (error != nullptr) *error = "fixture caller rejected";
            return false;
        }
        caller->callingUid = callingUid;
        caller->callerPackageName = "dev.fixture.caller";
        caller->visibilityScopeDigest = std::string(64, 'd');
        caller->canSeeAllPackages = true;
        caller->grantedPermissions = {"dev.fixture.permission.SEND"};
        return true;
    }
};

ComponentResolveRequestV1 Request(ComponentKind kind,
    const std::string& action)
{
    ComponentResolveRequestV1 request;
    request.requestId = "request-" + action;
    request.kind = kind;
    request.intent.action = action;
    request.intent.categories = {"android.intent.category.DEFAULT"};
    request.defaultOnly = true;
    request.caller.callingUid = 12001;
    request.caller.callerPackageName = "dev.fixture.caller";
    request.caller.visibilityScopeDigest = std::string(64, 'd');
    request.caller.canSeeAllPackages = true;
    return request;
}

ComponentResolveResponseV1 Resolve(ComponentResolveRequestV1 request,
    FixtureCatalog* catalog, FixtureGuards* guards,
    ResolveFaultInjectorV1* fault)
{
    ComponentResolverServiceV1 service(catalog, guards, fault);
    return service.Resolve(request);
}

void TestPositiveAndSorting()
{
    FixtureCatalog catalog;
    FixtureGuards guards;
    NoResolveFaultInjectorV1 fault;
    auto request = Request(ComponentKind::ACTIVITY, "dev.fixture.VIEW");
    request.intent.resolvedType = "image/png";
    request.intent.scheme = "content";
    request.intent.host = "fixture.test";
    request.intent.path = "/images/42";
    const auto response = Resolve(request, &catalog, &guards, &fault);
    EQUAL(response.verdict, ComponentResolveVerdict::READY);
    EQUAL(response.results.size(), 2U);
    EQUAL(response.results[0].packageName, "dev.fixture.beta");
    EQUAL(response.results[1].packageName, "dev.fixture.alpha");
    EQUAL(response.results[0].match, response.results[1].match);
    EQUAL(response.guardJoin.size(), 2U);
    const auto positiveJson = ComponentResolveResponseJsonV1(response);
    EXPECT(positiveJson.find("\"canonicalState\":\"CANONICAL_SELECTED\"") !=
        std::string::npos);
    EXPECT(positiveJson.find("\"tokenState\":\"EXTERNAL_READY\"") !=
        std::string::npos);
    std::cout << "EVIDENCE P01 response=" << positiveJson << "\n";
    std::cout << "PASS P01 implicit_action_category_type_scheme_data_sort\n";

    catalog.catalog.packages[0].components[0].filters[0].hosts =
        {"FIXTURE.TEST"};
    const auto hostCaseResponse =
        Resolve(request, &catalog, &guards, &fault);
    EQUAL(hostCaseResponse.results.size(), 2U);
    std::cout << "PASS P01 authority_host_ascii_case_fold\n";

    catalog.catalog.packages[0].components[0].filters[0].schemes.clear();
    catalog.catalog.packages[0].components[0].filters[0].hosts.clear();
    catalog.catalog.packages[0].components[0].filters[0].pathPrefixes.clear();
    request.intent.packageSelector = "dev.fixture.alpha";
    const auto typeOnlyContent =
        Resolve(request, &catalog, &guards, &fault);
    EQUAL(typeOnlyContent.results.size(), 1U);
    std::cout << "PASS P01 android_type_only_content_scheme\n";
    catalog.catalog = Catalog();

    auto stable = Request(ComponentKind::ACTIVITY, "dev.fixture.STABLE");
    const auto stableResponse = Resolve(stable, &catalog, &guards, &fault);
    EQUAL(stableResponse.results.size(), 2U);
    EQUAL(stableResponse.results[0].componentName,
        "dev.fixture.alpha.StableOne");
    EQUAL(stableResponse.results[1].componentName,
        "dev.fixture.alpha.StableTwo");
    std::cout << "PASS P01 stable_complete_tie\n";

    auto explicitRequest =
        Request(ComponentKind::SERVICE, "ignored.explicit.action");
    explicitRequest.intent.explicitPackage = "dev.fixture.alpha";
    explicitRequest.intent.explicitClass =
        "dev.fixture.alpha.PrivateService";
    explicitRequest.caller.callerPackageName = "dev.fixture.alpha";
    const auto explicitResponse =
        Resolve(explicitRequest, &catalog, &guards, &fault);
    EQUAL(explicitResponse.results.size(), 1U);
    EQUAL(explicitResponse.results[0].componentName,
        "dev.fixture.alpha.PrivateService");
    std::cout << "PASS P01 explicit_same_package_private_component\n";
}

void TestNegative()
{
    FixtureCatalog catalog;
    FixtureGuards guards;
    NoResolveFaultInjectorV1 fault;

    auto invisible = Request(ComponentKind::ACTIVITY, "dev.fixture.VIEW");
    invisible.caller.canSeeAllPackages = false;
    const auto invisibleResponse =
        Resolve(invisible, &catalog, &guards, &fault);
    EQUAL(invisibleResponse.verdict, ComponentResolveVerdict::READY);
    EXPECT(invisibleResponse.results.empty());
    EXPECT(std::all_of(invisibleResponse.trace.begin(),
        invisibleResponse.trace.end(), [](const auto& event) {
            return event.packageName.empty() &&
                event.componentName.empty();
        }));

    auto notExported =
        Request(ComponentKind::SERVICE, "dev.fixture.SERVICE");
    const auto notExportedResponse =
        Resolve(notExported, &catalog, &guards, &fault);
    EXPECT(notExportedResponse.results.empty());

    auto denied =
        Request(ComponentKind::RECEIVER, "dev.fixture.RECEIVE");
    const auto deniedResponse =
        Resolve(denied, &catalog, &guards, &fault);
    EXPECT(deniedResponse.results.empty());
    denied.caller.grantedPermissions = {"dev.fixture.permission.SEND"};
    const auto grantedResponse =
        Resolve(denied, &catalog, &guards, &fault);
    EQUAL(grantedResponse.results.size(), 1U);

    auto noMatch = Request(ComponentKind::ACTIVITY, "dev.fixture.NONE");
    EXPECT(Resolve(noMatch, &catalog, &guards, &fault).results.empty());

    auto invalidKind = Request(ComponentKind::ACTIVITY, "dev.fixture.VIEW");
    invalidKind.kindWasRecognized = false;
    EQUAL(Resolve(invalidKind, &catalog, &guards, &fault).verdict,
        ComponentResolveVerdict::INVALID_COMPONENT_KIND);

    auto disabled = Request(ComponentKind::ACTIVITY, "dev.fixture.STABLE");
    catalog.catalog.packages[0].components[1].enabled = false;
    EQUAL(Resolve(disabled, &catalog, &guards, &fault).results.size(), 1U);
    disabled.flags = 0x00000200ULL;
    EQUAL(Resolve(disabled, &catalog, &guards, &fault).results.size(), 2U);
    disabled.flags = 1ULL << 63;
    EQUAL(Resolve(disabled, &catalog, &guards, &fault).verdict,
        ComponentResolveVerdict::NOT_SUPPORTED);

    auto unsupported = Request(ComponentKind::ACTIVITY, "dev.fixture.VIEW");
    catalog.catalog = Catalog();
    catalog.catalog.packages[0].components[0]
        .filters[0].hasUnsupportedPattern = true;
    EQUAL(Resolve(unsupported, &catalog, &guards, &fault).verdict,
        ComponentResolveVerdict::NOT_SUPPORTED_FILTER);

    catalog.catalog = Catalog();
    catalog.catalog.packages[0].removing = true;
    auto removing = Request(ComponentKind::ACTIVITY, "dev.fixture.STABLE");
    removing.intent.packageSelector = "dev.fixture.alpha";
    const auto removingResponse =
        Resolve(removing, &catalog, &guards, &fault);
    EQUAL(removingResponse.verdict,
        ComponentResolveVerdict::PACKAGE_REMOVING);
    std::cout << "EVIDENCE N01 response="
        << ComponentResolveResponseJsonV1(removingResponse) << "\n";
    catalog.catalog = Catalog();
    PackageGuardV1 tombstone;
    tombstone.catalogRevision = 42;
    tombstone.removing = true;
    guards.guards["dev.fixture.removing"] = tombstone;
    removing.intent.packageSelector = "dev.fixture.removing";
    EQUAL(Resolve(removing, &catalog, &guards, &fault).verdict,
        ComponentResolveVerdict::PACKAGE_REMOVING);
    std::cout << "PASS N01 empty_export_permission_visibility_kind_filter_removing\n";

    catalog.catalog = Catalog();
    auto mismatch = Request(ComponentKind::ACTIVITY, "dev.fixture.STABLE");
    mismatch.intent.packageSelector = "dev.fixture.alpha";
    mismatch.expectedGeneration = 99;
    EQUAL(Resolve(mismatch, &catalog, &guards, &fault).verdict,
        ComponentResolveVerdict::PACKAGE_NOT_READY);
    mismatch.expectedGeneration = 7;
    mismatch.expectedCanonicalDigest = std::string(64, 'e');
    EQUAL(Resolve(mismatch, &catalog, &guards, &fault).verdict,
        ComponentResolveVerdict::PACKAGE_NOT_READY);
    mismatch.userId = 10;
    EQUAL(Resolve(mismatch, &catalog, &guards, &fault).verdict,
        ComponentResolveVerdict::NOT_SUPPORTED);
    std::cout << "PASS N02 generation_digest_selector_mismatch\n";
}

void TestFailuresAndRestart()
{
    for (const auto phase : {ResolvePhase::SNAPSHOT_FROZEN,
             ResolvePhase::CANDIDATES_FILTERED,
             ResolvePhase::RESPONSE_SERIALIZED}) {
        FixtureCatalog catalog;
        FixtureGuards guards;
        OneShotFault fault(phase);
        auto request = Request(ComponentKind::ACTIVITY,
            "dev.fixture.STABLE");
        const auto interrupted =
            Resolve(request, &catalog, &guards, &fault);
        EQUAL(interrupted.verdict,
            ComponentResolveVerdict::PACKAGE_NOT_READY);
        EXPECT(interrupted.results.empty());
        if (phase == ResolvePhase::SNAPSHOT_FROZEN) {
            std::cout << "EVIDENCE F02 response="
                << ComponentResolveResponseJsonV1(interrupted) << "\n";
        }
        if (phase == ResolvePhase::SNAPSHOT_FROZEN) {
            request.intent.packageSelector = "dev.fixture.alpha";
            ++guards.guards["dev.fixture.alpha"].generation;
            const auto stale =
                Resolve(request, &catalog, &guards, &fault);
            EQUAL(stale.verdict,
                ComponentResolveVerdict::PACKAGE_NOT_READY);
            guards.guards["dev.fixture.alpha"] =
                Guard(Catalog().packages[0]);
        }
        const auto replay = Resolve(request, &catalog, &guards, &fault);
        EQUAL(replay.verdict, ComponentResolveVerdict::READY);
        EQUAL(replay.results.size(), 2U);
    }

    FixtureCatalog catalog;
    FixtureGuards guards;
    NoResolveFaultInjectorV1 fault;
    auto request = Request(ComponentKind::ACTIVITY, "dev.fixture.STABLE");
    catalog.fail = true;
    EQUAL(Resolve(request, &catalog, &guards, &fault).verdict,
        ComponentResolveVerdict::PACKAGE_NOT_READY);
    catalog.fail = false;
    guards.guards["dev.fixture.alpha"].projectionActive = false;
    request.intent.packageSelector = "dev.fixture.alpha";
    EQUAL(Resolve(request, &catalog, &guards, &fault).verdict,
        ComponentResolveVerdict::PACKAGE_NOT_READY);
    guards.guards["dev.fixture.alpha"] = Guard(Catalog().packages[0]);
    guards.guards["dev.fixture.alpha"].tokenCanonicalDigest =
        std::string(64, 'f');
    EQUAL(Resolve(request, &catalog, &guards, &fault).verdict,
        ComponentResolveVerdict::PACKAGE_NOT_READY);
    std::cout << "PASS F01_F02 guard_fault_restart_same_anchor\n";
}

void TestDurableCodecAndRuntime()
{
    std::vector<uint8_t> bytes;
    std::string error;
    EXPECT(SerializeComponentCatalogV1(Catalog(), &bytes, &error));
    ComponentCatalogV1 parsed;
    EXPECT(ParseComponentCatalogV1(bytes, &parsed, &error));
    EQUAL(parsed.packages.size(), 2U);
    EQUAL(parsed.packages[0].components.size(), 5U);
    EXPECT(ComponentCatalogDigestV1(bytes).size() == 64);
    bytes.push_back(0);
    EXPECT(!ParseComponentCatalogV1(bytes, &parsed, &error));
    std::cout << "PASS F01 durable_codec_trailing_corruption_rejected\n";

    auto request = Request(ComponentKind::ACTIVITY, "dev.fixture.STABLE");
    const auto closed = QueryComponentResolverRuntimeJsonV1(request, 12001);
    EXPECT(closed.find("COMPONENT_RESOLVER_RUNTIME_NOT_CONFIGURED") !=
        std::string::npos);

    FixtureCatalog catalog;
    FixtureGuards guards;
    FixtureCallerProvider caller;
    NoResolveFaultInjectorV1 fault;
    EXPECT(ConfigureComponentResolverRuntimeV1(
        &catalog, &guards, &caller, &fault, &error));
    const auto runtime = QueryComponentResolverRuntimeJsonV1(request, 12001);
    EXPECT(runtime.find("\"actionId\":\"Fn01.A06\"") !=
        std::string::npos);
    EXPECT(runtime.find("\"generation\":7") != std::string::npos);
    EXPECT(runtime.find("\"verdict\":\"READY\"") != std::string::npos);
    EXPECT(runtime.find("dev.fixture.alpha.StableOne") !=
        std::string::npos);
    ClearComponentResolverRuntimeV1();
    const auto restarted = QueryComponentResolverRuntimeJsonV1(
        request, 12001);
    EXPECT(restarted.find("COMPONENT_RESOLVER_RUNTIME_NOT_CONFIGURED") !=
        std::string::npos);
    std::cout << "PASS P02 runtime_configure_clear_restart_fail_closed\n";
}

}  // namespace

int main()
{
    TestPositiveAndSorting();
    TestNegative();
    TestFailuresAndRestart();
    TestDurableCodecAndRuntime();
    if (failures != 0) {
        std::cerr << "FAIL fn01_a06_host failures=" << failures << "\n";
        return 1;
    }
    std::cout << "PASS fn01_a06_host total=10\n";
    return 0;
}
