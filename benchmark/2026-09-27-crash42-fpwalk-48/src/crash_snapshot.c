#define _GNU_SOURCE
#include "crash_snapshot.h"
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <time.h>
#include <ucontext.h>
#include <unistd.h>
#include <link.h>
#include <elf.h>

/* No allocation, stdio, dladdr, locks, raw stack dereferences or signal APIs in
 * the observer. File I/O can still delay termination: this is diagnostic-only.
 * One capture at a time; concurrent/reentrant events are explicitly reported. */
static int root_fd = -1;
static unsigned busy;
static unsigned sequence;
static const uint64_t stack_limit = 64ull * 1024 * 1024;

static int put(int fd, const void *data, size_t size) {
    const char *p = data;
    while (size) {
        ssize_t n = write(fd, p, size);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return -1;
        p += n; size -= (size_t)n;
    }
    return 0;
}
static char *text(char *p, const char *s) { while (*s) *p++ = *s++; return p; }
static char *number(char *p, uint64_t n) {
    char b[16]; unsigned i = 0;
    do { b[i++] = "0123456789abcdef"[n & 15]; n >>= 4; } while (n);
    while (i) *p++ = b[--i];
    return p;
}
static void field(int fd, const char *key, uint64_t value) {
    char b[128], *p = text(b, "[CRASH42] ");
    p = text(p, key); p = text(p, "=0x"); p = number(p, value); *p++ = '\n';
    (void)put(fd, b, (size_t)(p-b));
}
static int event_file(const char *suffix, unsigned seq) {
    char name[128], *p = text(name, "event-");
    p = number(p, (uint64_t)getpid()); *p++ = '-';
    p = number(p, (uint64_t)syscall(SYS_gettid)); *p++ = '-';
    p = number(p, seq); *p++ = '.'; p = text(p, suffix); *p = 0;
    return openat(root_fd, name, O_CREAT|O_EXCL|O_WRONLY|O_CLOEXEC, 0600);
}
static uint64_t hex(const char **p) {
    uint64_t n = 0;
    for (;;) {
        char c = **p; unsigned d;
        if (c >= '0' && c <= '9') d = (unsigned)(c-'0');
        else if (c >= 'a' && c <= 'f') d = (unsigned)(c-'a'+10);
        else break;
        n = (n << 4) | d; ++*p;
    }
    return n;
}
static void mapping(const char *line, uint64_t sp, uint64_t *lo, uint64_t *hi) {
    const char *p = line; uint64_t a = hex(&p);
    if (*p++ != '-') return;
    uint64_t b = hex(&p);
    if (*p++ != ' ' || *p != 'r') return;
    if (a <= sp && sp < b) { *lo = a; *hi = b; }
}
static int copy_maps(int out, uint64_t sp, uint64_t *lo, uint64_t *hi) {
    int fd = open("/proc/self/maps", O_RDONLY|O_CLOEXEC);
    if (fd < 0) return -1;
    char block[1024], line[128]; size_t used = 0, total = 0;
    int ok = 0;
    for (;;) {
        ssize_t n = read(fd, block, sizeof(block));
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) { ok = -1; break; }
        if (!n) break;
        total += (size_t)n;
        if (total > 8u*1024*1024) { errno = EFBIG; ok = -1; break; }
        if (put(out, block, (size_t)n)) { ok = -1; break; }
        for (ssize_t i = 0; i < n; ++i) {
            if (block[i] == '\n') {
                line[used] = 0; mapping(line, sp, lo, hi); used = 0;
            } else if (used < sizeof(line)-1) line[used++] = block[i];
        }
    }
    int saved = errno; close(fd); errno = saved; return ok;
}

int wl_crash_snapshot_init(const char *directory) {
    if (root_fd >= 0 || !directory) { errno = EINVAL; return -1; }
    root_fd = open(directory, O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);
    return root_fd < 0 ? -1 : 0;
}

