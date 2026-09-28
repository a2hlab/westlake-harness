#pragma once
// libhwui-wide compatibility shim — force-included via -include
#include <memory>
#include <atomic>
// Undef C atomic macros that conflict with C++ shared_ptr.h
#undef atomic_is_lock_free
#undef atomic_load
#undef atomic_store
#undef atomic_exchange
#undef atomic_compare_exchange_strong
#undef atomic_compare_exchange_weak
#undef atomic_fetch_add
#undef atomic_fetch_sub
#undef atomic_fetch_or
#undef atomic_fetch_xor
#undef atomic_fetch_and
#include <inttypes.h>
#include <cstdint>
#include <cstdio>
#include <unistd.h>
#ifndef U16_GET_SUPPLEMENTARY
#define U16_GET_SUPPLEMENTARY(lead, trail) (((unsigned)(lead)<<10UL)+(unsigned)(trail)-0x35FDC00UL)
#endif

// __c11_atomic_thread_fence is a clang builtin, but utils/LightRefBase.h
// references it via std::__c11_atomic_thread_fence which doesn't exist in libcxx-ohos.
namespace std {
    inline void __c11_atomic_thread_fence(int order) { __atomic_thread_fence(order); }
}

// dprintf alias
#ifndef dprintf
extern "C" int dprintf(int fd, const char* fmt, ...);
#endif

// Skia trace util used by Properties.cpp

// SkMSec / float3 typedefs
typedef uint32_t SkMSec;
struct float3 { float x, y, z; };
struct mat3 { float m[9]; };

// LOG_ALWAYS_FATAL fallback (may be needed before liblog is included)
#ifndef LOG_ALWAYS_FATAL
#define LOG_ALWAYS_FATAL(...) do { fprintf(stderr, __VA_ARGS__); abort(); } while(0)
#endif

// bionic-style macro shims (musl/libcxx-ohos doesn't define these)
#ifndef __BEGIN_DECLS
#ifdef __cplusplus
#define __BEGIN_DECLS extern "C" {
#define __END_DECLS }
#else
#define __BEGIN_DECLS
#define __END_DECLS
#endif
#endif


// Round 12: SkCanvas::ColorBehavior was removed in Skia M133, but
// android::ImageDecoder.cpp references it. Provide a stub via macro.
// (Cannot patch SkCanvas itself — it's in OH Skia headers.)
namespace SkCanvasColorBehaviorShim {
    enum Behavior { kRespect = 0, kIgnore = 1 };
}
#ifndef SkCanvas_ColorBehavior_DEFINED
#define SkCanvas_ColorBehavior_DEFINED
// Use a non-conflicting name; AOSP code that does SkCanvas::ColorBehavior::kIgnore
// must be patched in source via round12 patch_image_decoder() below.
#endif

// 2026-04-11 P10.F: sk_float_pow was an AOSP Skia M116 internal helper,
// removed in M133. Provide as macro alias to std::pow.
#include <cmath>
#ifndef sk_float_pow
#define sk_float_pow(x, y) std::pow((x), (y))
#endif

// 2026-04-11 P10.D: NDK API compat
// Define __INTRODUCED_IN as empty so performance_hint.h parses (NDK availability annotation)
#ifndef __INTRODUCED_IN
#define __INTRODUCED_IN(api) /* P10.D: NDK availability gating disabled */
#endif

// Stub missing NDK ANativeWindow / ASurfaceTexture functions (Android-only extensions)
struct ANativeWindow;
struct ASurfaceTexture;
struct AHardwareBuffer;
extern "C" {
static inline int ANativeWindow_setDequeueTimeout(ANativeWindow*, long) { return 0; }
static inline int ANativeWindow_tryAllocateBuffers(ANativeWindow*) { return 0; }
static inline long ANativeWindow_getLastDequeueStartTime(ANativeWindow*) { return 0; }
static inline long ANativeWindow_getLastDequeueDuration(ANativeWindow*) { return 0; }
static inline long ANativeWindow_getLastQueueDuration(ANativeWindow*) { return 0; }
static inline unsigned long long ANativeWindow_getNextFrameId(ANativeWindow*) { return 0; }
static inline unsigned ASurfaceTexture_getCurrentTextureTarget(ASurfaceTexture*) { return 0; }
static inline AHardwareBuffer* ASurfaceTexture_dequeueBuffer(ASurfaceTexture*, ...) { return nullptr; }
}

// 2026-04-11 P10.B: AChoreographer NDK shim
typedef long AVsyncId;
struct AChoreographer;
extern "C" {
static inline AChoreographer* AChoreographer_create() { return nullptr; }
static inline int AChoreographer_getFd(AChoreographer*) { return -1; }
static inline void AChoreographer_handlePendingEvents(AChoreographer*, void*) {}
static inline void AChoreographer_registerRefreshRateCallback(AChoreographer*, ...) {}
}
