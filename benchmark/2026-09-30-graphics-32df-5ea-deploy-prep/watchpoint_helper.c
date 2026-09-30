// watchpoint_helper.c — arm64 ptrace HW write-watchpoint on the GrGLContext/GrGLInterface
// pointer field, to catch the writer of the misaligned value (Skia GL-family SIGSEGV).
// Method B3 (SKIA WATCHPOINT-EXPERIMENT-SPEC.md): SW breakpoint at onResetContext entry to
// resolve the per-run object address A, then HW write watchpoint on A; dump writer PC + fp-chain.
//
// Build (OH clang, arm64):  $OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang \
//     --target=aarch64-linux-ohos -static -O2 watchpoint_helper.c -o watchpoint_helper
// Run on board:  ./watchpoint_helper <renderthread_tid> <libskia_base_hex>
//   (get tid: the thread named RenderThread in the app pid; get base from /proc/<pid>/maps
//    for libskia_canvaskit.z.so). onResetContext file-offset is 0x123d230 (from disasm; verify
//    against the deployed .so — recompute if build-id != 2f7219f2).
//
// SAFETY: PTRACE_SEIZE (non-stop attach), clean PTRACE_DETACH on exit/signal. NEVER kill the
// tracee or appspawn-x. If the watchdog kills the paused process, fall back to spec retreat C.

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <signal.h>
#include <sys/ptrace.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/uio.h>
#include <linux/elf.h>
#include <linux/ptrace.h>
#include <asm/ptrace.h>   // struct user_pt_regs, struct user_hwdebug_state (aarch64 sysroot)

// onResetContext entry = base + this offset (verify vs deployed build-id 2f7219f2)
#define ONRESET_OFF 0x123d230UL
#define BRK_INSN    0xd4200000U   // aarch64 BRK #0

static long g_tid;

// ARM64 hardware watchpoint control register (DBGWCR) bit layout used via NT_ARM_HW_WATCH.
// E(enable)=bit0; PAC(priv)=bits1:2 (0b10 = EL0/user); LSC(load/store)=bits3:4 (0b10 = store/write);
// BAS(byte addr select)=bits5:12 (0xFF = 8 bytes). => write, 8 bytes, user.
static uint32_t wp_ctrl_write8(void){ return (1u<<0) | (0b10u<<1) | (0b10u<<3) | (0xFFu<<5); }

// struct user_hwdebug_state comes from <asm/ptrace.h> (sysroot)

static int getregs(struct user_pt_regs *r){
    struct iovec io = { r, sizeof(*r) };
    return ptrace(PTRACE_GETREGSET, g_tid, (void*)NT_PRSTATUS, &io);
}
static uint64_t peek(uint64_t addr){
    uint64_t v=0; struct iovec l={&v,8}, r={(void*)addr,8};
    process_vm_readv(g_tid,&l,1,&r,1,0); return v;
}

static int set_watchpoint(uint64_t A){
    struct user_hwdebug_state ws; memset(&ws,0,sizeof(ws));
    ws.dbg_regs[0].addr = A;                 // 8-byte aligned base of the slot
    ws.dbg_regs[0].ctrl = wp_ctrl_write8();
    struct iovec io = { &ws, sizeof(ws) };
    return ptrace(PTRACE_SETREGSET, g_tid, (void*)NT_ARM_HW_WATCH, &io);
}

static void dump_writer(void){
    struct user_pt_regs r; if(getregs(&r)){ perror("getregs"); return; }
    fprintf(stderr,"[WP-HIT] pc=%#llx lr=%#llx sp=%#llx x29=%#llx\n",
            (unsigned long long)r.pc,(unsigned long long)r.regs[30],
            (unsigned long long)r.sp,(unsigned long long)r.regs[29]);
    // mini fp-chain unwind: [fp]=next fp, [fp+8]=return addr
    uint64_t fp=r.regs[29];
    for(int i=0;i<24 && fp;i++){
        uint64_t ra=peek(fp+8), nfp=peek(fp);
        fprintf(stderr,"  #%02d ra=%#llx\n",i,(unsigned long long)ra);
        if(nfp<=fp) break; fp=nfp;
    }
}

