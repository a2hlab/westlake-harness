#include "package_transaction_v1.h"

#include "sha256.h"

#include <algorithm>
#include <cerrno>
#include <charconv>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <map>
#include <mutex>
#include <optional>
#include <set>
#include <sstream>
#include <string_view>
#include <sys/stat.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <tuple>
#include <unistd.h>
#include <utility>

namespace oh_adapter::package_transaction {
namespace {

constexpr uint32_t kPrimaryUserId = 0;

std::mutex gStoreLeaseMutex;
std::set<std::pair<uint64_t, uint64_t>> gStoreLeases;

struct JournalState {
    std::string jobId;
    std::string memberId;
    std::string operation;
    std::string transactionId;
    std::string requestDigest;
    std::string callerScopeDigest;
    std::string artifactSetDigest;
    std::optional<std::string> packageName;
    uint32_t userId = 0;
    uint64_t candidateGeneration = 0;
    DurablePhase phase = DurablePhase::P0_INPUT_FROZEN;
    ManagedFilesV1 candidateManagedFiles;
    std::optional<std::string> candidateCanonicalDigest;
    std::optional<PackageLifecycleReceiptV1> receipt;
    std::optional<UpdateReceiptV1> updateReceipt;
    std::optional<UninstallReceiptV1> uninstallReceipt;
};

std::string Sha256Hex(std::string_view value)
{
    unsigned char digest[32]{};
    sha256(reinterpret_cast<const unsigned char*>(value.data()), value.size(), digest);
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(64, '0');
    for (size_t i = 0; i < 32; ++i) {
        result[i * 2] = kHex[digest[i] >> 4];
        result[i * 2 + 1] = kHex[digest[i] & 0x0f];
    }
    return result;
}

std::string Sha256Hex(const std::vector<uint8_t>& value)
{
    return Sha256Hex(std::string_view(
        reinterpret_cast<const char*>(value.data()), value.size()));
}

bool IsLowerHexDigest(const std::string& value)
{
    if (value.size() != 64) {
        return false;
    }
    return std::all_of(value.begin(), value.end(), [](char character) {
        return (character >= '0' && character <= '9') ||
            (character >= 'a' && character <= 'f');
    });
}

std::string HexEncode(std::string_view value)
{
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result;
    result.reserve(value.size() * 2);
    for (unsigned char character : value) {
        result.push_back(kHex[character >> 4]);
        result.push_back(kHex[character & 0x0f]);
    }
    return result;
}

bool HexDecode(const std::string& value, std::string* result)
{
    if (result == nullptr || value.size() % 2 != 0) {
        return false;
    }
    auto nibble = [](char character) -> int {
        if (character >= '0' && character <= '9') return character - '0';
        if (character >= 'a' && character <= 'f') return character - 'a' + 10;
        return -1;
    };
    result->clear();
    result->reserve(value.size() / 2);
    for (size_t index = 0; index < value.size(); index += 2) {
        const int high = nibble(value[index]);
        const int low = nibble(value[index + 1]);
        if (high < 0 || low < 0) {
            result->clear();
            return false;
        }
        result->push_back(static_cast<char>((high << 4) | low));
    }
    return true;
}

template <typename Integer>
bool ParseUnsigned(const std::string& value, Integer* result)
{
    if (result == nullptr || value.empty()) {
        return false;
    }
    Integer parsed = 0;
    const char* begin = value.data();
    const char* end = begin + value.size();
    const auto conversion = std::from_chars(begin, end, parsed);
    if (conversion.ec != std::errc() || conversion.ptr != end) {
        return false;
    }
    *result = parsed;
    return true;
}

std::vector<std::string> SplitTabs(const std::string& value)
{
    std::vector<std::string> fields;
    size_t begin = 0;
    while (true) {
        const size_t separator = value.find('\t', begin);
        if (separator == std::string::npos) {
            fields.push_back(value.substr(begin));
            return fields;
        }
        fields.push_back(value.substr(begin, separator - begin));
        begin = separator + 1;
    }
}

std::string JoinTabs(const std::vector<std::string>& fields)
{
    std::string result;
    for (size_t index = 0; index < fields.size(); ++index) {
        if (index != 0) result.push_back('\t');
        result += fields[index];
    }
    return result;
}

std::vector<std::string> Split(const std::string& value, char separator)
{
    if (value.empty()) return {};
    std::vector<std::string> fields;
    size_t begin = 0;
    while (true) {
        const size_t found = value.find(separator, begin);
        if (found == std::string::npos) {
            fields.push_back(value.substr(begin));
            return fields;
        }
        fields.push_back(value.substr(begin, found - begin));
        begin = found + 1;
    }
}

std::string EncodeStrings(const std::vector<std::string>& values)
{
    std::string encoded;
    for (size_t index = 0; index < values.size(); ++index) {
        if (index != 0) encoded.push_back(',');
        encoded += HexEncode(values[index]);
    }
    return encoded;
}

bool DecodeStrings(const std::string& encoded,
    std::vector<std::string>* values)
{
    if (values == nullptr) return false;
    values->clear();
    for (const std::string& item : Split(encoded, ',')) {
        std::string value;
        if (!HexDecode(item, &value)) return false;
        values->push_back(std::move(value));
    }
    return true;
}

std::string EncodeUnsigneds(const std::vector<uint32_t>& values)
{
    std::string encoded;
    for (size_t index = 0; index < values.size(); ++index) {
        if (index != 0) encoded.push_back(',');
        encoded += std::to_string(values[index]);
    }
    return encoded;
}

bool DecodeUnsigneds(const std::string& encoded,
    std::vector<uint32_t>* values)
{
    if (values == nullptr) return false;
    values->clear();
    for (const std::string& item : Split(encoded, ',')) {
        uint32_t value = 0;
        if (!ParseUnsigned(item, &value)) return false;
        values->push_back(value);
    }
    return true;
}

std::string EncodeComponents(
    const std::vector<ManifestComponentFactV1>& components)
{
    std::string encoded;
    for (size_t index = 0; index < components.size(); ++index) {
        if (index != 0) encoded.push_back(',');
        const auto& component = components[index];
        encoded += HexEncode(component.kind) + ":" + HexEncode(component.name) +
            ":" + (component.exported.has_value()
                ? (*component.exported ? "t" : "f") : "n");
    }
    return encoded;
}

bool DecodeComponents(const std::string& encoded,
    std::vector<ManifestComponentFactV1>* components)
{
    if (components == nullptr) return false;
    components->clear();
    for (const std::string& item : Split(encoded, ',')) {
        const auto fields = Split(item, ':');
        if (fields.size() != 3) return false;
        ManifestComponentFactV1 component;
        if (!HexDecode(fields[0], &component.kind) ||
            !HexDecode(fields[1], &component.name)) {
            return false;
        }
        if (fields[2] == "t") component.exported = true;
        else if (fields[2] == "f") component.exported = false;
        else if (fields[2] != "n") return false;
        components->push_back(std::move(component));
    }
    return true;
}

std::string EncodeProvenance(
    const std::vector<ManifestFieldProvenanceV1>& provenance)
{
    std::string encoded;
    for (size_t index = 0; index < provenance.size(); ++index) {
        if (index != 0) encoded.push_back(',');
        const auto& item = provenance[index];
        encoded += HexEncode(item.field) + ":" + item.artifactSha256 + ":" +
            item.manifestEntrySha256 + ":" +
            std::to_string(item.manifestChunkOffset);
    }
    return encoded;
}

bool DecodeProvenance(const std::string& encoded,
    std::vector<ManifestFieldProvenanceV1>* provenance)
{
    if (provenance == nullptr) return false;
    provenance->clear();
    for (const std::string& item : Split(encoded, ',')) {
        const auto fields = Split(item, ':');
        ManifestFieldProvenanceV1 decoded;
        if (fields.size() != 4 ||
            !HexDecode(fields[0], &decoded.field) ||
            !IsLowerHexDigest(fields[1]) ||
            !IsLowerHexDigest(fields[2]) ||
            !ParseUnsigned(fields[3], &decoded.manifestChunkOffset)) {
            return false;
        }
        decoded.artifactSha256 = fields[1];
        decoded.manifestEntrySha256 = fields[2];
        provenance->push_back(std::move(decoded));
    }
    return true;
}

std::string EncodeSigningLineage(
    const std::vector<PackageSigningLineageFactV1>& lineage)
{
    std::string encoded;
    for (size_t index = 0; index < lineage.size(); ++index) {
        if (index != 0) encoded.push_back(',');
        encoded += lineage[index].certificateSha256 + ":" +
            std::to_string(lineage[index].capabilities);
    }
    return encoded;
}

bool DecodeSigningLineage(const std::string& encoded,
    std::vector<PackageSigningLineageFactV1>* lineage)
{
    if (lineage == nullptr) return false;
    lineage->clear();
    for (const std::string& item : Split(encoded, ',')) {
        const auto fields = Split(item, ':');
        PackageSigningLineageFactV1 fact;
        if (fields.size() != 2 ||
            !IsLowerHexDigest(fields[0]) ||
            !ParseUnsigned(fields[1], &fact.capabilities)) {
            return false;
        }
        fact.certificateSha256 = fields[0];
        lineage->push_back(std::move(fact));
    }
    return true;
}

std::string JsonString(std::string_view value)
{
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result{"\""};
    for (unsigned char character : value) {
        switch (character) {
            case '"': result += "\\\""; break;
            case '\\': result += "\\\\"; break;
            case '\b': result += "\\b"; break;
            case '\f': result += "\\f"; break;
            case '\n': result += "\\n"; break;
            case '\r': result += "\\r"; break;
            case '\t': result += "\\t"; break;
            default:
                if (character < 0x20) {
                    result += "\\u00";
                    result.push_back(kHex[character >> 4]);
                    result.push_back(kHex[character & 0x0f]);
                } else {
                    result.push_back(static_cast<char>(character));
                }
        }
    }
    result.push_back('"');
    return result;
}

std::string StringArrayJson(const std::vector<std::string>& values)
{
    std::string result = "[";
    for (size_t index = 0; index < values.size(); ++index) {
        if (index != 0) result += ",";
        result += JsonString(values[index]);
    }
    return result + "]";
}

std::string ComponentsJson(
    const std::vector<ManifestComponentFactV1>& components)
{
    std::string result = "[";
    for (size_t index = 0; index < components.size(); ++index) {
        if (index != 0) result += ",";
        const auto& item = components[index];
        result += "{\"exported\":";
        if (!item.exported.has_value()) result += "null";
        else result += (*item.exported ? "true" : "false");
        result += ",\"kind\":" + JsonString(item.kind) +
            ",\"name\":" + JsonString(item.name) + "}";
    }
    return result + "]";
}

std::string ProvenanceJson(
    const std::vector<ManifestFieldProvenanceV1>& provenance)
{
    std::string result = "[";
    for (size_t index = 0; index < provenance.size(); ++index) {
        if (index != 0) result += ",";
        const auto& item = provenance[index];
        result += "{\"artifactSha256\":" + JsonString(item.artifactSha256) +
            ",\"field\":" + JsonString(item.field) +
            ",\"manifestChunkOffset\":" +
            std::to_string(item.manifestChunkOffset) +
            ",\"manifestEntrySha256\":" +
            JsonString(item.manifestEntrySha256) + "}";
    }
    return result + "]";
}

const char* ArtifactRoleName(ArtifactRole role)
{
    switch (role) {
        case ArtifactRole::BASE: return "BASE";
        case ArtifactRole::SPLIT_CONFIG: return "SPLIT_CONFIG";
        case ArtifactRole::SPLIT_FEATURE: return "SPLIT_FEATURE";
    }
    return "UNKNOWN";
}

std::string PackageKey(uint32_t userId, const std::string& packageName)
{
    return std::to_string(userId) + ":" + packageName;
}

std::string ParentPath(const std::string& path)
{
    const size_t separator = path.find_last_of('/');
    if (separator == std::string::npos) return ".";
    if (separator == 0) return "/";
    return path.substr(0, separator);
}

bool EnsureDirectoryTree(const std::string& path, std::string* error)
{
    if (path.empty() || path[0] != '/') {
        if (error != nullptr) *error = "directory root must be absolute";
        return false;
    }
    std::string current;
    size_t begin = 1;
    current = "/";
    while (begin <= path.size()) {
        const size_t separator = path.find('/', begin);
        const size_t end = separator == std::string::npos ? path.size() : separator;
        if (end > begin) {
            if (current.size() > 1) current.push_back('/');
            current.append(path, begin, end - begin);
            struct stat status {};
            if (lstat(current.c_str(), &status) == 0) {
                if (!S_ISDIR(status.st_mode) || S_ISLNK(status.st_mode)) {
                    if (error != nullptr) *error = "unsafe non-directory path component";
                    return false;
                }
            } else if (errno == ENOENT) {
                if (mkdir(current.c_str(), 0700) != 0 && errno != EEXIST) {
                    if (error != nullptr) *error = std::strerror(errno);
                    return false;
                }
            } else {
                if (error != nullptr) *error = std::strerror(errno);
                return false;
            }
        }
        if (separator == std::string::npos) break;
        begin = separator + 1;
    }
    return true;
}

bool FsyncDirectory(const std::string& path, std::string* error)
{
    const int directory = open(path.c_str(), O_RDONLY | O_CLOEXEC);
    if (directory < 0) {
        if (error != nullptr) *error = std::strerror(errno);
        return false;
    }
    const bool success = fsync(directory) == 0;
    if (!success && error != nullptr) *error = std::strerror(errno);
    close(directory);
    return success;
}

bool WriteAll(int file, const uint8_t* data, size_t size, std::string* error)
{
    size_t offset = 0;
    while (offset < size) {
        const ssize_t written = write(file, data + offset, size - offset);
        if (written < 0) {
            if (errno == EINTR) continue;
            if (error != nullptr) *error = std::strerror(errno);
            return false;
        }
        if (written == 0) {
            if (error != nullptr) *error = "zero-byte write";
            return false;
        }
        offset += static_cast<size_t>(written);
    }
    return true;
}

PackageLifecycleReceiptV1 MakeReceipt(const InstallRequestV1& request,
    InstallVerdict verdict, const char* terminalState,
    const std::optional<std::string>& packageName = std::nullopt,
    const std::optional<uint64_t>& generation = std::nullopt,
    const std::optional<std::string>& canonicalDigest = std::nullopt)
{
    PackageLifecycleReceiptV1 receipt;
    receipt.transactionId = request.admission.transactionId;
    receipt.packageName = packageName;
    receipt.generation = generation;
    receipt.requestDigest = request.admission.requestDigest;
    if (!request.artifactSet.artifactSetDigest.empty()) {
        receipt.artifactSetDigest = request.artifactSet.artifactSetDigest;
    }
    receipt.durableRecordDigest = canonicalDigest;
    receipt.terminalState = terminalState;
    receipt.verdict = verdict;
    return receipt;
}

UpdateReceiptV1 MakeUpdateReceipt(const UpdateRequestV1& request,
    UpdateVerdict verdict, const char* terminalState,
    const std::optional<std::string>& packageName = std::nullopt,
    const std::optional<uint64_t>& oldGeneration = std::nullopt,
    const std::optional<uint64_t>& newGeneration = std::nullopt,
    const std::optional<std::string>& canonicalDigest = std::nullopt,
    const std::optional<std::string>& planDigest = std::nullopt)
{
    UpdateReceiptV1 receipt;
    receipt.transactionId = request.admission.transactionId;
    receipt.requestDigest = request.admission.requestDigest;
    receipt.packageName = packageName;
    receipt.oldGeneration = oldGeneration;
    receipt.newGeneration = newGeneration;
    if (!request.artifactSet.artifactSetDigest.empty()) {
        receipt.artifactSetDigest = request.artifactSet.artifactSetDigest;
    }
    receipt.canonicalDigest = canonicalDigest;
    receipt.policyRuleId = request.policySnapshot.ruleId;
    receipt.policyVersion = request.policySnapshot.policyVersion;
    receipt.policyRulesDigest = request.policySnapshot.rulesDigest;
    receipt.retirementPlanDigest = planDigest;
    receipt.verdict = verdict;
    receipt.terminalState = terminalState;
    return receipt;
}

std::vector<std::string> OpenRemovalObligations(
    const RemovalTombstoneV1& tombstone)
{
    std::vector<std::string> result;
    for (const auto& obligation : tombstone.obligations) {
        if (obligation.state == RemovalObligationState::OPEN) {
            result.push_back(obligation.kind);
        }
    }
    std::sort(result.begin(), result.end());
    return result;
}

UninstallReceiptV1 MakeUninstallReceipt(
    const UninstallRequestV1& request, UninstallVerdict verdict,
    const char* terminalState,
    const std::optional<std::string>& packageName = std::nullopt,
    const std::optional<uint64_t>& generation = std::nullopt,
    const std::optional<std::string>& canonicalDigest = std::nullopt,
    const RemovalTombstoneV1* tombstone = nullptr)
{
    UninstallReceiptV1 receipt;
    receipt.transactionId = request.admission.transactionId;
    receipt.requestDigest = request.admission.requestDigest;
    receipt.packageName = packageName;
    receipt.generation = generation;
    receipt.canonicalDigest = canonicalDigest;
    receipt.verdict = verdict;
    receipt.terminalState = terminalState;
    if (tombstone != nullptr) {
        receipt.transactionId = tombstone->transactionId;
        receipt.requestDigest = tombstone->requestDigest;
        receipt.packageName = tombstone->packageName;
        receipt.generation = tombstone->generation;
        receipt.canonicalDigest = tombstone->canonicalDigest;
        receipt.tombstoneDigest = tombstone->tombstoneDigest;
        receipt.residualObligations =
            OpenRemovalObligations(*tombstone);
    }
    return receipt;
}

std::string EncodeUninstallReceiptEvent(const char* type,
    const UninstallReceiptV1& receipt)
{
    return JoinTabs({
        type,
        HexEncode(receipt.transactionId),
        HexEncode(receipt.requestDigest),
        HexEncode(receipt.packageName.value_or("")),
        receipt.generation.has_value()
            ? std::to_string(*receipt.generation) : "",
        HexEncode(receipt.canonicalDigest.value_or("")),
        HexEncode(receipt.tombstoneDigest.value_or("")),
        EncodeStrings(receipt.residualObligations),
        HexEncode(receipt.terminalState),
        HexEncode(UninstallVerdictName(receipt.verdict)),
    });
}

bool DecodeUninstallVerdict(const std::string& name,
    UninstallVerdict* verdict)
{
    if (verdict == nullptr) return false;
    const UninstallVerdict values[] = {
        UninstallVerdict::REMOVED,
        UninstallVerdict::INVALID_ENVELOPE,
        UninstallVerdict::NOT_SUPPORTED,
        UninstallVerdict::PACKAGE_NOT_FOUND,
        UninstallVerdict::PACKAGE_REMOVING,
        UninstallVerdict::SELECTOR_MISMATCH,
        UninstallVerdict::GENERATION_MISMATCH,
        UninstallVerdict::IDEMPOTENCY_CONFLICT,
        UninstallVerdict::DATA_INCONSISTENT,
        UninstallVerdict::INTERNAL_IO_ERROR,
        UninstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
    };
    for (UninstallVerdict value : values) {
        if (name == UninstallVerdictName(value)) {
            *verdict = value;
            return true;
        }
    }
    return false;
}

bool DecodeUninstallReceiptFields(
    const std::vector<std::string>& fields,
    UninstallReceiptV1* receipt)
{
    if (receipt == nullptr || fields.size() != 10) return false;
    std::string packageName;
    std::string canonicalDigest;
    std::string tombstoneDigest;
    std::string verdictName;
    if (!HexDecode(fields[1], &receipt->transactionId) ||
        !HexDecode(fields[2], &receipt->requestDigest) ||
        !HexDecode(fields[3], &packageName) ||
        !HexDecode(fields[5], &canonicalDigest) ||
        !HexDecode(fields[6], &tombstoneDigest) ||
        !DecodeStrings(fields[7], &receipt->residualObligations) ||
        !HexDecode(fields[8], &receipt->terminalState) ||
        !HexDecode(fields[9], &verdictName) ||
        !DecodeUninstallVerdict(verdictName, &receipt->verdict)) {
        return false;
    }
    if (!packageName.empty()) receipt->packageName = packageName;
    if (!fields[4].empty()) {
        uint64_t generation = 0;
        if (!ParseUnsigned(fields[4], &generation)) return false;
        receipt->generation = generation;
    }
    if (!canonicalDigest.empty()) {
        receipt->canonicalDigest = canonicalDigest;
    }
    if (!tombstoneDigest.empty()) {
        receipt->tombstoneDigest = tombstoneDigest;
    }
    return true;
}

std::string RemovalTombstoneCanonical(
    const RemovalTombstoneV1& tombstone)
{
    std::vector<RemovalObligationV1> obligations =
        tombstone.obligations;
    std::sort(obligations.begin(), obligations.end(),
        [](const RemovalObligationV1& left,
           const RemovalObligationV1& right) {
            return std::tie(left.kind, left.identityDigest) <
                std::tie(right.kind, right.identityDigest);
        });
    std::string result = "{\"canonicalDigest\":" +
        JsonString(tombstone.canonicalDigest) +
        ",\"generation\":" + std::to_string(tombstone.generation) +
        ",\"managedCodeDigest\":" +
        JsonString(tombstone.managedCodeDigest) +
        ",\"managedCodePath\":" +
        JsonString(tombstone.managedCodePath) +
        ",\"obligations\":[";
    for (size_t index = 0; index < obligations.size(); ++index) {
        if (index != 0) result += ",";
        result += "{\"identityDigest\":" +
            JsonString(obligations[index].identityDigest) +
            ",\"kind\":" + JsonString(obligations[index].kind) +
            "}";
    }
    result += "],\"packageName\":" +
        JsonString(tombstone.packageName) +
        ",\"requestDigest\":" +
        JsonString(tombstone.requestDigest) +
        ",\"schemaVersion\":1,\"transactionId\":" +
        JsonString(tombstone.transactionId) +
        ",\"userId\":" + std::to_string(tombstone.userId) + "}";
    return result;
}

std::string ComputeRemovalTombstoneDigest(
    const RemovalTombstoneV1& tombstone)
{
    return Sha256Hex(RemovalTombstoneCanonical(tombstone));
}

std::string EncodeUpdateReceiptEvent(const char* type,
    const UpdateReceiptV1& receipt)
{
    return JoinTabs({
        type,
        HexEncode(receipt.transactionId),
        HexEncode(receipt.requestDigest),
        HexEncode(receipt.artifactSetDigest.value_or("")),
        HexEncode(receipt.packageName.value_or("")),
        receipt.oldGeneration.has_value()
            ? std::to_string(*receipt.oldGeneration) : "",
        receipt.newGeneration.has_value()
            ? std::to_string(*receipt.newGeneration) : "",
        HexEncode(receipt.canonicalDigest.value_or("")),
        HexEncode(receipt.policyRuleId),
        HexEncode(receipt.policyVersion),
        HexEncode(receipt.policyRulesDigest),
        HexEncode(receipt.retirementPlanDigest.value_or("")),
        HexEncode(receipt.terminalState),
        HexEncode(UpdateVerdictName(receipt.verdict)),
    });
}

bool DecodeUpdateVerdict(const std::string& name, UpdateVerdict* verdict)
{
    if (verdict == nullptr) return false;
    const UpdateVerdict values[] = {
        UpdateVerdict::UPDATED,
        UpdateVerdict::INVALID_ENVELOPE,
        UpdateVerdict::NOT_SUPPORTED,
        UpdateVerdict::NOT_SUPPORTED_ARTIFACT_PROFILE,
        UpdateVerdict::ARTIFACT_DIGEST_MISMATCH,
        UpdateVerdict::IDENTITY_MISMATCH,
        UpdateVerdict::SIGNING_REJECTED,
        UpdateVerdict::POLICY_REJECTED,
        UpdateVerdict::PACKAGE_NOT_FOUND,
        UpdateVerdict::PACKAGE_REMOVING,
        UpdateVerdict::GENERATION_MISMATCH,
        UpdateVerdict::IDEMPOTENCY_CONFLICT,
        UpdateVerdict::DATA_INCONSISTENT,
        UpdateVerdict::INTERNAL_IO_ERROR,
        UpdateVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
    };
    for (UpdateVerdict value : values) {
        if (name == UpdateVerdictName(value)) {
            *verdict = value;
            return true;
        }
    }
    return false;
}

bool DecodeUpdateReceiptFields(const std::vector<std::string>& fields,
    UpdateReceiptV1* receipt)
{
    if (receipt == nullptr || fields.size() != 14) return false;
    std::string artifactSet;
    std::string packageName;
    std::string canonicalDigest;
    std::string planDigest;
    std::string verdictName;
    if (!HexDecode(fields[1], &receipt->transactionId) ||
        !HexDecode(fields[2], &receipt->requestDigest) ||
        !HexDecode(fields[3], &artifactSet) ||
        !HexDecode(fields[4], &packageName) ||
        !HexDecode(fields[7], &canonicalDigest) ||
        !HexDecode(fields[8], &receipt->policyRuleId) ||
        !HexDecode(fields[9], &receipt->policyVersion) ||
        !HexDecode(fields[10], &receipt->policyRulesDigest) ||
        !HexDecode(fields[11], &planDigest) ||
        !HexDecode(fields[12], &receipt->terminalState) ||
        !HexDecode(fields[13], &verdictName) ||
        !DecodeUpdateVerdict(verdictName, &receipt->verdict)) {
        return false;
    }
    if (!artifactSet.empty()) receipt->artifactSetDigest = artifactSet;
    if (!packageName.empty()) receipt->packageName = packageName;
    if (!fields[5].empty()) {
        uint64_t generation = 0;
        if (!ParseUnsigned(fields[5], &generation)) return false;
        receipt->oldGeneration = generation;
    }
    if (!fields[6].empty()) {
        uint64_t generation = 0;
        if (!ParseUnsigned(fields[6], &generation)) return false;
        receipt->newGeneration = generation;
    }
    if (!canonicalDigest.empty()) receipt->canonicalDigest = canonicalDigest;
    if (!planDigest.empty()) receipt->retirementPlanDigest = planDigest;
    return true;
}

std::string EncodeReceiptEvent(const char* type,
    const PackageLifecycleReceiptV1& receipt)
{
    return JoinTabs({
        type,
        HexEncode(receipt.transactionId),
        HexEncode(receipt.requestDigest),
        HexEncode(receipt.artifactSetDigest.value_or("")),
        HexEncode(receipt.packageName.value_or("")),
        receipt.generation.has_value() ? std::to_string(*receipt.generation) : "",
        HexEncode(receipt.durableRecordDigest.value_or("")),
        HexEncode(receipt.terminalState),
        HexEncode(InstallVerdictName(receipt.verdict)),
    });
}

bool DecodeVerdict(const std::string& name, InstallVerdict* verdict)
{
    if (verdict == nullptr) return false;
    const InstallVerdict values[] = {
        InstallVerdict::COMMITTED,
        InstallVerdict::NOT_SUPPORTED,
        InstallVerdict::NOT_SUPPORTED_ARTIFACT_PROFILE,
        InstallVerdict::INVALID_ENVELOPE,
        InstallVerdict::ARTIFACT_DIGEST_MISMATCH,
        InstallVerdict::IDENTITY_MISMATCH,
        InstallVerdict::SIGNING_REJECTED,
        InstallVerdict::POLICY_REJECTED,
        InstallVerdict::PACKAGE_ALREADY_EXISTS,
        InstallVerdict::PACKAGE_REMOVING,
        InstallVerdict::GENERATION_MISMATCH,
        InstallVerdict::IDEMPOTENCY_CONFLICT,
        InstallVerdict::DATA_INCONSISTENT,
        InstallVerdict::INTERNAL_IO_ERROR,
        InstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
    };
    for (InstallVerdict value : values) {
        if (name == InstallVerdictName(value)) {
            *verdict = value;
            return true;
        }
    }
    return false;
}

bool DecodeReceiptFields(const std::vector<std::string>& fields,
    PackageLifecycleReceiptV1* receipt)
{
    if (receipt == nullptr || fields.size() != 9) return false;
    std::string transaction;
    std::string request;
    std::string artifactSet;
    std::string package;
    std::string canonical;
    std::string terminal;
    std::string verdictName;
    if (!HexDecode(fields[1], &transaction) ||
        !HexDecode(fields[2], &request) ||
        !HexDecode(fields[3], &artifactSet) ||
        !HexDecode(fields[4], &package) ||
        !HexDecode(fields[6], &canonical) ||
        !HexDecode(fields[7], &terminal) ||
        !HexDecode(fields[8], &verdictName)) {
        return false;
    }
    InstallVerdict verdict;
    if (!DecodeVerdict(verdictName, &verdict)) return false;
    receipt->transactionId = std::move(transaction);
    receipt->requestDigest = std::move(request);
    if (!artifactSet.empty()) receipt->artifactSetDigest = artifactSet;
    if (!package.empty()) receipt->packageName = package;
    if (!fields[5].empty()) {
        uint64_t generation = 0;
        if (!ParseUnsigned(fields[5], &generation)) return false;
        receipt->generation = generation;
    }
    if (!canonical.empty()) receipt->durableRecordDigest = canonical;
    receipt->terminalState = std::move(terminal);
    receipt->verdict = verdict;
    return true;
}

std::string CanonicalGenerationJson(const InstallRequestV1& request,
    uint64_t generation, const ManagedFilesV1& managedFiles,
    const char* operation = "INSTALL")
{
    const ArtifactDescriptorV1& artifact = request.artifactSet.artifacts.front();
    std::vector<std::string> signers = request.signing.signerCertificateDigests;
    std::sort(signers.begin(), signers.end());
    std::string signerJson = "[";
    for (size_t index = 0; index < signers.size(); ++index) {
        if (index != 0) signerJson += ",";
        signerJson += JsonString(signers[index]);
    }
    signerJson += "]";
    std::vector<uint32_t> schemes = request.signing.schemeVersions;
    std::sort(schemes.begin(), schemes.end());
    std::string schemeJson = "[";
    for (size_t index = 0; index < schemes.size(); ++index) {
        if (index != 0) schemeJson += ",";
        schemeJson += std::to_string(schemes[index]);
    }
    schemeJson += "]";
    std::string lineageJson = "[";
    for (size_t index = 0;
         index < request.signing.lineage.size(); ++index) {
        if (index != 0) lineageJson += ",";
        lineageJson += "{\"capabilities\":" +
            std::to_string(
                request.signing.lineage[index].capabilities) +
            ",\"certificateSha256\":" +
            JsonString(request.signing.lineage[index].
                certificateSha256) + "}";
    }
    lineageJson += "]";

    // RFC 8785 object keys are emitted in UTF-16 lexical order. All v1 keys
    // are ASCII, so ordinary lexical order is identical here.
    return std::string("{") +
        "\"artifactSetDigest\":" + JsonString(request.artifactSet.artifactSetDigest) +
        ",\"artifacts\":[{\"artifactId\":" + JsonString(artifact.artifactId) +
        ",\"byteLength\":" + std::to_string(artifact.byteLength) +
        ",\"role\":\"BASE\",\"sha256\":" + JsonString(artifact.sha256) + "}]" +
        ",\"generation\":" + std::to_string(generation) +
        ",\"hostProjectionRef\":{\"logicalKey\":{\"generation\":" +
            std::to_string(generation) + ",\"packageName\":" +
            JsonString(request.manifest.packageName) +
            "},\"projectionKind\":\"BMS_PACKAGE\"}" +
        ",\"managedFiles\":{\"baseCodeDigest\":" +
            JsonString(managedFiles.baseCodeDigest) +
            ",\"baseCodePath\":" + JsonString(managedFiles.baseCodePath) + "}" +
        ",\"manifestFacts\":{\"applicationClassName\":" +
            JsonString(request.manifest.applicationClassName) +
            ",\"applicationLabel\":" +
            JsonString(request.manifest.applicationLabel) +
            ",\"components\":" + ComponentsJson(request.manifest.components) +
            ",\"declaredPermissions\":" +
            StringArrayJson(request.manifest.declaredPermissions) +
            ",\"minSdk\":" + std::to_string(request.manifest.minSdk) +
            ",\"provenance\":" +
            ProvenanceJson(request.manifest.provenance) +
            ",\"requestedPermissions\":" +
            StringArrayJson(request.manifest.requestedPermissions) +
            ",\"targetSdk\":" + std::to_string(request.manifest.targetSdk) +
            ",\"versionCode\":" + std::to_string(request.manifest.versionCode) +
            ",\"versionName\":" + JsonString(request.manifest.versionName) + "}" +
        ",\"operation\":" + JsonString(operation) +
        ",\"packageName\":" + JsonString(request.manifest.packageName) +
        ",\"primaryUserState\":{\"enabled\":true,\"hidden\":false,\"installed\":true,"
            "\"stopped\":false,\"userId\":" + std::to_string(request.userId) + "}" +
        ",\"provenance\":{\"parserVersion\":" + JsonString(request.manifest.parserVersion) +
            ",\"planDigest\":" + JsonString(request.admission.requestDigest) +
            ",\"policyProfile\":" + JsonString(request.signing.policyProfile) +
            ",\"verifierVersion\":" + JsonString(request.signing.verifierVersion) + "}" +
        ",\"schemaVersion\":1" +
        ",\"signingFacts\":{\"lineageDigest\":" +
            (request.signing.lineageDigest.has_value()
                ? JsonString(*request.signing.lineageDigest) : "null") +
            ",\"lineage\":" + lineageJson +
            ",\"schemeVersions\":" + schemeJson +
            ",\"signerCertificateDerHex\":" +
            StringArrayJson(request.signing.signerCertificateDerHex) +
            ",\"signerCertificateDigests\":" + signerJson +
            ",\"sourceReceiptDigest\":" +
            (request.signing.sourceReceiptDigest.has_value()
                ? JsonString(*request.signing.sourceReceiptDigest) :
                "null") + "}" +
        ",\"transactionId\":" + JsonString(request.admission.transactionId) +
        "}";
}

InstallRequestV1 AsInstallShape(const UpdateRequestV1& request)
{
    InstallRequestV1 shaped;
    shaped.admission = request.admission;
    shaped.artifactSet = request.artifactSet;
    shaped.manifest = request.manifest;
    shaped.signing = request.signing;
    shaped.userId = request.userId;
    shaped.expectedPackageName = request.expectedPackageName;
    shaped.expectedGeneration = request.expectedGeneration;
    shaped.policyRef = request.policyRef;
    shaped.retryIdentity = request.retryIdentity;
    return shaped;
}

std::string RetirementPlanCanonical(
    const GenerationRetirementPlanV1& plan)
{
    std::vector<RetirementObligationV1> obligations = plan.obligations;
    std::sort(obligations.begin(), obligations.end(),
        [](const RetirementObligationV1& left,
           const RetirementObligationV1& right) {
            return std::tie(left.kind, left.identityDigest) <
                std::tie(right.kind, right.identityDigest);
        });
    std::string result = "{\"journalRef\":" + JsonString(plan.journalRef) +
        ",\"newGeneration\":" + std::to_string(plan.newGeneration) +
        ",\"obligations\":[";
    for (size_t index = 0; index < obligations.size(); ++index) {
        if (index != 0) result += ",";
        result += "{\"identityDigest\":" +
            JsonString(obligations[index].identityDigest) +
            ",\"kind\":" + JsonString(obligations[index].kind) + "}";
    }
    result += "],\"oldCanonicalDigest\":" +
        JsonString(plan.oldCanonicalDigest) +
        ",\"oldGeneration\":" + std::to_string(plan.oldGeneration) +
        ",\"oldManagedCodeDigest\":" +
        JsonString(plan.oldManagedCodeDigest) +
        ",\"oldManagedCodePath\":" +
        JsonString(plan.oldManagedCodePath) +
        ",\"packageName\":" + JsonString(plan.packageName) +
        ",\"schemaVersion\":1,\"sharedDataPreserved\":true" +
        ",\"sharedDataRootIdentity\":" +
        JsonString(plan.sharedDataRootIdentity) +
        ",\"transactionId\":" + JsonString(plan.transactionId) +
        ",\"userId\":" + std::to_string(plan.userId) + "}";
    return result;
}

std::string ComputeRetirementPlanDigest(
    const GenerationRetirementPlanV1& plan)
{
    return Sha256Hex(RetirementPlanCanonical(plan));
}

bool DigestRegularFile(const std::string& path, std::string* digest,
    std::string* reason)
{
    if (digest == nullptr || path.empty() || path[0] != '/') {
        if (reason != nullptr) *reason = "managed file path is not absolute";
        return false;
    }
    const int file = open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (file < 0) {
        if (reason != nullptr) {
            *reason = std::string("managed file open failed: ") +
                std::strerror(errno);
        }
        return false;
    }
    struct stat status {};
    if (fstat(file, &status) != 0 || !S_ISREG(status.st_mode) ||
        status.st_size < 0) {
        if (reason != nullptr) *reason = "managed file is not a regular file";
        close(file);
        return false;
    }
    const size_t length = static_cast<size_t>(status.st_size);
    const void* mapped = nullptr;
    if (length != 0) {
        mapped = mmap(nullptr, length, PROT_READ, MAP_PRIVATE, file, 0);
        if (mapped == MAP_FAILED) {
            if (reason != nullptr) {
                *reason = std::string("managed file mmap failed: ") +
                    std::strerror(errno);
            }
            close(file);
            return false;
        }
    }
    unsigned char bytes[32]{};
    sha256(length == 0 ? nullptr :
        reinterpret_cast<const unsigned char*>(mapped), length, bytes);
    if (length != 0) munmap(const_cast<void*>(mapped), length);
    close(file);
    static constexpr char kHex[] = "0123456789abcdef";
    digest->assign(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        (*digest)[index * 2] = kHex[bytes[index] >> 4];
        (*digest)[index * 2 + 1] = kHex[bytes[index] & 0x0f];
    }
    return true;
}

}  // namespace

struct FilePackageStore::Impl {
    explicit Impl(std::string root)
        : storeRoot(std::move(root)), eventLog(storeRoot + "/events.v1.log")
    {
    }

