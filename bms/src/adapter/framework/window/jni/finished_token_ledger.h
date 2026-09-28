/*
 * finished_token_ledger.h
 *
 * Fn05.A07 FINISHED-gated input receipt token ledger.
 *
 * Holds the completion boundary for a single input event that crosses the
 * OpenHarmony MMI/WMS -> Bridge -> Android AOSP input stack boundary.
 *
 * Invariant: MarkProcessed(oh_event_id) is never emitted before the matching
 * Android InputMessage::Type::FINISHED(seq) is observed, except through the
 * explicit timeout/failure paths.
 *
 * This header is host-testable and does not depend on OH or AOSP headers.
 */

#ifndef OH_ADAPTER_FINISHED_TOKEN_LEDGER_H
#define OH_ADAPTER_FINISHED_TOKEN_LEDGER_H

#include <chrono>
#include <cstdint>
#include <functional>
#include <mutex>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace oh_adapter {
namespace input {

/** Token lifecycle states. */
enum class TokenState {
    IDLE,
    ARMED,
    FINISHED_RECEIVED,
    PROCESSED_ACKED,
    TIMEOUT,
    CANCELLED,
};

/** Terminal reasons recorded in the evidence row. */
struct TerminalReason {
    static constexpr const char* FINISHED = "FINISHED";
    static constexpr const char* TIMEOUT = "TIMEOUT";
    static constexpr const char* CANCELLED = "CANCELLED";
    static constexpr const char* DUPLICATE_FINISHED = "DUPLICATE_FINISHED";
    static constexpr const char* WRONG_GENERATION = "WRONG_GENERATION";
    static constexpr const char* LEDGER_COLLISION = "LEDGER_COLLISION";
    static constexpr const char* UNKNOWN_SEQ = "UNKNOWN_SEQ";
    static constexpr const char* PUBLISH_REJECT = "PUBLISH_REJECT";
};

/** Evidence row for a single token. */
struct LedgerRow {
    std::string generation;
    int64_t oh_event_id = -1;
    uint32_t android_seq = 0;
    int64_t android_finished_time_ns = -1;
    // Wall time of the MarkProcessed callback; -1 when MarkProcessed was
    // never emitted for this row (TIMEOUT/CANCELLED/diagnostic rows).
    int64_t oh_processed_time_ns = -1;
    int64_t callback_tid = -1;
    // The `handled` bit from the Android FINISHED receipt (-1 when the row
    // does not originate from a FINISHED message).  DESIGN.md §10 requires
    // recording it for every FINISHED receipt.
    int handled = -1;
    // Publish (channel write) result code recorded on PUBLISH_REJECT rows
    // (DESIGN.md §5 diagnostic); 0 when not applicable.
    int64_t publish_rc = 0;
    std::string terminal_reason;
};

/**
 * In-flight token.  Internal to the ledger; exposed only through diagnostics.
 */
struct Token {
    std::string generation;
    int64_t oh_event_id = -1;
    uint32_t android_seq = 0;
    TokenState state = TokenState::IDLE;
    int64_t deadline_ns = -1;
    int64_t finished_time_ns = -1;
    int64_t processed_time_ns = -1;
    int64_t callback_tid = -1;
    int handled = -1;
    std::string terminal_reason;
};

/**
 * Callback invoked when the ledger is authorized to emit MarkProcessed.
 * The implementation must call OH MMI MarkProcessed(event_id) and must not
 * fail silently.  The ledger records the time at which this callback returns.
 *
 * REENTRANCY CONTRACT: the callback runs while the ledger mutex is held
 * (this serializes emission against teardown so MarkProcessed can never be
 * emitted for an already-cancelled token).  The callback must therefore
 * NEVER call back into FinishedTokenLedger, OhEventCompletionRouter or
 * OHInputBridge — synchronous re-entry deadlocks.  OH MMI MarkProcessed is
 * an IPC call and satisfies this contract.
 */
using MarkProcessedCallback =
    std::function<void(const std::string& generation, int64_t oh_event_id)>;

/**
 * Clock source used to capture wall time after the MarkProcessed callback
 * returns.  Injectable for deterministic host testing.
 */
using LedgerClock = std::function<int64_t()>;

/**
 * Configuration for the ledger.
 */
struct LedgerConfig {
    /** Maximum time to wait for FINISHED after arming, in nanoseconds.
     *  Must be positive and finite; the ledger constructor throws
     *  std::invalid_argument otherwise (fail-closed, DESIGN.md §9.5). */
    int64_t max_finished_wait_ns = 5'000'000'000LL;  // 5 s

    /** Clock returning nanoseconds. Defaults to steady_clock. */
    LedgerClock clock = []() {
        return std::chrono::duration_cast<std::chrono::nanoseconds>(
                   std::chrono::steady_clock::now().time_since_epoch())
            .count();
    };
};

/**
 * FINISHED-gated token ledger.
 *
 * Thread-safe.  All public methods may be called concurrently.
 */
class FinishedTokenLedger {
public:
    explicit FinishedTokenLedger(LedgerConfig config,
                                 MarkProcessedCallback mark_processed_cb);

