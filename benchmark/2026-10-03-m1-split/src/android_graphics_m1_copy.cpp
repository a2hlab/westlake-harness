// android_graphics_m1_copy.cpp
// ----------------------------------------------------------------------------
// M1 cross-copy window/Surface rescue, split out of android_graphics_compat_shim.cpp
// per benchmark/2026-10-03-m1-freeze-dossier/evidence/split-plan.md (preferred option).
// Original source: benchmark/2026-10-02-m1-session-slots/runtime/src (carried in the
// deployed U13 runtime 18763dd4, object android_graphics_compat_shim.o = 612236be).
//
// This TU holds ONLY the M1 helpers (m1_*) and the entry m1_native_window_from_other_copies.
// The compat shim keeps g_oh_wm_get_native_window_fn FILE-STATIC and passes the resolved
// bridge fn in as a parameter, so this file references NO shim global. That keeps the shim
// object equal to the baseline plus exactly one fallback call, and confines the only body
// difference vs 612236be to this entry reading its `resolvedFn` parameter instead of the
// file-static global (the four m1_* helpers below are byte-for-byte the same source).
// ----------------------------------------------------------------------------
#include <cstring>   // std::strrchr / std::strcmp / std::memcmp (as in the un-split shim)
#include <cstdint>   // uintptr_t / int32_t / size_t
#include <link.h>    // dl_iterate_phdr / dl_phdr_info / ElfW / PT_LOAD / PF_X

// Same HiLog hook + ALOGI macro the compat shim uses, so the [M1-COPY] log line is
// byte-identical (same domain 0xD000F00u, same "OH_GfxShim" tag).
extern "C" int HiLogPrint(int type, int level, unsigned int domain,
                          const char* tag, const char* fmt, ...)
    __attribute__((__format__(printf, 5, 6)));
#define ALOGI(...) HiLogPrint(3, 4, 0xD000F00u, "OH_GfxShim", __VA_ARGS__)

typedef void* (*oh_wm_get_native_window_fn_t)(int32_t);

namespace android {
namespace {
constexpr size_t kM1MaxCopies = 4;
constexpr size_t kM1CodeCheck = 32;

struct M1CopyScan {
    uintptr_t fnAddr = 0;       // resolved instance's oh_wm_get_native_window
    uintptr_t ownBase = 0;
    uintptr_t offset = 0;
    uintptr_t bases[kM1MaxCopies] = {};
    size_t count = 0;
};

bool m1_exec_range_contains(const dl_phdr_info* info, uintptr_t addr, size_t len) {
    for (int i = 0; i < info->dlpi_phnum; ++i) {
        const ElfW(Phdr)& ph = info->dlpi_phdr[i];
        if (ph.p_type != PT_LOAD || !(ph.p_flags & PF_X)) continue;
        uintptr_t lo = static_cast<uintptr_t>(info->dlpi_addr) + ph.p_vaddr;
        if (addr >= lo && addr + len <= lo + ph.p_memsz) return true;
    }
    return false;
}

bool m1_is_bridge(const char* name) {
    if (name == nullptr) return false;
    const char* slash = std::strrchr(name, '/');
    return std::strcmp(slash ? slash + 1 : name, "liboh_adapter_bridge.so") == 0;
}

// Pass 1: find the resolved instance (the one whose executable segment holds fnAddr).
int m1_find_own(struct dl_phdr_info* info, size_t, void* data) {
    auto* s = static_cast<M1CopyScan*>(data);
    if (!m1_is_bridge(info->dlpi_name) || !m1_exec_range_contains(info, s->fnAddr, kM1CodeCheck)) return 0;
    s->ownBase = static_cast<uintptr_t>(info->dlpi_addr);
    s->offset = s->fnAddr - s->ownBase;
    return 1;
}

// Pass 2: collect the other instances whose code at the same offset is byte-identical
// (same file). Nothing is called from inside dl_iterate_phdr (loader lock held).
int m1_collect_others(struct dl_phdr_info* info, size_t, void* data) {
    auto* s = static_cast<M1CopyScan*>(data);
    uintptr_t base = static_cast<uintptr_t>(info->dlpi_addr);
    if (!m1_is_bridge(info->dlpi_name) || base == s->ownBase || s->count >= kM1MaxCopies) return 0;
    uintptr_t addr = base + s->offset;
    if (!m1_exec_range_contains(info, addr, kM1CodeCheck)) return 0;
    if (std::memcmp(reinterpret_cast<const void*>(addr), reinterpret_cast<const void*>(s->fnAddr),
                    kM1CodeCheck) != 0) return 0;
    s->bases[s->count++] = base;
    return 0;
}
}  // namespace

// External linkage (was anon-namespace in the un-split shim) so the compat shim can call it.
// The ONLY body change vs 612236be: the resolved bridge fn is the `resolvedFn` parameter
// instead of the file-static g_oh_wm_get_native_window_fn. Everything after is identical.
void* m1_native_window_from_other_copies(oh_wm_get_native_window_fn_t resolvedFn, int32_t sessionId) {
    if (!resolvedFn) return nullptr;
    M1CopyScan scan;
    scan.fnAddr = reinterpret_cast<uintptr_t>(resolvedFn);
    dl_iterate_phdr(m1_find_own, &scan);
    if (scan.ownBase == 0) return nullptr;
    dl_iterate_phdr(m1_collect_others, &scan);
    for (size_t i = 0; i < scan.count; ++i) {
        auto fn = reinterpret_cast<oh_wm_get_native_window_fn_t>(scan.bases[i] + scan.offset);
        if (void* nw = fn(sessionId)) {
            ALOGI("[M1-COPY] sessionId=%d resolved by bridge copy base=%p (resolved copy base=%p returned null)",
                  sessionId, reinterpret_cast<void*>(scan.bases[i]), reinterpret_cast<void*>(scan.ownBase));
            return nw;
        }
    }
    return nullptr;
}
}  // namespace android
