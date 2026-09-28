#include "host_runtime_services.h"

#include <pthread.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

static const uint64_t kGeneration = UINT64_C(0x1122334455667788);
static int failures;
static int tests_run;
static int prepare_calls;
static int audit_calls;
static int verify_calls;
static int parent_prepare_calls;
static int parent_verify_calls;
static WlarHostServicesRegistryV1 *reentry_registry;
static WlncProcessIdentityV1 reentry_identity;
static WlncParentIdentityV1 reentry_parent_identity;
static _Thread_local uint64_t current_thread_token = UINT64_C(7);
static pthread_mutex_t concurrency_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t concurrency_condition = PTHREAD_COND_INITIALIZER;
static int concurrency_entered;
static volatile sig_atomic_t signal_reentry_result;

static uint64_t CurrentThreadToken(void)
{
    return current_thread_token;
}

static uint64_t ZeroThreadToken(void)
{
    return UINT64_C(0);
}

static void FillSha(uint8_t sha[WLASC_SHA256_SIZE], uint8_t seed)
{
    size_t index;
    for (index = 0; index < WLASC_SHA256_SIZE; ++index) {
        sha[index] = (uint8_t)(seed + (uint8_t)index);
    }
}

static int PrepareOk(const WlncProcessIdentityV1 *identity)
{
    ++prepare_calls;
    return identity != NULL ? WLNC_PREPARE_OK :
        WLNC_PREPARE_INVALID_IDENTITY;
}

static int PrepareParentOk(const WlncParentIdentityV1 *identity)
{
    ++parent_prepare_calls;
    return identity != NULL ? WLNC_PREPARE_OK :
        WLNC_PREPARE_INVALID_IDENTITY;
}

static int VerifyParentOk(uint64_t runtime_generation)
{
    ++parent_verify_calls;
    return runtime_generation == kGeneration ? WLNC_PREPARE_OK :
        WLNC_PREPARE_PROCESS_NOT_READY;
}

static int AuditOk(WlncAuditSnapshotV1 *snapshot)
{
    ++audit_calls;
    if (snapshot == NULL) {
        return WLNC_PREPARE_AUDIT_SNAPSHOT_INVALID;
    }
    memset(snapshot, 0, sizeof(*snapshot));
    return WLNC_PREPARE_OK;
}

static int VerifyOk(void)
{
    ++verify_calls;
    return WLNC_PREPARE_OK;
}

static int GetPthreadBridgeOpsOk(WlpbHostOpsV1 *out_ops)
{
    return out_ops != NULL ? WLNC_PREPARE_OK :
        WLNC_PREPARE_PROCESS_NOT_READY;
}

static void *OpenSealedExactOk(const char *absolute_path, int flags)
{
    (void)flags;
    return absolute_path != NULL ? (void *)(uintptr_t)UINT64_C(1) : NULL;
}

static int CreateConfiguredNamespacesOk(
    void *bridge_namespace, const char *bridge_name,
    const char *bridge_search_paths, const char *bridge_permitted_paths,
    const char *bridge_shared_sonames, const char *bridge_bootstrap_soname,
    const WlpbHostOpsV1 *pthread_bridge_ops,
    void **out_bridge_bootstrap_handle, void *app_namespace,
    const char *app_name, const char *app_search_paths,
    const char *app_permitted_paths)
{
    (void)bridge_namespace;
    (void)bridge_name;
    (void)bridge_search_paths;
    (void)bridge_permitted_paths;
    (void)bridge_shared_sonames;
    (void)bridge_bootstrap_soname;
    (void)pthread_bridge_ops;
    (void)app_name;
    (void)app_search_paths;
    (void)app_permitted_paths;
    if (out_bridge_bootstrap_handle != NULL) {
        *out_bridge_bootstrap_handle = NULL;
    }
    return app_namespace != NULL ? 0 : -1;
}

static void *OpenNamespaceOk(void *app_namespace, const char *path, int mode)
{
    (void)mode;
    return app_namespace != NULL && path != NULL ?
        (void *)(uintptr_t)UINT64_C(2) : NULL;
}

static int GetPthreadBridgeOpsError(WlpbHostOpsV1 *out_ops)
{
    (void)out_ops;
    return WLNC_PREPARE_PROCESS_NOT_READY;
}

static int GetPthreadBridgeOpsReentry(WlpbHostOpsV1 *out_ops)
{
    uint64_t nested[32] = {0};
    (void)out_ops;
    (void)WLAR_HostServicesGetPthreadBridgeOps(
        reentry_registry, (WlpbHostOpsV1 *)nested);
    return WLNC_PREPARE_OK;
}

