#include "spawn_oracle.h"
#include "epoch_registry.h"
#include "fork_capability.h"
#include "child_entry.h"

#include <errno.h>
#include <string.h>
#include <signal.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static const ChildEntryOptions kDefaultChildOptions = {
    .specialization_result = 0,
    .adapter_entry_result = 0,
    .inject_delay_after_pdeathsig = false,
    .delay_after_pdeathsig_ms = 0,
    .skip_ack = false,
    .exit_before_ack = false,
};

static void close_request_channel(SpawnRequest *req) {
    if (req->channel_fd >= 0) {
        close(req->channel_fd);
        req->channel_fd = -1;
    }
}

static void terminate_owned_child(SpawnRequest *req) {
    if (!req->owns_child_process || req->expected_fork_pid <= 0) {
        return;
    }
    int status;
    pid_t waited = waitpid(req->expected_fork_pid, &status, WNOHANG);
    if (waited == 0) {
        kill(req->expected_fork_pid, SIGKILL);
        do {
            waited = waitpid(req->expected_fork_pid, &status, 0);
        } while (waited < 0 && errno == EINTR);
    }
    req->owns_child_process = false;
}

static void reap_owned_host_child_after_success(SpawnRequest *req) {
    if (!req->owns_child_process || req->expected_fork_pid <= 0) {
        return;
    }
    /* child_entry_run() is a host protocol fixture and always exits immediately
     * after ACK. Production integration transfers the live child to AppMgr
     * instead of using this fixture function. Reap here so developer tests do
     * not leave successful fixture children as zombies. */
    int status;
    pid_t waited;
    do {
        waited = waitpid(req->expected_fork_pid, &status, 0);
    } while (waited < 0 && errno == EINTR);
    req->owns_child_process = false;
}

static SpawnOutcome finish_request(SpawnRequest *req, SpawnOutcome outcome) {
    if (outcome != SPAWN_SUCCESS) {
        terminate_owned_child(req);
    } else {
        reap_owned_host_child_after_success(req);
    }
    close_request_channel(req);
    req->outcome = outcome;
    req->state = (outcome == SPAWN_SUCCESS) ? SPAWN_STATE_ACKED_SUCCESS : SPAWN_STATE_REJECTED;
    return outcome;
}

/* NOTE: SPAWN_SUCCESS (0) returned by spawn_oracle_fork() means "no early
 * rejection, request is now PENDING_ACK" — NOT the final success verdict.
 * Only spawn_oracle_wait_ack()'s return value is the authoritative outcome
 * (FR-006: fork() succeeding is never, by itself, sufficient). */
SpawnOutcome spawn_oracle_fork(EpochRegistry *reg, SpawnRequest *req,
                                const ChildEntryOptions *child_opts) {
#ifndef MUTANT_FR007_ALLOW_DOUBLE_FORK
    if (atomic_exchange(&req->fork_claimed, true) ||
        req->state != SPAWN_STATE_PENDING_FORK) {
        /* FR-007: a request that already left PENDING_FORK (already forked,
         * or already terminal) may not be forked again. No real fork()
         * syscall is issued on this path. */
        req->outcome = REJECT_DOUBLE_FORK;
        return REJECT_DOUBLE_FORK;
    }
#endif

    int parent_fd, child_fd;
    if (fork_capability_channel_create(&parent_fd, &child_fd) != 0) {
        req->outcome = REJECT_FORK_FAILED;
        req->state = SPAWN_STATE_REJECTED;
        return REJECT_FORK_FAILED;
    }

    pid_t parent_pid_at_fork = getpid();
    pid_t pid = fork();
    if (pid < 0) {
        close(parent_fd);
        close(child_fd);
        req->outcome = REJECT_FORK_FAILED;
        req->state = SPAWN_STATE_REJECTED;
        return REJECT_FORK_FAILED;
    }

    if (pid == 0) {
        /* child branch: close the parent's endpoint immediately (FR-008 —
         * unused fd closed in every process), then hand off. Never returns. */
        close(parent_fd);
        child_entry_run(child_fd, parent_pid_at_fork, req,
                         child_opts ? child_opts : &kDefaultChildOptions);
        /* unreachable */
    }

    /* parent branch: close the child's endpoint immediately (FR-008). */
#ifndef MUTANT_FR008_LEAK_CHILD_FD_IN_PARENT
    close(child_fd);
#else
    /* MUTANT: parent "forgets" to close its copy of the child's channel
     * endpoint. test_edge_fd_leak.c's fd-count assertion (after_fork ==
     * before + 1) must catch this — an unclosed child_fd makes it +2. */
    (void)child_fd;
#endif
    epoch_registry_try_mark_forked(reg, req, pid, parent_fd);
    req->owns_child_process = true;

#ifdef MUTANT_FR006_REPORT_SUCCESS_ON_FORK
    /* MUTANT: reinstates the explicitly rejected pattern — reports success from
     * fork()'s return value alone, without waiting for the capability ACK. */
    req->outcome = SPAWN_SUCCESS;
    req->state = SPAWN_STATE_ACKED_SUCCESS;
#endif

    return SPAWN_SUCCESS;
}

