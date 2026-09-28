/*
 * Pure-C ABI boundary around OpenHarmony's stock HAP-domain specialization.
 *
 * HapDomainInfo contains C++ objects and must be constructed by the same OH
 * toolchain/runtime family as libhap_restorecon.z.so.  appspawn-x therefore
 * passes only POD values across this boundary.  The security operation itself
 * remains the canonical HapContext::HapDomainSetcontext() path, including its
 * stock libselinux setcon() call; no direct procattr bypass is permitted here.
 */

#include "hap_restorecon.h"

#include <cstddef>
#include <cstdint>

extern "C" int WestLakeHapDomainSetContext(
    const char* apl, size_t aplLength,
    const char* packageName, size_t packageLength,
    uint64_t hapFlags, uint32_t uid)
{
    if (apl == nullptr || packageName == nullptr) {
        return -1;
    }

    HapDomainInfo info;
    info.apl.assign(apl, aplLength);
    info.packageName.assign(packageName, packageLength);
    info.hapFlags = hapFlags;
    info.uid = uid;

    HapContext context;
    return context.HapDomainSetcontext(info);
}