static int VerifyConcurrent(void)
{
    int result = WLNC_PREPARE_OK;
    if (pthread_mutex_lock(&concurrency_mutex) != 0) {
        return WLNC_PREPARE_CURRENT_THREAD_NOT_READY;
    }
    ++concurrency_entered;
    if (concurrency_entered == 2) {
        if (pthread_cond_broadcast(&concurrency_condition) != 0) {
            result = WLNC_PREPARE_CURRENT_THREAD_NOT_READY;
        }
    } else {
        while (concurrency_entered < 2 && result == WLNC_PREPARE_OK) {
            if (pthread_cond_wait(&concurrency_condition,
                                  &concurrency_mutex) != 0) {
                result = WLNC_PREPARE_CURRENT_THREAD_NOT_READY;
            }
        }
    }
    if (pthread_mutex_unlock(&concurrency_mutex) != 0) {
        result = WLNC_PREPARE_CURRENT_THREAD_NOT_READY;
    }
    return result;
}

static int PrepareError(const WlncProcessIdentityV1 *identity)
{
    (void)identity;
    return WLNC_PREPARE_PROCESS_ARM_FAILED;
}

static int PrepareParentError(const WlncParentIdentityV1 *identity)
{
    (void)identity;
    return WLNC_PREPARE_PROCESS_ARM_FAILED;
}

static int VerifyParentError(uint64_t runtime_generation)
{
    (void)runtime_generation;
    return WLNC_PREPARE_PROCESS_NOT_READY;
}

static int AuditError(WlncAuditSnapshotV1 *snapshot)
{
    (void)snapshot;
    return WLNC_PREPARE_AUDIT_SNAPSHOT_RACE;
}

static int VerifyError(void)
{
    return WLNC_PREPARE_CURRENT_THREAD_NOT_READY;
}

static int PrepareReentry(const WlncProcessIdentityV1 *identity)
{
    (void)identity;
    (void)WLAR_HostServicesPrepareMain(
        reentry_registry, &reentry_identity);
    return WLNC_PREPARE_OK;
}

static int PrepareParentReentry(const WlncParentIdentityV1 *identity)
{
    (void)identity;
    (void)WLAR_HostServicesPrepareParentRuntime(
        reentry_registry, &reentry_parent_identity);
    return WLNC_PREPARE_OK;
}

static int VerifyParentReentry(uint64_t runtime_generation)
{
    (void)WLAR_HostServicesVerifyParentPreloadThreadReady(
        reentry_registry, runtime_generation);
    return WLNC_PREPARE_OK;
}

static int AuditReentry(WlncAuditSnapshotV1 *snapshot)
{
    WlncAuditSnapshotV1 nested;
    (void)snapshot;
    (void)WLAR_HostServicesGetAuditSnapshot(
        reentry_registry, &nested);
    return WLNC_PREPARE_OK;
}

static int VerifyReentry(void)
{
    (void)WLAR_HostServicesVerifyCurrentThreadReady(reentry_registry);
    return WLNC_PREPARE_OK;
}

static void VerifySignalHandler(int signal_number)
{
    (void)signal_number;
    signal_reentry_result =
        WLAR_HostServicesVerifyCurrentThreadReady(reentry_registry);
}

static int VerifySignalReentry(void)
{
    return raise(SIGUSR1) == 0 ? WLNC_PREPARE_OK :
        WLNC_PREPARE_CURRENT_THREAD_NOT_READY;
}

static int VerifyAbaMutation(void)
{
    size_t index;
    for (index = 0; index < WLAR_HOST_SERVICES_VERIFY_SLOTS; ++index) {
        if (reentry_registry->verify_active_tokens[index] ==
            current_thread_token) {
            reentry_registry->verify_active_tokens[index] =
                current_thread_token + UINT64_C(1);
            break;
        }
    }
    return WLNC_PREPARE_OK;
}

static WlascHostRuntimeServicesV1 GoodServices(void)
{
    WlascHostRuntimeServicesV1 services;
    memset(&services, 0, sizeof(services));
    services.abi_version = WLASC_HOST_SERVICES_ABI_VERSION;
    services.struct_size = sizeof(services);
    services.runtime_generation = kGeneration;
    FillSha(services.runtime_provider_sha256, UINT8_C(0x40));
    services.current_thread_token = CurrentThreadToken;
    services.prepare_parent_runtime = PrepareParentOk;
    services.verify_parent_preload_thread_ready = VerifyParentOk;
    services.prepare_main_thread = PrepareOk;
    services.verify_current_thread_ready = VerifyOk;
    services.get_audit_snapshot = AuditOk;
    services.get_pthread_bridge_ops = GetPthreadBridgeOpsOk;
    services.open_sealed_exact = OpenSealedExactOk;
    services.create_configured_namespaces = CreateConfiguredNamespacesOk;
    services.open_namespace = OpenNamespaceOk;
    return services;
}

