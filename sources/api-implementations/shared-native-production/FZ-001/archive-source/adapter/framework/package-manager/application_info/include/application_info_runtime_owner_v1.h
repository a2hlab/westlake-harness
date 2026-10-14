#ifndef OH_ADAPTER_APPLICATION_INFO_RUNTIME_OWNER_V1_H
#define OH_ADAPTER_APPLICATION_INFO_RUNTIME_OWNER_V1_H

#include "application_info_v1.h"
#include "package_transaction_v1.h"
#include "application_info_runtime_v1.h"

#include <cstdint>
#include <memory>
#include <string>

namespace oh_adapter::application_info {

struct ApplicationInfoRuntimeOwnerConfigV1 {
    std::string packageStoreRoot;
    std::string runtimeFactsRoot;
};

// Durable, generation-bound facts produced by the host projection owner.
// This reader never consults current BMS values and never guesses paths.
class FileHostApplicationRuntimeFactsResolverV1 final
    : public HostApplicationRuntimeFactsResolverV1 {
public:
    explicit FileHostApplicationRuntimeFactsResolverV1(
        std::string runtimeFactsRoot);

    HostApplicationFactsVerdict Resolve(const std::string& packageName,
        uint32_t userId, uint64_t generation,
        const std::string& canonicalDigest,
        HostApplicationRuntimeFactsV1* facts,
        std::string* error) override;

    std::string FactsPath(const std::string& packageName,
        uint32_t userId) const;

private:
    std::string runtimeFactsRoot_;
};

class StoreBackedCallerVisibilityResolverV1 final
    : public ApplicationInfoCallerResolverV1 {
public:
    StoreBackedCallerVisibilityResolverV1(
        package_transaction::FilePackageStore* store,
        HostApplicationRuntimeFactsResolverV1* hostFactsResolver);

    ApplicationInfoCallerVerdictV1 Resolve(
        int32_t callingUid, const std::string& packageName, uint32_t userId,
        package_query::CallerContextV1* caller,
        std::string* error) override;

private:
    package_transaction::FilePackageStore* store_;
    HostApplicationRuntimeFactsResolverV1* hostFactsResolver_;
};

class ApplicationInfoRuntimeOwnerV1 {
public:
    ApplicationInfoRuntimeOwnerV1();
    ~ApplicationInfoRuntimeOwnerV1();

    ApplicationInfoRuntimeOwnerV1(const ApplicationInfoRuntimeOwnerV1&) =
        delete;
    ApplicationInfoRuntimeOwnerV1& operator=(
        const ApplicationInfoRuntimeOwnerV1&) = delete;

    bool Start(const ApplicationInfoRuntimeOwnerConfigV1& config,
        std::string* error);
    void Stop();
    bool IsStarted() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

// Product lifecycle seam, owned by OHEnvironment.initialize()/shutdown().
bool StartProductApplicationInfoRuntimeV1(std::string* error);
void StopProductApplicationInfoRuntimeV1();

}  // namespace oh_adapter::application_info

#endif  // OH_ADAPTER_APPLICATION_INFO_RUNTIME_OWNER_V1_H
