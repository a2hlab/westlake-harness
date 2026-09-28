#include "application_info_v1.h"
#include "component_resolver_v1.h"
#include "package_info_v1.h"
#include "package_query_v1.h"
#include "package_transaction_v1.h"
#include "runtime_path_descriptor_v1.h"
#include "sha256.h"

#include <cerrno>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <sys/stat.h>
#include <utility>
#include <vector>

#if !defined(FN01_ENABLE_REFERENCE_FIXTURES)
#error "Fn01.A11 target fence probe requires test-only fixture seam"
#endif

namespace {

namespace ai = oh_adapter::application_info;
namespace cr = oh_adapter::component_resolver;
namespace pi = oh_adapter::package_info;
namespace pq = oh_adapter::package_query;
namespace pt = oh_adapter::package_transaction;
namespace rp = oh_adapter::runtime_path_descriptor;

int gFailures = 0;

void Require(bool condition, const char* expression, int line)
{
    if (condition) return;
    std::cerr << "ASSERTION_FAILED line=" << line
              << " expression=" << expression << "\n";
    ++gFailures;
}

#define REQUIRE(condition) Require((condition), #condition, __LINE__)

std::string Sha256Hex(std::string_view value)
{
    uint8_t digest[32]{};
    sha256(reinterpret_cast<const uint8_t*>(value.data()), value.size(),
        digest);
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        result[index * 2] = kHex[digest[index] >> 4];
        result[index * 2 + 1] = kHex[digest[index] & 0x0f];
    }
    return result;
}

std::string Json(std::string_view value)
{
    std::ostringstream out;
    out << '"';
    for (const unsigned char character : value) {
        switch (character) {
            case '"': out << "\\\""; break;
            case '\\': out << "\\\\"; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default:
                if (character >= 0x20) out << character;
        }
    }
    out << '"';
    return out.str();
}

pt::InstallRequestV1 MakeInstallRequest(const std::string& packageName)
{
    const std::string transactionId = "tx-fn01-a11-target-fence";
    const std::string bytes = "fn01-a11-prepared-snapshot-base-apk";
    pt::InstallRequestV1 request;
    pt::ArtifactDescriptorV1 artifact;
    artifact.artifactId = "base";
    artifact.role = pt::ArtifactRole::BASE;
    artifact.bytes.assign(bytes.begin(), bytes.end());
    artifact.byteLength = artifact.bytes.size();
    artifact.sha256 = Sha256Hex(bytes);
    request.artifactSet.artifacts.push_back(artifact);
    request.artifactSet.artifactSetDigest =
        pt::ComputeArtifactSetDigest(request.artifactSet);

    request.manifest.artifactSetDigest =
        request.artifactSet.artifactSetDigest;
    request.manifest.parserVersion = "fn01-a11-fence-probe-v1";
    request.manifest.packageName = packageName;
    request.manifest.versionCode = 11;
    request.manifest.versionName = "1.1";
    request.manifest.minSdk = 26;
    request.manifest.targetSdk = 35;
    request.manifest.applicationClassName = packageName + ".Application";
    request.manifest.applicationLabel = "Fn01 A11 fence probe";
    request.manifest.components.push_back(
        {"activity", packageName + ".MainActivity", true});

    request.signing.artifactSetDigest =
        request.artifactSet.artifactSetDigest;
    request.signing.verifierVersion = "fn01-a11-fence-probe-v1";
    request.signing.policyProfile = "fn01-a11-fence-policy-v1";
    request.signing.verified = true;
    request.signing.schemeVersions = {2, 3};
    request.signing.signerCertificateDigests = {
        Sha256Hex("signer:" + packageName),
    };
    request.signing.signerCertificateDerHex = {
        "30820100" + Sha256Hex("der:" + packageName),
    };

    request.userId = 0;
    request.expectedPackageName = packageName;
    request.policyRef = "fn01-a11-fence-policy-v1";
    request.retryIdentity = "retry:" + transactionId;
    request.admission.schemaVersion = 1;
    request.admission.jobId = "job:" + transactionId;
    request.admission.memberId = "member:" + transactionId;
    request.admission.memberIndex = 0;
    request.admission.operation = "INSTALL";
    request.admission.transactionId = transactionId;
    request.admission.jobRecordVersion = 1;
    request.admission.callerScopeDigest =
        Sha256Hex("fn01-a11-fence-caller");
    request.admission.policySnapshotId = request.policyRef;
    request.admission.requestDigest =
        pt::ComputeInstallRequestDigest(request);
    return request;
}

