#include "bms_projection_v1.h"

#include "sha256.h"

#include <cerrno>
#include <condition_variable>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <sstream>
#include <string>
#include <string_view>
#include <sys/types.h>
#include <thread>
#include <unistd.h>
#include <utility>
#include <vector>

namespace fs = std::filesystem;
using namespace oh_adapter::bms_projection;

namespace {

std::string Digest(std::string_view value)
{
    unsigned char bytes[32]{};
    sha256(reinterpret_cast<const uint8_t*>(value.data()), value.size(), bytes);
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(sizeof(bytes) * 2, '0');
    for (size_t index = 0; index < sizeof(bytes); ++index) {
        result[index * 2] = kHex[bytes[index] >> 4];
        result[index * 2 + 1] = kHex[bytes[index] & 0x0f];
    }
    return result;
}

std::string Hex(std::string_view value)
{
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result;
    result.reserve(value.size() * 2);
    for (const unsigned char character : value) {
        result.push_back(kHex[character >> 4]);
        result.push_back(kHex[character & 0x0f]);
    }
    return result;
}

bool Unhex(const std::string& value, std::string* decoded)
{
    if (decoded == nullptr || value.size() % 2 != 0) return false;
    auto nibble = [](char value) -> int {
        if (value >= '0' && value <= '9') return value - '0';
        if (value >= 'a' && value <= 'f') return value - 'a' + 10;
        return -1;
    };
    decoded->clear();
    decoded->reserve(value.size() / 2);
    for (size_t index = 0; index < value.size(); index += 2) {
        const int high = nibble(value[index]);
        const int low = nibble(value[index + 1]);
        if (high < 0 || low < 0) return false;
        decoded->push_back(static_cast<char>((high << 4) | low));
    }
    return true;
}

bool AtomicWrite(const fs::path& path, const std::string& value)
{
    fs::create_directories(path.parent_path());
    const fs::path temporary = path.string() + ".tmp." +
        std::to_string(static_cast<unsigned long long>(getpid()));
    {
        std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
        if (!output) return false;
        output << value;
        output.flush();
        if (!output) return false;
    }
    std::error_code error;
    fs::rename(temporary, path, error);
    if (error) {
        fs::remove(temporary);
        return false;
    }
    return true;
}

bool ReadFile(const fs::path& path, std::string* value)
{
    if (value == nullptr) return false;
    std::ifstream input(path, std::ios::binary);
    if (!input) return false;
    std::ostringstream buffer;
    buffer << input.rdbuf();
    *value = buffer.str();
    return input.good() || input.eof();
}

bool AtomicCreateOrExact(const fs::path& path, const std::string& value)
{
    fs::create_directories(path.parent_path());
    std::string pattern = path.string() + ".claim.XXXXXX";
    std::vector<char> temporary(pattern.begin(), pattern.end());
    temporary.push_back('\0');
    const int fd = mkstemp(temporary.data());
    if (fd < 0) return false;
    bool written = true;
    size_t offset = 0;
    while (offset < value.size()) {
        const ssize_t count =
            ::write(fd, value.data() + offset, value.size() - offset);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) {
            written = false;
            break;
        }
        offset += static_cast<size_t>(count);
    }
    if (written && fsync(fd) != 0) written = false;
    if (close(fd) != 0) written = false;
    bool result = false;
    if (written && link(temporary.data(), path.c_str()) == 0) {
        result = true;
    } else if (written && errno == EEXIST) {
        std::string current;
        result = ReadFile(path, &current) && current == value;
    }
    unlink(temporary.data());
    return result;
}

std::vector<std::string> SplitLines(const std::string& value)
{
    std::vector<std::string> lines;
    std::istringstream input(value);
    std::string line;
    while (std::getline(input, line)) lines.push_back(line);
    return lines;
}

std::string Key(
    const std::string& packageName, uint32_t userId, uint64_t generation)
{
    return Hex(packageName) + "-" + std::to_string(userId) + "-" +
        std::to_string(generation);
}

std::string EncodeReceipt(const ProjectionReceiptV1& receipt)
{
    std::ostringstream output;
    output << receipt.schemaVersion << "\n"
           << Hex(receipt.requestId) << "\n"
           << Hex(receipt.transactionId) << "\n"
           << Hex(receipt.packageName) << "\n"
           << receipt.userId << "\n"
           << receipt.generation << "\n"
           << receipt.canonicalDigest << "\n"
           << receipt.resourcePayloadDigest << "\n"
           << receipt.projectionDigest << "\n"
           << static_cast<int>(receipt.projectionState) << "\n"
           << static_cast<int>(receipt.tokenState) << "\n"
           << static_cast<int>(receipt.verdict) << "\n"
           << Hex(receipt.reason) << "\n"
           << Hex(receipt.actionId) << "\n"
           << Hex(receipt.operation) << "\n"
           << receipt.requestDigest << "\n";
    return output.str();
}

bool DecodeReceipt(const std::string& encoded, ProjectionReceiptV1* receipt)
{
    if (receipt == nullptr) return false;
    const auto lines = SplitLines(encoded);
    if (lines.size() != 13 && lines.size() != 16) return false;
    try {
        receipt->schemaVersion = static_cast<uint32_t>(std::stoul(lines[0]));
        if (!Unhex(lines[1], &receipt->requestId) ||
            !Unhex(lines[2], &receipt->transactionId) ||
            !Unhex(lines[3], &receipt->packageName) ||
            !Unhex(lines[12], &receipt->reason)) {
            return false;
        }
        receipt->userId = static_cast<uint32_t>(std::stoul(lines[4]));
        receipt->generation = std::stoull(lines[5]);
        receipt->canonicalDigest = lines[6];
        receipt->resourcePayloadDigest = lines[7];
        receipt->projectionDigest = lines[8];
        receipt->projectionState =
            static_cast<ProjectionState>(std::stoi(lines[9]));
        receipt->tokenState =
            static_cast<PublicationTokenState>(std::stoi(lines[10]));
        receipt->verdict =
            static_cast<ProjectionVerdict>(std::stoi(lines[11]));
        if (lines.size() == 16) {
            if (!Unhex(lines[13], &receipt->actionId) ||
                !Unhex(lines[14], &receipt->operation)) {
                return false;
            }
            receipt->requestDigest = lines[15];
        } else {
            receipt->actionId = "Fn01.A10";
            receipt->operation.clear();
            receipt->requestDigest.clear();
        }
        return true;
    } catch (...) {
        return false;
    }
}

class FileOutbox final : public ProjectionOutboxV1 {
public:
    explicit FileOutbox(fs::path root) : root_(std::move(root)) {}

    bool PutIntent(
        const std::string& requestId, const std::string& encodedIntent) override
    {
        const fs::path path = root_ / "intent" / Hex(requestId);
        return AtomicCreateOrExact(path, encodedIntent);
    }

    bool PutReceipt(
        const std::string& requestId,
        const ProjectionReceiptV1& receipt) override
    {
        const fs::path path = root_ / "receipt" / Hex(requestId);
        const std::string encoded = EncodeReceipt(receipt);
        std::string current;
        if (ReadFile(path, &current)) return current == encoded;
        return AtomicWrite(path, encoded);
    }

    bool GetIntent(
        const std::string& requestId,
        std::string* encodedIntent) const override
    {
        return ReadFile(root_ / "intent" / Hex(requestId), encodedIntent);
    }

    bool GetReceipt(
        const std::string& requestId,
        ProjectionReceiptV1* receipt) const override
    {
        std::string encoded;
        return ReadFile(root_ / "receipt" / Hex(requestId), &encoded) &&
            DecodeReceipt(encoded, receipt);
    }

    bool ReplaceReceiptForTest(
        const std::string& requestId,
        const ProjectionReceiptV1& receipt)
    {
        return AtomicWrite(
            root_ / "receipt" / Hex(requestId), EncodeReceipt(receipt));
    }

