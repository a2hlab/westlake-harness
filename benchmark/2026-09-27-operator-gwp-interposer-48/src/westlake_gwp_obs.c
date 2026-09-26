// westlake_gwp_obs.c — v4 OBSERVER (#48). NO guarding (does not perturb musl layout).
// The non-hook mallocng corruption clobbers a SHARED musl group/meta (victim thread random across
// main/ChromiumNet0/RenderThread/bd_tracker/platform-io, all a_crash at ld-musl 0xd6e20), NOT a
// thread-local user chunk — so a user-allocation adjacency guard (canary / page-guard v2/v3) can
// never see it, and relocating blocks to a private pool even changes musl-group adjacency
// (Heisenberg). So this build STOPS guarding and becomes a pure observer: it lets the corruption
// happen naturally and, at the a_crash SIGSEGV (100% hit), dumps IN-PROCESS the evidence DFX can't
// (its /proc/self/mem is EACCES): the faulting PC->lib+off, ALL GP registers (x0..x30/sp/pc — the
// victim chunk/meta pointer is usually in a register at a_crash), and a frame-pointer backtrace of
// the DETECTING thread (each saved LR resolved to lib+off via dl_iterate_phdr) = the free()/realloc
// call chain that tripped musl's integrity check. Keeps chain-load of the app-required shim.
//
// Malloc family is a thin PASS-THROUGH (guarding disabled) so musl's native allocator/layout is
// untouched. To guarantee our SIGSEGV handler stays ON TOP (our preload runs before out-crash42, so
// a later installer would shadow us), we interpose sigaction: any SIGSEGV registration re-installs
// OURS on top and chains to theirs. Header-minimal, -nostdlib, env-free, aarch64.
#include <stddef.h>
#include <stdint.h>

extern void *dlsym(void *, const char *);
extern void *dlopen(const char *, int);
extern char *dlerror(void);
extern int   dl_iterate_phdr(int (*)(void *, size_t, void *), void *);
extern char *getenv(const char *);
extern long  write(int, const void *, size_t);
extern void *memset(void *, int, size_t);
extern void  abort(void);
extern int   sigaction(int, const void *, void *);   // interposed below

#define RTLD_NEXT ((void*)-1)
#define RTLD_NOW  0x2
#define RTLD_GLOBAL 0x100
#define SIGSEGV_ 11
#define SA_SIGINFO_ 4
#define PT_LOAD 1
#define SI_ADDR_OFF 16       // siginfo_t si_addr (glibc & musl, both arches)
#if defined(__aarch64__)
#define UC_REGS_OFF 176      // aarch64 musl ucontext: uc_mcontext.regs[0] @176 (x0..x30), sp@424, pc@432, x29(fp)@408
#define UC_SP_OFF   424
#define UC_PC_OFF   432
#define UC_FP_OFF   408
#define NREGS       31
#elif defined(__x86_64__)             // glibc x86_64 self-test: uc_mcontext.gregs @40; RIP@168 RSP@160 RBP@120
#define UC_REGS_OFF 40
#define UC_SP_OFF   160
#define UC_PC_OFF   168
#define UC_FP_OFF   120
#define NREGS       23
#else
#define UC_REGS_OFF 176
#define UC_SP_OFF   424
#define UC_PC_OFF   432
#define UC_FP_OFF   408
#define NREGS       31
#endif

static void *(*real_malloc)(size_t);
static void  (*real_free)(void *);
static void *(*real_calloc)(size_t, size_t);
static void *(*real_realloc)(void *, size_t);
static int   (*real_posix_memalign)(void **, size_t, size_t);
static void *(*real_memalign)(size_t, size_t);
static void *(*real_aligned_alloc)(size_t, size_t);
static size_t(*real_usable)(void *);
static int   (*real_sigaction)(int, const void *, void *);

static void puts2(const char*s){ size_t n=0; while(s[n])n++; (void)write(2,s,n); }
static void puthex(unsigned long v){ char b[19]; b[0]='0';b[1]='x'; for(int i=0;i<16;i++){int nib=(v>>((15-i)*4))&0xf; b[2+i]=nib<10?('0'+nib):('a'+nib-10);} b[18]='\n'; (void)write(2,b,19); }
static void kv(const char*k, unsigned long v){ puts2(k); puthex(v); }

