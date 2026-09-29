/*
 * oh_input_bridge.cpp
 *
 * Native input event bridge implementation.
 *
 * Writes Android-format InputMessage structs to the server side of
 * InputChannel socket pairs. The message format must match what
 * InputConsumer (in ViewRootImpl) expects to read.
 *
 * InputMessage format (simplified for single-pointer touch):
 *   - Header: type, seq
 *   - Body (motion): action, deviceId, source, displayId, pointerCount,
 *                     downTime, eventTime, pointerProperties, pointerCoords
 */
#include "oh_input_bridge.h"

#include <android/log.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <poll.h>
#include <cerrno>
#include <cstring>
#include <ctime>

// OH MMI inner_api headers — pulled in here only (forward-decl'd in .h)
#include "axis_event.h"
#include "event_handler.h"
#include "event_runner.h"
#include "i_input_event_consumer.h"
#include "input_manager.h"
#include "key_event.h"
#include "pointer_event.h"

#define LOG_TAG "OH_InputBridge"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGD(...) __android_log_print(ANDROID_LOG_DEBUG, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

// Android InputMessage constants (from InputTransport.h)
// These must match the AOSP InputMessage struct layout
namespace {

// InputMessage types (mirror enum class InputMessage::Type at
// frameworks/native/include/input/InputTransport.h:69-77)
constexpr uint32_t INPUT_MSG_TYPE_KEY      = 0;
constexpr uint32_t INPUT_MSG_TYPE_MOTION   = 1;
constexpr uint32_t INPUT_MSG_TYPE_FINISHED = 2;
constexpr uint32_t INPUT_MSG_TYPE_FOCUS    = 3;
constexpr uint32_t INPUT_MSG_TYPE_CAPTURE  = 4;
constexpr uint32_t INPUT_MSG_TYPE_DRAG     = 5;
constexpr uint32_t INPUT_MSG_TYPE_TIMELINE = 6;
constexpr uint32_t INPUT_MSG_TYPE_TOUCHMODE = 7;

// MotionEvent source (from system/core/include/android/input.h)
constexpr int32_t AINPUT_SOURCE_TOUCHSCREEN = 0x00001002;
constexpr int32_t AINPUT_SOURCE_KEYBOARD    = 0x00000101;

// MotionEvent actions
constexpr int32_t AMOTION_EVENT_ACTION_DOWN = 0;
constexpr int32_t AMOTION_EVENT_ACTION_UP = 1;
constexpr int32_t AMOTION_EVENT_ACTION_MOVE = 2;
constexpr int32_t AMOTION_EVENT_ACTION_CANCEL = 3;

// MotionEvent tool type (enum class ToolType { UNKNOWN=0, FINGER=1, ... }
// from frameworks/native/include/input/Input.h:234 — underlying type int)
constexpr int32_t AMOTION_EVENT_TOOL_TYPE_FINGER = 1;

// AOSP 14 layout constants (frameworks/native/include/input/Input.h)
constexpr size_t MAX_POINTERS = 16;            // line 165
constexpr size_t MAX_POINTER_COORDS_AXES = 30; // PointerCoords::MAX_AXES

// Axis bit indices (subset; X/Y/Pressure/Size are the only ones we set)
constexpr uint64_t AXIS_X_BIT        = (1ULL << 0);
constexpr uint64_t AXIS_Y_BIT        = (1ULL << 1);
constexpr uint64_t AXIS_PRESSURE_BIT = (1ULL << 2);
constexpr uint64_t AXIS_SIZE_BIT     = (1ULL << 3);

// ============================================================
// AOSP 14 InputMessage canonical layout
// (frameworks/native/include/input/InputTransport.h:67-...)
//
// Audited 2026-05-18 against ECS ~/aosp source. ALL field order, alignment
// directives, and padding MUST match exactly — InputConsumer::consume()
// parses by struct size + offsets. Any drift = client reads garbage.
// ============================================================

// Header: 8 bytes total (4 type + 4 seq).
struct InputMessageHeader {
    uint32_t type;
    uint32_t seq;
};
static_assert(sizeof(InputMessageHeader) == 8, "Header must be 8 bytes");

// PointerProperties: 8 bytes (int32 id + enum class ToolType, default int).
struct PointerProperties {
    int32_t id;
    int32_t toolType;  // ToolType enum class — int underlying
};
static_assert(sizeof(PointerProperties) == 8, "PointerProperties must be 8B");

// PointerCoords: 136 bytes (bits 8 + values 120 + bool 1 + empty 7).
struct PointerCoords {
    uint64_t bits __attribute__((aligned(8)));
    float values[MAX_POINTER_COORDS_AXES];
    bool isResampled;
    uint8_t empty[7];
};
static_assert(sizeof(PointerCoords) == 136, "PointerCoords must be 136B");

// One pointer = properties + coords = 144 bytes.
struct InputMessagePointer {
    PointerProperties properties;
    PointerCoords coords;
};
static_assert(sizeof(InputMessagePointer) == 144,
              "InputMessagePointer must be 144B");

// Motion body — order/alignment mirrors AOSP InputMessage::Body::Motion.
// Note: pointers[MAX_POINTERS] is the FULL array on the C++ side, but
// writeMotionEvent only sends `pointerCount` actual pointers over the wire
// (AOSP's Motion::size() formula). This struct's sizeof is the upper bound.
struct MotionEventBody {
    int32_t eventId;
    uint32_t pointerCount;
    int64_t eventTime __attribute__((aligned(8)));
    int32_t deviceId;
    int32_t source;
    int32_t displayId;
    uint8_t hmac[32];
    int32_t action;
    int32_t actionButton;
    int32_t flags;
    int32_t metaState;
    int32_t buttonState;
    uint8_t classification;       // MotionClassification : uint8_t
    uint8_t empty2[3];            // 3-byte gap before edgeFlags
    int32_t edgeFlags;
    int64_t downTime __attribute__((aligned(8)));
    // Window transform (6 floats, AOSP order: dsdx, dtdx, dtdy, dsdy, tx, ty)
    float dsdx;
    float dtdx;
    float dtdy;
    float dsdy;
    float tx;
    float ty;
    float xPrecision;
    float yPrecision;
    float xCursorPosition;
    float yCursorPosition;
    // Raw transform (6 floats, same order as window transform)
    float dsdxRaw;
    float dtdxRaw;
    float dtdyRaw;
    float dsdyRaw;
    float txRaw;
    float tyRaw;
    // Pointer data array — MUST be the last field of the struct so
    // wire-format size() can truncate trailing pointers (see AOSP comment).
    InputMessagePointer pointers[MAX_POINTERS] __attribute__((aligned(8)));
};

// Wire-format size for `pointerCount` actual pointers.
// Matches AOSP: sizeof(Motion) - MAX_POINTERS*sizeof(Pointer) + n*sizeof(Pointer).
constexpr size_t motionBodyWireSize(uint32_t pointerCount) {
    return sizeof(MotionEventBody)
            - sizeof(InputMessagePointer) * MAX_POINTERS
            + sizeof(InputMessagePointer) * pointerCount;
}

// Finished body — for ACK back from client to server.
struct FinishedBody {
    bool handled;
    uint8_t empty[7];
    int64_t consumeTime;
};
static_assert(sizeof(FinishedBody) == 16, "FinishedBody must be 16B");

// ============================================================
// AOSP 14 InputMessage::Body::Key canonical layout
// (frameworks/native/include/input/InputTransport.h:95-112)
//
// Audited 2026-05-26 against ECS ~/aosp source. 96 bytes total. ALL field
// order/alignment MUST match exactly — InputConsumer::consume() parses by
// struct size + offsets, any drift = client reads garbage.
// ============================================================
struct KeyEventBody {
    int32_t eventId;                                // 0
    uint32_t empty1;                                // 4
    int64_t eventTime __attribute__((aligned(8)));  // 8
    int32_t deviceId;                               // 16
    int32_t source;                                 // 20
    int32_t displayId;                              // 24
    uint8_t hmac[32];                               // 28
    int32_t action;                                 // 60
    int32_t flags;                                  // 64
    int32_t keyCode;                                // 68
    int32_t scanCode;                               // 72
    int32_t metaState;                              // 76
    int32_t repeatCount;                            // 80
    uint32_t empty2;                                // 84
    int64_t downTime __attribute__((aligned(8)));   // 88
};
static_assert(sizeof(KeyEventBody) == 96, "KeyEventBody must be 96B");

// OH MMI keyCode -> Android keyCode.  The numeric values differ between the
// two systems, so unmapped codes return -1 and are dropped (passing the raw
// OH value through would land on the wrong Android key).  Covers the keys the
// adapter currently needs; extend as new apps require more.
//   OH KEYCODE_BACK=2 -> Android KEYCODE_BACK=4
//   OH KEYCODE_HOME=1 -> Android KEYCODE_HOME=3
inline int32_t mapOhKeyCodeToAndroid(int32_t ohKeyCode) {
    switch (ohKeyCode) {
        case 2:  return 4;   // BACK
        case 1:  return 3;   // HOME
        default: return -1;  // unmapped -> drop
    }
}

}  // anonymous namespace

