#include "install_input_v2.h"
#include <cstring>
#if defined(__linux__) || defined(__OHOS__)
#include <fcntl.h>
#endif
namespace {
static_assert(sizeof(OhAdapterInstallInputV2) == 21056 && alignof(OhAdapterInstallInputV2) == 8);
bool Overlap(const void* a, size_t aSize, const void* b, size_t bSize)
{
    const auto left = reinterpret_cast<uintptr_t>(a), right = reinterpret_cast<uintptr_t>(b);
    return left <= right ? right - left < aSize : left - right < bSize;
}
int Duplicate(int fd)
{
#if defined(__linux__) || defined(__OHOS__)
    const int result = fcntl(fd, F_DUPFD_CLOEXEC, 0);
    if (result < 0) throw APK_INSTALL_PLAN_V2_RESOURCE_ERROR;
    return result;
#else
    (void)fd;
    throw APK_INSTALL_PLAN_V2_UNSUPPORTED_PLATFORM;
#endif
}
}
extern "C" uint64_t oh_adapter_install_input_abi_v2(void)
{ return (uint64_t{OH_ADAPTER_INSTALL_INPUT_ABI_V2} << 32) | sizeof(OhAdapterInstallInputV2); }
extern "C" void OhAdapterInstallInputV2_Init(OhAdapterInstallInputV2* input)
{
    if (!input) return;
    std::memset(input, 0, sizeof(*input));
    input->abiVersion = OH_ADAPTER_INSTALL_INPUT_ABI_V2;
    input->structSize = sizeof(*input); input->userId = -1;
    ApkInstallPlanV2_Init(&input->plan);
}
extern "C" int oh_adapter_acquire_install_input_v2(const void* planBytes, size_t planLength,
    int32_t userId, uint64_t requestedFlags, void* outputBytes, size_t outputLength)
{
    if (!outputBytes) return APK_INSTALL_PLAN_V2_BAD_ARGUMENT;
    if (outputLength != sizeof(OhAdapterInstallInputV2)) return APK_INSTALL_PLAN_V2_BAD_SIZE;
    if (planBytes && planLength == sizeof(ApkInstallPlanV2) &&
        Overlap(planBytes, planLength, outputBytes, outputLength)) return APK_INSTALL_PLAN_V2_BAD_ARGUMENT;
    OhAdapterInstallInputV2 candidate; OhAdapterInstallInputV2_Init(&candidate);
    std::memcpy(outputBytes, &candidate, sizeof(candidate));
    if (!planBytes) return APK_INSTALL_PLAN_V2_BAD_ARGUMENT;
    if (planLength != sizeof(ApkInstallPlanV2)) return APK_INSTALL_PLAN_V2_BAD_SIZE;
    if (userId < 0) return APK_INSTALL_PLAN_V2_BAD_CONTEXT;
    // Always copy to aligned storage. Validate the original descriptor set
    // before duplicating it, so duplicate input FD numbers cannot be hidden.
    ApkInstallPlanV2 source; std::memcpy(&source, planBytes, sizeof(source));
    try {
        const int status = ApkInstallPlanV2_Validate(&source);
        if (status != APK_INSTALL_PLAN_V2_OK) return status;
        if (source.context.userId != userId) return APK_INSTALL_PLAN_V2_BAD_CONTEXT;
        candidate.plan = source;
        candidate.plan.manifestSigning.fd = -1;
        for (auto& artifact : candidate.plan.artifacts) { artifact.apk.fd = -1; artifact.prepass.fd = -1; }
        struct Owner {
            OhAdapterInstallInputV2& input;
            ~Owner() { OhAdapterInstallInputV2_Release(&input); }
        } owner{candidate};
        candidate.plan.manifestSigning.fd = Duplicate(source.manifestSigning.fd);
        for (uint32_t i = 0; i < source.artifactCount; ++i) {
            candidate.plan.artifacts[i].apk.fd = Duplicate(source.artifacts[i].apk.fd);
            candidate.plan.artifacts[i].prepass.fd = Duplicate(source.artifacts[i].prepass.fd);
        }
        candidate.userId = userId; candidate.requestedFlags = requestedFlags;
        std::memcpy(outputBytes, &candidate, sizeof(candidate));
        // Publication transfers all owned descriptors to the caller's bytes.
        OhAdapterInstallInputV2_Init(&candidate);
        return APK_INSTALL_PLAN_V2_OK;
    } catch (ApkInstallPlanStatusV2 status) { return status; }
    catch (...) { return APK_INSTALL_PLAN_V2_RESOURCE_ERROR; }
}
extern "C" void OhAdapterInstallInputV2_Release(OhAdapterInstallInputV2* input)
{
    if (!input || input->abiVersion != OH_ADAPTER_INSTALL_INPUT_ABI_V2 || input->structSize != sizeof(*input)) return;
    ApkInstallPlanV2_Release(&input->plan); OhAdapterInstallInputV2_Init(input);
}
