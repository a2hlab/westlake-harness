#ifndef BRIDGE_FN01_TOPOLOGY_POLICY_H
#define BRIDGE_FN01_TOPOLOGY_POLICY_H

#include <cstdint>

namespace bridge::fn01::topology {

// Project-private experiment ID in OpenHarmony's vendor-reserved SA range.
// It must remain absent from the selected OH source baseline and target runtime
// before every experiment.
constexpr int32_t kProbeSaId = 0x0001F101;  // 127233
constexpr int32_t kVendorSaIdBegin = 0x00010000;
constexpr int32_t kVendorSaIdEnd = 0x00020000;
constexpr int32_t kPrimaryUserId = 0;

enum class ClaimVerdict {
    kAllow = 0,
    kClaimedUidMismatch = 1,
    kUnsupportedUser = 2,
};

inline ClaimVerdict EvaluateClaim(
    int32_t peerUid, int32_t claimedUid, int32_t claimedUser)
{
    if (claimedUid != peerUid) {
        return ClaimVerdict::kClaimedUidMismatch;
    }
    // Fn01 v1 is primary-user-only. The expected user is trusted service
    // configuration, not a value derived from or supplied by the DTO.
    if (claimedUser != kPrimaryUserId) {
        return ClaimVerdict::kUnsupportedUser;
    }
    return ClaimVerdict::kAllow;
}

inline const char *ClaimVerdictName(ClaimVerdict verdict)
{
    switch (verdict) {
        case ClaimVerdict::kAllow:
            return "ALLOW";
        case ClaimVerdict::kClaimedUidMismatch:
            return "CLAIMED_UID_MISMATCH";
        case ClaimVerdict::kUnsupportedUser:
            return "UNSUPPORTED_USER";
    }
    return "UNKNOWN";
}

static_assert(kProbeSaId >= kVendorSaIdBegin && kProbeSaId < kVendorSaIdEnd);
static_assert(kProbeSaId != 5502);

}  // namespace bridge::fn01::topology

#endif  // BRIDGE_FN01_TOPOLOGY_POLICY_H