namespace oh_adapter {

namespace {

/** Monotonic clock in nanoseconds for ledger arming/deadlines. */
int64_t steadyNowNs() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return static_cast<int64_t>(ts.tv_sec) * 1'000'000'000LL + ts.tv_nsec;
}

}  // namespace

OHInputBridge& OHInputBridge::getInstance() {
    static OHInputBridge instance;
    return instance;
}

void OHInputBridge::registerInputChannel(int32_t sessionId, int serverFd) {
    // Fn05.A07: rotate the session's window generation BEFORE the channel is
    // visible to injectors; any previous generation is torn down fail-closed.
    const std::string generation =
        completionRouter_.openSession(sessionId, steadyNowNs());

    std::lock_guard<std::mutex> lock(mutex_);

    SessionInput& session = sessions_[sessionId];
    session.serverFd = serverFd;
    session.seq = 0;
    session.generation = generation;

    LOGI("Registered input channel: session=%d, fd=%d, generation=%s",
         sessionId, serverFd, generation.c_str());

    // Fn05.A07: the ACK monitor is load-bearing — it observes Android
    // FINISHED messages and releases the gated OH MarkProcessed through the
    // completion ledger.  Start it with the first registered channel.
    if (!ackMonitoring_.load()) {
        ackMonitoring_ = true;
        ackThread_ = std::thread(&OHInputBridge::monitorAcks, this);
        ackThread_.detach();
    }
}

