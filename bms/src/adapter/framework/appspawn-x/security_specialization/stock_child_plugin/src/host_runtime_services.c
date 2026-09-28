#include "host_runtime_services.h"

#include <hilog/log.h>
#include <stddef.h>
#include <string.h>

_Static_assert(sizeof(WlascHostRuntimeServicesV1) == 128,
               "host runtime services ABI drift");
_Static_assert(WLAR_HOST_SERVICES_VERIFY_SLOTS == WLTG_MAX_THREAD_RECORDS,
               "verify slots must cover the WLTG product thread limit");
_Static_assert(offsetof(WlarHostServicesRegistryV1, services) == 32,
               "host runtime services registry layout drift");
_Static_assert(sizeof(WlarHostServicesRegistryV1) == 2208,
               "host runtime services registry size drift");

static void HspmGateMarker(const char *text)
{
    (void)HiLogPrint(LOG_CORE, LOG_INFO, UINT32_C(0xD002C11), "APPSPAWN",
                     "%{public}s", text);
}

static void HspmGateMarkerValue(const char *text, uint64_t value)
{
    (void)HiLogPrint(LOG_CORE, LOG_INFO, UINT32_C(0xD002C11), "APPSPAWN",
                     "%{public}s:%{public}llu", text,
                     (unsigned long long)value);
}

static uint32_t LoadState(const WlarHostServicesRegistryV1 *registry)
{
    return __atomic_load_n(&registry->state, __ATOMIC_ACQUIRE);
}

static void MarkFailed(WlarHostServicesRegistryV1 *registry)
{
    if (registry != NULL) {
        __atomic_store_n(&registry->state, WLAR_HOST_SERVICES_FAILED,
                         __ATOMIC_RELEASE);
    }
}

static int AllZero(const uint32_t *values, size_t count)
{
    uint32_t combined = UINT32_C(0);
    size_t index;
    for (index = 0; index < count; ++index) {
        combined |= values[index];
    }
    return combined == UINT32_C(0);
}

static int IdentityValid(
    const WlarHostServicesRegistryV1 *registry,
    const WlncProcessIdentityV1 *identity)
{
    return registry != NULL && identity != NULL &&
        LoadState(registry) == WLAR_HOST_SERVICES_CHILD_ENTERING &&
        identity->abi_version == WLNC_ABI_VERSION &&
        identity->struct_size == sizeof(*identity) &&
        identity->runtime_generation ==
            registry->services.runtime_generation &&
        identity->parent_stage_tail_reached == UINT32_C(1) &&
        identity->child_stage_tail_reached == UINT32_C(1) &&
        identity->bypass_guard_passed == UINT32_C(1) &&
        identity->security_owner_stock_appspawn == UINT32_C(1) &&
        identity->parent_tail_priority == WLASC_TAIL_PRIORITY &&
        identity->child_tail_priority == WLASC_TAIL_PRIORITY &&
        memcmp(identity->runtime_provider_sha256,
               registry->services.runtime_provider_sha256,
               WLASC_SHA256_SIZE) == 0 &&
        AllZero(identity->reserved_zero,
                sizeof(identity->reserved_zero) /
                    sizeof(identity->reserved_zero[0]));
}

static int ParentIdentityValid(
    const WlarHostServicesRegistryV1 *registry,
    const WlncParentIdentityV1 *identity)
{
    return registry != NULL && identity != NULL &&
        LoadState(registry) == WLAR_HOST_SERVICES_INSTALLED &&
        identity->abi_version == WLNC_ABI_VERSION &&
        identity->struct_size == sizeof(*identity) &&
        identity->runtime_generation ==
            registry->services.runtime_generation &&
        identity->pid != UINT32_C(0) &&
        memcmp(identity->runtime_provider_sha256,
               registry->services.runtime_provider_sha256,
               WLASC_SHA256_SIZE) == 0 &&
        identity->reserved_zero == UINT32_C(0) &&
        AllZero(identity->reserved_zero2,
                sizeof(identity->reserved_zero2) /
                    sizeof(identity->reserved_zero2[0]));
}

