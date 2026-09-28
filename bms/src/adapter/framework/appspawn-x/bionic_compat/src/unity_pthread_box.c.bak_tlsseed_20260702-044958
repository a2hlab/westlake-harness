// bionic_compat/src/unity_pthread_box.c
// [UNITY-PTHREAD-BOX] Wall-3 Route-A — bionic->musl pthread/sem opaque-struct
// boxing layer for self-contained Android Unity .so on OHOS/musl.
//
// WHY THIS FILE EXISTS
// --------------------
// libbionic_compat.so already closes the entire bionic *libc* gap (see
// unity_libc_stubs.c: __sF/__errno/_ctype_/__system_property_*). The ONE
// remaining bionic ABI piece is the pthread/sem opaque structs: libunity /
// libil2cpp / libc++_shared / libswappywrapper carry pthread_mutex_t /
// pthread_cond_t / pthread_rwlock_t / pthread_once_t / pthread_key_t /
// pthread_attr_t / sem_t *objects* compiled with BIONIC's struct layout. If
// those raw bionic blobs are passed straight into musl's pthread_*() the futex
// words / internal fields differ in MEANING -> latent SIGSEGV / lost wakeups.
//
// THE TECHNIQUE (ported from 16.41-AOSP-ATL/bionic_translation/pthread_wrapper)
// ----------------------------------------------------------------------------
// Each bionic sync object is a union { bionic_blob; musl_obj* ptr }. On first
// use we heap-alloc (mmap) the REAL musl object and stash its pointer in the
// first 8 bytes of the bionic blob. Detect "already boxed" vs
// "statically-initialized (PTHREAD_*_INITIALIZER)" with mincore(): if the first
// 8 bytes name a mapped page, it's our musl pointer; otherwise it's a static
// initializer and we lazily box it. This is the ATL approach verbatim, retargeted
// from glibc to OHOS-musl.
//
// SCOPE NOTE (musl-clean symbols stay direct)
// -------------------------------------------
// We export ONLY the symbols whose bionic ABI requires boxing or arg-shape
// translation. Symbols whose bionic and musl ABI already agree at the call
// boundary (pthread_self/equal/join/detach/exit/key_*/getspecific/setspecific/
// once/kill/sigmask/setname_np/sem_getvalue) are *also* exported here as thin
// pass-throughs ONLY where libunity/il2cpp import them as bionic @LIBC undefs
// that musl would otherwise resolve fine -- but to keep one resolution scope we
// forward them. The 263 truly musl-clean libc symbols are NOT touched; they bind
// straight to musl as before.
//
// Compiled as C ($CF: clang -std=c11, musl headers). The wrapper names are the
// PLAIN bionic symbol names (pthread_mutex_lock, ...) exported GLOBAL/strong so
// the Unity libs' `name@LIBC` undefs bind to THESE instead of to musl's real
// pthread_*. Inside, we call the real musl pthread_* via the __real_ aliases
// obtained with dlsym(RTLD_NEXT) is NOT reliable here (we ARE the global def),
// so we instead reference musl's implementation through the renamed prototypes
// declared with asm() labels where musl exposes them, falling back to the libc
// internal names. See musl_real_* below.

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#include <unistd.h>
#include <assert.h>
#include <errno.h>
#include <time.h>
#include <sched.h>
#include <sys/mman.h>
#include <dlfcn.h>

// ===========================================================================
// Reaching musl's REAL pthread_*/sem_* from inside a wrapper that shadows them
// ===========================================================================
// Our exported wrappers use the canonical names (pthread_mutex_lock, ...). If we
// called pthread_mutex_lock() inside, that would recurse into ourselves. We grab
// the genuine musl implementations once, lazily, via dlsym(RTLD_NEXT, name):
// RTLD_NEXT walks past *this* object to the next def in the resolution scope,
// which is musl libc.so. (musl supports RTLD_NEXT.)
//
// All real-fn pointers are cached in one table, populated on first use under a
// real (musl) once-guard that we obtain the same way.

