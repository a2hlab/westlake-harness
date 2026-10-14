#include "signing_metadata_v1.h"

#include "apk_signature_verifier.h"
#include "sha256.h"

#include <algorithm>
#include <array>
#include <cerrno>
#include <charconv>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <map>
#include <openssl/bio.h>
#include <openssl/evp.h>
#include <openssl/sha.h>
#include <openssl/x509.h>
#include <set>
#include <sstream>
#include <string_view>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <utility>

namespace oh_adapter::signing_metadata {
namespace {

using package_transaction::ArtifactRole;
using package_transaction::ComputeArtifactSetDigest;

constexpr size_t kMaxRequestIdBytes = 128;
constexpr size_t kMaxPolicyIdentityBytes = 128;
constexpr uint64_t kMaxArtifactBytes = 1024ULL * 1024ULL * 1024ULL;

bool IsLowerHex(const std::string& value, size_t bytes)
{
    if (value.size() != bytes * 2) return false;
    return std::all_of(value.begin(), value.end(), [](char character) {
        return (character >= '0' && character <= '9') ||
            (character >= 'a' && character <= 'f');
    });
}

std::string Hex(const uint8_t* bytes, size_t size)
{
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(size * 2, '0');
    for (size_t index = 0; index < size; ++index) {
        result[index * 2] = kHex[bytes[index] >> 4];
        result[index * 2 + 1] = kHex[bytes[index] & 0x0f];
    }
    return result;
}

std::string Hex(std::string_view value)
{
    return Hex(reinterpret_cast<const uint8_t*>(value.data()), value.size());
}

bool Unhex(const std::string& encoded, std::string* value)
{
    if (value == nullptr || encoded.size() % 2 != 0) return false;
    auto nibble = [](char character) -> int {
        if (character >= '0' && character <= '9') return character - '0';
        if (character >= 'a' && character <= 'f') {
            return character - 'a' + 10;
        }
        return -1;
    };
    value->clear();
    value->reserve(encoded.size() / 2);
    for (size_t index = 0; index < encoded.size(); index += 2) {
        const int high = nibble(encoded[index]);
        const int low = nibble(encoded[index + 1]);
        if (high < 0 || low < 0) {
            value->clear();
            return false;
        }
        value->push_back(static_cast<char>((high << 4) | low));
    }
    return true;
}

std::string Sha256Hex(std::string_view value)
{
    unsigned char digest[32]{};
    sha256(reinterpret_cast<const unsigned char*>(value.data()),
        value.size(), digest);
    return Hex(digest, sizeof(digest));
}

bool DigestFd(int fd, std::string* digest, uint64_t* byteLength)
{
    if (digest == nullptr || byteLength == nullptr) return false;
    EVP_MD_CTX* context = EVP_MD_CTX_new();
    if (context == nullptr ||
        EVP_DigestInit_ex(context, EVP_sha256(), nullptr) != 1) {
        EVP_MD_CTX_free(context);
        return false;
    }
    std::array<uint8_t, 64 * 1024> buffer{};
    uint64_t offset = 0;
    while (true) {
        const ssize_t count = pread(fd, buffer.data(), buffer.size(),
            static_cast<off_t>(offset));
        if (count < 0 && errno == EINTR) continue;
        if (count < 0) {
            EVP_MD_CTX_free(context);
            return false;
        }
        if (count == 0) break;
        if (EVP_DigestUpdate(context, buffer.data(),
                static_cast<size_t>(count)) != 1) {
            EVP_MD_CTX_free(context);
            return false;
        }
        offset += static_cast<uint64_t>(count);
        if (offset > kMaxArtifactBytes) {
            EVP_MD_CTX_free(context);
            return false;
        }
    }
    std::array<uint8_t, EVP_MAX_MD_SIZE> result{};
    unsigned int resultSize = 0;
    const bool finalized =
        EVP_DigestFinal_ex(context, result.data(), &resultSize) == 1;
    EVP_MD_CTX_free(context);
    if (!finalized || resultSize != SHA256_DIGEST_LENGTH) return false;
    *digest = Hex(result.data(), resultSize);
    *byteLength = offset;
    return true;
}

std::vector<std::string> Split(const std::string& value, char separator)
{
    if (value.empty()) return {};
    std::vector<std::string> result;
    size_t begin = 0;
    while (true) {
        const size_t found = value.find(separator, begin);
        if (found == std::string::npos) {
            result.push_back(value.substr(begin));
            return result;
        }
        result.push_back(value.substr(begin, found - begin));
        begin = found + 1;
    }
}

template <typename Integer>
bool ParseUnsigned(const std::string& value, Integer* result)
{
    if (result == nullptr || value.empty()) return false;
    Integer parsed = 0;
    const auto conversion =
        std::from_chars(value.data(), value.data() + value.size(), parsed);
    if (conversion.ec != std::errc() ||
        conversion.ptr != value.data() + value.size()) {
        return false;
    }
    *result = parsed;
    return true;
}

std::string Join(const std::vector<std::string>& values, char separator)
{
    std::string result;
    for (size_t index = 0; index < values.size(); ++index) {
        if (index != 0) result.push_back(separator);
        result += values[index];
    }
    return result;
}

std::string EncodeReceiptWithoutDigest(
    const SigningMetadataReceiptV1& receipt)
{
    std::vector<std::string> signers;
    for (const auto& signer : receipt.signers) {
        signers.push_back(
            signer.certificateSha256 + ":" + Hex(signer.subject));
    }
    std::vector<std::string> contentDigests;
    for (const auto& content : receipt.contentDigests) {
        contentDigests.push_back(
            Hex(content.algorithm) + ":" + content.sha256OrDigestHex);
    }
    std::vector<std::string> lineage;
    for (const auto& item : receipt.lineage) {
        lineage.push_back(item.certificateSha256 + ":" +
            std::to_string(item.capabilities));
    }
    return Join({
        "SMR1",
        receipt.artifactSha256,
        receipt.artifactSetDigest,
        Hex(receipt.policyVersion),
        Hex(receipt.verifierVersion),
        std::to_string(receipt.schemeVersion),
        Join(signers, ','),
        Join(contentDigests, ','),
        Join(lineage, ','),
        receipt.lineageDigest.value_or("-"),
        receipt.verificationTranscriptSha256,
    }, '\t');
}

bool SameReceipt(const SigningMetadataReceiptV1& left,
    const SigningMetadataReceiptV1& right)
{
    return left.receiptDigest == right.receiptDigest &&
        EncodeReceiptWithoutDigest(left) == EncodeReceiptWithoutDigest(right);
}

bool DecodeReceipt(const std::string& encoded,
    SigningMetadataReceiptV1* receipt)
{
    if (receipt == nullptr) return false;
    std::string line = encoded;
    if (!line.empty() && line.back() == '\n') line.pop_back();
    const auto fields = Split(line, '\t');
    if (fields.size() != 12 || fields[0] != "SMR1") return false;
    SigningMetadataReceiptV1 parsed;
    parsed.artifactSha256 = fields[1];
    parsed.artifactSetDigest = fields[2];
    if (!Unhex(fields[3], &parsed.policyVersion) ||
        !Unhex(fields[4], &parsed.verifierVersion) ||
        !ParseUnsigned(fields[5], &parsed.schemeVersion) ||
        !IsLowerHex(fields[10], 32) || !IsLowerHex(fields[11], 32)) {
        return false;
    }
    for (const auto& value : Split(fields[6], ',')) {
        const size_t separator = value.find(':');
        std::string subject;
        if (separator == std::string::npos ||
            !IsLowerHex(value.substr(0, separator), 32) ||
            !Unhex(value.substr(separator + 1), &subject)) {
            return false;
        }
        parsed.signers.push_back(
            {value.substr(0, separator), std::move(subject)});
    }
    for (const auto& value : Split(fields[7], ',')) {
        const size_t separator = value.find(':');
        std::string algorithm;
        if (separator == std::string::npos ||
            !Unhex(value.substr(0, separator), &algorithm) ||
            value.size() - separator - 1 == 0 ||
            (value.size() - separator - 1) % 2 != 0 ||
            !IsLowerHex(value.substr(separator + 1),
                (value.size() - separator - 1) / 2)) {
            return false;
        }
        parsed.contentDigests.push_back(
            {std::move(algorithm), value.substr(separator + 1)});
    }
    for (const auto& value : Split(fields[8], ',')) {
        const size_t separator = value.find(':');
        uint32_t capabilities = 0;
        if (separator == std::string::npos ||
            !IsLowerHex(value.substr(0, separator), 32) ||
            !ParseUnsigned(value.substr(separator + 1), &capabilities)) {
            return false;
        }
        parsed.lineage.push_back(
            {value.substr(0, separator), capabilities});
    }
    if (fields[9] != "-") {
        if (!IsLowerHex(fields[9], 32)) return false;
        parsed.lineageDigest = fields[9];
    }
    parsed.verificationTranscriptSha256 = fields[10];
    parsed.receiptDigest = fields[11];
    if (!IsLowerHex(parsed.artifactSha256, 32) ||
        !IsLowerHex(parsed.artifactSetDigest, 32) ||
        Sha256Hex(EncodeReceiptWithoutDigest(parsed)) !=
            parsed.receiptDigest) {
        return false;
    }
    *receipt = std::move(parsed);
    return true;
}

bool WriteAll(int fd, std::string_view value)
{
    size_t offset = 0;
    while (offset < value.size()) {
        const ssize_t count = write(fd, value.data() + offset,
            value.size() - offset);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) return false;
        offset += static_cast<size_t>(count);
    }
    return true;
}

bool ReadFile(const std::string& path, std::string* value)
{
    const int fd = open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return false;
    struct stat status {};
    if (fstat(fd, &status) != 0 || !S_ISREG(status.st_mode) ||
        status.st_size <= 0 || status.st_size > 1024 * 1024) {
        close(fd);
        return false;
    }
    value->assign(static_cast<size_t>(status.st_size), '\0');
    size_t offset = 0;
    while (offset < value->size()) {
        const ssize_t count = read(fd, value->data() + offset,
            value->size() - offset);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) {
            close(fd);
            return false;
        }
        offset += static_cast<size_t>(count);
    }
    close(fd);
    return true;
}