/* #48 path A: in-process address -> owning lib name + file offset via dl_iterate_phdr.
 * Called only from the fault handler FP walk. dl_iterate_phdr takes the loader lock; the
 * target a_crash is in mallocng (not ld.so) so that lock is free. Raw returns are written
 * BEFORE this runs, so the caller chain survives even if resolution is unavailable. */
struct wl_res { uint64_t addr; int fd; int found; };
static int wl_phdr_cb(struct dl_phdr_info *info, size_t sz, void *data) {
    (void)sz;
    struct wl_res *c = data;
    for (int i = 0; i < info->dlpi_phnum; ++i) {
        const ElfW(Phdr) *ph = &info->dlpi_phdr[i];
        if (ph->p_type != PT_LOAD) continue;
        uint64_t lo = (uint64_t)info->dlpi_addr + ph->p_vaddr;
        uint64_t hi = lo + ph->p_memsz;
        if (c->addr >= lo && c->addr < hi) {
            const char *nm = (info->dlpi_name && info->dlpi_name[0]) ? info->dlpi_name : "(exe)";
            char b[288], *p = text(b, "[CRASH42] fp_frame_lib=");
            while (*nm && (size_t)(p - b) < sizeof(b) - 40u) *p++ = *nm++;
            *p++ = '\n';
            (void)put(c->fd, b, (size_t)(p - b));
            field(c->fd, "fp_frame_libbase", (uint64_t)info->dlpi_addr);
            field(c->fd, "fp_frame_off", c->addr - (uint64_t)info->dlpi_addr);
            c->found = 1;
            return 1;
        }
    }
    return 0;
}
static void wl_resolve(int fd, uint64_t addr) {
    struct wl_res c = { addr, fd, 0 };
    dl_iterate_phdr(wl_phdr_cb, &c);
    if (!c.found) field(fd, "fp_frame_unresolved", addr);
}

