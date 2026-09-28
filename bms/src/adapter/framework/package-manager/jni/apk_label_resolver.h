#ifndef OH_ADAPTER_APK_LABEL_RESOLVER_H
#define OH_ADAPTER_APK_LABEL_RESOLVER_H

#include <cstdint>
#include <string>

namespace oh_adapter {

// Android label precedence for one manifest item: a literal value wins, then
// a resource reference is resolved from its owning APK/framework table, and
// finally the caller-provided application/package fallback is used.
std::string ResolveApkLabel(const std::string& apkPath,
    const std::string& literal, uint32_t resourceId,
    const std::string& fallback);

}  // namespace oh_adapter

#endif  // OH_ADAPTER_APK_LABEL_RESOLVER_H
