#ifndef WESTLAKE_MUSL_SIGNAL_BACKEND_H
#define WESTLAKE_MUSL_SIGNAL_BACKEND_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Normalized signal objects shared by the Android-ABI front end and the
 * OpenHarmony-musl back end.  These are private to the guest-only DSO; they are
 * deliberately neither a Bionic struct sigaction nor a musl struct sigaction.
 */
struct westlake_signal_action {
    uintptr_t handler;
    unsigned long flags;
    uintptr_t restorer;
    uint64_t mask;
};

struct westlake_signal_stack {
    uintptr_t sp;
    int flags;
    size_t size;
};

int westlake_musl_sigaction_bridge(int sig,
                                   const struct westlake_signal_action *act,
                                   struct westlake_signal_action *oldact);
int westlake_musl_sigprocmask_bridge(int how, const uint64_t *set,
                                     uint64_t *oldset);
int westlake_musl_pthread_sigmask_bridge(int how, const uint64_t *set,
                                         uint64_t *oldset);
int westlake_musl_sigsuspend_bridge(const uint64_t *set);
int westlake_musl_sigaltstack_bridge(
    const struct westlake_signal_stack *stack,
    struct westlake_signal_stack *oldstack);

#ifdef __cplusplus
}
#endif

#endif