static void resolve_real(void){
    real_malloc=(void*(*)(size_t))dlsym(RTLD_NEXT,"malloc");
    real_free=(void(*)(void*))dlsym(RTLD_NEXT,"free");
    real_calloc=(void*(*)(size_t,size_t))dlsym(RTLD_NEXT,"calloc");
    real_realloc=(void*(*)(void*,size_t))dlsym(RTLD_NEXT,"realloc");
    real_posix_memalign=(int(*)(void**,size_t,size_t))dlsym(RTLD_NEXT,"posix_memalign");
    real_memalign=(void*(*)(size_t,size_t))dlsym(RTLD_NEXT,"memalign");
    real_aligned_alloc=(void*(*)(size_t,size_t))dlsym(RTLD_NEXT,"aligned_alloc");
    real_usable=(size_t(*)(void*))dlsym(RTLD_NEXT,"malloc_usable_size");
    real_sigaction=(int(*)(int,const void*,void*))dlsym(RTLD_NEXT,"sigaction");
}

// resolve an address -> owning lib name + file offset (in-process; no /proc/maps needed)
struct find_ctx { unsigned long a; const char*name; unsigned long off; int found; };
static int phdr_cb(void*info, size_t sz, void*data){
    (void)sz; struct find_ctx*fc=(struct find_ctx*)data;
    unsigned long base=*(unsigned long*)info;
    const char*name=*(const char**)((char*)info+8);
    const void*phdr=*(const void**)((char*)info+16);
    unsigned short pn=*(unsigned short*)((char*)info+24);
    for(unsigned short i=0;i<pn;i++){ const char*ph=(const char*)phdr+(size_t)i*56;
        if(*(uint32_t*)ph!=PT_LOAD) continue;
        unsigned long lo=base+*(unsigned long*)(ph+16), hi=lo+*(unsigned long*)(ph+40);
        if(fc->a>=lo && fc->a<hi){ fc->name=(name&&name[0])?name:"(main/anon)"; fc->off=fc->a-base; fc->found=1; return 1; } }
    return 0;
}
static void resolve_print(const char*tag, unsigned long a){
    struct find_ctx fc={a,0,0,0}; dl_iterate_phdr(phdr_cb,&fc);
    puts2(tag); puthex(a);
    if(fc.found){ puts2("      -> "); puts2(fc.name); puts2(" + "); puthex(fc.off); }
    else puts2("      -> (unresolved)\n");
}

static unsigned long g_chain_h=0, g_chain_fl=0;   // handler we chain to (out-crash42)
static volatile int g_in_handler=0;

static void seg_handler(int sig, void*si, void*uc){
    if(__atomic_exchange_n(&g_in_handler,1,__ATOMIC_ACQ_REL)){
        // nested fault (e.g. while walking a bad fp) -> chain/abort immediately, no re-dump
        if(g_chain_h && g_chain_h!=1){ if(g_chain_fl&SA_SIGINFO_)((void(*)(int,void*,void*))g_chain_h)(sig,si,uc); else ((void(*)(int))g_chain_h)(sig); return; }
        abort();
    }
    unsigned long pc=*(unsigned long*)((char*)uc+UC_PC_OFF);
    unsigned long fa=*(unsigned long*)((char*)si+SI_ADDR_OFF);
    puts2("[WGWP-OBS] ==== SIGSEGV a_crash evidence ====\n");
    kv("  fault_addr=", fa);
    resolve_print("  pc=", pc);
    { struct find_ctx fc={pc,0,0,0}; dl_iterate_phdr(phdr_cb,&fc);
      if(fc.found && (fc.off==0xd6e20 || fc.off==0xd5e1c || (fc.off>=0xd6a00 && fc.off<=0xd6f00)))
          puts2("  *** PC in musl mallocng integrity a_crash region -> the fp-chain below is the free()/realloc caller; regs hold the victim chunk/meta ptr ***\n"); }
    // all GP registers (x0..x30), sp, pc — victim chunk/meta ptr usually in a reg at a_crash
    puts2("  regs:\n");
    for(int i=0;i<NREGS;i++){ char t[12]; int p=0; t[p++]=' ';t[p++]=' ';t[p++]=' ';t[p++]=' ';t[p++]='x'; if(i>=10)t[p++]='0'+i/10; t[p++]='0'+i%10; t[p++]='='; t[p]=0; puts2(t); puthex(*(unsigned long*)((char*)uc+UC_REGS_OFF+(size_t)i*8)); }
    kv("    sp =", *(unsigned long*)((char*)uc+UC_SP_OFF));
    kv("    pc =", pc);
    // frame-pointer backtrace of the DETECTING thread (the free/realloc stack DFX can't get)
    puts2("  fp-backtrace (saved LR per frame -> lib+off):\n");
    unsigned long fp=*(unsigned long*)((char*)uc+UC_FP_OFF);
    for(int k=0;k<32;k++){
        if(fp==0 || (fp&15)!=0) break;                 // sane fp: non-null, 16-aligned
        unsigned long saved_fp=*(unsigned long*)fp;     // [fp] (may fault -> nested handler chains out)
        unsigned long lr=*(unsigned long*)(fp+8);       // [fp+8]
        if(lr) resolve_print("    lr=", lr);
        if(saved_fp<=fp || saved_fp-fp>0x100000) break; // monotonic, bounded frame
        fp=saved_fp;
    }
    puts2("[WGWP-OBS] ==== end ====\n");
    // chain to out-crash42 (also captures) or abort (re-raise)
    if(g_chain_h && g_chain_h!=1){ if(g_chain_fl&SA_SIGINFO_)((void(*)(int,void*,void*))g_chain_h)(sig,si,uc); else ((void(*)(int))g_chain_h)(sig); g_in_handler=0; return; }
    abort();
}

