#include "resource_projection_v1.h"

#include "sha256.h"

#include <cassert>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <sys/stat.h>
#include <thread>
#include <vector>

namespace fs = std::filesystem;
using namespace oh_adapter::resource_projection;
using oh_adapter::package_layout::LayoutVerdict;

namespace {

std::string Digest(const std::string& value)
{
    unsigned char result[32]{};
    sha256(reinterpret_cast<const unsigned char*>(value.data()),
        value.size(), result);
    static constexpr char kHex[] = "0123456789abcdef";
    std::string hex(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        hex[index * 2] = kHex[result[index] >> 4];
        hex[index * 2 + 1] = kHex[result[index] & 0x0f];
    }
    return hex;
}

ResourceProjectionRequestV1 MakeRequest(const std::string& packageName,
    uint64_t generation, const std::string& transaction,
    const std::string& label)
{
    ResourceProjectionRequestV1 request;
    request.requestId = "request-" + transaction;
    request.transactionId = transaction;
    request.callerScopeDigest = Digest("allowed-caller");
    request.packageName = packageName;
    request.generation = generation;
    request.canonicalDigest =
        Digest(packageName + "-canonical-" + std::to_string(generation));
    request.buildPolicyVersion = "resource-policy-v1";
    request.presentationTarget = "LAUNCHER_PRESENTATION";
    request.resourceFacts.presentationStatus =
        ResourcePresentationStatus::RESOLVED;
    request.resourceFacts.componentName = packageName + ".MainActivity";
    request.resourceFacts.configurationHash = Digest("en-US-320dpi");
    request.resourceFacts.label = label;
    request.resourceFacts.iconBytes =
        std::vector<uint8_t>(label.begin(), label.end());
    request.resourceFacts.iconContentType = "image/png";
    request.resourceFacts.sourceArtifactSha256 =
        Digest(packageName + "-base.apk");

    request.layoutReceipt.actionId = "Fn01.A07";
    request.layoutReceipt.requestId = request.requestId;
    request.layoutReceipt.transactionId = request.transactionId;
    request.layoutReceipt.packageName = packageName;
    request.layoutReceipt.userId = 0;
    request.layoutReceipt.generation = generation;
    request.layoutReceipt.artifactSetDigest =
        Digest(packageName + "-artifact-set");
    request.layoutReceipt.managedRootPolicyId = "layout-policy-v1";
    request.layoutReceipt.terminalState = "FINALIZED";
    request.layoutReceipt.verdict = LayoutVerdict::FINALIZED;
    request.layoutReceipt.baseCode.path =
        "/managed/u0/" + packageName + "/g" +
        std::to_string(generation) + "/base.apk";
    request.layoutReceipt.baseCode.sha256 =
        request.resourceFacts.sourceArtifactSha256;
    request.layoutReceipt.baseCode.byteLength = 1024;
    return request;
}

class OneShotFault final : public ResourceProjectionFaultInjector {
public:
    OneShotFault(ResourceProjectionFaultPhase phase,
        ResourceProjectionFaultDecision decision)
        : phase_(phase), decision_(decision)
    {
    }

    ResourceProjectionFaultDecision At(
        ResourceProjectionFaultPhase phase) override
    {
        if (!used_ && phase == phase_) {
            used_ = true;
            return decision_;
        }
        return ResourceProjectionFaultDecision::NONE;
    }

private:
    ResourceProjectionFaultPhase phase_;
    ResourceProjectionFaultDecision decision_;
    bool used_ = false;
};

std::string ReadFile(const fs::path& path)
{
    std::ifstream input(path, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>());
}

void Record(std::ofstream& responses, const std::string& caseId,
    const ResourceProjectionReceiptV1& receipt)
{
    std::string serialized =
        ResourceProjectionBuilderV1::SerializeReceipt(receipt);
    if (!serialized.empty() && serialized.back() == '\n') {
        serialized.pop_back();
    }
    responses << "{\"caseId\":\"" << caseId << "\",\"receipt\":"
              << serialized << "}\n";
}

void Expect(ResourceProjectionVerdict actual,
    ResourceProjectionVerdict expected)
{
    if (actual != expected) {
        std::cerr << "expected "
                  << ResourceProjectionBuilderV1::VerdictName(expected)
                  << " got "
                  << ResourceProjectionBuilderV1::VerdictName(actual)
                  << '\n';
        std::abort();
    }
}

ino_t Inode(const fs::path& path)
{
    struct stat status {};
    assert(stat(path.c_str(), &status) == 0);
    return status.st_ino;
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::cerr << "usage: resource_projection_host_test <evidence-dir>\n";
        return 2;
    }
    const fs::path evidence(argv[1]);
    fs::create_directories(evidence);
    const fs::path managed = evidence / "managed";
    fs::create_directories(managed);
    ResourceProjectionPolicyV1 policy;
    policy.policyVersion = "resource-policy-v1";
    policy.expectedCallerScopeDigest = Digest("allowed-caller");
    ResourceProjectionBuilderV1 builder(managed.string(), policy);
    std::ofstream responses(evidence / "responses.jsonl");