std::string ReceiptKey(const SigningMetadataPolicyV1& policy,
    const std::string& artifactSha256)
{
    return Sha256Hex("Fn01.A13\n" + artifactSha256 + "\n" +
        policy.policyVersion + "\n" + policy.verifierVersion);
}

std::string JsonEscape(std::string_view value)
{
    std::ostringstream output;
    for (const unsigned char character : value) {
        switch (character) {
            case '"': output << "\\\""; break;
            case '\\': output << "\\\\"; break;
            case '\n': output << "\\n"; break;
            case '\r': output << "\\r"; break;
            case '\t': output << "\\t"; break;
            default:
                if (character < 0x20) {
                    static constexpr char kHex[] = "0123456789abcdef";
                    output << "\\u00" << kHex[character >> 4]
                           << kHex[character & 0x0f];
                } else {
                    output << character;
                }
        }
    }
    return output.str();
}

SigningMetadataResponseV1 Reject(const SigningMetadataRequestV1& request,
    SigningMetadataVerdict verdict, std::string reason)
{
    SigningMetadataResponseV1 response;
    response.requestId = request.requestId;
    response.verdict = verdict;
    response.negativeReason = std::move(reason);
    response.receipt.reset();
    response.signerTruthVisible = false;
    response.replayed = false;
    return response;
}

