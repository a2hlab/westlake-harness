/* DRAFT — ANativeWindow_lock / ANativeWindow_unlockAndPost for libandroid.
 *
 * NEW libandroid C++ TU: framework/hwui-shim/jni/anativewindow_lock.cpp
 *   add to native/hwui-shim-sources.json + native/hwui15-platform-sources.json.
 *
 * WHY libandroid and not the shim: oh_anativewindow_shim.cpp (AdapterAnw + oh_anw_wrap) ships in the
 * 846 liboh_adapter_bridge.so, which is #96 = not reproducible from source, so we must NOT add exports
 * there. libandroid's oh_native_window_shim.c already imports oh_anw_get_oh(w) from the bridge; we reuse
 * it, call the OH NDK OH_NativeWindow_* by dlsym (no new DT_NEEDED), and keep our own lock-state map.
 * The 846 bridge stays byte-identical.
 *
 * Refinements (outer ring 2026-10-01): (1) BufferHandle layout from the bms frozen sysroot buffer_handle.h
 * (confirm virAddr offset; disassemble the on-board lib if unsure). (2) .cpp (this file). (3) no copy-forward:
 * on return set inOutDirtyBounds to the whole buffer; the NDK ANativeWindow_lock contract allows the impl to
 * expand the dirty region (android/native_window.h), and FlushBuffer with an empty region = full surface.
 */
#include <cstdint>
#include <cstddef>
#include <mutex>
#include <unordered_map>
#include <dlfcn.h>
#include <sys/mman.h>
#include <poll.h>
#include <unistd.h>
#include <errno.h>
#include "android/native_window.h"                    // ANativeWindow, ANativeWindow_Buffer, ARect
#include "../../surface/jni/pixel_format_mapper.h"     // oh_pixel_format_to_android

extern "C" {
struct OHNativeWindow;
struct OHNativeWindowBuffer;
/* (1) EXACT layout from the bms frozen sysroot buffer_handle.h:48-61 (oh_mirror .../graphic_surface/
 *     interfaces/inner_api/buffer_handle/buffer_handle.h). NOTE usage is uint64_t (NOT int) -> virAddr @ +0x20.
 *     Offsets (LP64): fd@0x0 width@0x4 stride@0x8 height@0xc size@0x10 format@0x14 usage@0x18 virAddr@0x20
 *     phyAddr@0x28 reserveFds@0x30 reserveInts@0x34 reserve@0x38. */
struct BufferHandle { int32_t fd; int32_t width; int32_t stride; int32_t height; int32_t size;
                      int32_t format; uint64_t usage; void* virAddr; uint64_t phyAddr;
                      uint32_t reserveFds; uint32_t reserveInts; int32_t reserve[0]; };
struct OHRegionRect { int32_t x; int32_t y; uint32_t w; uint32_t h; };
struct OHRegion     { OHRegionRect* rects; int32_t rectNumber; };
OHNativeWindow* oh_anw_get_oh(ANativeWindow* w);        // bridge export, already imported by libandroid
int HiLogPrint(int, int, unsigned, const char*, const char*, ...);
}  // extern "C"
#define ALOGW(...) HiLogPrint(3, 5, 0xD000F00u, "OH_AnwLock", __VA_ARGS__)

namespace {
/* OH NDK resolved by name — resident in the app process (the bridge pulls them in), so no new DT_NEEDED
 * edge (keeps the N2 native gate green; same dlsym trick the shim uses for SetScalingModeV2). */
using RequestFn = int32_t (*)(OHNativeWindow*, OHNativeWindowBuffer**, int*);
using FlushFn   = int32_t (*)(OHNativeWindow*, OHNativeWindowBuffer*, int, OHRegion);
using AbortFn   = int32_t (*)(OHNativeWindow*, OHNativeWindowBuffer*);
using HandleFn  = int32_t (*)(OHNativeWindow*, int, ...);
using GetHFn    = BufferHandle* (*)(OHNativeWindowBuffer*);
template <class F> F sym(const char* n) { static F f = reinterpret_cast<F>(dlsym(RTLD_DEFAULT, n)); return f; }

struct Locked { OHNativeWindowBuffer* ohBuf; void* mmapAddr; size_t mmapSize; };
std::mutex g_lock;
std::unordered_map<OHNativeWindow*, Locked> g_locked;   // one CPU-locked buffer per OH window

int android_bytes_per_pixel(int f) {
    switch (f) { case 1: case 2: case 5: case 0x2b: return 4;  // RGBA/RGBX/BGRA_8888, RGBA_1010102
                 case 3: return 3;                             // RGB_888
                 case 4: return 2;                             // RGB_565
                 case 0x16: return 8;                          // RGBA_FP16
                 default: return 4; }
}
}  // namespace