    std::string storeRoot;
    std::string eventLog;
    mutable std::mutex mutex;
    int writerLeaseFd = -1;
    std::optional<std::pair<uint64_t, uint64_t>> writerLeaseIdentity;
    bool opened = false;
    bool readOnly = false;
    bool corrupt = false;
    uint64_t recordVersion = 0;
    std::map<std::string, JournalState> journals;
    std::map<std::string, PublishedPackageSnapshotV1> packages;
    std::map<std::string, PublicationTokenV1> publicationTokens;
    std::map<std::string, HostProjectionRuntimeV1> projections;
    std::map<std::string, GenerationRetirementPlanV1> retirementPlans;
    std::map<std::string, RemovalTombstoneV1> removalPlans;
    std::map<std::string, std::string> removalOwnerByPackage;
    std::map<std::string, uint64_t> lastGenerations;
    std::set<std::string> removalTombstones;
    std::set<std::string> quarantinedPackages;

    bool AcquireWriterLease(std::string* error)
    {
        if (writerLeaseFd >= 0) return true;
        struct stat directoryStatus {};
        if (stat(storeRoot.c_str(), &directoryStatus) != 0 ||
            !S_ISDIR(directoryStatus.st_mode)) {
            if (error != nullptr) {
                *error = "store root identity is unavailable";
            }
            return false;
        }
        const std::pair<uint64_t, uint64_t> identity = {
            static_cast<uint64_t>(directoryStatus.st_dev),
            static_cast<uint64_t>(directoryStatus.st_ino),
        };
        std::lock_guard<std::mutex> leaseLock(gStoreLeaseMutex);
        if (gStoreLeases.count(identity) != 0) {
            if (error != nullptr) {
                *error = "store writer lease is already held in this process";
            }
            return false;
        }
        const std::string lockPath = storeRoot + "/writer.v1.lock";
        const int lockFd = open(lockPath.c_str(),
            O_RDWR | O_CREAT | O_CLOEXEC | O_NOFOLLOW, 0600);
        if (lockFd < 0) {
            if (error != nullptr) {
                *error = std::string("store writer lease open failed: ") +
                    std::strerror(errno);
            }
            return false;
        }
        struct stat lockStatus {};
        if (fstat(lockFd, &lockStatus) != 0 ||
            !S_ISREG(lockStatus.st_mode)) {
            if (error != nullptr) {
                *error = "store writer lease is not a regular file";
            }
            close(lockFd);
            return false;
        }
        struct flock lease {};
        lease.l_type = F_WRLCK;
        lease.l_whence = SEEK_SET;
        lease.l_start = 0;
        lease.l_len = 0;
        if (fcntl(lockFd, F_SETLK, &lease) != 0) {
            if (error != nullptr) {
                *error = std::string("store writer lease unavailable: ") +
                    std::strerror(errno);
            }
            close(lockFd);
            return false;
        }
        gStoreLeases.insert(identity);
        writerLeaseFd = lockFd;
        writerLeaseIdentity = identity;
        return true;
    }

    void ReleaseWriterLease()
    {
        std::lock_guard<std::mutex> leaseLock(gStoreLeaseMutex);
        if (writerLeaseFd >= 0) {
            struct flock lease {};
            lease.l_type = F_UNLCK;
            lease.l_whence = SEEK_SET;
            lease.l_start = 0;
            lease.l_len = 0;
            (void)fcntl(writerLeaseFd, F_SETLK, &lease);
            close(writerLeaseFd);
            writerLeaseFd = -1;
        }
        if (writerLeaseIdentity.has_value()) {
            gStoreLeases.erase(*writerLeaseIdentity);
            writerLeaseIdentity.reset();
        }
    }

    bool ValidatePublishedPackage(const std::string& packageKey,
        const PublishedPackageSnapshotV1& snapshot, std::string* reason) const
    {
        const auto token = publicationTokens.find(packageKey);
        if (snapshot.userId != kPrimaryUserId || snapshot.packageName.empty() ||
            snapshot.generation == 0 ||
            !IsLowerHexDigest(snapshot.artifactSetDigest) ||
            !IsLowerHexDigest(snapshot.canonicalDigest) ||
            snapshot.managedFiles.baseCodePath.empty() ||
            !IsLowerHexDigest(snapshot.managedFiles.baseCodeDigest) ||
            snapshot.primaryUserState.userId != snapshot.userId ||
            snapshot.artifacts.size() != 1 ||
            snapshot.artifacts.front().artifactId.empty() ||
            snapshot.artifacts.front().sha256 !=
                snapshot.managedFiles.baseCodeDigest ||
            token == publicationTokens.end() ||
            token->second.packageName != snapshot.packageName ||
            token->second.userId != snapshot.userId ||
            token->second.generation != snapshot.generation ||
            token->second.canonicalDigest != snapshot.canonicalDigest ||
            (token->second.state != PublicationState::CANONICAL_SELECTED &&
                token->second.state != PublicationState::EXTERNAL_READY)) {
            if (reason != nullptr) {
                *reason = "canonical/token identity join failed";
            }
            return false;
        }
        if (snapshot.artifacts.front().byteLength != 0) {
            PackageArtifactSetV1 persistedArtifacts;
            ArtifactDescriptorV1 descriptor;
            descriptor.artifactId = snapshot.artifacts.front().artifactId;
            descriptor.role = ArtifactRole::BASE;
            descriptor.byteLength = snapshot.artifacts.front().byteLength;
            descriptor.sha256 = snapshot.artifacts.front().sha256;
            persistedArtifacts.artifacts.push_back(std::move(descriptor));
            if (ComputeArtifactSetDigest(persistedArtifacts) !=
                snapshot.artifactSetDigest) {
                if (reason != nullptr) {
                    *reason = "artifact provenance join failed";
                }
                return false;
            }
        }
        std::string actualDigest;
        if (!DigestRegularFile(snapshot.managedFiles.baseCodePath,
                &actualDigest, reason)) {
            return false;
        }
        if (actualDigest != snapshot.managedFiles.baseCodeDigest) {
            if (reason != nullptr) {
                *reason = "managed file digest mismatch";
            }
            return false;
        }
        return true;
    }

    void RefreshQuarantine()
    {
        quarantinedPackages.clear();
        for (const auto& [packageKey, snapshot] : packages) {
            if (removalTombstones.count(packageKey) != 0) {
                continue;
            }
            std::string reason;
            if (!ValidatePublishedPackage(packageKey, snapshot, &reason)) {
                quarantinedPackages.insert(packageKey);
            }
        }
    }

    bool ClosePublishedTransactionsAfterReplay(std::string* error)
    {
        std::vector<std::string> pending;
        for (const auto& [transactionId, journal] : journals) {
            if (!journal.receipt.has_value() &&
                !journal.updateReceipt.has_value() &&
                !journal.uninstallReceipt.has_value() &&
                journal.operation == "INSTALL" &&
                journal.phase ==
                    DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED) {
                pending.push_back(transactionId);
            }
        }
        for (const std::string& transactionId : pending) {
            const auto journal = journals.find(transactionId);
            if (journal == journals.end() ||
                !journal->second.packageName.has_value()) {
                if (error != nullptr) {
                    *error = "published journal has no package identity";
                }
                return false;
            }
            const std::string packageKey = PackageKey(journal->second.userId,
                *journal->second.packageName);
            const auto package = packages.find(packageKey);
            std::string validationReason;
            if (package == packages.end() ||
                quarantinedPackages.count(packageKey) != 0 ||
                !ValidatePublishedPackage(
                    packageKey, package->second, &validationReason)) {
                quarantinedPackages.insert(packageKey);
                continue;
            }
            PackageLifecycleReceiptV1 receipt;
            receipt.transactionId = transactionId;
            receipt.packageName = package->second.packageName;
            receipt.generation = package->second.generation;
            receipt.requestDigest = journal->second.requestDigest;
            receipt.artifactSetDigest = package->second.artifactSetDigest;
            receipt.durableRecordDigest = package->second.canonicalDigest;
            receipt.terminalState = "CLOSED_COMMITTED";
            receipt.verdict = InstallVerdict::COMMITTED;
            if (!AppendEvent(EncodeReceiptEvent("P6", receipt), error)) {
                return false;
            }
        }
        return true;
    }

