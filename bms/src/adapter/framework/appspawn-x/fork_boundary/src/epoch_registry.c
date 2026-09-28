#include "epoch_registry.h"
#include "nonce.h"

#include <errno.h>
#include <pthread.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define REGISTRY_CAPACITY 256

struct EpochRegistry {
    uint64_t epoch;
    NonceSet *nonces;
    pthread_mutex_t nonce_mutex;
    SpawnRequest requests[REGISTRY_CAPACITY];
    size_t count;
    uint64_t next_request_id;
};

EpochRegistry *epoch_registry_create(uint64_t epoch) {
    EpochRegistry *reg = calloc(1, sizeof(EpochRegistry));
    if (!reg) {
        abort();
    }
    reg->epoch = epoch;
    reg->nonces = nonce_set_create();
    if (pthread_mutex_init(&reg->nonce_mutex, NULL) != 0) {
        nonce_set_destroy(reg->nonces);
        free(reg);
        abort();
    }
    reg->next_request_id = 1;
    return reg;
}

void epoch_registry_destroy(EpochRegistry *reg) {
    if (!reg) return;
    /* Close every parent-side channel fd still on record — including ones
     * belonging to requests that already reached a terminal state
     * (ACKED_SUCCESS/REJECTED/RECONCILED). Those fds were never closed
     * anywhere else once the request finished, so without this loop every
     * completed request leaked one fd for the lifetime of the registry. */
    for (size_t i = 0; i < reg->count; i++) {
        SpawnRequest *req = &reg->requests[i];
        if (req->channel_fd >= 0) {
            close(req->channel_fd);
            req->channel_fd = -1;
        }
        /* Registry teardown is an ownership boundary. A request created by
         * spawn_oracle_fork() must never leave a live/zombie child behind just
         * because the caller destroys the registry before wait_ack(). Synthetic
         * protocol fixtures have owns_child_process=false and are never killed. */
        if (req->owns_child_process && req->expected_fork_pid > 0) {
            int status;
            pid_t waited = waitpid(req->expected_fork_pid, &status, WNOHANG);
            if (waited == 0) {
                (void)kill(req->expected_fork_pid, SIGKILL);
                do {
                    waited = waitpid(req->expected_fork_pid, &status, 0);
                } while (waited < 0 && errno == EINTR);
            }
            req->owns_child_process = false;
        }
    }
    pthread_mutex_destroy(&reg->nonce_mutex);
    nonce_set_destroy(reg->nonces);
    free(reg);
}

uint64_t epoch_registry_epoch(const EpochRegistry *reg) {
    return reg->epoch;
}

SpawnRequest *epoch_registry_new_request(EpochRegistry *reg, uint32_t generation,
                                          const char *bundle_name,
                                          const char *adapter_entry) {
    if (reg->count >= REGISTRY_CAPACITY) {
        abort(); /* this round's fixture set never approaches this bound */
    }
    SpawnRequest *req = &reg->requests[reg->count++];
    memset(req, 0, sizeof(*req));
    req->request_id = reg->next_request_id++;
    req->epoch = reg->epoch;
    req->generation = generation;
    strncpy(req->bundle_name, bundle_name, SPAWN_BUNDLE_NAME_LEN - 1);
    strncpy(req->adapter_entry, adapter_entry, SPAWN_ADAPTER_ENTRY_LEN - 1);
    nonce_generate(req->nonce);
    req->channel_fd = -1;
    atomic_init(&req->fork_claimed, false);
    atomic_init(&req->wait_claimed, false);
    req->state = SPAWN_STATE_PENDING_FORK;
    return req;
}

bool epoch_registry_try_mark_forked(EpochRegistry *reg, SpawnRequest *req,
                                     pid_t fork_pid, int parent_channel_fd) {
    (void)reg;
    if (req->state != SPAWN_STATE_PENDING_FORK) {
        /* FR-007: already forked (or already terminal) -> reject second fork */
        return false;
    }
    req->expected_fork_pid = fork_pid;
    req->channel_fd = parent_channel_fd;
    req->state = SPAWN_STATE_PENDING_ACK;
    return true;
}

