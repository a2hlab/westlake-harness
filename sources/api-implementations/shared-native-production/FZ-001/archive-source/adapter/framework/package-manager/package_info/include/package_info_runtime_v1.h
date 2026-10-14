#ifndef OH_ADAPTER_PACKAGE_INFO_RUNTIME_V1_H
#define OH_ADAPTER_PACKAGE_INFO_RUNTIME_V1_H

#include "package_info_v1.h"

#include <cstdint>
#include <string>

namespace oh_adapter::package_info {

class CallerVisibilityResolverV1 {
public:
    virtual ~CallerVisibilityResolverV1() = default;
    virtual bool Resolve(int32_t callingUid, const std::string& packageName,
        package_query::CallerContextV1* caller, std::string* error) = 0;
};

// Startup owns all three objects and must keep them alive until Clear. There
// is deliberately no permissive default: an unconfigured runtime fails closed.
bool ConfigurePackageInfoRuntimeV1(
    package_transaction::FilePackageStore* store,
    CallerVisibilityResolverV1* visibilityResolver,
    PackageInfoFaultInjector* faultInjector,
    std::string* error);
void ClearPackageInfoRuntimeV1();

std::string QueryPackageInfoRuntimeJsonV1(const std::string& requestId,
    const std::string& packageName, uint64_t flags, uint32_t userId,
    int32_t callingUid);

}  // namespace oh_adapter::package_info

#endif
