#include "package_list_v1.h"

#include "sha256.h"

#include <algorithm>
#include <array>
#include <cstring>
#include <limits>
#include <set>
#include <utility>

namespace oh_adapter::package_list {
namespace {

constexpr uint32_t kPrimaryUserId = 0;
constexpr size_t kSha256Bytes = 32;
constexpr size_t kHmacBlockBytes = 64;
constexpr size_t kMinimumSigningKeyBytes = 16;
constexpr size_t kMaximumEpochBytes = 128;
constexpr size_t kMaximumRequestIdBytes = 256;
constexpr size_t kMaximumCallerIdentityBytes = 512;
constexpr char kTokenPrefix[] = "PT1.";

std::string Hex(const uint8_t* bytes, size_t size)
{
    static constexpr char kDigits[] = "0123456789abcdef";
    std::string result;
    result.reserve(size * 2);
    for (size_t i = 0; i < size; ++i) {
        result.push_back(kDigits[(bytes[i] >> 4) & 0x0f]);
        result.push_back(kDigits[bytes[i] & 0x0f]);
    }
    return result;
}

bool HexDigit(char value, uint8_t* result)
{
    if (value >= '0' && value <= '9') {
        *result = static_cast<uint8_t>(value - '0');
        return true;
    }
    if (value >= 'a' && value <= 'f') {
        *result = static_cast<uint8_t>(value - 'a' + 10);
        return true;
    }
    return false;
}

bool Unhex(const std::string& value, std::vector<uint8_t>* bytes)
{
    if (value.empty() || value.size() % 2 != 0) return false;
    bytes->clear();
    bytes->reserve(value.size() / 2);
    for (size_t i = 0; i < value.size(); i += 2) {
        uint8_t high = 0;
        uint8_t low = 0;
        if (!HexDigit(value[i], &high) || !HexDigit(value[i + 1], &low)) {
            bytes->clear();
            return false;
        }
        bytes->push_back(static_cast<uint8_t>((high << 4) | low));
    }
    return true;
}

std::array<uint8_t, kSha256Bytes> Digest(const uint8_t* bytes, size_t size)
{
    std::array<uint8_t, kSha256Bytes> result {};
    sha256(bytes, size, result.data());
    return result;
}

std::array<uint8_t, kSha256Bytes> HmacSha256(
    const std::vector<uint8_t>& key, const std::string& message)
{
    std::array<uint8_t, kHmacBlockBytes> normalized {};
    if (key.size() > normalized.size()) {
        const auto digest = Digest(key.data(), key.size());
        std::copy(digest.begin(), digest.end(), normalized.begin());
    } else {
        std::copy(key.begin(), key.end(), normalized.begin());
    }

    std::array<uint8_t, kHmacBlockBytes> innerPad {};
    std::array<uint8_t, kHmacBlockBytes> outerPad {};
    for (size_t i = 0; i < normalized.size(); ++i) {
        innerPad[i] = static_cast<uint8_t>(normalized[i] ^ 0x36);
        outerPad[i] = static_cast<uint8_t>(normalized[i] ^ 0x5c);
    }

    std::vector<uint8_t> inner;
    inner.reserve(innerPad.size() + message.size());
    inner.insert(inner.end(), innerPad.begin(), innerPad.end());
    inner.insert(inner.end(), message.begin(), message.end());
    const auto innerDigest = Digest(inner.data(), inner.size());

    std::vector<uint8_t> outer;
    outer.reserve(outerPad.size() + innerDigest.size());
    outer.insert(outer.end(), outerPad.begin(), outerPad.end());
    outer.insert(outer.end(), innerDigest.begin(), innerDigest.end());
    return Digest(outer.data(), outer.size());
}

bool ConstantTimeEqual(const std::string& first, const std::string& second)
{
    if (first.size() != second.size()) return false;
    uint8_t difference = 0;
    for (size_t i = 0; i < first.size(); ++i) {
        difference |= static_cast<uint8_t>(first[i] ^ second[i]);
    }
    return difference == 0;
}

std::string EncodeEpochPayload(
    const std::string& epoch, const std::vector<uint8_t>& nonce)
{
    std::vector<uint8_t> payload;
    payload.reserve(2 + epoch.size() + nonce.size());
    payload.push_back(static_cast<uint8_t>((epoch.size() >> 8) & 0xff));
    payload.push_back(static_cast<uint8_t>(epoch.size() & 0xff));
    payload.insert(payload.end(), epoch.begin(), epoch.end());
    payload.insert(payload.end(), nonce.begin(), nonce.end());
    return Hex(payload.data(), payload.size());
}

bool DecodeEpochPayload(const std::string& payloadHex, std::string* epoch)
{
    std::vector<uint8_t> payload;
    if (!Unhex(payloadHex, &payload) || payload.size() < 3) return false;
    const size_t epochSize =
        (static_cast<size_t>(payload[0]) << 8) | payload[1];
    if (epochSize == 0 || epochSize > kMaximumEpochBytes ||
        payload.size() <= 2 + epochSize) {
        return false;
    }
    *epoch = std::string(
        reinterpret_cast<const char*>(payload.data() + 2), epochSize);
    return true;
}

ListPackagesResponseV1 MakeResponse(const ListPackagesRequestV1& request,
    PackageListVerdict verdict, const char* reason)
{
    ListPackagesResponseV1 response;
    response.requestId = request.requestId;
    response.verdict = verdict;
    response.reason = reason;
    return response;
}

bool IsVisible(const package_query::CallerContextV1& caller,
    const std::string& packageName)
{
    if (caller.canSeeAllPackages) return true;
    return std::find(caller.visiblePackageNames.begin(),
               caller.visiblePackageNames.end(),
               packageName) != caller.visiblePackageNames.end();
}

bool FilterMatches(
    const PackageListFilterV1& filter, const std::string& packageName)
{
    if (filter.kind == PackageListFilterKind::ALL) return true;
    if (filter.kind == PackageListFilterKind::PACKAGE_NAME_PREFIX) {
        return packageName.compare(0, filter.value.size(), filter.value) == 0;
    }
    return false;
}

bool SameCaller(const package_query::CallerContextV1& first,
    const package_query::CallerContextV1& second)
{
    return first.callerId == second.callerId &&
        first.visibilityScopeDigest == second.visibilityScopeDigest;
}

bool SameFilter(
    const PackageListFilterV1& first, const PackageListFilterV1& second)
{
    return first.kind == second.kind && first.value == second.value;
}

bool IsSupportedFilter(const PackageListFilterV1& filter)
{
    if (filter.kind == PackageListFilterKind::ALL) {
        return filter.value.empty();
    }
    if (filter.kind == PackageListFilterKind::PACKAGE_NAME_PREFIX) {
        return !filter.value.empty();
    }
    return false;
}

void AppendField(std::string* output, const std::string& value)
{
    *output += std::to_string(value.size());
    output->push_back(':');
    output->append(value);
    output->push_back(';');
}

std::string RequestIdentity(const ListPackagesRequestV1& request)
{
    std::string identity;
    AppendField(&identity, request.caller.callerId);
    AppendField(&identity, request.requestId);
    return identity;
}

std::string RequestFingerprint(const ListPackagesRequestV1& request)
{
    std::string canonical;
    canonical.reserve(256);
    AppendField(&canonical, std::to_string(request.schemaVersion));
    AppendField(&canonical, request.requestId);
    AppendField(&canonical, std::to_string(request.userId));
    AppendField(&canonical, std::to_string(request.pageSize));
    AppendField(
        &canonical, std::to_string(static_cast<int>(request.filter.kind)));
    AppendField(&canonical, request.filter.value);
    AppendField(&canonical, request.caller.callerId);
    AppendField(&canonical, request.caller.visibilityScopeDigest);
    AppendField(
        &canonical, request.caller.canSeeAllPackages ? "true" : "false");
    for (const auto& packageName :
         request.caller.visiblePackageNames) {
        AppendField(&canonical, packageName);
    }
    AppendField(&canonical,
        request.pageToken.has_value() ? *request.pageToken : "");
    const auto digest = Digest(
        reinterpret_cast<const uint8_t*>(canonical.data()),
        canonical.size());
    return Hex(digest.data(), digest.size());
}

}  // namespace

struct StablePackageListService::SnapshotState {
    std::string sourceSnapshotId;
    uint64_t catalogRevision = 0;
    uint64_t totalCount = 0;
    uint32_t pageSize = 0;
    uint32_t userId = 0;
    uint64_t expiresAtMillis = 0;
    PackageListFilterV1 filter;
    package_query::CallerContextV1 caller;
};

struct StablePackageListService::TokenState {
    std::string snapshotId;
    uint64_t cursor = 0;
    std::optional<std::string> nextToken;
};

struct StablePackageListService::RequestReplayState {
    std::string fingerprint;
    ListPackagesResponseV1 response;
    uint64_t expiresAtMillis = 0;
};

StablePackageListService::StablePackageListService(
    PackageCatalogSnapshotSource* source, PackageListClock* clock,
    PackageListEntropy* entropy, PackageListFaultInjector* faultInjector,
    PackageListLimitsV1 limits, std::vector<uint8_t> tokenSigningKey,
    std::string processEpoch)
    : source_(source),
      clock_(clock),
      entropy_(entropy),
      faultInjector_(faultInjector),
      limits_(limits),
      tokenSigningKey_(std::move(tokenSigningKey)),
      processEpoch_(std::move(processEpoch))
{
}

StablePackageListService::~StablePackageListService()
{
    if (source_ == nullptr) return;
    for (const auto& item : snapshots_) {
        source_->Release(item.second.sourceSnapshotId);
    }
}

ListPackagesResponseV1 StablePackageListService::ListPackages(
    const ListPackagesRequestV1& request)
{
    std::lock_guard<std::mutex> lock(mutex_);
    if (source_ == nullptr || clock_ == nullptr || entropy_ == nullptr ||
        faultInjector_ == nullptr || limits_.maxPageSize == 0 ||
        limits_.maxFilterBytes == 0 || limits_.maxTokenBytes == 0 ||
        limits_.tokenEntropyBytes == 0 || limits_.tokenTtlMillis == 0 ||
        limits_.maxCatalogEntries == 0 ||
        limits_.maxActiveSnapshotsPerCaller == 0 ||
        tokenSigningKey_.size() < kMinimumSigningKeyBytes ||
        processEpoch_.empty() || processEpoch_.size() > kMaximumEpochBytes ||
        request.schemaVersion != 1 || request.requestId.empty() ||
        request.requestId.size() > kMaximumRequestIdBytes ||
        request.caller.callerId.empty() ||
        request.caller.callerId.size() > kMaximumCallerIdentityBytes ||
        request.caller.visibilityScopeDigest.empty() ||
        request.caller.visibilityScopeDigest.size() >
            kMaximumCallerIdentityBytes) {
        return MakeResponse(
            request, PackageListVerdict::INVALID_REQUEST, "INVALID_REQUEST");
    }
    if (request.userId != kPrimaryUserId) {
        return MakeResponse(
            request, PackageListVerdict::NOT_SUPPORTED, "USER_NOT_SUPPORTED");
    }
    if (request.pageSize == 0 ||
        request.pageSize > limits_.maxPageSize) {
        return MakeResponse(request, PackageListVerdict::NOT_SUPPORTED,
            "PAGE_SIZE_NOT_SUPPORTED");
    }
    if (request.filter.value.size() > limits_.maxFilterBytes ||
        !IsSupportedFilter(request.filter)) {
        return MakeResponse(request, PackageListVerdict::NOT_SUPPORTED,
            "FILTER_NOT_SUPPORTED");
    }

    const uint64_t nowMillis = clock_->NowMillis();
    for (auto item = requestReplays_.begin();
         item != requestReplays_.end();) {
        if (nowMillis > item->second.expiresAtMillis) {
            item = requestReplays_.erase(item);
        } else {
            ++item;
        }
    }
    for (auto item = snapshots_.begin(); item != snapshots_.end();) {
        if (nowMillis <= item->second.expiresAtMillis) {
            ++item;
            continue;
        }
        const std::string expiredSnapshotId = item->first;
        source_->Release(item->second.sourceSnapshotId);
        item = snapshots_.erase(item);
        for (auto token = tokens_.begin(); token != tokens_.end();) {
            if (token->second.snapshotId == expiredSnapshotId) {
                token = tokens_.erase(token);
            } else {
                ++token;
            }
        }
    }

    const std::string requestIdentity = RequestIdentity(request);
    const std::string requestFingerprint = RequestFingerprint(request);
    auto replay = requestReplays_.find(requestIdentity);
    if (replay != requestReplays_.end()) {
        if (replay->second.fingerprint != requestFingerprint) {
            return MakeResponse(request,
                PackageListVerdict::INVALID_REQUEST,
                "IDEMPOTENCY_CONFLICT");
        }
        if (clock_->NowMillis() <= replay->second.expiresAtMillis) {
            return replay->second.response;
        }
        requestReplays_.erase(replay);
    }

    auto makeToken = [&](std::string* token, std::string* error) -> bool {
        std::vector<uint8_t> nonce(limits_.tokenEntropyBytes);
        if (!entropy_->Fill(nonce.data(), nonce.size(), error)) return false;
        const std::string payload =
            EncodeEpochPayload(processEpoch_, nonce);
        const std::string unsignedToken =
            std::string(kTokenPrefix) + payload;
        const auto mac = HmacSha256(tokenSigningKey_, unsignedToken);
        *token = unsignedToken + "." + Hex(mac.data(), mac.size());
        if (token->size() > limits_.maxTokenBytes) {
            if (error != nullptr) *error = "TOKEN_LIMIT_EXCEEDED";
            token->clear();
            return false;
        }
        return true;
    };

    auto validateToken =
        [&](const std::string& token, std::string* epoch) -> bool {
        if (token.size() > limits_.maxTokenBytes ||
            token.compare(0, std::strlen(kTokenPrefix), kTokenPrefix) != 0) {
            return false;
        }
        const size_t separator = token.find(
            '.', std::strlen(kTokenPrefix));
        if (separator == std::string::npos ||
            separator + 1 + kSha256Bytes * 2 != token.size()) {
            return false;
        }
        const std::string unsignedToken = token.substr(0, separator);
        const std::string suppliedMac = token.substr(separator + 1);
        const auto expectedMac =
            HmacSha256(tokenSigningKey_, unsignedToken);
        if (!ConstantTimeEqual(
                suppliedMac, Hex(expectedMac.data(), expectedMac.size()))) {
            return false;
        }
        return DecodeEpochPayload(
            unsignedToken.substr(std::strlen(kTokenPrefix)), epoch);
    };

    auto readVisibleEntries = [&](const SnapshotState& state,
                                  std::vector<package_query::
                                      PackageManagementSnapshotV1>* visible,
                                  PackageCatalogFailure* failure)
        -> bool {
        std::vector<package_query::PackageManagementSnapshotV1> entries;
        std::string error;
        *failure = PackageCatalogFailure::NONE;
        if (!source_->Read(
                state.sourceSnapshotId, &entries, failure, &error)) {
            return false;
        }
        if (entries.size() > limits_.maxCatalogEntries) {
            *failure = PackageCatalogFailure::LIMIT_EXCEEDED;
            return false;
        }
        std::set<std::string> identities;
        visible->clear();
        for (const auto& entry : entries) {
            if (entry.packageName.empty() || entry.userId != state.userId ||
                entry.generation == 0 || entry.canonicalDigest.empty()) {
                *failure = PackageCatalogFailure::DATA_INCONSISTENT;
                visible->clear();
                return false;
            }
            if (!identities.insert(entry.packageName).second) {
                *failure = PackageCatalogFailure::DATA_INCONSISTENT;
                visible->clear();
                return false;
            }
            if (entry.lifecycle == "REMOVING") continue;
            if (entry.lifecycle != "ACTIVE" ||
                entry.userState != "INSTALLED" ||
                entry.readiness != "READY") {
                *failure = PackageCatalogFailure::DATA_INCONSISTENT;
                visible->clear();
                return false;
            }
            if (IsVisible(state.caller, entry.packageName) &&
                FilterMatches(state.filter, entry.packageName)) {
                visible->push_back(entry);
            }
        }
        std::sort(visible->begin(), visible->end(),
            [](const auto& first, const auto& second) {
                return first.packageName < second.packageName;
            });
        return true;
    };

    std::string snapshotId;
    uint64_t cursor = 0;
    std::string incomingToken;
    const bool firstPage = !request.pageToken.has_value();
    if (!firstPage && request.pageToken->empty()) {
        return MakeResponse(request,
            PackageListVerdict::INVALID_PAGE_TOKEN,
            "INVALID_PAGE_TOKEN");
    }

    if (firstPage) {
        const size_t activeForCaller =
            static_cast<size_t>(std::count_if(
                snapshots_.begin(), snapshots_.end(),
                [&](const auto& item) {
                    return SameCaller(
                        item.second.caller, request.caller);
                }));
        if (activeForCaller >=
            limits_.maxActiveSnapshotsPerCaller) {
            return MakeResponse(request,
                PackageListVerdict::NOT_SUPPORTED,
                "ACTIVE_SNAPSHOT_LIMIT_EXCEEDED");
        }
        SnapshotState state;
        state.userId = request.userId;
        state.pageSize = request.pageSize;
        state.filter = request.filter;
        state.caller = request.caller;
        std::string error;
        PackageCatalogFailure captureFailure = PackageCatalogFailure::NONE;
        if (!source_->Capture(request.userId, &state.sourceSnapshotId,
                &state.catalogRevision, &captureFailure, &error) ||
            state.sourceSnapshotId.empty() || state.catalogRevision == 0) {
            return MakeResponse(request,
                captureFailure == PackageCatalogFailure::DATA_INCONSISTENT
                    ? PackageListVerdict::DATA_INCONSISTENT
                    : PackageListVerdict::CATALOG_READ_FAILED,
                "CATALOG_CAPTURE_FAILED");
        }
        if (faultInjector_->InterruptAfter(
                PackageListPhase::CATALOG_CAPTURED)) {
            source_->Release(state.sourceSnapshotId);
            return MakeResponse(request,
                PackageListVerdict::INTERRUPTED_RETRY,
                "CATALOG_CAPTURE_INTERRUPTED");
        }

        std::vector<package_query::PackageManagementSnapshotV1> visible;
        PackageCatalogFailure readFailure = PackageCatalogFailure::NONE;
        if (!readVisibleEntries(state, &visible, &readFailure)) {
            source_->Release(state.sourceSnapshotId);
            return MakeResponse(request,
                readFailure == PackageCatalogFailure::COMPACTED
                    ? PackageListVerdict::CATALOG_COMPACTED
                    : readFailure ==
                            PackageCatalogFailure::LIMIT_EXCEEDED
                        ? PackageListVerdict::NOT_SUPPORTED
                    : readFailure ==
                            PackageCatalogFailure::DATA_INCONSISTENT
                        ? PackageListVerdict::DATA_INCONSISTENT
                        : PackageListVerdict::CATALOG_READ_FAILED,
                readFailure == PackageCatalogFailure::COMPACTED
                    ? "CATALOG_SNAPSHOT_UNAVAILABLE"
                    : readFailure ==
                            PackageCatalogFailure::LIMIT_EXCEEDED
                        ? "CATALOG_SIZE_NOT_SUPPORTED"
                    : "CATALOG_READ_FAILED");
        }
        state.totalCount = visible.size();
        if (faultInjector_->InterruptAfter(
                PackageListPhase::SNAPSHOT_FILTERED)) {
            source_->Release(state.sourceSnapshotId);
            return MakeResponse(request,
                PackageListVerdict::INTERRUPTED_RETRY,
                "SNAPSHOT_FILTER_INTERRUPTED");
        }
        if (clock_->NowMillis() >
            std::numeric_limits<uint64_t>::max() -
                limits_.tokenTtlMillis) {
            source_->Release(state.sourceSnapshotId);
            return MakeResponse(request,
                PackageListVerdict::DATA_INCONSISTENT,
                "TOKEN_EXPIRY_OVERFLOW");
        }
        state.expiresAtMillis =
            clock_->NowMillis() + limits_.tokenTtlMillis;

        std::string snapshotToken;
        if (!makeToken(&snapshotToken, &error)) {
            source_->Release(state.sourceSnapshotId);
            return MakeResponse(request,
                PackageListVerdict::TOKEN_STORE_FAILED,
                "TOKEN_ENTROPY_FAILED");
        }
        const auto publicDigest = Digest(
            reinterpret_cast<const uint8_t*>(snapshotToken.data()),
            snapshotToken.size());
        snapshotId = "S1-" + Hex(publicDigest.data(), publicDigest.size());
        snapshots_.emplace(snapshotId, std::move(state));
    } else {
        const std::string& token = *request.pageToken;
        incomingToken = token;
        std::string tokenEpoch;
        if (!validateToken(token, &tokenEpoch)) {
            return MakeResponse(request,
                PackageListVerdict::INVALID_PAGE_TOKEN,
                "INVALID_PAGE_TOKEN");
        }
        if (tokenEpoch != processEpoch_) {
            return MakeResponse(request,
                PackageListVerdict::PAGE_TOKEN_EXPIRED,
                "PAGE_TOKEN_EXPIRED");
        }
        const auto tokenIt = tokens_.find(token);
        if (tokenIt == tokens_.end()) {
            return MakeResponse(request,
                PackageListVerdict::PAGE_TOKEN_EXPIRED,
                "PAGE_TOKEN_EXPIRED");
        }
        snapshotId = tokenIt->second.snapshotId;
        cursor = tokenIt->second.cursor;
        const auto snapshotIt = snapshots_.find(snapshotId);
        if (snapshotIt == snapshots_.end() ||
            clock_->NowMillis() > snapshotIt->second.expiresAtMillis) {
            return MakeResponse(request,
                PackageListVerdict::PAGE_TOKEN_EXPIRED,
                "PAGE_TOKEN_EXPIRED");
        }
        const SnapshotState& state = snapshotIt->second;
        if (state.userId != request.userId ||
            !SameCaller(state.caller, request.caller)) {
            return MakeResponse(request,
                PackageListVerdict::PAGE_TOKEN_CALLER_MISMATCH,
                "PAGE_TOKEN_CALLER_MISMATCH");
        }
        if (state.pageSize != request.pageSize ||
            !SameFilter(state.filter, request.filter)) {
            return MakeResponse(request,
                PackageListVerdict::PAGE_TOKEN_CONTEXT_MISMATCH,
                "PAGE_TOKEN_CONTEXT_MISMATCH");
        }
    }

    auto snapshotIt = snapshots_.find(snapshotId);
    if (snapshotIt == snapshots_.end()) {
        return MakeResponse(request,
            PackageListVerdict::TOKEN_STORE_FAILED,
            "SNAPSHOT_STATE_MISSING");
    }
    SnapshotState& state = snapshotIt->second;
    std::vector<package_query::PackageManagementSnapshotV1> visible;
    PackageCatalogFailure readFailure = PackageCatalogFailure::NONE;
    if (!readVisibleEntries(state, &visible, &readFailure)) {
        return MakeResponse(request,
            readFailure == PackageCatalogFailure::COMPACTED
                ? PackageListVerdict::CATALOG_COMPACTED
                : readFailure == PackageCatalogFailure::LIMIT_EXCEEDED
                    ? PackageListVerdict::NOT_SUPPORTED
                : readFailure == PackageCatalogFailure::DATA_INCONSISTENT
                    ? PackageListVerdict::DATA_INCONSISTENT
                    : PackageListVerdict::CATALOG_READ_FAILED,
            readFailure == PackageCatalogFailure::COMPACTED
                ? "CATALOG_SNAPSHOT_UNAVAILABLE"
                : readFailure == PackageCatalogFailure::LIMIT_EXCEEDED
                    ? "CATALOG_SIZE_NOT_SUPPORTED"
                : "CATALOG_READ_FAILED");
    }
    if (visible.size() != state.totalCount || cursor > visible.size()) {
        return MakeResponse(request,
            PackageListVerdict::DATA_INCONSISTENT,
            "SNAPSHOT_CONTENT_CHANGED");
    }

    ListPackagesResponseV1 response =
        MakeResponse(request, PackageListVerdict::READY, "READY");
    response.snapshotId = snapshotId;
    response.catalogRevision = state.catalogRevision;
    response.totalCount = state.totalCount;
    const uint64_t pageEnd = std::min<uint64_t>(
        visible.size(), cursor + state.pageSize);
    response.entries.insert(response.entries.end(),
        visible.begin() + static_cast<std::ptrdiff_t>(cursor),
        visible.begin() + static_cast<std::ptrdiff_t>(pageEnd));
    response.pageEntryCount =
        static_cast<uint32_t>(response.entries.size());

    if (pageEnd < visible.size()) {
        std::string token;
        std::string error;
        if (!firstPage) {
            const auto incoming = tokens_.find(incomingToken);
            if (incoming != tokens_.end() &&
                incoming->second.nextToken.has_value()) {
                token = *incoming->second.nextToken;
            }
        }
        if ((token.empty() && !makeToken(&token, &error)) ||
            faultInjector_->InterruptAfter(
                PackageListPhase::TOKEN_STORED)) {
            response.entries.clear();
            response.pageEntryCount = 0;
            response.verdict = PackageListVerdict::TOKEN_STORE_FAILED;
            response.reason = "TOKEN_STORE_FAILED";
            if (firstPage) {
                source_->Release(state.sourceSnapshotId);
                snapshots_.erase(snapshotId);
            }
            return response;
        }
        if (tokens_.find(token) == tokens_.end()) {
            tokens_[token] =
                TokenState { snapshotId, pageEnd, std::nullopt };
        }
        if (!firstPage) {
            auto incoming = tokens_.find(incomingToken);
            if (incoming != tokens_.end()) {
                incoming->second.nextToken = token;
            }
        }
        response.nextPageToken = std::move(token);
    }

    if (faultInjector_->InterruptAfter(
            PackageListPhase::RESPONSE_SERIALIZED)) {
        response.entries.clear();
        response.pageEntryCount = 0;
        response.nextPageToken.reset();
        response.verdict = PackageListVerdict::INTERRUPTED_RETRY;
        response.reason = "RESPONSE_SERIALIZATION_INTERRUPTED";
        if (firstPage) {
            for (auto token = tokens_.begin(); token != tokens_.end();) {
                if (token->second.snapshotId == snapshotId) {
                    token = tokens_.erase(token);
                } else {
                    ++token;
                }
            }
            source_->Release(state.sourceSnapshotId);
            snapshots_.erase(snapshotId);
        }
        return response;
    }
    requestReplays_[requestIdentity] = RequestReplayState {
        requestFingerprint, response, state.expiresAtMillis };
    return response;
}

const char* PackageListVerdictName(PackageListVerdict verdict)
{
    switch (verdict) {
        case PackageListVerdict::READY: return "READY";
        case PackageListVerdict::INVALID_REQUEST: return "INVALID_REQUEST";
        case PackageListVerdict::NOT_SUPPORTED: return "NOT_SUPPORTED";
        case PackageListVerdict::INVALID_PAGE_TOKEN:
            return "INVALID_PAGE_TOKEN";
        case PackageListVerdict::PAGE_TOKEN_CALLER_MISMATCH:
            return "PAGE_TOKEN_CALLER_MISMATCH";
        case PackageListVerdict::PAGE_TOKEN_CONTEXT_MISMATCH:
            return "PAGE_TOKEN_CONTEXT_MISMATCH";
        case PackageListVerdict::PAGE_TOKEN_EXPIRED:
            return "PAGE_TOKEN_EXPIRED";
        case PackageListVerdict::CATALOG_COMPACTED:
            return "CATALOG_COMPACTED";
        case PackageListVerdict::CATALOG_READ_FAILED:
            return "CATALOG_READ_FAILED";
        case PackageListVerdict::TOKEN_STORE_FAILED:
            return "TOKEN_STORE_FAILED";
        case PackageListVerdict::DATA_INCONSISTENT:
            return "DATA_INCONSISTENT";
        case PackageListVerdict::INTERRUPTED_RETRY:
            return "INTERRUPTED_RETRY";
    }
    return "DATA_INCONSISTENT";
}

}  // namespace oh_adapter::package_list
