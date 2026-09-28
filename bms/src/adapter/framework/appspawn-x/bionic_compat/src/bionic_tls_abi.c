// bionic_tls_abi.c
// ============================================================================
// GENERAL bionic -> musl thread-ABI translation rule (definition unit).
// See bionic_tls_abi.h for the full rationale. This is application-independent:
// it establishes the bionic TLS stack-guard ABI on threads running bionic code.
// ============================================================================

#include "bionic_tls_abi.h"

#include <unistd.h>
#include <fcntl.h>
#include <stdint.h>

// musl's process-global stack guard. bionic guarded code reads TLS slot 5, but
// we keep BOTH in sync (slot 5 == this global) so global-guard readers (musl
// libc, and any global-model bionic build) and TLS-slot readers agree.
extern uintptr_t __stack_chk_guard;

// The single process-wide guard value.
uintptr_t g_bionic_tls_guard = 0;

// 0 = unset, 1 = initialized. First-writer-wins under an atomic guard.
static int g_guard_ready = 0;

uintptr_t bionic_tls_get_guard(void) {
    // fast path
    if (__atomic_load_n(&g_guard_ready, __ATOMIC_ACQUIRE)) {
        return g_bionic_tls_guard;
    }
    // compute a guard candidate
    uintptr_t guard = 0;
    int fd = open("/dev/urandom", O_RDONLY | O_CLOEXEC);
    if (fd >= 0) {
        ssize_t n = read(fd, &guard, sizeof(guard));
        close(fd);
        if (n != (ssize_t)sizeof(guard) || guard == 0) {
            guard = 0;
        }
    }
    if (guard == 0) {
        // Fallback constant (matches the historical misc_compat fallback), with
        // the low byte zeroed as bionic does so string ops can't leak/scan it.
        guard = 0x00000aff0a0d0000UL;
    }
    // first-writer-wins: publish exactly one value process-wide.
    int expected = 0;
    if (__atomic_compare_exchange_n(&g_guard_ready, &expected, 1,
                                    0, __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        g_bionic_tls_guard = guard;
        __stack_chk_guard   = guard;   // keep musl global in sync
        __atomic_thread_fence(__ATOMIC_RELEASE);
    }
    return g_bionic_tls_guard;
}

// Seed the main/engine thread's bionic TLS slot 5 as early as possible, before
// libunity (or any bionic .so) runs a guarded function on this thread. A shared-
// object constructor runs at dlopen time of this shim, which is loaded before the
// bionic engine libs it services.
__attribute__((constructor))
static void bionic_tls_abi_init_main_thread(void) {
    bionic_tls_establish_current_thread();
}