void OHInputBridge::unregisterInputChannel(int32_t sessionId) {
    // Fn05.A07: teardown the window generation fail-closed (all in-flight
    // tokens CANCELLED, pending MarkProcessed thunks purged uncalled).
    completionRouter_.closeSession(sessionId, steadyNowNs());

    std::lock_guard<std::mutex> lock(mutex_);

    auto it = sessions_.find(sessionId);
    if (it != sessions_.end()) {
        // Don't close serverFd here; Java InputChannel owns it
        LOGI("Unregistered input channel: session=%d", sessionId);
        sessions_.erase(it);
    }
}

void OHInputBridge::registerOHInputFd(int32_t sessionId, int ohInputFd) {
    std::lock_guard<std::mutex> lock(mutex_);

    auto it = sessions_.find(sessionId);
    if (it != sessions_.end()) {
        it->second.ohInputFd = ohInputFd;
        LOGI("Registered OH input fd: session=%d, ohFd=%d", sessionId, ohInputFd);
    }

    // Start monitoring thread if not already running
    if (!monitoring_.load()) {
        monitoring_ = true;
        monitorThread_ = std::thread(&OHInputBridge::monitorOHInputEvents, this);
        monitorThread_.detach();
    }
}

int32_t OHInputBridge::injectTouchEvent(int32_t sessionId, int32_t action,
                                          float x, float y,
                                          int64_t downTime, int64_t eventTime,
                                          int64_t ohEventId,
                                          input::MarkProcessedThunk markProcessed) {
    // Fn05.A07: accept into the completion ledger first.  If the event cannot
    // be tracked, tell the caller to MarkProcessed immediately — injecting
    // without a ledger token would produce a FINISHED with no pairing and
    // (worse) leave OH waiting on a MarkProcessed that is never gated.  A
    // ledger REJECTION (collision) is already recorded fail-closed; the
    // caller must not ack.
    switch (completionRouter_.acceptEvent(sessionId, ohEventId,
                                          std::move(markProcessed))) {
        case input::OhEventCompletionRouter::AcceptResult::ACCEPTED:
            break;
        case input::OhEventCompletionRouter::AcceptResult::UNTRACKED:
            LOGD("injectTouchEvent: session=%d ohEvent=%lld not trackable",
                 sessionId, (long long)ohEventId);
            return INJECT_RC_UNTRACKED;
        case input::OhEventCompletionRouter::AcceptResult::REJECTED:
            LOGD("injectTouchEvent: session=%d ohEvent=%lld ledger-rejected",
                 sessionId, (long long)ohEventId);
            return INJECT_RC_REJECTED;
    }

    std::lock_guard<std::mutex> lock(mutex_);

    auto it = sessions_.find(sessionId);
    if (it == sessions_.end() || it->second.serverFd < 0) {
        LOGE("injectTouchEvent: session %d has no server fd", sessionId);
        completionRouter_.publishReject(sessionId, ohEventId, steadyNowNs(),
                                        -1);
        return -1;
    }

    SessionInput& session = it->second;
    session.seq++;
    const uint32_t seq = session.seq;

    if (!completionRouter_.arm(sessionId, ohEventId, seq, steadyNowNs())) {
        LOGE("injectTouchEvent: session=%d ohEvent=%lld arm failed (seq=%u)",
             sessionId, (long long)ohEventId, seq);
        completionRouter_.publishReject(sessionId, ohEventId, steadyNowNs(),
                                        -1);
        return -1;
    }

    int result = writeMotionEvent(session.serverFd, seq,
                                   action, x, y, downTime, eventTime);
    if (result != 0) {
        completionRouter_.publishReject(sessionId, ohEventId, steadyNowNs(),
                                        result);
        return result;
    }

    LOGD("injectTouchEvent: session=%d, action=%d, x=%.1f, y=%.1f, seq=%u armed",
         sessionId, action, x, y, seq);

    return INJECT_RC_OK;
}

int32_t OHInputBridge::injectSyntheticTouchEvent(int32_t sessionId,
                                                  int32_t action,
                                                  float x, float y,
                                                  int64_t downTime,
                                                  int64_t eventTime) {
    const int64_t syntheticEventId =
        nextSyntheticEventId_.fetch_sub(1, std::memory_order_relaxed);
    return injectTouchEvent(sessionId, action, x, y, downTime, eventTime,
                            syntheticEventId, {});
}

