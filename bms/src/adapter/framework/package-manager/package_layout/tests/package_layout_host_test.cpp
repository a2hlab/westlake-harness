#include "package_layout_v1.h"

#include "sha256.h"

#include <fcntl.h>
#include <atomic>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <string>
#include <string_view>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>
#include <vector>

using namespace oh_adapter::package_layout;
namespace fs = std::filesystem;

namespace {

int gFailures = 0;
std::ofstream gResponses;

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
    return std::string(
        std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
}

int WriteArtifact(const fs::path& path, std::string_view bytes)
{
    const int fd =
        open(path.c_str(), O_RDWR | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    EXPECT_TRUE(fd >= 0);
    if (fd < 0) return -1;
    size_t offset = 0;
    while (offset < bytes.size()) {
        const ssize_t count =
            write(fd, bytes.data() + offset, bytes.size() - offset);
        EXPECT_TRUE(count > 0);
        if (count <= 0) break;
        offset += static_cast<size_t>(count);
    }
    EXPECT_EQ(offset, bytes.size());
    EXPECT_TRUE(fsync(fd) == 0);
    return fd;
}

FilePlanV1 MakePlan(const std::string& packageName,
    const std::string& transactionId, uint64_t generation,
    std::string_view bytes)
{
    FilePlanV1 plan;
    plan.requestId = "request-" + transactionId;
    plan.transactionId = transactionId;
    plan.callerScopeDigest = Sha256Hex("caller:installer");
    plan.userId = 0;
    plan.packageName = packageName;
    plan.generation = generation;
    plan.artifactSetDigest = Sha256Hex("set:" + std::string(bytes));
    plan.managedRootPolicyId = "managed-root-policy-v1";
    plan.nativeAbis = {"arm64-v8a"};
    return plan;
}

VerifiedArtifactReceiptV1 MakeVerified(
    const FilePlanV1& plan, std::string_view bytes)
{
    VerifiedArtifactReceiptV1 receipt;
    receipt.requestId = plan.requestId;
    receipt.transactionId = plan.transactionId;
    receipt.packageName = plan.packageName;
    receipt.artifactSetDigest = plan.artifactSetDigest;
    receipt.artifactSha256 = Sha256Hex(bytes);
    receipt.byteLength = bytes.size();
    receipt.policyVersion = "apk-signing-policy-v3";
    receipt.verifierVersion = "apksig-bridge-v2";
    receipt.verified = true;
    return receipt;
}

ManagedRootPolicyV1 MakePolicy(const fs::path& managedRoot)
{
    ManagedRootPolicyV1 policy;
    policy.policyId = "managed-root-policy-v1";
    policy.permittedCanonicalRoots = {fs::canonical(managedRoot).string()};
    return policy;
}

void Emit(const std::string& caseId, const PackageLayoutReceiptV1& receipt)
{
    gResponses << "{\"caseId\":\"" << caseId << "\",\"response\":"
               << PackageLayoutV1::SerializeReceipt(receipt).substr(
                      0, PackageLayoutV1::SerializeReceipt(receipt).size() - 1)
               << "}\n";
    gResponses.flush();
}

class OneFault final : public LayoutFaultInjector {
public:
    OneFault(LayoutFaultPhase phase, LayoutFaultDecision decision)
        : phase_(phase), decision_(decision)
    {
    }

    LayoutFaultDecision At(LayoutFaultPhase phase) override
    {
        if (!fired_ && phase == phase_) {
            fired_ = true;
            return decision_;
        }
        return LayoutFaultDecision::NONE;
    }

private:
    LayoutFaultPhase phase_;
    LayoutFaultDecision decision_;
    bool fired_ = false;
};

void TestPositiveAndReplay(const fs::path& runRoot)
{
    const fs::path managedRoot = runRoot / "p01-managed";
    fs::create_directories(managedRoot);
    PackageLayoutV1 layout(managedRoot.string(), MakePolicy(managedRoot));
    NoLayoutFaultInjector noFault;

    const std::string alphaBytes = "arbitrary-alpha-base-apk";
    const FilePlanV1 alphaPlan =
        MakePlan("org.example.alpha", "tx-alpha", 2, alphaBytes);
    const VerifiedArtifactReceiptV1 alphaVerified =
        MakeVerified(alphaPlan, alphaBytes);
    const int alphaFd =
        WriteArtifact(runRoot / "p01-alpha.input.apk", alphaBytes);
    PackageLayoutReceiptV1 alpha =
        layout.Finalize(alphaPlan, alphaVerified, alphaFd, &noFault);
    Emit("P01-alpha", alpha);
    EXPECT_EQ(alpha.verdict, LayoutVerdict::FINALIZED);
    EXPECT_EQ(ReadFile(alpha.baseCode.path), alphaBytes);
    EXPECT_TRUE(alpha.baseCode.path.find("org.example.alpha/g2/base.apk") !=
        std::string::npos);

    PackageLayoutReceiptV1 replay =
        layout.Finalize(alphaPlan, alphaVerified, alphaFd, &noFault);
    Emit("P02-replay", replay);
    EXPECT_EQ(replay.verdict, LayoutVerdict::FINALIZED);
    EXPECT_EQ(PackageLayoutV1::SerializeReceipt(replay),
        PackageLayoutV1::SerializeReceipt(alpha));

    const std::string betaBytes = "different-beta-content";
    const FilePlanV1 betaPlan =
        MakePlan("net.sample.beta", "tx-beta", 7, betaBytes);
    const VerifiedArtifactReceiptV1 betaVerified =
        MakeVerified(betaPlan, betaBytes);
    const int betaFd = WriteArtifact(runRoot / "p01-beta.input.apk", betaBytes);
    PackageLayoutReceiptV1 beta =
        layout.Finalize(betaPlan, betaVerified, betaFd, &noFault);
    Emit("P01-beta", beta);
    EXPECT_EQ(beta.verdict, LayoutVerdict::FINALIZED);
    EXPECT_EQ(ReadFile(beta.baseCode.path), betaBytes);
    EXPECT_TRUE(alpha.baseCode.path != beta.baseCode.path);
    close(alphaFd);
    close(betaFd);
}

void TestNegativeBoundaries(const fs::path& runRoot)
{
    const fs::path managedRoot = runRoot / "n01-managed";
    fs::create_directories(managedRoot);
    PackageLayoutV1 layout(managedRoot.string(), MakePolicy(managedRoot));
    NoLayoutFaultInjector noFault;
    const std::string bytes = "negative-fixture";

    FilePlanV1 illegal =
        MakePlan("../escape", "tx-path", 1, bytes);
    VerifiedArtifactReceiptV1 illegalVerified = MakeVerified(illegal, bytes);
    const int fd = WriteArtifact(runRoot / "n01.input.apk", bytes);
    PackageLayoutReceiptV1 result =
        layout.Finalize(illegal, illegalVerified, fd, &noFault);
    Emit("N01-illegal-path", result);
    EXPECT_EQ(result.verdict, LayoutVerdict::PATH_REJECTED);
    EXPECT_TRUE(!fs::exists(runRoot / "escape"));

    FilePlanV1 unsupported =
        MakePlan("org.example.unsupported", "tx-abi", 1, bytes);
    unsupported.nativeAbis = {"x86_64"};
    result =
        layout.Finalize(unsupported, MakeVerified(unsupported, bytes), fd, &noFault);
    Emit("N01-unsupported-abi", result);
    EXPECT_EQ(result.verdict, LayoutVerdict::NOT_SUPPORTED_ABI);

    FilePlanV1 secondary =
        MakePlan("org.example.secondary", "tx-user", 1, bytes);
    secondary.userId = 10;
    result =
        layout.Finalize(secondary, MakeVerified(secondary, bytes), fd, &noFault);
    Emit("N02-user-mismatch", result);
    EXPECT_EQ(result.verdict, LayoutVerdict::NOT_SUPPORTED_USER);

    FilePlanV1 policy =
        MakePlan("org.example.policy", "tx-policy", 1, bytes);
    policy.managedRootPolicyId = "caller-selected-root";
    result = layout.Finalize(policy, MakeVerified(policy, bytes), fd, &noFault);
    Emit("N02-policy-mismatch", result);
    EXPECT_EQ(result.verdict, LayoutVerdict::MANAGED_ROOT_POLICY_MISMATCH);

    ManagedRootPolicyV1 outsidePolicy = MakePolicy(managedRoot);
    outsidePolicy.permittedCanonicalRoots = {fs::canonical(runRoot).string()};
    PackageLayoutV1 outsideLayout(managedRoot.string(), outsidePolicy);
    FilePlanV1 outsidePlan =
        MakePlan("org.example.outside", "tx-outside", 1, bytes);
    result = outsideLayout.Finalize(
        outsidePlan, MakeVerified(outsidePlan, bytes), fd, &noFault);
    Emit("N01-managed-root-outside-policy", result);
    EXPECT_EQ(result.verdict, LayoutVerdict::MANAGED_ROOT_POLICY_MISMATCH);

    FilePlanV1 receipt =
        MakePlan("org.example.receipt", "tx-receipt", 1, bytes);
    VerifiedArtifactReceiptV1 mismatched = MakeVerified(receipt, bytes);
    mismatched.transactionId = "tx-other";
    result = layout.Finalize(receipt, mismatched, fd, &noFault);
    Emit("N02-receipt-mismatch", result);
    EXPECT_EQ(result.verdict, LayoutVerdict::VERIFIED_RECEIPT_MISMATCH);

    fs::create_directories(managedRoot / "u0");
    const fs::path outside = runRoot / "outside";
    fs::create_directories(outside);
    EXPECT_TRUE(symlink(outside.c_str(),
        (managedRoot / "u0/org.example.symlink").c_str()) == 0);
    FilePlanV1 symlinkPlan =
        MakePlan("org.example.symlink", "tx-symlink", 1, bytes);
    result = layout.Finalize(
        symlinkPlan, MakeVerified(symlinkPlan, bytes), fd, &noFault);
    Emit("N01-symlink-escape", result);
    EXPECT_EQ(result.verdict, LayoutVerdict::SYMLINK_ESCAPE);
    EXPECT_TRUE(fs::is_empty(outside));

    FilePlanV1 noSpace =
        MakePlan("org.example.nospace", "tx-nospace", 1, bytes);
    OneFault noSpaceFault(
        LayoutFaultPhase::DURING_COPY, LayoutFaultDecision::FAIL_NO_SPACE);
    result = layout.Finalize(
        noSpace, MakeVerified(noSpace, bytes), fd, &noSpaceFault);
    Emit("N01-no-space", result);
    EXPECT_EQ(result.verdict, LayoutVerdict::NO_SPACE);

    FilePlanV1 denied =
        MakePlan("org.example.denied", "tx-denied", 1, bytes);
    OneFault deniedFault(
        LayoutFaultPhase::DURING_COPY, LayoutFaultDecision::FAIL_PERMISSION);
    result =
        layout.Finalize(denied, MakeVerified(denied, bytes), fd, &deniedFault);
    Emit("N01-permission", result);
    EXPECT_EQ(result.verdict, LayoutVerdict::PERMISSION_DENIED);
    close(fd);
}

void TestFailureAndRestart(const fs::path& runRoot)
{
    const fs::path managedRoot = runRoot / "f01-managed";
    fs::create_directories(managedRoot);
    PackageLayoutV1 layout(managedRoot.string(), MakePolicy(managedRoot));
    NoLayoutFaultInjector noFault;
    const std::string oldBytes = "published-old-generation";
    const FilePlanV1 oldPlan =
        MakePlan("org.example.upgrade", "tx-old", 1, oldBytes);
    const int oldFd = WriteArtifact(runRoot / "f01-old.input.apk", oldBytes);
    const PackageLayoutReceiptV1 oldReceipt =
        layout.Finalize(oldPlan, MakeVerified(oldPlan, oldBytes), oldFd, &noFault);
    EXPECT_EQ(oldReceipt.verdict, LayoutVerdict::FINALIZED);

    const std::vector<std::pair<LayoutFaultPhase, LayoutFaultDecision>> faults = {
        {LayoutFaultPhase::DURING_COPY, LayoutFaultDecision::FAIL_IO},
        {LayoutFaultPhase::AFTER_FILE_FSYNC, LayoutFaultDecision::FAIL_NO_SPACE},
        {LayoutFaultPhase::BEFORE_RENAME,
            LayoutFaultDecision::FAIL_PERMISSION},
    };
    size_t index = 0;
    for (const auto& [phase, decision] : faults) {
        const std::string transaction = "tx-fail-" + std::to_string(index);
        const std::string newBytes = "new-generation-" + std::to_string(index);
        const FilePlanV1 plan =
            MakePlan("org.example.upgrade", transaction, 2 + index, newBytes);
        const fs::path input =
            runRoot / ("f01-new-" + std::to_string(index) + ".input.apk");
        const int fd = WriteArtifact(input, newBytes);
        OneFault fault(phase, decision);
        const PackageLayoutReceiptV1 result =
            layout.Finalize(plan, MakeVerified(plan, newBytes), fd, &fault);
        Emit("F01-" + std::to_string(index), result);
        EXPECT_TRUE(result.verdict != LayoutVerdict::FINALIZED);
        const fs::path generation = managedRoot / "u0/org.example.upgrade" /
            ("g" + std::to_string(plan.generation));
        EXPECT_TRUE(!fs::exists(generation / "base.apk"));
        EXPECT_EQ(ReadFile(oldReceipt.baseCode.path), oldBytes);
        close(fd);
        ++index;
    }

    const std::string renameBytes = "restart-after-rename";
    const FilePlanV1 renamePlan =
        MakePlan("org.example.restart", "tx-restart-rename", 4, renameBytes);
    const int renameFd =
        WriteArtifact(runRoot / "f02-rename.input.apk", renameBytes);
    OneFault afterRename(
        LayoutFaultPhase::AFTER_RENAME, LayoutFaultDecision::INTERRUPT);
    PackageLayoutReceiptV1 result = layout.Finalize(
        renamePlan, MakeVerified(renamePlan, renameBytes), renameFd, &afterRename);
    Emit("F02-after-rename-interrupt", result);
    EXPECT_EQ(result.verdict, LayoutVerdict::INTERRUPTED);
    PackageLayoutV1 restarted(managedRoot.string(), MakePolicy(managedRoot));
    result = restarted.Finalize(
        renamePlan, MakeVerified(renamePlan, renameBytes), renameFd, &noFault);
    Emit("F02-after-rename-replay", result);
    EXPECT_EQ(result.verdict, LayoutVerdict::FINALIZED);
    EXPECT_EQ(ReadFile(result.baseCode.path), renameBytes);
    close(renameFd);

    const std::vector<std::pair<LayoutFaultPhase, std::string>> replayPhases = {
        {LayoutFaultPhase::AFTER_PLAN_DURABLE, "after-plan"},
        {LayoutFaultPhase::DURING_COPY, "during-copy"},
        {LayoutFaultPhase::BEFORE_READBACK, "before-readback"},
    };
    uint64_t replayGeneration = 10;
    for (const auto& [phase, label] : replayPhases) {
        const std::string bytes = "restart-" + label;
        const std::string transaction = "tx-restart-" + label;
        const FilePlanV1 plan = MakePlan(
            "org.example." + std::to_string(replayGeneration),
            transaction, replayGeneration, bytes);
        const int fd =
            WriteArtifact(runRoot / ("f02-" + label + ".input.apk"), bytes);
        OneFault interruption(phase, LayoutFaultDecision::INTERRUPT);
        result = layout.Finalize(
            plan, MakeVerified(plan, bytes), fd, &interruption);
        Emit("F02-" + label + "-interrupt", result);
        EXPECT_EQ(result.verdict, LayoutVerdict::INTERRUPTED);
        result =
            restarted.Finalize(plan, MakeVerified(plan, bytes), fd, &noFault);
        Emit("F02-" + label + "-replay", result);
        EXPECT_EQ(result.verdict, LayoutVerdict::FINALIZED);
        EXPECT_EQ(ReadFile(result.baseCode.path), bytes);
        close(fd);
        ++replayGeneration;
    }

    const std::string receiptBytes = "restart-after-receipt";
    const FilePlanV1 receiptPlan =
        MakePlan("org.example.receiptrestart", "tx-restart-receipt", 9,
            receiptBytes);
    const int receiptFd =
        WriteArtifact(runRoot / "f02-receipt.input.apk", receiptBytes);
    OneFault afterReceipt(
        LayoutFaultPhase::AFTER_RECEIPT_DURABLE, LayoutFaultDecision::INTERRUPT);
    result = layout.Finalize(receiptPlan, MakeVerified(receiptPlan, receiptBytes),
        receiptFd, &afterReceipt);
    Emit("F02-after-receipt-interrupt", result);
    EXPECT_EQ(result.verdict, LayoutVerdict::INTERRUPTED);
    result = restarted.Finalize(receiptPlan,
        MakeVerified(receiptPlan, receiptBytes), receiptFd, &noFault);
    Emit("F02-after-receipt-replay", result);
    EXPECT_EQ(result.verdict, LayoutVerdict::FINALIZED);
    close(receiptFd);
    close(oldFd);
}

void TestConcurrentSingleWriter(const fs::path& runRoot)
{
    const fs::path managedRoot = runRoot / "concurrent-managed";
    fs::create_directories(managedRoot);
    PackageLayoutV1 layout(managedRoot.string(), MakePolicy(managedRoot));
    NoLayoutFaultInjector noFault;
    const std::string bytesA = "concurrent-artifact-a";
    const std::string bytesB = "concurrent-artifact-b";
    const FilePlanV1 planA =
        MakePlan("org.example.concurrent", "tx-concurrent-a", 3, bytesA);
    const FilePlanV1 planB =
        MakePlan("org.example.concurrent", "tx-concurrent-b", 3, bytesB);
    const int fdA = WriteArtifact(runRoot / "concurrent-a.input.apk", bytesA);
    const int fdB = WriteArtifact(runRoot / "concurrent-b.input.apk", bytesB);
    std::atomic<int> ready{0};
    std::atomic<bool> start{false};
    PackageLayoutReceiptV1 resultA;
    PackageLayoutReceiptV1 resultB;
    int errorA = 0;
    int errorB = 0;
    auto invoke = [&](const FilePlanV1& plan, std::string_view bytes, int fd,
                      PackageLayoutReceiptV1* output, int* platformError) {
        ++ready;
        while (!start.load()) std::this_thread::yield();
        errno = 0;
        *output = layout.Finalize(plan, MakeVerified(plan, bytes), fd, &noFault);
        *platformError = errno;
    };
    std::thread first(invoke, std::cref(planA), std::string_view(bytesA), fdA,
        &resultA, &errorA);
    std::thread second(invoke, std::cref(planB), std::string_view(bytesB), fdB,
        &resultB, &errorB);
    while (ready.load() != 2) std::this_thread::yield();
    start.store(true);
    first.join();
    second.join();
    Emit("N02-concurrent-a", resultA);
    Emit("N02-concurrent-b", resultB);
    const bool aWon = resultA.verdict == LayoutVerdict::FINALIZED;
    if (resultA.verdict != LayoutVerdict::FINALIZED &&
        resultA.verdict != LayoutVerdict::TRANSACTION_CONFLICT) {
        std::cerr << "concurrent-a unexpected verdict="
                  << PackageLayoutV1::VerdictName(resultA.verdict)
                  << " errno=" << errorA << "\n";
    }
    if (resultB.verdict != LayoutVerdict::FINALIZED &&
        resultB.verdict != LayoutVerdict::TRANSACTION_CONFLICT) {
        std::cerr << "concurrent-b unexpected verdict="
                  << PackageLayoutV1::VerdictName(resultB.verdict)
                  << " errno=" << errorB << "\n";
    }
    EXPECT_TRUE(aWon || resultB.verdict == LayoutVerdict::FINALIZED);
    EXPECT_EQ(aWon ? resultB.verdict : resultA.verdict,
        LayoutVerdict::TRANSACTION_CONFLICT);
    const PackageLayoutReceiptV1& winner = aWon ? resultA : resultB;
    const std::string winnerBytes = aWon ? bytesA : bytesB;
    EXPECT_EQ(ReadFile(winner.baseCode.path), winnerBytes);
    const fs::path receiptPath =
        managedRoot / "u0/org.example.concurrent/g3/file-receipt.v1.json";
    EXPECT_EQ(ReadFile(receiptPath),
        PackageLayoutV1::SerializeReceipt(winner));
    close(fdA);
    close(fdB);
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::cerr << "usage: package_layout_host_test OUTPUT_ROOT\n";
        return 2;
    }
    const fs::path runRoot(argv[1]);
    fs::create_directories(runRoot);
    gResponses.open(runRoot / "responses.jsonl", std::ios::binary);
    if (!gResponses.good()) return 2;

    TestPositiveAndReplay(runRoot);
    TestNegativeBoundaries(runRoot);
    TestFailureAndRestart(runRoot);
    TestConcurrentSingleWriter(runRoot);

    std::ofstream summary(runRoot / "summary.json", std::ios::binary);
    summary << "{\"actionId\":\"Fn01.A07\",\"developerTest\":"
            << (gFailures == 0 ? "\"READY_FOR_HANDOFF\"" : "\"FAILED\"")
            << ",\"formalVerdict\":\"NOT_ISSUED\",\"failures\":"
            << gFailures << "}\n";
    std::cout << "FN01_A07_DEVELOPER_TEST failures=" << gFailures
              << " evidence=" << runRoot << "\n";
    return gFailures == 0 ? 0 : 1;
}
