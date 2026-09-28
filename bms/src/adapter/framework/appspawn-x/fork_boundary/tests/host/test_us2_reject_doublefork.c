/* User Story 2 / Acceptance Scenario 3: a second fork() attempt on a request that already
 * left PENDING_FORK must be rejected as REJECT_DOUBLE_FORK, and must not execute a second
 * real fork() — the original in-flight request must be left completely unaffected and able
 * to complete normally afterwards. */
#include "epoch_registry.h"
#include "spawn_oracle.h"
#include "test_util.h"

int main(void) {
    EpochRegistry *reg = epoch_registry_create(1);
    SpawnRequest *req = epoch_registry_new_request(reg, 1, "com.sample.target", "entry");

    SpawnOutcome first = spawn_oracle_fork(reg, req, NULL);
    CHECK(first == SPAWN_SUCCESS, "first fork should not early-reject, got %d", first);
    CHECK(req->state == SPAWN_STATE_PENDING_ACK, "state must be PENDING_ACK after first fork");
    pid_t first_pid = req->expected_fork_pid;

    SpawnOutcome second = spawn_oracle_fork(reg, req, NULL);
    CHECK(second == REJECT_DOUBLE_FORK, "second fork must be REJECT_DOUBLE_FORK, got %d", second);
    CHECK(req->expected_fork_pid == first_pid,
          "expected_fork_pid must be unchanged by the rejected second fork attempt");
    CHECK(req->state == SPAWN_STATE_PENDING_ACK,
          "state must remain PENDING_ACK (not corrupted by the rejected second fork)");

    /* Prove the original in-flight request still completes normally afterwards —
     * a broken double-fork guard would either corrupt this or leak a second child. */
    SpawnOutcome outcome = spawn_oracle_wait_ack(reg, req, 500, NULL);
    CHECK(outcome == SPAWN_SUCCESS, "original request must still succeed, got %d", outcome);

    epoch_registry_destroy(reg);
    TEST_MAIN_EXIT();
}