int OHInputBridge::writeMotionEvent(int fd, uint32_t seq, int32_t action,
                                     float x, float y,
                                     int64_t downTime, int64_t eventTime) {
    /*
     * 2026-05-18 Phase 2: bit-exact AOSP 14 InputMessage::Body::Motion format.
     * AOSP InputConsumer::consume reads (header + body) where body size is
     * computed from pointerCount — see motionBodyWireSize(). Sending the full
     * sizeof(MotionEventBody) (incl. all MAX_POINTERS slots) would also work
     * for SOCK_SEQPACKET (boundary preserves count) but wastes bytes; AOSP
     * truncates to actual pointer count.
     *
     * Field order MUST match AOSP — see frameworks/native/include/input/
     * InputTransport.h:67-... (audited 2026-05-18).
     */

    // Stack buffer for header + body (single pointer = 144B + ~200B body
    // header + 8B msg header = well under 4KB, fits in typical stack frame).
    struct {
        InputMessageHeader header;
        MotionEventBody body;
    } msg;
    memset(&msg, 0, sizeof(msg));

    // Header
    msg.header.type = INPUT_MSG_TYPE_MOTION;
    msg.header.seq = seq;

    // Motion body — AOSP field order
    msg.body.eventId = static_cast<int32_t>(seq);
    msg.body.pointerCount = 1;
    msg.body.eventTime = eventTime;
    msg.body.deviceId = 1;
    msg.body.source = AINPUT_SOURCE_TOUCHSCREEN;
    msg.body.displayId = 0;
    // hmac left zeroed (AOSP InputDispatcher signs events for security; OH
    // side has no equivalent — consumer accepts any when hmac is zero).
    msg.body.action = action;
    msg.body.actionButton = 0;
    msg.body.flags = 0;
    msg.body.metaState = 0;
    msg.body.buttonState = 0;
    msg.body.classification = 0;   // MotionClassification::NONE
    // empty2[3] already zeroed by memset
    msg.body.edgeFlags = 0;
    msg.body.downTime = downTime;

    // Window transform = identity (AOSP order: dsdx, dtdx, dtdy, dsdy, tx, ty)
    msg.body.dsdx = 1.0f;
    msg.body.dtdx = 0.0f;
    msg.body.dtdy = 0.0f;
    msg.body.dsdy = 1.0f;
    msg.body.tx   = 0.0f;
    msg.body.ty   = 0.0f;

    msg.body.xPrecision = 1.0f;
    msg.body.yPrecision = 1.0f;
    msg.body.xCursorPosition = 0.0f;
    msg.body.yCursorPosition = 0.0f;

    // Raw transform = identity (same field order as window transform)
    msg.body.dsdxRaw = 1.0f;
    msg.body.dtdxRaw = 0.0f;
    msg.body.dtdyRaw = 0.0f;
    msg.body.dsdyRaw = 1.0f;
    msg.body.txRaw   = 0.0f;
    msg.body.tyRaw   = 0.0f;

    // Single pointer at index 0
    InputMessagePointer& p0 = msg.body.pointers[0];
    p0.properties.id = 0;
    p0.properties.toolType = AMOTION_EVENT_TOOL_TYPE_FINGER;
    p0.coords.bits = AXIS_X_BIT | AXIS_Y_BIT | AXIS_PRESSURE_BIT | AXIS_SIZE_BIT;
    p0.coords.values[0] = x;       // AXIS_X
    p0.coords.values[1] = y;       // AXIS_Y
    p0.coords.values[2] = 1.0f;    // AXIS_PRESSURE
    p0.coords.values[3] = 0.01f;   // AXIS_SIZE
    p0.coords.isResampled = false;

    // Send only header + body-for-this-pointer-count (AOSP wire format).
    const size_t wireSize = sizeof(InputMessageHeader)
                            + motionBodyWireSize(1);
    ssize_t written = send(fd, &msg, wireSize, MSG_DONTWAIT | MSG_NOSIGNAL);
    if (written < 0) {
        LOGE("writeMotionEvent: send failed, errno=%d (%s)", errno, strerror(errno));
        return -errno;
    }
    if (static_cast<size_t>(written) != wireSize) {
        LOGE("writeMotionEvent: short write %zd / %zu", written, wireSize);
        return -1;
    }
    return 0;
}

int32_t OHInputBridge::injectKeyEvent(int32_t sessionId, int32_t action,
                                       int32_t keyCode, int32_t metaState,
                                       int64_t downTime, int64_t eventTime,
                                       int64_t ohEventId,
                                       input::MarkProcessedThunk markProcessed) {
    // Fn05.A07: same FINISHED-gated contract as injectTouchEvent.
    switch (completionRouter_.acceptEvent(sessionId, ohEventId,
                                          std::move(markProcessed))) {
        case input::OhEventCompletionRouter::AcceptResult::ACCEPTED:
            break;
        case input::OhEventCompletionRouter::AcceptResult::UNTRACKED:
            LOGD("injectKeyEvent: session=%d ohEvent=%lld not trackable",
                 sessionId, (long long)ohEventId);
            return INJECT_RC_UNTRACKED;
        case input::OhEventCompletionRouter::AcceptResult::REJECTED:
            LOGD("injectKeyEvent: session=%d ohEvent=%lld ledger-rejected",
                 sessionId, (long long)ohEventId);
            return INJECT_RC_REJECTED;
    }

    std::lock_guard<std::mutex> lock(mutex_);

    auto it = sessions_.find(sessionId);
    if (it == sessions_.end() || it->second.serverFd < 0) {
        LOGE("injectKeyEvent: session %d has no server fd", sessionId);
        completionRouter_.publishReject(sessionId, ohEventId, steadyNowNs(),
                                        -1);
        return -1;
    }

    SessionInput& session = it->second;
    session.seq++;
    const uint32_t seq = session.seq;

    if (!completionRouter_.arm(sessionId, ohEventId, seq, steadyNowNs())) {
        LOGE("injectKeyEvent: session=%d ohEvent=%lld arm failed (seq=%u)",
             sessionId, (long long)ohEventId, seq);
        completionRouter_.publishReject(sessionId, ohEventId, steadyNowNs(),
                                        -1);
        return -1;
    }

    int result = writeKeyEvent(session.serverFd, seq,
                               action, keyCode, metaState, downTime, eventTime);
    if (result != 0) {
        completionRouter_.publishReject(sessionId, ohEventId, steadyNowNs(),
                                        result);
        return result;
    }

    LOGI("injectKeyEvent: session=%d, action=%d, keyCode=%d, seq=%u armed",
         sessionId, action, keyCode, seq);

    return INJECT_RC_OK;
}