    auto alpha = MakeRequest("org.example.alpha", 1, "tx-alpha", "Alpha");
    const auto alphaReady = builder.Build(alpha, nullptr);
    Expect(alphaReady.verdict, ResourceProjectionVerdict::READY);
    assert(alphaReady.state == "READY");
    assert(alphaReady.payloadKind == "MATERIALIZED");
    assert(alphaReady.label == "Alpha");
    assert(ReadFile(alphaReady.payloadPath).find("labelHex=416c706861") !=
        std::string::npos);
    Record(responses, "P01-distinct-label-alpha", alphaReady);

    auto beta = MakeRequest("org.example.beta", 1, "tx-beta", "Beta");
    const auto betaReady = builder.Build(beta, nullptr);
    Expect(betaReady.verdict, ResourceProjectionVerdict::READY);
    assert(betaReady.label == "Beta");
    assert(alphaReady.resourcePayloadDigest !=
        betaReady.resourcePayloadDigest);
    assert(ReadFile(betaReady.payloadPath).find("labelHex=42657461") !=
        std::string::npos);
    Record(responses, "P01-distinct-label-beta", betaReady);

    auto large = MakeRequest(
        "org.example.large", 1, "tx-large", "Large");
    large.resourceFacts.iconBytes.assign(5 * 1024 * 1024, 0x5a);
    const auto largeReady = builder.Build(large, nullptr);
    Expect(largeReady.verdict, ResourceProjectionVerdict::READY);
    assert(fs::file_size(largeReady.payloadPath) > 10 * 1024 * 1024);
    Record(responses, "P01-policy-limit-readback", largeReady);

    auto empty = MakeRequest("org.example.empty", 1, "tx-empty", "unused");
    empty.resourceFacts.presentationStatus =
        ResourcePresentationStatus::NONE;
    empty.resourceFacts.componentName.clear();
    empty.resourceFacts.configurationHash.clear();
    empty.resourceFacts.label.clear();
    empty.resourceFacts.iconBytes.clear();
    empty.resourceFacts.iconContentType.clear();
    const auto emptyReady = builder.Build(empty, nullptr);
    Expect(emptyReady.verdict, ResourceProjectionVerdict::READY);
    assert(emptyReady.payloadKind == "EMPTY");
    Record(responses, "P01-empty-ready", emptyReady);

    const ino_t alphaInode = Inode(alphaReady.payloadPath);
    const auto alphaReplay = builder.Build(alpha, nullptr);
    Expect(alphaReplay.verdict, ResourceProjectionVerdict::READY);
    assert(alphaReplay.resourcePayloadDigest ==
        alphaReady.resourcePayloadDigest);
    assert(Inode(alphaReplay.payloadPath) == alphaInode);
    Record(responses, "P02-idempotent-replay", alphaReplay);

    auto missing = MakeRequest(
        "org.example.missing", 1, "tx-missing", "missing");
    missing.resourceFacts.presentationStatus =
        ResourcePresentationStatus::MISSING;
    const auto missingResult = builder.Build(missing, nullptr);
    Expect(missingResult.verdict,
        ResourceProjectionVerdict::RESOURCE_NOT_FOUND);
    assert(!fs::exists(managed / "u0" / missing.packageName));
    Record(responses, "N01-resource-not-found", missingResult);

