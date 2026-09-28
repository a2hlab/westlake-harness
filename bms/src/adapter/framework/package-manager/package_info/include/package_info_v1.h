#ifndef OH_ADAPTER_PACKAGE_INFO_V1_H
#define OH_ADAPTER_PACKAGE_INFO_V1_H

#include "package_query_v1.h"
#include "package_transaction_v1.h"

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace oh_adapter::package_info {

constexpr uint64_t GET_ACTIVITIES = 0x00000001ULL;
constexpr uint64_t GET_RECEIVERS = 0x00000002ULL;
constexpr uint64_t GET_SERVICES = 0x00000004ULL;
constexpr uint64_t GET_PROVIDERS = 0x00000008ULL;
constexpr uint64_t GET_SIGNATURES = 0x00000040ULL;
constexpr uint64_t GET_PERMISSIONS = 0x00001000ULL;
constexpr uint64_t GET_SIGNING_CERTIFICATES = 0x08000000ULL;

enum class PackageInfoVerdict {
    READY,
    INVALID_REQUEST,
    NOT_SUPPORTED,
    PACKAGE_NOT_FOUND,
    PACKAGE_NOT_VISIBLE,
    PACKAGE_NOT_READY,
    STALE_GENERATION,
    DATA_INCONSISTENT,
    INTERRUPTED,
};

enum class PackageInfoPhase {
    SNAPSHOT_FROZEN,
    FIELDS_PROJECTED,
    RESPONSE_SERIALIZED,
};

struct PackageInfoRequestV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    std::string packageName;
    uint64_t flags = 0;
    uint32_t userId = 0;
    package_query::CallerContextV1 caller;
    std::optional<uint64_t> expectedGeneration;
    std::optional<std::string> expectedCanonicalDigest;
};

struct ApplicationInfoViewV1 {
    std::string packageName;
    std::string className;
    std::string label;
    uint32_t minSdk = 0;
    uint32_t targetSdk = 0;
};

struct PackageInfoViewV1 {
    std::string packageName;
    uint64_t versionCode = 0;
    std::string versionName;
    ApplicationInfoViewV1 applicationInfo;
    std::optional<std::vector<package_transaction::ManifestComponentFactV1>>
        activities;
    std::optional<std::vector<package_transaction::ManifestComponentFactV1>>
        receivers;
    std::optional<std::vector<package_transaction::ManifestComponentFactV1>>
        services;
    std::optional<std::vector<package_transaction::ManifestComponentFactV1>>
        providers;
    std::optional<std::vector<std::string>> requestedPermissions;
    std::optional<std::vector<std::string>> signatures;
    std::optional<std::vector<std::string>> signingCertificateDigests;
    std::optional<std::vector<std::string>> signerCertificateDerHex;
    std::optional<uint32_t> signingSchemeVersion;
};

struct PackageInfoResponseV1 {
    std::string requestId;
    PackageInfoVerdict verdict = PackageInfoVerdict::DATA_INCONSISTENT;
    std::string reason;
    uint64_t catalogRevision = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    uint32_t userId = 0;
    uint64_t flags = 0;
    std::string callerScopeDigest;
    std::optional<PackageInfoViewV1> packageInfo;
};

class PackageInfoFaultInjector {
public:
    virtual ~PackageInfoFaultInjector() = default;
    virtual bool InterruptAfter(PackageInfoPhase phase) = 0;
};

class NoPackageInfoFaultInjector final : public PackageInfoFaultInjector {
public:
    bool InterruptAfter(PackageInfoPhase) override { return false; }
};

class PackageInfoServiceV1 {
public:
    PackageInfoServiceV1(package_transaction::FilePackageStore* store,
        PackageInfoFaultInjector* faultInjector);

    PackageInfoResponseV1 GetPackageInfo(
        const PackageInfoRequestV1& request) const;

private:
    package_transaction::FilePackageStore* store_;
    PackageInfoFaultInjector* faultInjector_;
};

const char* PackageInfoVerdictName(PackageInfoVerdict verdict);
std::string PackageInfoResponseJson(const PackageInfoResponseV1& response);

}  // namespace oh_adapter::package_info

#endif
