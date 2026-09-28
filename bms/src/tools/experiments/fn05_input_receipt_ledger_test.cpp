#include <cstdlib>
#include <iostream>
#include <string>

#include "../../src/adapter/framework/window/jni/input_receipt_ledger.h"

namespace {

void require(bool condition, const std::string& label) {
    if (!condition) {
        std::cerr << "FAIL " << label << '\n';
        std::exit(1);
    }
    std::cout << "PASS " << label << '\n';
}

}  // namespace

int main() {
    using oh_adapter::InputReceiptKey;
    using oh_adapter::InputReceiptLedger;

    InputReceiptLedger ledger;
    const auto now = InputReceiptLedger::Clock::now();
    int completionCount = 0;
    bool handledValue = false;

    const InputReceiptKey original{34, 7, 101};
    require(ledger.arm(
                original,
                [&](bool handled) {
                    ++completionCount;
                    handledValue = handled;
                },
                now + std::chrono::seconds(3)),
            "arm-first-token");
    require(!ledger.arm(original, [](bool) {}, now + std::chrono::seconds(3)),
            "reject-duplicate-arm");
    require(!ledger.take(InputReceiptKey{34, 8, 101}),
            "reject-wrong-generation");
    require(!ledger.take(InputReceiptKey{34, 7, 102}),
            "reject-wrong-sequence");

    auto completion = ledger.take(original);
    require(static_cast<bool>(completion), "take-exact-finished");
    completion(true);
    require(completionCount == 1 && handledValue,
            "complete-exactly-once");
    require(!ledger.take(original), "reject-duplicate-finished");
    require(ledger.size() == 0, "empty-after-terminal");

    const InputReceiptKey timeoutKey{34, 7, 103};
    require(ledger.arm(timeoutKey, [&](bool) { ++completionCount; },
                       now - std::chrono::milliseconds(1)),
            "arm-timeout-token");
    auto expired = ledger.expire(now);
    require(expired.size() == 1 && expired.front() == timeoutKey,
            "expire-withheld-finished");
    require(!ledger.take(timeoutKey), "reject-late-finished-after-timeout");
    require(completionCount == 1, "timeout-does-not-ack-oh-event");

    require(ledger.arm(InputReceiptKey{40, 9, 1}, [](bool) {},
                       now + std::chrono::seconds(3)),
            "arm-generation-token-1");
    require(ledger.arm(InputReceiptKey{40, 9, 2}, [](bool) {},
                       now + std::chrono::seconds(3)),
            "arm-generation-token-2");
    require(ledger.arm(InputReceiptKey{40, 10, 1}, [](bool) {},
                       now + std::chrono::seconds(3)),
            "arm-replacement-generation");
    require(ledger.dropGeneration(40, 9) == 2,
            "drop-teardown-generation");
    require(ledger.size() == 1, "preserve-replacement-generation");
    require(ledger.dropGeneration(40, 9) == 0,
            "teardown-idempotent");
    require(ledger.cancel(InputReceiptKey{40, 10, 1}),
            "cancel-publish-failure");
    require(!ledger.cancel(InputReceiptKey{40, 10, 1}),
            "cancel-idempotent");
    require(ledger.size() == 0, "ledger-finally-empty");

    std::cout << "VERDICT PASS fn05_input_receipt_ledger\n";
    return 0;
}
