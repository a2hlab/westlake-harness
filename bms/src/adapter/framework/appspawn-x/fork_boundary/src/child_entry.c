#include "child_entry.h"
#include "fork_capability.h"

#include <signal.h>
#include <string.h>
#include <sys/prctl.h>
#include <time.h>
#include <unistd.h>

enum {
    EXIT_PPID_MISMATCH = 111,
    EXIT_INJECTED_CRASH = 112,
};

static void sleep_ms(int ms) {
    struct timespec ts = { .tv_sec = ms / 1000, .tv_nsec = (long)(ms % 1000) * 1000000L };
    nanosleep(&ts, NULL);
}

void child_entry_run(int child_fd, pid_t parent_pid_at_fork, const SpawnRequest *req,
                      const ChildEntryOptions *opts) {
    /* research.md R4 / FR-004: set parent-death SIGKILL FIRST, before anything
     * else, to minimize the race window in which the parent could die
     * unnoticed. */
    prctl(PR_SET_PDEATHSIG, SIGKILL);

    if (opts->inject_delay_after_pdeathsig) {
        /* Edge Case: PDEATHSIG race window — a test can hold the child here to
         * simulate "parent died in the gap between prctl() and signal
         * delivery" and assert the getppid() recheck below still catches it. */
        sleep_ms(opts->delay_after_pdeathsig_ms);
    }

#ifndef MUTANT_FR004_SKIP_PID_RECHECK
    if (getppid() != parent_pid_at_fork) {
        /* parent already gone (or replaced) — do not proceed to ACK */
        _exit(EXIT_PPID_MISMATCH);
    }
#else
    (void)parent_pid_at_fork; /* MUTANT: getppid() recheck removed */
#endif

    if (opts->exit_before_ack) {
        _exit(EXIT_INJECTED_CRASH);
    }

    if (opts->skip_ack) {
        /* simulate a hung/uncooperative child: outlive the parent's timeout
         * without ever sending an ACK, then exit cleanly so the test process
         * doesn't leak a runaway sleeper. */
        sleep_ms(2000);
        _exit(0);
    }

    /* STUB：OH security specialization 与 runtime adapter entry 都由测试注入结果。
     * 本 host 模型只验证回执协议会 fail closed；它没有执行真实 setcon/token/sandbox，
     * 也没有进入 AndroidRuntime/ActivityThread，不能作为产品运行证据。 */
    int specialization_result = opts->specialization_result;
    int adapter_entry_result = opts->adapter_entry_result;

    CapabilityAck ack;
    memset(&ack, 0, sizeof(ack));
    ack.epoch = req->epoch;
    ack.fork_pid = getpid();
    memcpy(ack.nonce, req->nonce, SPAWN_NONCE_LEN);
    ack.generation = req->generation;
    ack.specialization_result = specialization_result;
    ack.adapter_entry_result = adapter_entry_result;
    strncpy(ack.adapter_entry, req->adapter_entry, SPAWN_ADAPTER_ENTRY_LEN - 1);

    fork_capability_send_ack(child_fd, &ack);

    _exit(0);
}
