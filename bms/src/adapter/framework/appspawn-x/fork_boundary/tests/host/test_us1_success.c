/* User Story 1: 10 个目标 arm64 il2cpp 游戏的 spawn 请求都能拿到有界 ACK 并被判定 success.
 * Also covers Acceptance Scenario P1-3: before the ACK arrives, the request must read as
 * pending, never as an optimistic success based on fork()'s return value alone. */
#include "epoch_registry.h"
#include "spawn_oracle.h"
#include "test_util.h"
#include "fixtures_games.h"

#include <stdio.h>
#include <string.h>

int main(void) {
    EpochRegistry *reg = epoch_registry_create(1);
    int success_count = 0;

    for (int i = 0; i < GAME_FIXTURE_COUNT; i++) {
        const GameFixture *fx = &kGameFixtures[i];
        SpawnRequest *req = epoch_registry_new_request(reg, /*generation=*/1,
                                                         fx->bundle_name,
                                                         "AndroidRuntime::start");

        SpawnOutcome fork_rc = spawn_oracle_fork(reg, req, NULL);
        CHECK(fork_rc == SPAWN_SUCCESS, "%s: spawn_oracle_fork should not early-reject", fx->label);

        /* Acceptance Scenario P1-3: right after fork(), before the ACK has been
         * processed, the request MUST read as pending — not success. This is the
         * direct negation of "fork() returning a PID is itself success". */
        CHECK(req->state == SPAWN_STATE_PENDING_ACK,
              "%s: state must be PENDING_ACK immediately after fork, not %d",
              fx->label, req->state);

        SpawnSuccessInfo info;
        memset(&info, 0, sizeof(info));
        SpawnOutcome outcome = spawn_oracle_wait_ack(reg, req, /*timeout_ms=*/500, &info);

        CHECK(outcome == SPAWN_SUCCESS, "%s: expected SPAWN_SUCCESS, got outcome=%d",
              fx->label, outcome);
        if (outcome != SPAWN_SUCCESS) {
            continue;
        }
        CHECK(info.pid > 0, "%s: success PID must be non-zero, got %d", fx->label, (int)info.pid);
        CHECK(strcmp(info.bundle_name, fx->bundle_name) == 0,
              "%s: success bundle_name mismatch: got '%s'", fx->label, info.bundle_name);
        CHECK(strlen(info.adapter_entry) > 0,
              "%s: ACK adapter_entry field must be non-empty", fx->label);

        fprintf(stdout, "[US1] %-32s -> SPAWN_SUCCESS pid=%d bundle=%s\n",
                fx->label, (int)info.pid, info.bundle_name);
        success_count++;
    }

    CHECK(success_count == GAME_FIXTURE_COUNT, "expected %d/%d successes, got %d",
          GAME_FIXTURE_COUNT, GAME_FIXTURE_COUNT, success_count);

    epoch_registry_destroy(reg);
    TEST_MAIN_EXIT();
}
