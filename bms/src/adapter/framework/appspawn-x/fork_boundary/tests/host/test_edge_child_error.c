/* Edge Case: child terminates abnormally before sending an ACK — parent must return
 * REJECT_CHILD_ERROR (not hang until timeout, and not misreport as success). */
#include "child_entry.h"
#include "epoch_registry.h"
#include "spawn_oracle.h"
#include "test_util.h"

int main(void) {
    EpochRegistry *reg = epoch_registry_create(1);
    SpawnRequest *req = epoch_registry_new_request(reg, 1, "com.sample.crashy", "entry");

    ChildEntryOptions opts = { .specialization_result = 0, .exit_before_ack = true };
    CHECK(spawn_oracle_fork(reg, req, &opts) == SPAWN_SUCCESS, "fork should not early-reject");

    /* generous timeout: this must resolve quickly via waitpid, not via timing out */
    SpawnOutcome outcome = spawn_oracle_wait_ack(reg, req, /*timeout_ms=*/2000, NULL);

    CHECK(outcome == REJECT_CHILD_ERROR, "expected REJECT_CHILD_ERROR, got %d", outcome);
    CHECK(req->state == SPAWN_STATE_REJECTED, "state must be REJECTED, got %d", req->state);
    CHECK(req->child_wait_status != 0, "child_wait_status must be recorded for diagnosis");

    epoch_registry_destroy(reg);
    TEST_MAIN_EXIT();
}
