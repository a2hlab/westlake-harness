#include "runtime_path_descriptor_v1.h"

#include "sha256.h"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

using namespace oh_adapter::package_transaction;
using namespace oh_adapter::runtime_path_descriptor;
namespace fs = std::filesystem;

namespace {

int gFailures = 0;
std::ofstream gResponses;
std::ofstream gConsumer;

#define EXPECT_TRUE(condition)                                                   \
    do {                                                                         \
        if (!(condition)) {                                                       \
            std::cerr << "FAIL " << __FILE__ << ":" << __LINE__ << " "         \
                      << #condition << "\n";                                     \
            ++gFailures;                                                          \
        }                                                                         \
    } while (0)

#define EXPECT_EQ(left, right)                                                    \
    do {                                                                         \
        const auto leftValue = (left);                                             \
        const auto rightValue = (right);                                           \
        if (!(leftValue == rightValue)) {                                          \
            std::cerr << "FAIL " << __FILE__ << ":" << __LINE__ << " "         \
                      << #left << " != " << #right << "\n";                       \
            ++gFailures;                                                          \
        }                                                                         \
    } while (0)

std::string Sha256Hex(std::string_view value)
{
    unsigned char digest[32]{};
    sha256(reinterpret_cast<const unsigned char*>(value.data()), value.size(),
        digest);
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        result[index * 2] = kHex[digest[index] >> 4];
        result[index * 2 + 1] = kHex[digest[index] & 0x0f];
    }
    return result;
}

std::string ReadFile(const fs::path& path)
{
    std::ifstream input(path, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>());
}

void WriteFile(const fs::path& path, const std::vector<uint8_t>& bytes)
{
    fs::create_directories(path.parent_path());
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    output.write(reinterpret_cast<const char*>(bytes.data()), bytes.size());
    output.flush();
    EXPECT_TRUE(output.good());
}

void WriteFile(const fs::path& path, std::string_view bytes)
{
    WriteFile(path, std::vector<uint8_t>(bytes.begin(), bytes.end()));
}

std::vector<uint8_t> MakeElf(uint16_t machine, uint8_t marker)
{
    std::vector<uint8_t> bytes(64, 0);
    bytes[0] = 0x7f;
    bytes[1] = 'E';
    bytes[2] = 'L';
    bytes[3] = 'F';
    bytes[4] = 2;
    bytes[5] = 1;
    bytes[6] = 1;
    bytes[18] = static_cast<uint8_t>(machine & 0xff);
    bytes[19] = static_cast<uint8_t>(machine >> 8);
    bytes[63] = marker;
    return bytes;
}

InstallRequestV1 MakeInstallRequest(const std::string& packageName,
    const std::string& transactionId, std::string_view bytes)
{
    InstallRequestV1 request;
    ArtifactDescriptorV1 artifact;
    artifact.artifactId = "base";
    artifact.role = ArtifactRole::BASE;
    artifact.bytes.assign(bytes.begin(), bytes.end());
    artifact.byteLength = artifact.bytes.size();
    artifact.sha256 = Sha256Hex(bytes);
    request.artifactSet.artifacts.push_back(artifact);
    request.artifactSet.artifactSetDigest =
        ComputeArtifactSetDigest(request.artifactSet);
    request.manifest.artifactSetDigest = request.artifactSet.artifactSetDigest;
    request.manifest.parserVersion = "fixture-parser-v1";
    request.manifest.packageName = packageName;
    request.manifest.versionCode = 1;
    request.manifest.versionName = "1";
    request.manifest.minSdk = 26;
    request.manifest.targetSdk = 35;
    request.signing.artifactSetDigest = request.artifactSet.artifactSetDigest;
    request.signing.verifierVersion = "fixture-verifier-v1";
    request.signing.policyProfile = "fixture-policy-v1";
    request.signing.verified = true;
    request.signing.schemeVersions = {2};
    request.signing.signerCertificateDigests = {
        Sha256Hex("signer:" + packageName),
    };
    request.userId = 0;
    request.expectedPackageName = packageName;
    request.policyRef = "fixture-policy-v1";
    request.retryIdentity = "retry:" + transactionId;
    request.admission.schemaVersion = 1;
    request.admission.jobId = "job:" + transactionId;
    request.admission.memberId = "member:" + transactionId;
    request.admission.memberIndex = 0;
    request.admission.operation = "INSTALL";
    request.admission.transactionId = transactionId;
    request.admission.jobRecordVersion = 1;
    request.admission.callerScopeDigest = Sha256Hex("fixture-caller");
    request.admission.policySnapshotId = request.policyRef;
    request.admission.requestDigest = ComputeInstallRequestDigest(request);
    return request;
}

