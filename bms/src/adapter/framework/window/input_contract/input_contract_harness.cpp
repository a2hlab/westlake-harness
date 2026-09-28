#include "input_contract_harness.h"

#include <cmath>
#include <utility>

namespace oh_adapter {
namespace input {

InputContractHarness::InputContractHarness(
    LedgerConfig config,
    MarkProcessedCallback mark_processed_cb)
    : completion_ledger_(std::move(config), std::move(mark_processed_cb)) {}

bool InputContractHarness::attachWindow(
    const WindowRouteIdentity& identity) {
    if (identity.session_id < 0 || identity.window_id < 0 ||
        identity.display_id < 0 || identity.generation.empty()) {
        return false;
    }
    std::lock_guard<std::mutex> lock(mutex_);
    auto existing = windows_.find(identity.window_id);
    if (existing != windows_.end()) {
        return false;
    }
    for (const auto& entry : windows_) {
        if (entry.second.session_id == identity.session_id) {
            return false;
        }
    }
    windows_[identity.window_id] = identity;
    next_seq_by_generation_.try_emplace(identity.generation, 0);
    return true;
}

bool InputContractHarness::setWindowVisible(
    int32_t window_id,
    const std::string& generation,
    bool visible) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = windows_.find(window_id);
    if (it == windows_.end() || it->second.generation != generation) {
        return false;
    }
    it->second.visible = visible;
    if (!visible) {
        auto focus_it = focus_by_display_.find(it->second.display_id);
        if (focus_it != focus_by_display_.end() &&
            focus_it->second.window_id == window_id &&
            focus_it->second.generation == generation) {
            focus_by_display_.erase(focus_it);
        }
    }
    return true;
}

bool InputContractHarness::confirmFocus(
    int32_t display_id,
    int32_t window_id,
    const std::string& generation,
    int64_t focus_epoch) {
    if (focus_epoch < 0) {
        return false;
    }
    std::lock_guard<std::mutex> lock(mutex_);
    auto window_it = windows_.find(window_id);
    if (window_it == windows_.end() ||
        window_it->second.generation != generation ||
        window_it->second.display_id != display_id ||
        !window_it->second.visible) {
        return false;
    }
    auto focus_it = focus_by_display_.find(display_id);
    if (focus_it != focus_by_display_.end() &&
        focus_epoch <= focus_it->second.epoch) {
        return false;
    }
    focus_by_display_[display_id] =
        FocusIdentity{window_id, generation, focus_epoch};
    return true;
}

bool InputContractHarness::closeWindow(
    int32_t window_id,
    const std::string& generation,
    int64_t now_ns) {
    int32_t display_id = -1;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = windows_.find(window_id);
        if (it == windows_.end() || it->second.generation != generation) {
            return false;
        }
        display_id = it->second.display_id;
        windows_.erase(it);
        auto focus_it = focus_by_display_.find(display_id);
        if (focus_it != focus_by_display_.end() &&
            focus_it->second.window_id == window_id &&
            focus_it->second.generation == generation) {
            focus_by_display_.erase(focus_it);
        }
    }
    completion_ledger_.teardownGeneration(generation, now_ns);
    return true;
}

bool InputContractHarness::peerDied(
    int32_t window_id,
    const std::string& generation,
    int64_t now_ns) {
    return closeWindow(window_id, generation, now_ns);
}

AdmissionReceipt InputContractHarness::admit(
    const RoutedInputEvent& event,
    int64_t now_ns) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (event.oh_event_id < 0 || event.target_window_id < 0 ||
        event.target_generation.empty() ||
        (event.kind == RoutedInputKind::POINTER &&
         (!std::isfinite(event.window_x) || !std::isfinite(event.window_y)))) {
        return reject(event, AdmissionStatus::MALFORMED_EVENT,
                      "MALFORMED_EVENT");
    }

    auto window_it = windows_.find(event.target_window_id);
    if (window_it == windows_.end()) {
        return reject(event, AdmissionStatus::UNKNOWN_WINDOW,
                      "UNKNOWN_WINDOW");
    }
    const WindowRouteIdentity& window = window_it->second;
    if (window.generation != event.target_generation) {
        return reject(event, AdmissionStatus::STALE_GENERATION,
                      "STALE_GENERATION");
    }
    if (!window.visible) {
        return reject(event, AdmissionStatus::HIDDEN_WINDOW,
                      "HIDDEN_WINDOW");
    }

    if (event.kind == RoutedInputKind::KEY) {
        auto focus_it = focus_by_display_.find(window.display_id);
        if (focus_it == focus_by_display_.end() ||
            focus_it->second.window_id != window.window_id ||
            focus_it->second.generation != window.generation ||
            focus_it->second.epoch != event.focus_epoch) {
            return reject(event, AdmissionStatus::FOCUS_MISMATCH,
                          "FOCUS_MISMATCH");
        }
    }

    if (!completion_ledger_.acceptEvent(window.generation,
                                        event.oh_event_id)) {
        return reject(event, AdmissionStatus::LEDGER_REJECTED,
                      "LEDGER_REJECTED");
    }
    uint32_t& next_seq = next_seq_by_generation_[window.generation];
    ++next_seq;
    if (!completion_ledger_.arm(window.generation, event.oh_event_id,
                                next_seq, now_ns)) {
        return reject(event, AdmissionStatus::LEDGER_REJECTED,
                      "LEDGER_REJECTED");
    }

    AdmissionReceipt receipt;
    receipt.status = AdmissionStatus::ADMITTED;
    receipt.kind = event.kind;
    receipt.oh_event_id = event.oh_event_id;
    receipt.target_window_id = event.target_window_id;
    receipt.target_generation = event.target_generation;
    receipt.android_seq = next_seq;
    receipt.reason = "ADMITTED";
    admission_receipts_.push_back(receipt);
    return receipt;
}

void InputContractHarness::onFinished(
    const std::string& generation,
    uint32_t android_seq,
    int64_t now_ns,
    int64_t callback_tid,
    int handled) {
    completion_ledger_.onFinished(generation, android_seq, now_ns,
                                  callback_tid, handled);
}

void InputContractHarness::scanTimeouts(int64_t now_ns) {
    completion_ledger_.scanTimeouts(now_ns);
}

std::vector<AdmissionReceipt>
InputContractHarness::admissionReceipts() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return admission_receipts_;
}

std::vector<LedgerRow> InputContractHarness::completionReceipts() const {
    return completion_ledger_.getRows();
}

size_t InputContractHarness::inFlightCount() const {
    return completion_ledger_.inFlightCount();
}

AdmissionReceipt InputContractHarness::reject(
    const RoutedInputEvent& event,
    AdmissionStatus status,
    const std::string& reason) {
    AdmissionReceipt receipt;
    receipt.status = status;
    receipt.kind = event.kind;
    receipt.oh_event_id = event.oh_event_id;
    receipt.target_window_id = event.target_window_id;
    receipt.target_generation = event.target_generation;
    receipt.reason = reason;
    admission_receipts_.push_back(receipt);
    return receipt;
}

}  // namespace input
}  // namespace oh_adapter
