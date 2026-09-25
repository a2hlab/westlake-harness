#define _GNU_SOURCE
#include "crash_snapshot.h"
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <ucontext.h>
#include <unistd.h>

static int observe, pipe_fd;
static void handler(int sig, siginfo_t *si, void *raw) {
    siginfo_t before_si;
    ucontext_t before_uc;
    memcpy(&before_si, si, sizeof(before_si));
    memcpy(&before_uc, raw, sizeof(before_uc));
    errno = EDOM;
    if (observe) wl_crash_snapshot(sig, si, raw);
    int unchanged = errno == EDOM && !memcmp(&before_si, si, sizeof(*si)) &&
                    !memcmp(&before_uc, raw, sizeof(before_uc));
    int result[4] = {sig, si->si_code, unchanged, si->si_addr == NULL};
    ssize_t n = write(pipe_fd, result, sizeof(result));
    if (n != sizeof(result)) _exit(98);
    /* Test fixture termination, NOT recorder code: refault original instruction. */
    struct sigaction dfl = {.sa_handler = SIG_DFL};
    sigemptyset(&dfl.sa_mask); sigaction(sig, &dfl, NULL);
}
__attribute__((noinline)) static void crash(void *p) { *(volatile int *)p = 1; }
int main(int argc, char **argv) {
    assert(argc == 2);
    struct rlimit lim = {0, 0}; assert(!setrlimit(RLIMIT_CORE, &lim));
    int expected[4] = {0};
    for (int enabled = 0; enabled < 2; ++enabled) {
        int fds[2]; assert(!pipe(fds));
        pid_t child = fork(); assert(child >= 0);
        if (!child) {
            close(fds[0]); pipe_fd = fds[1]; observe = enabled;
            assert(!wl_crash_snapshot_init(argv[1]));
            struct sigaction sa = {.sa_sigaction = handler, .sa_flags = SA_SIGINFO};
            sigemptyset(&sa.sa_mask); assert(!sigaction(SIGSEGV, &sa, NULL));
            void *p = mmap(NULL, 4096, PROT_NONE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
            assert(p != MAP_FAILED); crash(p); _exit(99);
        }
        close(fds[1]); int got[4], status;
        assert(read(fds[0], got, sizeof(got)) == sizeof(got)); close(fds[0]);
        assert(waitpid(child, &status, 0) == child);
        assert(WIFSIGNALED(status) && WTERMSIG(status) == SIGSEGV);
        fprintf(stderr, "enabled=%d sig=%d code=%d unchanged=%d\n", enabled, got[0], got[1], got[2]);
        assert(got[0] == SIGSEGV && (got[1] == SEGV_ACCERR || got[1] == SEGV_MAPERR) && got[2] == 1);
        if (!enabled) memcpy(expected, got, sizeof(got));
        else assert(!memcmp(expected, got, sizeof(got)));
    }
    puts("PASS: observer preserved errno/siginfo/ucontext, si_code and final SIGSEGV");
}
