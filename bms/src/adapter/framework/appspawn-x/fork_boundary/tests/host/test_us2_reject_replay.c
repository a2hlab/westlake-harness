/* User Story 2 / Acceptance Scenario 1: a nonce already consumed by a prior successful
 * request must be rejected as REJECT_NONCE_REPLAYED when reused, never accepted again. */
#include "epoch_registry.h"
#include "spawn_oracle.h"
#include "test_util.h"

#include <string.h>

int main(void) {
    EpochRegistry *reg = epoch_registry_create(1);

    /* First request: goes through normally and succeeds, consuming its nonce. */
    SpawnRequest *req1 = epoch_registry_new_request(reg, 1, "com.sample.first", "entry");
    CHECK(spawn_oracle_fork(reg, req1, NULL) == SPAWN_SUCCESS, "req1 fork should not early-reject");
    SpawnOutcome rc1 = spawn_oracle_wait_ack(reg, req1, 500, NULL);
    CHECK(rc1 == SPAWN_SUCCESS, "req1 expected SPAWN_SUCCESS, got %d", rc1);

    /* Second request: deliberately reuse req1's already-consumed nonce (the request's own
     * generated nonce is overwritten before fork so the real child ACKs with the replayed
     * value — this exercises the exact wire path an attacker replaying a captured ACK
     * would take, not just the in-memory comparison). */
    SpawnRequest *req2 = epoch_registry_new_request(reg, 1, "com.sample.second", "entry");
    memcpy(req2->nonce, req1->nonce, SPAWN_NONCE_LEN);

    CHECK(spawn_oracle_fork(reg, req2, NULL) == SPAWN_SUCCESS, "req2 fork should not early-reject");
    SpawnOutcome rc2 = spawn_oracle_wait_ack(reg, req2, 500, NULL);
    CHECK(rc2 == REJECT_NONCE_REPLAYED, "req2 expected REJECT_NONCE_REPLAYED, got %d", rc2);
    CHECK(req2->state == SPAWN_STATE_REJECTED, "req2 state must be REJECTED, got %d", req2->state);

    epoch_registry_destroy(reg);
    TEST_MAIN_EXIT();
}
