// bionic_tls_abi.h
// ============================================================================
// GENERAL bionic -> musl thread-ABI translation rule: establish the bionic TLS
// ABI on every thread that runs bionic code.
// ============================================================================
//
// This is APPLICATION-INDEPENDENT. It is NOT a Unity-specific patch.
//
// WHY
// ---
// bionic code compiled with -fstack-protector (i.e. essentially ALL bionic .so,
// including libunity/libil2cpp but equally any other bionic binary) reads its
// stack-protector canary DIRECTLY from the bionic TLS block via the thread
// pointer:  __builtin_thread_pointer()[TLS_SLOT_STACK_GUARD].
// On aarch64 the bionic TLS layout puts TLS_SLOT_STACK_GUARD at slot index 5,
// i.e. tpidr_el0 + 0x28 (8-byte slots). Function prologues load that word and
// epilogues re-load and compare it; a mismatch calls __stack_chk_fail -> abort.
//
// musl does NOT use a per-thread TLS canary. musl reads a single PROCESS-GLOBAL
// object `__stack_chk_guard`. Its `pthread` struct (which tpidr_el0 points at on
// an OH/musl thread) has NO stable stack-guard at +0x28. So when bionic code
// runs on a musl-created thread, the value it reads at tpidr_el0+0x28 is whatever
// musl happens to keep there -- it is not preserved across the guarded function's
// body, so entry-vs-exit MISMATCHES -> __stack_chk_fail -> silent abort.
//
// Empirically (histogram of tpidr_el0-relative accesses in a bionic libunity.so):
//   slot 5  (0x28, TLS_SLOT_STACK_GUARD) : 2105 reads   <-- dominant, the hot one
//   slot 0  (0x00, TLS_SLOT_SELF)        :    7 reads
//   slot 1/2 (thread self/id)            :  few reads
//   (all other slots: single-digit noise)
// So the stack-guard slot is the one bionic code touches at scale and the one
// that drives the abort. TLS_SLOT_SELF/THREAD_ID are read a handful of times but
// on musl tpidr_el0 already points at a self-consistent thread block, so those
// low-slot reads observe musl's own self/tid and do not fault.
//
// THE RULE
// --------
// On EVERY thread that will run bionic code, seed the bionic TLS stack-guard slot
// with a stable, process-wide guard value BEFORE any bionic guarded function runs:
//     ((uintptr_t*)__builtin_thread_pointer())[5] = g_guard;
// Use the SAME g_guard the shim installs into musl's global __stack_chk_guard, so
// TLS-slot readers (bionic) and global readers (musl) agree.
//
// WHERE this is applied (the two thread-entry points a bionic binary can reach):
//   1. the main/engine thread  -> android_reset_stack_guards() (misc_compat.cpp)
//   2. every pthread_create'd thread -> the pthread_create trampoline
//      (unity_pthread_box.c), which seeds the slot on the NEW thread before
//      calling the real start_routine.
//
// This makes the fix a reusable bionic->musl translation-layer primitive: any
// bionic binary boxed onto OH/musl through this shim gets a correct bionic TLS
// ABI on all its threads.

#ifndef BIONIC_TLS_ABI_H
#define BIONIC_TLS_ABI_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// aarch64 bionic TLS slot indices (8-byte slots off the thread pointer).
// Only STACK_GUARD is seeded at scale; the others are named for documentation.
#define BIONIC_TLS_SLOT_SELF        0   // 0x00
#define BIONIC_TLS_SLOT_THREAD_ID   1   // 0x08
#define BIONIC_TLS_SLOT_APP         2   // 0x10 (bionic app-specific / errno-ish)
#define BIONIC_TLS_SLOT_STACK_GUARD 5   // 0x28  <-- the hot one (2105 reads)

// The single process-wide guard value. Set once, first-writer-wins, and mirrored
// into both musl's global __stack_chk_guard and every thread's bionic TLS slot 5.
extern uintptr_t g_bionic_tls_guard;

// Compute/return the process-wide guard (lazy, thread-safe, first-writer-wins).
uintptr_t bionic_tls_get_guard(void);

// Establish the bionic TLS ABI on the CALLING thread: write g_bionic_tls_guard
// into bionic TLS slot 5 (tpidr_el0 + 0x28). Idempotent; call on every thread
// that will run bionic code, before it runs any guarded bionic function.
static inline void bionic_tls_establish_current_thread(void) {
    uintptr_t g = bionic_tls_get_guard();
    uintptr_t *tp = (uintptr_t *)__builtin_thread_pointer();
    tp[BIONIC_TLS_SLOT_STACK_GUARD] = g;
}

#ifdef __cplusplus
}
#endif

#endif // BIONIC_TLS_ABI_H
