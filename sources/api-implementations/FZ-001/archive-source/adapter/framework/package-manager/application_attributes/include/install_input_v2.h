#ifndef OH_ADAPTER_INSTALL_INPUT_V2_H
#define OH_ADAPTER_INSTALL_INPUT_V2_H
#include "apk_install_plan_v2.h"
#ifdef __cplusplus
#define OH_INSTALL_INPUT_ALIGN8 alignas(8)
extern "C" {
#else
#define OH_INSTALL_INPUT_ALIGN8 _Alignas(8)
#endif
#define OH_ADAPTER_INSTALL_INPUT_ABI_V2 2u
// An owned, same-process snapshot for the install entry. Requested flags are
// preserved as bits, not authorized here. The transaction must obtain granted
// policy from its trusted caller owner before using them.
typedef struct OhAdapterInstallInputV2 {
    OH_INSTALL_INPUT_ALIGN8 uint32_t abiVersion;
    uint32_t structSize;
    uint64_t requestedFlags;
    int32_t userId;
    uint32_t reservedZero;
    ApkInstallPlanV2 plan;
} OhAdapterInstallInputV2;
uint64_t oh_adapter_install_input_abi_v2(void);
void OhAdapterInstallInputV2_Init(OhAdapterInstallInputV2* input);
// Borrows immutable plan bytes and descriptors until return. Both byte spans
// must be accessible for their supplied lengths and must not overlap. The
// output must be unowned storage of the exact negotiated size; it may be
// unaligned. Success duplicates every FD with CLOEXEC and publishes all fields
// together. Failure leaves an empty initialized output (no borrowed FDs or
// partial payload). Invalid output size/pointer or overlap leaves it untouched.
// This is input acquisition, not caller authentication, authorization, signing
// verification, host readiness or installation. Uses ApkInstallPlanStatusV2.
int oh_adapter_acquire_install_input_v2(const void* planBytes, size_t planLength,
    int32_t userId, uint64_t requestedFlags, void* outputBytes, size_t outputLength);
// Only an owner of a same-process initialized object may release it. Closing
// the acquired snapshot never closes the source plan's borrowed descriptors.
void OhAdapterInstallInputV2_Release(OhAdapterInstallInputV2* input);
#ifdef __cplusplus
}
#endif
#undef OH_INSTALL_INPUT_ALIGN8
#endif
