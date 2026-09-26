// westlake_gwp_shim.c — LEFT-adjacent page-guard malloc interposer + shim chain-load (#48)
// Hunts the NON-HOOK mallocng HEADER/underflow corruptor (p-4 / front-zone clobber; the rear-zone
// canary stayed silent, and musl a_crashes at 0xd6e20 in its own metadata check with si_addr=0 =
// its own null write, victim != writer). A page-guard faults AT the corrupting write so the crash
// PC == the writer. Because the clobber is BEFORE the user pointer, the guard page must be
// LEFT-adjacent: user data is page-aligned at the START with a PROT_NONE guard page immediately
// BEFORE it, so a write to p-4 / p-K (K<=PAGE) lands in the guard and faults at the write.
//
// Env-free (DIGEST B-9: env does not reach the appspawn-x child): everything is hardcoded on by
// default. Single-slot preload: point WESTLAKE_ANDROID_NATIVE_PRELOAD at THIS .so; it CHAIN-LOADS
// libwebview_bionic_shim (app-required) itself. A SA_SIGINFO SIGSEGV handler resolves the faulting
// PC -> lib+offset IN-PROCESS via dl_iterate_phdr (defeats the /proc EACCES / DFX gap) and logs it
// plus the guarded block's allocation-site return address, then chains to the previous handler
// (out-crash42) so it still captures. Header-minimal, -nostdlib.
//
// Env overrides (only if they reach the process): WGWP_SAMPLE(default 1=guard all) WGWP_CAP(default
// 4096 live guarded regions, recycled) WGWP_MAXSZ(default page) WGWP_SHIM(default board shim path).
#include <stddef.h>
#include <stdint.h>

extern void *mmap(void *, size_t, int, int, int, long);
extern int   munmap(void *, size_t);
extern int   mprotect(void *, size_t, int);
extern void *dlsym(void *, const char *);
extern void *dlopen(const char *, int);
extern char *dlerror(void);
extern int   dl_iterate_phdr(int (*)(void *, size_t, void *), void *);
extern char *getenv(const char *);
extern int   atoi(const char *);
extern long  atol(const char *);
extern long  write(int, const void *, size_t);
extern void *memset(void *, int, size_t);
extern void *memcpy(void *, const void *, size_t);
extern int   sigaction(int, const void *, void *);
extern void  abort(void);

#define PROT_NONE 0
#define PROT_RW   3
#define MAP_PA    0x22
#define MAP_FAILED ((void*)-1)
#define RTLD_NEXT ((void*)-1)
#define RTLD_NOW  0x2
#define RTLD_GLOBAL 0x100
#define PAGE ((size_t)4096)
#define SIGSEGV_ 11
#define SA_SIGINFO_ 4
#define PT_LOAD 1
// aarch64 musl ucontext_t: uc_mcontext@168 -> pc@432. x86_64 glibc: RIP within gregs @168 (self-test).
#if defined(__aarch64__)
#define UC_PC_OFF 432
#elif defined(__x86_64__)
#define UC_PC_OFF 168
#else
#define UC_PC_OFF 432
#endif
#define SI_ADDR_OFF 16   /* siginfo_t si_addr: offset 16 on glibc & musl (both arches) */

static void *(*real_malloc)(size_t);
static void  (*real_free)(void *);
static void *(*real_calloc)(size_t, size_t);
static void *(*real_realloc)(void *, size_t);
static int   (*real_posix_memalign)(void **, size_t, size_t);
static size_t (*real_usable)(void *);

static int g_sample = 1, g_ready = 0;
static size_t g_cap = 16384, g_minsz = 1, g_maxsz = (size_t)-1;  /* v3: no size cap -> guard ALL sizes (IO buffers >4KB too) */

static char g_boot[1 << 20]; static size_t g_boot_off = 0;
static int in_boot(void *p){ return (char*)p>=g_boot && (char*)p<g_boot+sizeof(g_boot); }
static void *boot_alloc(size_t n){ size_t a=(n+15)&~(size_t)15; if(g_boot_off+a>sizeof(g_boot))return 0; void*p=g_boot+g_boot_off; g_boot_off+=a; return p; }