int OHInputBridge::writeKeyEvent(int fd, uint32_t seq, int32_t action,
                                  int32_t keyCode, int32_t metaState,
                                  int64_t downTime, int64_t eventTime) {
    // Bit-exact AOSP 14 InputMessage::Body::Key — field order MUST match
    // frameworks/native/include/input/InputTransport.h:95-112.
    struct {
        InputMessageHeader header;
        KeyEventBody body;
    } msg;
    memset(&msg, 0, sizeof(msg));

    msg.header.type = INPUT_MSG_TYPE_KEY;
    msg.header.seq = seq;

    msg.body.eventId = static_cast<int32_t>(seq);
    msg.body.eventTime = eventTime;
    // deviceId = -1 (KeyCharacterMap.VIRTUAL_KEYBOARD): a synthetic source with
    // a guaranteed built-in keymap, so ViewRootImpl won't try to load a
    // physical device's KeyCharacterMap for our injected key.
    msg.body.deviceId = -1;
    msg.body.source = AINPUT_SOURCE_KEYBOARD;
    msg.body.displayId = 0;
    // hmac left zeroed (consumer accepts zero hmac — same as motion path).
    msg.body.action = action;
    msg.body.flags = 0;
    msg.body.keyCode = keyCode;
    msg.body.scanCode = 0;
    msg.body.metaState = metaState;
    msg.body.repeatCount = 0;
    msg.body.downTime = downTime;

    const size_t wireSize = sizeof(InputMessageHeader) + sizeof(KeyEventBody);
    ssize_t written = send(fd, &msg, wireSize, MSG_DONTWAIT | MSG_NOSIGNAL);
    if (written < 0) {
        LOGE("writeKeyEvent: send failed, errno=%d (%s)", errno, strerror(errno));
        return -errno;
    }
    if (static_cast<size_t>(written) != wireSize) {
        LOGE("writeKeyEvent: short write %zd / %zu", written, wireSize);
        return -1;
    }
    LOGI("writeKeyEvent: sent %zd bytes to fd=%d seq=%u keyCode=%d", written, fd, seq, keyCode);
    return 0;
}

void OHInputBridge::monitorOHInputEvents() {
    LOGI("OH input monitor thread started");

    while (monitoring_.load()) {
        std::vector<pollfd> fds;
        std::vector<int32_t> sessionIds;

        {
            std::lock_guard<std::mutex> lock(mutex_);
            for (auto& pair : sessions_) {
                if (pair.second.ohInputFd >= 0 && pair.second.serverFd >= 0) {
                    pollfd pfd;
                    pfd.fd = pair.second.ohInputFd;
                    pfd.events = POLLIN;
                    pfd.revents = 0;
                    fds.push_back(pfd);
                    sessionIds.push_back(pair.first);
                }
            }
        }

        if (fds.empty()) {
            // No OH input fds to monitor yet, sleep briefly
            usleep(100000); // 100ms
            continue;
        }

        int ret = poll(fds.data(), fds.size(), 100 /* timeout_ms */);
        if (ret <= 0) continue;

        for (size_t i = 0; i < fds.size(); i++) {
            if (fds[i].revents & POLLIN) {
                /*
                 * Read OH input event and convert to Android MotionEvent.
                 *
                 * OH PointerEvent format (from MultiModal Input framework):
                 * - action: DOWN/UP/MOVE
                 * - pointerId, x, y, pressure
                 * - timestamp
                 *
                 * Phase 2: Parse the actual OH MMI event format here.
                 * Phase 1: The monitoring thread is set up but real OH
                 * event parsing depends on the actual OH MMI binary format.
                 */
                uint8_t buf[4096];
                ssize_t nread = read(fds[i].fd, buf, sizeof(buf));
                if (nread > 0) {
                    LOGD("OH input event received: session=%d, %zd bytes",
                         sessionIds[i], nread);
                    // Phase 2: Parse OH event format and call injectTouchEvent()
                }
            }
        }
    }

    LOGI("OH input monitor thread stopped");
}

