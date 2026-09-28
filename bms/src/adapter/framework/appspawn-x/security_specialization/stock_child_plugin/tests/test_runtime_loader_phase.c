#include "runtime_loader_phase.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

static int failures;
static int tests_run;

static void FillSha(uint8_t sha[WLASC_SHA256_SIZE])
{
    size_t index;
    for (index = 0; index < WLASC_SHA256_SIZE; ++index) {
        sha[index] = (uint8_t)(index + 1U);
    }
}

static bool Begin(WlarLoaderPhaseRegistryV1 *registry, uint8_t sha[32])
{
    memset(registry, 0, sizeof(*registry));
    FillSha(sha);
    return WLAR_LoaderPhaseBeginParentPreload(
        registry, UINT64_C(99), sha, UINT64_C(1001),
        UINT64_C(2002)) == 0;
}

static bool ParentLifecycle(void)
{
    WlarLoaderPhaseRegistryV1 registry;
    uint8_t sha[32];
    return Begin(&registry, sha) &&
        WLAR_LoaderPhaseIsParentPreloading(
            &registry, UINT64_C(1001), UINT64_C(2002)) == 1 &&
        WLAR_LoaderPhaseIsParentPreloading(
            &registry, UINT64_C(1001), UINT64_C(2003)) == 0 &&
        WLAR_LoaderPhaseFinishParentPreload(
            &registry, UINT64_C(1001), UINT64_C(2002)) == 0 &&
        WLAR_LoaderPhaseGetState(&registry) ==
            WLAR_LOADER_PHASE_PARENT_DENIED &&
        WLAR_LoaderPhaseIsParentPreloading(
            &registry, UINT64_C(1001), UINT64_C(2002)) == 0;
}

static bool ChildLifecycle(void)
{
    WlarLoaderPhaseRegistryV1 registry;
    uint8_t sha[32];
    return Begin(&registry, sha) &&
        WLAR_LoaderPhaseFinishParentPreload(
            &registry, UINT64_C(1001), UINT64_C(2002)) == 0 &&
        WLAR_LoaderPhaseBeginChild(
            &registry, UINT64_C(99), sha, UINT64_C(1002)) == 0 &&
        !WLAR_LoaderPhaseIsChildReady(&registry, UINT64_C(1002)) &&
        WLAR_LoaderPhaseMarkChildReady(
            &registry, UINT64_C(1002)) == 0 &&
        WLAR_LoaderPhaseIsChildReady(&registry, UINT64_C(1002)) &&
        !WLAR_LoaderPhaseIsChildReady(&registry, UINT64_C(1001));
}

static bool ZeroTokenRejected(void)
{
    WlarLoaderPhaseRegistryV1 registry = {0};
    uint8_t sha[32];
    FillSha(sha);
    return WLAR_LoaderPhaseBeginParentPreload(
        &registry, UINT64_C(99), sha, UINT64_C(1001), UINT64_C(0)) != 0 &&
        registry.state == WLAR_LOADER_PHASE_FAILED;
}

static bool ZeroShaRejected(void)
{
    WlarLoaderPhaseRegistryV1 registry = {0};
    uint8_t sha[32] = {0};
    return WLAR_LoaderPhaseBeginParentPreload(
        &registry, UINT64_C(99), sha, UINT64_C(1001),
        UINT64_C(2002)) != 0;
}

static bool BeginReplayRejected(void)
{
    WlarLoaderPhaseRegistryV1 registry;
    uint8_t sha[32];
    return Begin(&registry, sha) &&
        WLAR_LoaderPhaseBeginParentPreload(
            &registry, UINT64_C(99), sha, UINT64_C(1001),
            UINT64_C(2002)) != 0 &&
        registry.state == WLAR_LOADER_PHASE_FAILED;
}

static bool WrongParentRejected(void)
{
    WlarLoaderPhaseRegistryV1 registry;
    uint8_t sha[32];
    return Begin(&registry, sha) &&
        WLAR_LoaderPhaseFinishParentPreload(
            &registry, UINT64_C(1002), UINT64_C(2002)) != 0;
}

