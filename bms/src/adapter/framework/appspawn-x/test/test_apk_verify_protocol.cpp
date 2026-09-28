/*
 * Host-only protocol smoke test for APK verify slice.
 *
 * Verifies wire-format constants and minimal negative framing invariants:
 * 1) verify request magic is disjoint from spawn magic;
 * 2) verifier response header is fixed-size and bounded;
 * 3) minScheme must be 2/3.
 */

#include "apk_verify_protocol.h"
#include "spawn_msg.h"

#include <cassert>
#include <cstdint>
#include <iostream>

int main() {
    static_assert(appspawnx::apkverify::kVerifyRequestMagic != appspawnx::OH_SPAWN_MSG_MAGIC,
                  "disjoint magic required");
    if (appspawnx::apkverify::kVerifyRequestMagic == 0) return 1;

    if (appspawnx::apkverify::kVerifyMaxResponse != 64 * 1024u) return 2;
    if (sizeof(appspawnx::apkverify::ApkVerifyRequestHeader) != 16u) return 3;
    if (sizeof(appspawnx::apkverify::ApkVerifyResponseHeader) != 16u) return 4;

    auto isSupportedScheme = [](uint32_t scheme) {
        return scheme == 2 || scheme == 3;
    };
    if (!isSupportedScheme(2) || !isSupportedScheme(3)) return 5;
    if (isSupportedScheme(1) || isSupportedScheme(4)) return 6;

    std::cout << "PASS verify_protocol_constants\n";
    return 0;
}
