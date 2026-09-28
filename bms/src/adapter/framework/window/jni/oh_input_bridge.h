/*
 * oh_input_bridge.h
 *
 * Native input event bridge between OH MMI and Android InputChannel.
 *
 * Manages per-session InputPublisher instances that write Android-format
 * MotionEvents to the server side of an InputChannel pair. ViewRootImpl
 * reads from the client side, completing the touch event pipeline.
 *
 * Also monitors OH input event fds (obtained during session creation)
 * and forwards events through the InputPublisher.
 */
#ifndef OH_INPUT_BRIDGE_H
#define OH_INPUT_BRIDGE_H

#include <jni.h>
#include <cstdint>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <thread>
#include <atomic>

#include "oh_event_completion_router.h"

// Forward decls (full OH MMI headers pulled in by .cpp only — keep .h lean)
namespace OHOS {
namespace MMI {
struct IInputEventConsumer;
}
namespace AppExecFwk {
class EventHandler;
}
}

namespace oh_adapter {

/**
 * Manages input event bridging for all window sessions.
 *
 * For each window session, holds:
 * - The server-side InputChannel fd (from Java InputChannel pair)
 * - The OH input event fd (from OH session creation)
 * - An event forwarding mechanism between the two
 */
class OHInputBridge {
public:
    static OHInputBridge& getInstance();

    /**
     * Register a server-side Android InputChannel fd for a session.
     * Called from Java when InputEventBridge creates a channel pair.
     */
    void registerInputChannel(int32_t sessionId, int serverFd);

    /**
     * Unregister and clean up for a session.
     */
    void unregisterInputChannel(int32_t sessionId);

    /**
     * Register the OH-side input event fd for a session.
     * Called when the OH session is created and returns its input channel fd.
     * Starts monitoring for OH input events on this fd.
     */
    void registerOHInputFd(int32_t sessionId, int ohInputFd);

    /**
     * Inject a touch event into the Android InputChannel for a session.
     * Converts parameters to Android InputMessage format and writes
     * to the server-side fd.
     *
     * Fn05.A07 FINISHED-gated completion: the event is accepted into the
     * completion ledger and armed with its allocated Android seq BEFORE the
     * write.  The supplied MarkProcessed thunk is invoked only when the
     * matching Android FINISHED(seq) is observed; on publish failure the
     * token is closed as PUBLISH_REJECT and the thunk is purged uncalled
     * (fail-closed, DESIGN.md §5).
     *
     * @param sessionId  Window session ID
     * @param action     MotionEvent action (0=DOWN, 1=UP, 2=MOVE)
     * @param x          Touch X coordinate in window space
     * @param y          Touch Y coordinate in window space
     * @param downTime   Timestamp of ACTION_DOWN in nanoseconds
     * @param eventTime  Timestamp of this event in nanoseconds
     * @param ohEventId  OH MMI InputEvent::GetId() of the source event
     * @param markProcessed  Thunk emitting OH MarkProcessed for the event
     * @return INJECT_RC_OK (0) when accepted and published — caller must NOT
     *         MarkProcessed, completion is ledger-gated;
     *         INJECT_RC_UNTRACKED (1) when the event cannot be tracked (no
     *         ledger token, no FINISHED will ever arrive) — caller MUST
     *         MarkProcessed immediately;
     *         INJECT_RC_REJECTED (2) when the ledger rejected the event
     *         (e.g. LEDGER_COLLISION, already recorded fail-closed) —
     *         caller must NOT MarkProcessed;
     *         negative on publish failure after arming — caller must NOT
     *         MarkProcessed (PUBLISH_REJECT already recorded fail-closed).
     */
    static constexpr int32_t INJECT_RC_OK = 0;
    static constexpr int32_t INJECT_RC_UNTRACKED = 1;
    static constexpr int32_t INJECT_RC_REJECTED = 2;
    int32_t injectTouchEvent(int32_t sessionId, int32_t action,
                              float x, float y,
                              int64_t downTime, int64_t eventTime,
                              int64_t ohEventId,
                              input::MarkProcessedThunk markProcessed);

    /**
     * Inject a touch event that has no originating OH InputEvent.
     *
     * JNI/control-plane injection still needs an Android FINISHED token so
     * it cannot bypass the Fn05.A07 backpressure ledger.  This wrapper assigns
     * a bridge-private identity outside OH InputEvent's int32 id domain and
     * uses an empty MarkProcessed thunk: FINISHED closes the ledger row, but
     * no OH acknowledgement is fabricated.
     */
    int32_t injectSyntheticTouchEvent(int32_t sessionId, int32_t action,
                                       float x, float y,
                                       int64_t downTime, int64_t eventTime);

    /**
     * Inject a key event into the Android InputChannel for a session.
     * Converts parameters to Android InputMessage (type=KEY) format and writes
     * to the server-side fd, symmetric to injectTouchEvent — including the
     * Fn05.A07 FINISHED-gated completion contract (see injectTouchEvent).
     *
     * @param sessionId  Window session ID
     * @param action     Android KeyEvent action (0=ACTION_DOWN, 1=ACTION_UP)
     * @param keyCode    Android keyCode (already mapped from OH, e.g. BACK=4)
     * @param metaState  Android meta state bitmask (0 if none)
     * @param downTime   Timestamp of the ACTION_DOWN in nanoseconds
     * @param eventTime  Timestamp of this event in nanoseconds
     * @param ohEventId  OH MMI InputEvent::GetId() of the source event
     * @param markProcessed  Thunk emitting OH MarkProcessed for the event
     * @return same contract as injectTouchEvent
     */
    int32_t injectKeyEvent(int32_t sessionId, int32_t action,
                            int32_t keyCode, int32_t metaState,
                            int64_t downTime, int64_t eventTime,
                            int64_t ohEventId,
                            input::MarkProcessedThunk markProcessed);

