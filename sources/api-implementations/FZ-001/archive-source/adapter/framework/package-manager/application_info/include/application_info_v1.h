#ifndef OH_ADAPTER_APPLICATION_INFO_V1_H
#define OH_ADAPTER_APPLICATION_INFO_V1_H

#include "package_query_v1.h"
#include "package_transaction_v1.h"

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace oh_adapter::application_info {

constexpr uint64_t MATCH_DISABLED_COMPONENTS = 0x00000200ULL;

enum class ApplicationInfoVerdict {
    READY,
    INVALID_REQUEST,
    NOT_SUPPORTED,
    PACKAGE_NOT_FOUND,
    PACKAGE_NOT_VISIBLE,
    PACKAGE_NOT_READY,
    DATA_INCONSISTENT,
    PATH_READBACK_FAILED,
    INTERRUPTED,
};

enum class ApplicationInfoPhase {
    SNAPSHOT_FROZEN,
    PATHS_READ_BACK,
    FIELDS_PROJECTED,
    RESPONSE_SERIALIZED,
};

enum class ManagedPathKind {
    BASE_CODE_FILE,
    DATA_DIRECTORY,
    NATIVE_LIBRARY_DIRECTORY,
};

struct ManagedPathExpectationV1 {
    ManagedPathKind kind = ManagedPathKind::BASE_CODE_FILE;
    std::string path;
    std::string expectedDigest;
    std::optional<uint32_t> expectedOwnerUid;
};

struct ManagedPathReadbackV1 {
    ManagedPathKind kind = ManagedPathKind::BASE_CODE_FILE;
    std::string path;
    std::string observedDigest;
    uint32_t ownerUid = 0;
    uint32_t mode = 0;
};

struct HostApplicationRuntimeFactsV1 {
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    std::string projectionDigest;
    std::string bundleName;
    std::string appId;
    int32_t uid = -1;
    uint64_t accessTokenId = 0;
    bool projectionActive = false;
    bool tokenExternalReady = false;
    bool installed = true;
    bool enabled = true;
    bool hidden = false;
    ManagedPathExpectationV1 dataDirectory;
    ManagedPathExpectationV1 deviceProtectedDataDirectory;
    ManagedPathExpectationV1 credentialProtectedDataDirectory;
    std::optional<ManagedPathExpectationV1> nativeLibraryDirectory;
    std::optional<std::string> primaryCpuAbi;
};

enum class HostApplicationFactsVerdict {
    READY,
    PACKAGE_NOT_READY,
    DATA_INCONSISTENT,
};

struct ApplicationInfoRequestV1 {
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
    std::string processName;
    std::string label;
    int32_t uid = -1;
    std::string sourceDir;
    std::string publicSourceDir;
    std::string dataDir;
    std::string deviceProtectedDataDir;
    std::string credentialProtectedDataDir;
    std::optional<std::string> nativeLibraryDir;
    std::optional<std::string> primaryCpuAbi;
    uint32_t minSdk = 0;
    uint32_t targetSdk = 0;
    uint32_t applicationFlags = 0;
    bool enabled = true;
};

struct ApplicationInfoResponseV1 {
    std::string requestId;
    ApplicationInfoVerdict verdict =
        ApplicationInfoVerdict::DATA_INCONSISTENT;
    std::string reason;
    uint64_t catalogRevision = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    std::string artifactSetDigest;
    std::string projectionDigest;
    uint32_t userId = 0;
    uint64_t flags = 0;
    std::string callerScopeDigest;
    std::vector<ManagedPathReadbackV1> pathReadbacks;
    std::optional<ApplicationInfoViewV1> applicationInfo;
};

class ApplicationInfoFaultInjector {
public:
    virtual ~ApplicationInfoFaultInjector() = default;
    virtual bool InterruptAfter(ApplicationInfoPhase phase) = 0;
};

class NoApplicationInfoFaultInjector final
    : public ApplicationInfoFaultInjector {
public:
    bool InterruptAfter(ApplicationInfoPhase) override { return false; }
};

class HostApplicationRuntimeFactsResolverV1 {
public:
    virtual ~HostApplicationRuntimeFactsResolverV1() = default;
    virtual HostApplicationFactsVerdict Resolve(
        const std::string& packageName, uint32_t userId,
        uint64_t generation, const std::string& canonicalDigest,
        HostApplicationRuntimeFactsV1* facts, std::string* error) = 0;
};

class ManagedPathReaderV1 {
public:
    virtual ~ManagedPathReaderV1() = default;
    virtual bool Read(const ManagedPathExpectationV1& expectation,
        ManagedPathReadbackV1* readback, std::string* error) = 0;
};

class PosixManagedPathReaderV1 final : public ManagedPathReaderV1 {
public:
    bool Read(const ManagedPathExpectationV1& expectation,
        ManagedPathReadbackV1* readback, std::string* error) override;
};

class ApplicationInfoServiceV1 {
public:
    ApplicationInfoServiceV1(
        package_transaction::FilePackageStore* store,
        HostApplicationRuntimeFactsResolverV1* hostFactsResolver,
        ManagedPathReaderV1* pathReader,
        ApplicationInfoFaultInjector* faultInjector);

    ApplicationInfoResponseV1 GetApplicationInfo(
        const ApplicationInfoRequestV1& request) const;

private:
    package_transaction::FilePackageStore* store_;
    HostApplicationRuntimeFactsResolverV1* hostFactsResolver_;
    ManagedPathReaderV1* pathReader_;
    ApplicationInfoFaultInjector* faultInjector_;
};

const char* ApplicationInfoVerdictName(ApplicationInfoVerdict verdict);
const char* ManagedPathKindName(ManagedPathKind kind);
std::string ComputeManagedDirectoryDigestV1(const std::string& path);
std::string ApplicationInfoResponseJson(
    const ApplicationInfoResponseV1& response);

}  // namespace oh_adapter::application_info

#endif  // OH_ADAPTER_APPLICATION_INFO_V1_H
