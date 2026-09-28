#include "resource_projection_v1.h"

#include "sha256.h"

#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <string_view>
#include <vector>

namespace fs = std::filesystem;
using namespace oh_adapter::resource_projection;
using oh_adapter::package_layout::LayoutVerdict;

namespace {

std::string Digest(std::string_view value)
{
    unsigned char bytes[32]{};
    sha256(reinterpret_cast<const unsigned char*>(value.data()),
        value.size(), bytes);
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        result[index * 2] = kHex[bytes[index] >> 4];
        result[index * 2 + 1] = kHex[bytes[index] & 0x0f];
    }
    return result;
}

ResourceProjectionRequestV1 Request()
{
    ResourceProjectionRequestV1 request;
    request.requestId = "request-owner-a08-cleanup";
    request.transactionId = "tx-owner-a08-cleanup";
    request.callerScopeDigest = Digest("a08-remediation-caller");
    request.packageName = "org.remediation.cleanup";
    request.generation = 9;
    request.canonicalDigest = Digest("a08-remediation-canonical");
    request.buildPolicyVersion = "a08-remediation-policy-v1";
    request.presentationTarget = "LAUNCHER_PRESENTATION";
    request.resourceFacts.presentationStatus =
        ResourcePresentationStatus::RESOLVED;
    request.resourceFacts.componentName =
        "org.remediation.cleanup.MainActivity";
    request.resourceFacts.configurationHash =
        Digest("a08-remediation-en-US-320dpi");
    request.resourceFacts.label = "A08 cleanup owner";
    request.resourceFacts.iconBytes = {'A', '0', '8'};
    request.resourceFacts.iconContentType = "image/png";
    request.resourceFacts.sourceArtifactSha256 =
        Digest("a08-remediation-base-apk");

    request.layoutReceipt.actionId = "Fn01.A07";
    request.layoutReceipt.requestId = request.requestId;
    request.layoutReceipt.transactionId = request.transactionId;
    request.layoutReceipt.packageName = request.packageName;
    request.layoutReceipt.userId = 0;
    request.layoutReceipt.generation = request.generation;
    request.layoutReceipt.artifactSetDigest =
        Digest("a08-remediation-artifact-set");
    request.layoutReceipt.managedRootPolicyId = "layout-policy-v1";
    request.layoutReceipt.terminalState = "FINALIZED";
    request.layoutReceipt.verdict = LayoutVerdict::FINALIZED;
    request.layoutReceipt.baseCode.path =
        "/managed/u0/org.remediation.cleanup/g9/base.apk";
    request.layoutReceipt.baseCode.sha256 =
        request.resourceFacts.sourceArtifactSha256;
    request.layoutReceipt.baseCode.byteLength = 1024;
    return request;
}

ResourceCleanupObligationV1 Obligation(
    const ResourceProjectionRequestV1& request,
    const ResourceProjectionReceiptV1& ready)
{
    ResourceCleanupObligationV1 obligation;
    obligation.requestId = request.requestId;
    obligation.transactionId = request.transactionId;
    obligation.callerScopeDigest = request.callerScopeDigest;
    obligation.packageName = request.packageName;
    obligation.userId = request.userId;
    obligation.generation = request.generation;
    obligation.canonicalDigest = ready.canonicalDigest;
    obligation.resourcePayloadDigest = ready.resourcePayloadDigest;
    obligation.cause = "GENERATION_RETIREMENT";
    return obligation;
}

std::string Read(const fs::path& path)
{
    std::ifstream input(path, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>());
}

void Record(std::ofstream& output, const std::string& caseId,
    const ResourceProjectionReceiptV1& receipt)
{
    std::string body =
        ResourceProjectionBuilderV1::SerializeReceipt(receipt);
    if (!body.empty() && body.back() == '\n') body.pop_back();
    output << "{\"caseId\":\"" << caseId << "\",\"receipt\":"
           << body << "}\n";
}