static WlncProcessIdentityV1 GoodIdentity(void)
{
    WlncProcessIdentityV1 identity;
    memset(&identity, 0, sizeof(identity));
    identity.abi_version = WLNC_ABI_VERSION;
    identity.struct_size = sizeof(identity);
    identity.runtime_generation = kGeneration;
    identity.message_id = UINT64_C(41);
    identity.uid = UINT32_C(20010045);
    identity.gid = UINT32_C(20010045);
    identity.parent_stage_tail_reached = UINT32_C(1);
    identity.child_stage_tail_reached = UINT32_C(1);
    identity.bypass_guard_passed = UINT32_C(1);
    identity.security_owner_stock_appspawn = UINT32_C(1);
    identity.parent_tail_priority = WLASC_TAIL_PRIORITY;
    identity.child_tail_priority = WLASC_TAIL_PRIORITY;
    FillSha(identity.runtime_provider_sha256, UINT8_C(0x40));
    return identity;
}

static WlncParentIdentityV1 GoodParentIdentity(void)
{
    WlncParentIdentityV1 identity;
    memset(&identity, 0, sizeof(identity));
    identity.abi_version = WLNC_ABI_VERSION;
    identity.struct_size = sizeof(identity);
    identity.runtime_generation = kGeneration;
    identity.pid = UINT32_C(1234);
    identity.uid = UINT32_C(1000);
    identity.gid = UINT32_C(1000);
    FillSha(identity.runtime_provider_sha256, UINT8_C(0x40));
    return identity;
}

static void ResetCounters(void)
{
    prepare_calls = 0;
    audit_calls = 0;
    verify_calls = 0;
    parent_prepare_calls = 0;
    parent_verify_calls = 0;
    reentry_registry = NULL;
    current_thread_token = UINT64_C(7);
    memset(&reentry_identity, 0, sizeof(reentry_identity));
    memset(&reentry_parent_identity, 0, sizeof(reentry_parent_identity));
}

static bool InstallGood(WlarHostServicesRegistryV1 *registry,
                        WlascHostRuntimeServicesV1 *services)
{
    memset(registry, 0, sizeof(*registry));
    *services = GoodServices();
    return WLAR_HostServicesInstall(
        registry, kGeneration, services->runtime_provider_sha256,
        services) == 0;
}

static bool PrepareParent(WlarHostServicesRegistryV1 *registry)
{
    WlncParentIdentityV1 identity = GoodParentIdentity();
    return WLAR_HostServicesPrepareParentRuntime(registry, &identity) == 0 &&
        WLAR_HostServicesVerifyParentPreloadThreadReady(
            registry, kGeneration) == 0;
}

static bool ReachConsumed(WlarHostServicesRegistryV1 *registry,
                          WlascHostRuntimeServicesV1 *services)
{
    WlncParentIdentityV1 parent_identity = GoodParentIdentity();
    WlncProcessIdentityV1 identity = GoodIdentity();
    WlncAuditSnapshotV1 snapshot;
    return InstallGood(registry, services) &&
        WLAR_HostServicesPrepareParentRuntime(
            registry, &parent_identity) == 0 &&
        WLAR_HostServicesVerifyParentPreloadThreadReady(
            registry, kGeneration) == 0 &&
        WLAR_HostServicesBeginChild(registry) == 0 &&
        WLAR_HostServicesPrepareMain(registry, &identity) == 0 &&
        WLAR_HostServicesGetAuditSnapshot(registry, &snapshot) == 0 &&
        WLAR_HostServicesMarkChildConsumed(registry) == 0;
}

static bool ReachChildOnlyConsumed(WlarHostServicesRegistryV1 *registry,
                                   WlascHostRuntimeServicesV1 *services)
{
    WlncProcessIdentityV1 identity = GoodIdentity();
    WlncAuditSnapshotV1 snapshot;
    return InstallGood(registry, services) &&
        WLAR_HostServicesBeginChildOnly(registry) == 0 &&
        WLAR_HostServicesPrepareMain(registry, &identity) == 0 &&
        WLAR_HostServicesGetAuditSnapshot(registry, &snapshot) == 0 &&
        WLAR_HostServicesMarkChildConsumed(registry) == 0;
}

static bool HappyLifecycle(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    ResetCounters();
    return ReachConsumed(&registry, &services) &&
        registry.state == WLAR_HOST_SERVICES_CHILD_CONSUMED &&
        registry.prepare_call_count == UINT32_C(1) &&
        registry.audit_call_count == UINT32_C(1) &&
        WLAR_HostServicesVerifyCurrentThreadReady(&registry) == 0 &&
        WLAR_HostServicesVerifyCurrentThreadReady(&registry) == 0 &&
        registry.verify_success_count == UINT32_C(2) &&
        registry.verify_active_count == UINT32_C(0) &&
        registry.parent_prepare_call_count == UINT32_C(1) &&
        registry.parent_verify_success_count == UINT32_C(1) &&
        parent_prepare_calls == 1 && parent_verify_calls == 1 &&
        prepare_calls == 1 && audit_calls == 1 && verify_calls == 2;
}

