// ============================================================================
// android_ndk_libandroid_shim.cpp
//
// [UNITY-NDK-LIBANDROID]  Wall 3 — NDK "libandroid.so" surface for Unity.
//
// Unity's libunity.so (+ libswappywrapper.so) lists libandroid.so in its
// DT_NEEDED and binds these NDK entry points eagerly at dlopen time.  On OH,
// libandroid.so is a symlink to liboh_android_runtime.so (deploy_stage.sh
// :536), so every symbol libunity references MUST be defined here or dlopen
// fails with "FATAL: Unable to load library libunity.so".
//
// Groups in this file:
//   1. ALooper_*            — REAL, self-contained epoll-based event loop
//                            (epoll fd + eventfd wake).  Drives Unity main /
//                            render threads + Swappy.  MOST CRITICAL.
//   2. AConfiguration_*     — REAL trivial (getSdkVersion -> 34).
//   3. ASensor* / ASensorManager* / ASensorEventQueue*
//                          — STUB (no sensors; Unity tolerates).
//   4. AChoreographer_*     — FUNCTIONAL: frame callbacks driven by a timerfd
//                            registered on the calling thread's ALooper, fired
//                            from ALooper_pollOnce.  ~60Hz software cadence.
//
// AAsset* / AAssetManager* are provided by the REAL AOSP source
// frameworks/base/native/android/asset_manager.cpp (added to SRCS_AOSP in the
// build driver), backed by the AssetManager2 engine + the adapter helper
// NdkAssetManagerForJavaObject in android_util_AssetManager_aosp.cpp.
//
// Compiled in the SRCS group (gnu++17, OH ABI, -fno-rtti, libcxx_compat).
// ============================================================================

#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <sys/epoll.h>
#include <sys/eventfd.h>
#include <sys/timerfd.h>
#include <mutex>
#include <vector>
#include <unordered_map>
#include <atomic>

extern "C" int HiLogPrint(int type, int level, unsigned int domain,
                          const char* tag, const char* fmt, ...)
    __attribute__((__format__(printf, 5, 6)));
#define NDK_LOGI(...) HiLogPrint(3, 4, 0xD000F00u, "OH_NdkAndroid", __VA_ARGS__)
#define NDK_LOGW(...) HiLogPrint(3, 5, 0xD000F00u, "OH_NdkAndroid", __VA_ARGS__)

// ===========================================================================
// 1. ALooper  (REAL — epoll + eventfd)
// ===========================================================================
// NDK ABI constants (android/looper.h).
enum {
    OH_ALOOPER_PREPARE_ALLOW_NON_CALLBACKS = 1 << 0,
    OH_ALOOPER_POLL_WAKE     = -1,
    OH_ALOOPER_POLL_CALLBACK = -2,
    OH_ALOOPER_POLL_TIMEOUT  = -3,
    OH_ALOOPER_POLL_ERROR    = -4,
    OH_ALOOPER_EVENT_INPUT   = 1 << 0,
    OH_ALOOPER_EVENT_OUTPUT  = 1 << 1,
    OH_ALOOPER_EVENT_ERROR   = 1 << 2,
    OH_ALOOPER_EVENT_HANGUP  = 1 << 3,
    OH_ALOOPER_EVENT_INVALID = 1 << 4,
};

extern "C" {
typedef struct ALooper ALooper;
typedef int (*ALooper_callbackFunc)(int fd, int events, void* data);
}