SpawnRequest *epoch_registry_find_pending_by_pid(EpochRegistry *reg, pid_t fork_pid) {
    for (size_t i = 0; i < reg->count; i++) {
        SpawnRequest *req = &reg->requests[i];
        if (req->state == SPAWN_STATE_PENDING_ACK && req->expected_fork_pid == fork_pid) {
            return req;
        }
    }
    return NULL;
}

bool nonce_registry_try_consume(EpochRegistry *reg, const uint8_t nonce[SPAWN_NONCE_LEN]) {
    pthread_mutex_lock(&reg->nonce_mutex);
    bool consumed = nonce_set_try_consume(reg->nonces, nonce);
    pthread_mutex_unlock(&reg->nonce_mutex);
    return consumed;
}

int epoch_registry_reconcile(EpochRegistry *new_reg, EpochRegistry *old_reg) {
    (void)new_reg; /* new_reg intentionally starts from an empty table (research.md R3):
                     * reconcile only tears down old_reg's orphans, it does not copy
                     * any state forward. */
    int reconciled = 0;
#ifdef MUTANT_FR003_SKIP_EPOCH_RECONCILE
    /* MUTANT: reconcile is a no-op — old-epoch orphans are left running and
     * never marked RECONCILED. */
    (void)old_reg;
#else
    for (size_t i = 0; i < old_reg->count; i++) {
        SpawnRequest *req = &old_reg->requests[i];
        if (req->state != SPAWN_STATE_PENDING_ACK) {
            continue;
        }
        pid_t target = req->expected_fork_pid;
        bool confirmed_gone = false;
        if (kill(target, SIGKILL) == 0) {
            /* kill() succeeded: reap it, retrying across EINTR. Only two
             * waitpid() outcomes count as "confirmed gone": w == target (we
             * reaped it ourselves) or w == -1 && errno == ECHILD (something
             * else already reaped it — still means the process is gone).
             * Any other waitpid() result (unexpected errno, or an unlikely
             * w == 0 despite the blocking call) is NOT treated as confirmed —
             * codex round 2 correctly flagged that silently falling through
             * to RECONCILED here, without checking what waitpid() actually
             * returned, could mask a still-alive orphan. */
            int status;
            pid_t w;
            do {
                w = waitpid(target, &status, 0);
            } while (w == -1 && errno == EINTR);
            confirmed_gone = (w == target) || (w == -1 && errno == ECHILD);
        } else if (errno == ESRCH) {
            /* kill() itself already reports "no such process" — the orphan
             * was already gone before we got here (e.g. it exited via its
             * own PDEATHSIG race). No waitpid() call needed/possible. */
            confirmed_gone = true;
        }
        /* else: kill() failed for a reason OTHER than "process already gone"
         * (e.g. EPERM: PID was reused by a process we no longer own, or some
         * other unexpected errno) — confirmed_gone stays false. */

        if (!confirmed_gone) {
            /* Unlike the original unconditional behavior, this entry is
             * intentionally left un-reconciled instead of being silently
             * marked RECONCILED (which would have risked either masking a
             * real leaked orphan or, worse, papering over a mistaken SIGKILL
             * sent to an unrelated reused PID). state stays PENDING_ACK, so
             * spawn_oracle_wait_ack()'s state gate — not req->outcome's
             * zero-initialized default — is what any caller must consult;
             * outcome is set anyway as defense-in-depth against a caller
             * reading the field directly without going through that gate. */
            req->outcome = REJECT_CHILD_ERROR;
            continue;
        }
        req->state = SPAWN_STATE_RECONCILED;
        reconciled++;
    }
#endif
    return reconciled;
}