std::string SnapshotIdentity(const pt::PackageManagementReadV1& state)
{
    std::ostringstream out;
    out << state.catalogRevision << "|" << state.removing;
    if (state.canonical.has_value()) {
        out << "|canonical|" << state.canonical->packageName
            << "|" << state.canonical->userId
            << "|" << state.canonical->generation
            << "|" << state.canonical->canonicalDigest
            << "|" << static_cast<int>(state.canonical->publicationState);
    }
    if (state.projection.has_value()) {
        out << "|projection|" << state.projection->packageName
            << "|" << state.projection->userId
            << "|" << state.projection->generation
            << "|" << state.projection->canonicalDigest
            << "|" << static_cast<int>(state.projection->state);
    }
    if (state.publicationToken.has_value()) {
        out << "|token|" << state.publicationToken->packageName
            << "|" << state.publicationToken->userId
            << "|" << state.publicationToken->generation
            << "|" << state.publicationToken->canonicalDigest
            << "|" << static_cast<int>(state.publicationToken->state);
    }
    return out.str();
}

class SnapshotCatalogProvider final : public cr::ComponentCatalogProviderV1 {
public:
    explicit SnapshotCatalogProvider(
        const pt::PackageManagementReadV1& state)
    {
        cr::PackageComponentIndexV1 package;
        package.packageName = state.canonical->packageName;
        package.userId = state.canonical->userId;
        package.generation = state.canonical->generation;
        package.canonicalDigest = state.canonical->canonicalDigest;
        cr::ComponentFactV1 component;
        component.kind = cr::ComponentKind::ACTIVITY;
        component.name = package.packageName + ".MainActivity";
        component.enabled = true;
        component.exported = true;
        package.components.push_back(std::move(component));
        catalog_.catalogRevision = state.catalogRevision;
        catalog_.packages.push_back(std::move(package));
        std::vector<uint8_t> bytes;
        std::string error;
        valid_ = cr::SerializeComponentCatalogV1(catalog_, &bytes, &error);
        digest_ = valid_ ? cr::ComponentCatalogDigestV1(bytes) : "";
    }

    bool Read(cr::ComponentCatalogV1* catalog, std::string* digest,
        std::string* error) override
    {
        ++calls;
        if (!valid_ || catalog == nullptr || digest == nullptr) {
            if (error != nullptr) *error = "catalog unavailable";
            return false;
        }
        *catalog = catalog_;
        *digest = digest_;
        return true;
    }

    int calls = 0;

private:
    cr::ComponentCatalogV1 catalog_;
    std::string digest_;
    bool valid_ = false;
};

class StoreGuardReader final : public cr::PackageGuardReaderV1 {
public:
    explicit StoreGuardReader(pt::FilePackageStore* store) : store_(store) {}

