#ifndef OH_ADAPTER_PACKAGE_LIST_V1_H
#define OH_ADAPTER_PACKAGE_LIST_V1_H

#include "package_query_v1.h"

#include <cstdint>
#include <map>
#include <mutex>
#include <optional>
#include <string>
#include <vector>

namespace oh_adapter::package_list {

enum class PackageListFilterKind {
    ALL = 0,
    PACKAGE_NAME_PREFIX = 1,
};

enum class PackageListVerdict {
    READY,
    INVALID_REQUEST,
    NOT_SUPPORTED,
    INVALID_PAGE_TOKEN,
    PAGE_TOKEN_CALLER_MISMATCH,
    PAGE_TOKEN_CONTEXT_MISMATCH,
    PAGE_TOKEN_EXPIRED,
    CATALOG_COMPACTED,
    CATALOG_READ_FAILED,
    TOKEN_STORE_FAILED,
    DATA_INCONSISTENT,
    INTERRUPTED_RETRY,
};

enum class PackageCatalogFailure {
    NONE,
    COMPACTED,
    IO_ERROR,
    DATA_INCONSISTENT,
    LIMIT_EXCEEDED,
};

enum class PackageListPhase {
    CATALOG_CAPTURED,
    SNAPSHOT_FILTERED,
    TOKEN_STORED,
    RESPONSE_SERIALIZED,
};

struct PackageListFilterV1 {
    PackageListFilterKind kind = PackageListFilterKind::ALL;
    std::string value;
};

struct ListPackagesRequestV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    uint32_t userId = 0;
    uint32_t pageSize = 0;
    PackageListFilterV1 filter;
    package_query::CallerContextV1 caller;
    std::optional<std::string> pageToken;
};

struct ListPackagesResponseV1 {
    std::string requestId;
    PackageListVerdict verdict = PackageListVerdict::DATA_INCONSISTENT;
    std::string reason;
    std::string snapshotId;
    uint64_t catalogRevision = 0;
    uint64_t totalCount = 0;
    uint32_t pageEntryCount = 0;
    std::vector<package_query::PackageManagementSnapshotV1> entries;
    std::optional<std::string> nextPageToken;
};

struct PackageListLimitsV1 {
    uint32_t maxPageSize = 0;
    uint32_t maxFilterBytes = 0;
    uint32_t maxTokenBytes = 0;
    uint32_t tokenEntropyBytes = 0;
    uint32_t maxCatalogEntries = 0;
    uint32_t maxActiveSnapshotsPerCaller = 0;
    uint64_t tokenTtlMillis = 0;
};

class PackageCatalogSnapshotSource {
public:
    virtual ~PackageCatalogSnapshotSource() = default;

    // Captures one immutable catalog revision and retains it until Release.
    virtual bool Capture(uint32_t userId, std::string* sourceSnapshotId,
        uint64_t* catalogRevision, PackageCatalogFailure* failure,
        std::string* error) = 0;
    virtual bool Read(const std::string& sourceSnapshotId,
        std::vector<package_query::PackageManagementSnapshotV1>* entries,
        PackageCatalogFailure* failure, std::string* error) const = 0;
    virtual void Release(const std::string& sourceSnapshotId) = 0;
};

class PackageListClock {
public:
    virtual ~PackageListClock() = default;
    virtual uint64_t NowMillis() const = 0;
};

class PackageListEntropy {
public:
    virtual ~PackageListEntropy() = default;
    virtual bool Fill(uint8_t* bytes, size_t size, std::string* error) = 0;
};

class PackageListFaultInjector {
public:
    virtual ~PackageListFaultInjector() = default;
    virtual bool InterruptAfter(PackageListPhase phase) = 0;
};

class NoPackageListFaultInjector final : public PackageListFaultInjector {
public:
    bool InterruptAfter(PackageListPhase) override
    {
        return false;
    }
};

class StablePackageListService {
public:
    StablePackageListService(PackageCatalogSnapshotSource* source,
        PackageListClock* clock, PackageListEntropy* entropy,
        PackageListFaultInjector* faultInjector,
        PackageListLimitsV1 limits, std::vector<uint8_t> tokenSigningKey,
        std::string processEpoch);
    ~StablePackageListService();

    StablePackageListService(const StablePackageListService&) = delete;
    StablePackageListService& operator=(const StablePackageListService&) =
        delete;

    ListPackagesResponseV1 ListPackages(
        const ListPackagesRequestV1& request);

private:
    struct SnapshotState;
    struct TokenState;
    struct RequestReplayState;

    PackageCatalogSnapshotSource* source_;
    PackageListClock* clock_;
    PackageListEntropy* entropy_;
    PackageListFaultInjector* faultInjector_;
    PackageListLimitsV1 limits_;
    std::vector<uint8_t> tokenSigningKey_;
    std::string processEpoch_;
    std::map<std::string, SnapshotState> snapshots_;
    std::map<std::string, TokenState> tokens_;
    std::map<std::string, RequestReplayState> requestReplays_;
    std::mutex mutex_;
};

const char* PackageListVerdictName(PackageListVerdict verdict);

}  // namespace oh_adapter::package_list

#endif  // OH_ADAPTER_PACKAGE_LIST_V1_H