bool SubjectFromDer(const std::vector<uint8_t>& der, std::string* subject)
{
    const uint8_t* cursor = der.data();
    X509* certificate = d2i_X509(
        nullptr, &cursor, static_cast<long>(der.size()));
    if (certificate == nullptr || cursor != der.data() + der.size()) {
        X509_free(certificate);
        return false;
    }
    BIO* output = BIO_new(BIO_s_mem());
    const bool ok = output != nullptr &&
        X509_NAME_print_ex(output, X509_get_subject_name(certificate),
            0, XN_FLAG_RFC2253) >= 0;
    char* data = nullptr;
    const long size = ok ? BIO_get_mem_data(output, &data) : 0;
    if (!ok || size <= 0 || data == nullptr) {
        BIO_free(output);
        X509_free(certificate);
        return false;
    }
    subject->assign(data, static_cast<size_t>(size));
    BIO_free(output);
    X509_free(certificate);
    return true;
}

std::optional<std::string> ComputeLineageDigest(
    const std::vector<SigningLineageFactV1>& lineage)
{
    if (lineage.empty()) return std::nullopt;
    std::string canonical = "SigningLineageV1";
    for (const auto& item : lineage) {
        canonical += "\n" + item.certificateSha256 + ":" +
            std::to_string(item.capabilities);
    }
    return Sha256Hex(canonical);
}

bool SameSignerSet(const std::vector<Sha256Digest>& left,
    const std::vector<Sha256Digest>& right)
{
    auto leftSorted = left;
    auto rightSorted = right;
    std::sort(leftSorted.begin(), leftSorted.end());
    std::sort(rightSorted.begin(), rightSorted.end());
    return leftSorted == rightSorted;
}

std::string PriorSigningFactsDigest(const PriorSigningFactsV1& prior)
{
    std::vector<std::string> signers;
    signers.reserve(prior.currentSignerSha256.size());
    for (const auto& signer : prior.currentSignerSha256) {
        signers.push_back(Hex(signer.data(), signer.size()));
    }
    std::sort(signers.begin(), signers.end());
    std::string canonical =
        "PriorSigningFactsV1\nS:" + Join(signers, ',');
    for (const auto& lineage : prior.lineage) {
        canonical += "\nL:" +
            Hex(lineage.sha256.data(), lineage.sha256.size()) + ":" +
            std::to_string(lineage.capabilities);
    }
    return Sha256Hex(canonical);
}

bool ContinuityAllowed(const PriorSigningFactsV1& prior,
    const ApkVerifiedIdentity& current, std::string* capabilityPath)
{
    if (capabilityPath != nullptr) capabilityPath->clear();
    if (prior.currentSignerSha256.empty() ||
        current.currentSignerSha256.empty()) {
        return false;
    }
    if (SameSignerSet(prior.currentSignerSha256,
            current.currentSignerSha256)) {
        if (capabilityPath != nullptr) {
            *capabilityPath = "SAME_SIGNER_SET";
        }
        return true;
    }
    if (prior.currentSignerSha256.size() != 1 ||
        current.currentSignerSha256.size() != 1) {
        return false;
    }
    for (const auto& entry : current.lineage) {
        if (entry.sha256 == prior.currentSignerSha256[0] &&
            (entry.capabilities &
                kApkSignerCapabilityInstalledData) != 0) {
            if (capabilityPath != nullptr) {
                *capabilityPath =
                    "CURRENT_LINEAGE_INSTALLED_DATA";
            }
            return true;
        }
    }
    for (const auto& entry : prior.lineage) {
        if (entry.sha256 == current.currentSignerSha256[0] &&
            (entry.capabilities & kApkSignerCapabilityRollback) != 0) {
            if (capabilityPath != nullptr) {
                *capabilityPath = "PRIOR_LINEAGE_ROLLBACK";
            }
            return true;
        }
    }
    return false;
}

SigningContinuityDecisionV1 ContinuityDecision(
    const PriorSigningFactsV1& prior, bool allowed,
    std::string capabilityPath, const std::string& receiptDigest)
{
    SigningContinuityDecisionV1 decision;
    decision.priorSigningFactsDigest = PriorSigningFactsDigest(prior);
    decision.allowed = allowed;
    decision.capabilityPath = std::move(capabilityPath);
    decision.decisionDigest = Sha256Hex(
        "SigningContinuityDecisionV1\n" + receiptDigest + "\n" +
        decision.priorSigningFactsDigest + "\n" +
        (decision.allowed ? "ALLOWED" : "REJECTED") + "\n" +
        decision.capabilityPath);
    return decision;
}

