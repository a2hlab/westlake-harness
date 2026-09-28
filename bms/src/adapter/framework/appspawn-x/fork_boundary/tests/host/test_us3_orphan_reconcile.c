/* User Story 3: parent 重启后正确 reconcile 旧 epoch orphan.
 *
 * Three sub-scenarios (tasks.md T015 a/b/c):
 *  (a) child sets PDEATHSIG; when its immediate parent dies before ACK, the child does not
 *      linger as a live orphan.
 *  (b) PDEATHSIG race window: even if signal delivery is delayed, the child's own getppid()
 *      recheck independently catches a dead parent and exits via EXIT_PPID_MISMATCH.
 *  (c) epoch_registry_reconcile() on a real in-flight orphan actually kills+reaps it, and a
 *      late ACK carrying the old epoch is rejected by a freshly created (new epoch) registry.
 *
 * (a)/(b) need a real "parent dies while a real child is alive" scenario without killing the
 * test binary itself, so we use a two-level fork: test process (subreaper) -> fake_parent ->
 * real child. When fake_parent exits, the real child is reparented to the test process (which
 * set PR_SET_CHILD_SUBREAPER), so the test can waitpid() on it directly.
 */
#include "child_entry.h"
#include "epoch_registry.h"
#include "fork_capability.h"
#include "spawn_oracle.h"
#include "test_util.h"

#include <signal.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

enum { EXIT_PPID_MISMATCH_EXPECTED = 111 };

static void sleep_ms(int ms) {
    struct timespec ts = { .tv_sec = ms / 1000, .tv_nsec = (long)(ms % 1000) * 1000000L };
    nanosleep(&ts, NULL);
}

/* Forks a "fake_parent" that itself spawns a real child via spawn_oracle_fork(), reports the
 * real child's pid back over a pipe, then exits after `parent_lifetime_ms`. Returns the real
 * child's pid (already reparented to us as subreaper by the time this returns, once reaped). */
static pid_t spawn_via_fake_parent(const ChildEntryOptions *child_opts, int parent_lifetime_ms) {
    int pipe_fd[2];
    if (pipe(pipe_fd) != 0) {
        return -1;
    }

    pid_t fake_parent = fork();
    if (fake_parent == 0) {
        close(pipe_fd[0]);
        EpochRegistry *reg = epoch_registry_create(1);
        SpawnRequest *req = epoch_registry_new_request(reg, 1, "com.sample.orphan", "entry");
        spawn_oracle_fork(reg, req, child_opts);
        pid_t child_pid = req->expected_fork_pid;
        (void)!write(pipe_fd[1], &child_pid, sizeof(child_pid));
        close(pipe_fd[1]);
        sleep_ms(parent_lifetime_ms);
        _exit(0); /* fake_parent dies here — PDEATHSIG fires in the real child */
    }

    close(pipe_fd[1]);
    pid_t child_pid = -1;
    ssize_t got = read(pipe_fd[0], &child_pid, sizeof(child_pid));
    close(pipe_fd[0]);
    int status;
    waitpid(fake_parent, &status, 0); /* reap fake_parent so the real child fully reparents */
    return (got == (ssize_t)sizeof(child_pid)) ? child_pid : -1;
}

static void scenario_a_child_does_not_linger(void) {
    ChildEntryOptions opts = { .specialization_result = 0 };
    pid_t child_pid = spawn_via_fake_parent(&opts, /*parent_lifetime_ms=*/20);
    CHECK(child_pid > 0, "scenario A: fake_parent must report a real child pid");

    int status = -1;
    pid_t reaped = -1;
    for (int i = 0; i < 100 && reaped <= 0; i++) {
        reaped = waitpid(child_pid, &status, WNOHANG);
        if (reaped == 0) {
            sleep_ms(10);
            reaped = -1;
        }
    }
    CHECK(reaped == child_pid,
          "scenario A: orphaned child must be reaped (exit) shortly after its parent died");
    fprintf(stdout, "[US3-a] orphan pid=%d exited status=0x%x (no lingering orphan)\n",
            (int)child_pid, (unsigned)status);
}

static void scenario_b_pdeathsig_race_window(void) {
    /* delay window (300ms) deliberately longer than fake_parent's lifetime (20ms), so the
     * fake_parent is guaranteed dead before the child reaches its getppid() recheck. */
    ChildEntryOptions opts = {
        .specialization_result = 0,
        .inject_delay_after_pdeathsig = true,
        .delay_after_pdeathsig_ms = 300,
    };
    pid_t child_pid = spawn_via_fake_parent(&opts, /*parent_lifetime_ms=*/20);
    CHECK(child_pid > 0, "scenario B: fake_parent must report a real child pid");

    int status = -1;
    pid_t reaped = -1;
    for (int i = 0; i < 100 && reaped <= 0; i++) {
        reaped = waitpid(child_pid, &status, WNOHANG);
        if (reaped == 0) {
            sleep_ms(10);
            reaped = -1;
        }
    }
    CHECK(reaped == child_pid, "scenario B: child must eventually exit");
    /* Either the getppid() recheck catches it (clean exit 111) or PDEATHSIG's SIGKILL wins
     * the race first — both are acceptable proof the dead parent was detected; what must NOT
     * happen is the child completing normally (exit 0) as if nothing were wrong. */
    bool detected_dead_parent =
        (WIFEXITED(status) && WEXITSTATUS(status) == EXIT_PPID_MISMATCH_EXPECTED) ||
        (WIFSIGNALED(status) && WTERMSIG(status) == SIGKILL);
    CHECK(detected_dead_parent,
          "scenario B: child must exit via getppid-recheck(111) or PDEATHSIG(SIGKILL), got status=0x%x",
          (unsigned)status);
    fprintf(stdout, "[US3-b] orphan pid=%d exited status=0x%x (dead-parent detected)\n",
            (int)child_pid, (unsigned)status);
}