static unsigned char g_oldsa[160];
static void install_ours(void){
    unsigned char act[160]; memset(act,0,sizeof(act));
    *(unsigned long*)act=(unsigned long)&seg_handler;      // sa_handler @0
    *(unsigned long*)(act+136)=SA_SIGINFO_;                // sa_flags @136 (after 8B handler + 128B mask)
    real_sigaction(SIGSEGV_, act, g_oldsa);                // our 160B buf -> no OOB
    unsigned long prev=*(unsigned long*)g_oldsa;
    if(prev && prev!=(unsigned long)&seg_handler){ g_chain_h=prev; g_chain_fl=*(unsigned long*)(g_oldsa+136); }
}

// interpose sigaction: keep OUR SIGSEGV handler on top; chain to whoever registers later (out-crash42)
int sigaction(int sig, const void*act, void*old){
    if(!real_sigaction) resolve_real();
    if(sig==SIGSEGV_ && act){
        unsigned long th=*(unsigned long*)act;
        if(th!=(unsigned long)&seg_handler){
            g_chain_h=th; g_chain_fl=*(unsigned long*)((char*)act+136);   // their handler = our new chain
            if(old){ memset(old,0,160); *(unsigned long*)old=(unsigned long)&seg_handler; }  // best-effort
            install_ours();                                              // re-assert ours on top
            return 0;
        }
    }
    return real_sigaction ? real_sigaction(sig,act,old) : 0;
}

__attribute__((constructor(101)))
static void obs_init(void){
    resolve_real();
    install_ours();
    puts2("[WGWP-OBS] armed (observer: no guarding; regs+fp-backtrace dump at a_crash)\n");
    const char*shim=getenv("WGWP_SHIM"); if(!shim||!shim[0]) shim="/data/local/tmp/asx/webview-t-lib/libwebview_bionic_shim.so";
    void*h=dlopen(shim,RTLD_GLOBAL|RTLD_NOW);
    if(!h){ puts2("[WGWP-OBS] shim dlopen FAILED path="); puts2(shim); puts2("\n"); char*er=dlerror(); if(er){puts2("[WGWP-OBS]   dlerror="); puts2(er); puts2("\n");} }
    else puts2("[WGWP-OBS] shim chain-loaded\n");
}

// thin PASS-THROUGH malloc family (guarding disabled -> musl native layout untouched)
void *malloc(size_t n){ if(!real_malloc) resolve_real(); return real_malloc(n); }
void free(void*p){ if(!real_free) resolve_real(); real_free(p); }
void *calloc(size_t a,size_t b){ if(!real_calloc) resolve_real(); return real_calloc(a,b); }
void *realloc(void*p,size_t n){ if(!real_realloc) resolve_real(); return real_realloc(p,n); }
int posix_memalign(void**o,size_t a,size_t n){ if(!real_posix_memalign) resolve_real(); return real_posix_memalign(o,a,n); }
void *memalign(size_t a,size_t n){ if(!real_memalign) resolve_real(); return real_memalign(a,n); }
void *aligned_alloc(size_t a,size_t n){ if(!real_aligned_alloc) resolve_real(); return real_aligned_alloc(a,n); }
size_t malloc_usable_size(void*p){ if(!real_usable) resolve_real(); return real_usable(p); }
