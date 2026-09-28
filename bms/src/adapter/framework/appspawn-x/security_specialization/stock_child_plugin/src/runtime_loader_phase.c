#include "runtime_loader_phase.h"

#include <stddef.h>
#include <string.h>

_Static_assert(sizeof(WlarLoaderPhaseRegistryV1) == 72,
               "runtime loader phase registry ABI drift");

static uint32_t LoadState(const WlarLoaderPhaseRegistryV1 *registry)
{
    return registry == NULL ? WLAR_LOADER_PHASE_FAILED :
        __atomic_load_n(&registry->state, __ATOMIC_ACQUIRE);
}

static int ShaIsNonzero(const uint8_t *sha)
{
    uint8_t combined = UINT8_C(0);
    size_t index;
    if (sha == NULL) {
        return 0;
    }
    for (index = 0; index < WLASC_SHA256_SIZE; ++index) {
        combined = (uint8_t)(combined | sha[index]);
    }
    return combined != UINT8_C(0);
}

static int ShaEquals(const uint8_t *left, const uint8_t *right)
{
    uint8_t difference = UINT8_C(0);
    size_t index;
    if (left == NULL || right == NULL) {
        return 0;
    }
    for (index = 0; index < WLASC_SHA256_SIZE; ++index) {
        difference = (uint8_t)(difference | (left[index] ^ right[index]));
    }
    return difference == UINT8_C(0);
}

void WLAR_LoaderPhaseFail(WlarLoaderPhaseRegistryV1 *registry)
{
    if (registry != NULL) {
        __atomic_store_n(&registry->state, WLAR_LOADER_PHASE_FAILED,
                         __ATOMIC_RELEASE);
    }
}

