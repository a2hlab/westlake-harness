// bionic_compat/src/unity_signal_box.c
// [UNITY-SIGNAL-BOX] Wall-3 Route-A — bionic->kernel sigaction/sigset ABI box
// for the self-contained Android Unity .so on OHOS/musl.
//
// WHY THIS FILE EXISTS  (the +0x5633fc nativeResume __stack_chk_fail crash)
// ------------------------------------------------------------------------
// Unity's crash/signal-handler installer (libunity.so in split-Unity packages,
// or libtuanjie.so in Tuanjie/Unity-integrated packages) does:
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
// THE FIX: export STRONG GLOBAL bionic-ABI `sigaction` + sigset helpers here. They
// bind to libunity's undefs via the SAME proven mechanism the pthread box uses
// (libbionic_compat is libmain.so's FIRST DT_NEEDED -> loaded before libc.so ->
// precedes libc in the OHOS-musl reloc search list). The interposer talks to the
// kernel DIRECTLY via rt_sigaction with sigsetsize=8, so the oldact write is
// always the bionic-sized 8-byte sa_mask and NEVER musl's 128-byte blob.
//
// SAFETY (why a global bionic-ABI sigaction is OK in this tree): audited every
// .so in the Unity dlopen tree (libunity/libmain/liboh_android_runtime/
// liboh_unity_bridge/libohub_env). ONLY libunity imports sigaction/sigemptyset,
// and it is bionic-ABI. No musl-ABI lib imports them, so this interposer captures
// exactly the intended caller and corrupts no musl-ABI sigaction call.
//
// Compiled as C ($CF: clang -std=c11, musl headers). We deliberately DO NOT pull
// in musl's <signal.h> struct sigaction / sigset_t (128B) — all layouts here are
// the BIONIC/kernel ABI, defined raw.

#include <stdint.h>
#include <stddef.h>
#include <dlfcn.h>
#include <errno.h>
#include <string.h>      /* strcmp, strrchr, memset */
#include <sys/syscall.h>
#include <unistd.h>

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
    void             *handler;      // offset 8  (union sa_handler/sa_sigaction)
    bionic_sigset_t   sa_mask;      // offset 16 (8 bytes — the slot musl overran)
    void             *sa_restorer;  // offset 24
};                                  // sizeof == 32

_Static_assert(sizeof(bionic_sigset_t) == 8,
               "bionic LP64 sigset_t must remain 8 bytes");
_Static_assert(offsetof(struct bionic_sigaction, sa_flags) == 0,
               "bionic sigaction flags offset drift");
_Static_assert(offsetof(struct bionic_sigaction, handler) == 8,
               "bionic sigaction handler offset drift");
_Static_assert(offsetof(struct bionic_sigaction, sa_mask) == 16,
               "bionic sigaction mask offset drift");
_Static_assert(offsetof(struct bionic_sigaction, sa_restorer) == 24,
               "bionic sigaction restorer offset drift");
_Static_assert(sizeof(struct bionic_sigaction) == 32,
               "bionic sigaction size drift");

// ---- kernel struct sigaction (aarch64 asm-generic). sa_handler FIRST ----
struct kernel_sigaction {
    void             *k_handler;
    unsigned long     k_flags;
    void             *k_restorer;
    uint64_t          k_mask;       // 8-byte kernel sigset
};

_Static_assert(sizeof(struct kernel_sigaction) == 32,
               "aarch64 kernel sigaction size drift");

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
// GATE: inspect the handler that currently owns the kernel signal.  Refuse the
//   guest install only when that handler really belongs to the active ART signal
//   chain (libart.so or libsigchain.so).  Other owners and default/ignored
//   dispositions keep classic pass-through behavior.  This makes the rule about
//   runtime ownership rather than a hard-coded application title.
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

static int faultguard_owner_path_allowed(const char *path) {
    const char *base;
    if (!path) return 0;
    base = strrchr(path, '/');
    base = base ? base + 1 : path;
    return strcmp(base, "libart.so") == 0 ||
           strcmp(base, "libsigchain.so") == 0;
}

