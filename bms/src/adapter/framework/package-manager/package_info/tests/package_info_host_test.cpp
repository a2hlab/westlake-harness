#include "package_info_v1.h"
#include "package_info_runtime_v1.h"

#include "sha256.h"

#include <fstream>
#include <iostream>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>

using namespace oh_adapter::package_info;
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
    manifest.versionCode = 42;
    manifest.versionName = "4.2";
    manifest.minSdk = 23;
    manifest.targetSdk = 35;
    manifest.applicationClassName = packageName + ".Application";
    manifest.applicationLabel = "Fixture " + packageName;
    manifest.components = {
        {"activity", packageName + ".MainActivity", true},
        {"activity-alias", packageName + ".Launcher", true},
        {"receiver", packageName + ".BootReceiver", false},
        {"service", packageName + ".SyncService", false},
        {"provider", packageName + ".DataProvider", true},
    };
    manifest.requestedPermissions = {
        "android.permission.INTERNET", "android.permission.CAMERA",
    };
    manifest.declaredPermissions = {packageName + ".permission.INTERNAL"};
    manifest.provenance = {
        {"packageName", artifact.sha256, Sha("manifest:" + packageName), 128},
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

PackageInfoRequestV1 Query(const std::string& id,
    const std::string& packageName, uint64_t flags)
{
    PackageInfoRequestV1 request;
    request.requestId = id;
    request.packageName = packageName;
    request.flags = flags;
    request.caller.callerId = "caller:" + id;
    request.caller.visibilityScopeDigest = Sha("visibility:" + id);
    request.caller.visiblePackageNames = {packageName};
    return request;
}

void Seed(FilePackageStore* store, PackageTransactionCoordinator* coordinator,
    const std::string& packageName, const std::string& transaction,
    std::string_view bytes, bool externalReady)
{
    const auto receipt =
        coordinator->Install(InstallRequest(packageName, transaction, bytes));
    EQUAL(receipt.verdict, InstallVerdict::COMMITTED);
    EXPECT(receipt.generation.has_value());
    EXPECT(receipt.durableRecordDigest.has_value());
    if (externalReady) {
        std::string error;
        EXPECT(store->SeedHostProjectionForFixture(0, packageName,
            receipt.generation.value_or(0),
            receipt.durableRecordDigest.value_or(""),
            HostProjectionState::ACTIVE, PublicationState::EXTERNAL_READY,
            &error));
    }
}

class OneShotFault final : public PackageInfoFaultInjector {
public:
    explicit OneShotFault(std::optional<PackageInfoPhase> phase)
        : phase_(phase) {}
    bool InterruptAfter(PackageInfoPhase phase) override
    {
        if (!fired_ && phase_ == phase) {
            fired_ = true;
            return true;
        }
        return false;
    }
private:
    std::optional<PackageInfoPhase> phase_;
    bool fired_ = false;
};

class FixtureVisibilityResolver final : public CallerVisibilityResolverV1 {
public:
    bool Resolve(int32_t callingUid, const std::string& packageName,
        oh_adapter::package_query::CallerContextV1* caller,
        std::string* error) override
    {
        if (callingUid != 10001) {
            if (error != nullptr) *error = "fixture caller denied";
            return false;
        }
        caller->callerId = "uid:" + std::to_string(callingUid);
        caller->visibilityScopeDigest =
            Sha("scope:" + std::to_string(callingUid));
        caller->visiblePackageNames = {packageName};
        return true;
    }
};

void Write(const std::string& path, const std::string& value)
{
    std::ofstream output(path, std::ios::trunc);
    EXPECT(output.good());
    output << value;
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2) return 2;
    const std::string root = argv[1];
    const std::string storePath = root + "/store";
    const std::string filesPath = root + "/files";
    const std::string firstName = "org.fixture.alpha";
    const std::string secondName = "net.sample.beta";
    NoFaultInjector noInstallFault;
    {
        FilePackageStore store(storePath);
        PosixPackageFileStager stager(filesPath);
        PackageTransactionCoordinator coordinator(
            &store, &stager, &noInstallFault);
        Seed(&store, &coordinator, firstName, "tx-alpha",
            "alpha-apk-content", true);
        Seed(&store, &coordinator, secondName, "tx-beta",
            "different-beta-content", true);
        Seed(&store, &coordinator, "org.fixture.pending", "tx-pending",
            "pending-content", false);
    }

    FilePackageStore reopened(storePath);
    NoPackageInfoFaultInjector noFault;
    PackageInfoServiceV1 service(&reopened, &noFault);
    std::ostringstream receipts;
    size_t positive = 0;
    size_t negative = 0;
    size_t failure = 0;

    auto base = service.GetPackageInfo(Query("P01-base", firstName, 0));
    EQUAL(base.verdict, PackageInfoVerdict::READY);
    EXPECT(base.packageInfo.has_value());
    EXPECT(!base.packageInfo->activities.has_value());
    EXPECT(!base.packageInfo->requestedPermissions.has_value());
    EXPECT(!base.packageInfo->signingCertificateDigests.has_value());
    receipts << PackageInfoResponseJson(base) << "\n";
    ++positive;

    const uint64_t allFlags = GET_ACTIVITIES | GET_RECEIVERS | GET_SERVICES |
        GET_PROVIDERS | GET_PERMISSIONS | GET_SIGNING_CERTIFICATES;
    auto all = service.GetPackageInfo(
        Query("P01-flags-matrix", firstName, allFlags));
    EQUAL(all.verdict, PackageInfoVerdict::READY);
    EQUAL(all.packageInfo->activities->size(), static_cast<size_t>(2));
    EQUAL(all.packageInfo->receivers->size(), static_cast<size_t>(1));
    EQUAL(all.packageInfo->services->size(), static_cast<size_t>(1));
    EQUAL(all.packageInfo->providers->size(), static_cast<size_t>(1));
    EQUAL(all.packageInfo->requestedPermissions->size(),
        static_cast<size_t>(2));
    EQUAL(all.packageInfo->signingCertificateDigests->size(),
        static_cast<size_t>(1));
    receipts << PackageInfoResponseJson(all) << "\n";
    ++positive;

    auto replay = service.GetPackageInfo(
        Query("P01-flags-matrix", firstName, allFlags));
    EQUAL(PackageInfoResponseJson(all), PackageInfoResponseJson(replay));
    auto second = service.GetPackageInfo(
        Query("P02-second-content", secondName, GET_ACTIVITIES));
    EQUAL(second.verdict, PackageInfoVerdict::READY);
    EXPECT(second.canonicalDigest != all.canonicalDigest);
    receipts << PackageInfoResponseJson(second) << "\n";
    positive += 2;

    auto hiddenRequest = Query("N01-hidden", firstName, allFlags);
    hiddenRequest.caller.visiblePackageNames.clear();
    auto hidden = service.GetPackageInfo(hiddenRequest);
    EQUAL(hidden.verdict, PackageInfoVerdict::PACKAGE_NOT_VISIBLE);
    EXPECT(!hidden.packageInfo.has_value());
    receipts << PackageInfoResponseJson(hidden) << "\n";
    ++negative;

    auto unsupported = Query("N01-unsupported-flag", firstName, 1ULL << 63);
    EQUAL(service.GetPackageInfo(unsupported).verdict,
        PackageInfoVerdict::NOT_SUPPORTED);
    auto secondary = Query("N01-secondary-user", firstName, 0);
    secondary.userId = 10;
    EQUAL(service.GetPackageInfo(secondary).verdict,
        PackageInfoVerdict::NOT_SUPPORTED);
    negative += 2;

    auto stale = Query("N02-stale-generation", firstName, allFlags);
    stale.expectedGeneration = all.generation + 1;
    EQUAL(service.GetPackageInfo(stale).verdict,
        PackageInfoVerdict::STALE_GENERATION);
    auto digest = Query("N02-digest-mismatch", firstName, allFlags);
    digest.expectedCanonicalDigest = Sha("wrong");
    EQUAL(service.GetPackageInfo(digest).verdict,
        PackageInfoVerdict::STALE_GENERATION);
    auto missing = service.GetPackageInfo(
        Query("N02-missing", "org.fixture.absent", 0));
    EQUAL(missing.verdict, PackageInfoVerdict::PACKAGE_NOT_FOUND);
    auto pending = service.GetPackageInfo(
        Query("N02-pending", "org.fixture.pending", 0));
    EQUAL(pending.verdict, PackageInfoVerdict::PACKAGE_NOT_READY);
    negative += 4;

    for (PackageInfoPhase phase : {PackageInfoPhase::SNAPSHOT_FROZEN,
             PackageInfoPhase::FIELDS_PROJECTED,
             PackageInfoPhase::RESPONSE_SERIALIZED}) {
        OneShotFault fault(phase);
        PackageInfoServiceV1 interrupted(&reopened, &fault);
        const auto result = interrupted.GetPackageInfo(
            Query("F01-interrupted", firstName, allFlags));
        EQUAL(result.verdict, PackageInfoVerdict::INTERRUPTED);
        EXPECT(!result.packageInfo.has_value());
        receipts << PackageInfoResponseJson(result) << "\n";
        const auto recovered = service.GetPackageInfo(
            Query("F02-replay", firstName, allFlags));
        EQUAL(recovered.verdict, PackageInfoVerdict::READY);
        EQUAL(recovered.canonicalDigest, all.canonicalDigest);
        ++failure;
    }

    const std::string unconfigured = QueryPackageInfoRuntimeJsonV1(
        "N01-runtime-unconfigured", firstName, 0, 0, 10001);
    EXPECT(unconfigured.find("PACKAGE_INFO_RUNTIME_NOT_CONFIGURED") !=
        std::string::npos);
    FixtureVisibilityResolver visibility;
    std::string configureError;
    EXPECT(ConfigurePackageInfoRuntimeV1(
        &reopened, &visibility, &noFault, &configureError));
    const std::string androidEntryReady = QueryPackageInfoRuntimeJsonV1(
        "P02-android-entry", firstName, allFlags, 0, 10001);
    EXPECT(androidEntryReady.find("\"verdict\":\"READY\"") !=
        std::string::npos);
    const std::string androidEntryDenied = QueryPackageInfoRuntimeJsonV1(
        "N01-android-entry-denied", firstName, allFlags, 0, 20002);
    EXPECT(androidEntryDenied.find("\"verdict\":\"PACKAGE_NOT_VISIBLE\"") !=
        std::string::npos);
    ClearPackageInfoRuntimeV1();
    receipts << androidEntryReady << "\n" << androidEntryDenied << "\n";
    ++positive;
    negative += 2;

    Write(root + "/responses.jsonl", receipts.str());
    Write(root + "/aosp-flags-oracle.json",
        "{\"generator\":\"fn01-a04-host-oracle-v1\","
        "\"source\":\"AOSP android-14.0.0_r1 "
        "PackageInfoUtils.java:239-343\","
        "\"matrix\":{\"GET_ACTIVITIES\":[\"activity\",\"activity-alias\"],"
        "\"GET_RECEIVERS\":[\"receiver\"],"
        "\"GET_SERVICES\":[\"service\"],"
        "\"GET_PROVIDERS\":[\"provider\"],"
        "\"GET_PERMISSIONS\":[\"requestedPermissions\"],"
        "\"GET_SIGNING_CERTIFICATES\":[\"signingCertificateDigests\"]}}\n");
    Write(root + "/before-after.json",
        "{\"canonicalMutation\":false,\"projectionMutation\":false,"
        "\"dtoDurableWrite\":false,\"reopenedStore\":true}\n");

    if (failures != 0) {
        std::cerr << "FAIL fn01_a04_package_info failures=" << failures << "\n";
        return 1;
    }
    std::cout << "PASS fn01_a04_package_info positive=" << positive
        << " negative=" << negative << " failure=" << failure
        << " flags_omission=true caller_visibility=true"
        << " generation_join=true product_hardcoding=none runtime_pass=false\n";
    return 0;
}