// We avoid a giant typed table; use a small struct of void* and cast at call.
struct real_tbl {
    void *pthread_mutex_init, *pthread_mutex_destroy, *pthread_mutex_lock,
         *pthread_mutex_trylock, *pthread_mutex_unlock;
    void *pthread_cond_init, *pthread_cond_destroy, *pthread_cond_wait,
         *pthread_cond_timedwait, *pthread_cond_signal, *pthread_cond_broadcast;
    void *pthread_rwlock_init, *pthread_rwlock_destroy, *pthread_rwlock_rdlock,
         *pthread_rwlock_wrlock, *pthread_rwlock_unlock;
    void *pthread_mutexattr_init, *pthread_mutexattr_destroy, *pthread_mutexattr_settype;
    void *pthread_condattr_init, *pthread_condattr_destroy, *pthread_condattr_setclock;
    void *pthread_attr_init, *pthread_attr_destroy, *pthread_attr_setdetachstate,
         *pthread_attr_setstacksize, *pthread_attr_getstack, *pthread_getattr_np;
    void *pthread_create;
    void *sem_init, *sem_destroy, *sem_post, *sem_wait, *sem_trywait,
         *sem_timedwait, *sem_getvalue;
};
static struct real_tbl g_real;

static void *real_ptr(const char *name, void **slot) {
    void *p = __atomic_load_n(slot, __ATOMIC_ACQUIRE);
    if (p) return p;
    p = dlsym(RTLD_NEXT, name);
    // dlsym should always find the musl symbol; if not we cannot proceed.
    assert(p && "bionic_compat: musl pthread symbol not found via RTLD_NEXT");
    __atomic_store_n(slot, p, __ATOMIC_RELEASE);
    return p;
}
// R(field, "name") -> cached real musl fn pointer (void*)
#define R(field, name) real_ptr(name, &g_real.field)

// ===========================================================================
// musl object sizes (OHOS aarch64 LP64) -- from the build sysroot bits/alltypes.h
//   pthread_mutex_t  : int __i[10]  -> 40 B
//   pthread_cond_t   : int __i[12]  -> 48 B
//   pthread_rwlock_t : int __i[14]  -> 56 B
//   pthread_attr_t   : int __i[14]  -> 56 B
//   pthread_mutexattr_t/condattr_t  : unsigned -> 4 B (we alloc 8 for safety)
//   sem_t            : int __val[4] -> 16 B (we alloc 32 for safety/futex align)
// We allocate generously (a full page each via mmap, as ATL does) so layout
// drift between musl revisions cannot under-allocate.
// ===========================================================================

// bionic LP64 opaque-blob unions. First pointer-slot aliases our musl ptr.
typedef union { int32_t blob[10]; void *musl; } bx_mutex_t;   // bionic 40B
typedef union { int32_t blob[12]; void *musl; } bx_cond_t;    // bionic 48B
typedef union { int32_t blob[14]; void *musl; } bx_rwlock_t;  // bionic 56B
typedef union { uint8_t blob[56]; void *musl; } bx_attr_t;    // bionic attr 56B
typedef union { int64_t blob;     void *musl; } bx_lattr_t;   // bionic long-attr 8B (mutexattr/condattr)
typedef union { uint32_t blob[4]; void *musl; } bx_sem_t;     // bionic sem 16B

// ---- static-init detection: is the first 8 bytes a pointer to a mapped page?
static bool is_boxed(const void *obj) {
    void *p;
    memcpy(&p, obj, sizeof p);
    if (!p) return false;                       // NULL => static initializer
    const size_t ps = (size_t)sysconf(_SC_PAGESIZE);
    void *base = (void*)((uintptr_t)p & ~(uintptr_t)(ps - 1));
    unsigned char vec;
    if (mincore(base, 1, &vec) != 0) return false;  // not mapped => not our ptr
    return true;
}

