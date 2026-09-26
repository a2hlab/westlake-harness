// westlake_canary.c — canary-guard-ALL malloc interposer (#48 path A hedge)
// Companion to libwestlake_gwp (page-guard). Trade-off:
//   page-guard: faults AT the corrupting write (PC == corruptor) but is per-page -> must SAMPLE,
//               and its page churn perturbs timing (Heisenbug).
//   canary-ALL: BYTE-cost redzones -> guards EVERY allocation, no sampling, low timing perturbation
//               (good for unattended long runs); detects overflow/UAF at free() and on a periodic
//               scan; reports the OVERFLOWED buffer + its ALLOCATION SITE (which lib/function
//               malloc'd it) + the clobbered canary bytes. It does NOT give the corruptor's write
//               PC (detection is deferred), so it complements page-guard rather than replacing it.
//
// Layout per allocation (served from the real allocator):
//   [ hdr_t: magic,size,site,fcanary ][ user bytes (size) ][ rear redzone (g_rear bytes, 0xEC) ]
// malloc returns base+sizeof(hdr_t). site = __builtin_return_address(0) (the malloc caller).
// free(): recover hdr; if magic is ours, verify fcanary (underflow) + rear redzone (overflow);
//   on mismatch -> report (buffer, size, alloc-site, which canary, clobber bytes) and (default) abort
//   so out-crash42 captures. Then real_free(base). Non-ours pointers pass through to real_free.
// Periodic scan (WGWP_SCAN=N): every N mallocs, walk a bounded ring of live blocks and verify
//   canaries -> catches corruption BEFORE the buffer is freed (closer to the write in time).
//
// Header-minimal (self-contained decls) -> builds against any OH sysroot; -nostdlib; no __emutls.
// Env: WGWP_REAR=bytes(default 16) WGWP_SCAN=N(default 0=off) WGWP_ABORT=0/1(default 1)
//      WGWP_CAP=ring(default 65536) WGWP_LOG=0/1
#include <stddef.h>
#include <stdint.h>

extern void *dlsym(void *, const char *);
extern char *getenv(const char *);
extern int   atoi(const char *);
extern long  atol(const char *);
extern long  write(int, const void *, size_t);
extern void *memcpy(void *, const void *, size_t);
extern void *memset(void *, int, size_t);
extern void  abort(void);
#define RTLD_NEXT ((void *)-1)

static void *(*real_malloc)(size_t);
static void  (*real_free)(void *);
static void *(*real_calloc)(size_t, size_t);
static void *(*real_realloc)(void *, size_t);
static int   (*real_posix_memalign)(void **, size_t, size_t);
static size_t (*real_usable)(void *);

#define HMAGIC   0x5741434e41525921ULL  /* 'WACNARY!' */
#define FCANARY  0xC0DEFACEDEADBEEFULL
#define RFILL    0xEC
static int    g_rear = 16, g_abort = 1, g_log = 0;
static unsigned long g_scan = 0, g_cap = 65536;
static int    g_ready = 0;
static unsigned long g_mallocs = 0;

typedef struct { uint64_t magic; size_t size; void *site; uint64_t fcanary; } hdr_t;

static char g_boot[1 << 20]; static size_t g_boot_off = 0;
static int in_boot(void *p){ return (char*)p>=g_boot && (char*)p<g_boot+sizeof(g_boot); }
static void *boot_alloc(size_t n){ size_t a=(n+15)&~(size_t)15; if(g_boot_off+a>sizeof(g_boot))return 0; void*p=g_boot+g_boot_off; g_boot_off+=a; return p; }

static volatile int g_spin=0, g_reentry=0;
static void LOCK(void){ while(__atomic_exchange_n(&g_spin,1,__ATOMIC_ACQUIRE)){} }
static void UNLOCK(void){ __atomic_store_n(&g_spin,0,__ATOMIC_RELEASE); }
static void **g_live=0;   // bounded ring of live user ptrs (for periodic scan)

