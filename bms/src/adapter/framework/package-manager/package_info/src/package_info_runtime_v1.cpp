#include "package_info_runtime_v1.h"

#include <mutex>

namespace oh_adapter::package_info {
namespace {

std::mutex runtimeMutex;
package_transaction::FilePackageStore* runtimeStore = nullptr;
CallerVisibilityResolverV1* runtimeVisibility = nullptr;
PackageInfoFaultInjector* runtimeFault = nullptr;

PackageInfoResponseV1 ClosedResponse(const std::string& requestId,
    uint64_t flags, uint32_t userId, PackageInfoVerdict verdict,
    const char* reason)
{
    PackageInfoResponseV1 response;
    response.requestId = requestId;
    response.flags = flags;
    response.userId = userId;
    response.verdict = verdict;
    response.reason = reason;
    return response;
}

}  // namespace

bool ConfigurePackageInfoRuntimeV1(
    package_transaction::FilePackageStore* store,
    CallerVisibilityResolverV1* visibilityResolver,
    PackageInfoFaultInjector* faultInjector,
    std::string* error)
{
    if (store == nullptr || visibilityResolver == nullptr ||
        faultInjector == nullptr) {
        if (error != nullptr) *error = "runtime dependency is null";
        return false;
    }
    std::lock_guard<std::mutex> lock(runtimeMutex);
    if (runtimeStore != nullptr) {
        if (error != nullptr) *error = "runtime is already configured";
        return false;
    }
    runtimeStore = store;
    runtimeVisibility = visibilityResolver;
    runtimeFault = faultInjector;
    if (error != nullptr) error->clear();
    return true;
}

void ClearPackageInfoRuntimeV1()
{
    std::lock_guard<std::mutex> lock(runtimeMutex);
    runtimeStore = nullptr;
    runtimeVisibility = nullptr;
    runtimeFault = nullptr;
}

std::string QueryPackageInfoRuntimeJsonV1(const std::string& requestId,
    const std::string& packageName, uint64_t flags, uint32_t userId,
    int32_t callingUid)
{
    package_transaction::FilePackageStore* store = nullptr;
    CallerVisibilityResolverV1* visibility = nullptr;
    PackageInfoFaultInjector* fault = nullptr;
    {
        std::lock_guard<std::mutex> lock(runtimeMutex);
        store = runtimeStore;
        visibility = runtimeVisibility;
        fault = runtimeFault;
    }
    if (store == nullptr || visibility == nullptr || fault == nullptr) {
        return PackageInfoResponseJson(ClosedResponse(requestId, flags, userId,
            PackageInfoVerdict::PACKAGE_NOT_READY,
            "PACKAGE_INFO_RUNTIME_NOT_CONFIGURED"));
    }
    package_query::CallerContextV1 caller;
    std::string error;
    if (!visibility->Resolve(callingUid, packageName, &caller, &error)) {
        return PackageInfoResponseJson(ClosedResponse(requestId, flags, userId,
            PackageInfoVerdict::PACKAGE_NOT_VISIBLE,
            "CALLER_VISIBILITY_DENIED"));
    }
    PackageInfoRequestV1 request;
    request.requestId = requestId;
    request.packageName = packageName;
    request.flags = flags;
    request.userId = userId;
    request.caller = std::move(caller);
    PackageInfoServiceV1 service(store, fault);
    return PackageInfoResponseJson(service.GetPackageInfo(request));
}

}  // namespace oh_adapter::package_info