static SpawnOutcome validate_and_finalize(EpochRegistry *reg, SpawnRequest *req,
                                           const CapabilityAck *ack,
                                           SpawnSuccessInfo *out_info) {
    SpawnOutcome outcome;

#ifdef MUTANT_FR005_SKIP_FIELD_epoch
    bool epoch_ok = true;
#else
    bool epoch_ok = (ack->epoch == epoch_registry_epoch(reg));
#endif
#ifdef MUTANT_FR005_SKIP_FIELD_pid
    bool pid_ok = true;
#else
    bool pid_ok = (ack->fork_pid == req->expected_fork_pid);
#endif
    bool nonce_value_ok = (memcmp(ack->nonce, req->nonce, SPAWN_NONCE_LEN) == 0);
    /* Only "spend" (consume) the nonce once epoch/PID/nonce-value have already
     * been confirmed to belong to THIS legitimate in-flight request. Consuming
     * unconditionally (i.e. before those checks) would let an illegitimate ACK
     * that merely guesses/replays the correct nonce bytes — but carries the
     * wrong epoch or PID — burn the nonce anyway, causing the real child's
     * later, correct ACK to be spuriously rejected as REJECT_NONCE_REPLAYED. */
    bool nonce_fresh = true;
#if defined(MUTANT_FR002_SKIP_NONCE_CHECK)
    (void)nonce_registry_try_consume; /* keep symbol referenced under this mutant build */
#else
    if (epoch_ok && pid_ok && nonce_value_ok) {
        nonce_fresh = nonce_registry_try_consume(reg, ack->nonce);
    }
#endif
#ifdef MUTANT_FR005_SKIP_FIELD_generation
    bool generation_ok = true;
#else
    bool generation_ok = (ack->generation == req->generation);
#endif
#ifdef MUTANT_FR005_SKIP_FIELD_specialization
    bool specialization_ok = true;
#else
    bool specialization_ok = (ack->specialization_result == 0);
#endif
#ifdef MUTANT_FR005_SKIP_FIELD_adapter_entry
    bool adapter_entry_ok = true;
#else
    bool adapter_entry_ok =
        (ack->adapter_entry_result == 0) &&
        (strncmp(ack->adapter_entry, req->adapter_entry, SPAWN_ADAPTER_ENTRY_LEN) == 0);
#endif

    if (!epoch_ok) {
        outcome = REJECT_EPOCH_MISMATCH;
    } else if (!pid_ok) {
        outcome = REJECT_PID_MISMATCH;
    } else if (!nonce_value_ok) {
        outcome = REJECT_NONCE_UNKNOWN;
    } else if (!nonce_fresh) {
        outcome = REJECT_NONCE_REPLAYED;
    } else if (!generation_ok) {
        outcome = REJECT_GENERATION_MISMATCH;
    } else if (!specialization_ok) {
        outcome = REJECT_SPECIALIZATION_FAILED;
    } else if (!adapter_entry_ok) {
        outcome = REJECT_ADAPTER_ENTRY_MISMATCH;
    } else {
        outcome = SPAWN_SUCCESS;
    }

    if (outcome == SPAWN_SUCCESS && out_info) {
        out_info->pid = req->expected_fork_pid;
        strncpy(out_info->bundle_name, req->bundle_name, SPAWN_BUNDLE_NAME_LEN - 1);
        strncpy(out_info->adapter_entry, req->adapter_entry, SPAWN_ADAPTER_ENTRY_LEN - 1);
    }
    return finish_request(req, outcome);
}