    bool ApplyEvent(const std::string& payload)
    {
        const std::vector<std::string> fields = SplitTabs(payload);
        if (fields.empty()) return false;
        if (fields[0] == "P0") {
            if (fields.size() != 15) return false;
            JournalState journal;
            std::string packageName;
            std::string retryIdentity;
            std::string policySnapshotId;
            std::string operation;
            uint32_t memberIndex = 0;
            uint64_t jobRecordVersion = 0;
            if (!HexDecode(fields[1], &journal.transactionId) ||
                !HexDecode(fields[2], &journal.requestDigest) ||
                !HexDecode(fields[3], &journal.artifactSetDigest) ||
                !HexDecode(fields[4], &packageName) ||
                !ParseUnsigned(fields[5], &journal.userId) ||
                !ParseUnsigned(fields[6], &journal.candidateGeneration) ||
                !HexDecode(fields[7], &retryIdentity) ||
                !HexDecode(fields[8], &journal.jobId) ||
                !HexDecode(fields[9], &journal.memberId) ||
                !ParseUnsigned(fields[10], &memberIndex) ||
                !ParseUnsigned(fields[11], &jobRecordVersion) ||
                !HexDecode(fields[12],
                    &journal.callerScopeDigest) ||
                !HexDecode(fields[13], &policySnapshotId) ||
                !HexDecode(fields[14], &operation) ||
                retryIdentity.empty() || journal.jobId.empty() ||
                journal.memberId.empty() || jobRecordVersion == 0 ||
                journal.callerScopeDigest.empty() ||
                policySnapshotId.empty() ||
                (operation != "INSTALL" && operation != "UPDATE" &&
                    operation != "UNINSTALL")) {
                return false;
            }
            (void)memberIndex;
            if (!packageName.empty()) journal.packageName = packageName;
            journal.operation = std::move(operation);
            journal.phase = DurablePhase::P0_INPUT_FROZEN;
            journals[journal.transactionId] = journal;
        } else if (fields[0] == "PHASE") {
            if (fields.size() != 4) return false;
            std::string transaction;
            std::string phase;
            if (!HexDecode(fields[1], &transaction) ||
                !HexDecode(fields[2], &phase)) {
                return false;
            }
            uint64_t generation = 0;
            if (!ParseUnsigned(fields[3], &generation)) return false;
            auto iterator = journals.find(transaction);
            if (iterator == journals.end()) return false;
            iterator->second.candidateGeneration = generation;
            if (phase == DurablePhaseName(DurablePhase::P1_PLAN_DURABLE)) {
                iterator->second.phase = DurablePhase::P1_PLAN_DURABLE;
            } else if (phase == DurablePhaseName(DurablePhase::P2_FILES_PREPARED)) {
                iterator->second.phase = DurablePhase::P2_FILES_PREPARED;
            } else if (phase == DurablePhaseName(DurablePhase::P3_CANONICAL_PREPARED)) {
                iterator->second.phase = DurablePhase::P3_CANONICAL_PREPARED;
            } else if (phase == DurablePhaseName(DurablePhase::P4_PUBLICATION_PREPARED)) {
                iterator->second.phase = DurablePhase::P4_PUBLICATION_PREPARED;
            } else {
                return false;
            }
        } else if (fields[0] == "P5" || fields[0] == "P5V2" ||
                   fields[0] == "P5V3" || fields[0] == "P5V4" ||
                   fields[0] == "P5V5" ||
                   fields[0] == "UPDATE_P5V1" ||
                   fields[0] == "UPDATE_P5V2") {
            const bool isUpdate = fields[0] == "UPDATE_P5V1" ||
                fields[0] == "UPDATE_P5V2";
            const bool hasLineageFacts =
                fields[0] == "P5V5" ||
                fields[0] == "UPDATE_P5V2";
            const bool hasFacts = fields[0] != "P5";
            const bool hasSignerBytes =
                fields[0] == "P5V3" || fields[0] == "P5V4" ||
                fields[0] == "P5V5" ||
                isUpdate;
            const bool hasRecoveryFacts =
                fields[0] == "P5V4" || fields[0] == "P5V5" ||
                isUpdate;
            if ((fields[0] == "P5" && fields.size() != 11) ||
                (fields[0] == "P5V2" && fields.size() != 30) ||
                (fields[0] == "P5V3" && fields.size() != 31) ||
                ((fields[0] == "P5V4" ||
                    fields[0] == "UPDATE_P5V1") &&
                    fields.size() != 38) ||
                ((fields[0] == "P5V5" ||
                    fields[0] == "UPDATE_P5V2") &&
                    fields.size() != 40)) {
                return false;
            }
            PublishedPackageSnapshotV1 snapshot;
            std::string transaction;
            std::string managedPath;
            std::string publication;
            uint64_t eventRecordVersion = 0;
            if (!HexDecode(fields[1], &transaction) ||
                !HexDecode(fields[2], &snapshot.packageName) ||
                !ParseUnsigned(fields[3], &snapshot.userId) ||
                !ParseUnsigned(fields[4], &snapshot.generation) ||
                !HexDecode(fields[5], &snapshot.artifactSetDigest) ||
                !HexDecode(fields[6], &snapshot.canonicalDigest) ||
                !HexDecode(fields[7], &managedPath) ||
                !HexDecode(fields[8], &snapshot.managedFiles.baseCodeDigest) ||
                !HexDecode(fields[9], &publication) ||
                !ParseUnsigned(fields[10], &eventRecordVersion) ||
                eventRecordVersion != recordVersion + 1) {
                return false;
            }
            snapshot.managedFiles.baseCodePath = std::move(managedPath);
            if (hasFacts) {
                ManifestFactsV1 manifest;
                SigningFactsV1 signing;
                std::string versionName;
                std::string appClass;
                std::string appLabel;
                std::string verifierVersion;
                std::string policyProfile;
                std::string lineage;
                manifest.packageName = snapshot.packageName;
                if (!HexDecode(fields[11], &manifest.artifactSetDigest) ||
                    !HexDecode(fields[12], &manifest.parserVersion) ||
                    !ParseUnsigned(fields[13], &manifest.versionCode) ||
                    !HexDecode(fields[14], &versionName) ||
                    !ParseUnsigned(fields[15], &manifest.minSdk) ||
                    !ParseUnsigned(fields[16], &manifest.targetSdk) ||
                    !HexDecode(fields[17], &appClass) ||
                    !HexDecode(fields[18], &appLabel) ||
                    !DecodeComponents(fields[19], &manifest.components) ||
                    !DecodeStrings(fields[20],
                        &manifest.requestedPermissions) ||
                    !DecodeStrings(fields[21],
                        &manifest.declaredPermissions) ||
                    !DecodeProvenance(fields[22], &manifest.provenance) ||
                    !HexDecode(fields[23], &signing.artifactSetDigest) ||
                    !HexDecode(fields[24], &verifierVersion) ||
                    !HexDecode(fields[25], &policyProfile) ||
                    (fields[26] != "0" && fields[26] != "1") ||
                    !DecodeUnsigneds(fields[27],
                        &signing.schemeVersions) ||
                    !DecodeStrings(fields[28],
                        &signing.signerCertificateDigests) ||
                    !HexDecode(fields[29], &lineage) ||
                    (hasSignerBytes &&
                        !DecodeStrings(fields[30],
                            &signing.signerCertificateDerHex))) {
                    return false;
                }
                manifest.versionName = std::move(versionName);
                manifest.applicationClassName = std::move(appClass);
                manifest.applicationLabel = std::move(appLabel);
                signing.verifierVersion = std::move(verifierVersion);
                signing.policyProfile = std::move(policyProfile);
                signing.verified = fields[26] == "1";
                if (!lineage.empty()) signing.lineageDigest = lineage;
                if (hasLineageFacts) {
                    std::string sourceReceiptDigest;
                    if (!DecodeSigningLineage(
                            fields[31], &signing.lineage) ||
                        !HexDecode(fields[32],
                            &sourceReceiptDigest) ||
                        (!sourceReceiptDigest.empty() &&
                            !IsLowerHexDigest(
                                sourceReceiptDigest))) {
                        return false;
                    }
                    if (!sourceReceiptDigest.empty()) {
                        signing.sourceReceiptDigest =
                            sourceReceiptDigest;
                    }
                }
                if (manifest.artifactSetDigest !=
                        snapshot.artifactSetDigest ||
                    signing.artifactSetDigest !=
                        snapshot.artifactSetDigest ||
                    manifest.parserVersion.empty() ||
                    !signing.verified ||
                    signing.verifierVersion.empty()) {
                    return false;
                }
                snapshot.manifestFacts = std::move(manifest);
                snapshot.signingFacts = std::move(signing);
            }
            if (hasRecoveryFacts) {
                RecoveredArtifactV1 artifact;
                const size_t recoveryOffset =
                    hasLineageFacts ? 33 : 31;
                if ((fields[recoveryOffset] != "0" &&
                        fields[recoveryOffset] != "1") ||
                    (fields[recoveryOffset + 1] != "0" &&
                        fields[recoveryOffset + 1] != "1") ||
                    (fields[recoveryOffset + 2] != "0" &&
                        fields[recoveryOffset + 2] != "1") ||
                    (fields[recoveryOffset + 3] != "0" &&
                        fields[recoveryOffset + 3] != "1") ||
                    !HexDecode(fields[recoveryOffset + 4],
                        &artifact.artifactId) ||
                    !ParseUnsigned(fields[recoveryOffset + 5],
                        &artifact.byteLength) ||
                    !HexDecode(fields[recoveryOffset + 6],
                        &artifact.sha256) ||
                    artifact.artifactId.empty() ||
                    !IsLowerHexDigest(artifact.sha256) ||
                    artifact.sha256 !=
                        snapshot.managedFiles.baseCodeDigest) {
                    return false;
                }
                snapshot.primaryUserState.userId = snapshot.userId;
                snapshot.primaryUserState.installed =
                    fields[recoveryOffset] == "1";
                snapshot.primaryUserState.enabled =
                    fields[recoveryOffset + 1] == "1";
                snapshot.primaryUserState.stopped =
                    fields[recoveryOffset + 2] == "1";
                snapshot.primaryUserState.hidden =
                    fields[recoveryOffset + 3] == "1";
                snapshot.artifacts.push_back(artifact);
                PackageArtifactSetV1 persistedArtifacts;
                ArtifactDescriptorV1 descriptor;
                descriptor.artifactId = artifact.artifactId;
                descriptor.role = ArtifactRole::BASE;
                descriptor.byteLength = artifact.byteLength;
                descriptor.sha256 = artifact.sha256;
                persistedArtifacts.artifacts.push_back(std::move(descriptor));
                if (ComputeArtifactSetDigest(persistedArtifacts) !=
                    snapshot.artifactSetDigest) {
                    return false;
                }
            } else {
                snapshot.primaryUserState = {
                    snapshot.userId, true, true, false, false,
                };
                snapshot.artifacts.push_back({
                    "base", 0, snapshot.managedFiles.baseCodeDigest,
                });
            }
            if (publication != PublicationStateName(PublicationState::CANONICAL_SELECTED)) {
                return false;
            }
            const std::string packageKey =
                PackageKey(snapshot.userId, snapshot.packageName);
            auto token = publicationTokens.find(packageKey);
            auto journal = journals.find(transaction);
            if (journal == journals.end()) return false;
            if (isUpdate) {
                auto plan = retirementPlans.find(transaction);
                const auto oldPackage = packages.find(packageKey);
                if (journal->second.operation != "UPDATE" ||
                    plan == retirementPlans.end() ||
                    plan->second.state != RetirementPlanState::OPEN ||
                    plan->second.packageName != snapshot.packageName ||
                    plan->second.userId != snapshot.userId ||
                    plan->second.newGeneration != snapshot.generation ||
                    journal->second.candidateCanonicalDigest !=
                        std::optional<std::string>(
                            snapshot.canonicalDigest) ||
                    journal->second.candidateManagedFiles.baseCodePath !=
                        snapshot.managedFiles.baseCodePath ||
                    journal->second.candidateManagedFiles.baseCodeDigest !=
                        snapshot.managedFiles.baseCodeDigest ||
                    oldPackage == packages.end() ||
                    oldPackage->second.generation !=
                        plan->second.oldGeneration ||
                    oldPackage->second.canonicalDigest !=
                        plan->second.oldCanonicalDigest) {
                    return false;
                }
                PublicationTokenV1 updateToken;
                updateToken.packageName = snapshot.packageName;
                updateToken.userId = snapshot.userId;
                updateToken.generation = snapshot.generation;
                updateToken.canonicalDigest = snapshot.canonicalDigest;
                updateToken.state = PublicationState::CANONICAL_SELECTED;
                publicationTokens[packageKey] = updateToken;
                const auto projection = projections.find(packageKey);
                if (projection != projections.end() &&
                    projection->second.generation ==
                        plan->second.oldGeneration) {
                    projection->second.state = HostProjectionState::STALE;
                    plan->second.oldProjectionState =
                        HostProjectionState::STALE;
                } else {
                    plan->second.oldProjectionState =
                        HostProjectionState::NONE;
                }
                plan->second.state = RetirementPlanState::ACTIVE;
                plan->second.recordVersion = recordVersion + 1;
            } else {
                if (token == publicationTokens.end() ||
                    token->second.state != PublicationState::PREPARED ||
                    token->second.generation != snapshot.generation ||
                    token->second.canonicalDigest !=
                        snapshot.canonicalDigest) {
                    return false;
                }
                token->second.state =
                    PublicationState::CANONICAL_SELECTED;
            }
            snapshot.publicationState = PublicationState::CANONICAL_SELECTED;
            journal->second.phase = DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED;
            journal->second.candidateGeneration = snapshot.generation;
            journal->second.packageName = snapshot.packageName;
            packages[packageKey] = snapshot;
            lastGenerations[packageKey] =
                std::max(lastGenerations[packageKey], snapshot.generation);
        } else if (fields[0] == "P4") {
            if (fields.size() != 7) return false;
            std::string transaction;
            PublicationTokenV1 token;
            std::string publication;
            if (!HexDecode(fields[1], &transaction) ||
                !HexDecode(fields[2], &token.packageName) ||
                !ParseUnsigned(fields[3], &token.userId) ||
                !ParseUnsigned(fields[4], &token.generation) ||
                !HexDecode(fields[5], &token.canonicalDigest) ||
                !HexDecode(fields[6], &publication)) {
                return false;
            }
            if (publication != PublicationStateName(PublicationState::PREPARED)) {
                return false;
            }
            auto journal = journals.find(transaction);
            if (journal == journals.end()) return false;
            journal->second.phase = DurablePhase::P4_PUBLICATION_PREPARED;
            journal->second.candidateGeneration = token.generation;
            token.state = PublicationState::PREPARED;
            publicationTokens[PackageKey(token.userId, token.packageName)] = token;
        } else if (fields[0] == "UNINSTALL_PLAN") {
            if (fields.size() != 11) return false;
            RemovalTombstoneV1 tombstone;
            uint64_t expectedRecordVersion = 0;
            if (!HexDecode(fields[1], &tombstone.transactionId) ||
                !HexDecode(fields[2], &tombstone.requestDigest) ||
                !HexDecode(fields[3], &tombstone.packageName) ||
                !ParseUnsigned(fields[4], &tombstone.userId) ||
                !ParseUnsigned(fields[5], &tombstone.generation) ||
                !HexDecode(fields[6], &tombstone.canonicalDigest) ||
                !HexDecode(fields[7], &tombstone.managedCodePath) ||
                !HexDecode(fields[8], &tombstone.managedCodeDigest) ||
                !HexDecode(fields[9], &tombstone.tombstoneDigest) ||
                !ParseUnsigned(fields[10], &expectedRecordVersion) ||
                expectedRecordVersion != recordVersion ||
                tombstone.transactionId.empty() ||
                tombstone.requestDigest.empty() ||
                tombstone.packageName.empty() ||
                tombstone.generation == 0 ||
                !IsLowerHexDigest(tombstone.canonicalDigest) ||
                tombstone.managedCodePath.empty() ||
                !IsLowerHexDigest(tombstone.managedCodeDigest)) {
                return false;
            }
            tombstone.state = RemovalTombstoneState::PREPARED;
            tombstone.obligations = {
                {"PROJECTION", Sha256Hex("PROJECTION_ABSENCE\n" +
                    tombstone.packageName + "\n" +
                    std::to_string(tombstone.generation)),
                    RemovalObligationState::OPEN, "", 0},
                {"TOKEN", Sha256Hex("TOKEN_ABSENCE\n" +
                    tombstone.packageName + "\n" +
                    std::to_string(tombstone.generation)),
                    RemovalObligationState::OPEN, "", 0},
                {"CODE", tombstone.managedCodeDigest,
                    RemovalObligationState::OPEN, "", 0},
                {"DATA", Sha256Hex("DATA_ROOT_ABSENCE\n" +
                    std::to_string(tombstone.userId) + "\n" +
                    tombstone.packageName),
                    RemovalObligationState::OPEN, "", 0},
                {"NATIVE", Sha256Hex("NATIVE_ABSENCE\n" +
                    tombstone.packageName + "\n" +
                    std::to_string(tombstone.generation)),
                    RemovalObligationState::OPEN, "", 0},
                {"RESOURCE", Sha256Hex("RESOURCE_ABSENCE\n" +
                    tombstone.packageName + "\n" +
                    std::to_string(tombstone.generation)),
                    RemovalObligationState::OPEN, "", 0},
                {"PRESENTATION", Sha256Hex("PRESENTATION_ABSENCE\n" +
                    tombstone.packageName + "\n" +
                    std::to_string(tombstone.generation)),
                    RemovalObligationState::OPEN, "", 0},
            };
            if (tombstone.tombstoneDigest !=
                    ComputeRemovalTombstoneDigest(tombstone) ||
                removalPlans.count(tombstone.transactionId) != 0) {
                return false;
            }
            auto journal = journals.find(tombstone.transactionId);
            const std::string packageKey = PackageKey(
                tombstone.userId, tombstone.packageName);
            const auto package = packages.find(packageKey);
            if (journal == journals.end() ||
                journal->second.operation != "UNINSTALL" ||
                journal->second.requestDigest !=
                    tombstone.requestDigest ||
                journal->second.packageName !=
                    std::optional<std::string>(
                        tombstone.packageName) ||
                package == packages.end() ||
                package->second.generation != tombstone.generation ||
                package->second.canonicalDigest !=
                    tombstone.canonicalDigest ||
                package->second.managedFiles.baseCodePath !=
                    tombstone.managedCodePath ||
                package->second.managedFiles.baseCodeDigest !=
                    tombstone.managedCodeDigest) {
                return false;
            }
            journal->second.phase = DurablePhase::P1_PLAN_DURABLE;
            journal->second.candidateGeneration =
                tombstone.generation;
            tombstone.recordVersion = recordVersion + 1;
            removalPlans[tombstone.transactionId] =
                std::move(tombstone);
        } else if (fields[0] == "UNINSTALL_P5") {
            if (fields.size() != 3) return false;
            std::string transaction;
            uint64_t expectedRecordVersion = 0;
            if (!HexDecode(fields[1], &transaction) ||
                !ParseUnsigned(fields[2], &expectedRecordVersion) ||
                expectedRecordVersion != recordVersion) {
                return false;
            }
            auto journal = journals.find(transaction);
            auto tombstone = removalPlans.find(transaction);
            if (journal == journals.end() ||
                journal->second.operation != "UNINSTALL" ||
                tombstone == removalPlans.end() ||
                tombstone->second.state !=
                    RemovalTombstoneState::PREPARED) {
                return false;
            }
            const std::string packageKey = PackageKey(
                tombstone->second.userId,
                tombstone->second.packageName);
            const auto package = packages.find(packageKey);
            if (package == packages.end() ||
                package->second.generation !=
                    tombstone->second.generation ||
                package->second.canonicalDigest !=
                    tombstone->second.canonicalDigest ||
                removalTombstones.count(packageKey) != 0) {
                return false;
            }
            tombstone->second.state =
                RemovalTombstoneState::OPEN;
            tombstone->second.recordVersion = recordVersion + 1;
            removalTombstones.insert(packageKey);
            removalOwnerByPackage[packageKey] = transaction;
            auto projection = projections.find(packageKey);
            if (projection != projections.end()) {
                projection->second.state =
                    HostProjectionState::REMOVING;
            }
            journal->second.phase =
                DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED;
        } else if (fields[0] == "UNINSTALL_OBLIGATION") {
            if (fields.size() != 5) return false;
            std::string transaction;
            std::string kind;
            std::string closeResult;
            uint64_t expectedRecordVersion = 0;
            if (!HexDecode(fields[1], &transaction) ||
                !HexDecode(fields[2], &kind) ||
                !HexDecode(fields[3], &closeResult) ||
                !ParseUnsigned(fields[4], &expectedRecordVersion) ||
                expectedRecordVersion != recordVersion ||
                closeResult.empty()) {
                return false;
            }
            auto tombstone = removalPlans.find(transaction);
            if (tombstone == removalPlans.end() ||
                tombstone->second.state !=
                    RemovalTombstoneState::OPEN) {
                return false;
            }
            auto obligation = std::find_if(
                tombstone->second.obligations.begin(),
                tombstone->second.obligations.end(),
                [&](const RemovalObligationV1& item) {
                    return item.kind == kind;
                });
            if (obligation ==
                    tombstone->second.obligations.end() ||
                obligation->state ==
                    RemovalObligationState::CLOSED) {
                return false;
            }
            const std::string packageKey = PackageKey(
                tombstone->second.userId,
                tombstone->second.packageName);
            if (kind == "PROJECTION") {
                const auto projection = projections.find(packageKey);
                if (projection != projections.end() &&
                    projection->second.state !=
                        HostProjectionState::REMOVING) {
                    return false;
                }
                projections.erase(packageKey);
            } else if (kind == "TOKEN") {
                publicationTokens.erase(packageKey);
            }
            obligation->state = RemovalObligationState::CLOSED;
            obligation->closeResult = closeResult;
            obligation->closedRecordVersion = recordVersion + 1;
            tombstone->second.recordVersion = recordVersion + 1;
        } else if (fields[0] == "UNINSTALL_CLOSE") {
            if (fields.size() != 3) return false;
            std::string transaction;
            uint64_t expectedRecordVersion = 0;
            if (!HexDecode(fields[1], &transaction) ||
                !ParseUnsigned(fields[2], &expectedRecordVersion) ||
                expectedRecordVersion != recordVersion) {
                return false;
            }
            auto tombstone = removalPlans.find(transaction);
            if (tombstone == removalPlans.end() ||
                tombstone->second.state !=
                    RemovalTombstoneState::OPEN ||
                !std::all_of(
                    tombstone->second.obligations.begin(),
                    tombstone->second.obligations.end(),
                    [](const RemovalObligationV1& item) {
                        return item.state ==
                            RemovalObligationState::CLOSED;
                    })) {
                return false;
            }
            const std::string packageKey = PackageKey(
                tombstone->second.userId,
                tombstone->second.packageName);
            const auto package = packages.find(packageKey);
            if (package == packages.end() ||
                package->second.generation !=
                    tombstone->second.generation ||
                package->second.canonicalDigest !=
                    tombstone->second.canonicalDigest) {
                return false;
            }
            packages.erase(packageKey);
            publicationTokens.erase(packageKey);
            projections.erase(packageKey);
            removalTombstones.erase(packageKey);
            removalOwnerByPackage.erase(packageKey);
            quarantinedPackages.erase(packageKey);
            tombstone->second.state =
                RemovalTombstoneState::CLOSED_REMOVED;
            tombstone->second.recordVersion = recordVersion + 1;
        } else if (fields[0] == "UPDATE_PLAN") {
            if (fields.size() != 14) return false;
            GenerationRetirementPlanV1 plan;
            std::string projectionState;
            uint64_t expectedRecordVersion = 0;
            if (!HexDecode(fields[1], &plan.transactionId) ||
                !HexDecode(fields[2], &plan.journalRef) ||
                !HexDecode(fields[3], &plan.packageName) ||
                !ParseUnsigned(fields[4], &plan.userId) ||
                !ParseUnsigned(fields[5], &plan.oldGeneration) ||
                !ParseUnsigned(fields[6], &plan.newGeneration) ||
                !HexDecode(fields[7], &plan.oldCanonicalDigest) ||
                !HexDecode(fields[8], &plan.oldManagedCodePath) ||
                !HexDecode(fields[9], &plan.oldManagedCodeDigest) ||
                !HexDecode(fields[10], &plan.sharedDataRootIdentity) ||
                !HexDecode(fields[11], &projectionState) ||
                !HexDecode(fields[12], &plan.planDigest) ||
                !ParseUnsigned(fields[13], &expectedRecordVersion) ||
                expectedRecordVersion != recordVersion ||
                plan.transactionId.empty() || plan.journalRef.empty() ||
                plan.packageName.empty() || plan.oldGeneration == 0 ||
                plan.newGeneration != plan.oldGeneration + 1 ||
                !IsLowerHexDigest(plan.oldCanonicalDigest) ||
                !IsLowerHexDigest(plan.oldManagedCodeDigest) ||
                !IsLowerHexDigest(plan.sharedDataRootIdentity)) {
                return false;
            }
            if (projectionState ==
                HostProjectionStateName(HostProjectionState::ACTIVE)) {
                plan.oldProjectionState = HostProjectionState::ACTIVE;
            } else if (projectionState ==
                       HostProjectionStateName(HostProjectionState::NONE)) {
                plan.oldProjectionState = HostProjectionState::NONE;
            } else {
                return false;
            }
            plan.sharedDataPreserved = true;
            plan.state = RetirementPlanState::OPEN;
            plan.obligations = {
                {"CODE", plan.oldManagedCodeDigest,
                    RetirementObligationState::OPEN, "", 0},
                {"NATIVE", Sha256Hex("NATIVE_ABSENCE\n" +
                    plan.packageName + "\n" +
                    std::to_string(plan.oldGeneration)),
                    RetirementObligationState::OPEN, "", 0},
                {"RESOURCE", Sha256Hex("RESOURCE_ABSENCE\n" +
                    plan.packageName + "\n" +
                    std::to_string(plan.oldGeneration)),
                    RetirementObligationState::OPEN, "", 0},
            };
            if (plan.planDigest != ComputeRetirementPlanDigest(plan) ||
                retirementPlans.count(plan.transactionId) != 0) {
                return false;
            }
            auto journal = journals.find(plan.transactionId);
            if (journal == journals.end() ||
                journal->second.operation != "UPDATE" ||
                journal->second.packageName !=
                    std::optional<std::string>(plan.packageName) ||
                journal->second.candidateGeneration !=
                    plan.newGeneration) {
                return false;
            }
            journal->second.phase = DurablePhase::P1_PLAN_DURABLE;
            plan.recordVersion = recordVersion + 1;
            retirementPlans[plan.transactionId] = std::move(plan);
        } else if (fields[0] == "UPDATE_STAGE") {
            if (fields.size() != 6) return false;
            std::string transaction;
            std::string path;
            std::string digest;
            uint64_t generation = 0;
            uint64_t expectedRecordVersion = 0;
            if (!HexDecode(fields[1], &transaction) ||
                !ParseUnsigned(fields[2], &generation) ||
                !HexDecode(fields[3], &path) ||
                !HexDecode(fields[4], &digest) ||
                !ParseUnsigned(fields[5], &expectedRecordVersion) ||
                expectedRecordVersion != recordVersion ||
                path.empty() || !IsLowerHexDigest(digest)) {
                return false;
            }
            auto journal = journals.find(transaction);
            auto plan = retirementPlans.find(transaction);
            if (journal == journals.end() ||
                journal->second.operation != "UPDATE" ||
                plan == retirementPlans.end() ||
                plan->second.state != RetirementPlanState::OPEN ||
                plan->second.newGeneration != generation) {
                return false;
            }
            journal->second.candidateGeneration = generation;
            journal->second.candidateManagedFiles = {path, digest};
            journal->second.phase = DurablePhase::P2_FILES_PREPARED;
            plan->second.recordVersion = recordVersion + 1;
        } else if (fields[0] == "UPDATE_P4") {
            if (fields.size() != 5) return false;
            std::string transaction;
            std::string canonicalDigest;
            uint64_t generation = 0;
            uint64_t expectedRecordVersion = 0;
            if (!HexDecode(fields[1], &transaction) ||
                !ParseUnsigned(fields[2], &generation) ||
                !HexDecode(fields[3], &canonicalDigest) ||
                !ParseUnsigned(fields[4], &expectedRecordVersion) ||
                expectedRecordVersion != recordVersion ||
                !IsLowerHexDigest(canonicalDigest)) {
                return false;
            }
            auto journal = journals.find(transaction);
            auto plan = retirementPlans.find(transaction);
            if (journal == journals.end() ||
                journal->second.operation != "UPDATE" ||
                plan == retirementPlans.end() ||
                plan->second.state != RetirementPlanState::OPEN ||
                plan->second.newGeneration != generation ||
                journal->second.candidateManagedFiles.baseCodePath.empty()) {
                return false;
            }
            journal->second.candidateCanonicalDigest = canonicalDigest;
            journal->second.phase = DurablePhase::P4_PUBLICATION_PREPARED;
            plan->second.recordVersion = recordVersion + 1;
        } else if (fields[0] == "RETIRE_PROJECTION") {
            if (fields.size() != 4) return false;
            std::string transaction;
            std::string state;
            uint64_t expectedRecordVersion = 0;
            if (!HexDecode(fields[1], &transaction) ||
                !HexDecode(fields[2], &state) ||
                !ParseUnsigned(fields[3], &expectedRecordVersion) ||
                expectedRecordVersion != recordVersion) {
                return false;
            }
            auto plan = retirementPlans.find(transaction);
            if (plan == retirementPlans.end() ||
                plan->second.state != RetirementPlanState::ACTIVE) {
                return false;
            }
            const std::string packageKey =
                PackageKey(plan->second.userId, plan->second.packageName);
            if (state ==
                HostProjectionStateName(HostProjectionState::REMOVING)) {
                if (plan->second.oldProjectionState !=
                        HostProjectionState::STALE) {
                    return false;
                }
                plan->second.oldProjectionState =
                    HostProjectionState::REMOVING;
                auto projection = projections.find(packageKey);
                if (projection != projections.end()) {
                    projection->second.state =
                        HostProjectionState::REMOVING;
                }
            } else if (state ==
                       HostProjectionStateName(HostProjectionState::NONE)) {
                if (plan->second.oldProjectionState !=
                        HostProjectionState::REMOVING &&
                    plan->second.oldProjectionState !=
                        HostProjectionState::NONE) {
                    return false;
                }
                plan->second.oldProjectionState =
                    HostProjectionState::NONE;
                projections.erase(packageKey);
            } else {
                return false;
            }
            plan->second.recordVersion = recordVersion + 1;
        } else if (fields[0] == "RETIRE_OBLIGATION") {
            if (fields.size() != 5) return false;
            std::string transaction;
            std::string kind;
            std::string closeResult;
            uint64_t expectedRecordVersion = 0;
            if (!HexDecode(fields[1], &transaction) ||
                !HexDecode(fields[2], &kind) ||
                !HexDecode(fields[3], &closeResult) ||
                !ParseUnsigned(fields[4], &expectedRecordVersion) ||
                expectedRecordVersion != recordVersion ||
                closeResult.empty()) {
                return false;
            }
            auto plan = retirementPlans.find(transaction);
            if (plan == retirementPlans.end() ||
                plan->second.state != RetirementPlanState::ACTIVE) {
                return false;
            }
            auto obligation = std::find_if(
                plan->second.obligations.begin(),
                plan->second.obligations.end(),
                [&](const RetirementObligationV1& item) {
                    return item.kind == kind;
                });
            if (obligation == plan->second.obligations.end()) return false;
            if (obligation->state == RetirementObligationState::CLOSED) {
                return false;
            }
            obligation->state = RetirementObligationState::CLOSED;
            obligation->closeResult = closeResult;
            obligation->closedRecordVersion = recordVersion + 1;
            plan->second.recordVersion = recordVersion + 1;
        } else if (fields[0] == "RETIRE_CLOSED") {
            if (fields.size() != 3) return false;
            std::string transaction;
            uint64_t expectedRecordVersion = 0;
            if (!HexDecode(fields[1], &transaction) ||
                !ParseUnsigned(fields[2], &expectedRecordVersion) ||
                expectedRecordVersion != recordVersion) {
                return false;
            }
            auto plan = retirementPlans.find(transaction);
            if (plan == retirementPlans.end() ||
                plan->second.state != RetirementPlanState::ACTIVE ||
                plan->second.oldProjectionState !=
                    HostProjectionState::NONE ||
                !plan->second.sharedDataPreserved ||
                !std::all_of(plan->second.obligations.begin(),
                    plan->second.obligations.end(),
                    [](const RetirementObligationV1& item) {
                        return item.state ==
                            RetirementObligationState::CLOSED;
                    })) {
                return false;
            }
            plan->second.state = RetirementPlanState::CLOSED;
            plan->second.recordVersion = recordVersion + 1;
        } else if (fields[0] == "UNINSTALL_P6" ||
                   fields[0] == "UNINSTALL_REJECT") {
            UninstallReceiptV1 receipt;
            if (!DecodeUninstallReceiptFields(fields, &receipt)) {
                return false;
            }
            auto journal = journals.find(receipt.transactionId);
            if (journal == journals.end() ||
                journal->second.operation != "UNINSTALL") {
                return false;
            }
            if (fields[0] == "UNINSTALL_P6") {
                const auto tombstone =
                    removalPlans.find(receipt.transactionId);
                if (receipt.verdict !=
                        UninstallVerdict::REMOVED ||
                    tombstone == removalPlans.end() ||
                    tombstone->second.state !=
                        RemovalTombstoneState::CLOSED_REMOVED ||
                    receipt.tombstoneDigest !=
                        std::optional<std::string>(
                            tombstone->second.tombstoneDigest) ||
                    !receipt.residualObligations.empty()) {
                    return false;
                }
            }
            journal->second.phase =
                DurablePhase::P6_RECEIPT_CLOSED;
            journal->second.uninstallReceipt = receipt;
        } else if (fields[0] == "UPDATE_P6" ||
                   fields[0] == "UPDATE_REJECT" ||
                   fields[0] == "UPDATE_ROLLBACK") {
            UpdateReceiptV1 receipt;
            if (!DecodeUpdateReceiptFields(fields, &receipt)) return false;
            auto journal = journals.find(receipt.transactionId);
            if (journal == journals.end() ||
                journal->second.operation != "UPDATE") {
                return false;
            }
            if (fields[0] == "UPDATE_P6") {
                const auto plan = retirementPlans.find(
                    receipt.transactionId);
                if (receipt.verdict != UpdateVerdict::UPDATED ||
                    plan == retirementPlans.end() ||
                    plan->second.state != RetirementPlanState::CLOSED ||
                    receipt.retirementPlanDigest !=
                        std::optional<std::string>(
                            plan->second.planDigest)) {
                    return false;
                }
            }
            journal->second.phase = DurablePhase::P6_RECEIPT_CLOSED;
            journal->second.updateReceipt = receipt;
        } else if (fields[0] == "P6" || fields[0] == "REJECT" ||
                   fields[0] == "ROLLBACK") {
            PackageLifecycleReceiptV1 receipt;
            if (!DecodeReceiptFields(fields, &receipt)) return false;
            auto journal = journals.find(receipt.transactionId);
            if (journal == journals.end()) {
                JournalState created;
                created.transactionId = receipt.transactionId;
                created.requestDigest = receipt.requestDigest;
                created.artifactSetDigest = receipt.artifactSetDigest.value_or("");
                created.packageName = receipt.packageName;
                created.candidateGeneration = receipt.generation.value_or(0);
                journals[receipt.transactionId] = created;
                journal = journals.find(receipt.transactionId);
            }
            if (fields[0] == "ROLLBACK" && receipt.packageName.has_value()) {
                publicationTokens.erase(
                    PackageKey(journal->second.userId, *receipt.packageName));
            }
            journal->second.phase = DurablePhase::P6_RECEIPT_CLOSED;
            journal->second.receipt = receipt;
        } else if (fields[0] == "TOMBSTONE") {
            if (fields.size() != 4) return false;
            std::string packageName;
            uint32_t userId = 0;
            uint64_t generation = 0;
            if (!ParseUnsigned(fields[1], &userId) ||
                !HexDecode(fields[2], &packageName) ||
                !ParseUnsigned(fields[3], &generation)) {
                return false;
            }
            (void)generation;
            const std::string packageKey = PackageKey(userId, packageName);
            removalTombstones.insert(packageKey);
            lastGenerations[packageKey] =
                std::max(lastGenerations[packageKey], generation);
        } else if (fields[0] == "PROJECTION") {
            if (fields.size() != 7) return false;
            HostProjectionRuntimeV1 projection;
            std::string projectionState;
            std::string tokenState;
            if (!ParseUnsigned(fields[1], &projection.userId) ||
                !HexDecode(fields[2], &projection.packageName) ||
                !ParseUnsigned(fields[3], &projection.generation) ||
                !HexDecode(fields[4], &projection.canonicalDigest) ||
                !HexDecode(fields[5], &projectionState) ||
                !HexDecode(fields[6], &tokenState)) {
                return false;
            }
            if (projectionState == HostProjectionStateName(
                    HostProjectionState::ACTIVE)) {
                projection.state = HostProjectionState::ACTIVE;
            } else if (projectionState == HostProjectionStateName(
                           HostProjectionState::PREPARED)) {
                projection.state = HostProjectionState::PREPARED;
            } else if (projectionState == HostProjectionStateName(
                           HostProjectionState::NONE)) {
                projection.state = HostProjectionState::NONE;
            } else {
                return false;
            }
            PublicationState parsedTokenState = PublicationState::NONE;
            if (tokenState == PublicationStateName(
                    PublicationState::CANONICAL_SELECTED)) {
                parsedTokenState = PublicationState::CANONICAL_SELECTED;
            } else if (tokenState == PublicationStateName(
                           PublicationState::EXTERNAL_READY)) {
                parsedTokenState = PublicationState::EXTERNAL_READY;
            } else if (tokenState == PublicationStateName(
                           PublicationState::PREPARED)) {
                parsedTokenState = PublicationState::PREPARED;
            } else {
                return false;
            }
            const std::string packageKey =
                PackageKey(projection.userId, projection.packageName);
            auto token = publicationTokens.find(packageKey);
            if (token == publicationTokens.end()) return false;
            token->second.state = parsedTokenState;
            projections[packageKey] = projection;
        } else {
            return false;
        }
        ++recordVersion;
        return true;
    }