static int current_handler_is_art_owned(const struct kernel_sigaction *current) {
    Dl_info owner;
    if (!current || current->k_handler == BSIG_DFL_PTR ||
        current->k_handler == BSIG_IGN_PTR) {
        return 0;
    }
    memset(&owner, 0, sizeof(owner));
    return dladdr(current->k_handler, &owner) != 0 &&
           faultguard_owner_path_allowed(owner.dli_fname);
}

// True only when `act` would INSTALL a real handler (not SIG_DFL / SIG_IGN) for
// a signal ART uses for implicit checks. A reset to default/ignore is allowed
// through (ART tears its own handler down via SIG_DFL on shutdown).
static int is_art_owned_install(int sig, const struct bionic_sigaction *act) {
    if (!act) return 0;                       // pure query — never blocked
    if (sig != BSIG_SEGV && sig != BSIG_BUS) return 0;
    void *h = act->handler;
    if (h == BSIG_DFL_PTR || h == BSIG_IGN_PTR) return 0;  // reset/ignore — allow
    return 1;                                 // installing a custom handler — block
}

// ===========================================================================
// sigaction — bionic ABI in, kernel rt_sigaction (sigsetsize=8) under the hood.
// Writes oldact back with a bionic 8-byte sa_mask; never musl's 128-byte blob.
// ===========================================================================
BIO_EXPORT int sigaction(int sig, const struct bionic_sigaction *act,
                         struct bionic_sigaction *oldact)
{
    struct kernel_sigaction kact, koldact;
    struct kernel_sigaction *kap = 0, *kop = 0;

    // [FAULT-GUARD] Refuse to overwrite ART's SIGSEGV/SIGBUS FaultManager
    // handler only after proving the current kernel owner is ART's signal chain.
    // Report the current handler in oldact and pretend the guest install
    // succeeded, preserving ART implicit-null-check and suspend-check handling.
    if (is_art_owned_install(sig, act)) {
        struct kernel_sigaction cur;
        long q = syscall(SYS_rt_sigaction, sig, (void *)0, &cur, KSIGSETSIZE);
        if (q == 0 && current_handler_is_art_owned(&cur)) {
            if (oldact) {
                oldact->sa_flags    = (int)cur.k_flags;
                oldact->handler     = cur.k_handler;
                oldact->sa_mask     = (bionic_sigset_t)cur.k_mask;
                oldact->sa_restorer = cur.k_restorer;
            }
            return 0;
        }
    }

    if (act) {
        kact.k_handler  = act->handler;
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
        oldact->handler     = koldact.k_handler;
        oldact->sa_mask     = (bionic_sigset_t)koldact.k_mask;  // EXACTLY 8 bytes
        oldact->sa_restorer = koldact.k_restorer;
    }
    return 0;
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

// Private, same-width spellings used by the guest import-rewrite seam.  OH
// musl's process-global symbol chain places the host sigaction/sigemptyset
// before a runtime-loaded compatibility DSO, so the canonical Android imports
// cannot be safely preempted inside an app namespace.  Keeping aliases at the
// exact implementation address lets a copied guest DSO name only the two
// bionic-layout entry points it needs without interposing on host callers.
BIO_EXPORT int wl_sigact(int sig, const struct bionic_sigaction *act,
                         struct bionic_sigaction *oldact)
    __attribute__((alias("sigaction")));
BIO_EXPORT int wl_sigempty(bionic_sigset_t *set)
    __attribute__((alias("sigemptyset")));

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
// sigprocmask — defensive bionic-ABI box (direct rt_sigprocmask, sigsetsize=8).
// Not imported by libunity in this title, but if il2cpp/other tree libs call it
// with a bionic 8-byte sigset, musl's would over-read/write 128B. Kept bionic-safe.
// NOTE: pthread_sigmask is already defined in unity_pthread_box.c — do NOT redefine.
// ===========================================================================
BIO_EXPORT int sigprocmask(int how, const bionic_sigset_t *set, bionic_sigset_t *oldset) {
    uint64_t kset, koldset;
    uint64_t *ksp = 0, *kop = 0;
    if (set)    { kset = (uint64_t)*set; ksp = &kset; }
    if (oldset) kop = &koldset;
    long r = syscall(SYS_rt_sigprocmask, how, ksp, kop, KSIGSETSIZE);
    if (r != 0) return -1;
    if (oldset) *oldset = (bionic_sigset_t)koldset;
    return 0;
}
