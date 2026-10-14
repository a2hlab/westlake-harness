/*
 * surface_oh_helper.cpp — P13.2.b helper
 *
 * Provides createInProcessProducer() — builds an OH producer Surface backed by
 * an in-process consumer. The dmabuf round-trip works (RequestBuffer/FlushBuffer
 * succeed, virAddr is mmapped), but the queued buffers go to an in-process
 * consumer that we ignore — pixels are not visible on screen.
 *
 * This bypasses oh_surface_bridge.cpp (which would create an RSSurfaceNode that
 * eventually displays via RenderService) because that file pulls in the entire
 * RS client header chain which has broken Skia includes (skcms.h at wrong path).
 *
 * Wiring to actual display = P13.2.c (requires WindowManagerService → SceneSession
 * → RSSurfaceNode integration that's beyond P13.2.b scope).
 */
#include "iconsumer_surface.h"
#include "surface.h"
#include "ibuffer_producer.h"
#include "surface_buffer.h"
#include "ibuffer_consumer_listener.h"   // [UNITY-OFFSCREEN] drain listener base
#include <android/log.h>
#include "hilog/log.h"                   // [S23 cut6.1] HiLogPrint %{public} for geometry verify
#include <atomic>                        // [UNITY-OFFSCREEN]
#include <cstdint>                       // [UNITY-OFFSCREEN]
#include <cstring>                       // [S23 cut6] memcpy for present copy

#define LOG_TAG "OH_SurfaceHelper"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

// [UNITY-OFFSCREEN] ----------------------------------------------------------
// The in-process producer below is a pure BufferQueue with NO consumer wired to
// a real display/compositor.  A producer-side dequeue blocks once the queue is
// full, so after SetQueueSize(3) buffers Unity's render thread would wedge on
// the 4th eglSwapBuffers (3 frames in flight, none ever released).
//
// Fix: register an OnBufferAvailable consumer listener that immediately
// Acquire+Release-drains every produced buffer, keeping a free slot perpetually
// available.  The listener also mmaps the freshest buffer (GetVirAddr) and
// caches its centre pixel — a zero-cost read hook that proves Unity's GPU
// output is actually landing in the dmabuf and gives downstream code a place to
// pull pixels from (surface_oh_offscreen_last_center_pixel()).
namespace {
std::atomic<uint32_t> g_unityLastCenterPixel{0};
std::atomic<uint64_t> g_unityDrainCount{0};

class OffscreenDrainListener : public OHOS::IBufferConsumerListener {
public:
    explicit OffscreenDrainListener(OHOS::IConsumerSurface* consumer)
        : consumer_(consumer) {}

    void OnBufferAvailable() override {
        if (consumer_ == nullptr) return;
        OHOS::sptr<OHOS::SurfaceBuffer> buffer;
        int32_t fence = -1;
        int64_t timestamp = 0;
        OHOS::Rect damage = {};
        // Acquire the just-queued buffer so the producer regains a free slot.
        auto ret = consumer_->AcquireBuffer(buffer, fence, timestamp, damage);
        if (ret != OHOS::GSERROR_OK || buffer == nullptr) return;

        // Optional read hook: mmap + sample the centre pixel (RGBA8888).
        void* vaddr = buffer->GetVirAddr();
        if (vaddr == nullptr) { (void)buffer->Map(); vaddr = buffer->GetVirAddr(); }
        if (vaddr != nullptr) {
            int32_t w = buffer->GetWidth();
            int32_t h = buffer->GetHeight();
            int32_t stride = buffer->GetStride();
            if (w > 0 && h > 0 && stride >= w * 4) {
                uint8_t* base = static_cast<uint8_t*>(vaddr);
                uint8_t* px = base + (h / 2) * stride + (w / 2) * 4;
                g_unityLastCenterPixel.store(*reinterpret_cast<uint32_t*>(px),
                                             std::memory_order_relaxed);
            }
        }
        // Release back to the BufferQueue (fence -1 = no GPU wait needed).
        consumer_->ReleaseBuffer(buffer, -1);
        g_unityDrainCount.fetch_add(1, std::memory_order_relaxed);
    }

private:
    OHOS::IConsumerSurface* consumer_;  // pinned (IncStrongRef) for queue lifetime
};

// [S23 cut6 2026-07-09] Present-drain listener: the adapter plays the
// SurfaceFlinger consumer role. Unity produces into an in-process BufferQueue
// whose CONSUMER default geometry WE set (1200x1920) -> alloc succeeds (client
// side proved zero-authority over RS self-draw nodes; owning the consumer is the
// only lever). On each Unity frame we Acquire it, then PRESENT to the on-screen
// RS node (AdapterSurfaceView) producer using an EXPLICIT-geometry RequestBuffer
// (adapter controls dims directly, bypassing the RS node's own 0x0 alloc default),
// copy pixels, and FlushBuffer -> RS composites -> pixels on screen.
std::atomic<uint64_t> g_presentOk{0};
std::atomic<uint64_t> g_presentFail{0};
std::atomic<uint64_t> g_presentRelease{0};
std::atomic<int32_t>  g_presentLastRc{0};

class PresentDrainListener : public OHOS::IBufferConsumerListener {
public:
    PresentDrainListener(OHOS::IConsumerSurface* consumer, OHOS::Surface* present,
                         int32_t w, int32_t h)
        : consumer_(consumer), present_(present), w_(w), h_(h) {}