    bool HasIntent(const std::string& requestId) const
    {
        return fs::is_regular_file(root_ / "intent" / Hex(requestId));
    }

private:
    fs::path root_;
};

class TwoPartyGate {
public:
    void ArriveAndWait()
    {
        std::unique_lock<std::mutex> lock(mutex_);
        ++arrived_;
        if (arrived_ == 2) {
            released_ = true;
            condition_.notify_all();
            return;
        }
        condition_.wait(lock, [this] { return released_; });
    }

private:
    std::mutex mutex_;
    std::condition_variable condition_;
    size_t arrived_ = 0;
    bool released_ = false;
};

class RacingOutbox final : public ProjectionOutboxV1 {
public:
    RacingOutbox(fs::path root, TwoPartyGate* gate)
        : delegate_(std::move(root)), gate_(gate)
    {
    }

    bool PutIntent(
        const std::string& requestId,
        const std::string& encodedIntent) override
    {
        return delegate_.PutIntent(requestId, encodedIntent);
    }

    bool GetIntent(
        const std::string& requestId,
        std::string* encodedIntent) const override
    {
        if (!waited_) {
            waited_ = true;
            gate_->ArriveAndWait();
        }
        return delegate_.GetIntent(requestId, encodedIntent);
    }

    bool PutReceipt(
        const std::string& requestId,
        const ProjectionReceiptV1& receipt) override
    {
        return delegate_.PutReceipt(requestId, receipt);
    }

    bool GetReceipt(
        const std::string& requestId,
        ProjectionReceiptV1* receipt) const override
    {
        return delegate_.GetReceipt(requestId, receipt);
    }

    bool GetStoredIntent(
        const std::string& requestId, std::string* encodedIntent) const
    {
        return delegate_.GetIntent(requestId, encodedIntent);
    }

private:
    FileOutbox delegate_;
    TwoPartyGate* gate_;
    mutable bool waited_ = false;
};

std::string EncodeRuntime(
    const HostProjectionRuntimeV1& runtime,
    const std::string& transactionId)
{
    const auto& payload = runtime.payload;
    std::ostringstream output;
    output << payload.schemaVersion << "\n"
           << Hex(payload.packageName) << "\n"
           << payload.userId << "\n"
           << payload.generation << "\n"
           << Hex(payload.hostIdentity.bundleName) << "\n"
           << Hex(payload.hostIdentity.appId) << "\n"
           << payload.hostIdentity.uid << "\n"
           << payload.hostIdentity.accessTokenId << "\n"
           << payload.canonicalDigest << "\n"
           << payload.resourcePayloadDigest << "\n"
           << payload.componentFactsDigest << "\n"
           << payload.managedPathDigest << "\n"
           << runtime.projectionDigest << "\n"
           << static_cast<int>(runtime.state) << "\n"
           << Hex(transactionId) << "\n";
    return output.str();
}

bool DecodeRuntime(
    const std::string& encoded, HostProjectionRuntimeV1* runtime,
    std::string* transactionId)
{
    if (runtime == nullptr || transactionId == nullptr) return false;
    const auto lines = SplitLines(encoded);
    if (lines.size() != 15) return false;
    try {
        runtime->payload.schemaVersion =
            static_cast<uint32_t>(std::stoul(lines[0]));
        if (!Unhex(lines[1], &runtime->payload.packageName) ||
            !Unhex(lines[4], &runtime->payload.hostIdentity.bundleName) ||
            !Unhex(lines[5], &runtime->payload.hostIdentity.appId) ||
            !Unhex(lines[14], transactionId)) {
            return false;
        }
        runtime->payload.userId =
            static_cast<uint32_t>(std::stoul(lines[2]));
        runtime->payload.generation = std::stoull(lines[3]);
        runtime->payload.hostIdentity.uid = std::stoull(lines[6]);
        runtime->payload.hostIdentity.accessTokenId = std::stoull(lines[7]);
        runtime->payload.canonicalDigest = lines[8];
        runtime->payload.resourcePayloadDigest = lines[9];
        runtime->payload.componentFactsDigest = lines[10];
        runtime->payload.managedPathDigest = lines[11];
        runtime->projectionDigest = lines[12];
        runtime->state =
            static_cast<ProjectionState>(std::stoi(lines[13]));
        return true;
    } catch (...) {
        return false;
    }
}

class FileBmsAdapter final : public BmsProjectionAdapterV1 {
public:
    explicit FileBmsAdapter(fs::path root) : root_(std::move(root)) {}

    BackendResult AllocateIdentity(
        const std::string& packageName, uint32_t userId, uint64_t generation,
        const std::string&, HostIdentityV1* identity) override
    {
        if (identity == nullptr) return BackendResult::IO_ERROR;
        const std::string seed =
            packageName + ":" + std::to_string(userId) + ":" +
            std::to_string(generation);
        const std::string digest = Digest(seed);
        identity->bundleName =
            packageName + ".g" + std::to_string(generation);
        identity->appId = "app." + digest.substr(0, 24);
        identity->uid =
            200000 + std::stoull(digest.substr(0, 6), nullptr, 16);
        identity->accessTokenId =
            400000 + std::stoull(digest.substr(6, 6), nullptr, 16);
        return denyAllocation_ ? BackendResult::DENIED : BackendResult::OK;
    }

    BackendResult CreatePrepared(
        const HostProjectionRuntimeV1& expected,
        const std::string& transactionId,
        HostProjectionRuntimeV1* readback) override
    {
        if (denyCreate_) return BackendResult::DENIED;
        const fs::path path = RuntimePath(expected.payload.packageName,
            expected.payload.userId, expected.payload.generation);
        std::string encoded;
        if (ReadFile(path, &encoded)) {
            HostProjectionRuntimeV1 existing;
            std::string owner;
            if (!DecodeRuntime(encoded, &existing, &owner)) {
                return BackendResult::IO_ERROR;
            }
            if (BmsProjectionCoordinatorV1::CanonicalPayload(existing.payload) !=
                    BmsProjectionCoordinatorV1::CanonicalPayload(
                        expected.payload) ||
                existing.projectionDigest != expected.projectionDigest ||
                (existing.state != ProjectionState::PREPARED &&
                    existing.state != ProjectionState::ACTIVE)) {
                return BackendResult::COLLISION;
            }
            if (readback != nullptr) *readback = existing;
            return BackendResult::OK;
        }
        if (!AtomicWrite(path, EncodeRuntime(expected, transactionId))) {
            return BackendResult::IO_ERROR;
        }
        if (readback != nullptr) *readback = expected;
        return BackendResult::OK;
    }

    BackendResult Activate(
        const std::string& packageName, uint32_t userId, uint64_t generation,
        const std::string& canonicalDigest,
        const std::string& projectionDigest,
        const std::string& transactionId,
        HostProjectionRuntimeV1* readback) override
    {
        if (denyActivation_) return BackendResult::DENIED;
        HostProjectionRuntimeV1 runtime;
        std::string owner;
        if (!ReadRuntime(
                packageName, userId, generation, &runtime, &owner)) {
            return BackendResult::NOT_FOUND;
        }
        if (owner != transactionId) {
            return BackendResult::OWNER_MISMATCH;
        }
        if (runtime.payload.canonicalDigest != canonicalDigest ||
            runtime.projectionDigest != projectionDigest) {
            return BackendResult::COLLISION;
        }
        runtime.state = ProjectionState::ACTIVE;
        if (!AtomicWrite(RuntimePath(packageName, userId, generation),
                EncodeRuntime(runtime, owner))) {
            return BackendResult::IO_ERROR;
        }
        if (readback != nullptr) *readback = runtime;
        return BackendResult::OK;
    }

