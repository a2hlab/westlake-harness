#include "application_info_runtime_v1.h"
#include "application_info_runtime_owner_v1.h"
#include "application_info_public_entry_v1.h"

#include "sha256.h"

#include <filesystem>
#include <fstream>
#include <atomic>
#include <cstdlib>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <thread>
#include <unistd.h>

using namespace oh_adapter::application_info;
using namespace oh_adapter::package_transaction;

namespace {

int failures = 0;
#define EXPECT(x) do { if (!(x)) { std::cerr << "FAIL line=" << __LINE__ \
    << " expression=" << #x << "\n"; ++failures; } } while (0)
#define EQUAL(a,b) do { const auto av=(a); const auto bv=(b); \
    if (!(av == bv)) { std::cerr << "FAIL line=" << __LINE__ \
    << " expression=" << #a << " == " << #b << "\n"; ++failures; } } while (0)

std::string Sha(std::string_view value)
{
    uint8_t digest[32];
    sha256(reinterpret_cast<const uint8_t*>(value.data()), value.size(), digest);
    static constexpr char HEX[] = "0123456789abcdef";
    std::string result(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        result[index * 2] = HEX[digest[index] >> 4];
        result[index * 2 + 1] = HEX[digest[index] & 15];
    }
    return result;
}

std::string ReadFile(const std::string& path)
{
    std::ifstream input(path, std::ios::binary);
    return std::string(
        std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>());
}

void Write(const std::string& path, const std::string& value)
{
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    EXPECT(output.good());
    output << value;
}

std::string RuntimeFactsText(const HostApplicationRuntimeFactsV1& facts)
{
    std::ostringstream out;
    out << "schemaVersion=1\n"
        << "packageName=" << facts.packageName << "\n"
        << "userId=" << facts.userId << "\n"
        << "generation=" << facts.generation << "\n"
        << "canonicalDigest=" << facts.canonicalDigest << "\n"
        << "projectionDigest=" << facts.projectionDigest << "\n"
        << "bundleName=" << facts.bundleName << "\n"
        << "appId=" << facts.appId << "\n"
        << "uid=" << facts.uid << "\n"
        << "accessTokenId=" << facts.accessTokenId << "\n"
        << "projectionActive="
        << (facts.projectionActive ? "true" : "false") << "\n"
        << "tokenExternalReady="
        << (facts.tokenExternalReady ? "true" : "false") << "\n"
        << "installed=" << (facts.installed ? "true" : "false") << "\n"
        << "enabled=" << (facts.enabled ? "true" : "false") << "\n"
        << "hidden=" << (facts.hidden ? "true" : "false") << "\n";
    const auto path = [&](const char* prefix,
                          const ManagedPathExpectationV1& value) {
        out << prefix << "=" << value.path << "\n"
            << prefix << "Digest=" << value.expectedDigest << "\n"
            << prefix << "OwnerUid="
            << value.expectedOwnerUid.value_or(0) << "\n";
    };
    path("dataDirectory", facts.dataDirectory);
    path("deviceProtectedDataDirectory",
        facts.deviceProtectedDataDirectory);
    path("credentialProtectedDataDirectory",
        facts.credentialProtectedDataDirectory);
    if (facts.nativeLibraryDirectory.has_value()) {
        path("nativeLibraryDirectory", *facts.nativeLibraryDirectory);
    }
    if (facts.primaryCpuAbi.has_value()) {
        out << "primaryCpuAbi=" << *facts.primaryCpuAbi << "\n";
    }
    return out.str();
}

InstallRequestV1 InstallRequest(const std::string& packageName,
    const std::string& transaction, std::string_view bytes)
{
    InstallRequestV1 request;
    ArtifactDescriptorV1 artifact;
    artifact.artifactId = "base";
    artifact.role = ArtifactRole::BASE;
    artifact.bytes.assign(bytes.begin(), bytes.end());
    artifact.byteLength = bytes.size();
    artifact.sha256 = Sha(bytes);
    request.artifactSet.artifacts.push_back(artifact);
    request.artifactSet.artifactSetDigest =
        ComputeArtifactSetDigest(request.artifactSet);
    auto& manifest = request.manifest;
    manifest.artifactSetDigest = request.artifactSet.artifactSetDigest;
    manifest.parserVersion = "bridge-manifest-facts-v1";
    manifest.packageName = packageName;
    manifest.versionCode = bytes.size();
    manifest.versionName = "v-" + std::to_string(bytes.size());
    manifest.minSdk = 23;
    manifest.targetSdk = 35;
    manifest.applicationClassName = packageName + ".Application";
    manifest.applicationLabel = "Label " + packageName;
    manifest.provenance = {
        {"packageName", artifact.sha256, Sha("manifest:" + packageName), 64},
    };
    request.signing.artifactSetDigest =
        request.artifactSet.artifactSetDigest;
    request.signing.verifierVersion = "host-verifier-v1";
    request.signing.policyProfile = "policy-v1";
    request.signing.verified = true;
    request.signing.schemeVersions = {2};
    request.signing.signerCertificateDigests = {
        Sha("signer:" + packageName),
    };
    request.signing.signerCertificateDerHex = {
        "30820100" + Sha("der:" + packageName),
    };
    request.userId = 0;
    request.expectedPackageName = packageName;
    request.policyRef = "policy-v1";
    request.retryIdentity = "retry:" + transaction;
    request.admission.jobId = "job:" + transaction;
    request.admission.memberId = "member:" + transaction;
    request.admission.transactionId = transaction;
    request.admission.jobRecordVersion = 1;
    request.admission.callerScopeDigest = Sha("caller");
    request.admission.policySnapshotId = request.policyRef;
    request.admission.requestDigest = ComputeInstallRequestDigest(request);
    return request;
}

ApplicationInfoRequestV1 Query(const std::string& id,
    const std::string& packageName, uint64_t flags = 0)
{
    ApplicationInfoRequestV1 request;
    request.requestId = id;
    request.packageName = packageName;
    request.flags = flags;
    request.caller.callerId = "caller:" + id;
    request.caller.visibilityScopeDigest = Sha("scope:" + id);
    request.caller.visiblePackageNames = {packageName};
    return request;
}

class FixtureHostFacts final
    : public HostApplicationRuntimeFactsResolverV1 {
public:
    HostApplicationFactsVerdict Resolve(const std::string& packageName,
        uint32_t userId, uint64_t generation,
        const std::string& canonicalDigest,
        HostApplicationRuntimeFactsV1* facts,
        std::string* error) override
    {
        const auto iterator = values.find(packageName);
        if (notReady) return HostApplicationFactsVerdict::PACKAGE_NOT_READY;
        if (iterator == values.end() || facts == nullptr) {
            if (error != nullptr) *error = "fixture facts absent";
            return HostApplicationFactsVerdict::DATA_INCONSISTENT;
        }
        *facts = iterator->second;
        if (forceGenerationMismatch) ++facts->generation;
        if (forceDigestMismatch) facts->canonicalDigest = Sha("wrong");
        if (facts->userId != userId || generation == 0 ||
            canonicalDigest.empty()) {
            return HostApplicationFactsVerdict::DATA_INCONSISTENT;
        }
        if (error != nullptr) error->clear();
        return HostApplicationFactsVerdict::READY;
    }

    std::map<std::string, HostApplicationRuntimeFactsV1> values;
    bool notReady = false;
    bool forceGenerationMismatch = false;
    bool forceDigestMismatch = false;
};

class OneShotFault final : public ApplicationInfoFaultInjector {
public:
    explicit OneShotFault(std::optional<ApplicationInfoPhase> phase)
        : phase_(phase) {}

    bool InterruptAfter(ApplicationInfoPhase phase) override
    {
        if (!fired_ && phase_ == phase) {
            fired_ = true;
            return true;
        }
        return false;
    }

private:
    std::optional<ApplicationInfoPhase> phase_;
    bool fired_ = false;
};

class FixtureVisibilityResolver final
    : public ApplicationInfoCallerResolverV1 {
public:
    ApplicationInfoCallerVerdictV1 Resolve(
        int32_t callingUid, const std::string& packageName, uint32_t userId,
        oh_adapter::package_query::CallerContextV1* caller,
        std::string* error) override
    {
        if (userId != 0) {
            return ApplicationInfoCallerVerdictV1::NOT_SUPPORTED;
        }
        if (callingUid != 10001 || caller == nullptr) {
            if (error != nullptr) *error = "fixture caller denied";
            return ApplicationInfoCallerVerdictV1::DENIED;
        }
        caller->callerId = "uid:" + std::to_string(callingUid);
        caller->visibilityScopeDigest =
            Sha("scope:" + std::to_string(callingUid));
        caller->visiblePackageNames = {packageName};
        return ApplicationInfoCallerVerdictV1::VISIBLE;
    }
};

void SeedPackage(FilePackageStore* store,
    PackageTransactionCoordinator* coordinator,
    FixtureHostFacts* hostFacts, const std::string& root,
    const std::string& packageName, const std::string& transaction,
    std::string_view bytes)
{
    const auto receipt =
        coordinator->Install(InstallRequest(packageName, transaction, bytes));
    EQUAL(receipt.verdict, InstallVerdict::COMMITTED);
    EXPECT(receipt.generation.has_value());
    EXPECT(receipt.durableRecordDigest.has_value());
    std::string error;
    EXPECT(store->SeedHostProjectionForFixture(0, packageName,
        receipt.generation.value_or(0),
        receipt.durableRecordDigest.value_or(""),
        HostProjectionState::ACTIVE, PublicationState::EXTERNAL_READY,
        &error));
    PackageManagementReadV1 read;
    EXPECT(store->ReadPackageManagementState(0, packageName, &read, &error));
    EXPECT(read.canonical.has_value());

    const std::string packageRoot =
        root + "/runtime/" + Sha(packageName).substr(0, 16);
    const std::string dataDirectory = packageRoot + "/data";
    const std::string deviceDataDirectory = packageRoot + "/data-de";
    const std::string credentialDataDirectory = packageRoot + "/data-ce";
    const std::string nativeDirectory = packageRoot + "/lib";
    std::filesystem::create_directories(dataDirectory);
    std::filesystem::create_directories(deviceDataDirectory);
    std::filesystem::create_directories(credentialDataDirectory);
    std::filesystem::create_directories(nativeDirectory);
    Write(dataDirectory + "/marker", "mutable-user-data");
    Write(deviceDataDirectory + "/marker", "device-protected-data");
    Write(credentialDataDirectory + "/marker", "credential-protected-data");
    Write(nativeDirectory + "/libfixture.so", "native:" + packageName);

    HostApplicationRuntimeFactsV1 facts;
    facts.packageName = packageName;
    facts.userId = 0;
    facts.generation = read.canonical->generation;
    facts.canonicalDigest = read.canonical->canonicalDigest;
    facts.projectionDigest = Sha("projection:" + packageName);
    facts.bundleName = "bundle:" + packageName;
    facts.appId = "app:" + Sha(packageName).substr(0, 12);
    facts.uid = static_cast<int32_t>(getuid());
    facts.accessTokenId =
        static_cast<uint64_t>(100000 + hostFacts->values.size());
    facts.projectionActive = true;
    facts.tokenExternalReady = true;
    facts.dataDirectory = {
        ManagedPathKind::DATA_DIRECTORY,
        dataDirectory,
        ComputeManagedDirectoryDigestV1(dataDirectory),
        static_cast<uint32_t>(getuid()),
    };
    facts.deviceProtectedDataDirectory = {
        ManagedPathKind::DATA_DIRECTORY,
        deviceDataDirectory,
        ComputeManagedDirectoryDigestV1(deviceDataDirectory),
        static_cast<uint32_t>(getuid()),
    };
    facts.credentialProtectedDataDirectory = {
        ManagedPathKind::DATA_DIRECTORY,
        credentialDataDirectory,
        ComputeManagedDirectoryDigestV1(credentialDataDirectory),
        static_cast<uint32_t>(getuid()),
    };
    facts.nativeLibraryDirectory = ManagedPathExpectationV1 {
        ManagedPathKind::NATIVE_LIBRARY_DIRECTORY,
        nativeDirectory,
        ComputeManagedDirectoryDigestV1(nativeDirectory),
        static_cast<uint32_t>(getuid()),
    };
    facts.primaryCpuAbi =
        packageName.find("alpha") != std::string::npos
            ? std::optional<std::string>("arm64-v8a")
            : std::optional<std::string>("x86_64");
    hostFacts->values[packageName] = std::move(facts);
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2) return 2;
    const std::string root = argv[1];
    const std::string storeRoot = root + "/store";
    const std::string fileRoot = root + "/files";
    const std::string alpha = "org.fixture.alpha";
    const std::string beta = "net.sample.beta";
    NoFaultInjector installFault;
    FixtureHostFacts hostFacts;
    {
        FilePackageStore store(storeRoot);
        PosixPackageFileStager stager(fileRoot);
        PackageTransactionCoordinator coordinator(
            &store, &stager, &installFault);
        SeedPackage(&store, &coordinator, &hostFacts, root, alpha,
            "tx-alpha", "alpha-apk-content");
        SeedPackage(&store, &coordinator, &hostFacts, root, beta,
            "tx-beta", "different-beta-content");
    }

    const std::string eventLog = storeRoot + "/events.v1.log";
    const std::string beforeDigest = Sha(ReadFile(eventLog));
    auto reopened = std::make_unique<FilePackageStore>(storeRoot);
    NoApplicationInfoFaultInjector noFault;
    PosixManagedPathReaderV1 pathReader;
    ApplicationInfoServiceV1 service(
        reopened.get(), &hostFacts, &pathReader, &noFault);
    std::ostringstream receipts;
    size_t positive = 0;
    size_t negative = 0;
    size_t failure = 0;

    const auto ready = service.GetApplicationInfo(Query("P01-alpha", alpha));
    EQUAL(ready.verdict, ApplicationInfoVerdict::READY);
    EXPECT(ready.applicationInfo.has_value());
    EQUAL(ready.applicationInfo->packageName, alpha);
    EQUAL(ready.applicationInfo->label, "Label " + alpha);
    EQUAL(ready.applicationInfo->sourceDir,
        ready.applicationInfo->publicSourceDir);
    EQUAL(ready.applicationInfo->dataDir,
        hostFacts.values[alpha].dataDirectory.path);
    EQUAL(ready.applicationInfo->nativeLibraryDir.value_or(""),
        hostFacts.values[alpha].nativeLibraryDirectory->path);
    EQUAL(ready.applicationInfo->uid,
        static_cast<int32_t>(getuid()));
    EQUAL(ready.applicationInfo->deviceProtectedDataDir,
        hostFacts.values[alpha].deviceProtectedDataDirectory.path);
    EQUAL(ready.applicationInfo->credentialProtectedDataDir,
        hostFacts.values[alpha].credentialProtectedDataDirectory.path);
    EQUAL(ready.pathReadbacks.size(), static_cast<size_t>(5));
    receipts << ApplicationInfoResponseJson(ready) << "\n";
    ++positive;

    const auto replay = service.GetApplicationInfo(Query("P02-replay", alpha));
    const auto replayAgain =
        service.GetApplicationInfo(Query("P02-replay", alpha));
    EQUAL(ApplicationInfoResponseJson(replay),
        ApplicationInfoResponseJson(replayAgain));
    const auto second =
        service.GetApplicationInfo(Query("P02-second-package", beta));
    EQUAL(second.verdict, ApplicationInfoVerdict::READY);
    EXPECT(second.applicationInfo.has_value());
    EXPECT(second.canonicalDigest != ready.canonicalDigest);
    EXPECT(second.applicationInfo->sourceDir !=
        ready.applicationInfo->sourceDir);
    EXPECT(second.applicationInfo->label !=
        ready.applicationInfo->label);
    receipts << ApplicationInfoResponseJson(replay) << "\n"
        << ApplicationInfoResponseJson(second) << "\n";
    positive += 3;

    auto hiddenRequest = Query("N01-caller-hidden", alpha);
    hiddenRequest.caller.visiblePackageNames.clear();
    const auto callerHidden = service.GetApplicationInfo(hiddenRequest);
    EQUAL(callerHidden.verdict,
        ApplicationInfoVerdict::PACKAGE_NOT_VISIBLE);
    EXPECT(!callerHidden.applicationInfo.has_value());
    ++negative;

    hostFacts.values[alpha].hidden = true;
    EQUAL(service.GetApplicationInfo(Query("N01-hidden", alpha)).verdict,
        ApplicationInfoVerdict::PACKAGE_NOT_VISIBLE);
    hostFacts.values[alpha].hidden = false;
    hostFacts.values[alpha].enabled = false;
    EQUAL(service.GetApplicationInfo(Query("N01-disabled", alpha)).verdict,
        ApplicationInfoVerdict::PACKAGE_NOT_VISIBLE);
    const auto matchedDisabled = service.GetApplicationInfo(
        Query("P02-match-disabled", alpha, MATCH_DISABLED_COMPONENTS));
    EQUAL(matchedDisabled.verdict, ApplicationInfoVerdict::READY);
    EXPECT(!matchedDisabled.applicationInfo->enabled);
    hostFacts.values[alpha].enabled = true;
    negative += 2;
    ++positive;

    EQUAL(service.GetApplicationInfo(
        Query("N01-missing", "org.fixture.missing")).verdict,
        ApplicationInfoVerdict::PACKAGE_NOT_FOUND);
    EQUAL(service.GetApplicationInfo(
        Query("N01-unsupported", alpha, 1ULL << 63)).verdict,
        ApplicationInfoVerdict::NOT_SUPPORTED);
    auto secondary = Query("N01-secondary", alpha);
    secondary.userId = 10;
    EQUAL(service.GetApplicationInfo(secondary).verdict,
        ApplicationInfoVerdict::NOT_SUPPORTED);
    negative += 3;

    auto staleGeneration = Query("N02-stale-generation", alpha);
    staleGeneration.expectedGeneration = ready.generation + 1;
    EQUAL(service.GetApplicationInfo(staleGeneration).verdict,
        ApplicationInfoVerdict::DATA_INCONSISTENT);
    auto staleDigest = Query("N02-stale-digest", alpha);
    staleDigest.expectedCanonicalDigest = Sha("wrong-canonical");
    EQUAL(service.GetApplicationInfo(staleDigest).verdict,
        ApplicationInfoVerdict::DATA_INCONSISTENT);
    hostFacts.forceGenerationMismatch = true;
    EQUAL(service.GetApplicationInfo(
        Query("N02-host-generation", alpha)).verdict,
        ApplicationInfoVerdict::DATA_INCONSISTENT);
    hostFacts.forceGenerationMismatch = false;
    hostFacts.forceDigestMismatch = true;
    EQUAL(service.GetApplicationInfo(
        Query("N02-host-digest", alpha)).verdict,
        ApplicationInfoVerdict::DATA_INCONSISTENT);
    hostFacts.forceDigestMismatch = false;
    negative += 4;

    hostFacts.notReady = true;
    EQUAL(service.GetApplicationInfo(
        Query("F01-host-not-ready", alpha)).verdict,
        ApplicationInfoVerdict::PACKAGE_NOT_READY);
    hostFacts.notReady = false;
    hostFacts.values[alpha].projectionActive = false;
    EQUAL(service.GetApplicationInfo(
        Query("F01-projection-prepared", alpha)).verdict,
        ApplicationInfoVerdict::PACKAGE_NOT_READY);
    hostFacts.values[alpha].projectionActive = true;
    hostFacts.values[alpha].tokenExternalReady = false;
    EQUAL(service.GetApplicationInfo(
        Query("F01-token-not-ready", alpha)).verdict,
        ApplicationInfoVerdict::PACKAGE_NOT_READY);
    hostFacts.values[alpha].tokenExternalReady = true;
    failure += 3;

    for (ApplicationInfoPhase phase : {
             ApplicationInfoPhase::SNAPSHOT_FROZEN,
             ApplicationInfoPhase::PATHS_READ_BACK,
             ApplicationInfoPhase::FIELDS_PROJECTED,
             ApplicationInfoPhase::RESPONSE_SERIALIZED}) {
        OneShotFault fault(phase);
        ApplicationInfoServiceV1 interrupted(
            reopened.get(), &hostFacts, &pathReader, &fault);
        const auto interruptedResult = interrupted.GetApplicationInfo(
            Query("F01-interrupted", alpha));
        EQUAL(interruptedResult.verdict,
            ApplicationInfoVerdict::INTERRUPTED);
        EXPECT(!interruptedResult.applicationInfo.has_value());
        receipts << ApplicationInfoResponseJson(interruptedResult) << "\n";
        const auto recovered =
            service.GetApplicationInfo(Query("F02-restart-replay", alpha));
        EQUAL(recovered.verdict, ApplicationInfoVerdict::READY);
        EQUAL(recovered.canonicalDigest, ready.canonicalDigest);
        ++failure;
    }

    auto badDataFacts = hostFacts.values[alpha].dataDirectory.expectedDigest;
    hostFacts.values[alpha].dataDirectory.expectedDigest = Sha("wrong-path");
    const auto badData =
        service.GetApplicationInfo(Query("F01-data-readback", alpha));
    EQUAL(badData.verdict,
        ApplicationInfoVerdict::PATH_READBACK_FAILED);
    EXPECT(!badData.applicationInfo.has_value());
    EXPECT(badData.pathReadbacks.empty());
    hostFacts.values[alpha].dataDirectory.expectedDigest = badDataFacts;
    ++failure;

    const auto realDataFacts = hostFacts.values[alpha].dataDirectory;
    const std::string dataSymlink =
        root + "/runtime/data-symlink-attack";
    std::filesystem::create_directory_symlink(
        realDataFacts.path, dataSymlink);
    hostFacts.values[alpha].dataDirectory.path = dataSymlink;
    hostFacts.values[alpha].dataDirectory.expectedDigest =
        ComputeManagedDirectoryDigestV1(dataSymlink);
    EQUAL(service.GetApplicationInfo(
        Query("F01-data-symlink", alpha)).verdict,
        ApplicationInfoVerdict::PATH_READBACK_FAILED);
    hostFacts.values[alpha].dataDirectory = realDataFacts;
    std::filesystem::remove(dataSymlink);
    ++failure;

    PackageManagementReadV1 alphaRead;
    std::string error;
    EXPECT(reopened->ReadPackageManagementState(0, alpha, &alphaRead, &error));
    EXPECT(alphaRead.canonical.has_value());
    const std::string originalApk =
        ReadFile(alphaRead.canonical->managedFiles.baseCodePath);
    Write(alphaRead.canonical->managedFiles.baseCodePath, "tampered-apk");
    EQUAL(service.GetApplicationInfo(
        Query("F01-base-digest", alpha)).verdict,
        ApplicationInfoVerdict::PATH_READBACK_FAILED);
    Write(alphaRead.canonical->managedFiles.baseCodePath, originalApk);
    ++failure;

    const std::string unconfigured = QueryApplicationInfoRuntimeJsonV1(
        "N01-runtime-unconfigured", alpha, 0, 0, 10001);
    EXPECT(unconfigured.find("APPLICATION_INFO_RUNTIME_NOT_CONFIGURED") !=
        std::string::npos);
    FixtureVisibilityResolver visibility;
    EXPECT(ConfigureApplicationInfoRuntimeV1(reopened.get(), &visibility,
        &hostFacts, &pathReader, &noFault, &error));
    const std::string runtimeReady = QueryApplicationInfoRuntimeJsonV1(
        "P02-android-entry", alpha, 0, 0, 10001);
    EXPECT(runtimeReady.find("\"verdict\":\"READY\"") !=
        std::string::npos);
    const std::string runtimeDenied = QueryApplicationInfoRuntimeJsonV1(
        "N01-android-entry-denied", alpha, 0, 0, 20002);
    EXPECT(runtimeDenied.find("\"verdict\":\"PACKAGE_NOT_VISIBLE\"") !=
        std::string::npos);
    ClearApplicationInfoRuntimeV1();
    reopened.reset();
    receipts << runtimeReady << "\n" << runtimeDenied << "\n";
    ++positive;
    negative += 2;

    const std::string factsRoot = root + "/runtime-facts";
    FileHostApplicationRuntimeFactsResolverV1 fileFacts(factsRoot);
    for (const auto& [packageName, facts] : hostFacts.values) {
        const std::string factsPath = fileFacts.FactsPath(packageName, 0);
        std::filesystem::create_directories(
            std::filesystem::path(factsPath).parent_path());
        Write(factsPath, RuntimeFactsText(facts));
    }
    ApplicationInfoRuntimeOwnerV1 owner;
    EXPECT(owner.Start({storeRoot, factsRoot}, &error));
    EXPECT(owner.IsStarted());
    const std::string ownerReady = QueryCanonicalApplicationInfoEntryV1(
        alpha, 0, 0,
        static_cast<int32_t>(getuid()));
    EXPECT(ownerReady.find("\"verdict\":\"READY\"") != std::string::npos);
    const std::string ownerMissing = QueryCanonicalApplicationInfoEntryV1(
        "org.fixture.absent", 0, 0, 4242);
    EXPECT(ownerMissing.find("\"verdict\":\"PACKAGE_NOT_FOUND\"") !=
        std::string::npos);
    const std::string betaFactsPath = fileFacts.FactsPath(beta, 0);
    const std::string betaFactsText = ReadFile(betaFactsPath);
    std::filesystem::remove(betaFactsPath);
    const std::string ownerFactsNotReady =
        QueryCanonicalApplicationInfoEntryV1(beta, 0, 0, 4242);
    EXPECT(ownerFactsNotReady.find("\"verdict\":\"PACKAGE_NOT_READY\"") !=
        std::string::npos);
    Write(betaFactsPath, betaFactsText);
    const std::string ownerSecondary =
        QueryCanonicalApplicationInfoEntryV1(alpha, 0, 10, 4242);
    EXPECT(ownerSecondary.find("\"verdict\":\"NOT_SUPPORTED\"") !=
        std::string::npos);

    std::atomic<bool> keepQuerying {true};
    std::atomic<size_t> lifecycleQueries {0};
    std::atomic<bool> lifecycleMalformed {false};
    std::thread reader([&]() {
        while (keepQuerying.load()) {
            const std::string response =
                QueryCanonicalApplicationInfoEntryV1(alpha, 0, 0,
                static_cast<int32_t>(getuid()));
            if (response.find("\"verdict\":\"READY\"") ==
                    std::string::npos &&
                response.find("APPLICATION_INFO_RUNTIME_NOT_CONFIGURED") ==
                    std::string::npos) {
                lifecycleMalformed.store(true);
            }
            ++lifecycleQueries;
        }
    });
    while (lifecycleQueries.load() == 0) std::this_thread::yield();
    owner.Stop();
    keepQuerying.store(false);
    reader.join();
    EXPECT(!lifecycleMalformed.load());
    EXPECT(!owner.IsStarted());
    const std::string ownerStopped = QueryCanonicalApplicationInfoEntryV1(
        alpha, 0, 0,
        static_cast<int32_t>(getuid()));
    EXPECT(ownerStopped.find("APPLICATION_INFO_RUNTIME_NOT_CONFIGURED") !=
        std::string::npos);
    EXPECT(owner.Start({storeRoot, factsRoot}, &error));
    const std::string ownerRestarted = QueryCanonicalApplicationInfoEntryV1(
        beta, 0, 0,
        static_cast<int32_t>(getuid()));
    EXPECT(ownerRestarted.find("\"verdict\":\"READY\"") !=
        std::string::npos);
    owner.Stop();
    receipts << ownerReady << "\n" << ownerMissing << "\n"
        << ownerFactsNotReady << "\n" << ownerSecondary << "\n"
        << ownerStopped << "\n"
        << ownerRestarted << "\n";
    positive += 2;
    negative += 2;
    failure += 3;

    const std::string productStateRoot = root + "/product-state";
    EXPECT(setenv(
        "OH_ADAPTER_FN01_STATE_ROOT", productStateRoot.c_str(), 1) == 0);
    // The public entry lazily retries the idempotent product owner so an
    // unavailable projection at process bootstrap is not a permanent failure.
    const std::string productConfigured =
        QueryCanonicalApplicationInfoEntryV1(
            "org.fixture.product-missing", 0, 0,
            static_cast<int32_t>(getuid()));
    EXPECT(productConfigured.find(
        "APPLICATION_INFO_RUNTIME_NOT_CONFIGURED") != std::string::npos);
    {
        FilePackageStore productWriter(
            productStateRoot + "/package-store-v1");
        EXPECT(productWriter.Open(&error));
    }
    const std::string productReadyMissing =
        QueryCanonicalApplicationInfoEntryV1(
            "org.fixture.product-missing", 0, 0,
            static_cast<int32_t>(getuid()));
    EXPECT(productReadyMissing.find("\"verdict\":\"PACKAGE_NOT_FOUND\"") !=
        std::string::npos);
    StopProductApplicationInfoRuntimeV1();
    EXPECT(unsetenv("OH_ADAPTER_FN01_STATE_ROOT") == 0);

    // A query owner must not retain either the writer lease or a stale
    // bootstrap snapshot.  A separate mutation owner may append after the
    // reader starts, and the next read must replay that new durable record.
    const std::string refreshStoreRoot = root + "/refresh-store";
    const std::string refreshFilesRoot = root + "/refresh-files";
    const std::string refreshPackage = "org.fixture.refresh";
    FixtureHostFacts refreshHostFacts;
    {
        FilePackageStore refreshWriter(refreshStoreRoot);
        PosixPackageFileStager refreshStager(refreshFilesRoot);
        PackageTransactionCoordinator refreshCoordinator(
            &refreshWriter, &refreshStager, &installFault);
        SeedPackage(&refreshWriter, &refreshCoordinator, &refreshHostFacts,
            root + "/refresh-runtime", refreshPackage, "tx-refresh",
            "refresh-apk-content");
    }
    FilePackageStore refreshReader(refreshStoreRoot);
    EXPECT(refreshReader.OpenReadOnly(&error));
    PackageManagementReadV1 refreshBefore;
    EXPECT(refreshReader.ReadPackageManagementState(
        0, refreshPackage, &refreshBefore, &error));
    EXPECT(refreshBefore.canonical.has_value());
    EXPECT(refreshBefore.projection.has_value());
    {
        FilePackageStore refreshWriter(refreshStoreRoot);
        EXPECT(refreshWriter.Open(&error));
        EXPECT(refreshWriter.SeedHostProjectionForFixture(0, refreshPackage,
            refreshBefore.canonical->generation,
            refreshBefore.canonical->canonicalDigest,
            HostProjectionState::ACTIVE, PublicationState::EXTERNAL_READY,
            &error));
    }
    PackageManagementReadV1 refreshAfter;
    const bool refreshRead = refreshReader.ReadPackageManagementState(
        0, refreshPackage, &refreshAfter, &error);
    if (!refreshRead) {
        std::cerr << "refresh reader failed: " << error << "\n";
    }
    EXPECT(refreshRead);
    EXPECT(refreshAfter.catalogRevision > refreshBefore.catalogRevision);
    EXPECT(refreshAfter.projection.has_value());
    EQUAL(refreshAfter.projection->state, HostProjectionState::ACTIVE);
    EXPECT(refreshAfter.publicationToken.has_value());
    EQUAL(refreshAfter.publicationToken->state,
        PublicationState::EXTERNAL_READY);
    ++positive;

    const std::string afterDigest = Sha(ReadFile(eventLog));
    EQUAL(beforeDigest, afterDigest);
    Write(root + "/responses.jsonl", receipts.str());
    Write(root + "/before-after.json",
        "{\"canonicalMutation\":false,\"eventLogAfter\":\"" +
        afterDigest + "\",\"eventLogBefore\":\"" + beforeDigest +
        "\",\"queryDurableWrite\":false,\"reopenedStore\":true}\n");
    Write(root + "/expected-matrix.json",
        "{\"aospSource\":\"AOSP android-14.0.0_r1 "
        "ComputerEngine.getApplicationInfo/PackageInfoUtils."
        "generateApplicationInfo\",\"cases\":[\"P01\",\"P02\",\"N01\","
        "\"N02\",\"F01\",\"F02\"],\"directoryDigest\":"
        "\"sha256(managed-directory-v1\\\\n+exactPath)\","
        "\"productPackageConstants\":[]}\n");

    if (failures != 0) {
        std::cerr << "FAIL fn01_a05_application_info failures="
            << failures << "\n";
        return 1;
    }
    std::cout << "PASS fn01_a05_application_info positive=" << positive
        << " negative=" << negative << " failure=" << failure
        << " multi_package=true generation_join=true"
        << " path_readback=true restart_replay=true"
        << " product_hardcoding=none runtime_pass=false\n";
    return 0;
}