static void scenario_c_reconcile_and_reject_late_ack(void) {
    /* Real orphan, forked directly by the test process (no fake_parent needed here since we
     * want epoch_registry_reconcile() itself — called from THIS process — to kill it). */
    EpochRegistry *old_reg = epoch_registry_create(1);
    SpawnRequest *old_req = epoch_registry_new_request(old_reg, 1, "com.sample.oldepoch", "entry");
    ChildEntryOptions opts = { .specialization_result = 0, .skip_ack = true };
    SpawnOutcome fork_rc = spawn_oracle_fork(old_reg, old_req, &opts);
    CHECK(fork_rc == SPAWN_SUCCESS, "scenario C: fork should not early-reject");
    CHECK(old_req->state == SPAWN_STATE_PENDING_ACK, "scenario C: request must be PENDING_ACK before reconcile");
    pid_t orphan_pid = old_req->expected_fork_pid;

    /* simulate "parent restart": brand-new registry, new epoch, no shared state */
    EpochRegistry *new_reg = epoch_registry_create(2);
    int reconciled = epoch_registry_reconcile(new_reg, old_reg);
    CHECK(reconciled == 1, "scenario C: exactly one orphan should be reconciled, got %d", reconciled);
    CHECK(old_req->state == SPAWN_STATE_RECONCILED, "scenario C: old request must be marked RECONCILED");

    /* confirm the orphan process is actually gone */
    sleep_ms(20);
    CHECK(kill(orphan_pid, 0) != 0, "scenario C: reconciled orphan process must no longer exist");

    /* a "late ACK" using the OLD epoch must be rejected by the NEW registry, even if every
     * other field would otherwise be a legitimate match for some hypothetical request. */
    SpawnRequest *new_req = epoch_registry_new_request(new_reg, 1, "com.sample.newepoch", "entry");
    int parent_fd, child_fd;
    /* build the channel directly (this test targets ACK validation, not process lifecycle) */
    CHECK(fork_capability_channel_create(&parent_fd, &child_fd) == 0, "scenario C: channel create failed");
    CHECK(epoch_registry_try_mark_forked(new_reg, new_req, 999999, parent_fd),
          "scenario C: mark_forked should succeed");

    CapabilityAck late_ack;
    memset(&late_ack, 0, sizeof(late_ack));
    late_ack.epoch = epoch_registry_epoch(old_reg); /* stale epoch, on purpose */
    late_ack.fork_pid = new_req->expected_fork_pid;
    memcpy(late_ack.nonce, new_req->nonce, SPAWN_NONCE_LEN);
    late_ack.generation = new_req->generation;
    late_ack.specialization_result = 0;
    strncpy(late_ack.adapter_entry, new_req->adapter_entry, SPAWN_ADAPTER_ENTRY_LEN - 1);
    CHECK(fork_capability_send_ack(child_fd, &late_ack) == 0, "scenario C: send_ack failed");

    SpawnOutcome outcome = spawn_oracle_wait_ack(new_reg, new_req, 200, NULL);
    CHECK(outcome == REJECT_EPOCH_MISMATCH,
          "scenario C: late ACK carrying old epoch must be REJECT_EPOCH_MISMATCH, got %d", outcome);

    epoch_registry_destroy(old_reg);
    epoch_registry_destroy(new_reg);
}

/* FR-004 isolated: exercises the child's getppid() recheck directly, independent of real
 * PDEATHSIG signal delivery (which would otherwise mask a broken recheck — a mutant that
 * only removes the recheck can still be "saved" by the unmutated PDEATHSIG SIGKILL in
 * scenario B). Passes a deliberately wrong parent_pid_at_fork so the check must fire even
 * though the real parent (this test process) never actually dies. */
static void scenario_d_isolated_ppid_recheck(void) {
    EpochRegistry *reg = epoch_registry_create(1);
    SpawnRequest *req = epoch_registry_new_request(reg, 1, "com.sample.isolated", "entry");

    int parent_fd, child_fd;
    CHECK(fork_capability_channel_create(&parent_fd, &child_fd) == 0, "scenario D: channel create failed");

    pid_t pid = fork();
    if (pid == 0) {
        close(parent_fd);
        ChildEntryOptions opts = { .specialization_result = 0 };
        pid_t bogus_parent_pid = 1; /* deliberately wrong regardless of real getppid() */
        child_entry_run(child_fd, bogus_parent_pid, req, &opts);
        /* unreachable */
    }
    close(child_fd);
    CHECK(epoch_registry_try_mark_forked(reg, req, pid, parent_fd), "scenario D: mark_forked failed");

    SpawnOutcome outcome = spawn_oracle_wait_ack(reg, req, 300, NULL);
    CHECK(outcome == REJECT_CHILD_ERROR,
          "scenario D: child must self-detect the ppid mismatch and exit before ACK, got outcome=%d",
          outcome);
    CHECK(WIFEXITED(req->child_wait_status) && WEXITSTATUS(req->child_wait_status) == EXIT_PPID_MISMATCH_EXPECTED,
          "scenario D: child must exit with the ppid-mismatch code, got status=0x%x",
          (unsigned)req->child_wait_status);

    epoch_registry_destroy(reg);
}

int main(void) {
    prctl(PR_SET_CHILD_SUBREAPER, 1); /* so orphaned grandchildren reparent to us, waitable */

    scenario_a_child_does_not_linger();
    scenario_b_pdeathsig_race_window();
    scenario_c_reconcile_and_reject_late_ack();
    scenario_d_isolated_ppid_recheck();

    TEST_MAIN_EXIT();
}
