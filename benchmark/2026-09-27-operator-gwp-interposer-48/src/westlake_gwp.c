// westlake_gwp.c — GWP-ASan-lite page-guard malloc interposer (#48)
// Purpose: pin the NON-HOOK mallocng heap corruptor by faulting AT the corrupting write.
// LD_PRELOAD this .so; it interposes the libc malloc family (malloc/free/calloc/realloc/
// posix_memalign/memalign/aligned_alloc/malloc_usable_size). In OH musl, LD_PRELOAD of libc
// symbols is GLOBALLY effective (unlike bytehook/shadowhook-exported symbols) — the property the
// hook/sigaction namespace blind spot lacked.
//
// A sampled subset of allocations is served from a dedicated mmap whose page immediately AFTER
// the user bytes is a PROT_NONE guard page, user data RIGHT-ALIGNED against it. An overflow write
// past the end hits the guard -> SIGSEGV AT the writing instruction: crash PC == corruptor (its
// lib+offset resolves from /proc/pid/maps). free() mprotect()s the block PROT_NONE (quarantine)
// so a use-after-free write also faults at the write. Non-sampled allocations pass through to the
// real allocator; live guarded regions are capped and the oldest recycled to bound memory.
//
// Header-minimal (only compiler builtins <stddef.h>/<stdint.h>): all libc/syscall prototypes and
// constants are declared here so it cross-compiles against any OH sysroot (no musl headers needed).
//
// Env:
//   WGWP_SAMPLE=N  guard 1 in N allocations (default 8; 1 guards every alloc — heavy)
//   WGWP_CAP=K     max live guarded regions before recycling oldest (default 4096)
//   WGWP_FRONT=1   also place a guard page BEFORE the block (catch underflow) (default 0)
//   WGWP_MINSZ / WGWP_MAXSZ  only guard sizes in [min,max] (default 1..pagesize)
//   WGWP_LOG=1     one stderr line when armed
#include <stddef.h>
#include <stdint.h>

// ---- self-contained libc / syscall declarations (aarch64 Linux/OH musl ABI) ----
extern void  *mmap(void *, size_t, int, int, int, long);
extern int    munmap(void *, size_t);
extern int    mprotect(void *, size_t, int);
extern void  *dlsym(void *, const char *);
extern char  *getenv(const char *);
extern int    atoi(const char *);
extern long   atol(const char *);
extern long   write(int, const void *, size_t);
extern void  *memset(void *, int, size_t);
extern void  *memcpy(void *, const void *, size_t);

#define PROT_NONE   0
#define PROT_READ   1
#define PROT_WRITE  2
#define MAP_PRIVATE 0x02
#define MAP_ANON    0x20
#define MAP_FAILED  ((void *)-1)
#define RTLD_NEXT   ((void *)-1)
#define PAGE        ((size_t)4096)   // OH DAYU boards: 4 KiB pages (confirmed from board maps)

static void *(*real_malloc)(size_t);
static void  (*real_free)(void *);
static void *(*real_calloc)(size_t, size_t);
static void *(*real_realloc)(void *, size_t);
static int   (*real_posix_memalign)(void **, size_t, size_t);
static size_t (*real_usable)(void *);

static int g_sample = 8, g_front = 0, g_log = 0, g_ready = 0;
static size_t g_cap = 4096, g_minsz = 1, g_maxsz = 4096;

// ---- tiny atomic spinlock (avoids pthread.h / any libc struct) ----
static volatile int g_spin = 0;
static void LOCK(void)   { while (__atomic_exchange_n(&g_spin, 1, __ATOMIC_ACQUIRE)) { } }
static void UNLOCK(void) { __atomic_store_n(&g_spin, 0, __ATOMIC_RELEASE); }

// ---- bootstrap allocator (dlsym() may allocate before real_* resolve) ----
static char g_boot[1 << 20];
static size_t g_boot_off = 0;
static int in_boot(void *p) { return (char *)p >= g_boot && (char *)p < g_boot + sizeof(g_boot); }
static void *boot_alloc(size_t n) {
    size_t a = (n + 15) & ~(size_t)15;
    if (g_boot_off + a > sizeof(g_boot)) return NULL;
    void *p = g_boot + g_boot_off; g_boot_off += a; return p;
}

typedef struct { void *map; size_t maplen; void *user; size_t usize; int quarantined; } region_t;
static region_t *g_regs = NULL;
static size_t g_head = 0, g_live = 0;
static unsigned long g_counter = 0;
static volatile int g_reentry = 0;

static void resolve_real(void) {
    real_malloc  = (void *(*)(size_t))dlsym(RTLD_NEXT, "malloc");
    real_free    = (void  (*)(void *))dlsym(RTLD_NEXT, "free");
    real_calloc  = (void *(*)(size_t, size_t))dlsym(RTLD_NEXT, "calloc");
    real_realloc = (void *(*)(void *, size_t))dlsym(RTLD_NEXT, "realloc");
    real_posix_memalign = (int (*)(void **, size_t, size_t))dlsym(RTLD_NEXT, "posix_memalign");
    real_usable  = (size_t (*)(void *))dlsym(RTLD_NEXT, "malloc_usable_size");
}