void wl_crash_snapshot(int sig, const siginfo_t *info, const void *raw) {
    int saved = errno;
    if (root_fd < 0 || !raw) { errno = saved; return; }
    if (__atomic_exchange_n(&busy, 1, __ATOMIC_ACQUIRE)) {
        static const char skip[] = "[CRASH42] skipped concurrent/reentrant event\n";
        (void)put(2, skip, sizeof(skip)-1); errno = saved; return;
    }
    unsigned seq = ++sequence;
    int meta = event_file("txt", seq);
    if (meta < 0) { field(2, "event_open_errno", (unsigned)errno); goto done; }
    const ucontext_t *uc = raw;
    uint64_t pc, sp, fp, lr;
#if defined(__aarch64__)
    pc = uc->uc_mcontext.pc; sp = uc->uc_mcontext.sp;
    fp = uc->uc_mcontext.regs[29]; lr = uc->uc_mcontext.regs[30];
#elif defined(__x86_64__)
    pc = (uint64_t)uc->uc_mcontext.gregs[REG_RIP];
    sp = (uint64_t)uc->uc_mcontext.gregs[REG_RSP];
    fp = (uint64_t)uc->uc_mcontext.gregs[REG_RBP]; lr = 0;
#else
#error Unsupported context architecture
#endif
    struct timespec ts = {0}; (void)clock_gettime(CLOCK_MONOTONIC, &ts);
    field(meta, "format", 1); field(meta, "pid", (uint64_t)getpid());
    field(meta, "tid", (uint64_t)syscall(SYS_gettid)); field(meta, "sequence", seq);
    field(meta, "signal", (unsigned)sig);
    if (info) {
        field(meta, "si_code", (uint64_t)(int64_t)info->si_code);
        field(meta, "si_addr_or_union", (uintptr_t)info->si_addr);
    }
    field(meta, "monotonic_ns", (uint64_t)ts.tv_sec*1000000000+(uint64_t)ts.tv_nsec);
    field(meta, "pc", pc); field(meta, "sp", sp); field(meta, "fp", fp); field(meta, "lr", lr);
    field(2, "event_sequence", seq); field(2, "tid", (uint64_t)syscall(SYS_gettid));
    field(2, "signal", (unsigned)sig); field(2, "pc", pc);
    int ctx = event_file("ucontext", seq);
    if (ctx >= 0) { if (put(ctx, uc, sizeof(*uc))) field(meta, "context_write_errno", (unsigned)errno); close(ctx); }
    else field(meta, "context_open_errno", (unsigned)errno);
    if (info) {
        int si = event_file("siginfo", seq);
        if (si >= 0) { if (put(si, info, sizeof(*info))) field(meta, "siginfo_write_errno", (unsigned)errno); close(si); }
        else field(meta, "siginfo_open_errno", (unsigned)errno);
    }
    char comm[64]; int cf = open("/proc/thread-self/comm", O_RDONLY|O_CLOEXEC);
    if (cf >= 0) {
        ssize_t n = read(cf, comm, sizeof(comm));
        if (n > 0) { (void)put(meta, "thread=", 7); (void)put(meta, comm, (size_t)n); }
        close(cf);
    }
    uint64_t lo = 0, hi = 0;
    int maps = event_file("maps", seq);
    if (maps >= 0) {
        if (copy_maps(maps, sp, &lo, &hi)) field(meta, "maps_errno", (unsigned)errno);
        close(maps);
    } else field(meta, "maps_open_errno", (unsigned)errno);
    field(meta, "stack_vma_lo", lo); field(meta, "stack_vma_hi", hi);
    int mem = open("/proc/self/mem", O_RDONLY|O_CLOEXEC);
    if (mem < 0) field(meta, "mem_open_errno", (unsigned)errno);
    else if (hi > sp) {
        int stack = event_file("stack", seq);
        if (stack >= 0) {
            uint64_t pos = sp, end = hi-sp > stack_limit ? sp+stack_limit : hi;
            char buf[1024];
            while (pos < end) {
                size_t want = end-pos < sizeof(buf) ? (size_t)(end-pos) : sizeof(buf);
                ssize_t n = pread(mem, buf, want, (off_t)pos);
                if (n < 0 && errno == EINTR) continue;
                if (n <= 0) { field(meta, "stack_read_errno", n < 0 ? (unsigned)errno : 0); break; }
                if (put(stack, buf, (size_t)n)) { field(meta, "stack_write_errno", (unsigned)errno); break; }
                pos += (uint64_t)n;
            }
            field(meta, "stack_base", sp); field(meta, "stack_bytes", pos-sp);
            field(meta, "stack_complete_to_vma_end", pos == hi); close(stack);
        } else field(meta, "stack_open_errno", (unsigned)errno);
        /* (FP walk moved below: now mem-independent -- #48 path A) */
    }
    if (mem >= 0) close(mem);
    /* #48 path A: mem-independent FP chain. The pread(/proc/self/mem) walk above is skipped
     * when mem<0 (EACCES on the board). Use the [lo,hi] stack VMA (from /proc/self/maps,
     * readable) + a guarded direct dereference so the free()/realloc caller chain is captured
     * even when /proc/self/mem is inaccessible. Bounds+align+monotonic guard: a bad fp stops
     * the walk instead of faulting. Raw returns first, then in-process symbolization. */
    if (hi > lo && fp != 0) {
        field(meta, "fp_frame_pc", pc);
        uint64_t returns[32];
        unsigned nret = 0;
        uint64_t f = fp;
        while (nret < 32u && f >= sp && f >= lo && (hi - f) >= 16u && f < hi && !(f & 7u)) {
            uint64_t next = ((const volatile uint64_t *)(uintptr_t)f)[0];
            uint64_t ret  = ((const volatile uint64_t *)(uintptr_t)f)[1];
            returns[nret++] = ret;
            field(meta, "fp_frame_return", ret); field(2, "fp_frame_return", ret);
            if (next <= f) break;
            f = next;
        }
        field(meta, "fp_steps", nret); field(meta, "fp_next", f);
        wl_resolve(meta, pc);
        for (unsigned k = 0; k < nret; ++k) wl_resolve(meta, returns[k]);
    }
    field(meta, "capture_end", 1); close(meta);
done:
    __atomic_store_n(&busy, 0, __ATOMIC_RELEASE); errno = saved;
}