    /**
     * Accept an OH event into the ledger.
     *
     * Creates an IDLE token for (generation, oh_event_id).  Returns false and
     * records a LEDGER_COLLISION diagnostic row if a token already exists for
     * that pair, or if the generation was already torn down.
     */
    bool acceptEvent(const std::string& generation, int64_t oh_event_id);

    /**
     * Arm a token: bind it to an Android seq and start the FINISHED timer.
     *
     * Precondition: an IDLE token for (generation, oh_event_id) exists.
     * Postcondition: token moves to ARMED with deadline = now + max wait.
     *
     * Returns false if:
     *  - no IDLE token exists for (generation, oh_event_id)
     *  - (generation, oh_event_id) or (generation, android_seq) is already
     *    bound to another token (LEDGER_COLLISION)
     */
    bool arm(const std::string& generation,
             int64_t oh_event_id,
             uint32_t android_seq,
             int64_t now_ns);

    /**
     * Notify the ledger that Android has returned FINISHED for a seq.
     *
     * If a matching ARMED token exists, records the finish time, invokes the
     * MarkProcessed callback, and tombstones the token as PROCESSED_ACKED.
     *
     * Otherwise records a failure row and drops the FINISHED:
     *  - WRONG_GENERATION: the generation was torn down, or the seq is bound
     *    to a live token in a different generation (DESIGN.md oracle N3).
     *  - DUPLICATE_FINISHED: the seq already completed a token.
     *  - UNKNOWN_SEQ: the seq is not live-bound anywhere (never seen, or the
     *    matching token is already terminal TIMEOUT/CANCELLED).
     */
    void onFinished(const std::string& generation,
                    uint32_t android_seq,
                    int64_t now_ns,
                    int64_t callback_tid,
                    int handled = -1);

    /**
     * Scan for tokens whose FINISHED deadline has expired.
     *
     * Transitions matching ARMED tokens to TIMEOUT.  Does not emit
     * MarkProcessed for timed-out tokens.
     *
     * When `timed_out` is non-null, the (generation, oh_event_id) of every
     * token that transitioned to TIMEOUT in this call is appended to it, so
     * the integrating bridge can release any per-event resources it holds
     * for those tokens.  Existing single-argument callers are unaffected.
     */
    void scanTimeouts(
        int64_t now_ns,
        std::vector<std::pair<std::string, int64_t>>* timed_out = nullptr);

    /**
     * Teardown all tokens belonging to a generation.
     *
     * Non-terminal tokens (IDLE, ARMED, FINISHED_RECEIVED) transition to
     * CANCELLED.  Late FINISHED messages for this generation are reported as
     * WRONG_GENERATION.
     */
    void teardownGeneration(const std::string& generation, int64_t now_ns);

    /**
     * Explicitly cancel a single event by OH event id.
     *
     * Used for PUBLISH_REJECT or other per-event failure paths.  If the token
     * is non-terminal, transitions it to CANCELLED and records the given
     * terminal reason.
     *
     * The reason must be one of the TerminalReason constants (DESIGN.md
     * invariant 6); an invalid reason is rejected fail-closed: no state
     * change, no evidence row, returns false.  Returns true when the token
     * was cancelled by this call.
     */
    bool cancelEvent(const std::string& generation,
                     int64_t oh_event_id,
                     int64_t now_ns,
                     const std::string& reason,
                     int64_t publish_rc = 0);

    /** Return true if reason is one of the TerminalReason constants. */
    static bool IsValidTerminalReason(const std::string& reason);

    /** Return a copy of the evidence rows for independent verification. */
    std::vector<LedgerRow> getRows() const;

    /** Return the number of in-flight (non-terminal) tokens. */
    size_t inFlightCount() const;

private:
    mutable std::mutex mutex_;
    LedgerConfig config_;
    MarkProcessedCallback mark_processed_cb_;

    struct GenerationState {
        std::unordered_map<int64_t, Token> by_oh_event_id;
        // seq -> oh_event_id lookup; by_oh_event_id is the stable owner.
        std::unordered_map<uint32_t, int64_t> by_seq;
    };

    std::unordered_map<std::string, GenerationState> generations_;
    std::unordered_set<std::string> torn_down_generations_;
    std::vector<LedgerRow> rows_;

    bool isTerminalState(TokenState state) const;
    // True when android_seq is bound to a non-terminal token in a live
    // generation other than `generation`.  Caller must hold mutex_.
    bool boundLiveElsewhere(const std::string& generation,
                            uint32_t android_seq) const;
    void transitionToTerminal(Token& token,
                              TokenState terminal_state,
                              int64_t now_ns,
                              const std::string& reason,
                              int64_t publish_rc = 0);
    void emitMarkProcessed(Token& token, int64_t now_ns);
};

}  // namespace input
}  // namespace oh_adapter

#endif  // OH_ADAPTER_FINISHED_TOKEN_LEDGER_H