RuntimePathRequestV1 MakeQuery(const PublishedPackageSnapshotV1& snapshot,
    const std::string& requestId)
{
    RuntimePathRequestV1 request;
    request.requestId = requestId;
    request.packageName = snapshot.packageName;
    request.userId = snapshot.userId;
    request.expectedGeneration = snapshot.generation;
    request.expectedCanonicalDigest = snapshot.canonicalDigest;
    request.abi = "arm64-v8a";
    request.callerScopeDigest = Sha256Hex("runtime-loader:primary");
    request.callerAuthorized = true;
    return request;
}

std::string Key(const std::string& packageName, uint32_t userId,
    uint64_t generation, const std::string& abi)
{
    return packageName + "#" + std::to_string(userId) + "#" +
        std::to_string(generation) + "#" + abi;
}

class MapFactsProvider final : public RuntimePathFactsProvider {
public:
    void Put(RuntimePathFactsV1 facts)
    {
        facts_[Key(facts.packageName, facts.userId, facts.generation,
            facts.abi)] = std::move(facts);
    }

    bool Read(const std::string& packageName, uint32_t userId,
        uint64_t generation, const std::string& abi, RuntimePathFactsV1* facts,
        std::string* error) const override
    {
        const auto iterator =
            facts_.find(Key(packageName, userId, generation, abi));
        if (iterator == facts_.end() || facts == nullptr) {
            if (error != nullptr) *error = "facts not found";
            return false;
        }
        *facts = iterator->second;
        return true;
    }

    RuntimePathFactsV1 Get(const RuntimePathRequestV1& request) const
    {
        return facts_.at(Key(request.packageName, request.userId,
            request.expectedGeneration, request.abi));
    }

private:
    std::map<std::string, RuntimePathFactsV1> facts_;
};

class OneShotFault final : public RuntimePathFaultInjector {
public:
    explicit OneShotFault(RuntimePathFaultPoint target) : target_(target) {}

    bool InterruptAfter(RuntimePathFaultPoint point) override
    {
        if (!fired_ && point == target_) {
            fired_ = true;
            return true;
        }
        return false;
    }

private:
    RuntimePathFaultPoint target_;
    bool fired_ = false;
};

void Emit(const std::string& caseId, const RuntimePathResponseV1& response)
{
    const std::string json = SerializeRuntimePathResponseJsonV1(response);
    gResponses << "{\"caseId\":\"" << caseId << "\",\"response\":"
               << json << "}\n";
    gResponses.flush();
}

void ExpectNoLeak(const RuntimePathResponseV1& response,
    const std::string& protectedRoot)
{
    EXPECT_TRUE(!response.descriptor.has_value());
    EXPECT_TRUE(response.observations.empty());
    EXPECT_TRUE(!response.classLoaderCreated);
    EXPECT_TRUE(SerializeRuntimePathResponseJsonV1(response).find(
        protectedRoot) == std::string::npos);
}

PublishedPackageSnapshotV1 InstallReadyPackage(FilePackageStore* store,
    PackageTransactionCoordinator* coordinator, const std::string& packageName,
    const std::string& transactionId, std::string_view bytes)
{
    const PackageLifecycleReceiptV1 receipt =
        coordinator->Install(MakeInstallRequest(packageName, transactionId, bytes));
    EXPECT_EQ(receipt.verdict, InstallVerdict::COMMITTED);
    PublishedPackageSnapshotV1 snapshot;
    std::string error;
    EXPECT_TRUE(store->ReadPublishedPackage(0, packageName, &snapshot, &error));
#if defined(FN01_ENABLE_REFERENCE_FIXTURES)
    EXPECT_TRUE(store->SeedHostProjectionForFixture(0, packageName,
        snapshot.generation, snapshot.canonicalDigest,
        HostProjectionState::ACTIVE, PublicationState::EXTERNAL_READY, &error));
#else
#error "A12 host test requires FN01_ENABLE_REFERENCE_FIXTURES"
#endif
    return snapshot;
}

