#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif

#include "westlake_musl_signal_backend.h"

#include <pthread.h>
#include <signal.h>
#include <string.h>

/*
 * OpenHarmony's public signal entry points participate in its built-in
 * sigchain.  Translate the compact Android mask into a native musl mask before
 * calling them; calling the kernel directly would bypass ART/faultloggerd
 * chaining even though it avoids the layout overflow.
 */
_Static_assert(sizeof(sigset_t) >= sizeof(uint64_t),
               "OpenHarmony sigset_t cannot hold the kernel signal set");
_Static_assert(sizeof(((struct sigaction *)0)->sa_handler) == sizeof(uintptr_t),
               "unexpected OpenHarmony signal-handler pointer size");
_Static_assert(sizeof(((struct sigaction *)0)->sa_restorer) == sizeof(uintptr_t),
               "unexpected OpenHarmony restorer pointer size");

static void mask_to_musl(sigset_t *output, const uint64_t *input)
{
    memset(output, 0, sizeof(*output));
    if (input) {
        memcpy(output, input, sizeof(*input));
    }
}

static uint64_t mask_from_musl(const sigset_t *input)
{
    uint64_t output = 0;
    memcpy(&output, input, sizeof(output));
    return output;
}

int westlake_musl_sigaction_bridge(int sig,
                                   const struct westlake_signal_action *act,
                                   struct westlake_signal_action *oldact)
{
    struct sigaction native_act;
    struct sigaction native_oldact;
    struct sigaction *native_act_ptr = NULL;
    struct sigaction *native_oldact_ptr = oldact ? &native_oldact : NULL;

    if (act) {
        memset(&native_act, 0, sizeof(native_act));
        memcpy(&native_act.sa_handler, &act->handler,
               sizeof(native_act.sa_handler));
        mask_to_musl(&native_act.sa_mask, &act->mask);
        native_act.sa_flags = (int)act->flags;
        memcpy(&native_act.sa_restorer, &act->restorer,
               sizeof(native_act.sa_restorer));
        native_act_ptr = &native_act;
    }

    int result = sigaction(sig, native_act_ptr, native_oldact_ptr);
    if (result == 0 && oldact) {
        memset(oldact, 0, sizeof(*oldact));
        memcpy(&oldact->handler, &native_oldact.sa_handler,
               sizeof(native_oldact.sa_handler));
        oldact->mask = mask_from_musl(&native_oldact.sa_mask);
        oldact->flags = (unsigned long)(unsigned int)native_oldact.sa_flags;
        memcpy(&oldact->restorer, &native_oldact.sa_restorer,
               sizeof(native_oldact.sa_restorer));
    }
    return result;
}

int westlake_musl_sigprocmask_bridge(int how, const uint64_t *set,
                                     uint64_t *oldset)
{
    sigset_t native_set;
    sigset_t native_oldset;
    sigset_t *native_set_ptr = NULL;
    sigset_t *native_oldset_ptr = oldset ? &native_oldset : NULL;

    if (set) {
        mask_to_musl(&native_set, set);
        native_set_ptr = &native_set;
    }
    int result = sigprocmask(how, native_set_ptr, native_oldset_ptr);
    if (result == 0 && oldset) {
        *oldset = mask_from_musl(&native_oldset);
    }
    return result;
}

int westlake_musl_pthread_sigmask_bridge(int how, const uint64_t *set,
                                         uint64_t *oldset)
{
    sigset_t native_set;
    sigset_t native_oldset;
    sigset_t *native_set_ptr = NULL;
    sigset_t *native_oldset_ptr = oldset ? &native_oldset : NULL;

    if (set) {
        mask_to_musl(&native_set, set);
        native_set_ptr = &native_set;
    }
    int result = pthread_sigmask(how, native_set_ptr, native_oldset_ptr);
    if (result == 0 && oldset) {
        *oldset = mask_from_musl(&native_oldset);
    }
    return result;
}

int westlake_musl_sigsuspend_bridge(const uint64_t *set)
{
    sigset_t native_set;
    mask_to_musl(&native_set, set);
    return sigsuspend(&native_set);
}

int westlake_musl_sigaltstack_bridge(
    const struct westlake_signal_stack *stack,
    struct westlake_signal_stack *oldstack)
{
    stack_t native_stack;
    stack_t native_oldstack;
    stack_t *native_stack_ptr = NULL;
    stack_t *native_oldstack_ptr = oldstack ? &native_oldstack : NULL;

    if (stack) {
        native_stack.ss_sp = (void *)stack->sp;
        native_stack.ss_flags = stack->flags;
        native_stack.ss_size = stack->size;
        native_stack_ptr = &native_stack;
    }
    int result = sigaltstack(native_stack_ptr, native_oldstack_ptr);
    if (result == 0 && oldstack) {
        oldstack->sp = (uintptr_t)native_oldstack.ss_sp;
        oldstack->flags = native_oldstack.ss_flags;
        oldstack->size = native_oldstack.ss_size;
    }
    return result;
}
