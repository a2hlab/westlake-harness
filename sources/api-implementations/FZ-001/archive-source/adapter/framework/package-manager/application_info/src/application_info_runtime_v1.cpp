#include "application_info_runtime_v1.h"

#include <mutex>
#include <utility>

namespace oh_adapter::application_info {
namespace {

std::mutex runtimeMutex;
package_transaction::FilePackageStore* runtimeStore = nullptr;
ApplicationInfoCallerResolverV1* runtimeCallerResolver = nullptr;
HostApplicationRuntimeFactsResolverV1* runtimeHostFacts = nullptr;
ManagedPathReaderV1* runtimePathReader = nullptr;
ApplicationInfoFaultInjector* runtimeFault = nullptr;

ApplicationInfoResponseV1 ClosedResponse(const std::string& requestId,
    uint64_t flags, uint32_t userId, ApplicationInfoVerdict verdict,
    const char* reason)
{
    ApplicationInfoResponseV1 response;
    response.requestId = requestId;
    response.flags = flags;
    response.userId = userId;
    response.verdict = verdict;
    response.reason = reason;
    return response;
}

}  // namespace

bool ConfigureApplicationInfoRuntimeV1(
    package_transaction::FilePackageStore* store,
    ApplicationInfoCallerResolverV1* callerResolver,
    HostApplicationRuntimeFactsResolverV1* hostFactsResolver,
    ManagedPathReaderV1* pathReader,
    ApplicationInfoFaultInjector* faultInjector,
    std::string* error)
{
    if (store == nullptr || callerResolver == nullptr ||
        hostFactsResolver == nullptr || pathReader == nullptr ||
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
    runtimeCallerResolver = callerResolver;
    runtimeHostFacts = hostFactsResolver;
    runtimePathReader = pathReader;
    runtimeFault = faultInjector;
    if (error != nullptr) error->clear();
    return true;
}

void ClearApplicationInfoRuntimeV1()
{
    std::lock_guard<std::mutex> lock(runtimeMutex);
    runtimeStore = nullptr;
    runtimeCallerResolver = nullptr;
    runtimeHostFacts = nullptr;
    runtimePathReader = nullptr;
    runtimeFault = nullptr;
}

std::string QueryApplicationInfoRuntimeJsonV1(
    const std::string& requestId, const std::string& packageName,
    uint64_t flags, uint32_t userId, int32_t callingUid)
{
    // The lock is deliberately held through the complete query. Clear()
    // therefore waits for in-flight readers before the lifecycle owner
    // destroys the dependencies behind these non-owning pointers.
    std::lock_guard<std::mutex> lock(runtimeMutex);
    if (runtimeStore == nullptr || runtimeCallerResolver == nullptr ||
        runtimeHostFacts == nullptr || runtimePathReader == nullptr ||
        runtimeFault == nullptr) {
        return ApplicationInfoResponseJson(ClosedResponse(requestId, flags,
            userId, ApplicationInfoVerdict::PACKAGE_NOT_READY,
            "APPLICATION_INFO_RUNTIME_NOT_CONFIGURED"));
    }
    package_query::CallerContextV1 caller;
    std::string error;
    const auto callerVerdict = runtimeCallerResolver->Resolve(
        callingUid, packageName, userId, &caller, &error);
    if (callerVerdict != ApplicationInfoCallerVerdictV1::VISIBLE) {
        ApplicationInfoVerdict verdict = ApplicationInfoVerdict::DATA_INCONSISTENT;
        const char* reason = "CALLER_ADMISSION_DATA_INCONSISTENT";
        switch (callerVerdict) {
            case ApplicationInfoCallerVerdictV1::NOT_SUPPORTED:
                verdict = ApplicationInfoVerdict::NOT_SUPPORTED;
                reason = "USER_NOT_SUPPORTED";
                break;
            case ApplicationInfoCallerVerdictV1::PACKAGE_NOT_FOUND:
                verdict = ApplicationInfoVerdict::PACKAGE_NOT_FOUND;
                reason = "PACKAGE_NOT_FOUND";
                break;
            case ApplicationInfoCallerVerdictV1::PACKAGE_NOT_READY:
                verdict = ApplicationInfoVerdict::PACKAGE_NOT_READY;
                reason = "HOST_APPLICATION_FACTS_NOT_READY";
                break;
            case ApplicationInfoCallerVerdictV1::DENIED:
                verdict = ApplicationInfoVerdict::PACKAGE_NOT_VISIBLE;
                reason = "CALLER_VISIBILITY_DENIED";
                break;
            case ApplicationInfoCallerVerdictV1::DATA_INCONSISTENT:
                break;
            case ApplicationInfoCallerVerdictV1::VISIBLE:
                break;
        }
        return ApplicationInfoResponseJson(
            ClosedResponse(requestId, flags, userId, verdict, reason));
    }
    ApplicationInfoRequestV1 request;
    request.requestId = requestId;
    request.packageName = packageName;
    request.flags = flags;
    request.userId = userId;
    request.caller = std::move(caller);
    ApplicationInfoServiceV1 service(
        runtimeStore, runtimeHostFacts, runtimePathReader, runtimeFault);
    return ApplicationInfoResponseJson(service.GetApplicationInfo(request));
}

}  // namespace oh_adapter::application_info