// Fn05.A07 — poll all server fds for FINISHED messages that ViewRootImpl's
// InputConsumer writes back after consuming an InputEvent, and forward them
// to the completion router.  This is the ONLY path that completes ledger
// tokens and releases the gated OH MarkProcessed; it also drives the
// FINISHED-deadline scan so stalled tokens close as TIMEOUT (fail-closed,
// no MarkProcessed) instead of hanging the ledger forever.
void OHInputBridge::monitorAcks() {
    LOGI("ACK monitor thread started (Fn05.A07 completion path)");
    while (ackMonitoring_.load()) {
        std::vector<pollfd> fds;
        // Generation bound to each fd AT REGISTRATION TIME: a FINISHED read
        // from this fd belongs to that generation, even if the session has
        // since been re-registered with a new generation and seq restart.
        std::vector<std::string> fdGenerations;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            for (auto& pair : sessions_) {
                if (pair.second.serverFd >= 0) {
                    pollfd pfd;
                    pfd.fd = pair.second.serverFd;
                    pfd.events = POLLIN;
                    pfd.revents = 0;
                    fds.push_back(pfd);
                    fdGenerations.push_back(pair.second.generation);
                }
            }
        }
        if (fds.empty()) {
            completionRouter_.scanTimeouts(steadyNowNs());
            usleep(100000);
            continue;
        }
        int ret = poll(fds.data(), fds.size(), 100 /* ms */);
        if (ret > 0) {
            for (size_t i = 0; i < fds.size(); i++) {
                if (fds[i].revents & POLLIN) {
                    uint8_t buf[512];
                    ssize_t n = recv(fds[i].fd, buf, sizeof(buf), MSG_DONTWAIT);
                    if (n >= 8) {
                        uint32_t type = *reinterpret_cast<uint32_t*>(buf);
                        uint32_t seq = *reinterpret_cast<uint32_t*>(buf + 4);
                        int handled = -1;
                        if (type == INPUT_MSG_TYPE_FINISHED && n >= 9) {
                            handled = buf[8];  // FinishedBody.handled (body offset 0)
                        }
                        LOGI("ACK generation=%s type=%u(%s) seq=%u handled=%d nread=%zd",
                             fdGenerations[i].c_str(), type,
                             (type == INPUT_MSG_TYPE_FINISHED ? "FINISHED" : "OTHER"),
                             seq, handled, n);
                        if (type == INPUT_MSG_TYPE_FINISHED) {
                            // Completes the ledger token in the fd's OWN
                            // generation; the gated OH MarkProcessed is
                            // emitted by the router only now.
                            completionRouter_.onFinishedGeneration(
                                fdGenerations[i], seq, steadyNowNs(),
                                static_cast<int64_t>(syscall(SYS_gettid)),
                                handled);
                        }
                    }
                }
            }
        }
        // Scan AFTER draining ready fds so a FINISHED that just arrived is
        // applied before its token can be judged timed out.
        completionRouter_.scanTimeouts(steadyNowNs());
    }
    LOGI("ACK monitor thread stopped");
}

// ============================================================
// OhMmiInputConsumer — bridges OH MMI events to Android InputChannel
//
// Implements OHOS::MMI::IInputEventConsumer. The MMI service holds a
// shared_ptr to this object (kept alive on the bridge side via
// OHInputBridge::mmiConsumer_) and dispatches each OH input event to one of
// the three OnInputEvent overloads on the registered EventHandler thread.
//
// Pointer/Key events are converted to Android MotionEvent/KeyEvent semantics
// and forwarded to OHInputBridge::injectTouchEvent/injectKeyEvent, which
// writes a binary Android InputMessage to the InputChannel server fd;
// ViewRootImpl's WindowInputEventReceiver reads from the client end and
// dispatches up the View tree (HelloWorld's Button.OnClickListener.onClick
// eventually fires).
//
// Fn05.A07 (2026-07-28): OH MarkProcessed is no longer emitted right after
// injection.  Accepted events are armed in the FINISHED-gated completion
// ledger and acked only when the matching Android FINISHED(seq) is observed
// by the ACK monitor; publish failures close the token as PUBLISH_REJECT
// with no OH ack (fail-closed).  Only pre-accept drops (unknown window,
// unmapped key/action, malformed event, axis noop) MarkProcessed
// immediately, because no FINISHED will ever exist for them.
//
// See doc/Input_Adapter_design.html §3.3.5 for design rationale.
// ============================================================
class OhMmiInputConsumer : public OHOS::MMI::IInputEventConsumer {
public:
    OhMmiInputConsumer() = default;
    ~OhMmiInputConsumer() override = default;