    bool AppendEvent(const std::string& payload, std::string* error)
    {
        const std::string record = payload + "\t" + Sha256Hex(payload) + "\n";
        const int file = open(eventLog.c_str(),
            O_WRONLY | O_APPEND | O_CREAT | O_CLOEXEC, 0600);
        if (file < 0) {
            if (error != nullptr) *error = std::strerror(errno);
            return false;
        }
        bool success = WriteAll(file,
            reinterpret_cast<const uint8_t*>(record.data()), record.size(), error);
        if (success && fsync(file) != 0) {
            if (error != nullptr) *error = std::strerror(errno);
            success = false;
        }
        close(file);
        if (!success) return false;
        if (!ApplyEvent(payload)) {
            corrupt = true;
            if (error != nullptr) *error = "internal event replay failure";
            return false;
        }
        return true;
    }

    bool OpenLocked(std::string* error)
    {
        if (opened) {
            if (readOnly) {
                if (error != nullptr) {
                    *error = "read-only package store cannot become a writer";
                }
                return false;
            }
            if (corrupt && error != nullptr) *error = "store is corrupt";
            return !corrupt;
        }
        if (!EnsureDirectoryTree(storeRoot, error)) {
            return false;
        }
        if (!AcquireWriterLease(error)) {
            return false;
        }
        std::ifstream input(eventLog, std::ios::binary);
        if (!input.good()) {
            if (errno != ENOENT && access(eventLog.c_str(), F_OK) == 0) {
                if (error != nullptr) *error = "unable to read event log";
                return false;
            }
            const int file = open(eventLog.c_str(),
                O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
            if (file >= 0) {
                close(file);
                if (!FsyncDirectory(storeRoot, error)) return false;
            } else if (errno != EEXIST) {
                if (error != nullptr) *error = std::strerror(errno);
                return false;
            }
            opened = true;
            return true;
        }
        std::ostringstream buffer;
        buffer << input.rdbuf();
        const std::string contents = buffer.str();
        if (!contents.empty() && contents.back() != '\n') {
            corrupt = true;
            if (error != nullptr) *error = "truncated event log";
            opened = true;
            return false;
        }
        size_t begin = 0;
        while (begin < contents.size()) {
            const size_t end = contents.find('\n', begin);
            const std::string line = contents.substr(begin, end - begin);
            begin = end + 1;
            const size_t checksumSeparator = line.find_last_of('\t');
            if (checksumSeparator == std::string::npos) {
                corrupt = true;
                break;
            }
            const std::string payload = line.substr(0, checksumSeparator);
            const std::string checksum = line.substr(checksumSeparator + 1);
            if (checksum != Sha256Hex(payload) || !ApplyEvent(payload)) {
                corrupt = true;
                break;
            }
        }
        opened = true;
        if (corrupt && error != nullptr) *error = "event log checksum/schema failure";
        if (corrupt) return false;
        RefreshQuarantine();
        if (!ClosePublishedTransactionsAfterReplay(error)) {
            corrupt = true;
            return false;
        }
        return true;
    }

    void ResetReplayState()
    {
        corrupt = false;
        recordVersion = 0;
        journals.clear();
        packages.clear();
        publicationTokens.clear();
        projections.clear();
        retirementPlans.clear();
        removalPlans.clear();
        removalOwnerByPackage.clear();
        lastGenerations.clear();
        removalTombstones.clear();
        quarantinedPackages.clear();
    }

    bool ReplayReadOnlyLocked(std::string* error)
    {
        struct stat directoryStatus {};
        if (stat(storeRoot.c_str(), &directoryStatus) != 0 ||
            !S_ISDIR(directoryStatus.st_mode)) {
            if (error != nullptr) *error = "package store is not ready";
            return false;
        }
        const std::pair<uint64_t, uint64_t> identity = {
            static_cast<uint64_t>(directoryStatus.st_dev),
            static_cast<uint64_t>(directoryStatus.st_ino),
        };
        const std::string lockPath = storeRoot + "/writer.v1.lock";
        const int lockFd = open(lockPath.c_str(),
            O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
        if (lockFd < 0) {
            if (error != nullptr) {
                *error = std::string("package store reader lock unavailable: ") +
                    std::strerror(errno);
            }
            return false;
        }
        struct stat lockStatus {};
        if (fstat(lockFd, &lockStatus) != 0 || !S_ISREG(lockStatus.st_mode)) {
            if (error != nullptr) {
                *error = "package store reader lock is not a regular file";
            }
            close(lockFd);
            return false;
        }

        bool localWriter = false;
        {
            std::lock_guard<std::mutex> leaseLock(gStoreLeaseMutex);
            localWriter = gStoreLeases.count(identity) != 0;
        }
        if (localWriter) {
            if (error != nullptr) {
                *error = "package store writer is active in this process";
            }
            close(lockFd);
            return false;
        }
        struct flock lease {};
        lease.l_type = F_RDLCK;
        lease.l_whence = SEEK_SET;
        lease.l_start = 0;
        lease.l_len = 0;
        if (fcntl(lockFd, F_SETLK, &lease) != 0) {
            if (error != nullptr) {
                *error = std::string("package store writer is active: ") +
                    std::strerror(errno);
            }
            close(lockFd);
            return false;
        }
        const auto releaseReaderLease = [&]() {
            struct flock lease {};
            lease.l_type = F_UNLCK;
            lease.l_whence = SEEK_SET;
            lease.l_start = 0;
            lease.l_len = 0;
            (void)fcntl(lockFd, F_SETLK, &lease);
            close(lockFd);
        };

        std::ifstream input(eventLog, std::ios::binary);
        if (!input.good()) {
            if (error != nullptr) *error = "package store event log is not ready";
            releaseReaderLease();
            return false;
        }
        std::ostringstream buffer;
        buffer << input.rdbuf();
        const std::string contents = buffer.str();
        if (!contents.empty() && contents.back() != '\n') {
            if (error != nullptr) *error = "truncated event log";
            releaseReaderLease();
            return false;
        }
        ResetReplayState();
        size_t begin = 0;
        while (begin < contents.size()) {
            const size_t end = contents.find('\n', begin);
            const std::string line = contents.substr(begin, end - begin);
            begin = end + 1;
            const size_t checksumSeparator = line.find_last_of('\t');
            if (checksumSeparator == std::string::npos) {
                corrupt = true;
                break;
            }
            const std::string payload = line.substr(0, checksumSeparator);
            const std::string checksum = line.substr(checksumSeparator + 1);
            if (checksum != Sha256Hex(payload) || !ApplyEvent(payload)) {
                corrupt = true;
                break;
            }
        }
        releaseReaderLease();
        opened = true;
        readOnly = true;
        if (corrupt && error != nullptr) {
            *error = "event log checksum/schema failure";
        }
        if (corrupt) return false;
        RefreshQuarantine();
        if (error != nullptr) error->clear();
        return true;
    }

    bool OpenReadOnlyLocked(std::string* error)
    {
        if (opened && !readOnly) {
            if (error != nullptr) {
                *error = "writer package store cannot become read-only";
            }
            return false;
        }
        if (corrupt) {
            if (error != nullptr) *error = "store is corrupt";
            return false;
        }
        return ReplayReadOnlyLocked(error);
    }

    bool ReadLocked(std::string* error)
    {
        if (opened && readOnly) return ReplayReadOnlyLocked(error);
        if (opened) {
            if (corrupt && error != nullptr) *error = "store is corrupt";
            return !corrupt;
        }
        return OpenLocked(error);
    }
};

PosixPackageFileStager::PosixPackageFileStager(std::string managedRoot)
    : managedRoot_(std::move(managedRoot))
{
}

bool PosixPackageFileStager::Stage(const std::string& packageName,
    uint32_t userId, uint64_t generation, const ArtifactDescriptorV1& artifact,
    ManagedFilesV1* managedFiles, std::string* error)
{
    if (managedFiles == nullptr || artifact.role != ArtifactRole::BASE ||
        packageName.empty() || managedRoot_.empty()) {
        if (error != nullptr) *error = "invalid staging input";
        return false;
    }
    const std::string packageDirectory = managedRoot_ + "/" +
        std::to_string(userId) + "/" + HexEncode(packageName) + "/" +
        std::to_string(generation);
    if (!EnsureDirectoryTree(packageDirectory, error)) return false;
    const std::string finalPath = packageDirectory + "/base.apk";
    const std::string temporaryPath = finalPath + ".tmp." + std::to_string(getpid());
    const int file = open(temporaryPath.c_str(),
        O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (file < 0) {
        if (errno == EEXIST) unlink(temporaryPath.c_str());
        if (error != nullptr) *error = std::strerror(errno);
        return false;
    }
    bool success = WriteAll(file, artifact.bytes.data(), artifact.bytes.size(), error);
    if (success && fsync(file) != 0) {
        if (error != nullptr) *error = std::strerror(errno);
        success = false;
    }
    close(file);
    if (success && rename(temporaryPath.c_str(), finalPath.c_str()) != 0) {
        if (error != nullptr) *error = std::strerror(errno);
        success = false;
    }
    if (success) success = FsyncDirectory(packageDirectory, error);
    if (!success) {
        unlink(temporaryPath.c_str());
        return false;
    }
    managedFiles->baseCodePath = finalPath;
    managedFiles->baseCodeDigest = Sha256Hex(artifact.bytes);
    return true;
}

bool PosixPackageFileStager::Cleanup(const ManagedFilesV1& managedFiles,
    std::string* error)
{
    if (managedFiles.baseCodePath.empty()) return true;
    if (unlink(managedFiles.baseCodePath.c_str()) != 0 && errno != ENOENT) {
        if (error != nullptr) *error = std::strerror(errno);
        return false;
    }
    return FsyncDirectory(ParentPath(managedFiles.baseCodePath), error);
}

FilePackageStore::FilePackageStore(std::string storeRoot)
    : impl_(new Impl(std::move(storeRoot)))
{
}

FilePackageStore::~FilePackageStore()
{
    impl_->ReleaseWriterLease();
    delete impl_;
}

bool FilePackageStore::Open(std::string* error)
{
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->OpenLocked(error);
}

bool FilePackageStore::OpenReadOnly(std::string* error)
{
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->OpenReadOnlyLocked(error);
}

bool FilePackageStore::ReadPublishedPackage(uint32_t userId,
    const std::string& packageName, PublishedPackageSnapshotV1* snapshot,
    std::string* error) const
{
    if (snapshot == nullptr) {
        if (error != nullptr) *error = "snapshot is null";
        return false;
    }
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->ReadLocked(error)) return false;
    const std::string packageKey = PackageKey(userId, packageName);
    if (impl_->quarantinedPackages.count(packageKey) != 0) {
        if (error != nullptr) *error = "package generation is quarantined";
        return false;
    }
    const auto iterator = impl_->packages.find(packageKey);
    if (iterator == impl_->packages.end()) {
        if (error != nullptr) *error = "package not found";
        return false;
    }
    *snapshot = iterator->second;
    return true;
}

bool FilePackageStore::ReadReceipt(const std::string& transactionId,
    PackageLifecycleReceiptV1* receipt, std::string* error) const
{
    if (receipt == nullptr) {
        if (error != nullptr) *error = "receipt is null";
        return false;
    }
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->ReadLocked(error)) return false;
    const auto iterator = impl_->journals.find(transactionId);
    if (iterator == impl_->journals.end() || !iterator->second.receipt.has_value()) {
        if (error != nullptr) *error = "receipt not found";
        return false;
    }
    if (iterator->second.receipt->packageName.has_value() &&
        impl_->quarantinedPackages.count(PackageKey(
            iterator->second.userId,
            *iterator->second.receipt->packageName)) != 0) {
        if (error != nullptr) *error = "package generation is quarantined";
        return false;
    }
    *receipt = *iterator->second.receipt;
    return true;
}

bool FilePackageStore::ReadPublicationToken(uint32_t userId,
    const std::string& packageName, PublicationTokenV1* token,
    std::string* error) const
{
    if (token == nullptr) {
        if (error != nullptr) *error = "token is null";
        return false;
    }
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->ReadLocked(error)) return false;
    const std::string packageKey = PackageKey(userId, packageName);
    if (impl_->quarantinedPackages.count(packageKey) != 0) {
        if (error != nullptr) *error = "package generation is quarantined";
        return false;
    }
    const auto iterator = impl_->publicationTokens.find(packageKey);
    if (iterator == impl_->publicationTokens.end()) {
        if (error != nullptr) *error = "publication token not found";
        return false;
    }
    *token = iterator->second;
    return true;
}

bool FilePackageStore::ReadPackageManagementState(uint32_t userId,
    const std::string& packageName, PackageManagementReadV1* state,
    std::string* error) const
{
    if (state == nullptr) {
        if (error != nullptr) *error = "management state is null";
        return false;
    }
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->ReadLocked(error)) return false;
    PackageManagementReadV1 result;
    result.catalogRevision = impl_->recordVersion;
    const std::string packageKey = PackageKey(userId, packageName);
    if (impl_->quarantinedPackages.count(packageKey) != 0) {
        if (error != nullptr) *error = "package generation is quarantined";
        return false;
    }
    result.removing = impl_->removalTombstones.count(packageKey) != 0;
    const auto canonical = impl_->packages.find(packageKey);
    if (canonical != impl_->packages.end()) result.canonical = canonical->second;
    const auto token = impl_->publicationTokens.find(packageKey);
    if (token != impl_->publicationTokens.end()) {
        result.publicationToken = token->second;
    }
    const auto projection = impl_->projections.find(packageKey);
    if (projection != impl_->projections.end()) {
        result.projection = projection->second;
    }
    *state = std::move(result);
    return true;
}

bool FilePackageStore::ReadUpdateReceipt(const std::string& transactionId,
    UpdateReceiptV1* receipt, std::string* error) const
{
    if (receipt == nullptr) {
        if (error != nullptr) *error = "update receipt is null";
        return false;
    }
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->ReadLocked(error)) return false;
    const auto journal = impl_->journals.find(transactionId);
    if (journal == impl_->journals.end() ||
        !journal->second.updateReceipt.has_value()) {
        if (error != nullptr) *error = "update receipt not found";
        return false;
    }
    *receipt = *journal->second.updateReceipt;
    return true;
}

bool FilePackageStore::ReadRetirementPlan(
    const std::string& transactionId,
    GenerationRetirementPlanV1* plan, std::string* error) const
{
    if (plan == nullptr) {
        if (error != nullptr) *error = "retirement plan is null";
        return false;
    }
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->ReadLocked(error)) return false;
    const auto iterator = impl_->retirementPlans.find(transactionId);
    if (iterator == impl_->retirementPlans.end()) {
        if (error != nullptr) *error = "retirement plan not found";
        return false;
    }
    *plan = iterator->second;
    return true;
}

bool FilePackageStore::ReadRemovalTombstone(
    const std::string& transactionId,
    RemovalTombstoneV1* tombstone, std::string* error) const
{
    if (tombstone == nullptr) {
        if (error != nullptr) *error = "removal tombstone is null";
        return false;
    }
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->ReadLocked(error)) return false;
    const auto iterator = impl_->removalPlans.find(transactionId);
    if (iterator == impl_->removalPlans.end()) {
        if (error != nullptr) *error = "removal tombstone not found";
        return false;
    }
    *tombstone = iterator->second;
    return true;
}