static void resolve_real(void){
    real_malloc=(void*(*)(size_t))dlsym(RTLD_NEXT,"malloc");
    real_free=(void(*)(void*))dlsym(RTLD_NEXT,"free");
    real_calloc=(void*(*)(size_t,size_t))dlsym(RTLD_NEXT,"calloc");
    real_realloc=(void*(*)(void*,size_t))dlsym(RTLD_NEXT,"realloc");
    real_posix_memalign=(int(*)(void**,size_t,size_t))dlsym(RTLD_NEXT,"posix_memalign");
    real_usable=(size_t(*)(void*))dlsym(RTLD_NEXT,"malloc_usable_size");
}
// need mmap for the ring (avoid recursing into our own malloc)
extern void *mmap(void*,size_t,int,int,int,long);
#define PROT_RW 3
#define MAP_PA  0x22   /* MAP_PRIVATE|MAP_ANON */

__attribute__((constructor(101)))
static void canary_init(void){
    char *e;
    if((e=getenv("WGWP_REAR"))){ int v=atoi(e); if(v>=8) g_rear=v; }
    if((e=getenv("WGWP_SCAN"))) g_scan=(unsigned long)atol(e);
    if((e=getenv("WGWP_ABORT"))) g_abort=atoi(e)?1:0;
    if((e=getenv("WGWP_CAP"))){ long v=atol(e); if(v>=256) g_cap=(unsigned long)v; }
    if((e=getenv("WGWP_LOG"))) g_log=atoi(e)?1:0;
    resolve_real();
    if(g_scan){ size_t len=((g_cap*sizeof(void*))+4095)&~(size_t)4095;
        void*r=mmap(0,len,PROT_RW,MAP_PA,-1,0); if(r!=(void*)-1) g_live=(void**)r; }
    g_ready=1;
    if(g_log){ const char m[]="[WGWP-CANARY] armed\n"; (void)write(2,m,sizeof(m)-1); }
}

// hex helpers for the report (no libc)
static void puts2(const char*s){ size_t n=0; while(s[n])n++; (void)write(2,s,n); }
static void puthex(unsigned long v){ char b[19]; int i; b[0]='0';b[1]='x'; for(i=0;i<16;i++){int nib=(v>>((15-i)*4))&0xf; b[2+i]=nib<10?('0'+nib):('a'+nib-10);} b[18]='\n'; (void)write(2,b,19); }

static void report(const char*what, void*user, size_t size, void*site, unsigned long clobber){
    puts2("[WGWP-CANARY] CORRUPTION "); puts2(what);
    puts2("\n  buffer="); puthex((unsigned long)user);
    puts2("  size="); puthex((unsigned long)size);
    puts2("  alloc_site="); puthex((unsigned long)site);       // resolve: site - lib base = file offset
    puts2("  clobber="); puthex(clobber);                       // overwritten canary word (writer signature)
    if(g_abort) abort();                                        // let out-crash42 capture PC/maps here
}

static int check_block(hdr_t*h, void*user){
    if(h->magic!=HMAGIC) return 1;                              // not ours / already torn
    if(h->fcanary!=FCANARY){ report("UNDERFLOW(front-canary)", user, h->size, h->site, h->fcanary); return 0; }
    unsigned char*rz=(unsigned char*)user + h->size;
    for(int i=0;i<g_rear;i++) if(rz[i]!=RFILL){
        unsigned long cw=0; for(int j=0;j<8 && i+j<g_rear;j++) cw|=((unsigned long)rz[i+j])<<(j*8);
        report("OVERFLOW(rear-redzone)", user, h->size, h->site, cw); return 0; }
    return 1;
}

static void reg_add(void*user){ if(!g_live)return; LOCK(); g_live[g_mallocs % g_cap]=user; UNLOCK(); }
static void periodic_scan(void){
    if(!g_live) return;
    LOCK();
    for(unsigned long i=0;i<g_cap;i++){ void*u=g_live[i]; if(!u)continue;
        hdr_t*h=(hdr_t*)((char*)u-sizeof(hdr_t)); check_block(h,u); }
    UNLOCK();
}