bool ReceiptMatchesRequest(const SigningMetadataReceiptV1& receipt,
    const SigningMetadataRequestV1& request,
    const SigningMetadataPolicyV1& policy,
    const std::string& artifactSha256)
{
    return receipt.schemaVersion == 1 &&
        receipt.actionId == "Fn01.A13" &&
        receipt.artifactSha256 == artifactSha256 &&
        receipt.artifactSetDigest ==
            request.artifactSet.artifactSetDigest &&
        receipt.policyVersion == policy.policyVersion &&
        receipt.verifierVersion == policy.verifierVersion &&
        receipt.schemeVersion >= policy.minimumSchemeVersion &&
        !receipt.signers.empty() && !receipt.contentDigests.empty() &&
        IsLowerHex(receipt.verificationTranscriptSha256, 32) &&
        IsLowerHex(receipt.receiptDigest, 32);
}

SigningMetadataResponseV1 PositiveResponse(
    const SigningMetadataRequestV1& request,
    SigningMetadataReceiptV1 receipt, bool replayed)
{
    SigningMetadataResponseV1 response;
    response.requestId = request.requestId;
    response.verdict = SigningMetadataVerdict::VERIFIED;
    response.receipt = std::move(receipt);
    response.signerTruthVisible = true;
    response.replayed = replayed;
    return response;
}

std::string ContentAlgorithmName(uint32_t signatureAlgorithmId)
{
    switch (signatureAlgorithmId) {
        case 0x0102:
        case 0x0202:
            return "APK_CHUNKED_SHA512";
        default:
            return "APK_CHUNKED_SHA256";
    }
}

}  // namespace

FileSigningMetadataReceiptStore::FileSigningMetadataReceiptStore(
    std::string root)
    : root_(std::move(root))
{
}

bool FileSigningMetadataReceiptStore::Open(std::string* error)
{
    if (root_.empty() || root_.front() != '/') {
        if (error != nullptr) *error = "receipt root must be absolute";
        return false;
    }
    if (mkdir(root_.c_str(), 0700) != 0 && errno != EEXIST) {
        if (error != nullptr) {
            *error = "cannot create receipt root: " +
                std::string(strerror(errno));
        }
        return false;
    }
    struct stat status {};
    if (lstat(root_.c_str(), &status) != 0 ||
        !S_ISDIR(status.st_mode) || S_ISLNK(status.st_mode)) {
        if (error != nullptr) *error = "receipt root is not a directory";
        return false;
    }
    if (error != nullptr) error->clear();
    return true;
}

SigningReceiptReadResult FileSigningMetadataReceiptStore::Read(
    const std::string& receiptKey, SigningMetadataReceiptV1* receipt,
    std::string* error) const
{
    if (!IsLowerHex(receiptKey, 32) || receipt == nullptr) {
        if (error != nullptr) *error = "invalid receipt key";
        return SigningReceiptReadResult::ERROR;
    }
    const std::string path = root_ + "/" + receiptKey + ".receipt";
    struct stat status {};
    if (lstat(path.c_str(), &status) != 0) {
        if (errno == ENOENT) return SigningReceiptReadResult::ABSENT;
        if (error != nullptr) {
            *error = "cannot stat receipt: " + std::string(strerror(errno));
        }
        return SigningReceiptReadResult::ERROR;
    }
    if (!S_ISREG(status.st_mode) || S_ISLNK(status.st_mode)) {
        if (error != nullptr) *error = "receipt is not a regular file";
        return SigningReceiptReadResult::ERROR;
    }
    std::string encoded;
    if (!ReadFile(path, &encoded) || !DecodeReceipt(encoded, receipt)) {
        if (error != nullptr) *error = "receipt readback is corrupt";
        return SigningReceiptReadResult::ERROR;
    }
    if (error != nullptr) error->clear();
    return SigningReceiptReadResult::FOUND;
}

bool FileSigningMetadataReceiptStore::Persist(
    const std::string& receiptKey,
    const SigningMetadataReceiptV1& receipt, std::string* error)
{
    if (!IsLowerHex(receiptKey, 32) ||
        Sha256Hex(EncodeReceiptWithoutDigest(receipt)) !=
            receipt.receiptDigest) {
        if (error != nullptr) *error = "invalid receipt identity";
        return false;
    }
    SigningMetadataReceiptV1 existing;
    const auto readResult = Read(receiptKey, &existing, error);
    if (readResult == SigningReceiptReadResult::FOUND) {
        return SameReceipt(existing, receipt);
    }
    if (readResult == SigningReceiptReadResult::ERROR) return false;

    const std::string target = root_ + "/" + receiptKey + ".receipt";
    std::string temporary = target + ".tmp.XXXXXX";
    std::vector<char> temporaryBuffer(
        temporary.begin(), temporary.end());
    temporaryBuffer.push_back('\0');
    const int fd = mkstemp(temporaryBuffer.data());
    if (fd < 0) {
        if (error != nullptr) {
            *error = "cannot create receipt temporary: " +
                std::string(strerror(errno));
        }
        return false;
    }
    temporary.assign(temporaryBuffer.data());
    if (fcntl(fd, F_SETFD, FD_CLOEXEC) != 0 ||
        fchmod(fd, 0600) != 0) {
        const int savedErrno = errno;
        close(fd);
        unlink(temporary.c_str());
        if (error != nullptr) {
            *error = "cannot secure receipt temporary: " +
                std::string(strerror(savedErrno));
        }
        return false;
    }
    const std::string encoded =
        EncodeReceiptWithoutDigest(receipt) + "\t" +
        receipt.receiptDigest + "\n";
    const bool written = WriteAll(fd, encoded) && fsync(fd) == 0;
    const int closeResult = close(fd);
    if (!written || closeResult != 0) {
        const int savedErrno = errno;
        unlink(temporary.c_str());
        if (error != nullptr) {
            *error = "cannot publish receipt: " +
                std::string(strerror(savedErrno));
        }
        return false;
    }
    if (link(temporary.c_str(), target.c_str()) != 0) {
        const int savedErrno = errno;
        unlink(temporary.c_str());
        if (savedErrno == EEXIST) {
            SigningMetadataReceiptV1 raced;
            if (Read(receiptKey, &raced, error) ==
                    SigningReceiptReadResult::FOUND &&
                SameReceipt(raced, receipt)) {
                return true;
            }
            if (error != nullptr && error->empty()) {
                *error = "concurrent receipt differs from candidate";
            }
            return false;
        }
        if (error != nullptr) {
            *error = "cannot publish immutable receipt: " +
                std::string(strerror(savedErrno));
        }
        return false;
    }
    unlink(temporary.c_str());
    const int directoryFd = open(
        root_.c_str(), O_RDONLY | O_CLOEXEC | O_DIRECTORY | O_NOFOLLOW);
    const bool durable =
        directoryFd >= 0 && fsync(directoryFd) == 0;
    if (directoryFd >= 0) close(directoryFd);
    if (!durable) {
        if (error != nullptr) *error = "cannot fsync receipt directory";
        return false;
    }
    if (error != nullptr) error->clear();
    return true;
}

