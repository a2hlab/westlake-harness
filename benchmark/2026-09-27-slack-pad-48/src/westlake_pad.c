// westlake_pad.c — global slack-padding malloc interposer (#48 mitigation).
// Statistical verdict (claude-2, 16 rounds): the non-hook mallocng corruption is a WHOLE-HEAP RANDOM
// adjacent-block-header smash — victims span sscronet/ICU/Mali-GPU/hilog/ipc/art, no single culprit
// subsystem, so a targeted fix is impossible and mitigation must be at the ALLOCATOR level. The exact
// writer is un-pinnable (victim side varies; a write-time guard perturbs adjacency). This is the last
// concrete lever: give every allocation SLACK tail bytes so a BOUNDED overflow past the user's n lands
// in that slack instead of smashing the NEXT musl chunk header.
//
// Design (deliberately minimal — pure slack, nothing else):
//   malloc/calloc/realloc/posix_memalign/memalign/aligned_alloc all request (n + SLACK) from the REAL
//   allocator and return the pointer UNCHANGED. The user sees n usable bytes; SLACK extra tail bytes
//   hide behind them. Because we never move/track the pointer (it IS a real allocation), free / realloc
//   / malloc_usable_size work on real pointers with NO bookkeeping. No mprotect, no guard pages, no
//   redzone/canary checks, no eviction, no private pool — functionally transparent (the app just gets a
//   legitimately larger buffer), so the feed-break risk is far lower than the earlier guards
//   (the r1 sscronet-detector guard broke the feed; pure slack does not change behavior).
//
// Header-minimal (self-contained decls) -> compiles against any OH sysroot; -nostdlib, no __thread
// (no __emutls), malloc family GLOBAL DEFAULT. env-free: SLACK hardcoded. Chain-loads the app's
// bionic-compat shim (single-slot WESTLAKE_ANDROID_NATIVE_PRELOAD points at us).
#include <stddef.h>
#include <stdint.h>

extern void *dlsym(void *, const char *);
extern void *dlopen(const char *, int);
extern char *dlerror(void);
extern char *getenv(const char *);
extern long  write(int, const void *, size_t);
extern void *memset(void *, int, size_t);

#define RTLD_NEXT   ((void*)-1)
#define RTLD_NOW    0x2
#define RTLD_GLOBAL 0x100

// Tail slack per allocation. 64 B first (enlarge later if the smash overruns further). env-free.
#define SLACK ((size_t)64)

static void *(*real_malloc)(size_t);
static void  (*real_free)(void *);
static void *(*real_calloc)(size_t, size_t);
static void *(*real_realloc)(void *, size_t);
static int   (*real_posix_memalign)(void **, size_t, size_t);
static void *(*real_memalign)(size_t, size_t);
static void *(*real_aligned_alloc)(size_t, size_t);
static size_t(*real_usable)(void *);

static void puts2(const char*s){ size_t n=0; while(s[n])n++; (void)write(2,s,n); }

// ---- bootstrap allocator: dlsym() may allocate before real_* resolve (reentrancy) ----
static char g_boot[1 << 16];
static size_t g_boot_off = 0;
static int in_boot(void *p){ return (char*)p >= g_boot && (char*)p < g_boot + sizeof(g_boot); }
static void *boot_alloc(size_t n){
    size_t a = (n + 15) & ~(size_t)15;
    if (g_boot_off + a > sizeof(g_boot)) return (void*)0;
    void *p = g_boot + g_boot_off; g_boot_off += a; return p;
}