namespace {

struct LooperFd {
    int                  ident;
    ALooper_callbackFunc callback;
    void*                data;
    int                  events;   // requested ALOOPER_EVENT_* mask
};

struct LooperImpl {
    int                          epfd   = -1;
    int                          wakefd = -1;   // eventfd for ALooper_wake
    std::atomic<int>             refcount{1};
    std::mutex                   mtx;
    std::unordered_map<int, LooperFd> fds;      // fd -> entry (callback / ident)
};

// One looper per thread, AOSP semantics (Looper::getForThread).
thread_local LooperImpl* t_looper = nullptr;

inline uint32_t toEpollEvents(int alooperEvents) {
    uint32_t e = 0;
    if (alooperEvents & OH_ALOOPER_EVENT_INPUT)  e |= EPOLLIN;
    if (alooperEvents & OH_ALOOPER_EVENT_OUTPUT) e |= EPOLLOUT;
    if (e == 0) e = EPOLLIN;   // default
    return e;
}

inline int toAlooperEvents(uint32_t epollEvents) {
    int e = 0;
    if (epollEvents & EPOLLIN)  e |= OH_ALOOPER_EVENT_INPUT;
    if (epollEvents & EPOLLOUT) e |= OH_ALOOPER_EVENT_OUTPUT;
    if (epollEvents & EPOLLERR) e |= OH_ALOOPER_EVENT_ERROR;
    if (epollEvents & EPOLLHUP) e |= OH_ALOOPER_EVENT_HANGUP;
    return e;
}

LooperImpl* prepareForThread() {
    if (t_looper) return t_looper;
    LooperImpl* L = new LooperImpl();
    L->epfd   = epoll_create1(EPOLL_CLOEXEC);
    L->wakefd = eventfd(0, EFD_NONBLOCK | EFD_CLOEXEC);
    if (L->epfd < 0 || L->wakefd < 0) {
        NDK_LOGW("ALooper_prepare: epoll_create1/eventfd failed errno=%{public}d", errno);
    } else {
        epoll_event ev{};
        ev.events  = EPOLLIN;
        ev.data.fd = L->wakefd;
        epoll_ctl(L->epfd, EPOLL_CTL_ADD, L->wakefd, &ev);
    }
    t_looper = L;
    return L;
}

}  // namespace

extern "C" ALooper* ALooper_forThread() {
    return reinterpret_cast<ALooper*>(t_looper);
}

extern "C" ALooper* ALooper_prepare(int /*opts*/) {
    return reinterpret_cast<ALooper*>(prepareForThread());
}

extern "C" void ALooper_acquire(ALooper* looper) {
    if (!looper) return;
    reinterpret_cast<LooperImpl*>(looper)->refcount.fetch_add(1);
}

extern "C" void ALooper_release(ALooper* looper) {
    if (!looper) return;
    // Thread-local loopers are intentionally never freed here to avoid
    // use-after-free races with the owning thread's poll loop.
    reinterpret_cast<LooperImpl*>(looper)->refcount.fetch_sub(1);
}

extern "C" void ALooper_wake(ALooper* looper) {
    if (!looper) return;
    LooperImpl* L = reinterpret_cast<LooperImpl*>(looper);
    if (L->wakefd < 0) return;
    uint64_t one = 1;
    ssize_t n;
    do { n = write(L->wakefd, &one, sizeof(one)); } while (n < 0 && errno == EINTR);
}

extern "C" int ALooper_addFd(ALooper* looper, int fd, int ident, int events,
                             ALooper_callbackFunc callback, void* data) {
    if (!looper || fd < 0) return -1;
    LooperImpl* L = reinterpret_cast<LooperImpl*>(looper);
    if (callback != nullptr) ident = OH_ALOOPER_POLL_CALLBACK;
    std::lock_guard<std::mutex> lk(L->mtx);
    bool exists = L->fds.count(fd) != 0;
    L->fds[fd] = LooperFd{ident, callback, data, events};
    epoll_event ev{};
    ev.events  = toEpollEvents(events);
    ev.data.fd = fd;
    int op = exists ? EPOLL_CTL_MOD : EPOLL_CTL_ADD;
    if (epoll_ctl(L->epfd, op, fd, &ev) < 0) {
        if (errno == EEXIST) epoll_ctl(L->epfd, EPOLL_CTL_MOD, fd, &ev);
        else { L->fds.erase(fd); return -1; }
    }
    return 1;
}