    void OnInputEvent(std::shared_ptr<OHOS::MMI::KeyEvent> keyEvent) const override {
        // 2026-05-26 DIAG (LOGE to survive hilog debug-level filtering): confirm
        // whether OH MMI client dispatches key events to this consumer at all.
        LOGE("DIAG OnInputEvent(KeyEvent) ENTERED keyEvent=%p", (void*)keyEvent.get());
        if (!keyEvent) return;

        const int32_t ohKeyCode = keyEvent->GetKeyCode();
        const int32_t ohAction  = keyEvent->GetKeyAction();

        // OH KeyAction -> Android KeyEvent action.
        //   OH: CANCEL=1, DOWN=2, UP=3      AOSP: ACTION_DOWN=0, ACTION_UP=1
        int32_t androidAction;
        if (ohAction == OHOS::MMI::KeyEvent::KEY_ACTION_DOWN) {
            androidAction = 0;
        } else if (ohAction == OHOS::MMI::KeyEvent::KEY_ACTION_UP) {
            androidAction = 1;
        } else {
            // Pre-accept drop: this event never enters the Fn05.A07 ledger,
            // so no FINISHED will ever exist for it — ack OH immediately.
            LOGI("OnInputEvent(KeyEvent): ohKeyCode=%d ohAction=%d not DOWN/UP, drop",
                 ohKeyCode, ohAction);
            keyEvent->MarkProcessed();
            return;
        }

        const int32_t androidKeyCode = mapOhKeyCodeToAndroid(ohKeyCode);
        if (androidKeyCode < 0) {
            // Pre-accept drop (unmapped key): ack OH immediately.
            LOGI("OnInputEvent(KeyEvent): ohKeyCode=%d unmapped, drop", ohKeyCode);
            keyEvent->MarkProcessed();
            return;
        }

        // Route by OH's own target-window decision, mirroring OH
        // InputTransferStation::OnInputEvent (input_transfer_station.cpp:68):
        // GetAgentWindowId() is the window OH focus delivered this key to.
        // sessionId == windowId in this adapter, so it IS the target session.
        // This makes input follow OH focus for every change (resume, back-stack
        // pop) with no cached state.
        int32_t sessionId = static_cast<int32_t>(keyEvent->GetAgentWindowId());
        if (!OHInputBridge::getInstance().isKnownSession(sessionId)) {
            // Pre-accept drop (not an adapter window): ack OH immediately.
            LOGD("OnInputEvent(KeyEvent): agentWindowId=%d not an adapter window, drop",
                 sessionId);
            keyEvent->MarkProcessed();
            return;
        }

        // OH timestamps are microseconds; Android InputMessage expects ns.
        int64_t eventTimeNs = keyEvent->GetActionTime() * 1000LL;
        // Android back-key dispatch ties DOWN and UP together: Activity.onKeyDown
        // calls event.startTracking() for KEYCODE_BACK, and onKeyUp fires
        // onBackPressed() only when event.isTracking() — which requires the UP to
        // carry the matching DOWN timestamp.  Cache downTime per-thread, mirroring
        // the PointerEvent downTime cache above.
        static thread_local int64_t s_keyDownNs = 0;
        int64_t downTimeNs;
        if (androidAction == 0 /* DOWN */) {
            s_keyDownNs = eventTimeNs;
            downTimeNs = eventTimeNs;
        } else {
            downTimeNs = (s_keyDownNs > 0) ? s_keyDownNs : eventTimeNs;
        }

        LOGI("OnInputEvent(KeyEvent): session=%d ohKey=%d->android=%d "
             "ohAction=%d->%d down=%lldns evt=%lldns",
             sessionId, ohKeyCode, androidKeyCode, ohAction, androidAction,
             (long long)downTimeNs, (long long)eventTimeNs);

        // Fn05.A07: completion is ledger-gated.  OH MarkProcessed is invoked
        // by the router only after the matching Android FINISHED arrives;
        // on publish failure it is never invoked (PUBLISH_REJECT).  Only an
        // untrackable event (no ledger token) is acked here immediately.
        const int64_t ohEventId = keyEvent->GetId();
        int32_t rc = OHInputBridge::getInstance().injectKeyEvent(
            sessionId, androidAction, androidKeyCode, /*metaState=*/0,
            downTimeNs, eventTimeNs, ohEventId,
            [keyEvent]() { keyEvent->MarkProcessed(); });
        if (rc == OHInputBridge::INJECT_RC_UNTRACKED) {
            LOGD("OnInputEvent(KeyEvent): ohEvent=%lld untrackable, ack now",
                 (long long)ohEventId);
            keyEvent->MarkProcessed();
        }
    }