static long elapsed_ms_since(const struct timespec *start) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (now.tv_sec - start->tv_sec) * 1000L + (now.tv_nsec - start->tv_nsec) / 1000000L;
}

SpawnOutcome spawn_oracle_wait_ack(EpochRegistry *reg, SpawnRequest *req, int timeout_ms,
                                    SpawnSuccessInfo *out_info) {
    if (atomic_exchange(&req->wait_claimed, true)) {
        return REJECT_CONCURRENT_WAITER;
    }
    if (req->state != SPAWN_STATE_PENDING_ACK) {
        return req->outcome; /* already terminal (e.g. spawn_oracle_fork rejected it) */
    }

    struct timespec start;
    clock_gettime(CLOCK_MONOTONIC, &start);
    const int slice_ms = 20;

    for (;;) {
#ifdef MUTANT_FR009_NO_TIMEOUT
        /* MUTANT: the timeout guard is broken — instead of failing closed at
         * timeout_ms, it fails OPEN (reports success) after a bounded extra
         * wait, so this build stays CI-safe while still being wrong. */
        long remaining = (timeout_ms * 5) - elapsed_ms_since(&start);
        if (remaining <= 0) {
            req->outcome = SPAWN_SUCCESS;
            req->state = SPAWN_STATE_ACKED_SUCCESS;
            return SPAWN_SUCCESS;
        }
#else
        long remaining = timeout_ms - elapsed_ms_since(&start);
        if (remaining <= 0) {
            return finish_request(req, REJECT_TIMEOUT);
        }
#endif
        int this_slice = (remaining < slice_ms) ? (int)remaining : slice_ms;

        CapabilityAck ack;
        int rc = fork_capability_recv_ack(req->channel_fd, this_slice, &ack);
        if (rc == 1) {
            return validate_and_finalize(reg, req, &ack, out_info);
        }
        if (rc == -1) {
            return finish_request(req, REJECT_MALFORMED_ACK);
        }

        /* rc == 0 (timeout, no data yet) or rc == -2 (peer closed the channel
         * without sending anything, e.g. child died before ACKing) — either
         * way, check child health before looping back (research.md R6). A
         * closed channel with no ACK is a strong signal the child is gone,
         * but the authoritative check is always waitpid(), not the channel
         * state alone. */
        int status;
        pid_t w = waitpid(req->expected_fork_pid, &status, WNOHANG);
        if (w == req->expected_fork_pid) {
            if (WIFEXITED(status) && WEXITSTATUS(status) == 0) {
                /* child exited cleanly; give the socket buffer one last
                 * non-blocking chance in case the ACK was sent just before
                 * exit and this waitpid() raced ahead of the poll() above */
                rc = fork_capability_recv_ack(req->channel_fd, 0, &ack);
                if (rc == 1) {
                    return validate_and_finalize(reg, req, &ack, out_info);
                }
            }
            req->child_wait_status = status;
            req->owns_child_process = false;
            return finish_request(req, REJECT_CHILD_ERROR);
        }
    }
}
