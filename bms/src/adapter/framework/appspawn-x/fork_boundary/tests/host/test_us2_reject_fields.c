/* FR-005: every ACK field is independently load-bearing. This file covers
 * generation / specialization_result / adapter_entry_result / adapter_entry — epoch is
 * covered by test_us3_orphan_reconcile's late-ACK scenario, fork_pid
 * by test_us2_reject_pidmismatch, and nonce by test_us2_reject_replay. Each sub-check builds
 * the ACK directly (no real child), isolating the field-validation contract exactly like
 * test_us2_reject_pidmismatch does. */
#include "epoch_registry.h"
#include "fork_capability.h"
#include "spawn_oracle.h"
#include "test_util.h"

#include <string.h>

static SpawnRequest *make_pending_request(EpochRegistry *reg, const char *bundle_name,
                                           int *out_parent_fd, int *out_child_fd,
                                           pid_t placeholder_pid) {
    SpawnRequest *req = epoch_registry_new_request(reg, 1, bundle_name, "entry");
    CHECK(fork_capability_channel_create(out_parent_fd, out_child_fd) == 0, "channel create failed");
    CHECK(epoch_registry_try_mark_forked(reg, req, placeholder_pid, *out_parent_fd),
          "mark_forked should succeed on a fresh PENDING_FORK request");
    return req;
}

static void fill_legit_ack(CapabilityAck *ack, EpochRegistry *reg, const SpawnRequest *req) {
    memset(ack, 0, sizeof(*ack));
    ack->epoch = epoch_registry_epoch(reg);
    ack->fork_pid = req->expected_fork_pid;
    memcpy(ack->nonce, req->nonce, SPAWN_NONCE_LEN);
    ack->generation = req->generation;
    ack->specialization_result = 0;
    ack->adapter_entry_result = 0;
    strncpy(ack->adapter_entry, req->adapter_entry, SPAWN_ADAPTER_ENTRY_LEN - 1);
}

static void check_generation_mismatch(EpochRegistry *reg) {
    int parent_fd, child_fd;
    SpawnRequest *req = make_pending_request(reg, "com.sample.gen", &parent_fd, &child_fd, 500001);
    CapabilityAck ack;
    fill_legit_ack(&ack, reg, req);
    ack.generation = req->generation + 1; /* the one deliberately wrong field */
    CHECK(fork_capability_send_ack(child_fd, &ack) == 0, "send_ack failed");
    SpawnOutcome outcome = spawn_oracle_wait_ack(reg, req, 200, NULL);
    CHECK(outcome == REJECT_GENERATION_MISMATCH, "expected REJECT_GENERATION_MISMATCH, got %d", outcome);
}

static void check_specialization_failed(EpochRegistry *reg) {
    int parent_fd, child_fd;
    SpawnRequest *req = make_pending_request(reg, "com.sample.spec", &parent_fd, &child_fd, 500002);
    CapabilityAck ack;
    fill_legit_ack(&ack, reg, req);
    ack.specialization_result = -1; /* the one deliberately wrong field */
    CHECK(fork_capability_send_ack(child_fd, &ack) == 0, "send_ack failed");
    SpawnOutcome outcome = spawn_oracle_wait_ack(reg, req, 200, NULL);
    CHECK(outcome == REJECT_SPECIALIZATION_FAILED, "expected REJECT_SPECIALIZATION_FAILED, got %d", outcome);
}

static void check_adapter_entry_mismatch(EpochRegistry *reg) {
    int parent_fd, child_fd;
    SpawnRequest *req = make_pending_request(reg, "com.sample.entry", &parent_fd, &child_fd, 500003);
    CapabilityAck ack;
    fill_legit_ack(&ack, reg, req);
    strncpy(ack.adapter_entry, "wrong::entry", SPAWN_ADAPTER_ENTRY_LEN - 1); /* deliberately wrong */
    CHECK(fork_capability_send_ack(child_fd, &ack) == 0, "send_ack failed");
    SpawnOutcome outcome = spawn_oracle_wait_ack(reg, req, 200, NULL);
    CHECK(outcome == REJECT_ADAPTER_ENTRY_MISMATCH, "expected REJECT_ADAPTER_ENTRY_MISMATCH, got %d", outcome);
}

static void check_adapter_entry_not_observed(EpochRegistry *reg) {
    int parent_fd, child_fd;
    SpawnRequest *req = make_pending_request(reg, "com.sample.entry.unreached",
                                              &parent_fd, &child_fd, 500004);
    CapabilityAck ack;
    fill_legit_ack(&ack, reg, req);
    ack.adapter_entry_result = -1; /* 真实 runtime entry 未被观察到 */
    CHECK(fork_capability_send_ack(child_fd, &ack) == 0, "send_ack failed");
    SpawnOutcome outcome = spawn_oracle_wait_ack(reg, req, 200, NULL);
    CHECK(outcome == REJECT_ADAPTER_ENTRY_MISMATCH,
          "adapter entry 未到达必须 fail closed，实际 outcome=%d", outcome);
}

int main(void) {
    EpochRegistry *reg = epoch_registry_create(1);
    check_generation_mismatch(reg);
    check_specialization_failed(reg);
    check_adapter_entry_mismatch(reg);
    check_adapter_entry_not_observed(reg);
    epoch_registry_destroy(reg);
    TEST_MAIN_EXIT();
}
