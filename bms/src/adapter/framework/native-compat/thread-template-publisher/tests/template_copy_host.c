#define _GNU_SOURCE

#include "westlake_thread_template_publisher.h"

#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/random.h>

enum {
    kReservationSize = 48,
    kGuardOffset = 24,
};

/* A file-backed TLS image is required; a pure .tbss image cannot be patched. */
__thread unsigned char g_main_tls_reservation[kReservationSize]
    __attribute__((aligned(16), tls_model("initial-exec"))) = {
        [0] = 0x51,
        [47] = 0xa7,
    };

typedef struct ThreadObservation {
    uint64_t expected;
    uint64_t observed;
    unsigned char first_canary;
    unsigned char last_canary;
} ThreadObservation;

static void *ObserveAtThreadStart(void *opaque)
{
    ThreadObservation *observation = (ThreadObservation *)opaque;
    memcpy(&observation->observed,
           &g_main_tls_reservation[kGuardOffset],
           sizeof(observation->observed));
    observation->first_canary = g_main_tls_reservation[0];
    observation->last_canary = g_main_tls_reservation[47];
    return NULL;
}

int main(void)
{
    const WltpProcessEpochSeedV1 seed = {
        .abi_version = WLTP_ABI_VERSION,
        .struct_size = sizeof(seed),
        .mode = WLTP_PROCESS_EPOCH_PARENT_BOOTSTRAP,
        .adapter_generation = UINT64_C(0x101),
        .process_epoch = UINT64_C(0x1001),
    };
    if (WLTP_BeginProcessEpoch(&seed, g_main_tls_reservation) !=
        WLTP_PROCESS_EPOCH_OK) {
        fprintf(stderr, "FAIL initial template generation reset\n");
        return 2;
    }
    uint64_t guard = UINT64_C(0);
    if (getrandom(&guard, sizeof(guard), 0) != (ssize_t)sizeof(guard) ||
        guard == UINT64_C(0)) {
        fprintf(stderr, "FAIL OS CSPRNG\n");
        return 3;
    }
    uint64_t current_before = UINT64_C(0);
    memcpy(&current_before, &g_main_tls_reservation[kGuardOffset],
           sizeof(current_before));
    if (current_before != UINT64_C(0)) {
        fprintf(stderr, "FAIL current TLS initial guard not zero\n");
        return 4;
    }

    /* Product order is MAIN admission first, then future-thread template. */
    memcpy(&g_main_tls_reservation[kGuardOffset], &guard, sizeof(guard));
    if (WLTP_PublishMainThreadTemplate(g_main_tls_reservation) !=
        WLTP_PUBLISH_OK) {
        fprintf(stderr, "FAIL template publisher\n");
        return 5;
    }
    if (WLTP_PublishMainThreadTemplate(g_main_tls_reservation) !=
        WLTP_PUBLISH_ALREADY_PUBLISHED) {
        fprintf(stderr, "FAIL second template publication accepted\n");
        return 6;
    }

    ThreadObservation observation = {.expected = guard};
    pthread_t thread;
    if (pthread_create(&thread, NULL, ObserveAtThreadStart, &observation) != 0 ||
        pthread_join(thread, NULL) != 0) {
        fprintf(stderr, "FAIL pthread lifecycle\n");
        return 8;
    }
    if (observation.observed != observation.expected ||
        observation.first_canary != 0x51 ||
        observation.last_canary != 0xa7) {
        fprintf(stderr, "FAIL new-thread TLS template copy\n");
        return 9;
    }
    puts("PASS host PT_TLS template copied before thread start");
    return 0;
}