    BackendResult Read(
        const std::string& packageName, uint32_t userId, uint64_t generation,
        HostProjectionRuntimeV1* readback) const override
    {
        std::string owner;
        if (!ReadRuntime(
                packageName, userId, generation, readback, &owner)) {
            return BackendResult::NOT_FOUND;
        }
        if (corruptNextRead_ && readback != nullptr) {
            readback->projectionDigest = Digest("corrupt-readback");
            corruptNextRead_ = false;
        }
        return BackendResult::OK;
    }

    BackendResult RemovePrepared(
        const std::string& packageName, uint32_t userId, uint64_t generation,
        const std::string& transactionId) override
    {
        HostProjectionRuntimeV1 runtime;
        std::string owner;
        if (!ReadRuntime(
                packageName, userId, generation, &runtime, &owner)) {
            return BackendResult::NOT_FOUND;
        }
        if (runtime.state != ProjectionState::PREPARED ||
            owner != transactionId) {
            return BackendResult::COLLISION;
        }
        std::error_code error;
        fs::remove(RuntimePath(packageName, userId, generation), error);
        return error ? BackendResult::IO_ERROR : BackendResult::OK;
    }

    void SetPendingTransaction(std::string transactionId)
    {
        pendingTransaction_ = std::move(transactionId);
    }
    void DenyAllocation(bool value) { denyAllocation_ = value; }
    void DenyCreate(bool value) { denyCreate_ = value; }
    void DenyActivation(bool value) { denyActivation_ = value; }
    void CorruptNextRead() const { corruptNextRead_ = true; }

    bool Seed(
        const HostProjectionRuntimeV1& runtime,
        const std::string& transactionId)
    {
        return AtomicWrite(RuntimePath(runtime.payload.packageName,
            runtime.payload.userId, runtime.payload.generation),
            EncodeRuntime(runtime, transactionId));
    }

    size_t RecordCount() const
    {
        const fs::path directory = root_ / "records";
        if (!fs::exists(directory)) return 0;
        size_t count = 0;
        for (const auto& entry : fs::directory_iterator(directory)) {
            if (entry.is_regular_file()) ++count;
        }
        return count;
    }

private:
    fs::path RuntimePath(
        const std::string& packageName, uint32_t userId,
        uint64_t generation) const
    {
        return root_ / "records" / Key(packageName, userId, generation);
    }

    bool ReadRuntime(
        const std::string& packageName, uint32_t userId, uint64_t generation,
        HostProjectionRuntimeV1* runtime, std::string* owner) const
    {
        std::string encoded;
        return ReadFile(RuntimePath(packageName, userId, generation), &encoded) &&
            DecodeRuntime(encoded, runtime, owner);
    }

    fs::path root_;
    std::string pendingTransaction_;
    bool denyAllocation_ = false;
    bool denyCreate_ = false;
    bool denyActivation_ = false;
    mutable bool corruptNextRead_ = false;
};

class FileTokenStore final : public PublicationTokenStoreV1 {
public:
    explicit FileTokenStore(fs::path root) : root_(std::move(root)) {}

    bool Read(
        const std::string& packageName, uint32_t userId, uint64_t generation,
        PublicationTokenState* state) const override
    {
        if (state == nullptr) return false;
        std::string encoded;
        if (!ReadFile(Path(packageName, userId, generation), &encoded)) {
            return false;
        }
        try {
            *state = static_cast<PublicationTokenState>(std::stoi(encoded));
            return true;
        } catch (...) {
            return false;
        }
    }

    bool CompareAndSwap(
        const std::string& packageName, uint32_t userId, uint64_t generation,
        PublicationTokenState expected,
        PublicationTokenState desired) override
    {
        PublicationTokenState current;
        if (failNextCas_) {
            failNextCas_ = false;
            return false;
        }
        return Read(packageName, userId, generation, &current) &&
            current == expected &&
            AtomicWrite(Path(packageName, userId, generation),
                std::to_string(static_cast<int>(desired)));
    }

    bool Seed(
        const std::string& packageName, uint32_t userId, uint64_t generation,
        PublicationTokenState state)
    {
        return AtomicWrite(Path(packageName, userId, generation),
            std::to_string(static_cast<int>(state)));
    }

    void FailNextCas() { failNextCas_ = true; }

private:
    fs::path Path(
        const std::string& packageName, uint32_t userId,
        uint64_t generation) const
    {
        return root_ / "tokens" / Key(packageName, userId, generation);
    }

    fs::path root_;
    bool failNextCas_ = false;
};

class OneShotFault final : public ProjectionFaultInjector {
public:
    explicit OneShotFault(ProjectionFaultPhase phase) : phase_(phase) {}
    bool InterruptAt(ProjectionFaultPhase phase) override
    {
        if (!fired_ && phase == phase_) {
            fired_ = true;
            return true;
        }
        return false;
    }

private:
    ProjectionFaultPhase phase_;
    bool fired_ = false;
};

struct Fixture {
    CommandEnvelopeV1 prepareEnvelope;
    CommandEnvelopeV1 activationEnvelope;
    P4CandidateFixtureV1 candidate;
    ResourceProjectionReadyReceiptV1 resource;
};

Fixture MakeFixture(const std::string& packageName, uint64_t generation)
{
    Fixture fixture;
    fixture.prepareEnvelope.requestId =
        "prepare-" + Digest(packageName).substr(0, 16);
    fixture.prepareEnvelope.callerScopeDigest = Digest("caller-scope-v1");
    fixture.prepareEnvelope.policyVersion = "fn01-bms-projection-v1";
    fixture.activationEnvelope.requestId =
        "activate-" + Digest(packageName).substr(0, 16);
    fixture.activationEnvelope.callerScopeDigest =
        fixture.prepareEnvelope.callerScopeDigest;
    fixture.activationEnvelope.policyVersion =
        fixture.prepareEnvelope.policyVersion;
    fixture.candidate.packageName = packageName;
    fixture.candidate.candidateGeneration = generation;
    fixture.candidate.canonicalDigest =
        Digest("canonical:" + packageName + ":" + std::to_string(generation));
    fixture.candidate.resourcePayloadDigest =
        Digest("resource:" + packageName + ":" + std::to_string(generation));
    fixture.candidate.componentFactsDigest =
        Digest("components:" + packageName + ":" + std::to_string(generation));
    fixture.candidate.managedPathDigest =
        Digest("paths:" + packageName + ":" + std::to_string(generation));
    fixture.candidate.canonicalCandidateState = "DURABLE";
    fixture.candidate.transactionId =
        "tx-" + Digest(packageName).substr(0, 16);
    fixture.candidate.recordVersion = 7;
    fixture.resource.requestId =
        "resource-" + Digest(packageName).substr(0, 16);
    fixture.resource.transactionId = fixture.candidate.transactionId;
    fixture.resource.packageName = packageName;
    fixture.resource.generation = generation;
    fixture.resource.canonicalDigest = fixture.candidate.canonicalDigest;
    fixture.resource.resourceInputDigest =
        Digest("resource-input:" + packageName + ":" +
            std::to_string(generation));
    fixture.resource.resourcePayloadDigest =
        fixture.candidate.resourcePayloadDigest;
    fixture.resource.buildPolicyVersion = "fn01-resource-projection-v1";
    fixture.resource.payloadKind =
        generation % 2 == 0 ? "EMPTY" : "MATERIALIZED";
    fixture.resource.state = "READY";
    fixture.resource.verdict = "READY";
    return fixture;
}

PostP5ActivationFixtureV1 ActivationFixture(
    const Fixture& fixture, const ProjectionReceiptV1& prepared)
{
    PostP5ActivationFixtureV1 activation;
    activation.packageName = fixture.candidate.packageName;
    activation.generation = fixture.candidate.candidateGeneration;
    activation.canonicalDigest = fixture.candidate.canonicalDigest;
    activation.projectionDigest = prepared.projectionDigest;
    activation.resourcePayloadDigest =
        fixture.candidate.resourcePayloadDigest;
    activation.canonicalState = "ACTIVE";
    activation.transactionId = fixture.candidate.transactionId;
    activation.recordVersion = fixture.candidate.recordVersion + 1;
    return activation;
}

