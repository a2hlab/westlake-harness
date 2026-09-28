/* Edge Case: child receives the request but never sends an ACK in time — parent must
 * return REJECT_TIMEOUT and must not hang. */
#include "child_entry.h"
#include "epoch_registry.h"
#include "spawn_oracle.h"
#include "test_util.h"

#include <time.h>

int main(void) {
    EpochRegistry *reg = epoch_registry_create(1);
    SpawnRequest *req = epoch_registry_new_request(reg, 1, "com.sample.slow", "entry");

    ChildEntryOptions opts = { .specialization_result = 0, .skip_ack = true };
    CHECK(spawn_oracle_fork(reg, req, &opts) == SPAWN_SUCCESS, "fork should not early-reject");

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    SpawnOutcome outcome = spawn_oracle_wait_ack(reg, req, /*timeout_ms=*/150, NULL);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    long elapsed_ms = (t1.tv_sec - t0.tv_sec) * 1000L + (t1.tv_nsec - t0.tv_nsec) / 1000000L;

    CHECK(outcome == REJECT_TIMEOUT, "expected REJECT_TIMEOUT, got %d", outcome);
    CHECK(req->state == SPAWN_STATE_REJECTED, "state must be REJECTED, got %d", req->state);
    /* must not hang far past the requested timeout (loose bound to avoid CI flakiness) */
    CHECK(elapsed_ms < 400, "wait_ack must not hang well past timeout_ms, took %ldms", elapsed_ms);

    epoch_registry_destroy(reg);
    TEST_MAIN_EXIT();
}