SigningMetadataServiceV1::SigningMetadataServiceV1(
    SigningMetadataReceiptStore* store,
    const SigningMetadataPolicyProvider* policyProvider,
    SigningMetadataFaultInjector* faultInjector)
    : store_(store), policyProvider_(policyProvider),
      faultInjector_(faultInjector)
{
}

SigningMetadataResponseV1 SigningMetadataServiceV1::VerifyAndPersist(
    int sealedArtifactFd, const SigningMetadataRequestV1& request) const
{
    if (request.schemaVersion != 1 ||
        request.policy.schemaVersion != 1) {
        return Reject(request, SigningMetadataVerdict::UNKNOWN_SCHEMA,
            "unknown request or policy schema");
    }
    if (store_ == nullptr || policyProvider_ == nullptr ||
        faultInjector_ == nullptr ||
        sealedArtifactFd < 0 || request.requestId.empty() ||
        request.requestId.size() > kMaxRequestIdBytes ||
        request.policy.policyVersion.empty() ||
        request.policy.verifierVersion.empty() ||
        request.policy.policyVersion.size() > kMaxPolicyIdentityBytes ||
        request.policy.verifierVersion.size() > kMaxPolicyIdentityBytes ||
        request.artifactSet.schemaVersion != 1 ||
        !IsLowerHex(request.artifactSet.artifactSetDigest, 32)) {
        return Reject(request, SigningMetadataVerdict::INVALID_REQUEST,
            "invalid request envelope");
    }
    SigningMetadataPolicyV1 trustedPolicy;
    std::string policyError;
    if (!policyProvider_->Resolve(request.policy.policyVersion,
            &trustedPolicy, &policyError)) {
        return Reject(request, SigningMetadataVerdict::POLICY_NOT_FOUND,
            policyError.empty() ? "policy version is not registered" :
                policyError);
    }
    if (trustedPolicy.schemaVersion != 1 ||
        trustedPolicy.policyVersion != request.policy.policyVersion ||
        trustedPolicy.verifierVersion.empty() ||
        trustedPolicy.minimumSchemeVersion < 1 ||
        trustedPolicy.minimumSchemeVersion > 4 ||
        trustedPolicy.targetPlatformSdk == 0) {
        return Reject(request, SigningMetadataVerdict::DATA_INCONSISTENT,
            "trusted policy provider returned invalid policy");
    }
    if (request.policy.schemaVersion != trustedPolicy.schemaVersion ||
        request.policy.verifierVersion != trustedPolicy.verifierVersion ||
        request.policy.minimumSchemeVersion !=
            trustedPolicy.minimumSchemeVersion ||
        request.policy.targetPlatformSdk !=
            trustedPolicy.targetPlatformSdk) {
        return Reject(request, SigningMetadataVerdict::POLICY_MISMATCH,
            "caller policy fields differ from trusted policy snapshot");
    }
    if (trustedPolicy.minimumSchemeVersion < 1 ||
        trustedPolicy.minimumSchemeVersion > 4) {
        return Reject(request, SigningMetadataVerdict::INVALID_REQUEST,
            "minimum scheme is outside v1-v4");
    }
    if (trustedPolicy.minimumSchemeVersion == 4) {
        return Reject(request, SigningMetadataVerdict::NOT_SUPPORTED_SCHEME,
            "APK v4 requires an idsig input not present in schema v1");
    }
    if (request.artifactSet.artifacts.size() != 1 ||
        request.artifactSet.artifacts.front().role !=
            ArtifactRole::BASE) {
        return Reject(request,
            SigningMetadataVerdict::NOT_SUPPORTED_ARTIFACT_PROFILE,
            "schema v1 accepts one base APK");
    }
    const auto& artifact = request.artifactSet.artifacts.front();
    if (!IsLowerHex(artifact.sha256, 32) ||
        artifact.byteLength == 0 ||
        request.artifactSet.artifactSetDigest !=
            ComputeArtifactSetDigest(request.artifactSet)) {
        return Reject(request, SigningMetadataVerdict::DATA_INCONSISTENT,
            "artifact-set digest does not match descriptor");
    }

    struct stat before {};
    if (fstat(sealedArtifactFd, &before) != 0 ||
        !S_ISREG(before.st_mode) || before.st_size <= 0 ||
        static_cast<uint64_t>(before.st_size) != artifact.byteLength ||
        static_cast<uint64_t>(before.st_size) > kMaxArtifactBytes) {
        return Reject(request, SigningMetadataVerdict::INVALID_REQUEST,
            "sealed artifact fd identity is invalid");
    }
    std::string artifactSha256;
    uint64_t byteLength = 0;
    if (!DigestFd(sealedArtifactFd, &artifactSha256, &byteLength) ||
        byteLength != artifact.byteLength ||
        artifactSha256 != artifact.sha256) {
        return Reject(request,
            SigningMetadataVerdict::ARTIFACT_DIGEST_MISMATCH,
            "sealed fd digest differs from PackageArtifactSetV1");
    }
    if (faultInjector_->InterruptAfter(
            SigningMetadataFaultPoint::AFTER_ARTIFACT_FREEZE)) {
        return Reject(request, SigningMetadataVerdict::INTERRUPTED,
            "interrupted after artifact freeze");
    }

    const std::string receiptKey =
        ReceiptKey(trustedPolicy, artifactSha256);
    SigningMetadataReceiptV1 existing;
    std::string storeError;
    const auto existingState =
        store_->Read(receiptKey, &existing, &storeError);
    if (existingState == SigningReceiptReadResult::ERROR) {
        return Reject(request, SigningMetadataVerdict::READBACK_FAILED,
            storeError);
    }
    if (existingState == SigningReceiptReadResult::FOUND) {
        if (!ReceiptMatchesRequest(
                existing, request, trustedPolicy, artifactSha256)) {
            return Reject(request, SigningMetadataVerdict::DATA_INCONSISTENT,
                "stored receipt identity differs from request");
        }
        if (request.priorSigningFacts.has_value()) {
            ApkVerifiedIdentity current;
            for (const auto& signer : existing.signers) {
                Sha256Digest digest{};
                std::string raw;
                if (!Unhex(signer.certificateSha256, &raw) ||
                    raw.size() != digest.size()) {
                    return Reject(request,
                        SigningMetadataVerdict::DATA_INCONSISTENT,
                        "stored signer digest is malformed");
                }
                std::copy(raw.begin(), raw.end(), digest.begin());
                current.currentSignerSha256.push_back(digest);
            }
            for (const auto& lineage : existing.lineage) {
                Sha256Digest digest{};
                std::string raw;
                if (!Unhex(lineage.certificateSha256, &raw) ||
                    raw.size() != digest.size()) {
                    return Reject(request,
                        SigningMetadataVerdict::DATA_INCONSISTENT,
                        "stored lineage digest is malformed");
                }
                std::copy(raw.begin(), raw.end(), digest.begin());
                current.lineage.push_back(
                    {digest, lineage.capabilities});
            }
            std::string capabilityPath;
            if (!ContinuityAllowed(*request.priorSigningFacts, current,
                    &capabilityPath)) {
                return Reject(request,
                    SigningMetadataVerdict::UPDATE_INCOMPATIBLE,
                    "prior signer is not accepted by current lineage");
            }
            existing.continuityDecision = ContinuityDecision(
                *request.priorSigningFacts, true,
                std::move(capabilityPath), existing.receiptDigest);
        }
        return PositiveResponse(request, std::move(existing), true);
    }

    ApkVerifiedIdentity identity;
    std::string verifierError;
    if (!ApkSignatureVerifier::VerifyFd(sealedArtifactFd,
            trustedPolicy.minimumSchemeVersion,
            trustedPolicy.targetPlatformSdk, &identity,
            &verifierError)) {
        const bool lineageFailure =
            verifierError.find("proof-of-rotation") != std::string::npos ||
            verifierError.find("rotation") != std::string::npos;
        return Reject(request,
            lineageFailure ? SigningMetadataVerdict::BAD_LINEAGE :
                SigningMetadataVerdict::SIGNATURE_INVALID,
            verifierError);
    }
    if (faultInjector_->InterruptAfter(
            SigningMetadataFaultPoint::AFTER_CRYPTOGRAPHIC_VERIFY)) {
        return Reject(request, SigningMetadataVerdict::INTERRUPTED,
            "interrupted after cryptographic verify");
    }

    std::string afterDigest;
    uint64_t afterLength = 0;
    struct stat after {};
    if (!DigestFd(sealedArtifactFd, &afterDigest, &afterLength) ||
        fstat(sealedArtifactFd, &after) != 0 ||
        after.st_dev != before.st_dev || after.st_ino != before.st_ino ||
        after.st_size != before.st_size ||
        afterLength != byteLength || afterDigest != artifactSha256) {
        return Reject(request,
            SigningMetadataVerdict::ARTIFACT_CHANGED_DURING_VERIFY,
            "artifact fd changed during verification");
    }
    if (identity.currentSignerSha256.empty() ||
        identity.currentSignerSha256.size() !=
            identity.currentSignerCertificateDer.size() ||
        (identity.schemeVersion >= 2 &&
            identity.verifiedContentDigests.empty())) {
        return Reject(request, SigningMetadataVerdict::DATA_INCONSISTENT,
            "verifier omitted required signing facts");
    }

    SigningMetadataReceiptV1 receipt;
    receipt.artifactSha256 = artifactSha256;
    receipt.artifactSetDigest = request.artifactSet.artifactSetDigest;
    receipt.policyVersion = trustedPolicy.policyVersion;
    receipt.verifierVersion = trustedPolicy.verifierVersion;
    receipt.schemeVersion = identity.schemeVersion;
    for (size_t index = 0;
         index < identity.currentSignerSha256.size(); ++index) {
        const auto& der = identity.currentSignerCertificateDer[index];
        std::array<uint8_t, SHA256_DIGEST_LENGTH> digest{};
        SHA256(der.data(), der.size(), digest.data());
        if (!std::equal(digest.begin(), digest.end(),
                identity.currentSignerSha256[index].begin())) {
            return Reject(request, SigningMetadataVerdict::DATA_INCONSISTENT,
                "signer DER digest differs from verifier identity");
        }
        std::string subject;
        if (!SubjectFromDer(der, &subject)) {
            return Reject(request, SigningMetadataVerdict::DATA_INCONSISTENT,
                "signer subject cannot be decoded");
        }
        receipt.signers.push_back({
            Hex(identity.currentSignerSha256[index].data(),
                identity.currentSignerSha256[index].size()),
            std::move(subject),
        });
    }
    if (identity.schemeVersion == 1) {
        receipt.contentDigests.push_back({
            "WHOLE_ARTIFACT_SHA256_AFTER_JAR_ENTRY_VERIFICATION",
            artifactSha256,
        });
    } else {
        for (const auto& content : identity.verifiedContentDigests) {
            receipt.contentDigests.push_back({
                ContentAlgorithmName(content.signatureAlgorithmId) +
                    "_SIGALG_" +
                    std::to_string(content.signatureAlgorithmId),
                Hex(content.digest.data(), content.digest.size()),
            });
        }
    }
    std::set<Sha256Digest> uniqueLineage;
    for (const auto& lineage : identity.lineage) {
        if (!uniqueLineage.insert(lineage.sha256).second) {
            return Reject(request, SigningMetadataVerdict::BAD_LINEAGE,
                "verifier returned duplicate lineage");
        }
        receipt.lineage.push_back({
            Hex(lineage.sha256.data(), lineage.sha256.size()),
            lineage.capabilities,
        });
    }
    if (!identity.lineage.empty() &&
        identity.lineage.back().sha256 !=
            identity.currentSignerSha256.front()) {
        return Reject(request, SigningMetadataVerdict::BAD_LINEAGE,
            "lineage terminal signer differs from current signer");
    }
    receipt.lineageDigest = ComputeLineageDigest(receipt.lineage);
    std::string transcript = "Fn01.A13\n" + artifactSha256 + "\n" +
        receipt.artifactSetDigest + "\n" + receipt.policyVersion + "\n" +
        receipt.verifierVersion + "\n" +
        std::to_string(receipt.schemeVersion);
    for (const auto& signer : receipt.signers) {
        transcript += "\nS:" + signer.certificateSha256;
    }
    for (const auto& content : receipt.contentDigests) {
        transcript += "\nC:" + content.algorithm + ":" +
            content.sha256OrDigestHex;
    }
    transcript += "\nL:" + receipt.lineageDigest.value_or("-");
    receipt.verificationTranscriptSha256 = Sha256Hex(transcript);
    receipt.receiptDigest =
        Sha256Hex(EncodeReceiptWithoutDigest(receipt));

    std::optional<SigningContinuityDecisionV1> continuityDecision;
    if (request.priorSigningFacts.has_value()) {
        std::string capabilityPath;
        if (!ContinuityAllowed(*request.priorSigningFacts, identity,
                &capabilityPath)) {
            return Reject(request,
                SigningMetadataVerdict::UPDATE_INCOMPATIBLE,
                "prior signer is not accepted by current lineage");
        }
        continuityDecision = ContinuityDecision(
            *request.priorSigningFacts, true,
            std::move(capabilityPath), receipt.receiptDigest);
    }
    if (!store_->Persist(receiptKey, receipt, &storeError)) {
        return Reject(request, SigningMetadataVerdict::PERSIST_FAILED,
            storeError);
    }
    if (faultInjector_->InterruptAfter(
            SigningMetadataFaultPoint::AFTER_RECEIPT_PERSIST)) {
        return Reject(request, SigningMetadataVerdict::INTERRUPTED,
            "interrupted after receipt persist");
    }
    SigningMetadataReceiptV1 readback;
    if (store_->Read(receiptKey, &readback, &storeError) !=
            SigningReceiptReadResult::FOUND ||
        !SameReceipt(receipt, readback) ||
        !ReceiptMatchesRequest(
            readback, request, trustedPolicy, artifactSha256)) {
        return Reject(request, SigningMetadataVerdict::READBACK_FAILED,
            storeError.empty() ? "receipt readback mismatch" : storeError);
    }
    if (faultInjector_->InterruptAfter(
            SigningMetadataFaultPoint::AFTER_RECEIPT_READBACK)) {
        return Reject(request, SigningMetadataVerdict::INTERRUPTED,
            "interrupted after receipt readback");
    }
    readback.continuityDecision = std::move(continuityDecision);
    return PositiveResponse(request, std::move(readback), false);
}

