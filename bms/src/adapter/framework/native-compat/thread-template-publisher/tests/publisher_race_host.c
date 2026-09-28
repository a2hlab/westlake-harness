#define _GNU_SOURCE

#include "westlake_thread_template_publisher.h"

#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

__thread uint8_t g_race_reservation[WLTP_RESERVATION_SIZE]
    __attribute__((aligned(16), tls_model("initial-exec"))) = {
        [0] = 0x51,
        [WLTP_RESERVATION_SIZE - 1U] = 0xa7,
    };

typedef struct RaceCall {
    const uint8_t *main_reservation;
    int result;
} RaceCall;

static _Atomic uint32_t g_ready;
static _Atomic uint32_t g_start;

static void *RacePublisher(void *opaque)
{
    RaceCall *call = (RaceCall *)opaque;
    atomic_fetch_add_explicit(&g_ready, UINT32_C(1), memory_order_release);
    while (atomic_load_explicit(&g_start, memory_order_acquire) == 0U) {
        sched_yield();
    }
    call->result = WLTP_PublishMainThreadTemplate(call->main_reservation);
    return NULL;
}

typedef struct Observation {
    uint64_t guard;
} Observation;

static void *Observe(void *opaque)
{
    Observation *observation = (Observation *)opaque;
    memcpy(&observation->guard,
           g_race_reservation + WLTP_GUARD_RELATIVE_OFFSET,
           sizeof(observation->guard));
    return NULL;
}

int main(void)
{
    const WltpProcessEpochSeedV1 seed = {
        .abi_version = WLTP_ABI_VERSION,
        .struct_size = sizeof(seed),
        .mode = WLTP_PROCESS_EPOCH_PARENT_BOOTSTRAP,
        .adapter_generation = UINT64_C(0x202),
        .process_epoch = UINT64_C(0x2002),
    };
    if (WLTP_BeginProcessEpoch(&seed, g_race_reservation) !=
        WLTP_PROCESS_EPOCH_OK) {
        return 1;
    }
    const uint64_t guard = UINT64_C(0x7e02b9d1634ca85f);
    memcpy(g_race_reservation + WLTP_GUARD_RELATIVE_OFFSET,
           &guard, sizeof(guard));

    RaceCall calls[2] = {
        {.main_reservation = g_race_reservation},
        {.main_reservation = g_race_reservation},
    };
    pthread_t threads[2];
    if (pthread_create(&threads[0], NULL, RacePublisher, &calls[0]) != 0 ||
        pthread_create(&threads[1], NULL, RacePublisher, &calls[1]) != 0) {
        return 2;
    }
    while (atomic_load_explicit(&g_ready, memory_order_acquire) != 2U) {
        sched_yield();
    }
    atomic_store_explicit(&g_start, UINT32_C(1), memory_order_release);
    if (pthread_join(threads[0], NULL) != 0 ||
        pthread_join(threads[1], NULL) != 0) {
        return 3;
    }
    const bool exact_once =
        (calls[0].result == WLTP_PUBLISH_OK &&
         calls[1].result == WLTP_PUBLISH_ALREADY_PUBLISHED) ||
        (calls[1].result == WLTP_PUBLISH_OK &&
         calls[0].result == WLTP_PUBLISH_ALREADY_PUBLISHED);
    if (!exact_once) {
        fprintf(stderr, "FAIL publisher race results=%d,%d\n",
                calls[0].result, calls[1].result);
        return 4;
    }

    Observation observation = {0};
    pthread_t observer;
    if (pthread_create(&observer, NULL, Observe, &observation) != 0 ||
        pthread_join(observer, NULL) != 0 || observation.guard != guard) {
        return 5;
    }
    puts("PASS process publisher exact-once race");
    return 0;
}