static volatile int g_spin=0, g_reentry=0;
static void LOCK(void){ while(__atomic_exchange_n(&g_spin,1,__ATOMIC_ACQUIRE)){} }
static void UNLOCK(void){ __atomic_store_n(&g_spin,0,__ATOMIC_RELEASE); }
static unsigned long g_counter=0;

typedef struct { void*map; size_t maplen; void*user; size_t usize; void*site; } region_t;
static region_t *g_regs=0; static size_t g_head=0, g_live=0;

// ---- async-signal-safe logging ----
static void puts2(const char*s){ size_t n=0; while(s[n])n++; (void)write(2,s,n); }
static void puthex(unsigned long v){ char b[19]; b[0]='0';b[1]='x'; for(int i=0;i<16;i++){int nib=(v>>((15-i)*4))&0xf; b[2+i]=nib<10?('0'+nib):('a'+nib-10);} b[18]='\n'; (void)write(2,b,19); }

static void resolve_real(void){
    real_malloc=(void*(*)(size_t))dlsym(RTLD_NEXT,"malloc");
    real_free=(void(*)(void*))dlsym(RTLD_NEXT,"free");
    real_calloc=(void*(*)(size_t,size_t))dlsym(RTLD_NEXT,"calloc");
    real_realloc=(void*(*)(void*,size_t))dlsym(RTLD_NEXT,"realloc");
    real_posix_memalign=(int(*)(void**,size_t,size_t))dlsym(RTLD_NEXT,"posix_memalign");
    real_usable=(size_t(*)(void*))dlsym(RTLD_NEXT,"malloc_usable_size");
}

// dl_iterate_phdr callback: find the lib whose PT_LOAD contains target pc -> name + file offset
struct find_ctx { unsigned long pc; const char *name; unsigned long off; int found; };
static int phdr_cb(void *info, size_t sz, void *data){
    (void)sz; struct find_ctx *fc=(struct find_ctx*)data;
    unsigned long base = *(unsigned long*)info;                 // dlpi_addr @0
    const char *name  = *(const char**)((char*)info+8);         // dlpi_name @8
    const void *phdr  = *(const void**)((char*)info+16);        // dlpi_phdr @16
    unsigned short pn = *(unsigned short*)((char*)info+24);     // dlpi_phnum @24
    for(unsigned short i=0;i<pn;i++){
        const char *ph=(const char*)phdr + (size_t)i*56;        // Elf64_Phdr = 56 bytes
        uint32_t ptype=*(uint32_t*)ph;                          // p_type @0
        if(ptype!=PT_LOAD) continue;
        unsigned long vaddr=*(unsigned long*)(ph+16);           // p_vaddr @16
        unsigned long memsz=*(unsigned long*)(ph+40);           // p_memsz @40
        unsigned long lo=base+vaddr, hi=lo+memsz;
        if(fc->pc>=lo && fc->pc<hi){ fc->name=(name&&name[0])?name:"(main/anon)"; fc->off=fc->pc-base; fc->found=1; return 1; }
    }
    return 0;
}

static region_t *find_region_addr(unsigned long a){
    for(size_t i=0;i<g_cap;i++){ region_t*r=&g_regs[i]; if(!r->map) continue;
        if(a>=(unsigned long)r->map && a<(unsigned long)r->map+r->maplen) return r; }
    return 0;
}