extern "C" int ALooper_removeFd(ALooper* looper, int fd) {
    if (!looper || fd < 0) return -1;
    LooperImpl* L = reinterpret_cast<LooperImpl*>(looper);
    std::lock_guard<std::mutex> lk(L->mtx);
    epoll_ctl(L->epfd, EPOLL_CTL_DEL, fd, nullptr);
    L->fds.erase(fd);
    return 1;
}

extern "C" int ALooper_pollOnce(int timeoutMillis, int* outFd,
                                int* outEvents, void** outData) {
    LooperImpl* L = t_looper;
    if (!L) L = prepareForThread();
    if (L->epfd < 0) return OH_ALOOPER_POLL_ERROR;

    for (;;) {
        epoll_event evs[16];
        int n = epoll_wait(L->epfd, evs, 16, timeoutMillis);
        if (n < 0) {
            if (errno == EINTR) continue;
            return OH_ALOOPER_POLL_ERROR;
        }
        if (n == 0) return OH_ALOOPER_POLL_TIMEOUT;

        bool invokedCallback = false;
        for (int i = 0; i < n; ++i) {
            int fd = evs[i].data.fd;
            if (fd == L->wakefd) {
                uint64_t cnt;
                while (read(L->wakefd, &cnt, sizeof(cnt)) > 0) { /* drain */ }
                if (outFd) *outFd = 0;
                if (outEvents) *outEvents = 0;
                if (outData) *outData = nullptr;
                return OH_ALOOPER_POLL_WAKE;
            }
            LooperFd entry;
            bool found = false;
            {
                std::lock_guard<std::mutex> lk(L->mtx);
                auto it = L->fds.find(fd);
                if (it != L->fds.end()) { entry = it->second; found = true; }
            }
            if (!found) continue;
            int aEvents = toAlooperEvents(evs[i].events);
            if (entry.callback != nullptr) {
                int keep = entry.callback(fd, aEvents, entry.data);
                if (keep == 0) ALooper_removeFd(reinterpret_cast<ALooper*>(L), fd);
                invokedCallback = true;
            } else {
                if (outFd) *outFd = fd;
                if (outEvents) *outEvents = aEvents;
                if (outData) *outData = entry.data;
                return entry.ident;
            }
        }
        if (invokedCallback) return OH_ALOOPER_POLL_CALLBACK;
        // Only wake/callback fds fired; loop again without blocking burn:
        timeoutMillis = 0;
        return OH_ALOOPER_POLL_CALLBACK;
    }
}

extern "C" int ALooper_pollAll(int timeoutMillis, int* outFd,
                               int* outEvents, void** outData) {
    for (;;) {
        int r = ALooper_pollOnce(timeoutMillis, outFd, outEvents, outData);
        if (r == OH_ALOOPER_POLL_CALLBACK) { timeoutMillis = 0; continue; }
        return r;
    }
}

// ===========================================================================
// 2. AConfiguration  (REAL trivial)
// ===========================================================================
extern "C" {
typedef struct AConfiguration AConfiguration;
}
// Unity only binds getSdkVersion from this family.  Report API 34 (Android 14),
// matching the adapter's AOSP-14 framework.jar baseline.
extern "C" int32_t AConfiguration_getSdkVersion(AConfiguration* /*config*/) {
    return 34;
}

// ===========================================================================
// 3. ASensor*  (STUB — no sensors; Unity tolerates a sensorless device)
// ===========================================================================
extern "C" {
typedef struct ASensorManager   ASensorManager;
typedef struct ASensorEventQueue ASensorEventQueue;
typedef struct ASensor          ASensor;
typedef ASensor const*          ASensorRef;
typedef ASensorRef const*       ASensorList;
}

// Singleton non-null manager token so callers don't read it as an error.
static ASensorManager* const kSensorManager =
    reinterpret_cast<ASensorManager*>(const_cast<char*>("OH_SENSORMGR"));