static volatile int g_resolving = 0;
static void resolve_real(void){
    if (g_resolving) return;               // dlsym may call us reentrantly -> use bootstrap
    g_resolving = 1;
    real_malloc         =(void*(*)(size_t))              dlsym(RTLD_NEXT,"malloc");
    real_free           =(void (*)(void*))               dlsym(RTLD_NEXT,"free");
    real_calloc         =(void*(*)(size_t,size_t))       dlsym(RTLD_NEXT,"calloc");
    real_realloc        =(void*(*)(void*,size_t))        dlsym(RTLD_NEXT,"realloc");
    real_posix_memalign =(int  (*)(void**,size_t,size_t))dlsym(RTLD_NEXT,"posix_memalign");
    real_memalign       =(void*(*)(size_t,size_t))       dlsym(RTLD_NEXT,"memalign");
    real_aligned_alloc  =(void*(*)(size_t,size_t))       dlsym(RTLD_NEXT,"aligned_alloc");
    real_usable         =(size_t(*)(void*))              dlsym(RTLD_NEXT,"malloc_usable_size");
    g_resolving = 0;
}

static size_t addpad(size_t n){ size_t t = n + SLACK; return t < n ? n : t; }   // overflow-safe

// ---- interposed malloc family: request n+SLACK from the real allocator, return the pointer as-is ----
void *malloc(size_t n){
    if (!real_malloc){ resolve_real(); if (!real_malloc) return boot_alloc(n); }
    return real_malloc(addpad(n));
}
void free(void *p){
    if (!p) return;
    if (in_boot(p)) return;                // bootstrap chunk: never handed to real free
    if (!real_free) resolve_real();
    if (real_free) real_free(p);
}
void *calloc(size_t nm, size_t sz){
    size_t total = nm * sz;
    if (sz && total / sz != nm) return (void*)0;             // overflow
    if (!real_malloc){ resolve_real(); if (!real_malloc){ void*p=boot_alloc(total); if(p)memset(p,0,total); return p; } }
    void *p = real_malloc(addpad(total));
    if (p) memset(p, 0, total);                              // zero exactly the user's n bytes
    return p;
}
void *realloc(void *p, size_t n){
    if (!real_realloc){ resolve_real(); if(!real_realloc) return (void*)0; }
    if (p && in_boot(p)){                                    // grow a bootstrap chunk out to the real heap
        void *np = real_malloc(addpad(n));
        if (np){ size_t i=0; char*d=np,*s=p; for(; i<n; ++i) d[i]=s[i]; }
        return np;
    }
    return real_realloc(p, addpad(n));                       // real_realloc preserves min(old,new)
}
int posix_memalign(void **out, size_t align, size_t n){
    if (!real_posix_memalign){ resolve_real(); if(!real_posix_memalign) return 12; }  // ENOMEM
    return real_posix_memalign(out, align, addpad(n));
}
void *memalign(size_t align, size_t n){
    if (!real_memalign){ resolve_real(); if(!real_memalign) return (void*)0; }
    return real_memalign(align, addpad(n));
}
void *aligned_alloc(size_t align, size_t n){
    if (!real_aligned_alloc){ resolve_real(); if(!real_aligned_alloc) return (void*)0; }
    size_t pad = addpad(n);
    if (align) pad = (pad + align - 1) & ~(align - 1);       // keep size a multiple of align (C11)
    return real_aligned_alloc(align, pad);
}
size_t malloc_usable_size(void *p){
    if (in_boot(p)) return 0;
    if (!real_usable) resolve_real();
    return real_usable ? real_usable(p) : 0;                 // real usable (incl. slack) — safe to use
}

__attribute__((constructor(101)))
static void pad_init(void){
    resolve_real();
    puts2("[WGWP-PAD] armed (global slack-padding, SLACK=64, pure pass-through +slack)\n");
    const char *shim = getenv("WGWP_SHIM"); if (!shim || !shim[0]) shim = "/data/local/tmp/asx/webview-t-lib/libwebview_bionic_shim.so";
    void *h = dlopen(shim, RTLD_GLOBAL | RTLD_NOW);
    if (!h){ puts2("[WGWP-PAD] shim dlopen FAILED path="); puts2(shim); puts2("\n"); char*er=dlerror(); if(er){puts2("[WGWP-PAD]   dlerror="); puts2(er); puts2("\n");} }
    else puts2("[WGWP-PAD] shim chain-loaded\n");
}