// chained previous SIGSEGV handler storage (musl struct sigaction = 152B: handler@0, mask@8(128), flags@136, restorer@144)
static unsigned char g_oldsa[160];
static void seg_handler(int sig, void *si, void *uc){
    unsigned long pc = *(unsigned long*)((char*)uc + UC_PC_OFF);
    unsigned long fa = *(unsigned long*)((char*)si + SI_ADDR_OFF);
    puts2("[WGWP-GUARD] FAULT (guard page hit at the corrupting write)\n");
    puts2("  fault_addr="); puthex(fa);
    puts2("  writer_pc=");  puthex(pc);
    struct find_ctx fc = {pc,0,0,0};
    dl_iterate_phdr(phdr_cb,&fc);
    if(fc.found){ puts2("  writer_lib="); puts2(fc.name); puts2("\n  writer_off="); puthex(fc.off); }
    else puts2("  writer_lib=UNRESOLVED (see out-crash42 pc+maps)\n");
    region_t *r=find_region_addr(fa);
    if(r){ puts2("  victim_buffer="); puthex((unsigned long)r->user); puts2("  victim_size="); puthex((unsigned long)r->usize); puts2("  alloc_site="); puthex((unsigned long)r->site); }
    // chain to the previous handler (out-crash42) so it also captures; else abort
    unsigned long oldh = *(unsigned long*)g_oldsa;              // old sa_handler/sa_sigaction @0
    unsigned long oldfl= *(unsigned long*)(g_oldsa+136);        // old sa_flags @136
    if(oldh && oldh!=0 && oldh!=1){
        if(oldfl & SA_SIGINFO_){ ((void(*)(int,void*,void*))oldh)(sig,si,uc); }
        else { ((void(*)(int))oldh)(sig); }
        return;
    }
    abort();
}

static void install_handler(void){
    unsigned char act[160]; memset(act,0,sizeof(act));
    *(unsigned long*)act = (unsigned long)&seg_handler;          // sa_handler/sa_sigaction @0
    *(unsigned long*)(act+136) = SA_SIGINFO_;                    // sa_flags @136 (after 8+128 mask)
    sigaction(SIGSEGV_, act, g_oldsa);                           // musl writes 152B into our 160B buf (no OOB)
}

__attribute__((constructor(101)))
static void gwp_init(void){
    char *e;
    if((e=getenv("WGWP_SAMPLE"))){ int v=atoi(e); if(v>=1) g_sample=v; }
    if((e=getenv("WGWP_CAP"))){ long v=atol(e); if(v>=16) g_cap=(size_t)v; }
    if((e=getenv("WGWP_MAXSZ"))){ g_maxsz=(size_t)atol(e); }
    resolve_real();
    size_t rlen=((g_cap*sizeof(region_t))+PAGE-1)&~(PAGE-1);
    void*r=mmap(0,rlen,PROT_RW,MAP_PA,-1,0);
    if(r!=MAP_FAILED){ g_regs=(region_t*)r; g_ready=1; }
    install_handler();
    puts2("[WGWP-GUARD] armed (LEFT-adjacent page-guard, env-free)\n");
    // chain-load the app-required bionic-compat shim (single-slot preload now points at us)
    const char *shim=getenv("WGWP_SHIM"); if(!shim||!shim[0]) shim="/data/local/tmp/asx/webview-t-lib/libwebview_bionic_shim.so";
    void*h=dlopen(shim,RTLD_GLOBAL|RTLD_NOW);
    if(!h){ puts2("[WGWP-GUARD] shim dlopen FAILED path="); puts2(shim); puts2("\n"); char*er=dlerror(); if(er){puts2("[WGWP-GUARD]   dlerror="); puts2(er); puts2("\n");} }
    else { puts2("[WGWP-GUARD] shim chain-loaded: "); puts2(shim); puts2("\n"); }
}