static int BeginCallback(WlarHostServicesRegistryV1 *registry,
                         uint32_t required_state)
{
    uint32_t expected = required_state;
    if (registry == NULL || !__atomic_compare_exchange_n(
            &registry->state, &expected, WLAR_HOST_SERVICES_CALLBACK_ACTIVE,
            0, __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        MarkFailed(registry);
        return -1;
    }
    return 0;
}

static int EndCallback(WlarHostServicesRegistryV1 *registry,
                       uint32_t restored_state, int callback_result)
{
    uint32_t expected = WLAR_HOST_SERVICES_CALLBACK_ACTIVE;
    if (callback_result != WLNC_PREPARE_OK ||
        !__atomic_compare_exchange_n(
            &registry->state, &expected, restored_state, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        MarkFailed(registry);
        return -1;
    }
    return 0;
}

static int AcquireVerifyToken(WlarHostServicesRegistryV1 *registry,
                              uint64_t token, size_t *out_slot)
{
    size_t index;
    size_t start;
    if (registry == NULL || out_slot == NULL || token == UINT64_C(0)) {
        MarkFailed(registry);
        return -1;
    }

    /* Same-thread signal/recursive entry must be found before any empty CAS. */
    for (index = 0; index < WLAR_HOST_SERVICES_VERIFY_SLOTS; ++index) {
        if (__atomic_load_n(&registry->verify_active_tokens[index],
                            __ATOMIC_ACQUIRE) == token) {
            MarkFailed(registry);
            return -1;
        }
    }

    start = (size_t)(token % WLAR_HOST_SERVICES_VERIFY_SLOTS);
    for (index = 0; index < WLAR_HOST_SERVICES_VERIFY_SLOTS; ++index) {
        size_t slot = (start + index) % WLAR_HOST_SERVICES_VERIFY_SLOTS;
        uint64_t empty = UINT64_C(0);
        if (__atomic_compare_exchange_n(
                &registry->verify_active_tokens[slot], &empty, token, 0,
                __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
            size_t duplicate;
            for (duplicate = 0;
                 duplicate < WLAR_HOST_SERVICES_VERIFY_SLOTS;
                 ++duplicate) {
                if (duplicate != slot &&
                    __atomic_load_n(
                        &registry->verify_active_tokens[duplicate],
                        __ATOMIC_ACQUIRE) == token) {
                    uint64_t expected = token;
                    (void)__atomic_compare_exchange_n(
                        &registry->verify_active_tokens[slot], &expected,
                        UINT64_C(0), 0, __ATOMIC_ACQ_REL,
                        __ATOMIC_ACQUIRE);
                    MarkFailed(registry);
                    return -1;
                }
            }
            __atomic_add_fetch(&registry->verify_active_count, UINT32_C(1),
                               __ATOMIC_ACQ_REL);
            *out_slot = slot;
            return 0;
        }
    }
    MarkFailed(registry);
    return -1;
}

static int ReleaseVerifyToken(WlarHostServicesRegistryV1 *registry,
                              uint64_t token, size_t slot)
{
    uint64_t expected = token;
    if (registry == NULL || slot >= WLAR_HOST_SERVICES_VERIFY_SLOTS ||
        !__atomic_compare_exchange_n(
            &registry->verify_active_tokens[slot], &expected, UINT64_C(0), 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        MarkFailed(registry);
        return -1;
    }
    if (__atomic_sub_fetch(&registry->verify_active_count, UINT32_C(1),
                           __ATOMIC_ACQ_REL) >
        WLAR_HOST_SERVICES_VERIFY_SLOTS) {
        MarkFailed(registry);
        return -1;
    }
    return 0;
}

int WLAR_HostServicesInstall(
    WlarHostServicesRegistryV1 *registry,
    uint64_t expected_generation,
    const uint8_t expected_provider_sha256[WLASC_SHA256_SIZE],
    const WlascHostRuntimeServicesV1 *services)
{
    uint32_t expected = WLAR_HOST_SERVICES_EMPTY;
    if (registry == NULL || !__atomic_compare_exchange_n(
            &registry->state, &expected, WLAR_HOST_SERVICES_INSTALLING, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        MarkFailed(registry);
        return -1;
    }
    if (services == NULL || expected_provider_sha256 == NULL ||
        services->abi_version != WLASC_HOST_SERVICES_ABI_VERSION ||
        services->struct_size != sizeof(*services) ||
        expected_generation == UINT64_C(0) ||
        services->runtime_generation != expected_generation ||
        memcmp(services->runtime_provider_sha256,
               expected_provider_sha256, WLASC_SHA256_SIZE) != 0 ||
        services->current_thread_token == NULL ||
        services->prepare_parent_runtime == NULL ||
        services->verify_parent_preload_thread_ready == NULL ||
        services->prepare_main_thread == NULL ||
        services->verify_current_thread_ready == NULL ||
        services->get_audit_snapshot == NULL ||
        services->get_pthread_bridge_ops == NULL ||
        services->open_sealed_exact == NULL ||
        services->create_configured_namespaces == NULL ||
        services->open_namespace == NULL) {
        MarkFailed(registry);
        return -1;
    }
    registry->parent_prepare_call_count = UINT32_C(0);
    registry->parent_verify_success_count = UINT32_C(0);
    registry->prepare_call_count = UINT32_C(0);
    registry->audit_call_count = UINT32_C(0);
    registry->verify_success_count = UINT32_C(0);
    registry->verify_active_count = UINT32_C(0);
    registry->reserved_zero = UINT32_C(0);
    memset(registry->verify_active_tokens, 0,
           sizeof(registry->verify_active_tokens));
    registry->services = *services;
    __atomic_store_n(&registry->state, WLAR_HOST_SERVICES_INSTALLED,
                     __ATOMIC_RELEASE);
    return 0;
}

int WLAR_HostServicesIsInstalled(
    const WlarHostServicesRegistryV1 *registry)
{
    return registry != NULL &&
        LoadState(registry) == WLAR_HOST_SERVICES_INSTALLED;
}

int WLAR_HostServicesGetCurrentThreadToken(
    WlarHostServicesRegistryV1 *registry, uint64_t *out_token)
{
    uint32_t state;
    uint64_t token;
    if (registry == NULL || out_token == NULL) {
        MarkFailed(registry);
        return -1;
    }
    state = LoadState(registry);
    if (state != WLAR_HOST_SERVICES_INSTALLED &&
        state != WLAR_HOST_SERVICES_CHILD_ENTERING &&
        state != WLAR_HOST_SERVICES_CHILD_CONSUMED) {
        MarkFailed(registry);
        return -1;
    }
    token = registry->services.current_thread_token();
    if (token == UINT64_C(0) || LoadState(registry) != state) {
        MarkFailed(registry);
        return -1;
    }
    *out_token = token;
    return 0;
}

int WLAR_HostServicesPrepareParentRuntime(
    WlarHostServicesRegistryV1 *registry,
    const WlncParentIdentityV1 *identity)
{
    uint32_t expected_count = UINT32_C(0);
    if (!ParentIdentityValid(registry, identity) ||
        !__atomic_compare_exchange_n(
            &registry->parent_prepare_call_count, &expected_count,
            UINT32_C(1), 0, __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE) ||
        BeginCallback(registry, WLAR_HOST_SERVICES_INSTALLED) != 0) {
        MarkFailed(registry);
        return -1;
    }
    return EndCallback(
        registry, WLAR_HOST_SERVICES_INSTALLED,
        registry->services.prepare_parent_runtime(identity));
}

int WLAR_HostServicesVerifyParentPreloadThreadReady(
    WlarHostServicesRegistryV1 *registry, uint64_t runtime_generation)
{
    if (registry == NULL ||
        LoadState(registry) != WLAR_HOST_SERVICES_INSTALLED ||
        runtime_generation == UINT64_C(0) ||
        runtime_generation != registry->services.runtime_generation ||
        __atomic_load_n(&registry->parent_prepare_call_count,
                        __ATOMIC_ACQUIRE) != UINT32_C(1) ||
        BeginCallback(registry, WLAR_HOST_SERVICES_INSTALLED) != 0) {
        MarkFailed(registry);
        return -1;
    }
    if (EndCallback(
            registry, WLAR_HOST_SERVICES_INSTALLED,
            registry->services.verify_parent_preload_thread_ready(
                runtime_generation)) != 0) {
        return -1;
    }
    __atomic_add_fetch(&registry->parent_verify_success_count, UINT32_C(1),
                       __ATOMIC_ACQ_REL);
    return 0;
}

int WLAR_HostServicesBeginChild(WlarHostServicesRegistryV1 *registry)
{
    uint32_t expected = WLAR_HOST_SERVICES_INSTALLED;
    if (registry == NULL ||
        __atomic_load_n(&registry->parent_prepare_call_count,
                        __ATOMIC_ACQUIRE) != UINT32_C(1) ||
        !__atomic_compare_exchange_n(
            &registry->state, &expected,
            WLAR_HOST_SERVICES_CHILD_ENTERING, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        MarkFailed(registry);
        return -1;
    }
    return 0;
}

int WLAR_HostServicesBeginChildOnly(WlarHostServicesRegistryV1 *registry)
{
    uint32_t expected = WLAR_HOST_SERVICES_INSTALLED;
    if (registry == NULL ||
        __atomic_load_n(&registry->parent_prepare_call_count,
                        __ATOMIC_ACQUIRE) != UINT32_C(0) ||
        !__atomic_compare_exchange_n(
            &registry->state, &expected,
            WLAR_HOST_SERVICES_CHILD_ENTERING, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        MarkFailed(registry);
        return -1;
    }
    return 0;
}

int WLAR_HostServicesPrepareMain(
    WlarHostServicesRegistryV1 *registry,
    const WlncProcessIdentityV1 *identity)
{
    uint32_t expected_count = UINT32_C(0);
    int callback_result;
    int end_result;

    HspmGateMarker("WLCGATE:HSPM:ENTER");
    HspmGateMarkerValue("WLCGATE:HSPM:OBSERVED_STATE",
                        registry == NULL ? UINT64_MAX : LoadState(registry));
    HspmGateMarkerValue("WLCGATE:HSPM:EXPECTED_STATE",
                        WLAR_HOST_SERVICES_CHILD_ENTERING);
    HspmGateMarkerValue("WLCGATE:HSPM:EXPECTED_GENERATION",
                        registry == NULL ? UINT64_C(0) :
                            registry->services.runtime_generation);
    HspmGateMarkerValue("WLCGATE:HSPM:OBSERVED_GENERATION",
                        identity == NULL ? UINT64_C(0) :
                            identity->runtime_generation);
    if (!IdentityValid(registry, identity)) {
        HspmGateMarker("WLCGATE:HSPM:FAIL_IDENTITY");
        MarkFailed(registry);
        return -1;
    }
    HspmGateMarker("WLCGATE:HSPM:PASS_IDENTITY");
    if (!__atomic_compare_exchange_n(
            &registry->prepare_call_count, &expected_count, UINT32_C(1), 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        HspmGateMarkerValue("WLCGATE:HSPM:FAIL_PREPARE_COUNT",
                            expected_count);
        MarkFailed(registry);
        return -1;
    }
    HspmGateMarker("WLCGATE:HSPM:PASS_PREPARE_COUNT");
    if (BeginCallback(registry, WLAR_HOST_SERVICES_CHILD_ENTERING) != 0) {
        HspmGateMarkerValue("WLCGATE:HSPM:FAIL_BEGIN_CALLBACK_STATE",
                            LoadState(registry));
        MarkFailed(registry);
        return -1;
    }
    HspmGateMarker("WLCGATE:HSPM:PASS_BEGIN_CALLBACK");
    callback_result = registry->services.prepare_main_thread(identity);
    HspmGateMarkerValue("WLCGATE:HSPM:PREPARE_MAIN_THREAD_RESULT",
                        (uint32_t)callback_result);
    end_result = EndCallback(registry, WLAR_HOST_SERVICES_CHILD_ENTERING,
                             callback_result);
    HspmGateMarkerValue("WLCGATE:HSPM:END_CALLBACK_RESULT",
                        (uint32_t)end_result);
    return end_result;
}

int WLAR_HostServicesGetAuditSnapshot(
    WlarHostServicesRegistryV1 *registry,
    WlncAuditSnapshotV1 *out_snapshot)
{
    uint32_t expected_count = UINT32_C(0);
    if (registry == NULL || out_snapshot == NULL ||
        __atomic_load_n(&registry->prepare_call_count,
                        __ATOMIC_ACQUIRE) != UINT32_C(1) ||
        !__atomic_compare_exchange_n(
            &registry->audit_call_count, &expected_count, UINT32_C(1), 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE) ||
        BeginCallback(registry, WLAR_HOST_SERVICES_CHILD_ENTERING) != 0) {
        MarkFailed(registry);
        return -1;
    }
    return EndCallback(
        registry, WLAR_HOST_SERVICES_CHILD_ENTERING,
        registry->services.get_audit_snapshot(out_snapshot));
}

int WLAR_HostServicesGetPthreadBridgeOps(
    WlarHostServicesRegistryV1 *registry, WlpbHostOpsV1 *out_ops)
{
    if (registry == NULL || out_ops == NULL ||
        LoadState(registry) != WLAR_HOST_SERVICES_CHILD_CONSUMED ||
        __atomic_load_n(&registry->parent_prepare_call_count,
                        __ATOMIC_ACQUIRE) != UINT32_C(0) ||
        BeginCallback(registry, WLAR_HOST_SERVICES_CHILD_CONSUMED) != 0) {
        MarkFailed(registry);
        return -1;
    }
    return EndCallback(
        registry, WLAR_HOST_SERVICES_CHILD_CONSUMED,
        registry->services.get_pthread_bridge_ops(out_ops));
}

int WLAR_HostServicesGetNamespaceCallbacks(
    WlarHostServicesRegistryV1 *registry,
    WlascCreateConfiguredNamespacesV1 *out_create,
    WlascOpenNamespaceV1 *out_open)
{
    if (registry == NULL || out_create == NULL || out_open == NULL ||
        LoadState(registry) != WLAR_HOST_SERVICES_CHILD_CONSUMED ||
        __atomic_load_n(&registry->parent_prepare_call_count,
                        __ATOMIC_ACQUIRE) != UINT32_C(0) ||
        BeginCallback(registry, WLAR_HOST_SERVICES_CHILD_CONSUMED) != 0) {
        MarkFailed(registry);
        return -1;
    }
    *out_create = registry->services.create_configured_namespaces;
    *out_open = registry->services.open_namespace;
    return EndCallback(
        registry, WLAR_HOST_SERVICES_CHILD_CONSUMED,
        *out_create != NULL && *out_open != NULL ? WLNC_PREPARE_OK : -1);
}

int WLAR_HostServicesMarkChildConsumed(
    WlarHostServicesRegistryV1 *registry)
{
    uint32_t expected = WLAR_HOST_SERVICES_CHILD_ENTERING;
    if (registry == NULL ||
        __atomic_load_n(&registry->prepare_call_count,
                        __ATOMIC_ACQUIRE) != UINT32_C(1) ||
        __atomic_load_n(&registry->audit_call_count,
                        __ATOMIC_ACQUIRE) != UINT32_C(1) ||
        __atomic_load_n(&registry->verify_active_count,
                        __ATOMIC_ACQUIRE) != UINT32_C(0) ||
        !__atomic_compare_exchange_n(
            &registry->state, &expected,
            WLAR_HOST_SERVICES_CHILD_CONSUMED, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        MarkFailed(registry);
        return -1;
    }
    return 0;
}

int WLAR_HostServicesVerifyCurrentThreadReady(
    WlarHostServicesRegistryV1 *registry)
{
    uint64_t token;
    size_t slot;
    int callback_result;
    if (registry == NULL ||
        LoadState(registry) != WLAR_HOST_SERVICES_CHILD_CONSUMED) {
        MarkFailed(registry);
        return -1;
    }
    token = registry->services.current_thread_token();
    if (token == UINT64_C(0) ||
        AcquireVerifyToken(registry, token, &slot) != 0) {
        MarkFailed(registry);
        return -1;
    }
    if (LoadState(registry) != WLAR_HOST_SERVICES_CHILD_CONSUMED) {
        (void)ReleaseVerifyToken(registry, token, slot);
        return -1;
    }
    callback_result = registry->services.verify_current_thread_ready();
    if (ReleaseVerifyToken(registry, token, slot) != 0 ||
        callback_result != WLNC_PREPARE_OK ||
        LoadState(registry) != WLAR_HOST_SERVICES_CHILD_CONSUMED) {
        MarkFailed(registry);
        return -1;
    }
    __atomic_add_fetch(&registry->verify_success_count, UINT32_C(1),
                       __ATOMIC_ACQ_REL);
    return 0;
}
