#include "apk_label_resolver.h"

#include "arsc_resolver.h"

namespace oh_adapter {

std::string ResolveApkLabel(const std::string& apkPath,
    const std::string& literal, uint32_t resourceId,
    const std::string& fallback)
{
    if (!literal.empty()) {
        return literal;
    }
    std::string resolved;
    if (resourceId != 0 &&
        ResolveApkResourceIdToString(apkPath, resourceId, resolved) &&
        !resolved.empty()) {
        return resolved;
    }
    return fallback;
}

}  // namespace oh_adapter
