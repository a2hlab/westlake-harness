/* User Story 2 / Acceptance Scenario 2: an ACK whose fork_pid field does not match the
 * request's expected_fork_pid must be rejected as REJECT_PID_MISMATCH — even when every
 * other field (epoch/nonce/generation/specialization/adapter_entry) is otherwise legitimate.
 * This isolates the fork_pid check itself: the channel is driven directly (no real second
 * process), which is a valid independent test of the ACK-validation contract in
 * contracts/capability_ack.md step 3, distinct from the process-lifecycle tests in US1/US3. */
#include "epoch_registry.h"
#include "fork_capability.h"
#include "spawn_oracle.h"
#include "test_util.h"

#include <string.h>

int main(void) {
    EpochRegistry *reg = epoch_registry_create(1);
    SpawnRequest *req = epoch_registry_new_request(reg, 1, "com.sample.target", "entry");

    int parent_fd, child_fd;
    CHECK(fork_capability_channel_create(&parent_fd, &child_fd) == 0, "channel create failed");

    const pid_t real_pid = 424242;   /* placeholder — this test exercises field validation,
                                       * not process lifecycle */
    const pid_t wrong_pid = 424243;
    CHECK(epoch_registry_try_mark_forked(reg, req, real_pid, parent_fd),
          "mark_forked should succeed on a fresh PENDING_FORK request");

    CapabilityAck ack;
    memset(&ack, 0, sizeof(ack));
    ack.epoch = epoch_registry_epoch(reg);
    ack.fork_pid = wrong_pid;   /* the one deliberately wrong field */
    memcpy(ack.nonce, req->nonce, SPAWN_NONCE_LEN);
    ack.generation = req->generation;
    ack.specialization_result = 0;
    strncpy(ack.adapter_entry, req->adapter_entry, SPAWN_ADAPTER_ENTRY_LEN - 1);

    CHECK(fork_capability_send_ack(child_fd, &ack) == 0, "send_ack failed");

    SpawnOutcome outcome = spawn_oracle_wait_ack(reg, req, 200, NULL);
    CHECK(outcome == REJECT_PID_MISMATCH, "expected REJECT_PID_MISMATCH, got %d", outcome);
    CHECK(req->state == SPAWN_STATE_REJECTED, "state must be REJECTED, got %d", req->state);

    epoch_registry_destroy(reg);
    TEST_MAIN_EXIT();
}