bool FilePackageStore::ReadUninstallReceipt(
    const std::string& transactionId,
    UninstallReceiptV1* receipt, std::string* error) const
{
    if (receipt == nullptr) {
        if (error != nullptr) *error = "uninstall receipt is null";
        return false;
    }
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->ReadLocked(error)) return false;
    const auto journal = impl_->journals.find(transactionId);
    if (journal == impl_->journals.end() ||
        !journal->second.uninstallReceipt.has_value()) {
        if (error != nullptr) *error = "uninstall receipt not found";
        return false;
    }
    *receipt = *journal->second.uninstallReceipt;
    return true;
}

bool FilePackageStore::CommitExternalReady(uint32_t userId,
    const std::string& packageName, uint64_t generation,
    const std::string& canonicalDigest, std::string* error)
{
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->OpenLocked(error)) return false;
    const std::string packageKey = PackageKey(userId, packageName);
    const auto package = impl_->packages.find(packageKey);
    const auto token = impl_->publicationTokens.find(packageKey);
    const auto projection = impl_->projections.find(packageKey);
    if (package == impl_->packages.end() ||
        token == impl_->publicationTokens.end() ||
        impl_->quarantinedPackages.count(packageKey) != 0 ||
        impl_->removalTombstones.count(packageKey) != 0 ||
        package->second.packageName != packageName ||
        package->second.userId != userId ||
        package->second.generation != generation ||
        package->second.canonicalDigest != canonicalDigest ||
        token->second.packageName != packageName ||
        token->second.userId != userId ||
        token->second.generation != generation ||
        token->second.canonicalDigest != canonicalDigest) {
        if (error != nullptr) {
            *error = "external-ready identity does not join canonical";
        }
        return false;
    }
    if (token->second.state == PublicationState::EXTERNAL_READY) {
        const bool exactReplay =
            projection != impl_->projections.end() &&
            projection->second.packageName == packageName &&
            projection->second.userId == userId &&
            projection->second.generation == generation &&
            projection->second.canonicalDigest == canonicalDigest &&
            projection->second.state == HostProjectionState::ACTIVE;
        if (!exactReplay && error != nullptr) {
            *error = "external-ready replay does not match projection";
        }
        return exactReplay;
    }
    if (token->second.state != PublicationState::CANONICAL_SELECTED) {
        if (error != nullptr) {
            *error = "canonical generation is not publication eligible";
        }
        return false;
    }
    if (projection != impl_->projections.end() &&
        (projection->second.packageName != packageName ||
            projection->second.userId != userId ||
            projection->second.generation != generation ||
            projection->second.canonicalDigest != canonicalDigest ||
            (projection->second.state != HostProjectionState::NONE &&
                projection->second.state !=
                    HostProjectionState::PREPARED))) {
        if (error != nullptr) {
            *error = "existing projection does not join canonical";
        }
        return false;
    }
    return impl_->AppendEvent(JoinTabs({
        "PROJECTION", std::to_string(userId), HexEncode(packageName),
        std::to_string(generation), HexEncode(canonicalDigest),
        HexEncode(HostProjectionStateName(HostProjectionState::ACTIVE)),
        HexEncode(PublicationStateName(PublicationState::EXTERNAL_READY)),
    }), error);
}

RestartRecoveryReceiptV1 FilePackageStore::RecoverAfterRestart(
    const RestartRecoveryRequestV1& request)
{
    RestartRecoveryReceiptV1 result;
    result.requestId = request.requestId;
    result.transactionId = request.transactionId;
    result.boundary = request.boundary;
    result.terminalState = "REJECTED_TYPED";
    auto rejectIdentity = [&](const std::string& reason) {
        result.verdict = RestartRecoveryVerdict::IDENTITY_MISMATCH;
        result.reason = reason;
        return result;
    };
    if (request.schemaVersion != 1 || request.requestId.empty() ||
        request.transactionId.empty()) {
        return rejectIdentity("invalid schema/request/transaction identity");
    }
    if (request.boundary.beforeBootId.empty() ||
        request.boundary.afterBootId.empty() ||
        request.boundary.beforeServiceId.empty() ||
        request.boundary.afterServiceId.empty() ||
        (request.boundary.beforeBootId == request.boundary.afterBootId &&
            request.boundary.beforeServiceId ==
                request.boundary.afterServiceId)) {
        return rejectIdentity("restart boundary identity did not advance");
    }
    if ((request.expectedRequestDigest.has_value() &&
            !IsLowerHexDigest(*request.expectedRequestDigest)) ||
        (request.expectedArtifactSetDigest.has_value() &&
            !IsLowerHexDigest(*request.expectedArtifactSetDigest)) ||
        (request.expectedCanonicalDigest.has_value() &&
            !IsLowerHexDigest(*request.expectedCanonicalDigest)) ||
        (request.expectedPackageName.has_value() &&
            request.expectedPackageName->empty()) ||
        (request.expectedGeneration.has_value() &&
            *request.expectedGeneration == 0)) {
        return rejectIdentity("expected identity has invalid shape");
    }

    std::lock_guard<std::mutex> lock(impl_->mutex);
    std::string openError;
    if (!impl_->OpenLocked(&openError)) {
        result.verdict = RestartRecoveryVerdict::DATA_INCONSISTENT;
        result.terminalState = "QUARANTINED";
        result.reason = openError.empty() ?
            "durable store replay failed" : openError;
        return result;
    }
    result.catalogRevision = impl_->recordVersion;
    const auto journal = impl_->journals.find(request.transactionId);
    if (journal == impl_->journals.end()) {
        result.verdict = RestartRecoveryVerdict::ABSENT;
        result.terminalState = "ABSENT";
        result.reason = "no durable P0 journal for transaction";
        return result;
    }
    result.journalPresent = true;
    result.requestDigest = journal->second.requestDigest;
    result.packageName = journal->second.packageName;
    result.artifactSetDigest = journal->second.artifactSetDigest.empty() ?
        std::optional<std::string>{} :
        std::optional<std::string>{journal->second.artifactSetDigest};
    if (journal->second.candidateGeneration != 0) {
        result.generation = journal->second.candidateGeneration;
    }
    result.durablePhase = journal->second.phase;

    if ((request.expectedRequestDigest.has_value() &&
            *request.expectedRequestDigest != journal->second.requestDigest) ||
        (request.expectedPackageName.has_value() &&
            request.expectedPackageName != journal->second.packageName) ||
        (request.expectedArtifactSetDigest.has_value() &&
            *request.expectedArtifactSetDigest !=
                journal->second.artifactSetDigest) ||
        (request.expectedGeneration.has_value() &&
            *request.expectedGeneration !=
                journal->second.candidateGeneration) ||
        (request.expectedPhase.has_value() &&
            *request.expectedPhase != journal->second.phase)) {
        return rejectIdentity("journal identity/phase mismatch");
    }

    if (!journal->second.receipt.has_value()) {
        if (journal->second.phase ==
            DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED) {
            result.verdict = RestartRecoveryVerdict::DATA_INCONSISTENT;
            result.terminalState = "QUARANTINED";
            result.reason =
                "published transaction could not close during store replay";
            return result;
        }
        if (journal->second.packageName.has_value()) {
            const std::string packageKey = PackageKey(journal->second.userId,
                *journal->second.packageName);
            if (impl_->packages.count(packageKey) != 0) {
                result.verdict = RestartRecoveryVerdict::DATA_INCONSISTENT;
                result.terminalState = "QUARANTINED";
                result.reason = "pre-P5 journal has canonical package";
                return result;
            }
            const auto token = impl_->publicationTokens.find(packageKey);
            if (token != impl_->publicationTokens.end()) {
                result.publicationState = token->second.state;
                if (journal->second.phase !=
                        DurablePhase::P4_PUBLICATION_PREPARED ||
                    token->second.state != PublicationState::PREPARED ||
                    token->second.generation !=
                        journal->second.candidateGeneration) {
                    result.verdict =
                        RestartRecoveryVerdict::DATA_INCONSISTENT;
                    result.terminalState = "QUARANTINED";
                    result.reason = "pre-P5 token/phase join failed";
                    return result;
                }
            }
        }
        result.verdict = RestartRecoveryVerdict::NON_READY;
        result.terminalState = "OPEN_NON_READY";
        result.reason = std::string("pre-P5 durable phase:") +
            DurablePhaseName(journal->second.phase);
        return result;
    }

    const PackageLifecycleReceiptV1& closed = *journal->second.receipt;
    if (closed.verdict != InstallVerdict::COMMITTED) {
        result.verdict = RestartRecoveryVerdict::ABSENT;
        result.terminalState = closed.terminalState;
        result.reason = std::string("closed non-committed install:") +
            InstallVerdictName(closed.verdict);
        return result;
    }
    if (!closed.packageName.has_value() || !closed.generation.has_value() ||
        !closed.artifactSetDigest.has_value() ||
        !closed.durableRecordDigest.has_value()) {
        result.verdict = RestartRecoveryVerdict::DATA_INCONSISTENT;
        result.terminalState = "QUARANTINED";
        result.reason = "closed receipt is missing canonical identity";
        return result;
    }
    const std::string packageKey =
        PackageKey(journal->second.userId, *closed.packageName);
    const auto package = impl_->packages.find(packageKey);
    std::string validationReason;
    if (package == impl_->packages.end() ||
        impl_->quarantinedPackages.count(packageKey) != 0 ||
        !impl_->ValidatePublishedPackage(
            packageKey, package->second, &validationReason) ||
        package->second.generation != *closed.generation ||
        package->second.artifactSetDigest != *closed.artifactSetDigest ||
        package->second.canonicalDigest != *closed.durableRecordDigest) {
        impl_->quarantinedPackages.insert(packageKey);
        result.verdict = RestartRecoveryVerdict::DATA_INCONSISTENT;
        result.terminalState = "QUARANTINED";
        result.reason = validationReason.empty() ?
            "closed receipt/canonical identity mismatch" : validationReason;
        return result;
    }
    if (request.expectedCanonicalDigest.has_value() &&
        *request.expectedCanonicalDigest != package->second.canonicalDigest) {
        return rejectIdentity("canonical digest mismatch");
    }
    result.packageName = package->second.packageName;
    result.artifactSetDigest = package->second.artifactSetDigest;
    result.generation = package->second.generation;
    result.canonicalDigest = package->second.canonicalDigest;
    result.managedFiles = package->second.managedFiles;
    result.primaryUserState = package->second.primaryUserState;
    result.artifacts = package->second.artifacts;
    result.durablePhase = DurablePhase::P6_RECEIPT_CLOSED;
    const auto projection = impl_->projections.find(packageKey);
    const auto token = impl_->publicationTokens.find(packageKey);
    result.hostProjectionState = projection == impl_->projections.end() ?
        HostProjectionState::NONE : projection->second.state;
    result.publicationState = token == impl_->publicationTokens.end() ?
        PublicationState::NONE : token->second.state;
    result.consumerReady =
        projection != impl_->projections.end() &&
        projection->second.state == HostProjectionState::ACTIVE &&
        token != impl_->publicationTokens.end() &&
        token->second.state == PublicationState::EXTERNAL_READY &&
        projection->second.generation == package->second.generation &&
        projection->second.canonicalDigest == package->second.canonicalDigest;
    result.verdict = RestartRecoveryVerdict::RESTORED_COMMITTED;
    result.terminalState = "CLOSED_COMMITTED";
    result.reason = "same committed generation restored from durable journal";
    result.catalogRevision = impl_->recordVersion;
    return result;
}

#if defined(FN01_ENABLE_REFERENCE_FIXTURES)
bool FilePackageStore::SeedRemovalTombstoneForFixture(uint32_t userId,
    const std::string& packageName, uint64_t generation, std::string* error)
{
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->OpenLocked(error)) return false;
    return impl_->AppendEvent(JoinTabs({
        "TOMBSTONE", std::to_string(userId), HexEncode(packageName),
        std::to_string(generation),
    }), error);
}

bool FilePackageStore::SeedHostProjectionForFixture(uint32_t userId,
    const std::string& packageName, uint64_t generation,
    const std::string& canonicalDigest,
    HostProjectionState projectionState,
    PublicationState tokenState, std::string* error)
{
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->OpenLocked(error)) return false;
    if (packageName.empty() || generation == 0 ||
        !IsLowerHexDigest(canonicalDigest) ||
        (tokenState != PublicationState::PREPARED &&
            tokenState != PublicationState::CANONICAL_SELECTED &&
            tokenState != PublicationState::EXTERNAL_READY)) {
        if (error != nullptr) *error = "invalid projection fixture";
        return false;
    }
    return impl_->AppendEvent(JoinTabs({
        "PROJECTION", std::to_string(userId), HexEncode(packageName),
        std::to_string(generation), HexEncode(canonicalDigest),
        HexEncode(HostProjectionStateName(projectionState)),
        HexEncode(PublicationStateName(tokenState)),
    }), error);
}
#endif

std::string ComputeArtifactSetDigest(const PackageArtifactSetV1& artifactSet)
{
    std::vector<const ArtifactDescriptorV1*> artifacts;
    artifacts.reserve(artifactSet.artifacts.size());
    for (const auto& artifact : artifactSet.artifacts) artifacts.push_back(&artifact);
    std::sort(artifacts.begin(), artifacts.end(),
        [](const ArtifactDescriptorV1* left, const ArtifactDescriptorV1* right) {
            return std::tie(left->role, left->artifactId, left->sha256, left->byteLength) <
                std::tie(right->role, right->artifactId, right->sha256, right->byteLength);
        });
    std::string canonical = "{\"artifacts\":[";
    for (size_t index = 0; index < artifacts.size(); ++index) {
        if (index != 0) canonical += ",";
        const ArtifactDescriptorV1& artifact = *artifacts[index];
        canonical += "{\"artifactId\":" + JsonString(artifact.artifactId) +
            ",\"byteLength\":" + std::to_string(artifact.byteLength) +
            ",\"role\":" + JsonString(ArtifactRoleName(artifact.role)) +
            ",\"sha256\":" + JsonString(artifact.sha256) + "}";
    }
    canonical += "],\"schemaVersion\":" +
        std::to_string(artifactSet.schemaVersion) + "}";
    return Sha256Hex(canonical);
}

std::string ComputeInstallRequestDigest(const InstallRequestV1& request)
{
    std::string canonical = "{\"artifactSetDigest\":" +
        JsonString(request.artifactSet.artifactSetDigest);
    if (request.expectedGeneration.has_value()) {
        canonical += ",\"expectedGeneration\":" +
            std::to_string(*request.expectedGeneration);
    }
    if (request.expectedPackageName.has_value()) {
        canonical += ",\"expectedPackageName\":" +
            JsonString(*request.expectedPackageName);
    }
    canonical += ",\"operation\":\"INSTALL\",\"policyRef\":" +
        JsonString(request.policyRef) + ",\"userId\":" +
        std::to_string(request.userId) + "}";
    return Sha256Hex(canonical);
}

std::string ComputeUpdateRequestDigest(const UpdateRequestV1& request)
{
    std::string canonical = "{\"artifactSetDigest\":" +
        JsonString(request.artifactSet.artifactSetDigest) +
        ",\"continuityDecisionDigest\":" +
        JsonString(request.signingContinuity.decisionDigest) +
        ",\"expectedGeneration\":";
    canonical += request.expectedGeneration.has_value()
        ? std::to_string(*request.expectedGeneration) : "null";
    canonical += ",\"expectedPackageName\":";
    canonical += request.expectedPackageName.has_value()
        ? JsonString(*request.expectedPackageName) : "null";
    canonical += ",\"operation\":\"UPDATE\",\"policyId\":" +
        JsonString(request.policySnapshot.policyId) +
        ",\"policyRef\":" + JsonString(request.policyRef) +
        ",\"policyRulesDigest\":" +
        JsonString(request.policySnapshot.rulesDigest) +
        ",\"policyVersion\":" +
        JsonString(request.policySnapshot.policyVersion) +
        ",\"signingReceiptDigest\":" +
        JsonString(request.signingContinuity.signingReceiptDigest) +
        ",\"userId\":" + std::to_string(request.userId) + "}";
    return Sha256Hex(canonical);
}

std::string ComputeUninstallRequestDigest(
    const UninstallRequestV1& request)
{
    std::string canonical = "{\"callerScopeDigest\":" +
        JsonString(request.admission.callerScopeDigest) +
        ",\"expectedGeneration\":";
    canonical += request.expectedGeneration.has_value()
        ? std::to_string(*request.expectedGeneration) : "null";
    canonical += ",\"expectedPackageName\":";
    canonical += request.expectedPackageName.has_value()
        ? JsonString(*request.expectedPackageName) : "null";
    canonical += ",\"operation\":\"UNINSTALL\",\"packageSelector\":" +
        JsonString(request.packageSelector) +
        ",\"policyRef\":" + JsonString(request.policyRef) +
        ",\"userId\":" + std::to_string(request.userId) + "}";
    return Sha256Hex(canonical);
}

std::string ComputePackageSigningFactsDigest(const SigningFactsV1& signing)
{
    std::vector<std::string> signers =
        signing.signerCertificateDigests;
    std::sort(signers.begin(), signers.end());
    std::string canonical = "PriorSigningFactsV1\nS:";
    for (size_t index = 0; index < signers.size(); ++index) {
        if (index != 0) canonical += ",";
        canonical += signers[index];
    }
    for (const auto& lineage : signing.lineage) {
        canonical += "\nL:" + lineage.certificateSha256 + ":" +
            std::to_string(lineage.capabilities);
    }
    return Sha256Hex(canonical);
}

PackageTransactionCoordinator::PackageTransactionCoordinator(
    FilePackageStore* store, PackageFileStager* stager,
    FaultInjector* faultInjector)
    : store_(store), stager_(stager), faultInjector_(faultInjector)
{
}

