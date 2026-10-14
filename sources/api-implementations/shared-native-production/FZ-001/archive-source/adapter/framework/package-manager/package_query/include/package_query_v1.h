#ifndef OH_ADAPTER_PACKAGE_QUERY_V1_H
#define OH_ADAPTER_PACKAGE_QUERY_V1_H

#include "package_transaction_v1.h"

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace oh_adapter::package_query {

enum class PackageQueryVerdict {
    READY,
    INVALID_REQUEST,
    NOT_SUPPORTED,
    PACKAGE_NOT_FOUND,
    PACKAGE_NOT_VISIBLE,
    PACKAGE_REMOVING,
    PACKAGE_NOT_READY,
    DATA_INCONSISTENT,
};

enum class QueryPhase {
    SNAPSHOT_FROZEN,
    VISIBILITY_CHECKED,
    RESPONSE_SERIALIZED,
};

struct CallerContextV1 {
    std::string callerId;
    std::string visibilityScopeDigest;
    bool canSeeAllPackages = false;
    std::vector<std::string> visiblePackageNames;
};

struct GetPackageRequestV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    std::string packageName;
    uint32_t userId = 0;
    uint32_t flags = 0;
    CallerContextV1 caller;
    std::optional<uint64_t> expectedGeneration;
    std::optional<std::string> expectedCanonicalDigest;
};

struct PackageManagementSnapshotV1 {
    std::string packageName;
    uint32_t userId = 0;
    std::string userState;
    std::string lifecycle;
    uint64_t generation = 0;
    std::string canonicalDigest;
    std::string readiness;
};

struct GetPackageResponseV1 {
    std::string requestId;
    PackageQueryVerdict verdict = PackageQueryVerdict::DATA_INCONSISTENT;
    std::string reason;
    uint64_t catalogRevision = 0;
    std::optional<PackageManagementSnapshotV1> package;
};

class QueryFaultInjector {
public:
    virtual ~QueryFaultInjector() = default;
    virtual bool InterruptAfter(QueryPhase phase) = 0;
};

class NoQueryFaultInjector final : public QueryFaultInjector {
public:
    bool InterruptAfter(QueryPhase) override
    {
        return false;
    }
};

class PackageQueryService {
public:
    PackageQueryService(
        package_transaction::FilePackageStore* store,
        QueryFaultInjector* faultInjector);

    GetPackageResponseV1 GetPackage(const GetPackageRequestV1& request) const;

private:
    package_transaction::FilePackageStore* store_;
    QueryFaultInjector* faultInjector_;
};

const char* PackageQueryVerdictName(PackageQueryVerdict verdict);

}  // namespace oh_adapter::package_query

#endif  // OH_ADAPTER_PACKAGE_QUERY_V1_H