static bool TableCopiedByValue(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncParentIdentityV1 parent_identity = GoodParentIdentity();
    WlncProcessIdentityV1 identity = GoodIdentity();
    WlncAuditSnapshotV1 snapshot;
    ResetCounters();
    if (!InstallGood(&registry, &services)) {
        return false;
    }
    services.prepare_main_thread = PrepareError;
    services.get_audit_snapshot = AuditError;
    services.verify_current_thread_ready = VerifyError;
    services.prepare_parent_runtime = PrepareParentError;
    services.verify_parent_preload_thread_ready = VerifyParentError;
    memset(services.runtime_provider_sha256, 0,
           sizeof(services.runtime_provider_sha256));
    return WLAR_HostServicesPrepareParentRuntime(
            &registry, &parent_identity) == 0 &&
        WLAR_HostServicesVerifyParentPreloadThreadReady(
            &registry, kGeneration) == 0 &&
        WLAR_HostServicesBeginChild(&registry) == 0 &&
        WLAR_HostServicesPrepareMain(&registry, &identity) == 0 &&
        WLAR_HostServicesGetAuditSnapshot(&registry, &snapshot) == 0 &&
        WLAR_HostServicesMarkChildConsumed(&registry) == 0 &&
        WLAR_HostServicesVerifyCurrentThreadReady(&registry) == 0;
}

static bool WrongAbiRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    WlascHostRuntimeServicesV1 services = GoodServices();
    services.abi_version++;
    return WLAR_HostServicesInstall(
        &registry, kGeneration, services.runtime_provider_sha256,
        &services) != 0 && registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool WrongSizeRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    WlascHostRuntimeServicesV1 services = GoodServices();
    services.struct_size--;
    return WLAR_HostServicesInstall(
        &registry, kGeneration, services.runtime_provider_sha256,
        &services) != 0;
}

static bool CrossGenerationRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    WlascHostRuntimeServicesV1 services = GoodServices();
    return WLAR_HostServicesInstall(
        &registry, kGeneration + UINT64_C(1),
        services.runtime_provider_sha256, &services) != 0;
}

static bool CrossShaRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    WlascHostRuntimeServicesV1 services = GoodServices();
    uint8_t expected_sha[WLASC_SHA256_SIZE];
    memcpy(expected_sha, services.runtime_provider_sha256,
           sizeof(expected_sha));
    expected_sha[31] ^= UINT8_C(1);
    return WLAR_HostServicesInstall(
        &registry, kGeneration, expected_sha, &services) != 0;
}

static bool NullNamespaceCreateRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    WlascHostRuntimeServicesV1 services = GoodServices();
    services.create_configured_namespaces = NULL;
    return WLAR_HostServicesInstall(
        &registry, kGeneration, services.runtime_provider_sha256,
        &services) != 0;
}

static bool NullNamespaceOpenRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    WlascHostRuntimeServicesV1 services = GoodServices();
    services.open_namespace = NULL;
    return WLAR_HostServicesInstall(
        &registry, kGeneration, services.runtime_provider_sha256,
        &services) != 0;
}

static bool NullPrepareRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    WlascHostRuntimeServicesV1 services = GoodServices();
    services.prepare_main_thread = NULL;
    return WLAR_HostServicesInstall(
        &registry, kGeneration, services.runtime_provider_sha256,
        &services) != 0;
}

static bool NullThreadTokenRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    WlascHostRuntimeServicesV1 services = GoodServices();
    services.current_thread_token = NULL;
    return WLAR_HostServicesInstall(
        &registry, kGeneration, services.runtime_provider_sha256,
        &services) != 0;
}

static bool NullParentPrepareRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    WlascHostRuntimeServicesV1 services = GoodServices();
    services.prepare_parent_runtime = NULL;
    return WLAR_HostServicesInstall(
        &registry, kGeneration, services.runtime_provider_sha256,
        &services) != 0;
}

static bool NullParentVerifyRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    WlascHostRuntimeServicesV1 services = GoodServices();
    services.verify_parent_preload_thread_ready = NULL;
    return WLAR_HostServicesInstall(
        &registry, kGeneration, services.runtime_provider_sha256,
        &services) != 0;
}

static bool NullAuditRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    WlascHostRuntimeServicesV1 services = GoodServices();
    services.get_audit_snapshot = NULL;
    return WLAR_HostServicesInstall(
        &registry, kGeneration, services.runtime_provider_sha256,
        &services) != 0;
}

static bool NullVerifyRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    WlascHostRuntimeServicesV1 services = GoodServices();
    services.verify_current_thread_ready = NULL;
    return WLAR_HostServicesInstall(
        &registry, kGeneration, services.runtime_provider_sha256,
        &services) != 0;
}

static bool NullPthreadBridgeOpsRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    WlascHostRuntimeServicesV1 services = GoodServices();
    services.get_pthread_bridge_ops = NULL;
    return WLAR_HostServicesInstall(
        &registry, kGeneration, services.runtime_provider_sha256,
        &services) != 0;
}

static bool NullSealedOpenRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    WlascHostRuntimeServicesV1 services = GoodServices();
    services.open_sealed_exact = NULL;
    return WLAR_HostServicesInstall(
        &registry, kGeneration, services.runtime_provider_sha256,
        &services) != 0;
}