static void *box_alloc(size_t musl_sz) {
    (void)musl_sz;
    // One page, zero-filled (MAP_ANONYMOUS guarantees zero) -- matches ATL.
    void *m = mmap(NULL, (size_t)sysconf(_SC_PAGESIZE), PROT_READ | PROT_WRITE,
                   MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    return (m == MAP_FAILED) ? NULL : m;
}
static void box_free(void *m) {
    if (m && m != MAP_FAILED) munmap(m, (size_t)sysconf(_SC_PAGESIZE));
}

// real-fn call shims (cast the void* to the right signature at the call site)
typedef int (*p1)(void*);
typedef int (*p2)(void*, const void*);
typedef int (*p3)(void*, const void*, const void*);

// ===========================================================================
// MUTEX
// ===========================================================================
// bionic PTHREAD_MUTEX_INITIALIZER == all-zero (normal). recursive/errorcheck
// encode the type in __private[0] as ((type & 3) << 14). musl init is all-zero
// too, but its internal layout differs, so we must box + pthread_mutex_init with
// the right type attr. We lazily box a static initializer here.
#define BIONIC_MUTEX_TYPE_SHIFT 14
#define BIONIC_MUTEX_TYPE_MASK  3
enum { B_MUTEX_NORMAL = 0, B_MUTEX_RECURSIVE = 1, B_MUTEX_ERRORCHECK = 2 };

static void *mutex_box(bx_mutex_t *m) {
    if (is_boxed(m)) return m->musl;
    // static initializer: read bionic type, build musl mutex with that type.
    int btype = (m->blob[0] >> BIONIC_MUTEX_TYPE_SHIFT) & BIONIC_MUTEX_TYPE_MASK;
    void *musl = box_alloc(40);
    assert(musl);
    // translate bionic mutex type -> musl PTHREAD_MUTEX_* (same numeric values:
    // NORMAL=0, RECURSIVE=1, ERRORCHECK=2 in both)
    if (btype != B_MUTEX_NORMAL) {
        // tiny on-stack musl mutexattr
        unsigned attr = 0;                       // musl mutexattr is `unsigned`
        ((int(*)(unsigned*,int))R(pthread_mutexattr_settype,"pthread_mutexattr_settype"))(&attr, btype);
        ((p2)R(pthread_mutex_init,"pthread_mutex_init"))(musl, &attr);
    } else {
        ((p2)R(pthread_mutex_init,"pthread_mutex_init"))(musl, NULL);
    }
    m->musl = musl;
    return musl;
}

int pthread_mutex_init(bx_mutex_t *m, const bx_lattr_t *attr) {
    void *musl = box_alloc(40);
    if (!musl) return ENOMEM;
    const void *mattr = NULL;
    unsigned ma = 0;
    if (attr) {
        // bionic mutexattr is `long`; the type lives in the low bits the same
        // way musl's `unsigned` mutexattr does (settype stored value). If the
        // caller boxed an attr, deref it; else treat the long as the raw attr.
        if (is_boxed(attr)) {
            mattr = ((const bx_lattr_t*)attr)->musl;
        } else {
            ma = (unsigned)(((const bx_lattr_t*)attr)->blob & 0xffffffff);
            mattr = &ma;
        }
    }
    int rc = ((p2)R(pthread_mutex_init,"pthread_mutex_init"))(musl, mattr);
    m->musl = musl;
    return rc;
}
int pthread_mutex_destroy(bx_mutex_t *m) {
    if (!is_boxed(m)) return 0;                  // never used
    int rc = ((p1)R(pthread_mutex_destroy,"pthread_mutex_destroy"))(m->musl);
    box_free(m->musl); m->musl = NULL;
    return rc;
}
int pthread_mutex_lock(bx_mutex_t *m)    { return ((p1)R(pthread_mutex_lock,"pthread_mutex_lock"))(mutex_box(m)); }
int pthread_mutex_trylock(bx_mutex_t *m) { return ((p1)R(pthread_mutex_trylock,"pthread_mutex_trylock"))(mutex_box(m)); }
int pthread_mutex_unlock(bx_mutex_t *m)  { return ((p1)R(pthread_mutex_unlock,"pthread_mutex_unlock"))(mutex_box(m)); }

// ===========================================================================
// COND
// ===========================================================================
static void *cond_box(bx_cond_t *c) {
    if (is_boxed(c)) return c->musl;
    void *musl = box_alloc(48);
    assert(musl);
    ((p2)R(pthread_cond_init,"pthread_cond_init"))(musl, NULL);  // zero init -> default
    c->musl = musl;
    return musl;
}
int pthread_cond_init(bx_cond_t *c, const bx_lattr_t *attr) {
    void *musl = box_alloc(48);
    if (!musl) return ENOMEM;
    const void *cattr = (attr && is_boxed(attr)) ? ((const bx_lattr_t*)attr)->musl : NULL;
    int rc = ((p2)R(pthread_cond_init,"pthread_cond_init"))(musl, cattr);
    c->musl = musl;
    return rc;
}
int pthread_cond_destroy(bx_cond_t *c) {
    if (!is_boxed(c)) return 0;
    int rc = ((p1)R(pthread_cond_destroy,"pthread_cond_destroy"))(c->musl);
    box_free(c->musl); c->musl = NULL;
    return rc;
}
int pthread_cond_signal(bx_cond_t *c)    { return ((p1)R(pthread_cond_signal,"pthread_cond_signal"))(cond_box(c)); }
int pthread_cond_broadcast(bx_cond_t *c) { return ((p1)R(pthread_cond_broadcast,"pthread_cond_broadcast"))(cond_box(c)); }
int pthread_cond_wait(bx_cond_t *c, bx_mutex_t *m) {
    return ((p2)R(pthread_cond_wait,"pthread_cond_wait"))(cond_box(c), mutex_box(m));
}
int pthread_cond_timedwait(bx_cond_t *c, bx_mutex_t *m, const struct timespec *ts) {
    return ((int(*)(void*,void*,const struct timespec*))R(pthread_cond_timedwait,"pthread_cond_timedwait"))
           (cond_box(c), mutex_box(m), ts);
}

// ===========================================================================
// RWLOCK
// ===========================================================================
static void *rwlock_box(bx_rwlock_t *r) {
    if (is_boxed(r)) return r->musl;
    void *musl = box_alloc(56);
    assert(musl);
    ((p2)R(pthread_rwlock_init,"pthread_rwlock_init"))(musl, NULL);
    r->musl = musl;
    return musl;
}
int pthread_rwlock_init(bx_rwlock_t *r, const void *attr) {
    void *musl = box_alloc(56);
    if (!musl) return ENOMEM;
    int rc = ((p2)R(pthread_rwlock_init,"pthread_rwlock_init"))(musl, attr /* rwlockattr ABI matches: unused/NULL in practice */);
    r->musl = musl;
    return rc;
}
int pthread_rwlock_destroy(bx_rwlock_t *r) {
    if (!is_boxed(r)) return 0;
    int rc = ((p1)R(pthread_rwlock_destroy,"pthread_rwlock_destroy"))(r->musl);
    box_free(r->musl); r->musl = NULL;
    return rc;
}
int pthread_rwlock_rdlock(bx_rwlock_t *r) { return ((p1)R(pthread_rwlock_rdlock,"pthread_rwlock_rdlock"))(rwlock_box(r)); }
int pthread_rwlock_wrlock(bx_rwlock_t *r) { return ((p1)R(pthread_rwlock_wrlock,"pthread_rwlock_wrlock"))(rwlock_box(r)); }
int pthread_rwlock_unlock(bx_rwlock_t *r) { return ((p1)R(pthread_rwlock_unlock,"pthread_rwlock_unlock"))(rwlock_box(r)); }

// ===========================================================================
// MUTEXATTR / CONDATTR  (bionic `long` 8B  <-> musl `unsigned` 4B)
// We box: stash a musl attr ptr into the bionic long. settype/setclock forward.
// ===========================================================================
static void *lattr_box(bx_lattr_t *a, bool is_cond) {
    if (is_boxed(a)) return a->musl;
    void *musl = box_alloc(8);
    assert(musl);
    if (is_cond) ((p1)R(pthread_condattr_init,"pthread_condattr_init"))(musl);
    else         ((p1)R(pthread_mutexattr_init,"pthread_mutexattr_init"))(musl);
    a->musl = musl;
    return musl;
}
int pthread_mutexattr_init(bx_lattr_t *a) {
    void *musl = box_alloc(8); if (!musl) return ENOMEM;
    int rc = ((p1)R(pthread_mutexattr_init,"pthread_mutexattr_init"))(musl);
    a->musl = musl; return rc;
}
int pthread_mutexattr_destroy(bx_lattr_t *a) {
    if (!is_boxed(a)) return 0;
    int rc = ((p1)R(pthread_mutexattr_destroy,"pthread_mutexattr_destroy"))(a->musl);
    box_free(a->musl); a->musl = NULL; return rc;
}
int pthread_mutexattr_settype(bx_lattr_t *a, int type) {
    return ((int(*)(void*,int))R(pthread_mutexattr_settype,"pthread_mutexattr_settype"))(lattr_box(a,false), type);
}
int pthread_condattr_init(bx_lattr_t *a) {
    void *musl = box_alloc(8); if (!musl) return ENOMEM;
    int rc = ((p1)R(pthread_condattr_init,"pthread_condattr_init"))(musl);
    a->musl = musl; return rc;
}
int pthread_condattr_destroy(bx_lattr_t *a) {
    if (!is_boxed(a)) return 0;
    int rc = ((p1)R(pthread_condattr_destroy,"pthread_condattr_destroy"))(a->musl);
    box_free(a->musl); a->musl = NULL; return rc;
}
int pthread_condattr_setclock(bx_lattr_t *a, int clk) {
    return ((int(*)(void*,int))R(pthread_condattr_setclock,"pthread_condattr_setclock"))(lattr_box(a,true), clk);
}

// ===========================================================================
// THREAD ATTR (bionic 56B struct <-> musl 56B struct, but DIFFERENT layout)
// box it; create reads the boxed musl attr.
// ===========================================================================
static void *attr_box(bx_attr_t *a) {
    if (is_boxed(a)) return a->musl;
    void *musl = box_alloc(56);
    assert(musl);
    ((p1)R(pthread_attr_init,"pthread_attr_init"))(musl);
    a->musl = musl;
    return musl;
}
int pthread_attr_init(bx_attr_t *a) {
    void *musl = box_alloc(56); if (!musl) return ENOMEM;
    int rc = ((p1)R(pthread_attr_init,"pthread_attr_init"))(musl);
    a->musl = musl; return rc;
}
int pthread_attr_destroy(bx_attr_t *a) {
    if (!is_boxed(a)) return 0;
    int rc = ((p1)R(pthread_attr_destroy,"pthread_attr_destroy"))(a->musl);
    box_free(a->musl); a->musl = NULL; return rc;
}
int pthread_attr_setdetachstate(bx_attr_t *a, int st) {
    return ((int(*)(void*,int))R(pthread_attr_setdetachstate,"pthread_attr_setdetachstate"))(attr_box(a), st);
}
int pthread_attr_setstacksize(bx_attr_t *a, size_t sz) {
    return ((int(*)(void*,size_t))R(pthread_attr_setstacksize,"pthread_attr_setstacksize"))(attr_box(a), sz);
}
int pthread_attr_getstack(const bx_attr_t *a, void **base, size_t *sz) {
    return ((int(*)(const void*,void**,size_t*))R(pthread_attr_getstack,"pthread_attr_getstack"))(attr_box((bx_attr_t*)a), base, sz);
}
int pthread_getattr_np(unsigned long thr, bx_attr_t *a) {
    void *musl = box_alloc(56); if (!musl) return ENOMEM;
    int rc = ((int(*)(unsigned long,void*))R(pthread_getattr_np,"pthread_getattr_np"))(thr, musl);
    a->musl = musl; return rc;
}

// ===========================================================================
// pthread_create  (bionic_attr* -> musl_attr*)
// ===========================================================================
int pthread_create(unsigned long *thr, const bx_attr_t *attr,
                   void *(*start)(void*), void *arg) {
    const void *mattr = NULL;
    if (attr) {
        // attr may be static-zero (rare) or boxed.
        mattr = is_boxed(attr) ? ((const bx_attr_t*)attr)->musl : attr_box((bx_attr_t*)attr);
    }
    return ((int(*)(unsigned long*,const void*,void*(*)(void*),void*))
            R(pthread_create,"pthread_create"))(thr, mattr, start, arg);
}

// ===========================================================================
// SEM  (bionic sem_t 16B  <-> musl sem_t 16B, different internal layout)
// ===========================================================================
static void *sem_box(bx_sem_t *s) {
    if (is_boxed(s)) return s->musl;
    // App used a sem without sem_init (seen in real apps) -> default-init to 0.
    void *musl = box_alloc(16);
    assert(musl);
    ((int(*)(void*,int,unsigned))R(sem_init,"sem_init"))(musl, 0, 0);
    s->musl = musl;
    return musl;
}
int sem_init(bx_sem_t *s, int pshared, unsigned value) {
    void *musl = box_alloc(16); if (!musl) return -1;
    int rc = ((int(*)(void*,int,unsigned))R(sem_init,"sem_init"))(musl, pshared, value);
    s->musl = musl; return rc;
}
int sem_destroy(bx_sem_t *s) {
    if (!is_boxed(s)) return 0;
    int rc = ((p1)R(sem_destroy,"sem_destroy"))(s->musl);
    box_free(s->musl); s->musl = NULL; return rc;
}
int sem_post(bx_sem_t *s)    { return ((p1)R(sem_post,"sem_post"))(sem_box(s)); }
int sem_wait(bx_sem_t *s)    { return ((p1)R(sem_wait,"sem_wait"))(sem_box(s)); }
int sem_trywait(bx_sem_t *s) { return ((p1)R(sem_trywait,"sem_trywait"))(sem_box(s)); }
int sem_timedwait(bx_sem_t *s, const struct timespec *ts) {
    return ((int(*)(void*,const struct timespec*))R(sem_timedwait,"sem_timedwait"))(sem_box(s), ts);
}
int sem_getvalue(bx_sem_t *s, int *val) {
    return ((int(*)(void*,int*))R(sem_getvalue,"sem_getvalue"))(sem_box(s), val);
}

// ===========================================================================
// NON-BOXED forwards: bionic objects here are SCALARS (pthread_t=long,
// pthread_key_t=int, pthread_once_t=int) whose ABI matches musl 1:1, OR take no
// opaque struct. We export them so libunity's @LIBC undefs bind into THIS shim's
// single resolution scope, then forward to musl via RTLD_NEXT. (No layout work.)
// ===========================================================================
unsigned long pthread_self(void) {
    static void *f; if (!f) f = dlsym(RTLD_NEXT,"pthread_self");
    return ((unsigned long(*)(void))f)();
}
int pthread_equal(unsigned long a, unsigned long b) {
    static void *f; if (!f) f = dlsym(RTLD_NEXT,"pthread_equal");
    return ((int(*)(unsigned long,unsigned long))f)(a,b);
}
int pthread_join(unsigned long t, void **ret) {
    static void *f; if (!f) f = dlsym(RTLD_NEXT,"pthread_join");
    return ((int(*)(unsigned long,void**))f)(t,ret);
}
int pthread_detach(unsigned long t) {
    static void *f; if (!f) f = dlsym(RTLD_NEXT,"pthread_detach");
    return ((int(*)(unsigned long))f)(t);
}
_Noreturn void pthread_exit(void *r) {
    static void *f; if (!f) f = dlsym(RTLD_NEXT,"pthread_exit");
    ((void(*)(void*))f)(r);
    __builtin_unreachable();
}
int pthread_once(int *once, void (*init)(void)) {
    // bionic pthread_once_t == int == musl pthread_once_t; pass straight through.
    static void *f; if (!f) f = dlsym(RTLD_NEXT,"pthread_once");
    return ((int(*)(int*,void(*)(void)))f)(once, init);
}
int pthread_key_create(unsigned *key, void (*dtor)(void*)) {
    static void *f; if (!f) f = dlsym(RTLD_NEXT,"pthread_key_create");
    return ((int(*)(unsigned*,void(*)(void*)))f)(key, dtor);
}
int pthread_key_delete(unsigned key) {
    static void *f; if (!f) f = dlsym(RTLD_NEXT,"pthread_key_delete");
    return ((int(*)(unsigned))f)(key);
}
void *pthread_getspecific(unsigned key) {
    static void *f; if (!f) f = dlsym(RTLD_NEXT,"pthread_getspecific");
    return ((void*(*)(unsigned))f)(key);
}
int pthread_setspecific(unsigned key, const void *val) {
    static void *f; if (!f) f = dlsym(RTLD_NEXT,"pthread_setspecific");
    return ((int(*)(unsigned,const void*))f)(key, val);
}
int pthread_kill(unsigned long t, int sig) {
    static void *f; if (!f) f = dlsym(RTLD_NEXT,"pthread_kill");
    return ((int(*)(unsigned long,int))f)(t, sig);
}
int pthread_sigmask(int how, const void *set, void *old) {
    static void *f; if (!f) f = dlsym(RTLD_NEXT,"pthread_sigmask");
    return ((int(*)(int,const void*,void*))f)(how, set, old);
}
int pthread_setname_np(unsigned long t, const char *name) {
    static void *f; if (!f) f = dlsym(RTLD_NEXT,"pthread_setname_np");
    return ((int(*)(unsigned long,const char*))f)(t, name);
}
// pthread_atfork is already provided by unity_libc_stubs.c (__register_atfork)
// and il2cpp imports bare pthread_atfork too -> forward it here.
int pthread_atfork(void (*prep)(void), void (*par)(void), void (*chi)(void)) {
    static void *f; if (!f) f = dlsym(RTLD_NEXT,"pthread_atfork");
    return ((int(*)(void(*)(void),void(*)(void),void(*)(void)))f)(prep, par, chi);
}