    bool Read(uint32_t userId, const std::string& packageName,
        cr::PackageGuardV1* guard, std::string* error) override
    {
        ++calls;
        pt::PackageManagementReadV1 state;
        if (guard == nullptr ||
            !store_->ReadPackageManagementState(
                userId, packageName, &state, error)) {
            return false;
        }
        guard->catalogRevision = state.catalogRevision;
        guard->removing = state.removing;
        guard->hasCanonical = state.canonical.has_value();
        if (state.canonical.has_value()) {
            guard->generation = state.canonical->generation;
            guard->canonicalDigest = state.canonical->canonicalDigest;
        }
        if (state.projection.has_value()) {
            guard->projectionActive =
                state.projection->state == pt::HostProjectionState::ACTIVE;
            guard->projectionGeneration = state.projection->generation;
            guard->projectionCanonicalDigest =
                state.projection->canonicalDigest;
        }
        if (state.publicationToken.has_value()) {
            guard->tokenExternalReady =
                state.publicationToken->state ==
                pt::PublicationState::EXTERNAL_READY;
            guard->tokenGeneration = state.publicationToken->generation;
            guard->tokenCanonicalDigest =
                state.publicationToken->canonicalDigest;
        }
        return true;
    }

    int calls = 0;

private:
    pt::FilePackageStore* store_;
};

class CountingApplicationFacts final
    : public ai::HostApplicationRuntimeFactsResolverV1 {
public:
    ai::HostApplicationFactsVerdict Resolve(const std::string&, uint32_t,
        uint64_t, const std::string&, ai::HostApplicationRuntimeFactsV1*,
        std::string*) override
    {
        ++calls;
        return ai::HostApplicationFactsVerdict::DATA_INCONSISTENT;
    }
    int calls = 0;
};

class CountingPathReader final : public ai::ManagedPathReaderV1 {
public:
    bool Read(const ai::ManagedPathExpectationV1&,
        ai::ManagedPathReadbackV1*, std::string*) override
    {
        ++calls;
        return false;
    }
    int calls = 0;
};

class CountingRuntimeFacts final : public rp::RuntimePathFactsProvider {
public:
    bool Read(const std::string&, uint32_t, uint64_t, const std::string&,
        rp::RuntimePathFactsV1*, std::string*) const override
    {
        ++calls;
        return false;
    }
    mutable int calls = 0;
};

void EmitSnapshot(const pt::PackageManagementReadV1& state,
    const std::string& identityDigest)
{
    std::cout << "{\"event\":\"prepared_snapshot\""
              << ",\"serviceRestartBoundary\":true"
              << ",\"catalogRevision\":" << state.catalogRevision
              << ",\"canonicalState\":"
              << Json(pt::PublicationStateName(
                     state.canonical->publicationState))
              << ",\"projectionState\":"
              << Json(pt::HostProjectionStateName(state.projection->state))
              << ",\"tokenState\":"
              << Json(pt::PublicationStateName(
                     state.publicationToken->state))
              << ",\"generation\":" << state.canonical->generation
              << ",\"canonicalDigest\":"
              << Json(state.canonical->canonicalDigest)
              << ",\"snapshotIdentitySha256\":"
              << Json(identityDigest) << "}\n";
}

bool IsOperation(const std::string& operation)
{
    return operation == "fixture_prepare" || operation == "query" ||
        operation == "resolver" || operation == "launcher" ||
        operation == "token" || operation == "process";
}

