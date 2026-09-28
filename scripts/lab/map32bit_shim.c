/*
 * LD_PRELOAD shim: honour MAP_32BIT under Rosetta, which ignores the flag.
 *
 * ART on x86-64 keeps 32-bit compressed heap references and gets low memory by passing MAP_32BIT
 * to mmap (arm64 uses ART's own low-4G allocator instead). Rosetta returns a high address, the
 * reference is truncated, and the host dex2oat faults in Runtime::Create. This shim turns each
 * MAP_32BIT request into a first-fit search of explicit low addresses with MAP_FIXED_NOREPLACE,
 * which Rosetta does honour. Only the host tool's own address-space layout changes; nothing
 * about its inputs or outputs does. Build: gcc -O2 -shared -fPIC -o libmap32bit.so map32bit_shim.c -ldl -pthread
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <sys/mman.h>
#include <sys/types.h>

#ifndef MAP_FIXED_NOREPLACE
#define MAP_FIXED_NOREPLACE 0x100000
#endif

#define LOW_START 0x10000000ul    /* leave the first 256 MiB alone */
#define LOW_END 0x100000000ul     /* compressed references only need the low 4 GiB */
#define STEP 0x10000ul

static void *(*real_mmap)(void *, size_t, int, int, int, off_t);
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static uintptr_t cursor = LOW_START;

static void *try_at(uintptr_t at, size_t len, int prot, int flags, int fd, off_t off) {
    void *p = real_mmap((void *)at, len, prot, (flags & ~MAP_32BIT) | MAP_FIXED_NOREPLACE, fd, off);
    /* Kernels without MAP_FIXED_NOREPLACE treat it as a hint: reject a placement elsewhere. */
    if (p != MAP_FAILED && (uintptr_t)p != at) {
        munmap(p, len);
        errno = EEXIST;
        return MAP_FAILED;
    }
    return p;
}

static void *low_mmap(void *addr, size_t len, int prot, int flags, int fd, off_t off) {
    size_t size = (len + STEP - 1) & ~(STEP - 1);
    void *p = MAP_FAILED;
    pthread_mutex_lock(&lock);
    if (addr && (uintptr_t)addr + size <= LOW_END)
        p = try_at((uintptr_t)addr, len, prot, flags, fd, off);
    for (int pass = 0; p == MAP_FAILED && pass < 2; pass++) {
        uintptr_t from = pass == 0 ? cursor : LOW_START, to = pass == 0 ? LOW_END : cursor;
        for (uintptr_t at = from; at + size <= to; at += STEP) {
            p = try_at(at, len, prot, flags, fd, off);
            if (p != MAP_FAILED) { cursor = at + size; break; }
            if (errno != EEXIST && errno != ENOMEM) break;
        }
    }
    pthread_mutex_unlock(&lock);
    if (p == MAP_FAILED) errno = ENOMEM;
    return p;
}

void *mmap(void *addr, size_t len, int prot, int flags, int fd, off_t off) {
    if (!real_mmap) real_mmap = dlsym(RTLD_NEXT, "mmap");
    if ((flags & MAP_32BIT) && !(flags & (MAP_FIXED | MAP_FIXED_NOREPLACE)))
        return low_mmap(addr, len, prot, flags, fd, off);
    return real_mmap(addr, len, prot, flags, fd, off);
}

void *mmap64(void *addr, size_t len, int prot, int flags, int fd, off_t off) {
    return mmap(addr, len, prot, flags, fd, off);
}