PackageLifecycleReceiptV1 PackageTransactionCoordinator::Install(
    const InstallRequestV1& request)
{
    if (store_ == nullptr || stager_ == nullptr || faultInjector_ == nullptr) {
        return MakeReceipt(request, InstallVerdict::INVALID_ENVELOPE, "REJECTED_TYPED");
    }
    std::lock_guard<std::mutex> lock(store_->impl_->mutex);
    std::string storeError;
    if (!store_->impl_->OpenLocked(&storeError)) {
        return MakeReceipt(request, InstallVerdict::DATA_INCONSISTENT, "FAIL_CLOSED");
    }

    auto existing = store_->impl_->journals.find(request.admission.transactionId);
    if (existing != store_->impl_->journals.end()) {
        if (existing->second.requestDigest != request.admission.requestDigest) {
            return MakeReceipt(request, InstallVerdict::IDEMPOTENCY_CONFLICT,
                "REJECTED_TYPED", existing->second.packageName,
                existing->second.candidateGeneration == 0
                    ? std::optional<uint64_t>{}
                    : std::optional<uint64_t>{existing->second.candidateGeneration});
        }
        if (existing->second.receipt.has_value()) {
            return *existing->second.receipt;
        }
        if (existing->second.phase ==
            DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED) {
            const std::string packageName = existing->second.packageName.value_or("");
            const std::string packageKey =
                PackageKey(existing->second.userId, packageName);
            const auto package = store_->impl_->packages.find(
                packageKey);
            std::string validationReason;
            if (package == store_->impl_->packages.end() ||
                store_->impl_->quarantinedPackages.count(packageKey) != 0 ||
                !store_->impl_->ValidatePublishedPackage(
                    packageKey, package->second, &validationReason)) {
                store_->impl_->quarantinedPackages.insert(packageKey);
                return MakeReceipt(request, InstallVerdict::DATA_INCONSISTENT,
                    "FAIL_CLOSED", existing->second.packageName);
            }
            PackageLifecycleReceiptV1 receipt = MakeReceipt(request,
                InstallVerdict::COMMITTED, "CLOSED_COMMITTED",
                package->second.packageName, package->second.generation,
                package->second.canonicalDigest);
            if (!store_->impl_->AppendEvent(EncodeReceiptEvent("P6", receipt),
                &storeError)) {
                return MakeReceipt(request, InstallVerdict::INTERNAL_IO_ERROR,
                    "RECOVERING_FORWARD", package->second.packageName,
                    package->second.generation, package->second.canonicalDigest);
            }
            return receipt;
        }
    }

    const bool hasStableTransaction = !request.admission.transactionId.empty() &&
        !request.admission.requestDigest.empty();
    const bool canPersistP0 = hasStableTransaction &&
        !request.retryIdentity.empty() &&
        !request.admission.jobId.empty() &&
        !request.admission.memberId.empty() &&
        request.admission.jobRecordVersion != 0 &&
        !request.admission.callerScopeDigest.empty() &&
        !request.admission.policySnapshotId.empty() &&
        request.admission.operation == "INSTALL";
    const std::string actualRequestDigest = ComputeInstallRequestDigest(request);
    auto persistRejection = [&](InstallVerdict verdict,
                                const std::optional<std::string>& packageName)
        -> PackageLifecycleReceiptV1 {
        PackageLifecycleReceiptV1 receipt =
            MakeReceipt(request, verdict, "REJECTED_TYPED", packageName);
        if (!canPersistP0) return receipt;
        if (store_->impl_->journals.find(request.admission.transactionId) ==
            store_->impl_->journals.end()) {
            const std::string p0 = JoinTabs({
                "P0",
                HexEncode(request.admission.transactionId),
                HexEncode(request.admission.requestDigest),
                HexEncode(request.artifactSet.artifactSetDigest),
                HexEncode(packageName.value_or("")),
                std::to_string(request.userId),
                "0",
                HexEncode(request.retryIdentity),
                HexEncode(request.admission.jobId),
                HexEncode(request.admission.memberId),
                std::to_string(request.admission.memberIndex),
                std::to_string(request.admission.jobRecordVersion),
                HexEncode(request.admission.callerScopeDigest),
                HexEncode(request.admission.policySnapshotId),
                HexEncode(request.admission.operation),
            });
            if (!store_->impl_->AppendEvent(p0, &storeError)) {
                receipt.verdict = InstallVerdict::INTERNAL_IO_ERROR;
                receipt.terminalState = "FAIL_CLOSED";
                return receipt;
            }
        }
        if (!store_->impl_->AppendEvent(EncodeReceiptEvent("REJECT", receipt),
            &storeError)) {
            receipt.verdict = InstallVerdict::INTERNAL_IO_ERROR;
            receipt.terminalState = "FAIL_CLOSED";
        }
        return receipt;
    };

    if (request.admission.schemaVersion != 1 ||
        request.admission.operation != "INSTALL" ||
        request.admission.jobId.empty() || request.admission.memberId.empty() ||
        request.admission.jobRecordVersion == 0 ||
        request.admission.callerScopeDigest.empty() ||
        request.retryIdentity.empty() || request.policyRef.empty() ||
        request.admission.policySnapshotId.empty() ||
        !hasStableTransaction ||
        request.admission.requestDigest != actualRequestDigest) {
        return persistRejection(InstallVerdict::INVALID_ENVELOPE, std::nullopt);
    }
    if (request.userId != kPrimaryUserId) {
        return persistRejection(InstallVerdict::NOT_SUPPORTED, std::nullopt);
    }
    if (request.artifactSet.schemaVersion != 1 ||
        request.artifactSet.artifacts.size() != 1 ||
        request.artifactSet.artifacts.front().role != ArtifactRole::BASE) {
        return persistRejection(
            InstallVerdict::NOT_SUPPORTED_ARTIFACT_PROFILE, std::nullopt);
    }
    const ArtifactDescriptorV1& artifact = request.artifactSet.artifacts.front();
    if (artifact.artifactId.empty() ||
        artifact.byteLength != artifact.bytes.size() ||
        artifact.sha256 != Sha256Hex(artifact.bytes) ||
        !IsLowerHexDigest(artifact.sha256) ||
        request.artifactSet.artifactSetDigest !=
            ComputeArtifactSetDigest(request.artifactSet)) {
        return persistRejection(
            InstallVerdict::ARTIFACT_DIGEST_MISMATCH, std::nullopt);
    }
    if (request.manifest.packageName.empty() ||
        request.manifest.artifactSetDigest != request.artifactSet.artifactSetDigest ||
        request.manifest.parserVersion.empty()) {
        return persistRejection(InstallVerdict::IDENTITY_MISMATCH, std::nullopt);
    }
    const std::optional<std::string> packageName = request.manifest.packageName;
    if (request.expectedPackageName.has_value() &&
        *request.expectedPackageName != request.manifest.packageName) {
        return persistRejection(InstallVerdict::IDENTITY_MISMATCH, packageName);
    }
    if (request.expectedGeneration.has_value() &&
        *request.expectedGeneration != 0) {
        return persistRejection(InstallVerdict::GENERATION_MISMATCH, packageName);
    }
    if (!request.signing.verified ||
        request.signing.artifactSetDigest != request.artifactSet.artifactSetDigest ||
        request.signing.verifierVersion.empty() ||
        request.signing.schemeVersions.empty() ||
        request.signing.signerCertificateDigests.empty() ||
        !std::all_of(request.signing.signerCertificateDigests.begin(),
            request.signing.signerCertificateDigests.end(), IsLowerHexDigest)) {
        return persistRejection(InstallVerdict::SIGNING_REJECTED, packageName);
    }
    if (request.signing.policyProfile != request.policyRef ||
        request.admission.policySnapshotId != request.policyRef) {
        return persistRejection(InstallVerdict::POLICY_REJECTED, packageName);
    }

    const std::string packageKey = PackageKey(request.userId,
        request.manifest.packageName);
    if (store_->impl_->removalTombstones.count(packageKey) != 0) {
        return persistRejection(InstallVerdict::PACKAGE_REMOVING, packageName);
    }
    if (store_->impl_->quarantinedPackages.count(packageKey) != 0) {
        return MakeReceipt(request, InstallVerdict::DATA_INCONSISTENT,
            "FAIL_CLOSED", packageName);
    }
    if (store_->impl_->packages.count(packageKey) != 0) {
        return persistRejection(InstallVerdict::PACKAGE_ALREADY_EXISTS, packageName);
    }

    const uint64_t generation = store_->impl_->lastGenerations[packageKey] + 1;
    if (store_->impl_->journals.find(request.admission.transactionId) ==
        store_->impl_->journals.end()) {
        const std::string p0 = JoinTabs({
            "P0",
            HexEncode(request.admission.transactionId),
            HexEncode(request.admission.requestDigest),
            HexEncode(request.artifactSet.artifactSetDigest),
            HexEncode(request.manifest.packageName),
            std::to_string(request.userId),
            std::to_string(generation),
            HexEncode(request.retryIdentity),
            HexEncode(request.admission.jobId),
            HexEncode(request.admission.memberId),
            std::to_string(request.admission.memberIndex),
            std::to_string(request.admission.jobRecordVersion),
            HexEncode(request.admission.callerScopeDigest),
            HexEncode(request.admission.policySnapshotId),
            HexEncode(request.admission.operation),
        });
        if (!store_->impl_->AppendEvent(p0, &storeError)) {
            return MakeReceipt(request, InstallVerdict::INTERNAL_IO_ERROR,
                "FAIL_CLOSED", packageName);
        }
    }
    if (faultInjector_->InterruptAfter(DurablePhase::P0_INPUT_FROZEN)) {
        return MakeReceipt(request,
            InstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE, "OPEN", packageName);
    }

    auto appendPhase = [&](DurablePhase phase) {
        return store_->impl_->AppendEvent(JoinTabs({
            "PHASE",
            HexEncode(request.admission.transactionId),
            HexEncode(DurablePhaseName(phase)),
            std::to_string(generation),
        }), &storeError);
    };
    auto rollback = [&](const ManagedFilesV1& managedFiles) {
        std::string cleanupError;
        if (!managedFiles.baseCodePath.empty()) {
            (void)stager_->Cleanup(managedFiles, &cleanupError);
        }
        PackageLifecycleReceiptV1 receipt = MakeReceipt(request,
            InstallVerdict::INTERNAL_IO_ERROR, "CLOSED_ROLLED_BACK",
            packageName);
        if (!store_->impl_->AppendEvent(EncodeReceiptEvent("ROLLBACK", receipt),
            &storeError)) {
            receipt.terminalState = "FAIL_CLOSED";
        }
        return receipt;
    };

    if (!appendPhase(DurablePhase::P1_PLAN_DURABLE)) {
        return MakeReceipt(request, InstallVerdict::INTERNAL_IO_ERROR,
            "FAIL_CLOSED", packageName);
    }
    if (faultInjector_->InterruptAfter(DurablePhase::P1_PLAN_DURABLE)) {
        if (faultInjector_->SimulatesProcessCrash()) {
            return MakeReceipt(request,
                InstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
                "OPEN_NON_READY", packageName, generation);
        }
        return rollback({});
    }

    ManagedFilesV1 managedFiles;
    std::string stagingError;
    if (!stager_->Stage(request.manifest.packageName, request.userId,
        generation, artifact, &managedFiles, &stagingError)) {
        return rollback(managedFiles);
    }
    if (managedFiles.baseCodeDigest != artifact.sha256 ||
        managedFiles.baseCodePath.empty()) {
        return rollback(managedFiles);
    }
    if (!appendPhase(DurablePhase::P2_FILES_PREPARED)) {
        return rollback(managedFiles);
    }
    if (faultInjector_->InterruptAfter(DurablePhase::P2_FILES_PREPARED)) {
        if (faultInjector_->SimulatesProcessCrash()) {
            return MakeReceipt(request,
                InstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
                "OPEN_NON_READY", packageName, generation);
        }
        return rollback(managedFiles);
    }

    const std::string canonicalDigest =
        Sha256Hex(CanonicalGenerationJson(request, generation, managedFiles));
    if (!appendPhase(DurablePhase::P3_CANONICAL_PREPARED)) {
        return rollback(managedFiles);
    }
    if (faultInjector_->InterruptAfter(DurablePhase::P3_CANONICAL_PREPARED)) {
        if (faultInjector_->SimulatesProcessCrash()) {
            return MakeReceipt(request,
                InstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
                "OPEN_NON_READY", packageName, generation);
        }
        return rollback(managedFiles);
    }
    const std::string p4 = JoinTabs({
        "P4",
        HexEncode(request.admission.transactionId),
        HexEncode(request.manifest.packageName),
        std::to_string(request.userId),
        std::to_string(generation),
        HexEncode(canonicalDigest),
        HexEncode(PublicationStateName(PublicationState::PREPARED)),
    });
    if (!store_->impl_->AppendEvent(p4, &storeError)) {
        return rollback(managedFiles);
    }
    if (faultInjector_->InterruptAfter(DurablePhase::P4_PUBLICATION_PREPARED)) {
        if (faultInjector_->SimulatesProcessCrash()) {
            return MakeReceipt(request,
                InstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
                "OPEN_NON_READY", packageName, generation, canonicalDigest);
        }
        return rollback(managedFiles);
    }

    const std::string p5 = JoinTabs({
        "P5V5",
        HexEncode(request.admission.transactionId),
        HexEncode(request.manifest.packageName),
        std::to_string(request.userId),
        std::to_string(generation),
        HexEncode(request.artifactSet.artifactSetDigest),
        HexEncode(canonicalDigest),
        HexEncode(managedFiles.baseCodePath),
        HexEncode(managedFiles.baseCodeDigest),
        HexEncode(PublicationStateName(PublicationState::CANONICAL_SELECTED)),
        std::to_string(store_->impl_->recordVersion + 1),
        HexEncode(request.manifest.artifactSetDigest),
        HexEncode(request.manifest.parserVersion),
        std::to_string(request.manifest.versionCode),
        HexEncode(request.manifest.versionName),
        std::to_string(request.manifest.minSdk),
        std::to_string(request.manifest.targetSdk),
        HexEncode(request.manifest.applicationClassName),
        HexEncode(request.manifest.applicationLabel),
        EncodeComponents(request.manifest.components),
        EncodeStrings(request.manifest.requestedPermissions),
        EncodeStrings(request.manifest.declaredPermissions),
        EncodeProvenance(request.manifest.provenance),
        HexEncode(request.signing.artifactSetDigest),
        HexEncode(request.signing.verifierVersion),
        HexEncode(request.signing.policyProfile),
        request.signing.verified ? "1" : "0",
        EncodeUnsigneds(request.signing.schemeVersions),
        EncodeStrings(request.signing.signerCertificateDigests),
        HexEncode(request.signing.lineageDigest.value_or("")),
        EncodeStrings(request.signing.signerCertificateDerHex),
        EncodeSigningLineage(request.signing.lineage),
        HexEncode(request.signing.sourceReceiptDigest.value_or("")),
        "1",
        "1",
        "0",
        "0",
        HexEncode(artifact.artifactId),
        std::to_string(artifact.byteLength),
        HexEncode(artifact.sha256),
    });
    if (!store_->impl_->AppendEvent(p5, &storeError)) {
        return rollback(managedFiles);
    }
    if (faultInjector_->InterruptAfter(
        DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED)) {
        return MakeReceipt(request,
            InstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
            "RECOVERING_FORWARD", packageName, generation, canonicalDigest);
    }

    PackageLifecycleReceiptV1 receipt = MakeReceipt(request,
        InstallVerdict::COMMITTED, "CLOSED_COMMITTED",
        packageName, generation, canonicalDigest);
    if (!store_->impl_->AppendEvent(EncodeReceiptEvent("P6", receipt),
        &storeError)) {
        receipt.verdict = InstallVerdict::INTERNAL_IO_ERROR;
        receipt.terminalState = "RECOVERING_FORWARD";
        return receipt;
    }
    return receipt;
}

UpdateReceiptV1 PackageTransactionCoordinator::FinishUpdateRetirement(
    const UpdateRequestV1& request)
{
    std::string storeError;
    const auto journal = store_->impl_->journals.find(
        request.admission.transactionId);
    auto plan = store_->impl_->retirementPlans.find(
        request.admission.transactionId);
    if (journal == store_->impl_->journals.end() ||
        journal->second.operation != "UPDATE" ||
        plan == store_->impl_->retirementPlans.end() ||
        (plan->second.state != RetirementPlanState::ACTIVE &&
            plan->second.state != RetirementPlanState::CLOSED)) {
        return MakeUpdateReceipt(request, UpdateVerdict::DATA_INCONSISTENT,
            "FAIL_CLOSED", request.manifest.packageName);
    }
    const std::string packageKey = PackageKey(
        plan->second.userId, plan->second.packageName);
    const auto package = store_->impl_->packages.find(packageKey);
    if (package == store_->impl_->packages.end() ||
        package->second.generation != plan->second.newGeneration ||
        package->second.canonicalDigest !=
            journal->second.candidateCanonicalDigest.value_or("")) {
        return MakeUpdateReceipt(request, UpdateVerdict::DATA_INCONSISTENT,
            "FAIL_CLOSED", plan->second.packageName,
            plan->second.oldGeneration, plan->second.newGeneration,
            journal->second.candidateCanonicalDigest,
            plan->second.planDigest);
    }

    auto appendProjectionState = [&](HostProjectionState state) {
        return store_->impl_->AppendEvent(JoinTabs({
            "RETIRE_PROJECTION",
            HexEncode(request.admission.transactionId),
            HexEncode(HostProjectionStateName(state)),
            std::to_string(store_->impl_->recordVersion),
        }), &storeError);
    };
    if (plan->second.state == RetirementPlanState::ACTIVE &&
        plan->second.oldProjectionState == HostProjectionState::STALE) {
        if (!appendProjectionState(HostProjectionState::REMOVING)) {
            return MakeUpdateReceipt(request,
                UpdateVerdict::INTERNAL_IO_ERROR, "RECOVERING_FORWARD",
                plan->second.packageName, plan->second.oldGeneration,
                plan->second.newGeneration, package->second.canonicalDigest,
                plan->second.planDigest);
        }
    }
    if (plan->second.state == RetirementPlanState::ACTIVE &&
        plan->second.oldProjectionState ==
            HostProjectionState::REMOVING) {
        if (!appendProjectionState(HostProjectionState::NONE)) {
            return MakeUpdateReceipt(request,
                UpdateVerdict::INTERNAL_IO_ERROR, "RECOVERING_FORWARD",
                plan->second.packageName, plan->second.oldGeneration,
                plan->second.newGeneration, package->second.canonicalDigest,
                plan->second.planDigest);
        }
    }

    auto closeObligation = [&](const std::string& kind,
                               const std::string& closeResult) {
        return store_->impl_->AppendEvent(JoinTabs({
            "RETIRE_OBLIGATION",
            HexEncode(request.admission.transactionId),
            HexEncode(kind),
            HexEncode(closeResult),
            std::to_string(store_->impl_->recordVersion),
        }), &storeError);
    };
    if (plan->second.state == RetirementPlanState::ACTIVE) {
        for (auto& obligation : plan->second.obligations) {
            if (obligation.state == RetirementObligationState::CLOSED) {
                continue;
            }
            if (obligation.kind == "CODE") {
                std::string cleanupError;
                const ManagedFilesV1 oldFiles = {
                    plan->second.oldManagedCodePath,
                    plan->second.oldManagedCodeDigest,
                };
                if (!stager_->Cleanup(oldFiles, &cleanupError) ||
                    access(oldFiles.baseCodePath.c_str(), F_OK) == 0 ||
                    errno != ENOENT) {
                    return MakeUpdateReceipt(request,
                        UpdateVerdict::INTERNAL_IO_ERROR,
                        "RECOVERING_FORWARD", plan->second.packageName,
                        plan->second.oldGeneration,
                        plan->second.newGeneration,
                        package->second.canonicalDigest,
                        plan->second.planDigest);
                }
                if (!closeObligation(
                        obligation.kind, "REMOVED_READBACK_ABSENT")) {
                    return MakeUpdateReceipt(request,
                        UpdateVerdict::INTERNAL_IO_ERROR,
                        "RECOVERING_FORWARD", plan->second.packageName,
                        plan->second.oldGeneration,
                        plan->second.newGeneration,
                        package->second.canonicalDigest,
                        plan->second.planDigest);
                }
            } else if (obligation.kind == "NATIVE" ||
                       obligation.kind == "RESOURCE") {
                if (!closeObligation(obligation.kind,
                        "ABSENT_CONFIRMED_NO_MANAGED_LOCATOR")) {
                    return MakeUpdateReceipt(request,
                        UpdateVerdict::INTERNAL_IO_ERROR,
                        "RECOVERING_FORWARD", plan->second.packageName,
                        plan->second.oldGeneration,
                        plan->second.newGeneration,
                        package->second.canonicalDigest,
                        plan->second.planDigest);
                }
            } else {
                return MakeUpdateReceipt(request,
                    UpdateVerdict::DATA_INCONSISTENT, "FAIL_CLOSED",
                    plan->second.packageName, plan->second.oldGeneration,
                    plan->second.newGeneration,
                    package->second.canonicalDigest,
                    plan->second.planDigest);
            }
        }
        plan = store_->impl_->retirementPlans.find(
            request.admission.transactionId);
        if (!store_->impl_->AppendEvent(JoinTabs({
                "RETIRE_CLOSED",
                HexEncode(request.admission.transactionId),
                std::to_string(store_->impl_->recordVersion),
            }), &storeError)) {
            return MakeUpdateReceipt(request,
                UpdateVerdict::INTERNAL_IO_ERROR, "RECOVERING_FORWARD",
                plan->second.packageName, plan->second.oldGeneration,
                plan->second.newGeneration, package->second.canonicalDigest,
                plan->second.planDigest);
        }
    }

    plan = store_->impl_->retirementPlans.find(
        request.admission.transactionId);
    UpdateReceiptV1 receipt = MakeUpdateReceipt(request,
        UpdateVerdict::UPDATED, "CLOSED_COMMITTED",
        plan->second.packageName, plan->second.oldGeneration,
        plan->second.newGeneration, package->second.canonicalDigest,
        plan->second.planDigest);
    if (!store_->impl_->AppendEvent(
            EncodeUpdateReceiptEvent("UPDATE_P6", receipt),
            &storeError)) {
        receipt.verdict = UpdateVerdict::INTERNAL_IO_ERROR;
        receipt.terminalState = "RECOVERING_FORWARD";
    }
    return receipt;
}