int WLAR_LoaderPhaseBeginParentPreload(
    WlarLoaderPhaseRegistryV1 *registry,
    uint64_t runtime_generation,
    const uint8_t runtime_provider_sha256[WLASC_SHA256_SIZE],
    uint64_t parent_pid, uint64_t parent_thread_token)
{
    uint32_t expected = WLAR_LOADER_PHASE_EMPTY;
    if (registry == NULL || runtime_generation == UINT64_C(0) ||
        !ShaIsNonzero(runtime_provider_sha256) ||
        parent_pid == UINT64_C(0) || parent_thread_token == UINT64_C(0)) {
        WLAR_LoaderPhaseFail(registry);
        return -1;
    }
    if (!__atomic_compare_exchange_n(
            &registry->state, &expected,
            WLAR_LOADER_PHASE_PARENT_INITIALIZING, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        WLAR_LoaderPhaseFail(registry);
        return -1;
    }
    registry->reserved_zero = UINT32_C(0);
    registry->runtime_generation = runtime_generation;
    registry->parent_pid = parent_pid;
    registry->parent_thread_token = parent_thread_token;
    registry->child_pid = UINT64_C(0);
    (void)memcpy(registry->runtime_provider_sha256,
                 runtime_provider_sha256, WLASC_SHA256_SIZE);
    expected = WLAR_LOADER_PHASE_PARENT_INITIALIZING;
    if (!__atomic_compare_exchange_n(
            &registry->state, &expected,
            WLAR_LOADER_PHASE_PARENT_PRELOADING, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        WLAR_LoaderPhaseFail(registry);
        return -1;
    }
    return 0;
}

int WLAR_LoaderPhaseFinishParentPreload(
    WlarLoaderPhaseRegistryV1 *registry,
    uint64_t parent_pid, uint64_t parent_thread_token)
{
    uint32_t expected = WLAR_LOADER_PHASE_PARENT_PRELOADING;
    if (registry == NULL || parent_pid == UINT64_C(0) ||
        parent_thread_token == UINT64_C(0) ||
        LoadState(registry) != WLAR_LOADER_PHASE_PARENT_PRELOADING ||
        registry->parent_pid != parent_pid ||
        registry->parent_thread_token != parent_thread_token ||
        !__atomic_compare_exchange_n(
            &registry->state, &expected,
            WLAR_LOADER_PHASE_PARENT_DENIED, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        WLAR_LoaderPhaseFail(registry);
        return -1;
    }
    return 0;
}

int WLAR_LoaderPhaseBeginChild(
    WlarLoaderPhaseRegistryV1 *registry,
    uint64_t runtime_generation,
    const uint8_t runtime_provider_sha256[WLASC_SHA256_SIZE],
    uint64_t child_pid)
{
    uint32_t expected = WLAR_LOADER_PHASE_PARENT_DENIED;
    if (registry == NULL || child_pid == UINT64_C(0) ||
        LoadState(registry) != WLAR_LOADER_PHASE_PARENT_DENIED ||
        child_pid == registry->parent_pid ||
        runtime_generation != registry->runtime_generation ||
        !ShaEquals(runtime_provider_sha256,
                   registry->runtime_provider_sha256) ||
        !__atomic_compare_exchange_n(
            &registry->state, &expected,
            WLAR_LOADER_PHASE_CHILD_INITIALIZING, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        WLAR_LoaderPhaseFail(registry);
        return -1;
    }
    registry->child_pid = child_pid;
    expected = WLAR_LOADER_PHASE_CHILD_INITIALIZING;
    if (!__atomic_compare_exchange_n(
            &registry->state, &expected,
            WLAR_LOADER_PHASE_CHILD_WAITING, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        WLAR_LoaderPhaseFail(registry);
        return -1;
    }
    return 0;
}

int WLAR_LoaderPhaseBeginChildOnly(
    WlarLoaderPhaseRegistryV1 *registry,
    uint64_t runtime_generation,
    const uint8_t runtime_provider_sha256[WLASC_SHA256_SIZE],
    uint64_t child_pid)
{
    uint32_t expected = WLAR_LOADER_PHASE_EMPTY;
    if (registry == NULL || runtime_generation == UINT64_C(0) ||
        !ShaIsNonzero(runtime_provider_sha256) || child_pid == UINT64_C(0) ||
        !__atomic_compare_exchange_n(
            &registry->state, &expected,
            WLAR_LOADER_PHASE_CHILD_INITIALIZING, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        WLAR_LoaderPhaseFail(registry);
        return -1;
    }
    registry->reserved_zero = UINT32_C(0);
    registry->runtime_generation = runtime_generation;
    registry->parent_pid = UINT64_C(0);
    registry->parent_thread_token = UINT64_C(0);
    registry->child_pid = child_pid;
    (void)memcpy(registry->runtime_provider_sha256,
                 runtime_provider_sha256, WLASC_SHA256_SIZE);
    expected = WLAR_LOADER_PHASE_CHILD_INITIALIZING;
    if (!__atomic_compare_exchange_n(
            &registry->state, &expected,
            WLAR_LOADER_PHASE_CHILD_WAITING, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        WLAR_LoaderPhaseFail(registry);
        return -1;
    }
    return 0;
}

int WLAR_LoaderPhaseMarkChildReady(
    WlarLoaderPhaseRegistryV1 *registry, uint64_t child_pid)
{
    uint32_t expected = WLAR_LOADER_PHASE_CHILD_WAITING;
    if (registry == NULL || child_pid == UINT64_C(0) ||
        LoadState(registry) != WLAR_LOADER_PHASE_CHILD_WAITING ||
        registry->child_pid != child_pid ||
        !__atomic_compare_exchange_n(
            &registry->state, &expected,
            WLAR_LOADER_PHASE_CHILD_READY, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        WLAR_LoaderPhaseFail(registry);
        return -1;
    }
    return 0;
}

WlarLoaderPhaseState WLAR_LoaderPhaseGetState(
    const WlarLoaderPhaseRegistryV1 *registry)
{
    return (WlarLoaderPhaseState)LoadState(registry);
}

int WLAR_LoaderPhaseIsParentPreloading(
    const WlarLoaderPhaseRegistryV1 *registry,
    uint64_t process_id, uint64_t thread_token)
{
    return registry != NULL &&
        LoadState(registry) == WLAR_LOADER_PHASE_PARENT_PRELOADING &&
        process_id != UINT64_C(0) && process_id == registry->parent_pid &&
        thread_token != UINT64_C(0) &&
        thread_token == registry->parent_thread_token;
}

int WLAR_LoaderPhaseIsChildReady(
    const WlarLoaderPhaseRegistryV1 *registry, uint64_t process_id)
{
    return registry != NULL &&
        LoadState(registry) == WLAR_LOADER_PHASE_CHILD_READY &&
        process_id != UINT64_C(0) && process_id == registry->child_pid &&
        process_id != registry->parent_pid;
}
