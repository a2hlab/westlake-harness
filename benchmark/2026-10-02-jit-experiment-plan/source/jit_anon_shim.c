/*
 * libwestlake_jit_anon.so -- experiment shim: give a route-A child's private JIT code cache ART's own anonymous
 * mapping, without changing libart.
 *
 * Why: OH refuses executable mappings of memfd files (XPM, EACCES), so AOSP 14's dual-view JIT cache
 * (art::memfd_create("jit-cache") + MAP_SHARED RX) fails and JIT is lost. The Westlake ART patch
 * (source/23-...oh-jit.patch, from aosp-art-15 jit_memory_region.cc) answers that by dropping the memfd and taking
 * ART's existing anonymous single-mapping path (MAP_PRIVATE|MAP_ANON, RX view, RWX while writing code). Board libart
 * 59e1bb45 cannot be rebuilt with that patch (its source is lost, DIGEST 502). AOSP 14 already takes the same
 * anonymous path when memfd_create fails and RWX is allowed (art-r1 jit_memory_region.cc:85-95, then :219
 * MAP_PRIVATE|MAP_ANON and :240 RX remap; RWX is allowed for every non-system-server process,
 * jit_code_cache.cc:1929), so failing that one call is equivalent to the patch's anonymous branch.
 *
 * What: interposes art::memfd_create(const char*, unsigned int) (libartbase export _ZN3art12memfd_createEPKcj, which
 * libart imports). Only the name "jit-cache" (private, non-zygote cache) is refused; every other caller, including
 * "jit-zygote-cache", goes to the real libartbase function. Loaded through the appspawn-x LD_PRELOAD list.
 * Marker: "[JIT-ANON] refused memfd jit-cache" once per process (log tag WestlakeJitAnon).
 * Build: aarch64-linux-ohos clang, -shared -fPIC -O2, link -ldl -llog (route-A liblog). Not built in this plan.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdatomic.h>
#include <string.h>

int __android_log_print(int prio, const char* tag, const char* fmt, ...);

typedef int (*memfd_fn)(const char*, unsigned int);

static atomic_int g_logged;

int wl_art_memfd_create(const char* name, unsigned int flags) __asm__("_ZN3art12memfd_createEPKcj");

int wl_art_memfd_create(const char* name, unsigned int flags) {
    if (name != NULL && strcmp(name, "jit-cache") == 0) {
        if (atomic_exchange(&g_logged, 1) == 0) {
            __android_log_print(5 /* WARN */, "WestlakeJitAnon",
                                "[JIT-ANON] refused memfd jit-cache: ART anonymous JIT cache (RWX updates)");
        }
        errno = EACCES;
        return -1;
    }
    static memfd_fn real;
    if (real == NULL) {
        real = (memfd_fn)dlsym(RTLD_NEXT, "_ZN3art12memfd_createEPKcj");
    }
    if (real == NULL) {
        errno = ENOSYS;
        return -1;
    }
    return real(name, flags);
}

__attribute__((constructor)) static void wl_jit_anon_loaded(void) {
    __android_log_print(4 /* INFO */, "WestlakeJitAnon", "[JIT-ANON] shim loaded");
}
