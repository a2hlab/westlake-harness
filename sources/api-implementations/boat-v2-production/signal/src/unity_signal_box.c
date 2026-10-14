// bionic_compat/src/unity_signal_box.c
// [UNITY-SIGNAL-BOX] Wall-3 Route-A — bionic->kernel sigaction/sigset ABI box
// for the self-contained Android Unity .so on OHOS/musl.
//
// WHY THIS FILE EXISTS  (the +0x5633fc nativeResume __stack_chk_fail crash)
// ------------------------------------------------------------------------
// libunity's crash/signal-handler installer (reached from UnityPlayer.nativeResume,
// cardwords 2022.3.62f2 libunity.so +0x563390) does:
//     sigemptyset(&act.sa_mask);            // libunity +0x563364  sigemptyset@plt
//     sigaction(sig, &act, &oldact);        // libunity +0x5633xx  sigaction@plt
// where `act`/`oldact` are BIONIC struct sigaction objects on libunity's stack:
//     struct sigaction { int sa_flags; <pad4>; void* sa_handler;     // off 0/8
//                        sigset_t sa_mask; void* sa_restorer; };      // off 16/24
// On LP64 bionic, sigset_t is 8 BYTES (one unsigned long). The whole struct is 32B.
//
// THE BUG: libunity imports `sigaction` and `sigemptyset` as plain bionic @LIBC
// undefs. Until now libbionic_compat.so exported NEITHER (verified: nm -D shows
// zero sig* exports), so libunity's undefs fell through the OHOS-musl
// reloc_can_search_dso_list and bound to MUSL libc.so. musl's sigemptyset/
// __libc_sigaction operate on a MUSL sigset_t whose _NSIG/8 == 128 BYTES: they
// memset/memcpy 128 bytes into the 8-byte bionic sa_mask slot -> overflow 112
// bytes past the bionic struct -> clobber the stack canary at sp+104 ->
// __stack_chk_fail -> SIGABRT (uncatchable by Java) at libunity +0x5633fc.
//
// THE FIX: expose a caller-scoped bionic-ABI `sigaction` + sigset codec. The
// production namespaced build translates into OH musl objects and uses musl's
// public signal entry points, preserving its built-in ART/DFX sigchain. Legacy
// fixtures retain the direct-kernel path. Either route writes only the bionic
// 8-byte sa_mask back to the guest, never musl's 128-byte object.
//
// SAFETY: this source must not be added as same-name global exports to the
// appspawn-wide pthread bridge. That experiment polluted host musl callers and
// failed the HelloWorld process-spawn gate. A guest-only producer compiles with
// WESTLAKE_SIGNAL_BOX_NAMESPACE and rewrites only the selected Android caller's
// imports to the namespaced symbols below. Builds without that define retain the
// historical names for isolated fixtures, but are not production-eligible.
//
// Compiled as C ($CF: clang -std=c11, musl headers). We deliberately DO NOT pull
// in musl's <signal.h> struct sigaction / sigset_t (128B) — all layouts here are
// the BIONIC/kernel ABI, defined raw.

#include <stdint.h>
#include <stddef.h>
#include <errno.h>
#include <stdlib.h>      /* getenv */
#include <string.h>      /* strcmp */
#include <sys/syscall.h>
#include <unistd.h>

#include "westlake_musl_signal_backend.h"

#ifdef WESTLAKE_SIGNAL_BOX_NAMESPACE
#define signal westlake_bionic_signal
#define sigaction westlake_bionic_sigaction
#define sigemptyset westlake_bionic_sigemptyset
#define sigfillset westlake_bionic_sigfillset
#define sigaddset westlake_bionic_sigaddset
#define sigdelset westlake_bionic_sigdelset
#define sigismember westlake_bionic_sigismember
#define sigprocmask westlake_bionic_sigprocmask
#define pthread_sigmask westlake_bionic_pthread_sigmask
#define sigsuspend westlake_bionic_sigsuspend
#define sigaltstack westlake_bionic_sigaltstack
#endif