extern "C" ASensorManager* ASensorManager_getInstance() { return kSensorManager; }
extern "C" ASensorManager* ASensorManager_getInstanceForPackage(const char* /*pkg*/) {
    return kSensorManager;
}
extern "C" int ASensorManager_getSensorList(ASensorManager* /*m*/, ASensorList* list) {
    if (list) *list = nullptr;
    return 0;   // count = 0
}
extern "C" ASensor const* ASensorManager_getDefaultSensor(ASensorManager* /*m*/, int /*type*/) {
    return nullptr;
}
extern "C" ASensor const* ASensorManager_getDefaultSensorEx(ASensorManager* /*m*/, int /*type*/,
                                                            bool /*wakeUp*/) {
    return nullptr;
}
extern "C" ASensorEventQueue* ASensorManager_createEventQueue(
        ASensorManager* /*m*/, ALooper* /*looper*/, int /*ident*/,
        ALooper_callbackFunc /*cb*/, void* /*data*/) {
    // Minimal non-null opaque token; never delivers events.
    return reinterpret_cast<ASensorEventQueue*>(::malloc(sizeof(void*)));
}
extern "C" int ASensorManager_destroyEventQueue(ASensorManager* /*m*/, ASensorEventQueue* q) {
    ::free(q);
    return 0;
}

extern "C" int ASensorEventQueue_registerSensor(ASensorEventQueue*, ASensor const*,
                                                int32_t, int64_t) { return -1; }
extern "C" int ASensorEventQueue_enableSensor(ASensorEventQueue*, ASensor const*)  { return -1; }
extern "C" int ASensorEventQueue_disableSensor(ASensorEventQueue*, ASensor const*) { return -1; }
extern "C" int ASensorEventQueue_setEventRate(ASensorEventQueue*, ASensor const*, int32_t) { return -1; }
extern "C" int ASensorEventQueue_hasEvents(ASensorEventQueue*) { return 0; }
// ASensorEvent is large; we never fill any, so a void* count signature is ABI-safe.
extern "C" ssize_t ASensorEventQueue_getEvents(ASensorEventQueue*, void* /*events*/, size_t /*count*/) {
    return 0;
}
extern "C" int ASensorEventQueue_requestAdditionalInfoEvents(ASensorEventQueue*, bool) { return 0; }

extern "C" const char* ASensor_getName(ASensor const*)   { return "none"; }
extern "C" const char* ASensor_getVendor(ASensor const*) { return "none"; }
extern "C" const char* ASensor_getStringType(ASensor const*) { return ""; }
extern "C" int   ASensor_getType(ASensor const*)        { return 0; }
extern "C" float ASensor_getResolution(ASensor const*)  { return 0.0f; }
extern "C" int   ASensor_getMinDelay(ASensor const*)    { return 0; }
extern "C" int   ASensor_getFifoMaxEventCount(ASensor const*)      { return 0; }
extern "C" int   ASensor_getFifoReservedEventCount(ASensor const*) { return 0; }
extern "C" int   ASensor_getReportingMode(ASensor const*)         { return 0; }
extern "C" int   ASensor_getHandle(ASensor const*)                { return 0; }

// ===========================================================================
// 4. AChoreographer  (FUNCTIONAL — timerfd-on-ALooper, ~60Hz)
// ===========================================================================
extern "C" {
typedef struct AChoreographer AChoreographer;
typedef void (*AChoreographer_frameCallback)(long frameTimeNanos, void* data);
typedef void (*AChoreographer_frameCallback64)(int64_t frameTimeNanos, void* data);
}