static bool SecondInstallRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    if (!InstallGood(&registry, &services)) {
        return false;
    }
    return WLAR_HostServicesInstall(
        &registry, kGeneration, services.runtime_provider_sha256,
        &services) != 0 && registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool BeginBeforeInstallRejected(void)
{
    WlarHostServicesRegistryV1 registry = {0};
    return WLAR_HostServicesBeginChild(&registry) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool ChildBeforeParentPrepareRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    return InstallGood(&registry, &services) &&
        WLAR_HostServicesBeginChild(&registry) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool ParentPrepareReplayRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncParentIdentityV1 identity = GoodParentIdentity();
    return InstallGood(&registry, &services) &&
        WLAR_HostServicesPrepareParentRuntime(&registry, &identity) == 0 &&
        WLAR_HostServicesPrepareParentRuntime(&registry, &identity) != 0;
}

static bool ParentVerifyBeforePrepareRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    return InstallGood(&registry, &services) &&
        WLAR_HostServicesVerifyParentPreloadThreadReady(
            &registry, kGeneration) != 0;
}

static bool ParentIdentityGenerationRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncParentIdentityV1 identity = GoodParentIdentity();
    identity.runtime_generation++;
    return InstallGood(&registry, &services) &&
        WLAR_HostServicesPrepareParentRuntime(&registry, &identity) != 0;
}

static bool ParentIdentityShaRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncParentIdentityV1 identity = GoodParentIdentity();
    identity.runtime_provider_sha256[0] ^= UINT8_C(1);
    return InstallGood(&registry, &services) &&
        WLAR_HostServicesPrepareParentRuntime(&registry, &identity) != 0;
}

static bool ParentIdentityPidRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncParentIdentityV1 identity = GoodParentIdentity();
    identity.pid = UINT32_C(0);
    return InstallGood(&registry, &services) &&
        WLAR_HostServicesPrepareParentRuntime(&registry, &identity) != 0;
}

static bool ParentPrepareErrorRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncParentIdentityV1 identity = GoodParentIdentity();
    if (!InstallGood(&registry, &services)) {
        return false;
    }
    registry.services.prepare_parent_runtime = PrepareParentError;
    return WLAR_HostServicesPrepareParentRuntime(
            &registry, &identity) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool ParentPrepareReentryRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncParentIdentityV1 identity = GoodParentIdentity();
    if (!InstallGood(&registry, &services)) {
        return false;
    }
    reentry_registry = &registry;
    reentry_parent_identity = identity;
    registry.services.prepare_parent_runtime = PrepareParentReentry;
    return WLAR_HostServicesPrepareParentRuntime(
            &registry, &identity) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool ParentVerifyWrongGenerationRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncParentIdentityV1 identity = GoodParentIdentity();
    return InstallGood(&registry, &services) &&
        WLAR_HostServicesPrepareParentRuntime(&registry, &identity) == 0 &&
        WLAR_HostServicesVerifyParentPreloadThreadReady(
            &registry, kGeneration + UINT64_C(1)) != 0;
}

static bool ParentVerifyErrorRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncParentIdentityV1 identity = GoodParentIdentity();
    if (!InstallGood(&registry, &services) ||
        WLAR_HostServicesPrepareParentRuntime(&registry, &identity) != 0) {
        return false;
    }
    registry.services.verify_parent_preload_thread_ready = VerifyParentError;
    return WLAR_HostServicesVerifyParentPreloadThreadReady(
            &registry, kGeneration) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool ParentVerifyReentryRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncParentIdentityV1 identity = GoodParentIdentity();
    if (!InstallGood(&registry, &services) ||
        WLAR_HostServicesPrepareParentRuntime(&registry, &identity) != 0) {
        return false;
    }
    reentry_registry = &registry;
    registry.services.verify_parent_preload_thread_ready = VerifyParentReentry;
    return WLAR_HostServicesVerifyParentPreloadThreadReady(
            &registry, kGeneration) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool IdentityGenerationRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncProcessIdentityV1 identity = GoodIdentity();
    identity.runtime_generation++;
    return InstallGood(&registry, &services) && PrepareParent(&registry) &&
        WLAR_HostServicesBeginChild(&registry) == 0 &&
        WLAR_HostServicesPrepareMain(&registry, &identity) != 0;
}

static bool IdentityShaRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncProcessIdentityV1 identity = GoodIdentity();
    identity.runtime_provider_sha256[0] ^= UINT8_C(1);
    return InstallGood(&registry, &services) && PrepareParent(&registry) &&
        WLAR_HostServicesBeginChild(&registry) == 0 &&
        WLAR_HostServicesPrepareMain(&registry, &identity) != 0;
}

