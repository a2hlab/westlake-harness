#ifndef OH_ADAPTER_APK_NATIVE_INVENTORY_H
#define OH_ADAPTER_APK_NATIVE_INVENTORY_H
#include "apk_native_inventory_names.h"
#include <cstdint>

namespace oh_adapter {
struct ApkNativeInventoryLimits {
    uint64_t maxApkBytes = 2ULL * 1024 * 1024 * 1024;
    uint64_t maxEntryBytes = 256ULL * 1024 * 1024;
    uint64_t maxTotalNativeBytes = 1024ULL * 1024 * 1024;
    uint64_t maxEntries = 100000;
};
struct NativeInventoryProfile {
    NativeAbiProfile abis;
    uint64_t pageSize = 0; // Actual runtime loader page size, never inferred from the host.
};
struct ApkNativeArtifact {
    std::string entryName, abi, entrySha256;
    uint64_t dataOffset = 0, compressedSize = 0, uncompressedSize = 0;
    uint16_t compressionMethod = 0;
    bool supportedByProfile = false;
    bool directlyLoadable = false; // STORE + aligned; this is not an install verdict.
    std::optional<package_transaction::ElfPrepassFacts> elfFacts;
};
enum class NativeInventoryVerdict {
    MATCHED_NATIVE, NO_NATIVE, NO_MATCHING_ABIS, PROFILE_UNAVAILABLE,
    INVALID_INPUT, FD_NOT_SEALED, DIGEST_MISMATCH, CORRUPT_APK,
    INVALID_ENTRY, ELF_REJECTED, LIMIT_EXCEEDED, IO_ERROR,
};
struct ApkNativeInventory {
    NativeInventoryVerdict verdict = NativeInventoryVerdict::INVALID_INPUT;
    std::string reason, apkSha256;
    uint64_t apkByteLength = 0;
    std::vector<ApkNativeArtifact> artifacts;
    std::optional<NativeEntryVerdict> entryVerdict;
    std::optional<package_transaction::ElfPrepassVerdict> elfVerdict;
};
// Borrows a sealed verified APK FD for this call; never opens a path, installs,
// extracts to disk, selects primary/secondary ABI, or closes the caller's FD.
// Errors publish no partial inventory. NO_MATCHING_ABIS retains observed facts.
ApkNativeInventory ReadApkNativeInventory(int sealedFd, uint64_t expectedLength,
    const std::string& expectedSha256, const NativeInventoryProfile& profile,
    const ApkNativeInventoryLimits& limits = {});
}
#endif