extern "C" int32_t ANativeWindow_lock(ANativeWindow* w, ANativeWindow_Buffer* outBuffer, ARect* inOutDirtyBounds) {
    if (!w || !outBuffer) return -EINVAL;
    OHNativeWindow* oh = oh_anw_get_oh(w);
    if (!oh) return -EINVAL;
    auto req = sym<RequestFn>("OH_NativeWindow_NativeWindowRequestBuffer");
    auto geth = sym<GetHFn>("OH_NativeWindow_GetBufferHandleFromNative");
    auto abort_ = sym<AbortFn>("OH_NativeWindow_NativeWindowAbortBuffer");
    auto handle = sym<HandleFn>("OH_NativeWindow_NativeWindowHandleOpt");
    if (!req || !geth) { ALOGW("lock: OH NDK symbols missing"); return -ENOSYS; }
    { std::lock_guard<std::mutex> g(g_lock); if (g_locked.count(oh)) { ALOGW("lock: already locked"); return -EINVAL; } }
    if (handle) handle(oh, /*OH_OP_SET_USAGE*/ 5, (uint64_t)((1u << 0) | (1u << 1)));  // CPU_READ|CPU_WRITE (confirm OH bit values)
    OHNativeWindowBuffer* ohBuf = nullptr; int fence = -1;
    int32_t rc = req(oh, &ohBuf, &fence);
    if (rc != 0 || !ohBuf) { ALOGW("lock: RequestBuffer rc=%d", rc); return -EIO; }
    if (fence >= 0) { struct pollfd p{fence, POLLIN, 0}; poll(&p, 1, 1000); close(fence); }  // wait producer/GPU
    BufferHandle* h = geth(ohBuf);
    if (!h) { if (abort_) abort_(oh, ohBuf); return -EIO; }
    void* bits = h->virAddr; void* mapAddr = nullptr; size_t mapSize = 0;
    if (!bits && h->fd >= 0 && h->size > 0) {
        bits = mmap(nullptr, (size_t)h->size, PROT_READ | PROT_WRITE, MAP_SHARED, h->fd, 0);
        if (bits == MAP_FAILED) { if (abort_) abort_(oh, ohBuf); return -EIO; }
        mapAddr = bits; mapSize = (size_t)h->size;
    }
    int fmt = oh_pixel_format_to_android(h->format);
    int bpp = android_bytes_per_pixel(fmt);
    outBuffer->width  = h->width;
    outBuffer->height = h->height;
    outBuffer->format = fmt;
    outBuffer->stride = (bpp > 0) ? (h->stride / bpp) : h->width;   // OH byte-stride -> AOSP pixel-stride
    outBuffer->bits   = bits;
    if (inOutDirtyBounds) {  // (3) no copy-forward: report the whole buffer as dirty
        inOutDirtyBounds->left = 0; inOutDirtyBounds->top = 0;
        inOutDirtyBounds->right = h->width; inOutDirtyBounds->bottom = h->height;
    }
    { std::lock_guard<std::mutex> g(g_lock); g_locked[oh] = Locked{ohBuf, mapAddr, mapSize}; }
    return 0;
}

extern "C" int32_t ANativeWindow_unlockAndPost(ANativeWindow* w) {
    if (!w) return -EINVAL;
    OHNativeWindow* oh = oh_anw_get_oh(w);
    if (!oh) return -EINVAL;
    Locked lk{};
    { std::lock_guard<std::mutex> g(g_lock);
      auto it = g_locked.find(oh);
      if (it == g_locked.end()) { ALOGW("unlockAndPost: not locked"); return -EINVAL; }
      lk = it->second; g_locked.erase(it); }
    if (lk.mmapAddr) munmap(lk.mmapAddr, lk.mmapSize);
    auto flush = sym<FlushFn>("OH_NativeWindow_NativeWindowFlushBuffer");
    if (!flush) return -ENOSYS;
    OHRegion region{nullptr, 0};   // empty region = full surface (matches whole-buffer dirty)
    int32_t rc = flush(oh, lk.ohBuf, -1, region);
    if (rc != 0) { ALOGW("unlockAndPost: FlushBuffer rc=%d", rc); return -EIO; }
    return 0;
}