static bool IdentityReceiptRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncProcessIdentityV1 identity = GoodIdentity();
    identity.child_stage_tail_reached = UINT32_C(0);
    return InstallGood(&registry, &services) && PrepareParent(&registry) &&
        WLAR_HostServicesBeginChild(&registry) == 0 &&
        WLAR_HostServicesPrepareMain(&registry, &identity) != 0;
}

static bool AuditBeforePrepareRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncAuditSnapshotV1 snapshot;
    return InstallGood(&registry, &services) && PrepareParent(&registry) &&
        WLAR_HostServicesBeginChild(&registry) == 0 &&
        WLAR_HostServicesGetAuditSnapshot(&registry, &snapshot) != 0;
}

static bool PrepareReplayRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncProcessIdentityV1 identity = GoodIdentity();
    return InstallGood(&registry, &services) &&
        WLAR_HostServicesBeginChildOnly(&registry) == 0 &&
        WLAR_HostServicesPrepareMain(&registry, &identity) == 0 &&
        WLAR_HostServicesPrepareMain(&registry, &identity) != 0;
}

static bool AuditReplayRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncProcessIdentityV1 identity = GoodIdentity();
    WlncAuditSnapshotV1 snapshot;
    return InstallGood(&registry, &services) && PrepareParent(&registry) &&
        WLAR_HostServicesBeginChild(&registry) == 0 &&
        WLAR_HostServicesPrepareMain(&registry, &identity) == 0 &&
        WLAR_HostServicesGetAuditSnapshot(&registry, &snapshot) == 0 &&
        WLAR_HostServicesGetAuditSnapshot(&registry, &snapshot) != 0;
}

static bool MarkBeforeAuditRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncProcessIdentityV1 identity = GoodIdentity();
    return InstallGood(&registry, &services) && PrepareParent(&registry) &&
        WLAR_HostServicesBeginChild(&registry) == 0 &&
        WLAR_HostServicesPrepareMain(&registry, &identity) == 0 &&
        WLAR_HostServicesMarkChildConsumed(&registry) != 0;
}

static bool PthreadBridgeBeforeConsumedRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncProcessIdentityV1 identity = GoodIdentity();
    WlncAuditSnapshotV1 snapshot;
    uint64_t ops[32] = {0};
    return InstallGood(&registry, &services) && PrepareParent(&registry) &&
        WLAR_HostServicesBeginChild(&registry) == 0 &&
        WLAR_HostServicesPrepareMain(&registry, &identity) == 0 &&
        WLAR_HostServicesGetAuditSnapshot(&registry, &snapshot) == 0 &&
        WLAR_HostServicesGetPthreadBridgeOps(
            &registry, (WlpbHostOpsV1 *)ops) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool PthreadBridgeAfterConsumedAccepted(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    uint64_t ops[32] = {0};
    return ReachChildOnlyConsumed(&registry, &services) &&
        WLAR_HostServicesGetPthreadBridgeOps(
            &registry, (WlpbHostOpsV1 *)ops) == 0 &&
        registry.state == WLAR_HOST_SERVICES_CHILD_CONSUMED;
}

static bool NamespaceCallbacksAfterConsumedAccepted(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlascCreateConfiguredNamespacesV1 create = NULL;
    WlascOpenNamespaceV1 open = NULL;
    return ReachChildOnlyConsumed(&registry, &services) &&
        WLAR_HostServicesGetNamespaceCallbacks(
            &registry, &create, &open) == 0 &&
        create == CreateConfiguredNamespacesOk &&
        open == OpenNamespaceOk &&
        registry.state == WLAR_HOST_SERVICES_CHILD_CONSUMED;
}

static bool NamespaceCallbacksBeforeConsumedRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlascCreateConfiguredNamespacesV1 create = NULL;
    WlascOpenNamespaceV1 open = NULL;
    return InstallGood(&registry, &services) &&
        WLAR_HostServicesGetNamespaceCallbacks(
            &registry, &create, &open) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool PthreadBridgeParentWrapperCohortRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    uint64_t ops[32] = {0};
    return ReachConsumed(&registry, &services) &&
        WLAR_HostServicesGetPthreadBridgeOps(
            &registry, (WlpbHostOpsV1 *)ops) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool PthreadBridgeErrorRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    uint64_t ops[32] = {0};
    if (!ReachChildOnlyConsumed(&registry, &services)) {
        return false;
    }
    registry.services.get_pthread_bridge_ops = GetPthreadBridgeOpsError;
    return WLAR_HostServicesGetPthreadBridgeOps(
            &registry, (WlpbHostOpsV1 *)ops) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool PthreadBridgeReentryRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    uint64_t ops[32] = {0};
    if (!ReachChildOnlyConsumed(&registry, &services)) {
        return false;
    }
    reentry_registry = &registry;
    registry.services.get_pthread_bridge_ops = GetPthreadBridgeOpsReentry;
    return WLAR_HostServicesGetPthreadBridgeOps(
            &registry, (WlpbHostOpsV1 *)ops) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool VerifyBeforeConsumedRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    return InstallGood(&registry, &services) &&
        WLAR_HostServicesVerifyCurrentThreadReady(&registry) != 0;
}

