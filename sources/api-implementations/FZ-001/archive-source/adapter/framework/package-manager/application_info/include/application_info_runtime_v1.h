#ifndef OH_ADAPTER_APPLICATION_INFO_RUNTIME_V1_H
#define OH_ADAPTER_APPLICATION_INFO_RUNTIME_V1_H

#include "application_info_v1.h"
#include <cstdint>
#include <string>

namespace oh_adapter::application_info {

enum class ApplicationInfoCallerVerdictV1 {
    VISIBLE,
    NOT_SUPPORTED,
    PACKAGE_NOT_FOUND,
    PACKAGE_NOT_READY,
    DATA_INCONSISTENT,
    DENIED,
};

class ApplicationInfoCallerResolverV1 {
public:
    virtual ~ApplicationInfoCallerResolverV1() = default;
    virtual ApplicationInfoCallerVerdictV1 Resolve(int32_t callingUid,
        const std::string& packageName, uint32_t userId,
        package_query::CallerContextV1* caller,
        std::string* error) = 0;
};

bool ConfigureApplicationInfoRuntimeV1(
    package_transaction::FilePackageStore* store,
    ApplicationInfoCallerResolverV1* callerResolver,
    HostApplicationRuntimeFactsResolverV1* hostFactsResolver,
    ManagedPathReaderV1* pathReader,
    ApplicationInfoFaultInjector* faultInjector,
    std::string* error);
void ClearApplicationInfoRuntimeV1();

std::string QueryApplicationInfoRuntimeJsonV1(
    const std::string& requestId, const std::string& packageName,
    uint64_t flags, uint32_t userId, int32_t callingUid);

}  // namespace oh_adapter::application_info

#endif  // OH_ADAPTER_APPLICATION_INFO_RUNTIME_V1_H
