/* 多个 generation-bound 请求同时处于 PENDING_ACK 时，PID、nonce、channel 与
 * terminal receipt 必须保持逐请求隔离；本测试只验证 host 协议模型。 */
#include "epoch_registry.h"
#include "fork_capability.h"
#include "spawn_oracle.h"
#include "test_util.h"

#include <stdio.h>
#include <pthread.h>
#include <string.h>
#include <unistd.h>

enum { REQUEST_COUNT = 8 };

typedef struct {
    EpochRegistry *reg;
    SpawnRequest *req;
    pid_t expected_pid;
    pthread_barrier_t *start;
    SpawnOutcome outcome;
    SpawnSuccessInfo info;
} ConcurrentWait;

static void *wait_independent_request(void *opaque) {
    ConcurrentWait *wait = opaque;
    pthread_barrier_wait(wait->start);
    wait->outcome = spawn_oracle_wait_ack(wait->reg, wait->req, 1000, &wait->info);
    return NULL;
}

int main(void) {
    EpochRegistry *reg = epoch_registry_create(77);
    SpawnRequest *requests[REQUEST_COUNT] = {0};
    pid_t pids[REQUEST_COUNT] = {0};

    for (int i = 0; i < REQUEST_COUNT; ++i) {
        char bundle[SPAWN_BUNDLE_NAME_LEN];
        snprintf(bundle, sizeof(bundle), "com.sample.concurrent.%d", i);
        requests[i] = epoch_registry_new_request(reg, (uint32_t)(1000 + i), bundle, "adapter-entry");
        CHECK(spawn_oracle_fork(reg, requests[i], NULL) == SPAWN_SUCCESS,
              "request %d fork should enter PENDING_ACK", i);
        CHECK(requests[i]->state == SPAWN_STATE_PENDING_ACK,
              "request %d state=%d, expected PENDING_ACK", i, requests[i]->state);
        pids[i] = requests[i]->expected_fork_pid;
        CHECK(pids[i] > 0, "request %d PID must be positive", i);
        for (int j = 0; j < i; ++j) {
            CHECK(pids[i] != pids[j], "requests %d/%d must not share PID %d", i, j, (int)pids[i]);
            CHECK(memcmp(requests[i]->nonce, requests[j]->nonce, SPAWN_NONCE_LEN) != 0,
                  "requests %d/%d must not share nonce", i, j);
            CHECK(requests[i]->channel_fd != requests[j]->channel_fd,
                  "requests %d/%d must not share parent channel fd", i, j);
        }
    }

    pthread_barrier_t start;
    pthread_t threads[REQUEST_COUNT];
    ConcurrentWait waits[REQUEST_COUNT] = {0};
    CHECK(pthread_barrier_init(&start, NULL, REQUEST_COUNT + 1) == 0,
          "concurrent start barrier init");
    for (int i = 0; i < REQUEST_COUNT; ++i) {
        waits[i].reg = reg;
        waits[i].req = requests[i];
        waits[i].expected_pid = pids[i];
        waits[i].start = &start;
        CHECK(pthread_create(&threads[i], NULL, wait_independent_request, &waits[i]) == 0,
              "create independent waiter %d", i);
    }
    pthread_barrier_wait(&start);
    for (int i = 0; i < REQUEST_COUNT; ++i) {
        pthread_join(threads[i], NULL);
        CHECK(waits[i].outcome == SPAWN_SUCCESS,
              "request %d must independently complete", i);
        CHECK(waits[i].info.pid == pids[i], "request %d receipt PID mismatch", i);
        CHECK(strcmp(waits[i].info.bundle_name, requests[i]->bundle_name) == 0,
              "request %d receipt bundle mismatch", i);
        CHECK(requests[i]->channel_fd == -1,
              "request %d terminal channel must be closed", i);
        CHECK(!requests[i]->owns_child_process,
              "request %d successful host child must be reaped", i);
    }
    pthread_barrier_destroy(&start);

    /* 多 in-flight 负控：A 的 cross-generation ACK 失败不得污染 B。 */
    SpawnRequest *bad = epoch_registry_new_request(reg, 9001, "com.sample.bad", "entry");
    SpawnRequest *good = epoch_registry_new_request(reg, 9002, "com.sample.good", "entry");
    int bad_parent, bad_child, good_parent, good_child;
    CHECK(fork_capability_channel_create(&bad_parent, &bad_child) == 0, "bad channel create");
    CHECK(fork_capability_channel_create(&good_parent, &good_child) == 0, "good channel create");
    CHECK(epoch_registry_try_mark_forked(reg, bad, 510001, bad_parent), "mark bad pending");
    CHECK(epoch_registry_try_mark_forked(reg, good, 510002, good_parent), "mark good pending");

    CapabilityAck bad_ack = {0};
    bad_ack.epoch = epoch_registry_epoch(reg);
    bad_ack.fork_pid = 510001;
    memcpy(bad_ack.nonce, bad->nonce, SPAWN_NONCE_LEN);
    bad_ack.generation = good->generation; /* deliberate cross-request generation */
    bad_ack.specialization_result = 0;
    bad_ack.adapter_entry_result = 0;
    strcpy(bad_ack.adapter_entry, "entry");
    CHECK(fork_capability_send_ack(bad_child, &bad_ack) == 0, "send bad ACK");
    CHECK(spawn_oracle_wait_ack(reg, bad, 200, NULL) == REJECT_GENERATION_MISMATCH,
          "cross-generation ACK must fail closed");

    CapabilityAck good_ack = {0};
    good_ack.epoch = epoch_registry_epoch(reg);
    good_ack.fork_pid = 510002;
    memcpy(good_ack.nonce, good->nonce, SPAWN_NONCE_LEN);
    good_ack.generation = good->generation;
    good_ack.specialization_result = 0;
    good_ack.adapter_entry_result = 0;
    strcpy(good_ack.adapter_entry, "entry");
    CHECK(fork_capability_send_ack(good_child, &good_ack) == 0, "send good ACK");
    SpawnSuccessInfo good_info = {0};
    CHECK(spawn_oracle_wait_ack(reg, good, 200, &good_info) == SPAWN_SUCCESS,
          "bad request must not contaminate independent pending request");
    CHECK(good_info.pid == 510002, "good receipt PID must remain isolated");
    close(bad_child);
    close(good_child);

    epoch_registry_destroy(reg);
    TEST_MAIN_EXIT();
}
