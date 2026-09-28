#ifndef OH_ADAPTER_INPUT_CONTRACT_HARNESS_H
#define OH_ADAPTER_INPUT_CONTRACT_HARNESS_H

#include "finished_token_ledger.h"

#include <cstdint>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace oh_adapter {
namespace input {

enum class RoutedInputKind {
    POINTER,
    KEY,
};

enum class AdmissionStatus {
    ADMITTED,
    UNKNOWN_WINDOW,
    STALE_GENERATION,
    HIDDEN_WINDOW,
    FOCUS_MISMATCH,
    MALFORMED_EVENT,
    LEDGER_REJECTED,
};

struct WindowRouteIdentity {
    int32_t session_id = -1;
    int32_t window_id = -1;
    int32_t display_id = -1;
    std::string generation;
    bool visible = false;
};

struct RoutedInputEvent {
    RoutedInputKind kind = RoutedInputKind::POINTER;
    int64_t oh_event_id = -1;
    int32_t target_window_id = -1;
    std::string target_generation;
    int64_t focus_epoch = -1;
    double window_x = 0.0;
    double window_y = 0.0;
};

struct AdmissionReceipt {
    AdmissionStatus status = AdmissionStatus::MALFORMED_EVENT;
    RoutedInputKind kind = RoutedInputKind::POINTER;
    int64_t oh_event_id = -1;
    int32_t target_window_id = -1;
    std::string target_generation;
    uint32_t android_seq = 0;
    std::string reason;

    bool admitted() const { return status == AdmissionStatus::ADMITTED; }
};

/**
 * Host/target-testable owner model for the Fn05 input seam.
 *
 * The class owns only admission and routing identity. FINISHED ownership stays
 * in FinishedTokenLedger, so the harness cannot create a second completion
 * writer. Pointer admission is target-window/generation based; key admission
 * additionally requires the current focus epoch for that display.
 */
class InputContractHarness {
public:
    explicit InputContractHarness(LedgerConfig config,
                                  MarkProcessedCallback mark_processed_cb);

    bool attachWindow(const WindowRouteIdentity& identity);
    bool setWindowVisible(int32_t window_id,
                          const std::string& generation,
                          bool visible);
    bool confirmFocus(int32_t display_id,
                      int32_t window_id,
                      const std::string& generation,
                      int64_t focus_epoch);
    bool closeWindow(int32_t window_id,
                     const std::string& generation,
                     int64_t now_ns);
    bool peerDied(int32_t window_id,
                  const std::string& generation,
                  int64_t now_ns);

    AdmissionReceipt admit(const RoutedInputEvent& event, int64_t now_ns);
    void onFinished(const std::string& generation,
                    uint32_t android_seq,
                    int64_t now_ns,
                    int64_t callback_tid,
                    int handled);
    void scanTimeouts(int64_t now_ns);

    std::vector<AdmissionReceipt> admissionReceipts() const;
    std::vector<LedgerRow> completionReceipts() const;
    size_t inFlightCount() const;

private:
    struct FocusIdentity {
        int32_t window_id = -1;
        std::string generation;
        int64_t epoch = -1;
    };

    mutable std::mutex mutex_;
    std::unordered_map<int32_t, WindowRouteIdentity> windows_;
    std::unordered_map<int32_t, FocusIdentity> focus_by_display_;
    std::unordered_map<std::string, uint32_t> next_seq_by_generation_;
    std::vector<AdmissionReceipt> admission_receipts_;
    FinishedTokenLedger completion_ledger_;

    AdmissionReceipt reject(const RoutedInputEvent& event,
                            AdmissionStatus status,
                            const std::string& reason);
};

}  // namespace input
}  // namespace oh_adapter

#endif  // OH_ADAPTER_INPUT_CONTRACT_HARNESS_H