static bool PrepareErrorRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncProcessIdentityV1 identity = GoodIdentity();
    if (!InstallGood(&registry, &services) || !PrepareParent(&registry)) {
        return false;
    }
    registry.services.prepare_main_thread = PrepareError;
    return WLAR_HostServicesBeginChild(&registry) == 0 &&
        WLAR_HostServicesPrepareMain(&registry, &identity) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool AuditErrorRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncProcessIdentityV1 identity = GoodIdentity();
    WlncAuditSnapshotV1 snapshot;
    if (!InstallGood(&registry, &services) || !PrepareParent(&registry)) {
        return false;
    }
    registry.services.get_audit_snapshot = AuditError;
    return WLAR_HostServicesBeginChild(&registry) == 0 &&
        WLAR_HostServicesPrepareMain(&registry, &identity) == 0 &&
        WLAR_HostServicesGetAuditSnapshot(&registry, &snapshot) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool VerifyErrorRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    if (!ReachConsumed(&registry, &services)) {
        return false;
    }
    registry.services.verify_current_thread_ready = VerifyError;
    return WLAR_HostServicesVerifyCurrentThreadReady(&registry) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool ZeroThreadTokenRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    if (!ReachConsumed(&registry, &services)) {
        return false;
    }
    registry.services.current_thread_token = ZeroThreadToken;
    return WLAR_HostServicesVerifyCurrentThreadReady(&registry) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED &&
        registry.verify_active_count == UINT32_C(0);
}

static bool PrepareReentryRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncProcessIdentityV1 identity = GoodIdentity();
    if (!InstallGood(&registry, &services) || !PrepareParent(&registry)) {
        return false;
    }
    reentry_registry = &registry;
    reentry_identity = identity;
    registry.services.prepare_main_thread = PrepareReentry;
    return WLAR_HostServicesBeginChild(&registry) == 0 &&
        WLAR_HostServicesPrepareMain(&registry, &identity) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool AuditReentryRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    WlncProcessIdentityV1 identity = GoodIdentity();
    WlncAuditSnapshotV1 snapshot;
    if (!InstallGood(&registry, &services) || !PrepareParent(&registry)) {
        return false;
    }
    reentry_registry = &registry;
    registry.services.get_audit_snapshot = AuditReentry;
    return WLAR_HostServicesBeginChild(&registry) == 0 &&
        WLAR_HostServicesPrepareMain(&registry, &identity) == 0 &&
        WLAR_HostServicesGetAuditSnapshot(&registry, &snapshot) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static bool VerifyReentryRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    if (!ReachConsumed(&registry, &services)) {
        return false;
    }
    reentry_registry = &registry;
    registry.services.verify_current_thread_ready = VerifyReentry;
    return WLAR_HostServicesVerifyCurrentThreadReady(&registry) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

typedef struct VerifyThreadArgument {
    WlarHostServicesRegistryV1 *registry;
    uint64_t token;
    int result;
} VerifyThreadArgument;

static void *RunConcurrentVerify(void *opaque)
{
    VerifyThreadArgument *argument = (VerifyThreadArgument *)opaque;
    current_thread_token = argument->token;
    argument->result =
        WLAR_HostServicesVerifyCurrentThreadReady(argument->registry);
    return NULL;
}

static bool ConcurrentDifferentThreadsAccepted(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    pthread_t first_thread;
    pthread_t second_thread;
    VerifyThreadArgument first = {&registry, UINT64_C(101), -1};
    VerifyThreadArgument second = {&registry, UINT64_C(202), -1};
    ResetCounters();
    if (!ReachConsumed(&registry, &services)) {
        return false;
    }
    registry.services.verify_current_thread_ready = VerifyConcurrent;
    concurrency_entered = 0;
    if (pthread_create(&first_thread, NULL, RunConcurrentVerify, &first) != 0 ||
        pthread_create(&second_thread, NULL, RunConcurrentVerify, &second) !=
            0) {
        return false;
    }
    if (pthread_join(first_thread, NULL) != 0 ||
        pthread_join(second_thread, NULL) != 0) {
        return false;
    }
    return first.result == 0 && second.result == 0 &&
        registry.state == WLAR_HOST_SERVICES_CHILD_CONSUMED &&
        registry.verify_active_count == UINT32_C(0) &&
        registry.verify_success_count == UINT32_C(2);
}

static bool SignalReentryRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    void (*old_handler)(int);
    if (!ReachConsumed(&registry, &services)) {
        return false;
    }
    reentry_registry = &registry;
    signal_reentry_result = 0;
    registry.services.verify_current_thread_ready = VerifySignalReentry;
    old_handler = signal(SIGUSR1, VerifySignalHandler);
    if (old_handler == SIG_ERR) {
        return false;
    }
    if (WLAR_HostServicesVerifyCurrentThreadReady(&registry) == 0) {
        (void)signal(SIGUSR1, old_handler);
        return false;
    }
    (void)signal(SIGUSR1, old_handler);
    return signal_reentry_result != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED &&
        registry.verify_active_count == UINT32_C(0);
}