#ifndef SYS_sigaltstack
#define SYS_sigaltstack 132     /* aarch64 __NR_sigaltstack */
#endif
#ifndef SYS_rt_sigsuspend
#define SYS_rt_sigsuspend 133   /* aarch64 __NR_rt_sigsuspend */
#endif
#ifndef SYS_rt_sigaction
#define SYS_rt_sigaction 134   /* aarch64 __NR_rt_sigaction */
#endif
#ifndef SYS_rt_sigprocmask
#define SYS_rt_sigprocmask 135 /* aarch64 __NR_rt_sigprocmask */
#endif

#define BIO_EXPORT __attribute__((visibility("default")))

// Kernel sigset is 8 bytes on aarch64 (_NSIG == 64). This is also EXACTLY the
// bionic LP64 sigset_t size, so the mask copies 1:1 with zero translation.
#define KSIGSETSIZE ((size_t)8)

// ---- bionic LP64 struct sigaction (aarch64). sa_flags FIRST, 8-byte sa_mask ----
typedef uint64_t bionic_sigset_t;   // bionic LP64 sigset_t == unsigned long == 8B
struct bionic_sigaction {
    int               sa_flags;     // offset 0  (+4 pad)
    void             *sa_handler;   // offset 8  (union sa_handler/sa_sigaction)
    bionic_sigset_t   sa_mask;      // offset 16 (8 bytes — the slot musl overran)
    void             *sa_restorer;  // offset 24
};                                  // sizeof == 32

// ---- kernel struct sigaction (aarch64 asm-generic). sa_handler FIRST ----
struct kernel_sigaction {
    void             *k_handler;
    unsigned long     k_flags;
    void             *k_restorer;
    uint64_t          k_mask;       // 8-byte kernel sigset
};

// sigaltstack is kernel-shaped on both Android/Bionic and OH/musl arm64.
struct bionic_sigaltstack {
    void   *ss_sp;
    int     ss_flags;
    size_t  ss_size;
};

#ifdef WESTLAKE_SIGNAL_BOX_NAMESPACE
static void action_to_bridge(const struct bionic_sigaction *input,
                             struct westlake_signal_action *output) {
    output->handler = (uintptr_t)input->sa_handler;
    output->flags = (unsigned long)(unsigned int)input->sa_flags;
    output->restorer = (uintptr_t)input->sa_restorer;
    output->mask = (uint64_t)input->sa_mask;
}

static void action_from_bridge(const struct westlake_signal_action *input,
                               struct bionic_sigaction *output) {
    output->sa_flags = (int)input->flags;
    output->sa_handler = (void *)input->handler;
    output->sa_mask = (bionic_sigset_t)input->mask;
    output->sa_restorer = (void *)input->restorer;
}
#endif

// ===========================================================================
// [FAULT-GUARD] Protect ART's FaultManager SIGSEGV/SIGBUS handler.
// ---------------------------------------------------------------------------
// WHY (RE 2026-07-01, sctrace_v3 primary-signal isolation, variant-3 cardwords):
//   The OH host ART installs a FaultManager SIGSEGV/SIGBUS handler at runtime
//   init to convert IMPLICIT null-checks / suspend-checks in AOT'd Java into
//   java.lang.NullPointerException (and to run the suspend-check trampoline).
//   Later, libunity's crash-handler installer (UnitySwappy_injectTracer /
//   nativeResume path, libunity 0x563340) loops a 7-signal table
//   { SIGILL, SIGABRT, SIGBUS, SIGFPE, SIGSEGV, SIGPIPE, 16 } and, for each,
//   calls sigaction(sig, act, oldact=NULL) at libunity 0x5633bc — i.e. it
//   OVERWRITES ART's handler WITHOUT chaining to the previous disposition.
//   Once ART's SIGSEGV/SIGBUS handler is displaced, the very next implicit
//   null-check in the framework RenderThread (ThreadedRenderer / HardwareRenderer
//   AOT frame boot-framework.oat+0x2fed6e4: `ldr w22,[x0,#56]` -> null, then
//   `ldr x1,[x22,#8]` -> SIGSEGV @0x8) is NOT converted to a Java NPE; it goes
//   to Unity's handler, which secondary-faults building its crash report
//   (introsort at libunity 0x93fc2c) -> process dies. That primary NPE is the
//   real variant-3 wall, MASKED by Unity's handler cascade.
//
// FIX: when the caller tries to INSTALL a handler for a signal ART owns for
//   control-flow (SIGSEGV=11, SIGBUS=7), DO NOT install it — leave ART's
//   already-installed handler in place — but still report the CURRENT (ART)
//   handler back in oldact so the caller's bookkeeping is consistent. All other
//   sigaction behavior (the 8-byte bionic ABI, non-fatal signals, queries with
//   act==NULL, and resets to SIG_DFL/SIG_IGN) is UNCHANGED.
//
// GATE: a WESTLAKE_SIGNAL_BOX_NAMESPACE build is a caller-scoped DSO whose
//   imports are rewritten only for a selected Android guest.  Such a guest is
//   necessarily running on the OH ART host, so the guard is always active.
//   Historical non-namespaced fixtures retain the OHUB_VARIANT allowlist; this
//   keeps the standalone bionic path and unrelated processes unchanged.
// ===========================================================================
#ifndef BSIG_SEGV
#define BSIG_SEGV 11
#endif
#ifndef BSIG_BUS
#define BSIG_BUS  7
#endif
#ifndef BSIG_DFL_PTR
#define BSIG_DFL_PTR ((void *)0)   /* SIG_DFL */
#endif
#ifndef BSIG_IGN_PTR
#define BSIG_IGN_PTR ((void *)1)   /* SIG_IGN */
#endif

