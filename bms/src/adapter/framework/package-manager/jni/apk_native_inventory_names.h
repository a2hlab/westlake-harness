#ifndef OH_ADAPTER_APK_NATIVE_INVENTORY_NAMES_H
#define OH_ADAPTER_APK_NATIVE_INVENTORY_NAMES_H
#include "elf_prepass_analyzer.h"
#include <set>
#include <string>
#include <vector>

namespace oh_adapter {
struct ApkNativeEntryInput {
    std::string entryName, apkSha256, entrySha256;
    std::vector<uint8_t> bytes;
    uint16_t zipVersionMadeBy = 0;
    uint32_t zipExternalAttributes = 0;
};
struct NativeAbiProfile {
    bool available = false;
    std::vector<std::string> supportedAbis;
};
enum class NativeEntryVerdict {
    VALID_NATIVE, NOT_NATIVE, INVALID_NAME, DUPLICATE_ENTRY,
    NON_REGULAR_ENTRY, PROFILE_UNAVAILABLE, ABI_UNSUPPORTED, ELF_REJECTED,
};
struct NativeEntryResult {
    NativeEntryVerdict verdict = NativeEntryVerdict::INVALID_NAME;
    std::string reason, canonicalName, abi, fileName;
    std::optional<package_transaction::ElfPrepassFacts> elfFacts;
    std::optional<package_transaction::ElfPrepassVerdict> elfVerdict;
};
// One invocation per archive entry. Seen names are local to that archive scan.
// Canonical native names are reserved before ABI/profile validation; callers
// abort an invalid scan rather than treating partial observations as inventory.
NativeEntryResult ValidateApkNativeEntry(const ApkNativeEntryInput& entry,
    const NativeAbiProfile& profile, std::set<std::string>& seenNativeNames);
}
#endif
