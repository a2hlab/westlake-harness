#ifndef WESTLAKE_HOST_RUNTIME_SERVICES_H
#define WESTLAKE_HOST_RUNTIME_SERVICES_H

#include "westlake_android_child_plugin.h"
#include "westlake_thread_guard_registry.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum WlarHostServicesState {
    WLAR_HOST_SERVICES_EMPTY = 0,
    WLAR_HOST_SERVICES_INSTALLING = 1,
    WLAR_HOST_SERVICES_INSTALLED = 2,
    WLAR_HOST_SERVICES_CHILD_ENTERING = 3,
    WLAR_HOST_SERVICES_CALLBACK_ACTIVE = 4,
    WLAR_HOST_SERVICES_CHILD_CONSUMED = 5,
    WLAR_HOST_SERVICES_FAILED = 6
} WlarHostServicesState;

#define WLAR_HOST_SERVICES_VERIFY_SLOTS WLTG_MAX_THREAD_RECORDS

typedef struct WlarHostServicesRegistryV1 {
    uint32_t state;
    uint32_t parent_prepare_call_count;
    uint32_t parent_verify_success_count;
    uint32_t prepare_call_count;
    uint32_t audit_call_count;
    uint32_t verify_success_count;
    uint32_t verify_active_count;
    uint32_t reserved_zero;
    WlascHostRuntimeServicesV1 services;
    uint64_t verify_active_tokens[WLAR_HOST_SERVICES_VERIFY_SLOTS];
} WlarHostServicesRegistryV1;

int WLAR_HostServicesInstall(
    WlarHostServicesRegistryV1 *registry,
    uint64_t expected_generation,
    const uint8_t expected_provider_sha256[WLASC_SHA256_SIZE],
    const WlascHostRuntimeServicesV1 *services);

int WLAR_HostServicesIsInstalled(
    const WlarHostServicesRegistryV1 *registry);

int WLAR_HostServicesGetCurrentThreadToken(
    WlarHostServicesRegistryV1 *registry, uint64_t *out_token);

int WLAR_HostServicesPrepareParentRuntime(
    WlarHostServicesRegistryV1 *registry,
    const WlncParentIdentityV1 *identity);

int WLAR_HostServicesVerifyParentPreloadThreadReady(
    WlarHostServicesRegistryV1 *registry, uint64_t runtime_generation);

int WLAR_HostServicesBeginChild(WlarHostServicesRegistryV1 *registry);

int WLAR_HostServicesBeginChildOnly(WlarHostServicesRegistryV1 *registry);

int WLAR_HostServicesPrepareMain(
    WlarHostServicesRegistryV1 *registry,
    const WlncProcessIdentityV1 *identity);

int WLAR_HostServicesGetAuditSnapshot(
    WlarHostServicesRegistryV1 *registry,
    WlncAuditSnapshotV1 *out_snapshot);

int WLAR_HostServicesGetPthreadBridgeOps(
    WlarHostServicesRegistryV1 *registry, WlpbHostOpsV1 *out_ops);

int WLAR_HostServicesGetNamespaceCallbacks(
    WlarHostServicesRegistryV1 *registry,
    WlascCreateConfiguredNamespacesV1 *out_create,
    WlascOpenNamespaceV1 *out_open);

int WLAR_HostServicesMarkChildConsumed(
    WlarHostServicesRegistryV1 *registry);

int WLAR_HostServicesVerifyCurrentThreadReady(
    WlarHostServicesRegistryV1 *registry);

#ifdef __cplusplus
}
#endif

#endif