static bool ChildBeforeFinishRejected(void)
{
    WlarLoaderPhaseRegistryV1 registry;
    uint8_t sha[32];
    return Begin(&registry, sha) &&
        WLAR_LoaderPhaseBeginChild(
            &registry, UINT64_C(99), sha, UINT64_C(1002)) != 0;
}

static bool ParentAsChildRejected(void)
{
    WlarLoaderPhaseRegistryV1 registry;
    uint8_t sha[32];
    return Begin(&registry, sha) &&
        WLAR_LoaderPhaseFinishParentPreload(
            &registry, UINT64_C(1001), UINT64_C(2002)) == 0 &&
        WLAR_LoaderPhaseBeginChild(
            &registry, UINT64_C(99), sha, UINT64_C(1001)) != 0;
}

static bool WrongGenerationRejected(void)
{
    WlarLoaderPhaseRegistryV1 registry;
    uint8_t sha[32];
    return Begin(&registry, sha) &&
        WLAR_LoaderPhaseFinishParentPreload(
            &registry, UINT64_C(1001), UINT64_C(2002)) == 0 &&
        WLAR_LoaderPhaseBeginChild(
            &registry, UINT64_C(100), sha, UINT64_C(1002)) != 0;
}

static bool WrongShaRejected(void)
{
    WlarLoaderPhaseRegistryV1 registry;
    uint8_t sha[32];
    if (!Begin(&registry, sha) ||
        WLAR_LoaderPhaseFinishParentPreload(
            &registry, UINT64_C(1001), UINT64_C(2002)) != 0) {
        return false;
    }
    sha[31] ^= UINT8_C(1);
    return WLAR_LoaderPhaseBeginChild(
        &registry, UINT64_C(99), sha, UINT64_C(1002)) != 0;
}

static bool WrongChildReadyRejected(void)
{
    WlarLoaderPhaseRegistryV1 registry;
    uint8_t sha[32];
    return Begin(&registry, sha) &&
        WLAR_LoaderPhaseFinishParentPreload(
            &registry, UINT64_C(1001), UINT64_C(2002)) == 0 &&
        WLAR_LoaderPhaseBeginChild(
            &registry, UINT64_C(99), sha, UINT64_C(1002)) == 0 &&
        WLAR_LoaderPhaseMarkChildReady(
            &registry, UINT64_C(1003)) != 0;
}

static bool ReadyReplayRejected(void)
{
    WlarLoaderPhaseRegistryV1 registry;
    uint8_t sha[32];
    return Begin(&registry, sha) &&
        WLAR_LoaderPhaseFinishParentPreload(
            &registry, UINT64_C(1001), UINT64_C(2002)) == 0 &&
        WLAR_LoaderPhaseBeginChild(
            &registry, UINT64_C(99), sha, UINT64_C(1002)) == 0 &&
        WLAR_LoaderPhaseMarkChildReady(
            &registry, UINT64_C(1002)) == 0 &&
        WLAR_LoaderPhaseMarkChildReady(
            &registry, UINT64_C(1002)) != 0;
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
    Run("parent_lifecycle", ParentLifecycle);
    Run("child_lifecycle", ChildLifecycle);
    Run("zero_token", ZeroTokenRejected);
    Run("zero_sha", ZeroShaRejected);
    Run("begin_replay", BeginReplayRejected);
    Run("wrong_parent", WrongParentRejected);
    Run("child_before_finish", ChildBeforeFinishRejected);
    Run("parent_as_child", ParentAsChildRejected);
    Run("wrong_generation", WrongGenerationRejected);
    Run("wrong_sha", WrongShaRejected);
    Run("wrong_child_ready", WrongChildReadyRejected);
    Run("ready_replay", ReadyReplayRejected);
    if (failures != 0) {
        return 1;
    }
    printf("RESULT PASS tests=%d\n", tests_run);
    return 0;
}