static void *carve(size_t n, void*site){
    size_t need=sizeof(hdr_t)+n+(size_t)g_rear;
    char*base=(char*)real_malloc(need); if(!base) return 0;
    hdr_t*h=(hdr_t*)base; h->magic=HMAGIC; h->size=n; h->site=site; h->fcanary=FCANARY;
    char*user=base+sizeof(hdr_t);
    memset(user+n,RFILL,(size_t)g_rear);
    reg_add(user);
    unsigned long m=__atomic_add_fetch(&g_mallocs,1,__ATOMIC_RELAXED);
    if(g_scan && (m % g_scan)==0){ g_reentry=1; periodic_scan(); g_reentry=0; }
    return user;
}

void *malloc(size_t n){
    if(!real_malloc){ resolve_real(); if(!real_malloc) return boot_alloc(n); }
    if(g_ready && !g_reentry){ g_reentry=1; void*p=carve(n,__builtin_return_address(0)); g_reentry=0; if(p) return p; }
    return real_malloc(n);
}
void *calloc(size_t nm,size_t sz){
    if(!real_calloc){ resolve_real(); if(!real_calloc){ size_t t=nm*sz; void*p=boot_alloc(t); if(p)memset(p,0,t); return p; } }
    size_t t=nm*sz; if(sz && t/sz!=nm) return 0;
    if(g_ready && !g_reentry){ g_reentry=1; void*p=carve(t,__builtin_return_address(0)); g_reentry=0; if(p){ memset(p,0,t); return p; } }
    return real_calloc(nm,sz);
}
void free(void *p){
    if(!p) return;
    if(in_boot(p)) return;
    hdr_t*h=(hdr_t*)((char*)p-sizeof(hdr_t));
    if(g_ready && h->magic==HMAGIC){ check_block(h,p); h->magic=0; /* poison */ if(g_live){ /* leave stale slot; scan skips via magic */ } if(real_free) real_free((void*)h); return; }
    if(real_free) real_free(p);
}
void *realloc(void*p,size_t n){
    if(!real_realloc) resolve_real();
    if(p && !in_boot(p)){ hdr_t*h=(hdr_t*)((char*)p-sizeof(hdr_t));
        if(g_ready && h->magic==HMAGIC){ check_block(h,p); void*np=malloc(n); if(np) memcpy(np,p,h->size<n?h->size:n); h->magic=0; if(real_free) real_free((void*)h); return np; } }
    if(p && in_boot(p)){ void*np=malloc(n); if(np) memcpy(np,p,n); return np; }
    if(g_ready && !g_reentry){ g_reentry=1; void*np=carve(n,__builtin_return_address(0)); g_reentry=0;
        if(np){ if(p){ memcpy(np,p,n); if(real_free) real_free(p);} return np; } }
    return real_realloc?real_realloc(p,n):0;
}
int posix_memalign(void**out,size_t align,size_t n){
    if(!real_posix_memalign) resolve_real();
    // canary path only when the natural (16B) alignment satisfies the request; else pass through
    if(g_ready && !g_reentry && align<=16){ g_reentry=1; void*p=carve(n,__builtin_return_address(0)); g_reentry=0;
        if(p && ((uintptr_t)p%align)==0){ *out=p; return 0; } }
    return real_posix_memalign?real_posix_memalign(out,align,n):22;
}
void *memalign(size_t a,size_t n){ void*o=0; return posix_memalign(&o,a,n)==0?o:0; }
void *aligned_alloc(size_t a,size_t n){ return memalign(a,n); }
size_t malloc_usable_size(void*p){
    if(p && !in_boot(p)){ hdr_t*h=(hdr_t*)((char*)p-sizeof(hdr_t)); if(g_ready && h->magic==HMAGIC) return h->size; }
    if(!real_usable) real_usable=(size_t(*)(void*))dlsym(RTLD_NEXT,"malloc_usable_size");
    return real_usable?real_usable(p):0;
}
