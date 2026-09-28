/* Edge Case / FR-008: fork() must leave each side holding only its own channel endpoint —
 * parent must not still hold the child's fd, and vice versa (verified indirectly for the
 * child via the parent-observable fd count delta; the child side is covered by code review
 * of fork_capability_channel_create()'s close() calls plus this test's own successful I/O,
 * which would hang/fail if either side leaked the wrong end). */
#include "child_entry.h"
#include "epoch_registry.h"
#include "spawn_oracle.h"
#include "test_util.h"

#include <dirent.h>
#include <stdio.h>

static int count_open_fds(void) {
    DIR *d = opendir("/proc/self/fd");
    if (!d) {
        return -1;
    }
    int count = 0;
    struct dirent *entry;
    while ((entry = readdir(d)) != NULL) {
        if (entry->d_name[0] != '.') {
            count++;
        }
    }
    closedir(d);
    return count;
}

int main(void) {
    int before = count_open_fds();
    CHECK(before >= 0, "must be able to enumerate /proc/self/fd on Linux host");

    EpochRegistry *reg = epoch_registry_create(1);
    SpawnRequest *req = epoch_registry_new_request(reg, 1, "com.sample.fdcheck", "entry");

    CHECK(spawn_oracle_fork(reg, req, NULL) == SPAWN_SUCCESS, "fork should not early-reject");
    int after_fork = count_open_fds();
    /* parent must hold exactly ONE new fd (its own channel endpoint) — not two (it must have
     * closed the child's endpoint per FR-008) */
    CHECK(after_fork == before + 1,
          "parent must hold exactly 1 new fd after fork (its own channel endpoint), before=%d after=%d",
          before, after_fork);

    SpawnOutcome outcome = spawn_oracle_wait_ack(reg, req, 500, NULL);
    CHECK(outcome == SPAWN_SUCCESS, "expected SPAWN_SUCCESS, got %d", outcome);

    epoch_registry_destroy(reg);
    TEST_MAIN_EXIT();
}
