#include "test_fixture_signing.h"

#include <stddef.h>
#include <stdint.h>

static const uint8_t kFixtureOnlyKey[32] = {
    UINT8_C(0x7d), UINT8_C(0x21), UINT8_C(0xc4), UINT8_C(0x09),
    UINT8_C(0x8a), UINT8_C(0x53), UINT8_C(0xee), UINT8_C(0x16),
    UINT8_C(0x94), UINT8_C(0x3b), UINT8_C(0x68), UINT8_C(0xd1),
    UINT8_C(0x2f), UINT8_C(0xb7), UINT8_C(0x40), UINT8_C(0x5c),
    UINT8_C(0xa2), UINT8_C(0x0e), UINT8_C(0x39), UINT8_C(0xf5),
    UINT8_C(0x61), UINT8_C(0x87), UINT8_C(0xdc), UINT8_C(0x24),
    UINT8_C(0x4a), UINT8_C(0x9f), UINT8_C(0x13), UINT8_C(0x72),
    UINT8_C(0xe8), UINT8_C(0x35), UINT8_C(0xb0), UINT8_C(0x66),
};

static void ComputeTestSeal(const WlafFixturePermitV1 *permit,
                            uint8_t output[WLAF_SIGNATURE_SIZE])
{
    const uint8_t *bytes = (const uint8_t *)(const void *)permit;
    const size_t signed_size = offsetof(WlafFixturePermitV1, signature);
    uint64_t lanes[8] = {
        UINT64_C(0xcbf29ce484222325), UINT64_C(0x9e3779b97f4a7c15),
        UINT64_C(0x6a09e667f3bcc909), UINT64_C(0xbb67ae8584caa73b),
        UINT64_C(0x3c6ef372fe94f82b), UINT64_C(0xa54ff53a5f1d36f1),
        UINT64_C(0x510e527fade682d1), UINT64_C(0x1f83d9abfb41bd6b),
    };
    size_t index;
    size_t lane;
    for (index = 0; index < signed_size; ++index) {
        lane = index & 7U;
        lanes[lane] ^= (uint64_t)(bytes[index] ^
                                  kFixtureOnlyKey[index & 31U]);
        lanes[lane] *= UINT64_C(0x100000001b3);
        lanes[lane] ^= lanes[(lane + 3U) & 7U] >> 11;
    }
    for (lane = 0; lane < 8U; ++lane) {
        uint64_t value = lanes[lane] ^
                         (UINT64_C(0x9e3779b97f4a7c15) * (lane + 1U));
        size_t byte_index;
        for (byte_index = 0; byte_index < 8U; ++byte_index) {
            output[lane * 8U + byte_index] =
                (uint8_t)(value >> (byte_index * 8U));
        }
    }
}

void WLAF_TestFixtureSign(WlafFixturePermitV1 *permit)
{
    size_t index;
    for (index = 0; index < WLAF_SIGNATURE_SIZE; ++index) {
        permit->signature[index] = UINT8_C(0);
    }
    ComputeTestSeal(permit, permit->signature);
}

int WLAF_TestFixtureVerify(const WlafFixturePermitV1 *permit)
{
    uint8_t expected[WLAF_SIGNATURE_SIZE];
    uint8_t difference = UINT8_C(0);
    size_t index;
    ComputeTestSeal(permit, expected);
    for (index = 0; index < WLAF_SIGNATURE_SIZE; ++index) {
        difference = (uint8_t)(difference |
                               (uint8_t)(expected[index] ^
                                         permit->signature[index]));
    }
    for (index = 0; index < WLAF_SIGNATURE_SIZE; ++index) {
        expected[index] = UINT8_C(0);
    }
    return difference == UINT8_C(0) ? 1 : 0;
}