    // Unity produced a frame into the in-process queue. ZERO-COPY present: attach
    // the SAME dma-buf to the on-screen RS node queue and flush -> RS composites
    // the identical physical buffer (dma-buf fd shared cross-process). NO memcpy.
    void OnBufferAvailable() override {
        if (consumer_ == nullptr || present_ == nullptr) return;
        OHOS::sptr<OHOS::SurfaceBuffer> ub;
        int32_t ufence = -1; int64_t ts = 0; OHOS::Rect damage = {};
        if (consumer_->AcquireBuffer(ub, ufence, ts, damage) != OHOS::GSERROR_OK || ub == nullptr)
            return;
        auto aret = present_->AttachBufferToQueue(ub);
        if (aret != OHOS::GSERROR_OK) {
            g_presentLastRc.store((int32_t)aret, std::memory_order_relaxed);
            g_presentFail.fetch_add(1, std::memory_order_relaxed);
            consumer_->ReleaseBuffer(ub, -1);   // drop this frame back to Unity
            return;
        }
        OHOS::BufferFlushConfig fc = {};
        fc.damage.x = 0; fc.damage.y = 0; fc.damage.w = w_; fc.damage.h = h_;
        fc.timestamp = ts;
        auto fret = present_->FlushBuffer(ub, ufence, fc);
        g_presentLastRc.store((int32_t)fret, std::memory_order_relaxed);
        if (fret == OHOS::GSERROR_OK) {
            g_presentOk.fetch_add(1, std::memory_order_relaxed);
            // buffer now owned by RS queue; reclaimed in OnPresentRelease.
        } else {
            g_presentFail.fetch_add(1, std::memory_order_relaxed);
            present_->DetachBufferFromQueue(ub);
            consumer_->ReleaseBuffer(ub, -1);
        }
    }

    // Called via present_->RegisterReleaseListener when RS finishes compositing a
    // buffer: detach it from the RS queue and release back to the in-process
    // (Unity) queue so Unity regains the slot. Keeps the zero-copy loop cycling.
    OHOS::GSError OnPresentRelease(OHOS::sptr<OHOS::SurfaceBuffer>& rb) {
        if (rb == nullptr) return OHOS::GSERROR_OK;
        if (present_)  present_->DetachBufferFromQueue(rb);
        if (consumer_) consumer_->ReleaseBuffer(rb, -1);
        g_presentRelease.fetch_add(1, std::memory_order_relaxed);
        return OHOS::GSERROR_OK;
    }

private:
    OHOS::IConsumerSurface* consumer_;
    OHOS::Surface* present_;
    int32_t w_, h_;
};
}  // namespace
// --------------------------------------------------------------------------