#ifndef WESTLAKE_SIGNAL_BOX_NAMESPACE
// Legacy non-namespaced fixture gate. Cached after first query:
// -1 unknown, 0 off, 1 on.
static int g_faultguard = -1;
static int faultguard_variant_allowed(const char *v) {
    return v && (strcmp(v, "cardwords") == 0 || strcmp(v, "game1") == 0);
}
#endif

static int faultguard_on(void) {
#ifdef WESTLAKE_SIGNAL_BOX_NAMESPACE
    // This DSO cannot intercept host callers: only the selected guest has its
    // relocations rewritten to westlake_bionic_sigaction. Preserve ART's
    // control-flow handlers unconditionally in that private domain.
    return 1;
#else
    if (g_faultguard < 0) {
        const char *v = getenv("OHUB_VARIANT");
        // Keep this an explicit title allowlist; never infer eligibility from a path.
        g_faultguard = faultguard_variant_allowed(v) ? 1 : 0;
    }
    return g_faultguard;
#endif
}

// True only when `act` would INSTALL a real handler (not SIG_DFL / SIG_IGN) for
// a signal ART uses for implicit checks. A reset to default/ignore is allowed
// through (ART tears its own handler down via SIG_DFL on shutdown).
static int is_art_owned_install(int sig, const struct bionic_sigaction *act) {
    if (!act) return 0;                       // pure query — never blocked
    if (sig != BSIG_SEGV && sig != BSIG_BUS) return 0;
    void *h = act->sa_handler;
    if (h == BSIG_DFL_PTR || h == BSIG_IGN_PTR) return 0;  // reset/ignore — allow
    return 1;                                 // installing a custom handler — block
}

// ===========================================================================
// sigaction — Bionic ABI at the guest edge. The namespaced production build
// translates through the public OH musl API so its signal-chain owner remains
// intact; the legacy unnamespaced build retains the raw-kernel fallback.
// Writes oldact back with a Bionic 8-byte sa_mask, never musl's 128-byte blob.
// ===========================================================================
BIO_EXPORT int sigaction(int sig, const struct bionic_sigaction *act,
                         struct bionic_sigaction *oldact)
{
#ifdef WESTLAKE_SIGNAL_BOX_NAMESPACE
    struct westlake_signal_action bridge_act;
    struct westlake_signal_action bridge_oldact;

    // Preserve ART's implicit-fault owners. Query through public OH sigaction,
    // not the raw kernel action, so the result describes the user slot behind
    // musl's sigchain front end.
    if (faultguard_on() && is_art_owned_install(sig, act)) {
        if (oldact) {
            int q = westlake_musl_sigaction_bridge(sig, NULL, &bridge_oldact);
            if (q == 0) {
                action_from_bridge(&bridge_oldact, oldact);
            } else {
                oldact->sa_flags = 0;
                oldact->sa_handler = BSIG_DFL_PTR;
                oldact->sa_mask = 0;
                oldact->sa_restorer = NULL;
            }
        }
        return 0;
    }