namespace {

struct FrameCb {
    AChoreographer_frameCallback   cb32;
    AChoreographer_frameCallback64 cb64;
    void*                          data;
    int64_t                        dueNanos;   // monotonic deadline
};

struct ChoreographerImpl {
    LooperImpl*           looper  = nullptr;
    int                   timerfd = -1;
    std::mutex            mtx;
    std::vector<FrameCb>  pending;
};

thread_local ChoreographerImpl* t_chor = nullptr;

inline int64_t nowNanos() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

// ALooper callback: timerfd fired -> drain it and run all due frame callbacks.
int chorTimerCallback(int fd, int /*events*/, void* data) {
    ChoreographerImpl* C = reinterpret_cast<ChoreographerImpl*>(data);
    uint64_t exp;
    while (read(fd, &exp, sizeof(exp)) > 0) { /* drain */ }
    int64_t now = nowNanos();
    std::vector<FrameCb> due;
    {
        std::lock_guard<std::mutex> lk(C->mtx);
        std::vector<FrameCb> remain;
        for (auto& f : C->pending) {
            if (f.dueNanos <= now) due.push_back(f);
            else remain.push_back(f);
        }
        C->pending.swap(remain);
        // Re-arm if work remains.
        if (!C->pending.empty()) {
            int64_t next = C->pending.front().dueNanos;
            for (auto& f : C->pending) if (f.dueNanos < next) next = f.dueNanos;
            int64_t delta = next - now; if (delta < 1000000) delta = 1000000;
            itimerspec its{};
            its.it_value.tv_sec  = delta / 1000000000LL;
            its.it_value.tv_nsec = delta % 1000000000LL;
            timerfd_settime(C->timerfd, 0, &its, nullptr);
        }
    }
    for (auto& f : due) {
        if (f.cb64) f.cb64(now, f.data);
        else if (f.cb32) f.cb32((long)now, f.data);
    }
    return 1;   // keep the fd registered
}

ChoreographerImpl* getChoreographerForThread() {
    if (t_chor) return t_chor;
    ChoreographerImpl* C = new ChoreographerImpl();
    C->looper  = prepareForThread();
    C->timerfd = timerfd_create(CLOCK_MONOTONIC, TFD_NONBLOCK | TFD_CLOEXEC);
    if (C->timerfd >= 0 && C->looper && C->looper->epfd >= 0) {
        ALooper_addFd(reinterpret_cast<ALooper*>(C->looper), C->timerfd,
                      OH_ALOOPER_POLL_CALLBACK, OH_ALOOPER_EVENT_INPUT,
                      chorTimerCallback, C);
    } else {
        NDK_LOGW("AChoreographer: timerfd/looper setup failed errno=%{public}d", errno);
    }
    t_chor = C;
    return C;
}

void postFrame(AChoreographer_frameCallback cb32, AChoreographer_frameCallback64 cb64,
               void* data, int64_t delayMillis) {
    ChoreographerImpl* C = getChoreographerForThread();
    if (delayMillis < 0) delayMillis = 0;
    int64_t due = nowNanos() + delayMillis * 1000000LL + 16666666LL;  // +~1 frame
    {
        std::lock_guard<std::mutex> lk(C->mtx);
        C->pending.push_back(FrameCb{cb32, cb64, data, due});
    }
    if (C->timerfd >= 0) {
        int64_t delta = (delayMillis * 1000000LL) + 16666666LL;
        itimerspec its{};
        its.it_value.tv_sec  = delta / 1000000000LL;
        its.it_value.tv_nsec = delta % 1000000000LL;
        timerfd_settime(C->timerfd, 0, &its, nullptr);
    }
}

}  // namespace

extern "C" AChoreographer* AChoreographer_getInstance() {
    return reinterpret_cast<AChoreographer*>(getChoreographerForThread());
}
extern "C" void AChoreographer_postFrameCallback(AChoreographer* /*c*/,
        AChoreographer_frameCallback cb, void* data) {
    postFrame(cb, nullptr, data, 0);
}
extern "C" void AChoreographer_postFrameCallback64(AChoreographer* /*c*/,
        AChoreographer_frameCallback64 cb, void* data) {
    postFrame(nullptr, cb, data, 0);
}
extern "C" void AChoreographer_postFrameCallbackDelayed(AChoreographer* /*c*/,
        AChoreographer_frameCallback cb, void* data, long delayMillis) {
    postFrame(cb, nullptr, data, (int64_t)delayMillis);
}
extern "C" void AChoreographer_postFrameCallbackDelayed64(AChoreographer* /*c*/,
        AChoreographer_frameCallback64 cb, void* data, uint32_t delayMillis) {
    postFrame(nullptr, cb, data, (int64_t)delayMillis);
}