static bool VerifyTokenAbaRejected(void)
{
    WlarHostServicesRegistryV1 registry;
    WlascHostRuntimeServicesV1 services;
    if (!ReachConsumed(&registry, &services)) {
        return false;
    }
    reentry_registry = &registry;
    registry.services.verify_current_thread_ready = VerifyAbaMutation;
    return WLAR_HostServicesVerifyCurrentThreadReady(&registry) != 0 &&
        registry.state == WLAR_HOST_SERVICES_FAILED;
}

static void Run(const char *name, bool (*test)(void))
{
    ++tests_run;
    if (!test()) {
        ++failures;
        fprintf(stderr, "FAIL %s\n", name);
    }
}

int main(void)
{
    Run("happy_lifecycle", HappyLifecycle);
    Run("table_copied_by_value", TableCopiedByValue);
    Run("wrong_abi", WrongAbiRejected);
    Run("wrong_size", WrongSizeRejected);
    Run("cross_generation", CrossGenerationRejected);
    Run("cross_sha", CrossShaRejected);
    Run("null_namespace_create", NullNamespaceCreateRejected);
    Run("null_namespace_open", NullNamespaceOpenRejected);
    Run("null_thread_token", NullThreadTokenRejected);
    Run("null_parent_prepare", NullParentPrepareRejected);
    Run("null_parent_verify", NullParentVerifyRejected);
    Run("null_prepare", NullPrepareRejected);
    Run("null_audit", NullAuditRejected);
    Run("null_verify", NullVerifyRejected);
    Run("null_pthread_bridge_ops", NullPthreadBridgeOpsRejected);
    Run("null_sealed_open", NullSealedOpenRejected);
    Run("second_install", SecondInstallRejected);
    Run("begin_before_install", BeginBeforeInstallRejected);
    Run("child_before_parent_prepare", ChildBeforeParentPrepareRejected);
    Run("parent_prepare_replay", ParentPrepareReplayRejected);
    Run("parent_verify_before_prepare", ParentVerifyBeforePrepareRejected);
    Run("parent_identity_generation", ParentIdentityGenerationRejected);
    Run("parent_identity_sha", ParentIdentityShaRejected);
    Run("parent_identity_pid", ParentIdentityPidRejected);
    Run("parent_prepare_callback_error", ParentPrepareErrorRejected);
    Run("parent_prepare_callback_reentry", ParentPrepareReentryRejected);
    Run("parent_verify_wrong_generation",
        ParentVerifyWrongGenerationRejected);
    Run("parent_verify_callback_error", ParentVerifyErrorRejected);
    Run("parent_verify_callback_reentry", ParentVerifyReentryRejected);
    Run("identity_generation", IdentityGenerationRejected);
    Run("identity_sha", IdentityShaRejected);
    Run("identity_receipt", IdentityReceiptRejected);
    Run("audit_before_prepare", AuditBeforePrepareRejected);
    Run("prepare_replay", PrepareReplayRejected);
    Run("audit_replay", AuditReplayRejected);
    Run("mark_before_audit", MarkBeforeAuditRejected);
    Run("pthread_bridge_before_consumed",
        PthreadBridgeBeforeConsumedRejected);
    Run("pthread_bridge_after_consumed",
        PthreadBridgeAfterConsumedAccepted);
    Run("namespace_callbacks_after_consumed",
        NamespaceCallbacksAfterConsumedAccepted);
    Run("namespace_callbacks_before_consumed",
        NamespaceCallbacksBeforeConsumedRejected);
    Run("pthread_bridge_parent_wrapper_cohort",
        PthreadBridgeParentWrapperCohortRejected);
    Run("pthread_bridge_callback_error", PthreadBridgeErrorRejected);
    Run("pthread_bridge_callback_reentry", PthreadBridgeReentryRejected);
    Run("verify_before_consumed", VerifyBeforeConsumedRejected);
    Run("prepare_callback_error", PrepareErrorRejected);
    Run("audit_callback_error", AuditErrorRejected);
    Run("verify_callback_error", VerifyErrorRejected);
    Run("zero_thread_token", ZeroThreadTokenRejected);
    Run("prepare_callback_reentry", PrepareReentryRejected);
    Run("audit_callback_reentry", AuditReentryRejected);
    Run("verify_callback_reentry", VerifyReentryRejected);
    Run("concurrent_different_threads", ConcurrentDifferentThreadsAccepted);
    Run("signal_reentry", SignalReentryRejected);
    Run("verify_token_aba", VerifyTokenAbaRejected);
    if (failures != 0) {
        fprintf(stderr, "RESULT FAIL tests=%d failures=%d\n",
                tests_run, failures);
        return 1;
    }
    printf("RESULT PASS tests=%d\n", tests_run);
    return 0;
}
