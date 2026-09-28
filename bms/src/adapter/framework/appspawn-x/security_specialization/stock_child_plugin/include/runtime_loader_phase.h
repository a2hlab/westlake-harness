#ifndef WESTLAKE_RUNTIME_LOADER_PHASE_H
#define WESTLAKE_RUNTIME_LOADER_PHASE_H

#include "westlake_android_child_plugin.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum WlarLoaderPhaseState {
    WLAR_LOADER_PHASE_EMPTY = 0,
    WLAR_LOADER_PHASE_PARENT_INITIALIZING = 1,
    WLAR_LOADER_PHASE_PARENT_PRELOADING = 2,
    WLAR_LOADER_PHASE_PARENT_DENIED = 3,
    WLAR_LOADER_PHASE_CHILD_INITIALIZING = 4,
    WLAR_LOADER_PHASE_CHILD_WAITING = 5,
    WLAR_LOADER_PHASE_CHILD_READY = 6,
    WLAR_LOADER_PHASE_FAILED = 7
} WlarLoaderPhaseState;

typedef struct WlarLoaderPhaseRegistryV1 {
    uint32_t state;
    uint32_t reserved_zero;
    uint64_t runtime_generation;
    uint64_t parent_pid;
    uint64_t parent_thread_token;
    uint64_t child_pid;
    uint8_t runtime_provider_sha256[WLASC_SHA256_SIZE];
} WlarLoaderPhaseRegistryV1;

int WLAR_LoaderPhaseBeginParentPreload(
    WlarLoaderPhaseRegistryV1 *registry,
    uint64_t runtime_generation,
    const uint8_t runtime_provider_sha256[WLASC_SHA256_SIZE],
    uint64_t parent_pid, uint64_t parent_thread_token);

int WLAR_LoaderPhaseFinishParentPreload(
    WlarLoaderPhaseRegistryV1 *registry,
    uint64_t parent_pid, uint64_t parent_thread_token);

int WLAR_LoaderPhaseBeginChild(
    WlarLoaderPhaseRegistryV1 *registry,
    uint64_t runtime_generation,
    const uint8_t runtime_provider_sha256[WLASC_SHA256_SIZE],
    uint64_t child_pid);

int WLAR_LoaderPhaseBeginChildOnly(
    WlarLoaderPhaseRegistryV1 *registry,
    uint64_t runtime_generation,
    const uint8_t runtime_provider_sha256[WLASC_SHA256_SIZE],
    uint64_t child_pid);

int WLAR_LoaderPhaseMarkChildReady(
    WlarLoaderPhaseRegistryV1 *registry, uint64_t child_pid);

void WLAR_LoaderPhaseFail(WlarLoaderPhaseRegistryV1 *registry);

WlarLoaderPhaseState WLAR_LoaderPhaseGetState(
    const WlarLoaderPhaseRegistryV1 *registry);

int WLAR_LoaderPhaseIsParentPreloading(
    const WlarLoaderPhaseRegistryV1 *registry,
    uint64_t process_id, uint64_t thread_token);

int WLAR_LoaderPhaseIsChildReady(
    const WlarLoaderPhaseRegistryV1 *registry, uint64_t process_id);

#ifdef __cplusplus
}
#endif

#endif