void Require(bool condition, const char* message)
{
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        std::abort();
    }
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::cerr << "usage: resource_projection_cleanup_remediation_host_test "
                     "<evidence-dir>\n";
        return 2;
    }
    const fs::path evidence = fs::absolute(argv[1]);
    const fs::path managed = evidence / "managed";
    fs::create_directories(managed);
    std::ofstream results(evidence / "results.jsonl");

    ResourceProjectionPolicyV1 policy;
    policy.policyVersion = "a08-remediation-policy-v1";
    policy.expectedCallerScopeDigest =
        Digest("a08-remediation-caller");
    ResourceProjectionBuilderV1 builder(managed.string(), policy);
    const auto request = Request();
    const auto ready = builder.Build(request, nullptr);
    Require(ready.verdict == ResourceProjectionVerdict::READY,
        "owner build must become READY");
    Record(results, "P01-owner-ready", ready);

    const fs::path generation = managed / "u0" / request.packageName / "g9";
    const fs::path payload = generation / "resource.payload";
    const fs::path runtime = generation / "resource-runtime.v1.json";
    const fs::path plan = generation / "resource-plan.v1.json";
    const std::string payloadBefore = Read(payload);
    const std::string runtimeBefore = Read(runtime);
    const std::string planBefore = Read(plan);

    auto foreignTransaction = Obligation(request, ready);
    foreignTransaction.requestId = "request-intruder-a08-cleanup";
    foreignTransaction.transactionId = "tx-intruder-a08-cleanup";
    const auto foreignTransactionResult =
        builder.Cleanup(foreignTransaction);
    Require(foreignTransactionResult.verdict ==
            ResourceProjectionVerdict::TRANSACTION_CONFLICT,
        "foreign transaction must be typed rejected");
    Require(Read(payload) == payloadBefore &&
            Read(runtime) == runtimeBefore && Read(plan) == planBefore,
        "foreign transaction must leave owner projection byte-identical");
    Require(!fs::exists(managed / "u0" / request.packageName /
            "resource-cleanup-g9-tx-intruder-a08-cleanup.v1.json"),
        "foreign transaction must not write a cleanup receipt");
    Record(results, "F01-foreign-transaction-rejected",
        foreignTransactionResult);

    auto foreignRequest = Obligation(request, ready);
    foreignRequest.requestId = "request-intruder-only-a08-cleanup";
    const auto foreignRequestResult = builder.Cleanup(foreignRequest);
    Require(foreignRequestResult.verdict ==
            ResourceProjectionVerdict::TRANSACTION_CONFLICT,
        "foreign request must be typed rejected");
    Require(Read(payload) == payloadBefore &&
            Read(runtime) == runtimeBefore && Read(plan) == planBefore,
        "foreign request must leave owner projection byte-identical");
    Record(results, "N02-foreign-request-rejected",
        foreignRequestResult);

    auto wrongCaller = Obligation(request, ready);
    wrongCaller.callerScopeDigest = Digest("foreign-caller");
    const auto wrongCallerResult = builder.Cleanup(wrongCaller);
    Require(wrongCallerResult.verdict ==
            ResourceProjectionVerdict::CALLER_SCOPE_MISMATCH,
        "foreign caller must remain rejected");
    Require(Read(payload) == payloadBefore &&
            Read(runtime) == runtimeBefore && Read(plan) == planBefore,
        "foreign caller must leave owner projection byte-identical");
    Record(results, "N02-foreign-caller-rejected", wrongCallerResult);

    auto wrongPayload = Obligation(request, ready);
    wrongPayload.resourcePayloadDigest = Digest("foreign-payload");
    const auto wrongPayloadResult = builder.Cleanup(wrongPayload);
    Require(wrongPayloadResult.verdict ==
            ResourceProjectionVerdict::DATA_INCONSISTENT,
        "foreign payload digest must remain fail-closed");
    Require(Read(payload) == payloadBefore &&
            Read(runtime) == runtimeBefore && Read(plan) == planBefore,
        "foreign payload digest must leave owner projection byte-identical");
    Record(results, "N02-foreign-payload-rejected", wrongPayloadResult);

    const fs::path savedPlan = generation / "resource-plan.saved";
    fs::rename(plan, savedPlan);
    const auto missingPlanResult =
        builder.Cleanup(Obligation(request, ready));
    Require(missingPlanResult.verdict ==
            ResourceProjectionVerdict::DATA_INCONSISTENT,
        "missing durable resource plan must fail closed");
    Require(Read(payload) == payloadBefore &&
            Read(runtime) == runtimeBefore &&
            !fs::exists(plan) && Read(savedPlan) == planBefore,
        "missing plan must not delete the owner payload or runtime");
    fs::rename(savedPlan, plan);
    Record(results, "F01-missing-plan-fail-closed", missingPlanResult);

    ResourceProjectionBuilderV1 restarted(managed.string(), policy);
    const auto replayed = restarted.Build(request, nullptr);
    Require(replayed.verdict == ResourceProjectionVerdict::READY &&
            replayed.resourcePayloadDigest == ready.resourcePayloadDigest,
        "fresh builder must replay the unchanged owner READY projection");
    Record(results, "F02-restart-owner-replay", replayed);

    const auto cleaned = restarted.Cleanup(Obligation(request, replayed));
    Require(cleaned.verdict == ResourceProjectionVerdict::CLEANED,
        "exact durable plan owner must clean successfully");
    Require(!fs::exists(payload) && !fs::exists(runtime) &&
            !fs::exists(plan),
        "owner cleanup must remove only the generation projection");
    Require(fs::exists(managed / "u0" / request.packageName /
            "resource-cleanup-g9-tx-owner-a08-cleanup.v1.json"),
        "owner cleanup must write its own receipt");
    Record(results, "F01-owner-cleanup", cleaned);

    results.close();
    std::ofstream summary(evidence / "summary.json");
    summary << "{\"actionId\":\"Fn01.A08\","
               "\"developerTest\":\"READY_FOR_REVERIFY\","
               "\"formalVerdict\":\"NOT_ISSUED\","
               "\"cases\":8,"
               "\"foreignMutation\":false,"
               "\"intruderReceipt\":false}\n";
    std::cout << "A08_CLEANUP_REMEDIATION_OK cases=8 "
                 "formal_verdict=NOT_ISSUED\n";
    return 0;
}
