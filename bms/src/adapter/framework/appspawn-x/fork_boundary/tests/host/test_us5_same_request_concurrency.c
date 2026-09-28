/* 同一 request 的 wait/finalize 必须只有一个消费者；竞争者不能重复 poll、close、
 * kill 或覆盖 terminal outcome。 */
#include "epoch_registry.h"
#include "spawn_oracle.h"
#include "test_util.h"

#include <pthread.h>

typedef struct {
    EpochRegistry *reg;
    SpawnRequest *req;
    SpawnOutcome outcome;
} WaitArgs;

static void *wait_once(void *opaque) {
    WaitArgs *args = opaque;
    args->outcome = spawn_oracle_wait_ack(args->reg, args->req, 1000, NULL);
    return NULL;
}

int main(void) {
    EpochRegistry *reg = epoch_registry_create(88);
    SpawnRequest *req = epoch_registry_new_request(reg, 321, "com.sample.same-request", "entry");
    CHECK(spawn_oracle_fork(reg, req, NULL) == SPAWN_SUCCESS, "fork must start");

    WaitArgs a = { .reg = reg, .req = req };
    WaitArgs b = { .reg = reg, .req = req };
    pthread_t ta, tb;
    CHECK(pthread_create(&ta, NULL, wait_once, &a) == 0, "create waiter A");
    CHECK(pthread_create(&tb, NULL, wait_once, &b) == 0, "create waiter B");
    pthread_join(ta, NULL);
    pthread_join(tb, NULL);

    int successes = (a.outcome == SPAWN_SUCCESS) + (b.outcome == SPAWN_SUCCESS);
    int rejected = (a.outcome == REJECT_CONCURRENT_WAITER) +
                   (b.outcome == REJECT_CONCURRENT_WAITER);
    CHECK(successes == 1, "exactly one waiter must finalize success, got %d", successes);
    CHECK(rejected == 1, "exactly one waiter must be rejected, got %d", rejected);
    CHECK(req->state == SPAWN_STATE_ACKED_SUCCESS, "terminal success must not be overwritten");
    CHECK(req->channel_fd == -1, "single finalizer must close channel");
    CHECK(!req->owns_child_process, "successful fixture child must be reaped once");

    epoch_registry_destroy(reg);
    TEST_MAIN_EXIT();
}