UpdateReceiptV1 PackageTransactionCoordinator::Update(
    const UpdateRequestV1& request)
{
    if (store_ == nullptr || stager_ == nullptr ||
        faultInjector_ == nullptr) {
        return MakeUpdateReceipt(request, UpdateVerdict::INVALID_ENVELOPE,
            "REJECTED_TYPED");
    }
    std::lock_guard<std::mutex> lock(store_->impl_->mutex);
    std::string storeError;
    if (!store_->impl_->OpenLocked(&storeError)) {
        return MakeUpdateReceipt(request, UpdateVerdict::DATA_INCONSISTENT,
            "FAIL_CLOSED");
    }

    auto existing = store_->impl_->journals.find(
        request.admission.transactionId);
    if (existing != store_->impl_->journals.end()) {
        if (existing->second.operation != "UPDATE" ||
            existing->second.requestDigest !=
                request.admission.requestDigest) {
            return MakeUpdateReceipt(request,
                UpdateVerdict::IDEMPOTENCY_CONFLICT, "REJECTED_TYPED",
                existing->second.packageName, request.expectedGeneration,
                existing->second.candidateGeneration == 0
                    ? std::optional<uint64_t>{}
                    : std::optional<uint64_t>{
                        existing->second.candidateGeneration});
        }
        if (existing->second.updateReceipt.has_value()) {
            return *existing->second.updateReceipt;
        }
        if (existing->second.phase ==
                DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED ||
            (store_->impl_->retirementPlans.count(
                 request.admission.transactionId) != 0 &&
             store_->impl_->retirementPlans.at(
                 request.admission.transactionId).state !=
                 RetirementPlanState::OPEN)) {
            return FinishUpdateRetirement(request);
        }

        if (!existing->second.candidateManagedFiles.baseCodePath.empty()) {
            std::string cleanupError;
            if (!stager_->Cleanup(
                    existing->second.candidateManagedFiles,
                    &cleanupError)) {
                return MakeUpdateReceipt(request,
                    UpdateVerdict::INTERNAL_IO_ERROR, "FAIL_CLOSED",
                    existing->second.packageName,
                    request.expectedGeneration,
                    existing->second.candidateGeneration);
            }
        }
        UpdateReceiptV1 rolledBack = MakeUpdateReceipt(request,
            UpdateVerdict::INTERNAL_IO_ERROR, "CLOSED_ROLLED_BACK",
            existing->second.packageName, request.expectedGeneration,
            existing->second.candidateGeneration == 0
                ? std::optional<uint64_t>{}
                : std::optional<uint64_t>{
                    existing->second.candidateGeneration},
            std::nullopt,
            store_->impl_->retirementPlans.count(
                request.admission.transactionId) == 0
                ? std::optional<std::string>{}
                : std::optional<std::string>{
                    store_->impl_->retirementPlans.at(
                        request.admission.transactionId).planDigest});
        if (!store_->impl_->AppendEvent(
                EncodeUpdateReceiptEvent("UPDATE_ROLLBACK", rolledBack),
                &storeError)) {
            rolledBack.verdict = UpdateVerdict::DATA_INCONSISTENT;
            rolledBack.terminalState = "FAIL_CLOSED";
        }
        return rolledBack;
    }

    const bool hasStableTransaction =
        !request.admission.transactionId.empty() &&
        !request.admission.requestDigest.empty();
    const bool canPersistP0 = hasStableTransaction &&
        !request.retryIdentity.empty() &&
        !request.admission.jobId.empty() &&
        !request.admission.memberId.empty() &&
        request.admission.jobRecordVersion != 0 &&
        !request.admission.callerScopeDigest.empty() &&
        !request.admission.policySnapshotId.empty() &&
        request.admission.operation == "UPDATE";
    auto appendP0 = [&](const std::optional<std::string>& packageName,
                        uint64_t generation) {
        return store_->impl_->AppendEvent(JoinTabs({
            "P0",
            HexEncode(request.admission.transactionId),
            HexEncode(request.admission.requestDigest),
            HexEncode(request.artifactSet.artifactSetDigest),
            HexEncode(packageName.value_or("")),
            std::to_string(request.userId),
            std::to_string(generation),
            HexEncode(request.retryIdentity),
            HexEncode(request.admission.jobId),
            HexEncode(request.admission.memberId),
            std::to_string(request.admission.memberIndex),
            std::to_string(request.admission.jobRecordVersion),
            HexEncode(request.admission.callerScopeDigest),
            HexEncode(request.admission.policySnapshotId),
            HexEncode(request.admission.operation),
        }), &storeError);
    };
    auto persistRejection = [&](UpdateVerdict verdict,
                                const std::optional<std::string>& packageName,
                                const std::optional<uint64_t>& oldGeneration)
        -> UpdateReceiptV1 {
        UpdateReceiptV1 receipt = MakeUpdateReceipt(request, verdict,
            "REJECTED_TYPED", packageName, oldGeneration);
        if (!canPersistP0) return receipt;
        if (!appendP0(packageName, 0) ||
            !store_->impl_->AppendEvent(
                EncodeUpdateReceiptEvent("UPDATE_REJECT", receipt),
                &storeError)) {
            receipt.verdict = UpdateVerdict::INTERNAL_IO_ERROR;
            receipt.terminalState = "FAIL_CLOSED";
        }
        return receipt;
    };

    const std::string actualRequestDigest =
        ComputeUpdateRequestDigest(request);
    if (request.admission.schemaVersion != 1 ||
        request.admission.operation != "UPDATE" ||
        request.admission.jobId.empty() ||
        request.admission.memberId.empty() ||
        request.admission.jobRecordVersion == 0 ||
        request.admission.callerScopeDigest.empty() ||
        request.retryIdentity.empty() || request.policyRef.empty() ||
        request.admission.policySnapshotId.empty() ||
        !hasStableTransaction ||
        request.admission.requestDigest != actualRequestDigest) {
        return persistRejection(UpdateVerdict::INVALID_ENVELOPE,
            std::nullopt, std::nullopt);
    }
    if (request.userId != kPrimaryUserId) {
        return persistRejection(UpdateVerdict::NOT_SUPPORTED,
            std::nullopt, std::nullopt);
    }
    if (request.artifactSet.schemaVersion != 1 ||
        request.artifactSet.artifacts.size() != 1 ||
        request.artifactSet.artifacts.front().role !=
            ArtifactRole::BASE) {
        return persistRejection(
            UpdateVerdict::NOT_SUPPORTED_ARTIFACT_PROFILE,
            std::nullopt, std::nullopt);
    }
    const ArtifactDescriptorV1& artifact =
        request.artifactSet.artifacts.front();
    if (artifact.artifactId.empty() ||
        artifact.byteLength != artifact.bytes.size() ||
        artifact.sha256 != Sha256Hex(artifact.bytes) ||
        !IsLowerHexDigest(artifact.sha256) ||
        request.artifactSet.artifactSetDigest !=
            ComputeArtifactSetDigest(request.artifactSet)) {
        return persistRejection(
            UpdateVerdict::ARTIFACT_DIGEST_MISMATCH,
            std::nullopt, std::nullopt);
    }
    if (request.manifest.packageName.empty() ||
        request.manifest.artifactSetDigest !=
            request.artifactSet.artifactSetDigest ||
        request.manifest.parserVersion.empty() ||
        !request.expectedPackageName.has_value() ||
        *request.expectedPackageName !=
            request.manifest.packageName) {
        return persistRejection(UpdateVerdict::IDENTITY_MISMATCH,
            request.manifest.packageName.empty()
                ? std::optional<std::string>{}
                : std::optional<std::string>{
                    request.manifest.packageName},
            std::nullopt);
    }
    const std::string packageKey = PackageKey(
        request.userId, request.manifest.packageName);
    if (store_->impl_->removalTombstones.count(packageKey) != 0) {
        return persistRejection(UpdateVerdict::PACKAGE_REMOVING,
            request.manifest.packageName, std::nullopt);
    }
    if (store_->impl_->quarantinedPackages.count(packageKey) != 0) {
        return MakeUpdateReceipt(request,
            UpdateVerdict::DATA_INCONSISTENT, "FAIL_CLOSED",
            request.manifest.packageName);
    }
    const auto oldPackage = store_->impl_->packages.find(packageKey);
    if (oldPackage == store_->impl_->packages.end()) {
        return persistRejection(UpdateVerdict::PACKAGE_NOT_FOUND,
            request.manifest.packageName, std::nullopt);
    }
    const uint64_t oldGeneration = oldPackage->second.generation;
    if (!request.expectedGeneration.has_value() ||
        *request.expectedGeneration != oldGeneration) {
        return persistRejection(UpdateVerdict::GENERATION_MISMATCH,
            request.manifest.packageName, oldGeneration);
    }
    if (!oldPackage->second.signingFacts.has_value() ||
        !request.signing.verified ||
        request.signing.artifactSetDigest !=
            request.artifactSet.artifactSetDigest ||
        request.signing.verifierVersion.empty() ||
        request.signing.schemeVersions.empty() ||
        request.signing.signerCertificateDigests.empty() ||
        !std::all_of(
            request.signing.signerCertificateDigests.begin(),
            request.signing.signerCertificateDigests.end(),
            IsLowerHexDigest) ||
        !std::all_of(request.signing.lineage.begin(),
            request.signing.lineage.end(),
            [](const PackageSigningLineageFactV1& item) {
                return IsLowerHexDigest(item.certificateSha256);
            }) ||
        !request.signing.sourceReceiptDigest.has_value() ||
        request.signingContinuity.schemaVersion != 1 ||
        !request.signingContinuity.allowed ||
        request.signingContinuity.capabilityPath.empty() ||
        !IsLowerHexDigest(
            request.signingContinuity.signingReceiptDigest) ||
        !IsLowerHexDigest(
            request.signingContinuity.decisionDigest) ||
        *request.signing.sourceReceiptDigest !=
            request.signingContinuity.signingReceiptDigest ||
        request.signingContinuity.priorSigningFactsDigest !=
            ComputePackageSigningFactsDigest(
                *oldPackage->second.signingFacts) ||
        request.signingContinuity.decisionDigest != Sha256Hex(
            "SigningContinuityDecisionV1\n" +
            request.signingContinuity.signingReceiptDigest + "\n" +
            request.signingContinuity.priorSigningFactsDigest +
            "\nALLOWED\n" +
            request.signingContinuity.capabilityPath)) {
        return persistRejection(UpdateVerdict::SIGNING_REJECTED,
            request.manifest.packageName, oldGeneration);
    }
    if (request.policySnapshot.schemaVersion != 1 ||
        request.policySnapshot.policyId != request.policyRef ||
        request.admission.policySnapshotId != request.policyRef ||
        request.signing.policyProfile != request.policyRef ||
        request.policySnapshot.policyVersion.empty() ||
        request.policySnapshot.ruleId.empty() ||
        !IsLowerHexDigest(request.policySnapshot.rulesDigest) ||
        !request.policySnapshot.permitsUpdate) {
        return persistRejection(UpdateVerdict::POLICY_REJECTED,
            request.manifest.packageName, oldGeneration);
    }

    const uint64_t generation = oldGeneration + 1;
    if (!appendP0(request.manifest.packageName, generation)) {
        return MakeUpdateReceipt(request,
            UpdateVerdict::INTERNAL_IO_ERROR, "FAIL_CLOSED",
            request.manifest.packageName, oldGeneration, generation);
    }
    if (faultInjector_->InterruptAfter(
            DurablePhase::P0_INPUT_FROZEN)) {
        return MakeUpdateReceipt(request,
            UpdateVerdict::INTERRUPTED_AFTER_DURABLE_WRITE, "OPEN",
            request.manifest.packageName, oldGeneration, generation);
    }

    GenerationRetirementPlanV1 plan;
    plan.transactionId = request.admission.transactionId;
    plan.journalRef = "events.v1.log#" +
        request.admission.transactionId;
    plan.packageName = request.manifest.packageName;
    plan.userId = request.userId;
    plan.oldGeneration = oldGeneration;
    plan.newGeneration = generation;
    plan.oldCanonicalDigest = oldPackage->second.canonicalDigest;
    plan.oldManagedCodePath =
        oldPackage->second.managedFiles.baseCodePath;
    plan.oldManagedCodeDigest =
        oldPackage->second.managedFiles.baseCodeDigest;
    plan.sharedDataRootIdentity = Sha256Hex(
        "PRIMARY_USER_DATA_ROOT\n" + std::to_string(request.userId) +
        "\n" + request.manifest.packageName);
    const auto oldProjection =
        store_->impl_->projections.find(packageKey);
    plan.oldProjectionState =
        oldProjection != store_->impl_->projections.end() &&
        oldProjection->second.generation == oldGeneration &&
        oldProjection->second.canonicalDigest ==
            oldPackage->second.canonicalDigest &&
        oldProjection->second.state == HostProjectionState::ACTIVE
        ? HostProjectionState::ACTIVE
        : HostProjectionState::NONE;
    plan.obligations = {
        {"CODE", plan.oldManagedCodeDigest,
            RetirementObligationState::OPEN, "", 0},
        {"NATIVE", Sha256Hex("NATIVE_ABSENCE\n" +
            plan.packageName + "\n" +
            std::to_string(plan.oldGeneration)),
            RetirementObligationState::OPEN, "", 0},
        {"RESOURCE", Sha256Hex("RESOURCE_ABSENCE\n" +
            plan.packageName + "\n" +
            std::to_string(plan.oldGeneration)),
            RetirementObligationState::OPEN, "", 0},
    };
    plan.planDigest = ComputeRetirementPlanDigest(plan);
    if (!store_->impl_->AppendEvent(JoinTabs({
            "UPDATE_PLAN",
            HexEncode(plan.transactionId),
            HexEncode(plan.journalRef),
            HexEncode(plan.packageName),
            std::to_string(plan.userId),
            std::to_string(plan.oldGeneration),
            std::to_string(plan.newGeneration),
            HexEncode(plan.oldCanonicalDigest),
            HexEncode(plan.oldManagedCodePath),
            HexEncode(plan.oldManagedCodeDigest),
            HexEncode(plan.sharedDataRootIdentity),
            HexEncode(HostProjectionStateName(
                plan.oldProjectionState)),
            HexEncode(plan.planDigest),
            std::to_string(store_->impl_->recordVersion),
        }), &storeError)) {
        return MakeUpdateReceipt(request,
            UpdateVerdict::INTERNAL_IO_ERROR, "FAIL_CLOSED",
            request.manifest.packageName, oldGeneration, generation);
    }

    auto rollback = [&](const ManagedFilesV1& candidate) {
        std::string cleanupError;
        if (!candidate.baseCodePath.empty()) {
            (void)stager_->Cleanup(candidate, &cleanupError);
        }
        UpdateReceiptV1 receipt = MakeUpdateReceipt(request,
            UpdateVerdict::INTERNAL_IO_ERROR, "CLOSED_ROLLED_BACK",
            request.manifest.packageName, oldGeneration, generation,
            std::nullopt, plan.planDigest);
        if (!store_->impl_->AppendEvent(
                EncodeUpdateReceiptEvent(
                    "UPDATE_ROLLBACK", receipt),
                &storeError)) {
            receipt.verdict = UpdateVerdict::DATA_INCONSISTENT;
            receipt.terminalState = "FAIL_CLOSED";
        }
        return receipt;
    };
    if (faultInjector_->InterruptAfter(
            DurablePhase::P1_PLAN_DURABLE)) {
        if (faultInjector_->SimulatesProcessCrash()) {
            return MakeUpdateReceipt(request,
                UpdateVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
                "OPEN_NON_READY", request.manifest.packageName,
                oldGeneration, generation, std::nullopt,
                plan.planDigest);
        }
        return rollback({});
    }

    ManagedFilesV1 managedFiles;
    std::string stagingError;
    if (!stager_->Stage(request.manifest.packageName,
            request.userId, generation, artifact, &managedFiles,
            &stagingError) ||
        managedFiles.baseCodeDigest != artifact.sha256 ||
        managedFiles.baseCodePath.empty()) {
        return rollback(managedFiles);
    }
    if (!store_->impl_->AppendEvent(JoinTabs({
            "UPDATE_STAGE",
            HexEncode(request.admission.transactionId),
            std::to_string(generation),
            HexEncode(managedFiles.baseCodePath),
            HexEncode(managedFiles.baseCodeDigest),
            std::to_string(store_->impl_->recordVersion),
        }), &storeError)) {
        return rollback(managedFiles);
    }
    if (faultInjector_->InterruptAfter(
            DurablePhase::P2_FILES_PREPARED)) {
        if (faultInjector_->SimulatesProcessCrash()) {
            return MakeUpdateReceipt(request,
                UpdateVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
                "OPEN_NON_READY", request.manifest.packageName,
                oldGeneration, generation, std::nullopt,
                plan.planDigest);
        }
        return rollback(managedFiles);
    }
    if (!store_->impl_->AppendEvent(JoinTabs({
            "PHASE",
            HexEncode(request.admission.transactionId),
            HexEncode(DurablePhaseName(
                DurablePhase::P3_CANONICAL_PREPARED)),
            std::to_string(generation),
        }), &storeError)) {
        return rollback(managedFiles);
    }
    if (faultInjector_->InterruptAfter(
            DurablePhase::P3_CANONICAL_PREPARED)) {
        if (faultInjector_->SimulatesProcessCrash()) {
            return MakeUpdateReceipt(request,
                UpdateVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
                "OPEN_NON_READY", request.manifest.packageName,
                oldGeneration, generation, std::nullopt,
                plan.planDigest);
        }
        return rollback(managedFiles);
    }

    const InstallRequestV1 canonicalRequest = AsInstallShape(request);
    const std::string canonicalDigest = Sha256Hex(
        CanonicalGenerationJson(canonicalRequest, generation,
            managedFiles, "UPDATE"));
    if (!store_->impl_->AppendEvent(JoinTabs({
            "UPDATE_P4",
            HexEncode(request.admission.transactionId),
            std::to_string(generation),
            HexEncode(canonicalDigest),
            std::to_string(store_->impl_->recordVersion),
        }), &storeError)) {
        return rollback(managedFiles);
    }
    if (faultInjector_->InterruptAfter(
            DurablePhase::P4_PUBLICATION_PREPARED)) {
        if (faultInjector_->SimulatesProcessCrash()) {
            return MakeUpdateReceipt(request,
                UpdateVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
                "OPEN_NON_READY", request.manifest.packageName,
                oldGeneration, generation, canonicalDigest,
                plan.planDigest);
        }
        return rollback(managedFiles);
    }

    const std::string p5 = JoinTabs({
        "UPDATE_P5V2",
        HexEncode(request.admission.transactionId),
        HexEncode(request.manifest.packageName),
        std::to_string(request.userId),
        std::to_string(generation),
        HexEncode(request.artifactSet.artifactSetDigest),
        HexEncode(canonicalDigest),
        HexEncode(managedFiles.baseCodePath),
        HexEncode(managedFiles.baseCodeDigest),
        HexEncode(PublicationStateName(
            PublicationState::CANONICAL_SELECTED)),
        std::to_string(store_->impl_->recordVersion + 1),
        HexEncode(request.manifest.artifactSetDigest),
        HexEncode(request.manifest.parserVersion),
        std::to_string(request.manifest.versionCode),
        HexEncode(request.manifest.versionName),
        std::to_string(request.manifest.minSdk),
        std::to_string(request.manifest.targetSdk),
        HexEncode(request.manifest.applicationClassName),
        HexEncode(request.manifest.applicationLabel),
        EncodeComponents(request.manifest.components),
        EncodeStrings(request.manifest.requestedPermissions),
        EncodeStrings(request.manifest.declaredPermissions),
        EncodeProvenance(request.manifest.provenance),
        HexEncode(request.signing.artifactSetDigest),
        HexEncode(request.signing.verifierVersion),
        HexEncode(request.signing.policyProfile),
        request.signing.verified ? "1" : "0",
        EncodeUnsigneds(request.signing.schemeVersions),
        EncodeStrings(request.signing.signerCertificateDigests),
        HexEncode(request.signing.lineageDigest.value_or("")),
        EncodeStrings(request.signing.signerCertificateDerHex),
        EncodeSigningLineage(request.signing.lineage),
        HexEncode(request.signing.sourceReceiptDigest.value_or("")),
        "1",
        "1",
        "0",
        "0",
        HexEncode(artifact.artifactId),
        std::to_string(artifact.byteLength),
        HexEncode(artifact.sha256),
    });
    if (!store_->impl_->AppendEvent(p5, &storeError)) {
        return rollback(managedFiles);
    }
    if (faultInjector_->InterruptAfter(
            DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED)) {
        return MakeUpdateReceipt(request,
            UpdateVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
            "RECOVERING_FORWARD", request.manifest.packageName,
            oldGeneration, generation, canonicalDigest,
            plan.planDigest);
    }
    return FinishUpdateRetirement(request);
}

UninstallReceiptV1 PackageTransactionCoordinator::Uninstall(
    const UninstallRequestV1& input)
{
    if (store_ == nullptr || stager_ == nullptr ||
        faultInjector_ == nullptr) {
        return MakeUninstallReceipt(input,
            UninstallVerdict::INVALID_ENVELOPE, "REJECTED_TYPED");
    }
    std::unique_lock<std::mutex> lock(store_->impl_->mutex);
    std::string storeError;
    if (!store_->impl_->OpenLocked(&storeError)) {
        return MakeUninstallReceipt(input,
            UninstallVerdict::DATA_INCONSISTENT, "FAIL_CLOSED");
    }

    UninstallRequestV1 request = input;
    const bool hasStableTransaction =
        !request.admission.transactionId.empty() &&
        !request.admission.requestDigest.empty();
    const std::string actualRequestDigest =
        ComputeUninstallRequestDigest(request);
    if (request.admission.schemaVersion != 1 ||
        request.admission.operation != "UNINSTALL" ||
        request.admission.jobId.empty() ||
        request.admission.memberId.empty() ||
        request.admission.jobRecordVersion == 0 ||
        request.admission.callerScopeDigest.empty() ||
        request.admission.policySnapshotId.empty() ||
        request.retryIdentity.empty() ||
        request.policyRef.empty() ||
        request.packageSelector.empty() ||
        !request.expectedGeneration.has_value() ||
        *request.expectedGeneration == 0 ||
        (request.expectedPackageName.has_value() &&
            request.expectedPackageName->empty()) ||
        !hasStableTransaction ||
        request.admission.requestDigest != actualRequestDigest) {
        return MakeUninstallReceipt(request,
            UninstallVerdict::INVALID_ENVELOPE,
            "REJECTED_TYPED");
    }
    if (request.userId != kPrimaryUserId) {
        return MakeUninstallReceipt(request,
            UninstallVerdict::NOT_SUPPORTED,
            "REJECTED_TYPED");
    }
    if (request.admission.policySnapshotId !=
            request.policyRef) {
        return MakeUninstallReceipt(request,
            UninstallVerdict::INVALID_ENVELOPE,
            "REJECTED_TYPED");
    }

    const bool canPersistP0 = hasStableTransaction &&
        !request.retryIdentity.empty() &&
        !request.admission.jobId.empty() &&
        !request.admission.memberId.empty() &&
        request.admission.jobRecordVersion != 0 &&
        !request.admission.callerScopeDigest.empty() &&
        !request.admission.policySnapshotId.empty() &&
        request.admission.operation == "UNINSTALL";
    auto appendP0 = [&](const std::optional<std::string>& packageName,
                        uint64_t generation) {
        return store_->impl_->AppendEvent(JoinTabs({
            "P0",
            HexEncode(request.admission.transactionId),
            HexEncode(request.admission.requestDigest),
            HexEncode(""),
            HexEncode(packageName.value_or("")),
            std::to_string(request.userId),
            std::to_string(generation),
            HexEncode(request.retryIdentity),
            HexEncode(request.admission.jobId),
            HexEncode(request.admission.memberId),
            std::to_string(request.admission.memberIndex),
            std::to_string(request.admission.jobRecordVersion),
            HexEncode(request.admission.callerScopeDigest),
            HexEncode(request.admission.policySnapshotId),
            HexEncode(request.admission.operation),
        }), &storeError);
    };
    auto persistRejection =
        [&](UninstallVerdict verdict,
            const std::optional<std::string>& packageName,
            const std::optional<uint64_t>& generation)
            -> UninstallReceiptV1 {
        UninstallReceiptV1 receipt = MakeUninstallReceipt(
            request, verdict, "REJECTED_TYPED", packageName,
            generation);
        if (!canPersistP0) return receipt;
        if (store_->impl_->journals.find(
                request.admission.transactionId) ==
                store_->impl_->journals.end() &&
            !appendP0(packageName, generation.value_or(0))) {
            receipt.verdict = UninstallVerdict::INTERNAL_IO_ERROR;
            receipt.terminalState = "FAIL_CLOSED";
            return receipt;
        }
        if (!store_->impl_->AppendEvent(
                EncodeUninstallReceiptEvent(
                    "UNINSTALL_REJECT", receipt),
                &storeError)) {
            receipt.verdict = UninstallVerdict::INTERNAL_IO_ERROR;
            receipt.terminalState = "FAIL_CLOSED";
        }
        return receipt;
    };

    auto existing = store_->impl_->journals.find(
        request.admission.transactionId);
    if (existing != store_->impl_->journals.end()) {
        if (existing->second.operation != "UNINSTALL" ||
            existing->second.requestDigest !=
                request.admission.requestDigest ||
            existing->second.callerScopeDigest !=
                request.admission.callerScopeDigest) {
            return MakeUninstallReceipt(request,
                UninstallVerdict::IDEMPOTENCY_CONFLICT,
                "REJECTED_TYPED");
        }
        if (existing->second.uninstallReceipt.has_value()) {
            return *existing->second.uninstallReceipt;
        }
    }

    const std::string packageKey = PackageKey(
        request.userId, request.packageSelector);
    auto removalOwner =
        store_->impl_->removalOwnerByPackage.find(packageKey);
    if (removalOwner !=
        store_->impl_->removalOwnerByPackage.end()) {
        auto tombstone = store_->impl_->removalPlans.find(
            removalOwner->second);
        if (tombstone == store_->impl_->removalPlans.end() ||
            tombstone->second.state !=
                RemovalTombstoneState::OPEN) {
            return MakeUninstallReceipt(request,
                UninstallVerdict::DATA_INCONSISTENT,
                "FAIL_CLOSED");
        }
        const auto ownerJournal =
            store_->impl_->journals.find(
                tombstone->second.transactionId);
        if (ownerJournal == store_->impl_->journals.end() ||
            ownerJournal->second.operation != "UNINSTALL") {
            return MakeUninstallReceipt(request,
                UninstallVerdict::DATA_INCONSISTENT,
                "FAIL_CLOSED");
        }
        if (tombstone->second.requestDigest !=
                request.admission.requestDigest ||
            ownerJournal->second.callerScopeDigest !=
                request.admission.callerScopeDigest ||
            request.expectedPackageName !=
                std::optional<std::string>(
                    tombstone->second.packageName) ||
            request.expectedGeneration !=
                std::optional<uint64_t>(
                    tombstone->second.generation)) {
            return MakeUninstallReceipt(request,
                UninstallVerdict::PACKAGE_REMOVING,
                "REJECTED_TYPED");
        }
        request.admission.transactionId =
            tombstone->second.transactionId;
        existing = store_->impl_->journals.find(
            request.admission.transactionId);
    } else if (store_->impl_->removalTombstones.count(
                   packageKey) != 0) {
        return MakeUninstallReceipt(request,
            UninstallVerdict::PACKAGE_REMOVING,
            "REJECTED_TYPED");
    }

    auto tombstone = store_->impl_->removalPlans.find(
        request.admission.transactionId);
    if (tombstone == store_->impl_->removalPlans.end()) {
        const auto package =
            store_->impl_->packages.find(packageKey);
        if (package == store_->impl_->packages.end()) {
            for (const auto& [transactionId, closed] :
                 store_->impl_->removalPlans) {
                if (closed.state ==
                        RemovalTombstoneState::CLOSED_REMOVED &&
                    closed.userId == request.userId &&
                    closed.packageName ==
                        request.packageSelector &&
                    closed.requestDigest ==
                        request.admission.requestDigest &&
                    request.expectedPackageName ==
                        std::optional<std::string>(
                            closed.packageName) &&
                    request.expectedGeneration ==
                        std::optional<uint64_t>(
                            closed.generation)) {
                    const auto journal =
                        store_->impl_->journals.find(transactionId);
                    if (journal ==
                        store_->impl_->journals.end()) {
                        return MakeUninstallReceipt(request,
                            UninstallVerdict::DATA_INCONSISTENT,
                            "FAIL_CLOSED");
                    }
                    if (journal->second.callerScopeDigest !=
                        request.admission.callerScopeDigest) {
                        continue;
                    }
                    if (!journal->second.uninstallReceipt.has_value()) {
                        UninstallReceiptV1 recovered =
                            MakeUninstallReceipt(
                                request,
                                UninstallVerdict::REMOVED,
                                "CLOSED_REMOVED",
                                closed.packageName,
                                closed.generation,
                                closed.canonicalDigest,
                                &closed);
                        if (!store_->impl_->AppendEvent(
                                EncodeUninstallReceiptEvent(
                                    "UNINSTALL_P6",
                                    recovered),
                                &storeError)) {
                            recovered.verdict =
                                UninstallVerdict::
                                    INTERNAL_IO_ERROR;
                            recovered.terminalState =
                                "RECOVERING_FORWARD";
                        }
                        return recovered;
                    }
                    return *journal->second.uninstallReceipt;
                }
            }
            return persistRejection(
                UninstallVerdict::PACKAGE_NOT_FOUND,
                std::nullopt, std::nullopt);
        }
        if (store_->impl_->quarantinedPackages.count(
                packageKey) != 0) {
            return MakeUninstallReceipt(request,
                UninstallVerdict::DATA_INCONSISTENT,
                "FAIL_CLOSED", package->second.packageName,
                package->second.generation,
                package->second.canonicalDigest);
        }
        if (request.expectedPackageName !=
                std::optional<std::string>(
                    package->second.packageName)) {
            return persistRejection(
                UninstallVerdict::SELECTOR_MISMATCH,
                package->second.packageName,
                package->second.generation);
        }
        if (request.expectedGeneration !=
                std::optional<uint64_t>(
                    package->second.generation)) {
            return persistRejection(
                UninstallVerdict::GENERATION_MISMATCH,
                package->second.packageName,
                package->second.generation);
        }
        if (existing ==
            store_->impl_->journals.end()) {
            if (!appendP0(package->second.packageName,
                    package->second.generation)) {
                return MakeUninstallReceipt(request,
                    UninstallVerdict::INTERNAL_IO_ERROR,
                    "FAIL_CLOSED",
                    package->second.packageName,
                    package->second.generation,
                    package->second.canonicalDigest);
            }
        }
        if (faultInjector_->InterruptAfter(
                DurablePhase::P0_INPUT_FROZEN)) {
            return MakeUninstallReceipt(request,
                UninstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
                "OPEN", package->second.packageName,
                package->second.generation,
                package->second.canonicalDigest);
        }

        RemovalTombstoneV1 prepared;
        prepared.transactionId =
            request.admission.transactionId;
        prepared.requestDigest =
            request.admission.requestDigest;
        prepared.packageName = package->second.packageName;
        prepared.userId = request.userId;
        prepared.generation = package->second.generation;
        prepared.canonicalDigest =
            package->second.canonicalDigest;
        prepared.managedCodePath =
            package->second.managedFiles.baseCodePath;
        prepared.managedCodeDigest =
            package->second.managedFiles.baseCodeDigest;
        prepared.obligations = {
            {"PROJECTION", Sha256Hex("PROJECTION_ABSENCE\n" +
                prepared.packageName + "\n" +
                std::to_string(prepared.generation)),
                RemovalObligationState::OPEN, "", 0},
            {"TOKEN", Sha256Hex("TOKEN_ABSENCE\n" +
                prepared.packageName + "\n" +
                std::to_string(prepared.generation)),
                RemovalObligationState::OPEN, "", 0},
            {"CODE", prepared.managedCodeDigest,
                RemovalObligationState::OPEN, "", 0},
            {"DATA", Sha256Hex("DATA_ROOT_ABSENCE\n" +
                std::to_string(prepared.userId) + "\n" +
                prepared.packageName),
                RemovalObligationState::OPEN, "", 0},
            {"NATIVE", Sha256Hex("NATIVE_ABSENCE\n" +
                prepared.packageName + "\n" +
                std::to_string(prepared.generation)),
                RemovalObligationState::OPEN, "", 0},
            {"RESOURCE", Sha256Hex("RESOURCE_ABSENCE\n" +
                prepared.packageName + "\n" +
                std::to_string(prepared.generation)),
                RemovalObligationState::OPEN, "", 0},
            {"PRESENTATION", Sha256Hex(
                "PRESENTATION_ABSENCE\n" +
                prepared.packageName + "\n" +
                std::to_string(prepared.generation)),
                RemovalObligationState::OPEN, "", 0},
        };
        prepared.tombstoneDigest =
            ComputeRemovalTombstoneDigest(prepared);
        if (!store_->impl_->AppendEvent(JoinTabs({
                "UNINSTALL_PLAN",
                HexEncode(prepared.transactionId),
                HexEncode(prepared.requestDigest),
                HexEncode(prepared.packageName),
                std::to_string(prepared.userId),
                std::to_string(prepared.generation),
                HexEncode(prepared.canonicalDigest),
                HexEncode(prepared.managedCodePath),
                HexEncode(prepared.managedCodeDigest),
                HexEncode(prepared.tombstoneDigest),
                std::to_string(store_->impl_->recordVersion),
            }), &storeError)) {
            return MakeUninstallReceipt(request,
                UninstallVerdict::INTERNAL_IO_ERROR,
                "FAIL_CLOSED", prepared.packageName,
                prepared.generation,
                prepared.canonicalDigest);
        }
        tombstone = store_->impl_->removalPlans.find(
            request.admission.transactionId);
        if (faultInjector_->InterruptAfter(
                DurablePhase::P1_PLAN_DURABLE)) {
            return MakeUninstallReceipt(request,
                UninstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
                "OPEN_NON_READY", prepared.packageName,
                prepared.generation,
                prepared.canonicalDigest, &tombstone->second);
        }
    }

    if (tombstone->second.state ==
            RemovalTombstoneState::PREPARED) {
        if (!store_->impl_->AppendEvent(JoinTabs({
                "UNINSTALL_P5",
                HexEncode(tombstone->second.transactionId),
                std::to_string(store_->impl_->recordVersion),
            }), &storeError)) {
            return MakeUninstallReceipt(request,
                UninstallVerdict::INTERNAL_IO_ERROR,
                "FAIL_CLOSED", tombstone->second.packageName,
                tombstone->second.generation,
                tombstone->second.canonicalDigest,
                &tombstone->second);
        }
        tombstone = store_->impl_->removalPlans.find(
            request.admission.transactionId);
        if (faultInjector_->InterruptAfter(
                DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED)) {
            return MakeUninstallReceipt(request,
                UninstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE,
                "RECOVERING_FORWARD",
                tombstone->second.packageName,
                tombstone->second.generation,
                tombstone->second.canonicalDigest,
                &tombstone->second);
        }
    }
    if (tombstone->second.state ==
            RemovalTombstoneState::CLOSED_REMOVED) {
        auto journal = store_->impl_->journals.find(
            tombstone->second.transactionId);
        if (journal == store_->impl_->journals.end()) {
            return MakeUninstallReceipt(request,
                UninstallVerdict::DATA_INCONSISTENT,
                "FAIL_CLOSED", tombstone->second.packageName,
                tombstone->second.generation,
                tombstone->second.canonicalDigest,
                &tombstone->second);
        }
        if (journal->second.uninstallReceipt.has_value()) {
            return *journal->second.uninstallReceipt;
        }
        UninstallReceiptV1 recovered = MakeUninstallReceipt(
            request, UninstallVerdict::REMOVED,
            "CLOSED_REMOVED", tombstone->second.packageName,
            tombstone->second.generation,
            tombstone->second.canonicalDigest,
            &tombstone->second);
        if (!store_->impl_->AppendEvent(
                EncodeUninstallReceiptEvent(
                    "UNINSTALL_P6", recovered),
                &storeError)) {
            recovered.verdict =
                UninstallVerdict::INTERNAL_IO_ERROR;
            recovered.terminalState =
                "RECOVERING_FORWARD";
        }
        return recovered;
    }
    if (tombstone->second.state !=
            RemovalTombstoneState::OPEN) {
        return MakeUninstallReceipt(request,
            UninstallVerdict::DATA_INCONSISTENT,
            "FAIL_CLOSED");
    }

    auto closeObligation = [&](const std::string& kind,
                               const std::string& closeResult) {
        return store_->impl_->AppendEvent(JoinTabs({
            "UNINSTALL_OBLIGATION",
            HexEncode(request.admission.transactionId),
            HexEncode(kind),
            HexEncode(closeResult),
            std::to_string(store_->impl_->recordVersion),
        }), &storeError);
    };
    while (true) {
        tombstone = store_->impl_->removalPlans.find(
            request.admission.transactionId);
        auto obligation = std::find_if(
            tombstone->second.obligations.begin(),
            tombstone->second.obligations.end(),
            [](const RemovalObligationV1& item) {
                return item.state ==
                    RemovalObligationState::OPEN;
            });
        if (obligation ==
            tombstone->second.obligations.end()) {
            break;
        }
        const std::string kind = obligation->kind;
        std::string closeResult =
            "ABSENT_CONFIRMED_NO_MANAGED_LOCATOR";
        if (kind == "CODE") {
            const ManagedFilesV1 managedFiles = {
                tombstone->second.managedCodePath,
                tombstone->second.managedCodeDigest,
            };
            lock.unlock();
            std::string cleanupError;
            const bool cleaned =
                stager_->Cleanup(managedFiles, &cleanupError);
            errno = 0;
            const bool absent =
                access(managedFiles.baseCodePath.c_str(), F_OK) != 0 &&
                errno == ENOENT;
            lock.lock();
            if (!cleaned || !absent) {
                tombstone = store_->impl_->removalPlans.find(
                    request.admission.transactionId);
                return MakeUninstallReceipt(request,
                    UninstallVerdict::INTERNAL_IO_ERROR,
                    "RECOVERING_FORWARD",
                    tombstone->second.packageName,
                    tombstone->second.generation,
                    tombstone->second.canonicalDigest,
                    &tombstone->second);
            }
            closeResult = "REMOVED_READBACK_ABSENT";
        } else if (kind == "PROJECTION" ||
                   kind == "TOKEN") {
            closeResult = "REMOVED_DURABLE_READBACK_ABSENT";
        }
        tombstone = store_->impl_->removalPlans.find(
            request.admission.transactionId);
        if (tombstone == store_->impl_->removalPlans.end() ||
            tombstone->second.state !=
                RemovalTombstoneState::OPEN ||
            !closeObligation(kind, closeResult)) {
            return MakeUninstallReceipt(request,
                UninstallVerdict::INTERNAL_IO_ERROR,
                "RECOVERING_FORWARD",
                tombstone == store_->impl_->removalPlans.end()
                    ? std::optional<std::string>{}
                    : std::optional<std::string>{
                        tombstone->second.packageName},
                tombstone == store_->impl_->removalPlans.end()
                    ? std::optional<uint64_t>{}
                    : std::optional<uint64_t>{
                        tombstone->second.generation});
        }
    }
    tombstone = store_->impl_->removalPlans.find(
        request.admission.transactionId);
    if (!store_->impl_->AppendEvent(JoinTabs({
            "UNINSTALL_CLOSE",
            HexEncode(request.admission.transactionId),
            std::to_string(store_->impl_->recordVersion),
        }), &storeError)) {
        return MakeUninstallReceipt(request,
            UninstallVerdict::INTERNAL_IO_ERROR,
            "RECOVERING_FORWARD",
            tombstone->second.packageName,
            tombstone->second.generation,
            tombstone->second.canonicalDigest,
            &tombstone->second);
    }
    tombstone = store_->impl_->removalPlans.find(
        request.admission.transactionId);
    UninstallReceiptV1 receipt = MakeUninstallReceipt(
        request, UninstallVerdict::REMOVED,
        "CLOSED_REMOVED", tombstone->second.packageName,
        tombstone->second.generation,
        tombstone->second.canonicalDigest,
        &tombstone->second);
    if (!store_->impl_->AppendEvent(
            EncodeUninstallReceiptEvent(
                "UNINSTALL_P6", receipt),
            &storeError)) {
        receipt.verdict =
            UninstallVerdict::INTERNAL_IO_ERROR;
        receipt.terminalState = "RECOVERING_FORWARD";
    }
    return receipt;
}