// LEFT-adjacent guarded block: [ GUARD page (PROT_NONE) ][ data pages, user = page-aligned start ]
// a write to user-K (K<=PAGE), e.g. the p-4 header clobber, lands in the guard page -> faults at the write.
static void *guarded_alloc(size_t n, void *site){
    size_t datapages=(n+PAGE-1)/PAGE; if(!datapages) datapages=1;
    size_t maplen=(1+datapages)*PAGE;
    char*base=(char*)mmap(0,maplen,PROT_RW,MAP_PA,-1,0); if(base==MAP_FAILED) return 0;
    if(mprotect(base,PAGE,PROT_NONE)!=0){ munmap(base,maplen); return 0; }   // LEFT guard page
    char*user=base+PAGE;                                                     // page-aligned start
    LOCK();
    if(g_live>=g_cap){ region_t*o=&g_regs[g_head]; if(o->map){ munmap(o->map,o->maplen); o->map=0; g_live--; } }
    region_t*s=&g_regs[g_head]; s->map=base; s->maplen=maplen; s->user=user; s->usize=n; s->site=site;
    g_head=(g_head+1)%g_cap; g_live++;
    UNLOCK();
    return user;
}
static region_t *find_region_user(void *p){
    if(!g_ready) return 0; unsigned long up=(unsigned long)p;
    for(size_t i=0;i<g_cap;i++){ region_t*r=&g_regs[i]; if(r->map && (r->user==p || (up>=(unsigned long)r->user && up<(unsigned long)r->user+r->usize))) return r; }
    return 0;
}
static int should_guard(size_t n){ if(!g_ready||!real_malloc||g_reentry) return 0; if(n<g_minsz||n>g_maxsz) return 0;
    unsigned long c=__atomic_add_fetch(&g_counter,1,__ATOMIC_RELAXED); return (c%(unsigned long)g_sample)==0; }

void *malloc(size_t n){
    if(!real_malloc){ resolve_real(); if(!real_malloc) return boot_alloc(n); }
    if(should_guard(n)){ g_reentry=1; void*p=guarded_alloc(n,__builtin_return_address(0)); g_reentry=0; if(p) return p; }
    return real_malloc(n);
}
void *calloc(size_t nm,size_t sz){
    if(!real_calloc){ resolve_real(); if(!real_calloc){ size_t t=nm*sz; void*p=boot_alloc(t); if(p)memset(p,0,t); return p; } }
    size_t t=nm*sz; if(sz && t/sz!=nm) return 0;
    if(should_guard(t)){ g_reentry=1; void*p=guarded_alloc(t,__builtin_return_address(0)); g_reentry=0; if(p) return p; } // mmap zero-filled
    return real_calloc(nm,sz);
}
void free(void *p){
    if(!p) return;
    if(in_boot(p)) return;
    region_t *r=find_region_user(p);
    if(r){ LOCK(); if(r->map){ munmap(r->map,r->maplen); r->map=0; g_live--; } UNLOCK(); return; }  // unmap -> UAF write faults
    if(real_free) real_free(p);
}
void *realloc(void*p,size_t n){
    if(!real_realloc) resolve_real();
    region_t*r=p?find_region_user(p):0;
    if(r){ void*np=malloc(n); if(np) memcpy(np,p,r->usize<n?r->usize:n); free(p); return np; }
    if(p && in_boot(p)){ void*np=malloc(n); if(np) memcpy(np,p,n); return np; }
    if(should_guard(n)){ g_reentry=1; void*gp=guarded_alloc(n,__builtin_return_address(0)); g_reentry=0; if(gp){ if(p){ memcpy(gp,p,n); if(real_free) real_free(p);} return gp; } }
    return real_realloc?real_realloc(p,n):0;
}
int posix_memalign(void**out,size_t align,size_t n){
    if(!real_posix_memalign) resolve_real();
    // page-aligned user already satisfies alignments up to PAGE
    if(should_guard(n) && align<=PAGE){ g_reentry=1; void*p=guarded_alloc(n,__builtin_return_address(0)); g_reentry=0; if(p && ((uintptr_t)p%align)==0){ *out=p; return 0; } if(p) free(p); }
    return real_posix_memalign?real_posix_memalign(out,align,n):22;
}
void *memalign(size_t a,size_t n){ void*o=0; return posix_memalign(&o,a,n)==0?o:0; }
void *aligned_alloc(size_t a,size_t n){ return memalign(a,n); }
size_t malloc_usable_size(void*p){ region_t*r=p?find_region_user(p):0; if(r) return r->usize;
    if(!real_usable) real_usable=(size_t(*)(void*))dlsym(RTLD_NEXT,"malloc_usable_size"); return real_usable?real_usable(p):0; }