    /**
     * Set JNI context for callbacks to Java layer.
     */
    void setJavaVM(JavaVM* jvm) { jvm_ = jvm; }

    /**
     * Subscribe to OH MMI input events for the given window session.
     *
     * Called once per process from createSession after the window is added.
     * Internally instantiates an MMI::IInputEventConsumer subclass and calls
     * MMI::InputManager::GetInstance()->SetWindowInputEventConsumer to register
     * it with the MMI service. The MMI service then dispatches PointerEvent /
     * KeyEvent / AxisEvent to the consumer in this process; the consumer
     * forwards them to injectTouchEvent / injectKeyEvent, routing each event to
     * the target window session by event->GetAgentWindowId() (OH's focus
     * decision) — mirroring OH InputTransferStation.
     *
     * Idempotent — the process-level consumer is registered only once.
     *
     * Implements the missing piece identified in
     * doc/Input_Adapter_design.html §3.3.4 / §3.3.5.
     *
     * @param sessionId  Window session ID that this process's input events
     *                   should be routed to.
     */
    void subscribeMmi(int32_t sessionId);

    /**
     * Whether the given window/session id is a live adapter window session.
     * The MMI consumer uses this to drop events whose OH GetAgentWindowId()
     * does not map to one of our windows (mirrors OH InputTransferStation
     * dropping events for unknown windowIds).
     */
    bool isKnownSession(int32_t sessionId);

private:
    OHInputBridge() = default;
    ~OHInputBridge() = default;

    struct SessionInput {
        int serverFd = -1;      // Android server-side InputChannel fd
        int ohInputFd = -1;     // OH input event fd
        uint32_t seq = 0;       // Sequence number for InputPublisher protocol
        // Fn05.A07: window generation bound to this fd at registration.
        // FINISHED messages read from this fd are attributed to THIS
        // generation (never the session's current one), so a stale FINISHED
        // from a previous channel cannot complete a new-generation token
        // when seq numbers restart after re-registration.
        std::string generation;
    };

    JavaVM* jvm_ = nullptr;
    std::mutex mutex_;
    std::unordered_map<int32_t, SessionInput> sessions_;

    // OH input event monitoring
    std::atomic<bool> monitoring_{false};
    std::thread monitorThread_;

    // Fn05.A07: completion router driving the FINISHED-gated token ledger.
    // Session open/close rotate and tear down window generations; accepted
    // events hold a MarkProcessed thunk that is invoked only after the
    // matching Android FINISHED is observed by the ACK monitor.
    //
    // Deadline: 30 s.  OH's own ANR window (~5 s) stays the truthful
    // not-responding signal; the ledger deadline exists only to bound token
    // hygiene and MUST exceed the DESIGN P2 oracle (main thread blocked
    // 12 s, real FINISHED still completes).  Per-device tuning is an
    // explicit open item (IMPLEMENTATION.yaml blockers).
    input::OhEventCompletionRouter completionRouter_{
        input::LedgerConfig{30'000'000'000LL}};

    // OH InputEvent::GetId() is int32.  Synthetic identities start below that
    // range and monotonically decrease, so they cannot collide with a real OH
    // event in the same window generation.
    std::atomic<int64_t> nextSyntheticEventId_{-2147483649LL};

    // ACK monitor: polls all server fds for the FINISHED messages
    // ViewRootImpl's InputConsumer writes back after consuming an InputEvent
    // and forwards them to completionRouter_ (Fn05.A07).  This monitor is
    // load-bearing: it is the only path authorized to complete a ledger
    // token and release the gated OH MarkProcessed.
    std::atomic<bool> ackMonitoring_{false};
    std::thread ackThread_;

    // MMI consumer subscription state (single per process), mirroring OH's
    // InputTransferStation: ONE process-level SetWindowInputEventConsumer; the
    // consumer routes each event to the per-window InputChannel by reading
    // event->GetAgentWindowId() (== our sessionId, since sessionId==windowId).
    // No cached "active session" — input follows OH's own focus decision, so
    // resume / multi-Activity back-stack pop are handled automatically.
    std::shared_ptr<OHOS::MMI::IInputEventConsumer> mmiConsumer_;
    std::shared_ptr<OHOS::AppExecFwk::EventHandler> mmiEventHandler_;
    std::atomic<bool> mmiSubscribed_{false};

    /**
     * Write an InputMessage to the server fd.
     * Constructs a minimal InputMessage struct for a single-pointer MotionEvent.
     */
    int writeMotionEvent(int fd, uint32_t seq, int32_t action,
                          float x, float y,
                          int64_t downTime, int64_t eventTime);

    /**
     * Write an Android InputMessage (type=KEY) to the server fd.
     * Constructs a Body::Key struct matching AOSP 14 wire layout.
     */
    int writeKeyEvent(int fd, uint32_t seq, int32_t action,
                       int32_t keyCode, int32_t metaState,
                       int64_t downTime, int64_t eventTime);

    /**
     * Monitor thread: polls OH input fds and forwards events.
     */
    void monitorOHInputEvents();

    /**
     * ACK monitor thread: polls all server fds for FINISHED messages written
     * back by ViewRootImpl's InputConsumer and forwards them to the Fn05.A07
     * completion router; also drives the router's FINISHED-deadline scan.
     */
    void monitorAcks();
};

}  // namespace oh_adapter

#endif  // OH_INPUT_BRIDGE_H