const char* DurablePhaseName(DurablePhase phase)
{
    switch (phase) {
        case DurablePhase::P0_INPUT_FROZEN: return "P0_INPUT_FROZEN";
        case DurablePhase::P1_PLAN_DURABLE: return "P1_PLAN_DURABLE";
        case DurablePhase::P2_FILES_PREPARED: return "P2_FILES_PREPARED";
        case DurablePhase::P3_CANONICAL_PREPARED:
            return "P3_CANONICAL_PREPARED";
        case DurablePhase::P4_PUBLICATION_PREPARED:
            return "P4_PUBLICATION_PREPARED";
        case DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED:
            return "P5_ACTIVE_GENERATION_PUBLISHED";
        case DurablePhase::P6_RECEIPT_CLOSED: return "P6_RECEIPT_CLOSED";
    }
    return "UNKNOWN";
}

const char* InstallVerdictName(InstallVerdict verdict)
{
    switch (verdict) {
        case InstallVerdict::COMMITTED: return "COMMITTED";
        case InstallVerdict::NOT_SUPPORTED: return "NOT_SUPPORTED";
        case InstallVerdict::NOT_SUPPORTED_ARTIFACT_PROFILE:
            return "NOT_SUPPORTED_ARTIFACT_PROFILE";
        case InstallVerdict::INVALID_ENVELOPE: return "INVALID_ENVELOPE";
        case InstallVerdict::ARTIFACT_DIGEST_MISMATCH:
            return "ARTIFACT_DIGEST_MISMATCH";
        case InstallVerdict::IDENTITY_MISMATCH: return "IDENTITY_MISMATCH";
        case InstallVerdict::SIGNING_REJECTED: return "SIGNING_REJECTED";
        case InstallVerdict::POLICY_REJECTED: return "POLICY_REJECTED";
        case InstallVerdict::PACKAGE_ALREADY_EXISTS:
            return "PACKAGE_ALREADY_EXISTS";
        case InstallVerdict::PACKAGE_REMOVING: return "PACKAGE_REMOVING";
        case InstallVerdict::GENERATION_MISMATCH: return "GENERATION_MISMATCH";
        case InstallVerdict::IDEMPOTENCY_CONFLICT:
            return "IDEMPOTENCY_CONFLICT";
        case InstallVerdict::DATA_INCONSISTENT: return "DATA_INCONSISTENT";
        case InstallVerdict::INTERNAL_IO_ERROR: return "INTERNAL_IO_ERROR";
        case InstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE:
            return "INTERRUPTED_AFTER_DURABLE_WRITE";
    }
    return "DATA_INCONSISTENT";
}

const char* UpdateVerdictName(UpdateVerdict verdict)
{
    switch (verdict) {
        case UpdateVerdict::UPDATED: return "UPDATED";
        case UpdateVerdict::INVALID_ENVELOPE:
            return "INVALID_ENVELOPE";
        case UpdateVerdict::NOT_SUPPORTED: return "NOT_SUPPORTED";
        case UpdateVerdict::NOT_SUPPORTED_ARTIFACT_PROFILE:
            return "NOT_SUPPORTED_ARTIFACT_PROFILE";
        case UpdateVerdict::ARTIFACT_DIGEST_MISMATCH:
            return "ARTIFACT_DIGEST_MISMATCH";
        case UpdateVerdict::IDENTITY_MISMATCH:
            return "IDENTITY_MISMATCH";
        case UpdateVerdict::SIGNING_REJECTED:
            return "SIGNING_REJECTED";
        case UpdateVerdict::POLICY_REJECTED:
            return "POLICY_REJECTED";
        case UpdateVerdict::PACKAGE_NOT_FOUND:
            return "PACKAGE_NOT_FOUND";
        case UpdateVerdict::PACKAGE_REMOVING:
            return "PACKAGE_REMOVING";
        case UpdateVerdict::GENERATION_MISMATCH:
            return "GENERATION_MISMATCH";
        case UpdateVerdict::IDEMPOTENCY_CONFLICT:
            return "IDEMPOTENCY_CONFLICT";
        case UpdateVerdict::DATA_INCONSISTENT:
            return "DATA_INCONSISTENT";
        case UpdateVerdict::INTERNAL_IO_ERROR:
            return "INTERNAL_IO_ERROR";
        case UpdateVerdict::INTERRUPTED_AFTER_DURABLE_WRITE:
            return "INTERRUPTED_AFTER_DURABLE_WRITE";
    }
    return "DATA_INCONSISTENT";
}

const char* UninstallVerdictName(UninstallVerdict verdict)
{
    switch (verdict) {
        case UninstallVerdict::REMOVED: return "REMOVED";
        case UninstallVerdict::INVALID_ENVELOPE:
            return "INVALID_ENVELOPE";
        case UninstallVerdict::NOT_SUPPORTED:
            return "NOT_SUPPORTED";
        case UninstallVerdict::PACKAGE_NOT_FOUND:
            return "PACKAGE_NOT_FOUND";
        case UninstallVerdict::PACKAGE_REMOVING:
            return "PACKAGE_REMOVING";
        case UninstallVerdict::SELECTOR_MISMATCH:
            return "SELECTOR_MISMATCH";
        case UninstallVerdict::GENERATION_MISMATCH:
            return "GENERATION_MISMATCH";
        case UninstallVerdict::IDEMPOTENCY_CONFLICT:
            return "IDEMPOTENCY_CONFLICT";
        case UninstallVerdict::DATA_INCONSISTENT:
            return "DATA_INCONSISTENT";
        case UninstallVerdict::INTERNAL_IO_ERROR:
            return "INTERNAL_IO_ERROR";
        case UninstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE:
            return "INTERRUPTED_AFTER_DURABLE_WRITE";
    }
    return "DATA_INCONSISTENT";
}

const char* RemovalTombstoneStateName(
    RemovalTombstoneState state)
{
    switch (state) {
        case RemovalTombstoneState::PREPARED: return "PREPARED";
        case RemovalTombstoneState::OPEN: return "OPEN";
        case RemovalTombstoneState::CLOSED_REMOVED:
            return "CLOSED_REMOVED";
    }
    return "PREPARED";
}

const char* RemovalObligationStateName(
    RemovalObligationState state)
{
    switch (state) {
        case RemovalObligationState::OPEN: return "OPEN";
        case RemovalObligationState::CLOSED: return "CLOSED";
    }
    return "OPEN";
}

const char* RetirementPlanStateName(RetirementPlanState state)
{
    switch (state) {
        case RetirementPlanState::OPEN: return "OPEN";
        case RetirementPlanState::ACTIVE: return "ACTIVE";
        case RetirementPlanState::CLOSED: return "CLOSED";
    }
    return "OPEN";
}

const char* RetirementObligationStateName(
    RetirementObligationState state)
{
    switch (state) {
        case RetirementObligationState::OPEN: return "OPEN";
        case RetirementObligationState::CLOSED: return "CLOSED";
    }
    return "OPEN";
}

const char* PublicationStateName(PublicationState state)
{
    switch (state) {
        case PublicationState::NONE: return "NONE";
        case PublicationState::PREPARED: return "PREPARED";
        case PublicationState::CANONICAL_SELECTED: return "CANONICAL_SELECTED";
        case PublicationState::EXTERNAL_READY: return "EXTERNAL_READY";
    }
    return "NONE";
}

const char* HostProjectionStateName(HostProjectionState state)
{
    switch (state) {
        case HostProjectionState::NONE: return "NONE";
        case HostProjectionState::PREPARED: return "PREPARED";
        case HostProjectionState::ACTIVE: return "ACTIVE";
        case HostProjectionState::STALE: return "STALE";
        case HostProjectionState::REMOVING: return "REMOVING";
    }
    return "NONE";
}

const char* RestartRecoveryVerdictName(RestartRecoveryVerdict verdict)
{
    switch (verdict) {
        case RestartRecoveryVerdict::RESTORED_COMMITTED:
            return "RESTORED_COMMITTED";
        case RestartRecoveryVerdict::NON_READY: return "NON_READY";
        case RestartRecoveryVerdict::ABSENT: return "ABSENT";
        case RestartRecoveryVerdict::IDENTITY_MISMATCH:
            return "IDENTITY_MISMATCH";
        case RestartRecoveryVerdict::DATA_INCONSISTENT:
            return "DATA_INCONSISTENT";
    }
    return "DATA_INCONSISTENT";
}

std::string SerializeRestartRecoveryReceipt(
    const RestartRecoveryReceiptV1& receipt)
{
    auto optionalString = [](const std::optional<std::string>& value) {
        return value.has_value() ? JsonString(*value) : std::string("null");
    };
    auto optionalUnsigned = [](const std::optional<uint64_t>& value) {
        return value.has_value() ? std::to_string(*value) :
            std::string("null");
    };
    std::string managedFiles = "null";
    if (receipt.managedFiles.has_value()) {
        managedFiles = "{\"baseCodeDigest\":" +
            JsonString(receipt.managedFiles->baseCodeDigest) +
            ",\"baseCodePath\":" +
            JsonString(receipt.managedFiles->baseCodePath) + "}";
    }
    std::string userState = "null";
    if (receipt.primaryUserState.has_value()) {
        const auto& state = *receipt.primaryUserState;
        userState = "{\"enabled\":" +
            std::string(state.enabled ? "true" : "false") +
            ",\"hidden\":" + (state.hidden ? "true" : "false") +
            ",\"installed\":" + (state.installed ? "true" : "false") +
            ",\"stopped\":" + (state.stopped ? "true" : "false") +
            ",\"userId\":" + std::to_string(state.userId) + "}";
    }
    std::string artifacts = "[";
    for (size_t index = 0; index < receipt.artifacts.size(); ++index) {
        if (index != 0) artifacts += ",";
        const auto& artifact = receipt.artifacts[index];
        artifacts += "{\"artifactId\":" + JsonString(artifact.artifactId) +
            ",\"byteLength\":" + std::to_string(artifact.byteLength) +
            ",\"sha256\":" + JsonString(artifact.sha256) + "}";
    }
    artifacts += "]";
    return std::string("{") +
        "\"actionId\":" + JsonString(receipt.actionId) +
        ",\"artifactSetDigest\":" +
            optionalString(receipt.artifactSetDigest) +
        ",\"artifacts\":" + artifacts +
        ",\"boundary\":{\"afterBootId\":" +
            JsonString(receipt.boundary.afterBootId) +
            ",\"afterServiceId\":" +
            JsonString(receipt.boundary.afterServiceId) +
            ",\"beforeBootId\":" +
            JsonString(receipt.boundary.beforeBootId) +
            ",\"beforeServiceId\":" +
            JsonString(receipt.boundary.beforeServiceId) + "}" +
        ",\"canonicalDigest\":" + optionalString(receipt.canonicalDigest) +
        ",\"catalogRevision\":" +
            std::to_string(receipt.catalogRevision) +
        ",\"consumerReady\":" +
            std::string(receipt.consumerReady ? "true" : "false") +
        ",\"durablePhase\":" + JsonString(DurablePhaseName(
            receipt.durablePhase)) +
        ",\"generation\":" + optionalUnsigned(receipt.generation) +
        ",\"hostProjectionState\":" +
            JsonString(HostProjectionStateName(
                receipt.hostProjectionState)) +
        ",\"journalPresent\":" +
            std::string(receipt.journalPresent ? "true" : "false") +
        ",\"managedFiles\":" + managedFiles +
        ",\"packageName\":" + optionalString(receipt.packageName) +
        ",\"primaryUserState\":" + userState +
        ",\"publicationState\":" +
            JsonString(PublicationStateName(receipt.publicationState)) +
        ",\"reason\":" + JsonString(receipt.reason) +
        ",\"requestDigest\":" + JsonString(receipt.requestDigest) +
        ",\"requestId\":" + JsonString(receipt.requestId) +
        ",\"schemaVersion\":" + std::to_string(receipt.schemaVersion) +
        ",\"terminalState\":" + JsonString(receipt.terminalState) +
        ",\"transactionId\":" + JsonString(receipt.transactionId) +
        ",\"verdict\":" +
            JsonString(RestartRecoveryVerdictName(receipt.verdict)) + "}";
}

std::string SerializeUpdateReceipt(const UpdateReceiptV1& receipt)
{
    auto optionalString = [](const std::optional<std::string>& value) {
        return value.has_value() ? JsonString(*value) :
            std::string("null");
    };
    auto optionalUnsigned = [](const std::optional<uint64_t>& value) {
        return value.has_value() ? std::to_string(*value) :
            std::string("null");
    };
    return std::string("{") +
        "\"actionId\":" + JsonString(receipt.actionId) +
        ",\"artifactSetDigest\":" +
            optionalString(receipt.artifactSetDigest) +
        ",\"canonicalDigest\":" +
            optionalString(receipt.canonicalDigest) +
        ",\"newGeneration\":" +
            optionalUnsigned(receipt.newGeneration) +
        ",\"oldGeneration\":" +
            optionalUnsigned(receipt.oldGeneration) +
        ",\"packageName\":" + optionalString(receipt.packageName) +
        ",\"policyRuleId\":" + JsonString(receipt.policyRuleId) +
        ",\"policyRulesDigest\":" +
            JsonString(receipt.policyRulesDigest) +
        ",\"policyVersion\":" + JsonString(receipt.policyVersion) +
        ",\"requestDigest\":" + JsonString(receipt.requestDigest) +
        ",\"retirementPlanDigest\":" +
            optionalString(receipt.retirementPlanDigest) +
        ",\"schemaVersion\":" + std::to_string(receipt.schemaVersion) +
        ",\"terminalState\":" + JsonString(receipt.terminalState) +
        ",\"transactionId\":" + JsonString(receipt.transactionId) +
        ",\"verdict\":" + JsonString(UpdateVerdictName(
            receipt.verdict)) + "}";
}

std::string SerializeRetirementPlan(
    const GenerationRetirementPlanV1& plan)
{
    std::string obligations = "[";
    for (size_t index = 0; index < plan.obligations.size(); ++index) {
        if (index != 0) obligations += ",";
        const auto& obligation = plan.obligations[index];
        obligations += "{\"closedRecordVersion\":" +
            std::to_string(obligation.closedRecordVersion) +
            ",\"closeResult\":" +
            JsonString(obligation.closeResult) +
            ",\"identityDigest\":" +
            JsonString(obligation.identityDigest) +
            ",\"kind\":" + JsonString(obligation.kind) +
            ",\"state\":" + JsonString(
                RetirementObligationStateName(obligation.state)) + "}";
    }
    obligations += "]";
    return std::string("{") +
        "\"journalRef\":" + JsonString(plan.journalRef) +
        ",\"newGeneration\":" + std::to_string(plan.newGeneration) +
        ",\"obligations\":" + obligations +
        ",\"oldCanonicalDigest\":" +
            JsonString(plan.oldCanonicalDigest) +
        ",\"oldGeneration\":" + std::to_string(plan.oldGeneration) +
        ",\"oldManagedCodeDigest\":" +
            JsonString(plan.oldManagedCodeDigest) +
        ",\"oldManagedCodePath\":" +
            JsonString(plan.oldManagedCodePath) +
        ",\"oldProjectionState\":" +
            JsonString(HostProjectionStateName(
                plan.oldProjectionState)) +
        ",\"packageName\":" + JsonString(plan.packageName) +
        ",\"planDigest\":" + JsonString(plan.planDigest) +
        ",\"recordVersion\":" + std::to_string(plan.recordVersion) +
        ",\"schemaVersion\":" + std::to_string(plan.schemaVersion) +
        ",\"sharedDataPreserved\":" +
            std::string(plan.sharedDataPreserved ? "true" : "false") +
        ",\"sharedDataRootIdentity\":" +
            JsonString(plan.sharedDataRootIdentity) +
        ",\"state\":" + JsonString(
            RetirementPlanStateName(plan.state)) +
        ",\"transactionId\":" + JsonString(plan.transactionId) +
        ",\"userId\":" + std::to_string(plan.userId) + "}";
}

std::string SerializeRemovalTombstone(
    const RemovalTombstoneV1& tombstone)
{
    std::string obligations = "[";
    for (size_t index = 0;
         index < tombstone.obligations.size(); ++index) {
        if (index != 0) obligations += ",";
        const auto& obligation = tombstone.obligations[index];
        obligations += "{\"closedRecordVersion\":" +
            std::to_string(obligation.closedRecordVersion) +
            ",\"closeResult\":" +
            JsonString(obligation.closeResult) +
            ",\"identityDigest\":" +
            JsonString(obligation.identityDigest) +
            ",\"kind\":" + JsonString(obligation.kind) +
            ",\"state\":" + JsonString(
                RemovalObligationStateName(
                    obligation.state)) + "}";
    }
    obligations += "]";
    return std::string("{") +
        "\"canonicalDigest\":" +
            JsonString(tombstone.canonicalDigest) +
        ",\"generation\":" +
            std::to_string(tombstone.generation) +
        ",\"managedCodeDigest\":" +
            JsonString(tombstone.managedCodeDigest) +
        ",\"managedCodePath\":" +
            JsonString(tombstone.managedCodePath) +
        ",\"obligations\":" + obligations +
        ",\"packageName\":" +
            JsonString(tombstone.packageName) +
        ",\"recordVersion\":" +
            std::to_string(tombstone.recordVersion) +
        ",\"requestDigest\":" +
            JsonString(tombstone.requestDigest) +
        ",\"schemaVersion\":" +
            std::to_string(tombstone.schemaVersion) +
        ",\"state\":" + JsonString(
            RemovalTombstoneStateName(tombstone.state)) +
        ",\"tombstoneDigest\":" +
            JsonString(tombstone.tombstoneDigest) +
        ",\"transactionId\":" +
            JsonString(tombstone.transactionId) +
        ",\"userId\":" + std::to_string(tombstone.userId) + "}";
}

std::string SerializeUninstallReceipt(
    const UninstallReceiptV1& receipt)
{
    auto optionalString = [](const std::optional<std::string>& value) {
        return value.has_value() ? JsonString(*value) :
            std::string("null");
    };
    auto optionalUnsigned = [](const std::optional<uint64_t>& value) {
        return value.has_value() ? std::to_string(*value) :
            std::string("null");
    };
    return std::string("{") +
        "\"actionId\":" + JsonString(receipt.actionId) +
        ",\"canonicalDigest\":" +
            optionalString(receipt.canonicalDigest) +
        ",\"generation\":" +
            optionalUnsigned(receipt.generation) +
        ",\"packageName\":" +
            optionalString(receipt.packageName) +
        ",\"requestDigest\":" +
            JsonString(receipt.requestDigest) +
        ",\"residualObligations\":" +
            StringArrayJson(receipt.residualObligations) +
        ",\"schemaVersion\":" +
            std::to_string(receipt.schemaVersion) +
        ",\"terminalState\":" +
            JsonString(receipt.terminalState) +
        ",\"tombstoneDigest\":" +
            optionalString(receipt.tombstoneDigest) +
        ",\"transactionId\":" +
            JsonString(receipt.transactionId) +
        ",\"verdict\":" +
            JsonString(UninstallVerdictName(
                receipt.verdict)) + "}";
}

}  // namespace oh_adapter::package_transaction