int Run(const std::string& root, const std::string& operation)
{
    const std::string packageName = "org.bridge.fn01.a11.fence";
    const std::string storeRoot = root + "/store";
    const std::string filesRoot = root + "/files";
    if (operation == "fixture_prepare") {
        const pt::InstallRequestV1 install = MakeInstallRequest(packageName);
        pt::FilePackageStore producerStore(storeRoot);
        pt::PosixPackageFileStager stager(filesRoot);
        pt::NoFaultInjector transactionFault;
        pt::PackageTransactionCoordinator coordinator(
            &producerStore, &stager, &transactionFault);
        const auto receipt = coordinator.Install(install);
        std::cout << "{\"event\":\"fixture_install\""
                  << ",\"verdict\":"
                  << Json(pt::InstallVerdictName(receipt.verdict))
                  << ",\"terminalState\":" << Json(receipt.terminalState)
                  << "}\n";
        REQUIRE(receipt.verdict == pt::InstallVerdict::COMMITTED);
        REQUIRE(receipt.generation.has_value());
        REQUIRE(receipt.durableRecordDigest.has_value());
        if (gFailures != 0) return 1;
        std::string seedError;
        REQUIRE(producerStore.SeedHostProjectionForFixture(
            0, packageName, *receipt.generation, *receipt.durableRecordDigest,
            pt::HostProjectionState::PREPARED,
            pt::PublicationState::CANONICAL_SELECTED, &seedError));
    }

    // Every operation reopens the store, making the persisted PREPARED state
    // cross a fresh service boundary before any consumer call.
    pt::FilePackageStore store(storeRoot);
    std::string error;
    REQUIRE(store.Open(&error));
    pt::PackageManagementReadV1 before;
    REQUIRE(store.ReadPackageManagementState(
        0, packageName, &before, &error));
    REQUIRE(before.canonical.has_value());
    REQUIRE(before.projection.has_value());
    REQUIRE(before.publicationToken.has_value());
    if (gFailures != 0) return 1;
    REQUIRE(before.canonical->publicationState ==
        pt::PublicationState::CANONICAL_SELECTED);
    REQUIRE(before.projection->state == pt::HostProjectionState::PREPARED);
    REQUIRE(before.publicationToken->state !=
        pt::PublicationState::EXTERNAL_READY);
    const std::string beforeIdentity = SnapshotIdentity(before);
    const std::string beforeDigest = Sha256Hex(beforeIdentity);
    EmitSnapshot(before, beforeDigest);

    if (operation == "query") {
        pq::NoQueryFaultInjector queryFault;
        pq::PackageQueryService queryService(&store, &queryFault);
        pq::GetPackageRequestV1 query;
        query.requestId = "a11-f02-package-query";
        query.packageName = packageName;
        query.userId = 0;
        query.caller.callerId = "fence-probe";
        query.caller.visibilityScopeDigest = Sha256Hex("query-scope");
        query.caller.canSeeAllPackages = true;
        query.expectedGeneration = before.canonical->generation;
        query.expectedCanonicalDigest = before.canonical->canonicalDigest;
        const auto response = queryService.GetPackage(query);
        REQUIRE(response.verdict == pq::PackageQueryVerdict::PACKAGE_NOT_READY);
        REQUIRE(response.reason == "EXTERNAL_READY_NOT_ESTABLISHED");
        REQUIRE(!response.package.has_value());
        std::cout << "{\"consumer\":\"PackageQueryService\""
                  << ",\"publicCall\":\"GetPackage\""
                  << ",\"verdict\":"
                  << Json(pq::PackageQueryVerdictName(response.verdict))
                  << ",\"reason\":" << Json(response.reason)
                  << ",\"payloadPresent\":"
                  << (response.package.has_value() ? "true" : "false")
                  << "}\n";
    } else if (operation == "resolver") {
        SnapshotCatalogProvider catalog(before);
        StoreGuardReader guards(&store);
        cr::NoResolveFaultInjectorV1 resolverFault;
        cr::ComponentResolverServiceV1 service(
            &catalog, &guards, &resolverFault);
        cr::ComponentResolveRequestV1 request;
        request.requestId = "a11-f02-component-resolver";
        request.kind = cr::ComponentKind::ACTIVITY;
        request.intent.explicitPackage = packageName;
        request.intent.explicitClass = packageName + ".MainActivity";
        request.userId = 0;
        request.caller.callingUid = 12001;
        request.caller.callerPackageName = "org.bridge.fence.caller";
        request.caller.visibilityScopeDigest = Sha256Hex("resolver-scope");
        request.caller.canSeeAllPackages = true;
        request.expectedGeneration = before.canonical->generation;
        request.expectedCanonicalDigest = before.canonical->canonicalDigest;
        const auto response = service.Resolve(request);
        REQUIRE(response.verdict ==
            cr::ComponentResolveVerdict::PACKAGE_NOT_READY);
        REQUIRE(response.reason == "EXTERNAL_READY_NOT_ESTABLISHED");
        REQUIRE(response.results.empty());
        REQUIRE(response.trace.empty());
        REQUIRE(response.guardJoin.size() == 1);
        REQUIRE(catalog.calls == 1);
        REQUIRE(guards.calls == 1);
        std::cout << "{\"consumer\":\"ComponentResolverService\""
                  << ",\"publicCall\":\"Resolve\""
                  << ",\"verdict\":"
                  << Json(cr::ComponentResolveVerdictNameV1(response.verdict))
                  << ",\"reason\":" << Json(response.reason)
                  << ",\"resultCount\":" << response.results.size()
                  << ",\"candidateTraceCount\":" << response.trace.size()
                  << ",\"catalogReads\":" << catalog.calls
                  << ",\"guardReads\":" << guards.calls << "}\n";
    } else if (operation == "launcher") {
        pi::NoPackageInfoFaultInjector fault;
        pi::PackageInfoServiceV1 service(&store, &fault);
        pi::PackageInfoRequestV1 request;
        request.requestId = "a11-f02-launcher-package-info";
        request.packageName = packageName;
        request.flags = pi::GET_ACTIVITIES;
        request.userId = 0;
        request.caller.callerId = "launcher";
        request.caller.visibilityScopeDigest = Sha256Hex("launcher-scope");
        request.caller.canSeeAllPackages = true;
        request.expectedGeneration = before.canonical->generation;
        request.expectedCanonicalDigest = before.canonical->canonicalDigest;
        const auto response = service.GetPackageInfo(request);
        REQUIRE(response.verdict == pi::PackageInfoVerdict::PACKAGE_NOT_READY);
        REQUIRE(response.reason == "EXTERNAL_READY_NOT_ESTABLISHED");
        REQUIRE(!response.packageInfo.has_value());
        std::cout << "{\"consumer\":\"PackageInfoService\""
                  << ",\"path\":\"launcher_GET_ACTIVITIES\""
                  << ",\"publicCall\":\"GetPackageInfo\""
                  << ",\"verdict\":"
                  << Json(pi::PackageInfoVerdictName(response.verdict))
                  << ",\"reason\":" << Json(response.reason)
                  << ",\"payloadPresent\":"
                  << (response.packageInfo.has_value() ? "true" : "false")
                  << "}\n";
    } else if (operation == "token") {
        CountingApplicationFacts applicationFacts;
        CountingPathReader pathReader;
        ai::NoApplicationInfoFaultInjector fault;
        ai::ApplicationInfoServiceV1 service(
            &store, &applicationFacts, &pathReader, &fault);
        ai::ApplicationInfoRequestV1 request;
        request.requestId = "a11-f02-token-application-info";
        request.packageName = packageName;
        request.userId = 0;
        request.caller.callerId = "application-info-client";
        request.caller.visibilityScopeDigest =
            Sha256Hex("application-info-scope");
        request.caller.canSeeAllPackages = true;
        request.expectedGeneration = before.canonical->generation;
        request.expectedCanonicalDigest = before.canonical->canonicalDigest;
        const auto response = service.GetApplicationInfo(request);
        REQUIRE(response.verdict == ai::ApplicationInfoVerdict::PACKAGE_NOT_READY);
        REQUIRE(response.reason == "EXTERNAL_READY_NOT_ESTABLISHED");
        REQUIRE(!response.applicationInfo.has_value());
        REQUIRE(response.pathReadbacks.empty());
        REQUIRE(applicationFacts.calls == 0);
        REQUIRE(pathReader.calls == 0);
        std::cout << "{\"consumer\":\"ApplicationInfoService\""
                  << ",\"path\":\"access-token/application-info\""
                  << ",\"publicCall\":\"GetApplicationInfo\""
                  << ",\"verdict\":"
                  << Json(ai::ApplicationInfoVerdictName(response.verdict))
                  << ",\"reason\":" << Json(response.reason)
                  << ",\"hostFactsReads\":" << applicationFacts.calls
                  << ",\"managedPathReads\":" << pathReader.calls
                  << ",\"payloadPresent\":"
                  << (response.applicationInfo.has_value() ? "true" : "false")
                  << "}\n";
    } else if (operation == "process") {
        CountingRuntimeFacts runtimeFacts;
        rp::NoRuntimePathFaultInjector fault;
        rp::RuntimePathDescriptorServiceV1 service(
            &store, &runtimeFacts, &fault);
        rp::RuntimePathRequestV1 request;
        request.requestId = "a11-f02-process-runtime-path";
        request.packageName = packageName;
        request.userId = 0;
        request.expectedGeneration = before.canonical->generation;
        request.expectedCanonicalDigest = before.canonical->canonicalDigest;
        request.abi = "arm64-v8a";
        request.callerScopeDigest = Sha256Hex("process-loader-scope");
        request.callerAuthorized = true;
        const auto response = service.Query(request);
        REQUIRE(response.verdict == rp::RuntimePathVerdict::PACKAGE_NOT_READY);
        REQUIRE(!response.descriptor.has_value());
        REQUIRE(response.observations.empty());
        REQUIRE(!response.classLoaderCreated);
        REQUIRE(runtimeFacts.calls == 0);
        std::cout << "{\"consumer\":\"RuntimePathDescriptorService\""
                  << ",\"path\":\"process-start\""
                  << ",\"publicCall\":\"Query\""
                  << ",\"verdict\":"
                  << Json(rp::RuntimePathVerdictName(response.verdict))
                  << ",\"factsReads\":" << runtimeFacts.calls
                  << ",\"observationCount\":" << response.observations.size()
                  << ",\"descriptorPresent\":"
                  << (response.descriptor.has_value() ? "true" : "false")
                  << ",\"classLoaderCreated\":"
                  << (response.classLoaderCreated ? "true" : "false")
                  << "}\n";
    }

    pt::PackageManagementReadV1 after;
    REQUIRE(store.ReadPackageManagementState(
        0, packageName, &after, &error));
    const std::string afterIdentity = SnapshotIdentity(after);
    const std::string afterDigest = Sha256Hex(afterIdentity);
    REQUIRE(afterIdentity == beforeIdentity);
    REQUIRE(gFailures == 0);
    std::cout << "{\"event\":\"developer_probe_operation_complete\""
              << ",\"operation\":" << Json(operation)
              << ",\"serviceRestartBoundary\":true"
              << ",\"publicConsumerCalls\":"
              << (operation == "fixture_prepare" ? 0 : 1)
              << ",\"aggregateConsumerReadyUsed\":false"
              << ",\"snapshotUnchanged\":"
              << (afterIdentity == beforeIdentity ? "true" : "false")
              << ",\"beforeSnapshotSha256\":" << Json(beforeDigest)
              << ",\"afterSnapshotSha256\":" << Json(afterDigest)
              << ",\"formalVerdict\":\"NOT_ISSUED\""
              << ",\"failureCount\":" << gFailures << "}\n";
    return gFailures == 0 ? 0 : 1;
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 3) {
        std::cerr << "usage: " << argv[0]
                  << " <state-root> <fixture_prepare|query|resolver|launcher"
                     "|token|process>\n";
        return 64;
    }
    const std::string root = argv[1];
    const std::string operation = argv[2];
    if (root.empty() || root.front() != '/' || !IsOperation(operation)) {
        std::cerr << "state-root must be absolute and operation must be typed\n";
        return 64;
    }
    if (mkdir(root.c_str(), 0700) != 0 && errno != EEXIST) {
        std::cerr << "mkdir failed path=" << root
                  << " error=" << std::strerror(errno) << "\n";
        return 73;
    }
    return Run(root, operation);
}
