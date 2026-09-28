/**
 * APK verifier socket protocol.
 *
 * Parent appspawn-x verifier slice runs on the same AppSpawnX socket but uses
 * a dedicated preamble magic to avoid ambiguity with existing appspawn msgs.
 */
#pragma once

#include <cstdint>
#include <cstddef>

namespace appspawnx {
namespace apkverify {

// Keep protocol tiny and fixed-width for host/device parity.
constexpr uint32_t kVerifyRequestMagic = 0x41504b56u; // 'APK V'
constexpr uint32_t kVerifyResponseMagic = 0x564f4b50u; // 'VOKP'
constexpr size_t kVerifyMaxResponse = 64 * 1024u;

// Request is sent as:
//   [u32 magic][u32 minScheme][u32 reserved][u32 reserved]
//   followed by one FD via SCM_RIGHTS.
#pragma pack(push, 4)
struct ApkVerifyRequestHeader {
    uint32_t magic;
    uint32_t minScheme;   // 2 => v2, 3 => v3 only
    uint32_t reserved1;
    uint32_t reserved2;
};

struct ApkVerifyResponseHeader {
    uint32_t magic;
    int32_t status;      // 0 = success, <0 = fail
    uint32_t payloadLen;  // number of raw verifier bytes in response payload
    uint32_t reserved;
};
#pragma pack(pop)

static_assert(sizeof(ApkVerifyRequestHeader) == 16, "Request header size mismatch");
static_assert(sizeof(ApkVerifyResponseHeader) == 16, "Response header size mismatch");

} // namespace apkverify
} // namespace appspawnx
