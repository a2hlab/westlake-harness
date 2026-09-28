#include "westlake_native_compat.h"

#include <stddef.h>
#include <stdint.h>

_Static_assert(UINTPTR_MAX == UINT64_MAX,
               "WLNC ABI v1 is a 64-bit process ABI");
_Static_assert(sizeof(WlncStatus) == 4, "WlncStatus ABI drift");
_Static_assert(sizeof(WlncReason) == 4, "WlncReason ABI drift");
_Static_assert(sizeof(WlncProcessState) == 4,
               "WlncProcessState ABI drift");
_Static_assert(sizeof(WlncThreadState) == 4, "WlncThreadState ABI drift");
_Static_assert(sizeof(WlncMechanism) == 4, "WlncMechanism ABI drift");

_Static_assert(sizeof(WlncResult) == 16, "WlncResult ABI drift");
_Static_assert(sizeof(WlncTargetIdentity) == 80,
               "WlncTargetIdentity ABI drift");
_Static_assert(sizeof(WlncPreverifiedCapabilityV1) == 192,
               "WlncPreverifiedCapabilityV1 ABI drift");
_Static_assert(sizeof(WlncForkSeed) == 32, "WlncForkSeed ABI drift");
_Static_assert(sizeof(WlncGuardSourceSample) == 24,
               "WlncGuardSourceSample ABI drift");
_Static_assert(sizeof(WlncAuditEvent) == 64, "WlncAuditEvent ABI drift");
_Static_assert(sizeof(WlncPlatformOps) == 40, "WlncPlatformOps ABI drift");
_Static_assert(sizeof(WlncLoadIdentity) == 64,
               "WlncLoadIdentity ABI drift");
_Static_assert(sizeof(WlncLoadPermit) == 40, "WlncLoadPermit ABI drift");
_Static_assert(sizeof(WlncAuditSnapshot) == 112,
               "WlncAuditSnapshot ABI drift");

_Static_assert(offsetof(WlncPreverifiedCapabilityV1, process_epoch) == 64,
               "capability process_epoch offset drift");
_Static_assert(offsetof(WlncPreverifiedCapabilityV1, profile_sha256) == 80,
               "capability profile offset drift");
_Static_assert(offsetof(WlncPreverifiedCapabilityV1, target) == 112,
               "capability target offset drift");
_Static_assert(offsetof(WlncAuditSnapshot, adapter_generation) == 32,
               "snapshot generation offset drift");
_Static_assert(offsetof(WlncAuditSnapshot, profile_sha256) == 80,
               "snapshot profile offset drift");

int WLNC_TestAbiLayoutCompilationUnit(void)
{
    return 0;
}