const char* SigningMetadataVerdictName(SigningMetadataVerdict verdict)
{
    switch (verdict) {
        case SigningMetadataVerdict::VERIFIED: return "VERIFIED";
        case SigningMetadataVerdict::INVALID_REQUEST:
            return "INVALID_REQUEST";
        case SigningMetadataVerdict::UNKNOWN_SCHEMA:
            return "UNKNOWN_SCHEMA";
        case SigningMetadataVerdict::POLICY_NOT_FOUND:
            return "POLICY_NOT_FOUND";
        case SigningMetadataVerdict::POLICY_MISMATCH:
            return "POLICY_MISMATCH";
        case SigningMetadataVerdict::NOT_SUPPORTED_ARTIFACT_PROFILE:
            return "NOT_SUPPORTED_ARTIFACT_PROFILE";
        case SigningMetadataVerdict::NOT_SUPPORTED_SCHEME:
            return "NOT_SUPPORTED_SCHEME";
        case SigningMetadataVerdict::ARTIFACT_DIGEST_MISMATCH:
            return "ARTIFACT_DIGEST_MISMATCH";
        case SigningMetadataVerdict::ARTIFACT_CHANGED_DURING_VERIFY:
            return "ARTIFACT_CHANGED_DURING_VERIFY";
        case SigningMetadataVerdict::SIGNATURE_INVALID:
            return "SIGNATURE_INVALID";
        case SigningMetadataVerdict::BAD_LINEAGE: return "BAD_LINEAGE";
        case SigningMetadataVerdict::UPDATE_INCOMPATIBLE:
            return "UPDATE_INCOMPATIBLE";
        case SigningMetadataVerdict::PERSIST_FAILED:
            return "PERSIST_FAILED";
        case SigningMetadataVerdict::READBACK_FAILED:
            return "READBACK_FAILED";
        case SigningMetadataVerdict::DATA_INCONSISTENT:
            return "DATA_INCONSISTENT";
        case SigningMetadataVerdict::INTERRUPTED: return "INTERRUPTED";
    }
    return "DATA_INCONSISTENT";
}

