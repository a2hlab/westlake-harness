/* 每条真实 terminal failure 必须关闭 capability fd、终止 owned child，并保持
 * typed failure；synthetic ACK 测试不能因此 kill 任意占位 PID。 */
#include "child_entry.h"
#include "epoch_registry.h"
#include "spawn_oracle.h"
#include "test_util.h"

#include <errno.h>
#include <signal.h>

static void check_timeout_cleanup(void) {
    EpochRegistry *reg = epoch_registry_create(1);
    SpawnRequest *req = epoch_registry_new_request(reg, 1, "com.sample.timeout-cleanup", "entry");
    ChildEntryOptions opts = {
        .specialization_result = 0,
        .adapter_entry_result = 0,
        .skip_ack = true,
    };
    CHECK(spawn_oracle_fork(reg, req, &opts) == SPAWN_SUCCESS, "fork must start");
    pid_t child = req->expected_fork_pid;
    CHECK(spawn_oracle_wait_ack(reg, req, 100, NULL) == REJECT_TIMEOUT,
          "timeout must remain typed");
    CHECK(req->channel_fd == -1, "timeout must close parent capability fd");
    CHECK(!req->owns_child_process, "timeout must relinquish reaped child ownership");
    errno = 0;
    CHECK(kill(child, 0) == -1 && errno == ESRCH, "timeout child must be gone");
    epoch_registry_destroy(reg);
}

static void check_specialization_cleanup(void) {
    EpochRegistry *reg = epoch_registry_create(2);
    SpawnRequest *req = epoch_registry_new_request(reg, 2, "com.sample.spec-cleanup", "entry");
    ChildEntryOptions opts = {
        .specialization_result = -13,
        .adapter_entry_result = 0,
    };
    CHECK(spawn_oracle_fork(reg, req, &opts) == SPAWN_SUCCESS, "fork must start");
    CHECK(spawn_oracle_wait_ack(reg, req, 500, NULL) == REJECT_SPECIALIZATION_FAILED,
          "specialization external gate must fail closed");
    CHECK(req->channel_fd == -1, "specialization failure must close capability fd");
    CHECK(req->state == SPAWN_STATE_REJECTED, "specialization failure must be terminal");
    epoch_registry_destroy(reg);
}

static void check_registry_destroy_cleanup(void) {
    EpochRegistry *reg = epoch_registry_create(3);
    SpawnRequest *req = epoch_registry_new_request(reg, 3, "com.sample.destroy-cleanup", "entry");
    ChildEntryOptions opts = {
        .specialization_result = 0,
        .adapter_entry_result = 0,
        .skip_ack = true,
    };
    CHECK(spawn_oracle_fork(reg, req, &opts) == SPAWN_SUCCESS, "fork must start");
    pid_t child = req->expected_fork_pid;
    epoch_registry_destroy(reg);
    errno = 0;
    CHECK(kill(child, 0) == -1 && errno == ESRCH,
          "destroying registry must terminate and reap its pending owned child");
}

int main(void) {
    check_timeout_cleanup();
    check_specialization_cleanup();
    check_registry_destroy_cleanup();
    TEST_MAIN_EXIT();
}