    const struct westlake_signal_action *bridge_act_ptr = NULL;
    if (act) {
        action_to_bridge(act, &bridge_act);
        bridge_act_ptr = &bridge_act;
    }
    int result = westlake_musl_sigaction_bridge(
        sig, bridge_act_ptr, oldact ? &bridge_oldact : NULL);
    if (result == 0 && oldact) {
        action_from_bridge(&bridge_oldact, oldact);
    }
    return result;
#else
    struct kernel_sigaction kact, koldact;
    struct kernel_sigaction *kap = 0, *kop = 0;

    // [FAULT-GUARD] Refuse to overwrite ART's SIGSEGV/SIGBUS FaultManager handler
    // with a Unity crash handler. Return the CURRENT handler in oldact (act=NULL
    // query) and report success, so libunity believes its install took while
    // ART's implicit-null-check / suspend-check path stays live.
    if (faultguard_on() && is_art_owned_install(sig, act)) {
        if (oldact) {
            struct kernel_sigaction cur;
            long q = syscall(SYS_rt_sigaction, sig, (void *)0, &cur, KSIGSETSIZE);
            if (q == 0) {
                oldact->sa_flags    = (int)cur.k_flags;
                oldact->sa_handler  = cur.k_handler;
                oldact->sa_mask     = (bionic_sigset_t)cur.k_mask;
                oldact->sa_restorer = cur.k_restorer;
            } else {
                oldact->sa_flags    = 0;
                oldact->sa_handler  = BSIG_DFL_PTR;
                oldact->sa_mask     = 0;
                oldact->sa_restorer = 0;
            }
        }
        return 0;   // pretend success; ART's handler is preserved
    }

    if (act) {
        kact.k_handler  = act->sa_handler;
        kact.k_flags    = (unsigned long)(unsigned int)act->sa_flags;
        kact.k_restorer = act->sa_restorer;     // pass bionic's own __restore_rt through
        kact.k_mask     = (uint64_t)act->sa_mask;  // 8B bionic mask == 8B kernel mask
        kap = &kact;
    }
    if (oldact) kop = &koldact;

    long r = syscall(SYS_rt_sigaction, sig, kap, kop, KSIGSETSIZE);
    if (r != 0) {
        // errno already set by musl's syscall() wrapper on -errno.
        return -1;
    }
    if (oldact) {
        oldact->sa_flags    = (int)koldact.k_flags;
        oldact->sa_handler  = koldact.k_handler;
        oldact->sa_mask     = (bionic_sigset_t)koldact.k_mask;  // EXACTLY 8 bytes
        oldact->sa_restorer = koldact.k_restorer;
    }
    return 0;
#endif
}

// Bionic signal(3) is a SA_RESTART sigaction convenience wrapper. Keep its
// handler ABI opaque here; function and data pointers are both one arm64 word.
#define BIONIC_SA_RESTART 0x10000000
#define BSIG_ERR_PTR ((void *)(intptr_t)-1)
BIO_EXPORT void *signal(int sig, void *handler) {
    struct bionic_sigaction act;
    struct bionic_sigaction oldact;
    act.sa_flags = BIONIC_SA_RESTART;
    act.sa_handler = handler;
    act.sa_mask = 0;
    act.sa_restorer = NULL;
    if (sigaction(sig, &act, &oldact) != 0) return BSIG_ERR_PTR;
    return oldact.sa_handler;
}