extern "C" {

// Returns an OHOS::Surface* (raw pointer wrapped via OHOS::sptr internally).
// Caller stores the sptr via the helpers below to keep ref count alive.
// Returns nullptr on failure.
void* surface_oh_create_in_process_producer(const char* name) {
    auto consumer = OHOS::IConsumerSurface::Create(name ? name : "OHAdapterSurface");
    if (!consumer) {
        LOGE("create_in_process_producer: IConsumerSurface::Create failed");
        return nullptr;
    }

    // Hold the consumer alive in a static map keyed by the producer pointer,
    // because once the consumer is dropped the producer becomes useless.
    // We leak the consumer ref intentionally — Surface lifetime is tied to
    // the JNI Surface object lifetime which we don't always have visibility into.
    OHOS::sptr<OHOS::IBufferProducer> producerIface = consumer->GetProducer();
    if (!producerIface) {
        LOGE("create_in_process_producer: GetProducer failed");
        return nullptr;
    }

    OHOS::sptr<OHOS::Surface> producer = OHOS::Surface::CreateSurfaceAsProducer(producerIface);
    if (!producer) {
        LOGE("create_in_process_producer: CreateSurfaceAsProducer failed");
        return nullptr;
    }

    // Set queue size for triple buffering
    producer->SetQueueSize(3);

    // [UNITY-OFFSCREEN] Register the auto-drain consumer listener BEFORE the
    // first frame is produced.  Without it the 3-slot queue saturates and the
    // producer's RequestBuffer/dequeue blocks after 3 frames, deadlocking the
    // Unity render thread.  The listener is pinned (leaked) for the lifetime of
    // the queue, matching the intentional consumer/producer leak below.
    OHOS::sptr<OHOS::IBufferConsumerListener> listener =
        new OffscreenDrainListener(consumer.GetRefPtr());
    auto lret = consumer->RegisterConsumerListener(listener);
    if (lret != OHOS::GSERROR_OK) {
        LOGE("create_in_process_producer: RegisterConsumerListener failed (%d)",
             static_cast<int>(lret));
    } else {
        listener->IncStrongRef(nullptr);  // pin drain listener
        LOGI("create_in_process_producer: drain listener registered (qsize=3)");
    }

    // Pin both refs by leaking sptr's increment.
    // We add a ref then return the raw pointer; caller manages release via _release.
    OHOS::Surface* raw = producer.GetRefPtr();
    raw->IncStrongRef(nullptr);
    consumer->IncStrongRef(nullptr);  // pin consumer

    LOGI("create_in_process_producer: ok, name=%s", name);
    return raw;
}

// [S23 cut6] Create the Unity-facing surface: an in-process BufferQueue whose
// CONSUMER default geometry WE set (w x h) so Unity's dequeue allocs real buffers
// (not Buffer[0 0]); the auto-drain PRESENT listener acquires each Unity frame and
// blits it to `presentTargetRaw` (the on-screen RS node producer) with explicit
// geometry. Returns the producer OHOS::Surface* to hand to Unity.
// presentTargetRaw = OHOS::Surface* of the on-screen RS node (child->GetSurface()).
void* surface_oh_create_unity_present_surface(void* presentTargetRaw,
                                              int32_t w, int32_t h) {
    if (w <= 0) w = 1200;
    if (h <= 0) h = 1920;
    auto consumer = OHOS::IConsumerSurface::Create("AdapterUnityInProcess");
    if (!consumer) {
        LOGE("create_unity_present_surface: IConsumerSurface::Create failed");
        return nullptr;
    }
    // *** THE KEY LEVER ***: consumer-side default geometry (white-box proven the
    // only authority over BufferQueue alloc; client producer side has zero).
    auto gret = consumer->SetDefaultWidthAndHeight(w, h);
    HiLogPrint(LOG_CORE, LOG_INFO, 0xD000F00u, "OH_SurfaceHelperP",
               "create_unity_present_surface: consumer SetDefaultWidthAndHeight %{public}dx%{public}d ret=%{public}d",
               w, h, static_cast<int>(gret));

    OHOS::sptr<OHOS::IBufferProducer> producerIface = consumer->GetProducer();
    if (!producerIface) { LOGE("create_unity_present_surface: GetProducer failed"); return nullptr; }
    OHOS::sptr<OHOS::Surface> producer = OHOS::Surface::CreateSurfaceAsProducer(producerIface);
    if (!producer) { LOGE("create_unity_present_surface: CreateSurfaceAsProducer failed"); return nullptr; }
    producer->SetQueueSize(3);
    // [S23 cut6.1] *** THE MISSING LEVER ***: native_window.cpp:104/217 build the
    // RequestBuffer config from the PRODUCER surface's GetDefaultWidth()/GetWindowConfig
    // — NOT the consumer default (that only seeds PreAlloc). For an in-process queue we
    // own both ends, so producer->SetDefaultWidthAndHeight sets the shared BufferQueue
    // default -> GetDefaultWidth()==w -> every Unity RequestBuffer allocs w x h.
    auto pgret = producer->SetDefaultWidthAndHeight(w, h);
    HiLogPrint(LOG_CORE, LOG_INFO, 0xD000F00u, "OH_SurfaceHelperP",
               "create_unity_present_surface: producer SetDefaultWidthAndHeight %{public}dx%{public}d "
               "ret=%{public}d -> GetDefaultWidth=%{public}d GetDefaultHeight=%{public}d",
               w, h, static_cast<int>(pgret),
               producer->GetDefaultWidth(), producer->GetDefaultHeight());

    OHOS::Surface* present = reinterpret_cast<OHOS::Surface*>(presentTargetRaw);
    if (present) present->IncStrongRef(nullptr);  // pin present target for queue lifetime
    auto* pl = new PresentDrainListener(consumer.GetRefPtr(), present, w, h);
    OHOS::sptr<OHOS::IBufferConsumerListener> listener = pl;
    auto lret = consumer->RegisterConsumerListener(listener);
    if (lret != OHOS::GSERROR_OK) {
        LOGE("create_unity_present_surface: RegisterConsumerListener failed (%d)",
             static_cast<int>(lret));
    } else {
        listener->IncStrongRef(nullptr);
        // Reclaim buffers after RS composites: zero-copy loop cycling.
        if (present) {
            present->RegisterReleaseListener(
                [pl](OHOS::sptr<OHOS::SurfaceBuffer>& b) -> OHOS::GSError {
                    return pl->OnPresentRelease(b);
                });
        }
        LOGI("create_unity_present_surface: present drain listener registered "
             "(qsize=3 present=%p %dx%d, zero-copy attach+flush)", present, w, h);
    }
    OHOS::Surface* raw = producer.GetRefPtr();
    raw->IncStrongRef(nullptr);
    consumer->IncStrongRef(nullptr);
    LOGI("create_unity_present_surface: ok producer=%p consumer_uid=%llu",
         raw, (unsigned long long)consumer->GetUniqueId());
    return raw;
}

// [S23 cut6] present stats for cold-verify (four-see ③④).
uint64_t surface_oh_present_ok_count(void)   { return g_presentOk.load(std::memory_order_relaxed); }
uint64_t surface_oh_present_fail_count(void) { return g_presentFail.load(std::memory_order_relaxed); }
int32_t  surface_oh_present_last_rc(void)    { return g_presentLastRc.load(std::memory_order_relaxed); }

void surface_oh_release_producer(void* producerRaw) {
    if (!producerRaw) return;
    auto* p = reinterpret_cast<OHOS::Surface*>(producerRaw);
    p->DecStrongRef(nullptr);
}

// [UNITY-OFFSCREEN] Read hook: most-recent centre pixel (RGBA8888 packed) and
// total drained frame count.  Lets callers confirm Unity is rendering into the
// offscreen dmabuf without owning the consumer.
uint32_t surface_oh_offscreen_last_center_pixel(void) {
    return g_unityLastCenterPixel.load(std::memory_order_relaxed);
}

uint64_t surface_oh_offscreen_drain_count(void) {
    return g_unityDrainCount.load(std::memory_order_relaxed);
}

}  // extern "C"