RuntimePathFactsV1 MakeFacts(const PublishedPackageSnapshotV1& snapshot,
    const fs::path& permittedRoot, const fs::path& nativeRoot,
    const fs::path& libraryPath, const std::vector<uint8_t>& libraryBytes)
{
    RuntimePathFactsV1 facts;
    facts.packageName = snapshot.packageName;
    facts.userId = snapshot.userId;
    facts.generation = snapshot.generation;
    facts.canonicalDigest = snapshot.canonicalDigest;
    facts.artifactSetDigest = snapshot.artifactSetDigest;
    facts.abi = "arm64-v8a";
    facts.permittedRoots = {fs::canonical(permittedRoot).string()};
    facts.nativeSearchRoots = {fs::canonical(nativeRoot).string()};
    facts.nativeLibraries = {
        {fs::canonical(libraryPath).string(),
            Sha256Hex(std::string_view(
                reinterpret_cast<const char*>(libraryBytes.data()),
                libraryBytes.size()))},
    };
    return facts;
}

void RunMatrix(const fs::path& runRoot, bool dependencyClosureSmoke)
{
    const fs::path managedRoot = runRoot / "managed";
    const fs::path storeRoot = runRoot / "store";
    fs::create_directories(managedRoot);

    MapFactsProvider provider;
    NoRuntimePathFaultInjector noFault;
    std::string error;
    RuntimePathRequestV1 alphaRequest;
    RuntimePathRequestV1 betaRequest;
    std::string alphaReadyJson;
    std::string eventDigestBefore;

    {
        FilePackageStore store(storeRoot.string());
        EXPECT_TRUE(store.Open(&error));
        PosixPackageFileStager stager(managedRoot.string());
        NoFaultInjector installNoFault;
        PackageTransactionCoordinator coordinator(
            &store, &stager, &installNoFault);

        const auto alpha = InstallReadyPackage(&store, &coordinator,
            "dev.fixture.alpha", "tx-fixture-alpha", "alpha-apk-content");
        const auto beta = InstallReadyPackage(&store, &coordinator,
            "io.fixture.beta", "tx-fixture-beta", "beta-apk-content");

        const fs::path alphaGeneration =
            fs::path(alpha.managedFiles.baseCodePath).parent_path();
        const fs::path alphaNative = alphaGeneration / "lib/arm64";
        const fs::path alphaLibrary = alphaNative / "libalpha.so";
        const auto alphaElf = MakeElf(183, 0x11);
        WriteFile(alphaLibrary, alphaElf);
        provider.Put(MakeFacts(
            alpha, alphaGeneration, alphaNative, alphaLibrary, alphaElf));

        const fs::path betaGeneration =
            fs::path(beta.managedFiles.baseCodePath).parent_path();
        const fs::path betaNative = betaGeneration / "lib/arm64";
        const fs::path betaLibrary = betaNative / "libbeta.so";
        const auto betaElf = MakeElf(183, 0x22);
        WriteFile(betaLibrary, betaElf);
        provider.Put(MakeFacts(
            beta, betaGeneration, betaNative, betaLibrary, betaElf));

        alphaRequest = MakeQuery(alpha, "request-alpha");
        betaRequest = MakeQuery(beta, "request-beta");
        eventDigestBefore = Sha256Hex(ReadFile(storeRoot / "events.v1.log"));

        RuntimePathDescriptorServiceV1 service(&store, &provider, &noFault);
        const auto ready = service.Query(alphaRequest);
        Emit("P01-alpha", ready);
        EXPECT_EQ(ready.verdict, RuntimePathVerdict::READY);
        EXPECT_TRUE(ready.descriptor.has_value());
        EXPECT_EQ(ready.descriptor->baseCodePath,
            fs::canonical(alpha.managedFiles.baseCodePath).string());
        EXPECT_TRUE(ready.descriptor->splitCodePaths.empty());
        EXPECT_EQ(ready.descriptor->nativeSearchRoots.size(), size_t(1));
        EXPECT_EQ(ready.descriptor->nativeLibraries.size(), size_t(1));
        EXPECT_EQ(ready.observations.back().elfMachine,
            std::optional<uint16_t>(183));
        EXPECT_TRUE(!ready.classLoaderCreated);
        EXPECT_EQ(ValidateDescriptorForConsumerV1(*ready.descriptor),
            RuntimePathVerdict::READY);
        alphaReadyJson = SerializeRuntimePathResponseJsonV1(ready);
        gConsumer << "{\"caseId\":\"P01-alpha\",\"accepted\":true,"
                     "\"classLoaderCreated\":false,\"verdict\":\"READY\"}\n";

        if (dependencyClosureSmoke) {
#if defined(FN01_ENABLE_REFERENCE_FIXTURES)
            EXPECT_TRUE(store.SeedHostProjectionForFixture(0,
                alpha.packageName, alpha.generation, alpha.canonicalDigest,
                HostProjectionState::PREPARED,
                PublicationState::EXTERNAL_READY, &error));
            const std::string preparedBefore =
                Sha256Hex(ReadFile(storeRoot / "events.v1.log"));
            const auto prepared = service.Query(alphaRequest);
            Emit("N02-projection-prepared", prepared);
            EXPECT_EQ(
                prepared.verdict, RuntimePathVerdict::PACKAGE_NOT_READY);
            ExpectNoLeak(prepared, alphaGeneration.string());
            EXPECT_EQ(Sha256Hex(ReadFile(storeRoot / "events.v1.log")),
                preparedBefore);
            EXPECT_TRUE(store.SeedHostProjectionForFixture(0,
                alpha.packageName, alpha.generation, alpha.canonicalDigest,
                HostProjectionState::ACTIVE,
                PublicationState::EXTERNAL_READY, &error));
            eventDigestBefore =
                Sha256Hex(ReadFile(storeRoot / "events.v1.log"));
#endif
        }

        if (!dependencyClosureSmoke) {
        const auto replay = service.Query(alphaRequest);
        Emit("P02-exact-replay", replay);
        EXPECT_EQ(SerializeRuntimePathResponseJsonV1(replay), alphaReadyJson);

        auto alternatePolicyFacts = provider.Get(alphaRequest);
        alternatePolicyFacts.permittedRoots = {
            fs::canonical(managedRoot).string(),
        };
        provider.Put(alternatePolicyFacts);
        const auto alternatePolicy = service.Query(alphaRequest);
        Emit("P02-alternate-root-policy", alternatePolicy);
        EXPECT_EQ(alternatePolicy.verdict, RuntimePathVerdict::READY);
        EXPECT_TRUE(alternatePolicy.descriptor.has_value());
        EXPECT_EQ(alternatePolicy.descriptor->permittedRoots.front(),
            fs::canonical(managedRoot).string());
        provider.Put(MakeFacts(
            alpha, alphaGeneration, alphaNative, alphaLibrary, alphaElf));

        const auto betaReady = service.Query(betaRequest);
        Emit("P02-second-package", betaReady);
        EXPECT_EQ(betaReady.verdict, RuntimePathVerdict::READY);
        EXPECT_TRUE(betaReady.descriptor.has_value());
        EXPECT_TRUE(betaReady.descriptor->baseCodePath !=
            ready.descriptor->baseCodePath);

        auto split = alphaRequest;
        split.requestId = "request-split";
        split.splitProfileRequested = true;
        const auto splitResponse = service.Query(split);
        Emit("N01-split-profile", splitResponse);
        EXPECT_EQ(splitResponse.verdict,
            RuntimePathVerdict::NOT_SUPPORTED_ARTIFACT_PROFILE);
        ExpectNoLeak(splitResponse, alphaGeneration.string());

        auto abi = alphaRequest;
        abi.requestId = "request-abi";
        abi.abi = "x86_64";
        const auto abiResponse = service.Query(abi);
        Emit("N01-unsupported-abi", abiResponse);
        EXPECT_EQ(abiResponse.verdict, RuntimePathVerdict::NOT_SUPPORTED_ABI);
        ExpectNoLeak(abiResponse, alphaGeneration.string());

        auto user = alphaRequest;
        user.requestId = "request-user";
        user.userId = 10;
        const auto userResponse = service.Query(user);
        Emit("N02-secondary-user", userResponse);
        EXPECT_EQ(
            userResponse.verdict, RuntimePathVerdict::NOT_SUPPORTED_USER);
        ExpectNoLeak(userResponse, alphaGeneration.string());

        auto caller = alphaRequest;
        caller.requestId = "request-caller";
        caller.callerAuthorized = false;
        const auto callerResponse = service.Query(caller);
        Emit("N02-caller-denied", callerResponse);
        EXPECT_EQ(callerResponse.verdict, RuntimePathVerdict::NOT_AUTHORIZED);
        ExpectNoLeak(callerResponse, alphaGeneration.string());

        auto stale = alphaRequest;
        stale.requestId = "request-stale";
        stale.expectedGeneration += 1;
        const auto staleResponse = service.Query(stale);
        Emit("N02-stale-generation", staleResponse);
        EXPECT_EQ(
            staleResponse.verdict, RuntimePathVerdict::STALE_GENERATION);
        ExpectNoLeak(staleResponse, alphaGeneration.string());

        auto outsideFacts = provider.Get(alphaRequest);
        outsideFacts.permittedRoots = {
            fs::canonical(runRoot).string() + "/not-present",
        };
        provider.Put(outsideFacts);
        const auto outsideResponse = service.Query(alphaRequest);
        Emit("N01-unreachable-root", outsideResponse);
        EXPECT_EQ(outsideResponse.verdict,
            RuntimePathVerdict::PATH_OUTSIDE_PERMITTED_ROOT);
        ExpectNoLeak(outsideResponse, alphaGeneration.string());
        provider.Put(MakeFacts(
            alpha, alphaGeneration, alphaNative, alphaLibrary, alphaElf));

        const fs::path reachableOutsideRoot = runRoot / "reachable-outside";
        const fs::path reachableOutsideLibrary =
            reachableOutsideRoot / "libescape.so";
        WriteFile(reachableOutsideLibrary, alphaElf);
        auto escapedFacts = provider.Get(alphaRequest);
        escapedFacts.nativeSearchRoots = {
            fs::canonical(reachableOutsideRoot).string(),
        };
        escapedFacts.nativeLibraries = {
            {fs::canonical(reachableOutsideLibrary).string(),
                Sha256Hex(std::string_view(
                    reinterpret_cast<const char*>(alphaElf.data()),
                    alphaElf.size()))},
        };
        provider.Put(escapedFacts);
        const auto escapedResponse = service.Query(alphaRequest);
        Emit("N01-reachable-path-outside-policy", escapedResponse);
        EXPECT_EQ(escapedResponse.verdict,
            RuntimePathVerdict::PATH_OUTSIDE_PERMITTED_ROOT);
        ExpectNoLeak(escapedResponse, alphaGeneration.string());
        EXPECT_TRUE(SerializeRuntimePathResponseJsonV1(escapedResponse).find(
            reachableOutsideRoot.string()) == std::string::npos);
        provider.Put(MakeFacts(
            alpha, alphaGeneration, alphaNative, alphaLibrary, alphaElf));

        const std::string originalBase =
            ReadFile(alpha.managedFiles.baseCodePath);
        WriteFile(alpha.managedFiles.baseCodePath, "tampered-base");
        const auto baseMismatch = service.Query(alphaRequest);
        Emit("F01-base-digest-mismatch", baseMismatch);
        EXPECT_EQ(
            baseMismatch.verdict, RuntimePathVerdict::DIGEST_MISMATCH);
        ExpectNoLeak(baseMismatch, alphaGeneration.string());
        WriteFile(alpha.managedFiles.baseCodePath, originalBase);

        auto digestFacts = provider.Get(alphaRequest);
        digestFacts.nativeLibraries.front().sha256 = Sha256Hex("wrong");
        provider.Put(digestFacts);
        const auto nativeDigestMismatch = service.Query(alphaRequest);
        Emit("F01-native-digest-mismatch", nativeDigestMismatch);
        EXPECT_EQ(nativeDigestMismatch.verdict,
            RuntimePathVerdict::DIGEST_MISMATCH);
        ExpectNoLeak(nativeDigestMismatch, alphaGeneration.string());

        const auto wrongElf = MakeElf(62, 0x33);
        WriteFile(alphaLibrary, wrongElf);
        auto elfFacts = provider.Get(alphaRequest);
        elfFacts.nativeLibraries.front().sha256 =
            Sha256Hex(std::string_view(
                reinterpret_cast<const char*>(wrongElf.data()),
                wrongElf.size()));
        provider.Put(elfFacts);
        const auto elfMismatch = service.Query(alphaRequest);
        Emit("F01-elf-identity-mismatch", elfMismatch);
        EXPECT_EQ(elfMismatch.verdict,
            RuntimePathVerdict::ELF_IDENTITY_MISMATCH);
        ExpectNoLeak(elfMismatch, alphaGeneration.string());
        WriteFile(alphaLibrary, alphaElf);
        provider.Put(MakeFacts(
            alpha, alphaGeneration, alphaNative, alphaLibrary, alphaElf));

        const std::vector<std::pair<RuntimePathFaultPoint, std::string>> faults = {
            {RuntimePathFaultPoint::AFTER_GENERATION_SNAPSHOT, "snapshot"},
            {RuntimePathFaultPoint::AFTER_FILE_READBACK, "file-readback"},
            {RuntimePathFaultPoint::AFTER_ELF_READBACK, "elf-readback"},
            {RuntimePathFaultPoint::AFTER_SERIALIZATION, "serialization"},
        };
        for (const auto& [point, label] : faults) {
            OneShotFault fault(point);
            RuntimePathDescriptorServiceV1 interrupted(
                &store, &provider, &fault);
            const auto interruption = interrupted.Query(alphaRequest);
            Emit("F02-" + label + "-interrupt", interruption);
            EXPECT_EQ(
                interruption.verdict, RuntimePathVerdict::INTERRUPTED);
            ExpectNoLeak(interruption, alphaGeneration.string());
            const auto replayAfterFault = service.Query(alphaRequest);
            Emit("F02-" + label + "-replay", replayAfterFault);
            EXPECT_EQ(SerializeRuntimePathResponseJsonV1(replayAfterFault),
                alphaReadyJson);
        }
        }
    }

    {
        FilePackageStore restartedStore(storeRoot.string());
        EXPECT_TRUE(restartedStore.Open(&error));
        RuntimePathDescriptorServiceV1 restarted(
            &restartedStore, &provider, &noFault);
        const auto restartReplay = restarted.Query(alphaRequest);
        Emit("F02-process-restart-replay", restartReplay);
        EXPECT_EQ(SerializeRuntimePathResponseJsonV1(restartReplay),
            alphaReadyJson);
    }

    const std::string eventDigestAfter =
        Sha256Hex(ReadFile(storeRoot / "events.v1.log"));
    EXPECT_EQ(eventDigestAfter, eventDigestBefore);
    std::ofstream beforeAfter(
        runRoot / "before-after.json", std::ios::binary);
    beforeAfter << "{\"canonicalEventLogSha256Before\":\""
                << eventDigestBefore
                << "\",\"canonicalEventLogSha256After\":\""
                << eventDigestAfter
                << "\",\"mutationObserved\":"
                << (eventDigestAfter == eventDigestBefore ? "false" : "true")
                << "}\n";
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2 && argc != 3) {
        std::cerr << "usage: runtime_path_descriptor_host_test OUTPUT_ROOT "
                     "[--dependency-closure-smoke]\n";
        return 2;
    }
    const bool dependencyClosureSmoke =
        argc == 3 && std::string(argv[2]) == "--dependency-closure-smoke";
    if (argc == 3 && !dependencyClosureSmoke) return 2;
    const fs::path runRoot = fs::absolute(argv[1]);
    fs::create_directories(runRoot);
    gResponses.open(runRoot / "responses.jsonl", std::ios::binary);
    gConsumer.open(runRoot / "consumer-dry-run.jsonl", std::ios::binary);
    if (!gResponses.good() || !gConsumer.good()) return 2;

    RunMatrix(runRoot, dependencyClosureSmoke);

    std::ofstream fixture(runRoot / "fixture-manifest.json", std::ios::binary);
    fixture << "{\"fixture\":\"FN01_DURABLE_COMMITTED_GENERATION_FIXTURE\","
               "\"packages\":2,\"artifactProfile\":\"single-base\","
               "\"abi\":\"arm64-v8a\",\"source\":\"generated-input\"}\n";
    std::ofstream summary(runRoot / "summary.json", std::ios::binary);
    summary << "{\"actionId\":\"Fn01.A12\",\"developerTest\":"
            << (gFailures == 0 ?
                (dependencyClosureSmoke ?
                    "\"DEPENDENCY_CLOSURE_SMOKE\"" :
                    "\"READY_FOR_HANDOFF\"") :
                "\"FAILED\"")
            << ",\"formalVerdict\":\"NOT_ISSUED\",\"failures\":"
            << gFailures << "}\n";
    std::cout << "FN01_A12_DEVELOPER_TEST failures=" << gFailures
              << " evidence=" << runRoot << "\n";
    return gFailures == 0 ? 0 : 1;
}