    void OnInputEvent(std::shared_ptr<OHOS::MMI::PointerEvent> pointerEvent) const override {
        if (!pointerEvent) return;

        // Route by OH's target-window decision, mirroring OH InputTransferStation
        // (input_transfer_station.cpp:98).  sessionId == windowId here.
        int32_t sessionId = static_cast<int32_t>(pointerEvent->GetAgentWindowId());
        if (!OHInputBridge::getInstance().isKnownSession(sessionId)) {
            // Pre-accept drop (not an adapter window): ack OH immediately.
            LOGD("OnInputEvent(PointerEvent): agentWindowId=%d not an adapter window, drop",
                 sessionId);
            pointerEvent->MarkProcessed();
            return;
        }

        int32_t pointerId = pointerEvent->GetPointerId();
        OHOS::MMI::PointerEvent::PointerItem item;
        if (!pointerEvent->GetPointerItem(pointerId, item)) {
            // Pre-accept drop (malformed event): ack OH immediately.
            LOGE("OnInputEvent(PointerEvent): GetPointerItem(%d) failed", pointerId);
            pointerEvent->MarkProcessed();
            return;
        }

        // OH MMI PointerEvent::POINTER_ACTION_* → Android MotionEvent action.
        // OH:  CANCEL=1, DOWN=2, MOVE=3, UP=4
        // AOSP MotionEvent: ACTION_DOWN=0, UP=1, MOVE=2, CANCEL=3
        int32_t androidAction = -1;
        switch (pointerEvent->GetPointerAction()) {
            case OHOS::MMI::PointerEvent::POINTER_ACTION_DOWN:    androidAction = 0; break;
            case OHOS::MMI::PointerEvent::POINTER_ACTION_UP:      androidAction = 1; break;
            case OHOS::MMI::PointerEvent::POINTER_ACTION_MOVE:    androidAction = 2; break;
            case OHOS::MMI::PointerEvent::POINTER_ACTION_CANCEL:  androidAction = 3; break;
            default:
                // Pre-accept drop (unhandled action): ack OH immediately.
                LOGD("OnInputEvent(PointerEvent): unhandled OH action=%d, drop",
                     pointerEvent->GetPointerAction());
                pointerEvent->MarkProcessed();
                return;
        }

        // Use window-relative X/Y (aligned with ArkUI mmi_event_convertor.cpp:190-194).
        // InputMessage transform is identity (dsdx=dsdy=1, tx=ty=0), so AOSP consumer
        // treats MotionEvent.getX/Y as window-relative — feeding window coords
        // directly is correct regardless of where SCB places the window on display.
        // GetWindowXPos returns double for sub-pixel precision; fall back to
        // GetWindowX (int) when sub-pixel data unavailable.
        float x = static_cast<float>(item.GetWindowXPos());
        float y = static_cast<float>(item.GetWindowYPos());
        if (x == 0.0f && y == 0.0f) {
            x = static_cast<float>(item.GetWindowX());
            y = static_cast<float>(item.GetWindowY());
        }

        // OH timestamps are microseconds; Android InputMessage expects ns.
        int64_t eventTimeNs = pointerEvent->GetActionTime() * 1000LL;
        // OH PointerEvent::GetDownTime() returns 0 on this device (OH MMI
        // doesn't populate it for synthetic / non-Stage callers).  AOSP
        // ViewRootImpl click detection compares (eventTime - downTime) against
        // ViewConfiguration.getLongPressTimeout() (500ms); a downTime=0 with
        // multi-second eventTime registers as a non-click long-press and
        // Button.performClick() never fires.  Adapter caches its own
        // per-action-sequence downTime: set at DOWN, reused at MOVE/UP, reset
        // at UP/CANCEL.  Phase 1: single-touch only, single static cache;
        // multi-touch (Phase 2) needs per-pointerId map.
        static thread_local int64_t s_cachedDownTimeNs = 0;
        int64_t downTimeNs;
        if (androidAction == 0 /* AMOTION_EVENT_ACTION_DOWN */) {
            s_cachedDownTimeNs = eventTimeNs;
            downTimeNs = eventTimeNs;
        } else {
            int64_t ohDownNs = item.GetDownTime() * 1000LL;
            if (ohDownNs > 0) {
                downTimeNs = ohDownNs;        // trust OH if it actually has one
            } else if (s_cachedDownTimeNs > 0) {
                downTimeNs = s_cachedDownTimeNs;  // fall back to adapter cache
            } else {
                downTimeNs = eventTimeNs;     // no prior DOWN seen; use event time
            }
            if (androidAction == 1 /* UP */ || androidAction == 3 /* CANCEL */) {
                int64_t carry = downTimeNs;
                s_cachedDownTimeNs = 0;
                downTimeNs = carry;
            }
        }

        LOGI("OnInputEvent(PointerEvent): session=%d action=%d (oh=%d) x=%.1f y=%.1f "
             "down=%lldns evt=%lldns",
             sessionId, androidAction, pointerEvent->GetPointerAction(), x, y,
             (long long)downTimeNs, (long long)eventTimeNs);

        // Fn05.A07: completion is ledger-gated (see KeyEvent path above).
        const int64_t ohEventId = pointerEvent->GetId();
        int32_t rc = OHInputBridge::getInstance().injectTouchEvent(
            sessionId, androidAction, x, y, downTimeNs, eventTimeNs,
            ohEventId,
            [pointerEvent]() { pointerEvent->MarkProcessed(); });
        if (rc == OHInputBridge::INJECT_RC_UNTRACKED) {
            LOGD("OnInputEvent(PointerEvent): ohEvent=%lld untrackable, ack now",
                 (long long)ohEventId);
            pointerEvent->MarkProcessed();
        }
    }

    void OnInputEvent(std::shared_ptr<OHOS::MMI::AxisEvent> axisEvent) const override {
        // Axis events (wheel / pinch / etc.) — not used by HelloWorld; Phase 1 noop.
        // Pre-accept drop: never enters the Fn05.A07 ledger, ack OH immediately.
        if (axisEvent) axisEvent->MarkProcessed();
    }
};

bool OHInputBridge::isKnownSession(int32_t sessionId) {
    std::lock_guard<std::mutex> lock(mutex_);
    return sessions_.find(sessionId) != sessions_.end();
}

void OHInputBridge::subscribeMmi(int32_t sessionId) {
    // Single-shot process-level consumer registration, mirroring OH
    // InputTransferStation: ONE SetWindowInputEventConsumer for the process.
    // The consumer routes each event by GetAgentWindowId() (OH's focus
    // decision) — no per-session "active" state is tracked here.
    bool expected = false;
    if (!mmiSubscribed_.compare_exchange_strong(expected, true)) {
        LOGI("subscribeMmi: consumer already registered (latest session=%d)", sessionId);
        return;
    }

    // EventHandler running on the current thread's runner; if we're on a
    // worker thread without a runner, fall back to creating a dedicated runner
    // so MMI callbacks have somewhere to land. HelloWorld createSession is
    // called from JNI on a binder/worker thread, so we explicitly Create() a
    // new runner thread for MMI delivery — this matches how OH native
    // InputTransferStation creates its INPUT_AND_VSYNC_THREAD runner.
    auto runner = OHOS::AppExecFwk::EventRunner::Create("AdapterMmiConsumer");
    if (!runner) {
        LOGE("subscribeMmi: EventRunner::Create failed");
        mmiSubscribed_.store(false);
        return;
    }
    mmiEventHandler_ = std::make_shared<OHOS::AppExecFwk::EventHandler>(runner);
    mmiConsumer_ = std::make_shared<OhMmiInputConsumer>();

    int32_t rc = OHOS::MMI::InputManager::GetInstance()->SetWindowInputEventConsumer(
        mmiConsumer_, mmiEventHandler_);
    if (rc != 0) {
        LOGE("subscribeMmi: SetWindowInputEventConsumer rc=%d (session=%d)", rc, sessionId);
        // Don't roll back state — MMI may have partially registered; future
        // calls just no-op.
        return;
    }
    LOGI("subscribeMmi: MMI consumer registered for session=%d (Input_Adapter_design §3.3.5)",
         sessionId);
}

}  // namespace oh_adapter