class TestRun {
public:
    explicit TestRun(fs::path output)
        : output_(std::move(output)),
          responses_(output_ / "responses.jsonl", std::ios::trunc)
    {
        fs::create_directories(output_);
        if (!responses_) throw std::runtime_error("cannot open responses");
    }

    std::string NextPackage(std::string_view caseName)
    {
        ++counter_;
        return "fixture.dynamic." + std::to_string(getpid()) + "." +
            std::to_string(counter_) + "." +
            Digest(caseName).substr(0, 8);
    }

    void Record(
        const std::string& caseId, const ProjectionReceiptV1& receipt,
        bool passed, std::string extra = "")
    {
        responses_ << "{\"caseId\":\"" << caseId << "\",\"passed\":"
                   << (passed ? "true" : "false")
                   << ",\"receipt\":"
                   << BmsProjectionCoordinatorV1::SerializeReceipt(receipt);
        if (!extra.empty()) responses_ << ",\"note\":\"" << extra << "\"";
        responses_ << "}\n";
        ++cases_;
        if (!passed) ++failed_;
    }

    void Require(bool condition, const std::string& message)
    {
        if (!condition) throw std::runtime_error(message);
    }

    void Finish()
    {
        responses_.flush();
        std::ofstream summary(output_ / "summary.json", std::ios::trunc);
        summary << "{\"actionId\":\"Fn01.A10\",\"cases\":" << cases_
                << ",\"failed\":" << failed_
                << ",\"developerTest\":\""
                << (failed_ == 0 ? "READY_FOR_VERIFY" : "FAILED")
                << "\",\"formalVerdict\":\"NOT_ISSUED\"}\n";
        summary.flush();
        if (failed_ != 0) throw std::runtime_error("test cases failed");
    }

private:
    fs::path output_;
    std::ofstream responses_;
    size_t counter_ = 0;
    size_t cases_ = 0;
    size_t failed_ = 0;
};

BmsProjectionPolicyV1 Policy()
{
    BmsProjectionPolicyV1 policy;
    policy.policyVersion = "fn01-bms-projection-v1";
    policy.expectedCallerScopeDigest = Digest("caller-scope-v1");
    return policy;
}