std::string SerializeSigningMetadataResponseJsonV1(
    const SigningMetadataResponseV1& response)
{
    std::ostringstream output;
    output << "{\"requestId\":\"" << JsonEscape(response.requestId)
           << "\",\"verdict\":\""
           << SigningMetadataVerdictName(response.verdict)
           << "\",\"signerTruthVisible\":"
           << (response.signerTruthVisible ? "true" : "false")
           << ",\"replayed\":" << (response.replayed ? "true" : "false")
           << ",\"negativeReason\":\""
           << JsonEscape(response.negativeReason) << "\",\"receipt\":";
    if (!response.receipt.has_value()) {
        output << "null}";
        return output.str();
    }
    const auto& receipt = *response.receipt;
    output << "{\"schemaVersion\":" << receipt.schemaVersion
           << ",\"actionId\":\"" << receipt.actionId
           << "\",\"artifactSha256\":\"" << receipt.artifactSha256
           << "\",\"artifactSetDigest\":\"" << receipt.artifactSetDigest
           << "\",\"policyVersion\":\""
           << JsonEscape(receipt.policyVersion)
           << "\",\"verifierVersion\":\""
           << JsonEscape(receipt.verifierVersion)
           << "\",\"schemeVersion\":" << receipt.schemeVersion
           << ",\"signers\":[";
    for (size_t index = 0; index < receipt.signers.size(); ++index) {
        if (index != 0) output << ",";
        output << "{\"certificateSha256\":\""
               << receipt.signers[index].certificateSha256
               << "\",\"subject\":\""
               << JsonEscape(receipt.signers[index].subject) << "\"}";
    }
    output << "],\"contentDigests\":[";
    for (size_t index = 0; index < receipt.contentDigests.size();
         ++index) {
        if (index != 0) output << ",";
        output << "{\"algorithm\":\""
               << JsonEscape(receipt.contentDigests[index].algorithm)
               << "\",\"digest\":\""
               << receipt.contentDigests[index].sha256OrDigestHex
               << "\"}";
    }
    output << "],\"lineage\":[";
    for (size_t index = 0; index < receipt.lineage.size(); ++index) {
        if (index != 0) output << ",";
        output << "{\"certificateSha256\":\""
               << receipt.lineage[index].certificateSha256
               << "\",\"capabilities\":"
               << receipt.lineage[index].capabilities << "}";
    }
    output << "],\"lineageDigest\":";
    if (receipt.lineageDigest.has_value()) {
        output << "\"" << *receipt.lineageDigest << "\"";
    } else {
        output << "null";
    }
    output << ",\"verificationTranscriptSha256\":\""
           << receipt.verificationTranscriptSha256
           << "\",\"receiptDigest\":\"" << receipt.receiptDigest
           << "\",\"continuityDecision\":";
    if (!receipt.continuityDecision.has_value()) {
        output << "null";
    } else {
        const auto& continuity = *receipt.continuityDecision;
        output << "{\"priorSigningFactsDigest\":\""
               << continuity.priorSigningFactsDigest
               << "\",\"allowed\":"
               << (continuity.allowed ? "true" : "false")
               << ",\"capabilityPath\":\""
               << JsonEscape(continuity.capabilityPath)
               << "\",\"decisionDigest\":\""
               << continuity.decisionDigest << "\"}";
    }
    output << "}}";
    return output.str();
}

}  // namespace oh_adapter::signing_metadata