    auto unsupported = MakeRequest(
        "org.example.unsupported", 1, "tx-unsupported", "unsupported");
    unsupported.resourceFacts.presentationStatus =
        ResourcePresentationStatus::UNSUPPORTED_CONFIGURATION;
    const auto unsupportedResult = builder.Build(unsupported, nullptr);
    Expect(unsupportedResult.verdict,
        ResourceProjectionVerdict::UNSUPPORTED_CONFIGURATION);
    Record(responses, "N01-unsupported-configuration",
        unsupportedResult);

    auto invalid = MakeRequest(
        "org.example.invalid", 1, "tx-invalid", "invalid");
    invalid.resourceFacts.label.clear();
    const auto invalidResult = builder.Build(invalid, nullptr);
    Expect(invalidResult.verdict,
        ResourceProjectionVerdict::INVALID_RESOURCE_PAYLOAD);
    Record(responses, "N01-invalid-payload", invalidResult);

    auto wrongCaller = MakeRequest(
        "org.example.caller", 1, "tx-caller", "Caller");
    wrongCaller.callerScopeDigest = Digest("unauthorized");
    const auto wrongCallerResult = builder.Build(wrongCaller, nullptr);
    Expect(wrongCallerResult.verdict,
        ResourceProjectionVerdict::CALLER_SCOPE_MISMATCH);
    assert(!fs::exists(managed / "u0" / wrongCaller.packageName));
    Record(responses, "N02-caller-scope", wrongCallerResult);

    auto wrongGeneration = MakeRequest(
        "org.example.generation", 2, "tx-generation", "Generation");
    wrongGeneration.layoutReceipt.generation = 1;
    const auto wrongGenerationResult =
        builder.Build(wrongGeneration, nullptr);
    Expect(wrongGenerationResult.verdict,
        ResourceProjectionVerdict::LAYOUT_RECEIPT_MISMATCH);
    Record(responses, "N02-layout-generation", wrongGenerationResult);

    auto wrongTransaction = MakeRequest(
        "org.example.transaction", 1, "tx-current", "Transaction");
    wrongTransaction.layoutReceipt.transactionId = "tx-prior";
    const auto wrongTransactionResult =
        builder.Build(wrongTransaction, nullptr);
    Expect(wrongTransactionResult.verdict,
        ResourceProjectionVerdict::LAYOUT_RECEIPT_MISMATCH);
    Record(responses, "N02-layout-transaction", wrongTransactionResult);

    auto wrongTarget = MakeRequest(
        "org.example.target", 1, "tx-target", "Target");
    wrongTarget.presentationTarget = "WIDGET_PRESENTATION";
    const auto wrongTargetResult = builder.Build(wrongTarget, nullptr);
    Expect(wrongTargetResult.verdict,
        ResourceProjectionVerdict::NOT_SUPPORTED_TARGET);
    Record(responses, "N02-target", wrongTargetResult);

    auto secondary = MakeRequest(
        "org.example.secondary", 1, "tx-secondary", "Secondary");
    secondary.userId = 10;
    secondary.layoutReceipt.userId = 10;
    const auto secondaryResult = builder.Build(secondary, nullptr);
    Expect(secondaryResult.verdict,
        ResourceProjectionVerdict::NOT_SUPPORTED_USER);
    Record(responses, "N02-user", secondaryResult);

    auto noSpace = MakeRequest(
        "org.example.nospace", 1, "tx-nospace", "NoSpace");
    OneShotFault noSpaceFault(
        ResourceProjectionFaultPhase::DURING_PAYLOAD_WRITE,
        ResourceProjectionFaultDecision::FAIL_NO_SPACE);
    const auto noSpaceResult = builder.Build(noSpace, &noSpaceFault);
    Expect(noSpaceResult.verdict, ResourceProjectionVerdict::NO_SPACE);
    const fs::path noSpaceGeneration =
        managed / "u0" / noSpace.packageName / "g1";
    assert(!fs::exists(noSpaceGeneration / "resource.payload"));
    assert(!fs::exists(noSpaceGeneration / "resource-runtime.v1.json"));
    Record(responses, "F01-no-space-clean", noSpaceResult);