void SeedP4Token(FileTokenStore* tokens, const Fixture& fixture)
{
    if (!tokens->Seed(fixture.candidate.packageName,
            fixture.candidate.userId,
            fixture.candidate.candidateGeneration,
            PublicationTokenState::PREPARED)) {
        throw std::runtime_error("cannot seed P4 token");
    }
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::cerr << "usage: " << argv[0] << " <fresh-output-dir>\n";
        return 64;
    }
    try {
        const fs::path output = argv[1];
        if (fs::exists(output)) {
            throw std::runtime_error("output directory must be fresh");
        }
        fs::create_directories(output);
        TestRun run(output);

        {
            const fs::path root = output / "p01";
            Fixture fixture = MakeFixture(run.NextPackage("p01"), 1);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            adapter.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens, fixture);
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const ProjectionReceiptV1 prepared = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            HostProjectionRuntimeV1 preparedReadback;
            PublicationTokenState token;
            const bool prepareOk =
                prepared.verdict == ProjectionVerdict::PREPARED &&
                adapter.Read(fixture.candidate.packageName, 0, 1,
                    &preparedReadback) == BackendResult::OK &&
                preparedReadback.state == ProjectionState::PREPARED &&
                tokens.Read(fixture.candidate.packageName, 0, 1, &token) &&
                token == PublicationTokenState::PREPARED &&
                prepared.projectionDigest ==
                    BmsProjectionCoordinatorV1::ProjectionDigest(
                        preparedReadback.payload);
            run.Record("P01a-p4-prepared-readback", prepared, prepareOk);
            run.Require(prepareOk, "P01a failed");

            run.Require(tokens.Seed(fixture.candidate.packageName, 0, 1,
                PublicationTokenState::CANONICAL_SELECTED),
                "cannot seed post-P5 token");
            const auto activation = ActivationFixture(fixture, prepared);
            const ProjectionReceiptV1 activated = coordinator.Activate(
                fixture.activationEnvelope, activation,
                fixture.resource, nullptr);
            HostProjectionRuntimeV1 activeReadback;
            const bool activationOk =
                activated.verdict == ProjectionVerdict::ACTIVATED &&
                adapter.Read(fixture.candidate.packageName, 0, 1,
                    &activeReadback) == BackendResult::OK &&
                activeReadback.state == ProjectionState::ACTIVE &&
                tokens.Read(fixture.candidate.packageName, 0, 1, &token) &&
                token == PublicationTokenState::EXTERNAL_READY;
            run.Record("P01b-controlled-activation", activated, activationOk);
            run.Require(activationOk, "P01b failed");

            const ProjectionReceiptV1 replay = coordinator.Activate(
                fixture.activationEnvelope, activation,
                fixture.resource, nullptr);
            const bool replayOk =
                replay.verdict == ProjectionVerdict::ACTIVATED &&
                replay.projectionDigest == activated.projectionDigest &&
                adapter.RecordCount() == 1;
            run.Record("P02-closed-replay-single-record", replay, replayOk);
            run.Require(replayOk, "P02 replay failed");
        }

        {
            const fs::path root = output / "p02-second-package";
            Fixture first = MakeFixture(run.NextPackage("p02-first"), 3);
            Fixture second = MakeFixture(run.NextPackage("p02-second"), 8);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            SeedP4Token(&tokens, first);
            SeedP4Token(&tokens, second);
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            adapter.SetPendingTransaction(first.candidate.transactionId);
            const auto firstReceipt = coordinator.Prepare(
                first.prepareEnvelope, first.candidate, first.resource, nullptr);
            adapter.SetPendingTransaction(second.candidate.transactionId);
            const auto secondReceipt = coordinator.Prepare(
                second.prepareEnvelope, second.candidate, second.resource,
                nullptr);
            const bool passed =
                firstReceipt.verdict == ProjectionVerdict::PREPARED &&
                secondReceipt.verdict == ProjectionVerdict::PREPARED &&
                firstReceipt.packageName != secondReceipt.packageName &&
                firstReceipt.generation != secondReceipt.generation &&
                adapter.RecordCount() == 2;
            run.Record("P02-dynamic-multi-package", secondReceipt, passed);
            run.Require(passed, "dynamic multi-package failed");
        }

        {
            const fs::path root = output / "n01-collision";
            Fixture fixture = MakeFixture(run.NextPackage("n01-collision"), 4);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            SeedP4Token(&tokens, fixture);
            HostProjectionRuntimeV1 foreign;
            foreign.payload.packageName = fixture.candidate.packageName;
            foreign.payload.generation = fixture.candidate.candidateGeneration;
            foreign.payload.canonicalDigest = Digest("foreign-canonical");
            foreign.payload.resourcePayloadDigest = Digest("foreign-resource");
            foreign.payload.componentFactsDigest = Digest("foreign-component");
            foreign.payload.managedPathDigest = Digest("foreign-path");
            foreign.payload.hostIdentity.bundleName =
                fixture.candidate.packageName + ".foreign";
            foreign.payload.hostIdentity.appId = "app.foreign";
            foreign.payload.hostIdentity.uid = 800001;
            foreign.payload.hostIdentity.accessTokenId = 900001;
            foreign.projectionDigest =
                BmsProjectionCoordinatorV1::ProjectionDigest(foreign.payload);
            foreign.state = ProjectionState::PREPARED;
            run.Require(adapter.Seed(foreign, "tx-foreign"),
                "cannot seed collision");
            adapter.SetPendingTransaction(fixture.candidate.transactionId);
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto receipt = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            const bool passed =
                receipt.verdict == ProjectionVerdict::HOST_COLLISION &&
                adapter.RecordCount() == 1;
            run.Record("N01-host-collision", receipt, passed);
            run.Require(passed, "collision did not reject");
        }

        {
            const fs::path root = output / "n01-host-denial";
            Fixture fixture = MakeFixture(run.NextPackage("n01-denial"), 5);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            SeedP4Token(&tokens, fixture);
            adapter.DenyCreate(true);
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto receipt = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            const bool passed =
                receipt.verdict == ProjectionVerdict::HOST_DENIED &&
                adapter.RecordCount() == 0 &&
                outbox.HasIntent(fixture.prepareEnvelope.requestId);
            run.Record("N01-host-denial-recoverable-intent", receipt, passed);
            run.Require(passed, "host denial did not fail closed");
        }

        {
            const fs::path root = output / "n02-caller";
            Fixture fixture = MakeFixture(run.NextPackage("n02-caller"), 6);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            SeedP4Token(&tokens, fixture);
            fixture.prepareEnvelope.callerScopeDigest = Digest("foreign");
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto receipt = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            const bool passed =
                receipt.verdict ==
                    ProjectionVerdict::CALLER_SCOPE_MISMATCH &&
                adapter.RecordCount() == 0;
            run.Record("N02-caller-scope", receipt, passed);
            run.Require(passed, "caller mismatch did not reject");
        }

        {
            const fs::path root = output / "n02-policy-version";
            Fixture fixture = MakeFixture(
                run.NextPackage("n02-policy-version"), 16);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            SeedP4Token(&tokens, fixture);
            fixture.prepareEnvelope.policyVersion =
                "foreign-bms-projection-policy";
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto receipt = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            const bool passed =
                receipt.verdict == ProjectionVerdict::INVALID_REQUEST &&
                !outbox.HasIntent(fixture.prepareEnvelope.requestId) &&
                adapter.RecordCount() == 0;
            run.Record("N02-policy-version-bound", receipt, passed);
            run.Require(passed, "policy version mismatch did not fail closed");
        }

        {
            const fs::path root = output / "n02-resource";
            Fixture fixture = MakeFixture(run.NextPackage("n02-resource"), 7);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            SeedP4Token(&tokens, fixture);
            fixture.resource.resourcePayloadDigest =
                Digest("copied-but-foreign-resource");
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto receipt = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            const bool passed =
                receipt.verdict ==
                    ProjectionVerdict::RESOURCE_RECEIPT_MISMATCH &&
                adapter.RecordCount() == 0;
            run.Record("N02-a08-receipt-digest", receipt, passed);
            run.Require(passed, "resource mismatch did not reject");
        }

        {
            const fs::path root = output / "n02-resource-provenance";
            Fixture fixture = MakeFixture(
                run.NextPackage("n02-resource-provenance"), 17);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            SeedP4Token(&tokens, fixture);
            fixture.resource.transactionId =
                "tx-" + Digest("foreign-a08-owner").substr(0, 16);
            fixture.resource.verdict = "READY";
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto receipt = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            const bool passed =
                receipt.verdict ==
                    ProjectionVerdict::TRANSACTION_MISMATCH &&
                !outbox.HasIntent(fixture.prepareEnvelope.requestId) &&
                adapter.RecordCount() == 0;
            run.Record("N02-a08-provenance-owner-bound", receipt, passed);
            run.Require(passed,
                "foreign A08 owner provenance was accepted");
        }

        {
            const fs::path root = output / "n03-order";
            Fixture fixture = MakeFixture(run.NextPackage("n03-order"), 9);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            adapter.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens, fixture);
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto prepared = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            const auto activation = ActivationFixture(fixture, prepared);
            const auto receipt = coordinator.Activate(
                fixture.activationEnvelope, activation,
                fixture.resource, nullptr);
            HostProjectionRuntimeV1 readback;
            PublicationTokenState token;
            const bool passed =
                receipt.verdict ==
                    ProjectionVerdict::ACTIVATION_NOT_AUTHORIZED &&
                adapter.Read(fixture.candidate.packageName, 0, 9, &readback) ==
                    BackendResult::OK &&
                readback.state == ProjectionState::PREPARED &&
                tokens.Read(fixture.candidate.packageName, 0, 9, &token) &&
                token == PublicationTokenState::PREPARED;
            run.Record("N03-pre-p5-activation-rejected", receipt, passed);
            run.Require(passed, "pre-P5 activation was not fenced");
        }

        {
            const fs::path root = output / "n02-transaction";
            Fixture fixture = MakeFixture(
                run.NextPackage("n02-transaction"), 14);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            adapter.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens, fixture);
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto prepared = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            run.Require(tokens.Seed(fixture.candidate.packageName, 0, 14,
                PublicationTokenState::CANONICAL_SELECTED),
                "cannot seed transaction mismatch token");
            auto activation = ActivationFixture(fixture, prepared);
            activation.transactionId =
                "tx-" + Digest("foreign-activation-owner").substr(0, 16);
            auto foreignResource = fixture.resource;
            foreignResource.transactionId = activation.transactionId;
            const auto receipt = coordinator.Activate(
                fixture.activationEnvelope, activation,
                foreignResource, nullptr);
            HostProjectionRuntimeV1 readback;
            PublicationTokenState token;
            const bool passed =
                receipt.verdict ==
                    ProjectionVerdict::TRANSACTION_MISMATCH &&
                receipt.reason == "host activation failed" &&
                adapter.Read(fixture.candidate.packageName, 0, 14,
                    &readback) == BackendResult::OK &&
                readback.state == ProjectionState::PREPARED &&
                tokens.Read(fixture.candidate.packageName, 0, 14, &token) &&
                token == PublicationTokenState::CANONICAL_SELECTED;
            run.Record("N02-activation-transaction-owner", receipt, passed);
            run.Require(passed, "activation transaction mismatch leaked");
        }

        {
            const fs::path root = output / "f01-readback";
            Fixture fixture = MakeFixture(run.NextPackage("f01-readback"), 10);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            adapter.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens, fixture);
            adapter.CorruptNextRead();
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto receipt = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            const bool passed =
                receipt.verdict == ProjectionVerdict::READBACK_MISMATCH &&
                adapter.RecordCount() == 0;
            run.Record("F01-readback-corruption-cleanup", receipt, passed);
            run.Require(passed, "corrupt PREPARED was not cleaned");
        }

        {
            const fs::path root = output / "f02-prepare-restart";
            Fixture fixture = MakeFixture(
                run.NextPackage("f02-prepare-restart"), 11);
            FileOutbox outbox1(root / "outbox");
            FileBmsAdapter adapter1(root / "bms");
            FileTokenStore tokens1(root / "token");
            adapter1.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens1, fixture);
            BmsProjectionCoordinatorV1 coordinator1(
                Policy(), &outbox1, &adapter1, &tokens1);
            OneShotFault fault(
                ProjectionFaultPhase::AFTER_PREPARED_DURABLE);
            const auto interrupted = coordinator1.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, &fault);
            FileOutbox outbox2(root / "outbox");
            FileBmsAdapter adapter2(root / "bms");
            FileTokenStore tokens2(root / "token");
            adapter2.SetPendingTransaction(fixture.candidate.transactionId);
            BmsProjectionCoordinatorV1 coordinator2(
                Policy(), &outbox2, &adapter2, &tokens2);
            const auto recovered = coordinator2.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            const bool passed =
                interrupted.verdict == ProjectionVerdict::INTERRUPTED &&
                recovered.verdict == ProjectionVerdict::PREPARED &&
                adapter2.RecordCount() == 1;
            run.Record("F02-prepare-restart-replay", recovered, passed);
            run.Require(passed, "PREPARED restart recovery failed");
        }

        {
            const fs::path root = output / "f02-active-restart";
            Fixture fixture = MakeFixture(
                run.NextPackage("f02-active-restart"), 12);
            FileOutbox outbox1(root / "outbox");
            FileBmsAdapter adapter1(root / "bms");
            FileTokenStore tokens1(root / "token");
            adapter1.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens1, fixture);
            BmsProjectionCoordinatorV1 coordinator1(
                Policy(), &outbox1, &adapter1, &tokens1);
            const auto prepared = coordinator1.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            run.Require(tokens1.Seed(fixture.candidate.packageName, 0, 12,
                PublicationTokenState::CANONICAL_SELECTED),
                "cannot seed activation token");
            const auto activation = ActivationFixture(fixture, prepared);
            OneShotFault fault(ProjectionFaultPhase::AFTER_ACTIVE_DURABLE);
            const auto interrupted = coordinator1.Activate(
                fixture.activationEnvelope, activation,
                fixture.resource, &fault);
            FileOutbox outbox2(root / "outbox");
            FileBmsAdapter adapter2(root / "bms");
            FileTokenStore tokens2(root / "token");
            BmsProjectionCoordinatorV1 coordinator2(
                Policy(), &outbox2, &adapter2, &tokens2);
            const auto recovered = coordinator2.Activate(
                fixture.activationEnvelope, activation,
                fixture.resource, nullptr);
            PublicationTokenState token;
            const bool passed =
                interrupted.verdict == ProjectionVerdict::INTERRUPTED &&
                recovered.verdict == ProjectionVerdict::ACTIVATED &&
                tokens2.Read(fixture.candidate.packageName, 0, 12, &token) &&
                token == PublicationTokenState::EXTERNAL_READY &&
                adapter2.RecordCount() == 1;
            run.Record("F02-active-before-token-restart", recovered, passed);
            run.Require(passed, "ACTIVE forward recovery failed");
        }

        {
            const fs::path root = output / "f02-token-restart";
            Fixture fixture = MakeFixture(
                run.NextPackage("f02-token-restart"), 13);
            FileOutbox outbox1(root / "outbox");
            FileBmsAdapter adapter1(root / "bms");
            FileTokenStore tokens1(root / "token");
            adapter1.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens1, fixture);
            BmsProjectionCoordinatorV1 coordinator1(
                Policy(), &outbox1, &adapter1, &tokens1);
            const auto prepared = coordinator1.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            run.Require(tokens1.Seed(fixture.candidate.packageName, 0, 13,
                PublicationTokenState::CANONICAL_SELECTED),
                "cannot seed activation token");
            const auto activation = ActivationFixture(fixture, prepared);
            OneShotFault fault(ProjectionFaultPhase::AFTER_TOKEN_CAS);
            const auto interrupted = coordinator1.Activate(
                fixture.activationEnvelope, activation,
                fixture.resource, &fault);
            FileOutbox outbox2(root / "outbox");
            FileBmsAdapter adapter2(root / "bms");
            FileTokenStore tokens2(root / "token");
            BmsProjectionCoordinatorV1 coordinator2(
                Policy(), &outbox2, &adapter2, &tokens2);
            const auto recovered = coordinator2.Activate(
                fixture.activationEnvelope, activation,
                fixture.resource, nullptr);
            PublicationTokenState token;
            const bool passed =
                interrupted.verdict == ProjectionVerdict::INTERRUPTED &&
                recovered.verdict == ProjectionVerdict::ACTIVATED &&
                recovered.reason.find("forward recovery") != std::string::npos &&
                tokens2.Read(fixture.candidate.packageName, 0, 13, &token) &&
                token == PublicationTokenState::EXTERNAL_READY &&
                adapter2.RecordCount() == 1;
            run.Record("F02-post-token-cas-restart", recovered, passed);
            run.Require(passed, "post-token CAS recovery failed");
        }

        {
            const fs::path root = output / "f02-prepare-intent-bound";
            Fixture fixture = MakeFixture(
                run.NextPackage("f02-prepare-intent-bound"), 24);
            FileOutbox outbox1(root / "outbox");
            FileBmsAdapter adapter1(root / "bms");
            FileTokenStore tokens1(root / "token");
            adapter1.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens1, fixture);
            BmsProjectionCoordinatorV1 coordinator1(
                Policy(), &outbox1, &adapter1, &tokens1);
            OneShotFault fault(
                ProjectionFaultPhase::AFTER_INTENT_DURABLE);
            const auto interrupted = coordinator1.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, &fault);
            std::string originalIntent;
            run.Require(outbox1.GetIntent(
                fixture.prepareEnvelope.requestId, &originalIntent),
                "prepare intent was not durable before interruption");

            FileOutbox outbox2(root / "outbox");
            FileBmsAdapter adapter2(root / "bms");
            FileTokenStore tokens2(root / "token");
            adapter2.SetPendingTransaction(fixture.candidate.transactionId);
            BmsProjectionCoordinatorV1 coordinator2(
                Policy(), &outbox2, &adapter2, &tokens2);
            auto changed = fixture.candidate;
            changed.componentFactsDigest =
                Digest("interrupted-changed-component-facts");
            const auto conflict = coordinator2.Prepare(
                fixture.prepareEnvelope, changed, fixture.resource, nullptr);
            std::string retainedIntent;
            run.Require(outbox2.GetIntent(
                fixture.prepareEnvelope.requestId, &retainedIntent),
                "prepare intent disappeared after conflict");
            const auto recovered = coordinator2.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            const bool passed =
                interrupted.verdict == ProjectionVerdict::INTERRUPTED &&
                conflict.verdict ==
                    ProjectionVerdict::IDEMPOTENCY_CONFLICT &&
                conflict.requestDigest != recovered.requestDigest &&
                originalIntent == retainedIntent &&
                recovered.verdict == ProjectionVerdict::PREPARED &&
                adapter2.RecordCount() == 1;
            run.Record("F02-interrupted-prepare-intent-bound",
                conflict, passed);
            run.Require(passed,
                "interrupted PREPARE intent was overwritten or ignored");
        }

        {
            const fs::path root = output / "f02-activation-intent-bound";
            Fixture fixture = MakeFixture(
                run.NextPackage("f02-activation-intent-bound"), 25);
            FileOutbox outbox1(root / "outbox");
            FileBmsAdapter adapter1(root / "bms");
            FileTokenStore tokens1(root / "token");
            adapter1.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens1, fixture);
            BmsProjectionCoordinatorV1 coordinator1(
                Policy(), &outbox1, &adapter1, &tokens1);
            const auto prepared = coordinator1.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            run.Require(tokens1.Seed(fixture.candidate.packageName, 0, 25,
                PublicationTokenState::CANONICAL_SELECTED),
                "cannot seed interrupted activation token");
            const auto activation = ActivationFixture(fixture, prepared);
            OneShotFault fault(
                ProjectionFaultPhase::AFTER_ACTIVATION_INTENT_DURABLE);
            const auto interrupted = coordinator1.Activate(
                fixture.activationEnvelope, activation,
                fixture.resource, &fault);
            std::string originalIntent;
            run.Require(outbox1.GetIntent(
                fixture.activationEnvelope.requestId, &originalIntent),
                "activation intent was not durable before interruption");

            FileOutbox outbox2(root / "outbox");
            FileBmsAdapter adapter2(root / "bms");
            FileTokenStore tokens2(root / "token");
            BmsProjectionCoordinatorV1 coordinator2(
                Policy(), &outbox2, &adapter2, &tokens2);
            auto changed = activation;
            changed.recordVersion += 1;
            const auto conflict = coordinator2.Activate(
                fixture.activationEnvelope, changed, fixture.resource, nullptr);
            std::string retainedIntent;
            run.Require(outbox2.GetIntent(
                fixture.activationEnvelope.requestId, &retainedIntent),
                "activation intent disappeared after conflict");
            const auto recovered = coordinator2.Activate(
                fixture.activationEnvelope, activation,
                fixture.resource, nullptr);
            PublicationTokenState token;
            const bool passed =
                interrupted.verdict == ProjectionVerdict::INTERRUPTED &&
                conflict.verdict ==
                    ProjectionVerdict::IDEMPOTENCY_CONFLICT &&
                conflict.requestDigest != recovered.requestDigest &&
                originalIntent == retainedIntent &&
                recovered.verdict == ProjectionVerdict::ACTIVATED &&
                tokens2.Read(fixture.candidate.packageName, 0, 25, &token) &&
                token == PublicationTokenState::EXTERNAL_READY &&
                adapter2.RecordCount() == 1;
            run.Record("F02-interrupted-activation-intent-bound",
                conflict, passed);
            run.Require(passed,
                "interrupted ACTIVATE intent was overwritten or ignored");
        }

        {
            const fs::path root = output / "f02-concurrent-intent-claim";
            Fixture fixture = MakeFixture(
                run.NextPackage("f02-concurrent-intent-claim"), 26);
            auto changed = fixture.candidate;
            changed.componentFactsDigest =
                Digest("concurrent-changed-component-facts");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            adapter.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens, fixture);
            TwoPartyGate gate;
            RacingOutbox outboxA(root / "outbox", &gate);
            RacingOutbox outboxB(root / "outbox", &gate);
            BmsProjectionCoordinatorV1 coordinatorA(
                Policy(), &outboxA, &adapter, &tokens);
            BmsProjectionCoordinatorV1 coordinatorB(
                Policy(), &outboxB, &adapter, &tokens);
            ProjectionReceiptV1 receiptA;
            ProjectionReceiptV1 receiptB;
            std::thread threadA([&] {
                receiptA = coordinatorA.Prepare(
                    fixture.prepareEnvelope, fixture.candidate,
                    fixture.resource, nullptr);
            });
            std::thread threadB([&] {
                receiptB = coordinatorB.Prepare(
                    fixture.prepareEnvelope, changed,
                    fixture.resource, nullptr);
            });
            threadA.join();
            threadB.join();
            std::string storedIntent;
            run.Require(outboxA.GetStoredIntent(
                fixture.prepareEnvelope.requestId, &storedIntent),
                "concurrent winner intent was not durable");
            const bool aWon =
                receiptA.verdict == ProjectionVerdict::PREPARED &&
                receiptB.verdict == ProjectionVerdict::IDEMPOTENCY_CONFLICT;
            const bool bWon =
                receiptB.verdict == ProjectionVerdict::PREPARED &&
                receiptA.verdict == ProjectionVerdict::IDEMPOTENCY_CONFLICT;
            const ProjectionReceiptV1& winner = aWon ? receiptA : receiptB;
            const ProjectionReceiptV1& conflict = aWon ? receiptB : receiptA;
            const auto replay = aWon
                ? coordinatorA.Prepare(
                      fixture.prepareEnvelope, fixture.candidate,
                      fixture.resource, nullptr)
                : coordinatorB.Prepare(
                      fixture.prepareEnvelope, changed,
                      fixture.resource, nullptr);
            const auto loserRetry = aWon
                ? coordinatorB.Prepare(
                      fixture.prepareEnvelope, changed,
                      fixture.resource, nullptr)
                : coordinatorA.Prepare(
                      fixture.prepareEnvelope, fixture.candidate,
                      fixture.resource, nullptr);
            const std::string winnerDigestField =
                "\"requestDigest\":\"" + winner.requestDigest + "\"";
            const std::string loserDigestField =
                "\"requestDigest\":\"" + conflict.requestDigest + "\"";
            const bool passed =
                (aWon != bWon) &&
                conflict.packageName == fixture.candidate.packageName &&
                replay.verdict == ProjectionVerdict::PREPARED &&
                replay.requestDigest == winner.requestDigest &&
                loserRetry.verdict ==
                    ProjectionVerdict::IDEMPOTENCY_CONFLICT &&
                storedIntent.find(winnerDigestField) != std::string::npos &&
                storedIntent.find(loserDigestField) == std::string::npos &&
                adapter.RecordCount() == 1 &&
                !storedIntent.empty();
            run.Record("F02-concurrent-first-intent-single-winner",
                conflict, passed);
            run.Require(passed,
                "concurrent different intents did not produce one winner");
        }

        {
            const fs::path root = output / "f02-legacy-receipt";
            Fixture fixture = MakeFixture(
                run.NextPackage("f02-legacy-receipt"), 27);
            const fs::path outboxRoot = root / "outbox";
            std::ostringstream legacy;
            legacy << 1 << "\n"
                   << Hex(fixture.prepareEnvelope.requestId) << "\n"
                   << Hex(fixture.candidate.transactionId) << "\n"
                   << Hex(fixture.candidate.packageName) << "\n"
                   << fixture.candidate.userId << "\n"
                   << fixture.candidate.candidateGeneration << "\n"
                   << fixture.candidate.canonicalDigest << "\n"
                   << fixture.candidate.resourcePayloadDigest << "\n"
                   << Digest("legacy-projection") << "\n"
                   << static_cast<int>(ProjectionState::PREPARED) << "\n"
                   << static_cast<int>(
                          PublicationTokenState::PREPARED) << "\n"
                   << static_cast<int>(ProjectionVerdict::PREPARED) << "\n"
                   << Hex("legacy pre-promotion developer receipt") << "\n";
            run.Require(AtomicWrite(
                outboxRoot / "receipt" /
                    Hex(fixture.prepareEnvelope.requestId),
                legacy.str()), "cannot seed legacy receipt");
            run.Require(AtomicWrite(
                outboxRoot / "intent" /
                    Hex(fixture.prepareEnvelope.requestId),
                "{\"legacySchema\":1}"), "cannot seed legacy intent");
            FileOutbox outbox(outboxRoot);
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            adapter.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens, fixture);
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto receipt = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            const bool passed =
                receipt.verdict ==
                    ProjectionVerdict::IDEMPOTENCY_CONFLICT &&
                receipt.packageName == fixture.candidate.packageName &&
                adapter.RecordCount() == 0;
            run.Record("F02-legacy-receipt-fails-closed", receipt, passed);
            run.Require(passed,
                "legacy pre-promotion receipt did not fail closed");
        }

        {
            const fs::path root = output / "n02-closed-prepare-caller";
            Fixture owner = MakeFixture(
                run.NextPackage("n02-closed-prepare-owner"), 20);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            adapter.SetPendingTransaction(owner.candidate.transactionId);
            SeedP4Token(&tokens, owner);
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto ownerReceipt = coordinator.Prepare(
                owner.prepareEnvelope, owner.candidate, owner.resource, nullptr);
            Fixture intruder = MakeFixture(
                run.NextPackage("n02-closed-prepare-intruder"), 120);
            intruder.prepareEnvelope.requestId =
                owner.prepareEnvelope.requestId;
            intruder.prepareEnvelope.callerScopeDigest =
                Digest("foreign-closed-replay-caller");
            const auto receipt = coordinator.Prepare(
                intruder.prepareEnvelope, intruder.candidate,
                intruder.resource, nullptr);
            const bool passed =
                ownerReceipt.verdict == ProjectionVerdict::PREPARED &&
                receipt.verdict ==
                    ProjectionVerdict::CALLER_SCOPE_MISMATCH &&
                receipt.packageName == intruder.candidate.packageName &&
                receipt.packageName != ownerReceipt.packageName &&
                adapter.RecordCount() == 1;
            run.Record("N02-closed-replay-caller-input-bound",
                receipt, passed);
            run.Require(passed, "closed PREPARE replay leaked owner receipt");
        }

        {
            const fs::path root = output / "n02-closed-prepare-payload";
            Fixture fixture = MakeFixture(
                run.NextPackage("n02-closed-prepare-payload"), 21);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            adapter.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens, fixture);
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto ownerReceipt = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            auto changed = fixture.candidate;
            changed.componentFactsDigest =
                Digest("changed-component-facts");
            changed.managedPathDigest = Digest("changed-managed-path");
            const auto receipt = coordinator.Prepare(
                fixture.prepareEnvelope, changed, fixture.resource, nullptr);
            const bool passed =
                ownerReceipt.verdict == ProjectionVerdict::PREPARED &&
                receipt.verdict ==
                    ProjectionVerdict::IDEMPOTENCY_CONFLICT &&
                receipt.requestDigest != ownerReceipt.requestDigest &&
                adapter.RecordCount() == 1;
            run.Record("N02-closed-replay-full-payload-bound",
                receipt, passed);
            run.Require(passed, "closed PREPARE replay ignored full payload");
        }

        {
            const fs::path root = output / "n02-closed-activate-caller";
            Fixture owner = MakeFixture(
                run.NextPackage("n02-closed-activate-owner"), 22);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            adapter.SetPendingTransaction(owner.candidate.transactionId);
            SeedP4Token(&tokens, owner);
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto prepared = coordinator.Prepare(
                owner.prepareEnvelope, owner.candidate, owner.resource, nullptr);
            run.Require(tokens.Seed(owner.candidate.packageName, 0, 22,
                PublicationTokenState::CANONICAL_SELECTED),
                "cannot seed closed activation owner token");
            const auto activation = ActivationFixture(owner, prepared);
            const auto ownerReceipt = coordinator.Activate(
                owner.activationEnvelope, activation, owner.resource, nullptr);
            Fixture intruder = MakeFixture(
                run.NextPackage("n02-closed-activate-intruder"), 122);
            intruder.activationEnvelope.requestId =
                owner.activationEnvelope.requestId;
            intruder.activationEnvelope.callerScopeDigest =
                Digest("foreign-closed-activation-caller");
            const auto intruderActivation =
                ActivationFixture(intruder, ownerReceipt);
            const auto receipt = coordinator.Activate(
                intruder.activationEnvelope, intruderActivation,
                intruder.resource, nullptr);
            const bool passed =
                ownerReceipt.verdict == ProjectionVerdict::ACTIVATED &&
                receipt.verdict ==
                    ProjectionVerdict::CALLER_SCOPE_MISMATCH &&
                receipt.packageName == intruder.candidate.packageName &&
                receipt.packageName != ownerReceipt.packageName &&
                adapter.RecordCount() == 1;
            run.Record("N02-closed-activation-replay-bound",
                receipt, passed);
            run.Require(passed, "closed ACTIVATE replay leaked owner receipt");
        }

        {
            const fs::path root = output / "n02-operation-bound";
            Fixture fixture = MakeFixture(
                run.NextPackage("n02-operation-bound"), 23);
            fixture.activationEnvelope.requestId =
                fixture.prepareEnvelope.requestId;
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            adapter.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens, fixture);
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto prepared = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            run.Require(tokens.Seed(fixture.candidate.packageName, 0, 23,
                PublicationTokenState::CANONICAL_SELECTED),
                "cannot seed operation-bound token");
            const auto activation = ActivationFixture(fixture, prepared);
            const auto receipt = coordinator.Activate(
                fixture.activationEnvelope, activation,
                fixture.resource, nullptr);
            HostProjectionRuntimeV1 readback;
            PublicationTokenState token;
            const bool passed =
                prepared.verdict == ProjectionVerdict::PREPARED &&
                receipt.verdict ==
                    ProjectionVerdict::IDEMPOTENCY_CONFLICT &&
                receipt.operation == "ACTIVATE" &&
                adapter.Read(fixture.candidate.packageName, 0, 23,
                    &readback) == BackendResult::OK &&
                readback.state == ProjectionState::PREPARED &&
                tokens.Read(fixture.candidate.packageName, 0, 23, &token) &&
                token == PublicationTokenState::CANONICAL_SELECTED;
            run.Record("N02-request-id-operation-bound", receipt, passed);
            run.Require(passed, "requestId crossed operation boundary");
        }

        {
            const fs::path root = output / "n02-prepare-receipt-tamper";
            Fixture fixture = MakeFixture(
                run.NextPackage("n02-prepare-receipt-tamper"), 26);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            adapter.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens, fixture);
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto ownerReceipt = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            auto tampered = ownerReceipt;
            tampered.transactionId =
                "tx-" + Digest("tampered-prepare-owner").substr(0, 16);
            tampered.projectionDigest =
                Digest("tampered-prepare-projection");
            run.Require(outbox.ReplaceReceiptForTest(
                fixture.prepareEnvelope.requestId, tampered),
                "cannot tamper prepare receipt");
            const auto receipt = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            HostProjectionRuntimeV1 readback;
            const bool passed =
                ownerReceipt.verdict == ProjectionVerdict::PREPARED &&
                receipt.verdict ==
                    ProjectionVerdict::IDEMPOTENCY_CONFLICT &&
                receipt.transactionId == fixture.candidate.transactionId &&
                receipt.transactionId != tampered.transactionId &&
                adapter.Read(fixture.candidate.packageName, 0, 26,
                    &readback) == BackendResult::OK &&
                readback.projectionDigest == ownerReceipt.projectionDigest &&
                adapter.RecordCount() == 1;
            run.Record("N02-closed-prepare-receipt-tamper",
                receipt, passed);
            run.Require(passed, "tampered PREPARE receipt replayed");
        }

        {
            const fs::path root = output / "n02-activate-receipt-tamper";
            Fixture fixture = MakeFixture(
                run.NextPackage("n02-activate-receipt-tamper"), 27);
            FileOutbox outbox(root / "outbox");
            FileBmsAdapter adapter(root / "bms");
            FileTokenStore tokens(root / "token");
            adapter.SetPendingTransaction(fixture.candidate.transactionId);
            SeedP4Token(&tokens, fixture);
            BmsProjectionCoordinatorV1 coordinator(
                Policy(), &outbox, &adapter, &tokens);
            const auto prepared = coordinator.Prepare(
                fixture.prepareEnvelope, fixture.candidate,
                fixture.resource, nullptr);
            run.Require(tokens.Seed(fixture.candidate.packageName, 0, 27,
                PublicationTokenState::CANONICAL_SELECTED),
                "cannot seed activation receipt tamper token");
            const auto activation = ActivationFixture(fixture, prepared);
            const auto ownerReceipt = coordinator.Activate(
                fixture.activationEnvelope, activation,
                fixture.resource, nullptr);
            auto tampered = ownerReceipt;
            tampered.schemaVersion = 2;
            tampered.packageName = "foreign.tampered.receipt";
            run.Require(outbox.ReplaceReceiptForTest(
                fixture.activationEnvelope.requestId, tampered),
                "cannot tamper activation receipt");
            const auto receipt = coordinator.Activate(
                fixture.activationEnvelope, activation,
                fixture.resource, nullptr);
            HostProjectionRuntimeV1 readback;
            PublicationTokenState token;
            const bool passed =
                ownerReceipt.verdict == ProjectionVerdict::ACTIVATED &&
                receipt.verdict ==
                    ProjectionVerdict::IDEMPOTENCY_CONFLICT &&
                receipt.schemaVersion == 1 &&
                receipt.packageName == fixture.candidate.packageName &&
                receipt.packageName != tampered.packageName &&
                adapter.Read(fixture.candidate.packageName, 0, 27,
                    &readback) == BackendResult::OK &&
                readback.state == ProjectionState::ACTIVE &&
                tokens.Read(fixture.candidate.packageName, 0, 27, &token) &&
                token == PublicationTokenState::EXTERNAL_READY;
            run.Record("N02-closed-activate-receipt-tamper",
                receipt, passed);
            run.Require(passed, "tampered ACTIVATE receipt replayed");
        }

        run.Finish();
        std::cout
            << "DEVELOPER_TEST_READY_FOR_VERIFY action=Fn01.A10 "
               "formal_verdict=NOT_ISSUED output="
            << output << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << "\n";
        return 1;
    }
}