// ===========================================================================
// sigset_t helpers on the BIONIC 8-byte sigset. libunity calls sigemptyset on a
// bionic sa_mask; musl's would memset 128B and overflow it. These touch 8 bytes.
// Valid for all real signals (1..64) on aarch64 — the only signals that exist.
// ===========================================================================
BIO_EXPORT int sigemptyset(bionic_sigset_t *set) {
    if (!set) { errno = EINVAL; return -1; }
    *set = 0;
    return 0;
}
BIO_EXPORT int sigfillset(bionic_sigset_t *set) {
    if (!set) { errno = EINVAL; return -1; }
    *set = ~(uint64_t)0;
    return 0;
}
BIO_EXPORT int sigaddset(bionic_sigset_t *set, int sig) {
    if (!set || sig < 1 || sig > 64) { errno = EINVAL; return -1; }
    *set |= (uint64_t)1 << (sig - 1);
    return 0;
}
BIO_EXPORT int sigdelset(bionic_sigset_t *set, int sig) {
    if (!set || sig < 1 || sig > 64) { errno = EINVAL; return -1; }
    *set &= ~((uint64_t)1 << (sig - 1));
    return 0;
}
BIO_EXPORT int sigismember(const bionic_sigset_t *set, int sig) {
    if (!set || sig < 1 || sig > 64) { errno = EINVAL; return -1; }
    return (int)((*set >> (sig - 1)) & 1);
}

// ===========================================================================
// sigprocmask — defensive Bionic-ABI box. The namespaced production build
// translates through OH musl; the legacy build uses rt_sigprocmask directly.
// Keeping this and pthread_sigmask in the guest-only signal DSO prevents musl
// from over-reading/writing a Bionic 8-byte sigset.
// ===========================================================================
BIO_EXPORT int sigprocmask(int how, const bionic_sigset_t *set, bionic_sigset_t *oldset) {
#ifdef WESTLAKE_SIGNAL_BOX_NAMESPACE
    return westlake_musl_sigprocmask_bridge(
        how, (const uint64_t *)set, (uint64_t *)oldset);
#else
    uint64_t kset, koldset;
    uint64_t *ksp = 0, *kop = 0;
    if (set)    { kset = (uint64_t)*set; ksp = &kset; }
    if (oldset) kop = &koldset;
    long r = syscall(SYS_rt_sigprocmask, how, ksp, kop, KSIGSETSIZE);
    if (r != 0) return -1;
    if (oldset) *oldset = (bionic_sigset_t)koldset;
    return 0;
#endif
}

// pthread_sigmask differs from sigprocmask only in error convention: POSIX
// returns the error number directly instead of setting errno and returning -1.
BIO_EXPORT int pthread_sigmask(int how, const bionic_sigset_t *set,
                               bionic_sigset_t *oldset) {
#ifdef WESTLAKE_SIGNAL_BOX_NAMESPACE
    return westlake_musl_pthread_sigmask_bridge(
        how, (const uint64_t *)set, (uint64_t *)oldset);
#else
    int saved_errno = errno;
    int result = sigprocmask(how, set, oldset);
    if (result == 0) {
        errno = saved_errno;
        return 0;
    }
    result = errno;
    errno = saved_errno;
    return result;
#endif
}

BIO_EXPORT int sigsuspend(const bionic_sigset_t *set) {
    if (!set) { errno = EINVAL; return -1; }
#ifdef WESTLAKE_SIGNAL_BOX_NAMESPACE
    return westlake_musl_sigsuspend_bridge((const uint64_t *)set);
#else
    return (int)syscall(SYS_rt_sigsuspend, set, KSIGSETSIZE);
#endif
}

BIO_EXPORT int sigaltstack(const struct bionic_sigaltstack *stack,
                           struct bionic_sigaltstack *oldstack) {
#ifdef WESTLAKE_SIGNAL_BOX_NAMESPACE
    struct westlake_signal_stack bridge_stack;
    struct westlake_signal_stack bridge_oldstack;
    const struct westlake_signal_stack *bridge_stack_ptr = NULL;
    if (stack) {
        bridge_stack.sp = (uintptr_t)stack->ss_sp;
        bridge_stack.flags = stack->ss_flags;
        bridge_stack.size = stack->ss_size;
        bridge_stack_ptr = &bridge_stack;
    }
    int result = westlake_musl_sigaltstack_bridge(
        bridge_stack_ptr, oldstack ? &bridge_oldstack : NULL);
    if (result == 0 && oldstack) {
        oldstack->ss_sp = (void *)bridge_oldstack.sp;
        oldstack->ss_flags = bridge_oldstack.flags;
        oldstack->ss_size = bridge_oldstack.size;
    }
    return result;
#else
    return (int)syscall(SYS_sigaltstack, stack, oldstack);
#endif
}