    auto corruptReadback = MakeRequest(
        "org.example.corrupt", 1, "tx-corrupt", "Corrupt");
    OneShotFault corruptFault(
        ResourceProjectionFaultPhase::BEFORE_READBACK,
        ResourceProjectionFaultDecision::CORRUPT_PAYLOAD);
    const auto corruptResult = builder.Build(corruptReadback, &corruptFault);
    Expect(corruptResult.verdict,
        ResourceProjectionVerdict::DATA_INCONSISTENT);
    const fs::path corruptGeneration =
        managed / "u0" / corruptReadback.packageName / "g1";
    assert(!fs::exists(corruptGeneration / "resource.payload"));
    assert(!fs::exists(corruptGeneration / "resource-runtime.v1.json"));
    Record(responses, "F01-readback-corruption-clean", corruptResult);

    auto restartPrepared = MakeRequest(
        "org.example.restartprepared", 1, "tx-restart-prepared", "Restart");
    OneShotFault preparedInterrupt(
        ResourceProjectionFaultPhase::AFTER_PREPARED_DURABLE,
        ResourceProjectionFaultDecision::INTERRUPT);
    const auto interruptedPrepared =
        builder.Build(restartPrepared, &preparedInterrupt);
    Expect(interruptedPrepared.verdict,
        ResourceProjectionVerdict::INTERRUPTED);
    const auto recoveredPrepared = builder.Build(restartPrepared, nullptr);
    Expect(recoveredPrepared.verdict, ResourceProjectionVerdict::READY);
    Record(responses, "F02-recover-prepared", recoveredPrepared);

    auto restartReady = MakeRequest(
        "org.example.restartready", 1, "tx-restart-ready", "ReadyRestart");
    OneShotFault readyInterrupt(
        ResourceProjectionFaultPhase::AFTER_READY_DURABLE,
        ResourceProjectionFaultDecision::INTERRUPT);
    const auto interruptedReady = builder.Build(restartReady, &readyInterrupt);
    Expect(interruptedReady.verdict, ResourceProjectionVerdict::INTERRUPTED);
    const auto recoveredReady = builder.Build(restartReady, nullptr);
    Expect(recoveredReady.verdict, ResourceProjectionVerdict::READY);
    Record(responses, "F02-recover-ready", recoveredReady);

    const std::vector<std::pair<ResourceProjectionFaultPhase, std::string>>
        remainingRestartPhases = {
            {ResourceProjectionFaultPhase::DURING_PAYLOAD_WRITE,
                "during-payload-write"},
            {ResourceProjectionFaultPhase::AFTER_PAYLOAD_FSYNC,
                "after-payload-fsync"},
            {ResourceProjectionFaultPhase::BEFORE_READY_DURABLE,
                "before-ready-durable"},
            {ResourceProjectionFaultPhase::BEFORE_READBACK,
                "before-readback"},
            {ResourceProjectionFaultPhase::AFTER_RECEIPT_DURABLE,
                "after-receipt-durable"},
        };
    uint64_t restartGeneration = 2;
    for (const auto& [phase, phaseName] : remainingRestartPhases) {
        auto restart = MakeRequest("org.example.restartmatrix",
            restartGeneration, "tx-restart-" + phaseName, phaseName);
        OneShotFault interrupt(
            phase, ResourceProjectionFaultDecision::INTERRUPT);
        const auto interrupted = builder.Build(restart, &interrupt);
        Expect(interrupted.verdict, ResourceProjectionVerdict::INTERRUPTED);
        const auto recovered = builder.Build(restart, nullptr);
        Expect(recovered.verdict, ResourceProjectionVerdict::READY);
        Record(responses, "F02-recover-" + phaseName, recovered);
        ++restartGeneration;
    }