__attribute__((constructor(101)))
static void gwp_init(void) {
    char *e;
    if ((e = getenv("WGWP_SAMPLE"))) { int v = atoi(e); if (v >= 1) g_sample = v; }
    if ((e = getenv("WGWP_CAP")))    { long v = atol(e); if (v >= 16) g_cap = (size_t)v; }
    if ((e = getenv("WGWP_FRONT")))  g_front = atoi(e) ? 1 : 0;
    if ((e = getenv("WGWP_LOG")))    g_log = atoi(e) ? 1 : 0;
    if ((e = getenv("WGWP_MINSZ")))  g_minsz = (size_t)atol(e);
    if ((e = getenv("WGWP_MAXSZ")))  { g_maxsz = (size_t)atol(e); }
    if (g_maxsz > PAGE) g_maxsz = PAGE;
    resolve_real();
    size_t rlen = ((g_cap * sizeof(region_t)) + PAGE - 1) & ~(PAGE - 1);
    void *r = mmap(NULL, rlen, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    if (r != MAP_FAILED) { g_regs = (region_t *)r; g_ready = 1; }
    if (g_log) { const char m[] = "[WGWP] armed\n"; (void)write(2, m, sizeof(m) - 1); }
}

static void *guarded_alloc(size_t n, size_t align) {
    size_t datapages = (n + PAGE - 1) / PAGE; if (datapages == 0) datapages = 1;
    size_t maplen = (datapages + 1 + (g_front ? 1u : 0u)) * PAGE;
    char *base = (char *)mmap(NULL, maplen, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    if (base == MAP_FAILED) return NULL;
    char *data_start = base + (g_front ? PAGE : 0);
    char *guard = data_start + datapages * PAGE;
    if (mprotect(guard, PAGE, PROT_NONE) != 0) { munmap(base, maplen); return NULL; }
    if (g_front) mprotect(base, PAGE, PROT_NONE);
    char *user = guard - n;                                   // right-align against trailing guard
    if (align > 16) user = (char *)((uintptr_t)user & ~(align - 1));
    LOCK();
    if (g_live >= g_cap) { region_t *o = &g_regs[g_head]; if (o->map) { munmap(o->map, o->maplen); o->map = NULL; g_live--; } }
    region_t *s = &g_regs[g_head];
    s->map = base; s->maplen = maplen; s->user = user; s->usize = n; s->quarantined = 0;
    g_head = (g_head + 1) % g_cap; g_live++;
    UNLOCK();
    return user;
}

static region_t *find_region(void *p) {
    if (!g_ready) return NULL;
    uintptr_t up = (uintptr_t)p;
    for (size_t i = 0; i < g_cap; i++) {
        region_t *r = &g_regs[i];
        if (!r->map) continue;
        if (r->user == p) return r;
        if (up >= (uintptr_t)r->user && up < (uintptr_t)r->user + r->usize) return r;
    }
    return NULL;
}

static int should_guard(size_t n) {
    if (!g_ready || !real_malloc || g_reentry) return 0;
    if (n < g_minsz || n > g_maxsz) return 0;
    unsigned long c = __atomic_add_fetch(&g_counter, 1, __ATOMIC_RELAXED);
    return (c % (unsigned long)g_sample) == 0;
}

void *malloc(size_t n) {
    if (!real_malloc) { resolve_real(); if (!real_malloc) return boot_alloc(n); }
    if (should_guard(n)) { g_reentry = 1; void *p = guarded_alloc(n, 16); g_reentry = 0; if (p) return p; }
    return real_malloc(n);
}

void *calloc(size_t nm, size_t sz) {
    if (!real_calloc) { resolve_real(); if (!real_calloc) { size_t t = nm * sz; void *p = boot_alloc(t); if (p) memset(p, 0, t); return p; } }
    size_t total = nm * sz;
    if (sz && total / sz != nm) return NULL;
    if (should_guard(total)) { g_reentry = 1; void *p = guarded_alloc(total, 16); g_reentry = 0; if (p) return p; } // mmap is zero-filled
    return real_calloc(nm, sz);
}

void free(void *p) {
    if (!p) return;
    if (in_boot(p)) return;
    region_t *r = find_region(p);
    if (r) {
        LOCK();
        if (!r->quarantined) {
            char *guard = (char *)r->map + (g_front ? PAGE : 0);
            size_t datalen = r->maplen - PAGE - (g_front ? PAGE : 0);
            mprotect(guard, datalen, PROT_NONE);              // UAF write now faults at the write
            r->quarantined = 1;
        }
        UNLOCK();
        return;
    }
    if (real_free) real_free(p);
}

void *realloc(void *p, size_t n) {
    if (!real_realloc) resolve_real();
    region_t *r = p ? find_region(p) : NULL;
    if (r) { void *np = malloc(n); if (np) memcpy(np, p, r->usize < n ? r->usize : n); free(p); return np; }
    if (p && in_boot(p)) { void *np = malloc(n); if (np) memcpy(np, p, n); return np; }
    if (should_guard(n)) { g_reentry = 1; void *gp = guarded_alloc(n, 16); g_reentry = 0;
        if (gp) { if (p) { memcpy(gp, p, n); if (real_free) real_free(p); } return gp; } }
    return real_realloc ? real_realloc(p, n) : NULL;
}

int posix_memalign(void **out, size_t align, size_t n) {
    if (!real_posix_memalign) resolve_real();
    if (should_guard(n) && align <= PAGE) { g_reentry = 1; void *p = guarded_alloc(n, align); g_reentry = 0;
        if (p && ((uintptr_t)p % align) == 0) { *out = p; return 0; }
        if (p) free(p); }
    return real_posix_memalign ? real_posix_memalign(out, align, n) : 22;
}

void *memalign(size_t align, size_t n) { void *o = NULL; return posix_memalign(&o, align, n) == 0 ? o : NULL; }
void *aligned_alloc(size_t align, size_t n) { return memalign(align, n); }

size_t malloc_usable_size(void *p) {
    region_t *r = p ? find_region(p) : NULL;
    if (r) return r->usize;
    if (!real_usable) real_usable = (size_t (*)(void *))dlsym(RTLD_NEXT, "malloc_usable_size");
    return real_usable ? real_usable(p) : 0;
}