int main(int argc,char**argv){
    if(argc<3){ fprintf(stderr,"usage: %s <renderthread_tid> <libskia_base_hex>\n",argv[0]); return 2; }
    g_tid = strtol(argv[1],0,0);
    uint64_t base = strtoull(argv[2],0,16);
    uint64_t brk_at = base + ONRESET_OFF;

    if(ptrace(PTRACE_SEIZE,g_tid,0,0)){ perror("SEIZE"); return 1; }
    if(ptrace(PTRACE_INTERRUPT,g_tid,0,0)){ perror("INTERRUPT"); }
    int st; waitpid(g_tid,&st,__WALL);

    // 1) plant SW breakpoint (BRK) at onResetContext entry to capture a valid object address.
    uint64_t orig = peek(brk_at);
    uint64_t patched = (orig & ~0xffffffffULL) | BRK_INSN;
    { struct iovec l={&patched,8}, rr={(void*)brk_at,8}; process_vm_writev(g_tid,&l,1,&rr,1,0); }
    ptrace(PTRACE_CONT,g_tid,0,0);
    waitpid(g_tid,&st,__WALL);          // stops at BRK

    // 2) resolve A = *(GrGLGpu+0xb0) + 0x8   (address of the pointer slot)
    struct user_pt_regs r; getregs(&r);
    uint64_t self = r.regs[19];         // x19 = GrGLGpu this (per disasm)
    uint64_t inner = peek(self + 0xb0); // *(this+0xb0)
    uint64_t A = inner + 0x8;           // slot address
    uint64_t cur = peek(A);
    fprintf(stderr,"[RESOLVE] this=%#llx inner=%#llx A=%#llx cur=%#llx %s\n",
            (unsigned long long)self,(unsigned long long)inner,(unsigned long long)A,
            (unsigned long long)cur,(cur&7)?"(cur MISALIGNED!)":"(cur aligned)");

    // restore original insn, rewind pc to re-exec it
    { struct iovec l={&orig,8}, rr={(void*)brk_at,8}; process_vm_writev(g_tid,&l,1,&rr,1,0); }
    r.pc = brk_at; { struct iovec io={&r,sizeof(r)}; ptrace(PTRACE_SETREGSET,g_tid,(void*)NT_PRSTATUS,&io); }

    // 3) HW write watchpoint on A; wait for the corrupting store.
    if(set_watchpoint(A)){ perror("SETREGSET NT_ARM_HW_WATCH"); ptrace(PTRACE_DETACH,g_tid,0,0); return 1; }
    fprintf(stderr,"[WP-ARMED] write watchpoint on A=%#llx (8 bytes)\n",(unsigned long long)A);

    for(;;){
        ptrace(PTRACE_CONT,g_tid,0,0);
        if(waitpid(g_tid,&st,__WALL)<0) break;
        if(WIFEXITED(st)||WIFSIGNALED(st)){ fprintf(stderr,"[EXIT] tracee gone\n"); break; }
        if(WIFSTOPPED(st) && WSTOPSIG(st)==SIGTRAP){
            uint64_t v=peek(A);
            fprintf(stderr,"[WP-WRITE] A=%#llx newval=%#llx %s\n",(unsigned long long)A,
                    (unsigned long long)v,(v&7)?"<< MISALIGNED WRITE — WRITER FOUND":"(aligned; benign)");
            dump_writer();
            if(v&7){ fprintf(stderr,"[DONE] captured corrupting writer.\n"); break; }
            // aligned write: benign re-init, keep watching
        }
    }
    ptrace(PTRACE_DETACH,g_tid,0,0);     // clean detach; never kill
    return 0;
}
