#include "input_contract_harness.h"
#include "typed_service_capability.h"

#include <cstdlib>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

namespace {

void require(bool condition, const std::string& label) {
    if (!condition) {
        std::cerr << "FAIL " << label << '\n';
        std::exit(EXIT_FAILURE);
    }
    std::cout << "PASS " << label << '\n';
}

int countTerminal(const std::vector<oh_adapter::input::LedgerRow>& rows,
                  const std::string& generation,
                  const std::string& reason) {
    int count = 0;
    for (const auto& row : rows) {
        if (row.generation == generation && row.terminal_reason == reason) {
            ++count;
        }
    }
    return count;
}

void testInputContract() {
    using namespace oh_adapter::input;

    std::vector<std::pair<std::string, int64_t>> processed;
    int64_t clock_ns = 1'000;
    InputContractHarness harness(
        LedgerConfig{
            100,
            [&clock_ns]() { return clock_ns; },
        },
        [&processed](const std::string& generation, int64_t event_id) {
            processed.emplace_back(generation, event_id);
        });

    require(harness.attachWindow({11, 101, 0, "W101-G1", true}),
            "input attach first window");
    require(harness.attachWindow({12, 102, 0, "W102-G1", true}),
            "input attach second window");
    require(harness.confirmFocus(0, 101, "W101-G1", 7),
            "input confirm focus epoch for first window");

    RoutedInputEvent pointer;
    pointer.kind = RoutedInputKind::POINTER;
    pointer.oh_event_id = 1001;
    pointer.target_window_id = 102;
    pointer.target_generation = "W102-G1";
    pointer.window_x = 17.5;
    pointer.window_y = 23.0;
    auto pointer_receipt = harness.admit(pointer, 1'000);
    require(pointer_receipt.admitted(),
            "pointer admission follows hit-test target, not key focus");
    harness.onFinished("W102-G1", pointer_receipt.android_seq,
                       1'010, 501, 1);
    require(processed.size() == 1 && processed[0].second == 1001,
            "pointer FINISHED emits exactly one OH receipt");

    RoutedInputEvent unfocused_key;
    unfocused_key.kind = RoutedInputKind::KEY;
    unfocused_key.oh_event_id = 1002;
    unfocused_key.target_window_id = 102;
    unfocused_key.target_generation = "W102-G1";
    unfocused_key.focus_epoch = 7;
    require(harness.admit(unfocused_key, 1'020).status ==
                AdmissionStatus::FOCUS_MISMATCH,
            "key rejects non-focused multiwindow target");

    RoutedInputEvent focused_key;
    focused_key.kind = RoutedInputKind::KEY;
    focused_key.oh_event_id = 1003;
    focused_key.target_window_id = 101;
    focused_key.target_generation = "W101-G1";
    focused_key.focus_epoch = 7;
    auto key_receipt = harness.admit(focused_key, 1'030);
    require(key_receipt.admitted(), "key admits exact focus epoch");
    harness.onFinished("W101-G1", key_receipt.android_seq,
                       1'040, 502, 0);
    require(processed.size() == 2 && processed[1].second == 1003,
            "key FINISHED emits independent OH receipt");

    require(harness.confirmFocus(0, 102, "W102-G1", 8),
            "focus moves to second window with newer epoch");
    unfocused_key.oh_event_id = 1004;
    require(harness.admit(unfocused_key, 1'050).status ==
                AdmissionStatus::FOCUS_MISMATCH,
            "stale focus epoch is rejected");
    unfocused_key.focus_epoch = 8;
    auto timeout_key = harness.admit(unfocused_key, 1'060);
    require(timeout_key.admitted(), "key admits current focus epoch");
    harness.scanTimeouts(1'161);
    require(processed.size() == 2, "timeout never fabricates OH receipt");
    require(countTerminal(harness.completionReceipts(), "W102-G1",
                          TerminalReason::TIMEOUT) == 1,
            "timeout is typed terminal");
    harness.onFinished("W102-G1", timeout_key.android_seq,
                       1'170, 503, 1);
    require(processed.size() == 2, "late FINISHED after timeout is dropped");

    RoutedInputEvent dying_pointer = pointer;
    dying_pointer.oh_event_id = 1005;
    auto dying_receipt = harness.admit(dying_pointer, 1'180);
    require(dying_receipt.admitted(), "event admitted before peer death");
    require(harness.peerDied(102, "W102-G1", 1'181),
            "peer death tears down exact window generation");
    harness.onFinished("W102-G1", dying_receipt.android_seq,
                       1'182, 504, 1);
    require(processed.size() == 2,
            "late FINISHED after peer death cannot ack successor");
    require(countTerminal(harness.completionReceipts(), "W102-G1",
                          TerminalReason::WRONG_GENERATION) >= 1,
            "death produces stale-generation diagnostic");

    require(harness.attachWindow({12, 102, 0, "W102-G2", true}),
            "same window id can attach as new generation");
    require(harness.confirmFocus(0, 102, "W102-G2", 9),
            "new generation obtains a new focus epoch");
    pointer.oh_event_id = 1006;
    pointer.target_generation = "W102-G2";
    auto replacement = harness.admit(pointer, 1'190);
    require(replacement.admitted(), "replacement generation accepts pointer");
    harness.onFinished("W102-G2", replacement.android_seq,
                       1'191, 505, 1);
    require(processed.size() == 3 &&
                processed.back().first == "W102-G2",
            "replacement generation completes independently");
    require(harness.inFlightCount() == 0,
            "input contract has no residual in-flight token");
}

oh_adapter::service::CapabilitySpec spec(
    std::string name,
    std::string descriptor,
    std::string schema,
    oh_adapter::service::ServicePlacement placement,
    std::initializer_list<const char*> methods,
    bool critical,
    bool death_aware) {
    oh_adapter::service::CapabilitySpec result;
    result.service_name = std::move(name);
    result.descriptor = std::move(descriptor);
    result.schema_hash = std::move(schema);
    result.placement = placement;
    for (const char* method : methods) {
        result.methods.emplace(method);
    }
    result.construction_critical = critical;
    result.death_aware = death_aware;
    result.timeout_ns = 100;
    return result;
}

oh_adapter::service::LookupRequest request(
    std::string id,
    std::string service_name,
    std::string descriptor,
    std::string schema_hash,
    std::string method,
    int64_t now_ns) {
    oh_adapter::service::LookupRequest result;
    result.request_id = std::move(id);
    result.service_name = std::move(service_name);
    result.descriptor = std::move(descriptor);
    result.schema_hash = std::move(schema_hash);
    result.method = std::move(method);
    result.caller = {20001, 3001, 0, 41};
    result.now_ns = now_ns;
    return result;
}

void testTypedServiceContract() {
    using namespace oh_adapter::service;

    TypedServiceCapabilityRegistry registry;
    require(registry.registerCapability(spec(
                "window", "android.view.IWindowManager", "schema-window-v1",
                ServicePlacement::OH_DIRECT,
                {"openSession", "requestFocus"}, true, true)),
            "service register window direct capability");
    require(registry.registerCapability(spec(
                "input_method", "com.android.internal.view.IInputMethodManager",
                "schema-ime-lookup-v1", ServicePlacement::LOCAL_ADAPTER,
                {"getInputMethodList", "startInputOrWindowGainedFocus"},
                true, false)),
            "service register input-method local typed capability");
    require(registry.registerCapability(spec(
                "package", "android.content.pm.IPackageManager",
                "schema-package-v1", ServicePlacement::PRIVILEGED_BROKER,
                {"getPackageInfo"}, true, true)),
            "service register package broker capability");
    require(registry.registerCapability(spec(
                "bluetooth", "android.bluetooth.IBluetoothManager",
                "schema-bluetooth-v1",
                ServicePlacement::EXPLICIT_UNSUPPORTED,
                {}, false, false)),
            "service register explicit unsupported capability");

    require(!registry.publishEndpoint(
                "window", "android.view.IWindowManager",
                "schema-window-v1",
                ServicePlacement::LOCAL_ADAPTER, 1),
            "service rejects placement shortcut");
    require(!registry.publishEndpoint(
                "window", "android.view.IWindowManager",
                "wrong-schema", ServicePlacement::OH_DIRECT, 1),
            "service rejects endpoint schema mismatch");
    require(registry.publishEndpoint(
                "window", "android.view.IWindowManager",
                "schema-window-v1",
                ServicePlacement::OH_DIRECT, 1),
            "service publishes exact window endpoint");
    require(registry.publishEndpoint(
                "input_method",
                "com.android.internal.view.IInputMethodManager",
                "schema-ime-lookup-v1",
                ServicePlacement::LOCAL_ADAPTER, 7),
            "service publishes exact input-method endpoint");
    require(registry.publishEndpoint(
                "package", "android.content.pm.IPackageManager",
                "schema-package-v1",
                ServicePlacement::PRIVILEGED_BROKER, 3),
            "service publishes exact package endpoint");
    require(registry.allConstructionCriticalReady(),
            "construction set is ready only with all typed endpoints");

    auto window_lookup = registry.beginLookup(request(
        "r-window", "window", "android.view.IWindowManager",
        "schema-window-v1",
        "requestFocus", 1'000));
    require(window_lookup.status == LookupStatus::IN_FLIGHT &&
                window_lookup.placement == ServicePlacement::OH_DIRECT,
            "window lookup preserves per-service placement");
    require(registry.completeLookup("r-window", 1, 1'050).status ==
                LookupStatus::BOUND,
            "window lookup completes on exact endpoint generation");

    auto ime_lookup = registry.beginLookup(request(
        "r-ime", "input_method",
        "com.android.internal.view.IInputMethodManager",
        "schema-ime-lookup-v1",
        "getInputMethodList", 1'100));
    require(ime_lookup.status == LookupStatus::IN_FLIGHT &&
                ime_lookup.placement == ServicePlacement::LOCAL_ADAPTER,
            "input-method lookup uses independent local route");
    require(registry.completeLookup("r-ime", 7, 1'201).status ==
                LookupStatus::TIMEOUT,
            "service timeout is a typed terminal");

    auto package_lookup = registry.beginLookup(request(
        "r-package", "package", "android.content.pm.IPackageManager",
        "schema-package-v1",
        "getPackageInfo", 1'300));
    require(package_lookup.status == LookupStatus::IN_FLIGHT,
            "package broker request enters in-flight");
    require(registry.endpointDied("package", 3),
            "service endpoint death tombstones broker generation");
    require(registry.completeLookup("r-package", 3, 1'310).status ==
                LookupStatus::STALE_GENERATION,
            "late completion after death cannot revive request");
    require(!registry.allConstructionCriticalReady(),
            "dead construction-critical endpoint removes readiness");
    require(registry.publishEndpoint(
                "package", "android.content.pm.IPackageManager",
                "schema-package-v1",
                ServicePlacement::PRIVILEGED_BROKER, 4),
            "service rebind requires newer endpoint generation");

    require(registry.beginLookup(request(
        "r-unknown", "sensor_privacy",
        "android.hardware.ISensorPrivacyManager",
        "schema-sensor-privacy-v1",
        "supportsSensorToggle", 1'400)).status ==
                LookupStatus::ABSENT,
            "unknown service has no universal fallback route");
    require(registry.beginLookup(request(
        "r-schema", "window", "wrong.descriptor",
        "schema-window-v1",
        "requestFocus", 1'400)).status ==
                LookupStatus::SCHEMA_MISMATCH,
            "descriptor mismatch fails before transport");
    require(registry.beginLookup(request(
                "r-schema-hash", "window",
                "android.view.IWindowManager", "wrong-schema",
                "requestFocus", 1'400)).status ==
                LookupStatus::SCHEMA_MISMATCH,
            "schema hash mismatch fails before transport");
    require(registry.beginLookup(request(
        "r-method", "window", "android.view.IWindowManager",
        "schema-window-v1",
        "unfrozenMethod", 1'400)).status ==
                LookupStatus::UNKNOWN_METHOD,
            "unknown method fails before transport");
    require(registry.beginLookup(request(
        "r-unsupported", "bluetooth",
        "android.bluetooth.IBluetoothManager",
        "schema-bluetooth-v1",
        "getAdapter", 1'400)).status ==
                LookupStatus::UNSUPPORTED,
            "declared unsupported service is explicit");
    require(registry.beginLookup(request(
        "r-window", "window", "android.view.IWindowManager",
        "schema-window-v1",
        "requestFocus", 1'500)).status ==
                LookupStatus::DUPLICATE_REQUEST,
            "request identity is single-use across endpoint generations");
}

}  // namespace

int main() {
    testInputContract();
    testTypedServiceContract();
    std::cout << "RESULT build_pass fn05_fn11_contract_harness\n";
    return EXIT_SUCCESS;
}
