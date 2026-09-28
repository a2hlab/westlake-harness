#ifndef CHILD_ENTRY_H
#define CHILD_ENTRY_H

#include "spawn_oracle.h"

/* Test-injection knobs for the child branch. Production behavior is the
 * all-false/zero default; tests flip these to exercise edge cases without
 * duplicating the whole child flow per test. */
typedef struct ChildEntryOptions {
    int  specialization_result;      /* STUB: OH security specialization result; 0 = success */
    int  adapter_entry_result;       /* STUB: runtime adapter entry result; 0 = observed */
    bool inject_delay_after_pdeathsig; /* race-window hook for Edge Case: PDEATHSIG race */
    int  delay_after_pdeathsig_ms;
    bool skip_ack;                   /* simulate a child that never ACKs (timeout test) */
    bool exit_before_ack;            /* simulate a child crashing before ACK (child-error test) */
} ChildEntryOptions;

/* Runs entirely in the child branch after fork(). Never returns — always
 * terminates the child process via _exit(). `parent_pid_at_fork` is the PID
 * the child recorded for its parent at the moment of fork(), used for the
 * FR-004 getppid() recheck. */
void child_entry_run(int child_fd, pid_t parent_pid_at_fork, const SpawnRequest *req,
                      const ChildEntryOptions *opts) __attribute__((noreturn));

#endif /* CHILD_ENTRY_H */