    auto concurrentA = MakeRequest(
        "org.example.concurrent", 1, "tx-concurrent-a", "Concurrent A");
    auto concurrentB = MakeRequest(
        "org.example.concurrent", 1, "tx-concurrent-b", "Concurrent B");
    ResourceProjectionReceiptV1 concurrentAResult;
    ResourceProjectionReceiptV1 concurrentBResult;
    std::thread first([&]() {
        concurrentAResult = builder.Build(concurrentA, nullptr);
    });
    std::thread second([&]() {
        concurrentBResult = builder.Build(concurrentB, nullptr);
    });
    first.join();
    second.join();
    const bool exactlyOneReady =
        (concurrentAResult.verdict == ResourceProjectionVerdict::READY) !=
        (concurrentBResult.verdict == ResourceProjectionVerdict::READY);
    const bool exactlyOneConflict =
        (concurrentAResult.verdict ==
            ResourceProjectionVerdict::TRANSACTION_CONFLICT) !=
        (concurrentBResult.verdict ==
            ResourceProjectionVerdict::TRANSACTION_CONFLICT);
    assert(exactlyOneReady && exactlyOneConflict);
    Record(responses, "P02-concurrent-a", concurrentAResult);
    Record(responses, "P02-concurrent-b", concurrentBResult);

    const fs::path outside = evidence / "outside";
    fs::create_directories(outside);
    const fs::path symlinkPackage =
        managed / "u0" / "org.example.symlink";
    fs::create_directories(symlinkPackage.parent_path());
    fs::create_directory_symlink(outside, symlinkPackage);
    auto symlink = MakeRequest(
        "org.example.symlink", 1, "tx-symlink", "Symlink");
    const auto symlinkResult = builder.Build(symlink, nullptr);
    Expect(symlinkResult.verdict,
        ResourceProjectionVerdict::SYMLINK_ESCAPE);
    Record(responses, "N02-symlink-escape", symlinkResult);

    auto conflict = alpha;
    conflict.transactionId = "tx-alpha-conflict";
    conflict.requestId = "request-alpha-conflict";
    conflict.layoutReceipt.transactionId = conflict.transactionId;
    conflict.layoutReceipt.requestId = conflict.requestId;
    conflict.resourceFacts.label = "Not Alpha";
    conflict.resourceFacts.iconBytes = {'N', 'o', 't'};
    const auto conflictResult = builder.Build(conflict, nullptr);
    Expect(conflictResult.verdict,
        ResourceProjectionVerdict::TRANSACTION_CONFLICT);
    Record(responses, "P02-generation-conflict", conflictResult);

    const fs::path canonicalMarker =
        managed / "u0" / alpha.packageName / "canonical.marker";
    {
        std::ofstream marker(canonicalMarker);
        marker << "must-survive";
    }
    ResourceCleanupObligationV1 cleanup;
    cleanup.requestId = alpha.requestId;
    cleanup.transactionId = alpha.transactionId;
    cleanup.callerScopeDigest = Digest("allowed-caller");
    cleanup.packageName = alpha.packageName;
    cleanup.generation = alpha.generation;
    cleanup.canonicalDigest = alphaReady.canonicalDigest;
    cleanup.resourcePayloadDigest = alphaReady.resourcePayloadDigest;
    cleanup.cause = "GENERATION_RETIREMENT";
    auto unauthorizedCleanup = cleanup;
    unauthorizedCleanup.callerScopeDigest = Digest("unauthorized");
    const auto unauthorizedCleanupResult =
        builder.Cleanup(unauthorizedCleanup);
    Expect(unauthorizedCleanupResult.verdict,
        ResourceProjectionVerdict::CALLER_SCOPE_MISMATCH);
    assert(fs::exists(alphaReady.payloadPath));
    Record(responses, "N02-cleanup-caller-scope",
        unauthorizedCleanupResult);
    const auto cleaned = builder.Cleanup(cleanup);
    Expect(cleaned.verdict, ResourceProjectionVerdict::CLEANED);
    assert(fs::exists(canonicalMarker));
    assert(fs::exists(betaReady.payloadPath));
    assert(!fs::exists(alphaReady.payloadPath));
    Record(responses, "F01-generation-scoped-cleanup", cleaned);

    responses.close();
    std::ofstream summary(evidence / "summary.json");
    summary
        << "{\"actionId\":\"Fn01.A08\","
        << "\"developerTest\":\"READY_FOR_HANDOFF\","
        << "\"formalVerdict\":\"NOT_ISSUED\","
        << "\"cases\":28,"
        << "\"templatePlaceholderAccepted\":false,"
        << "\"a07ContractConsumed\":true}\n";
    std::cout
        << "RESOURCE_PROJECTION_HOST_TESTS_OK cases=28 "
        << "formal_verdict=NOT_ISSUED\n";
    return 0;
}
