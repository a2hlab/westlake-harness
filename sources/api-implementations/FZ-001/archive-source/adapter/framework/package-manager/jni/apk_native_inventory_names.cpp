#include "apk_native_inventory_names.h"
#include <algorithm>

namespace oh_adapter {
namespace {
NativeEntryResult Result(NativeEntryVerdict verdict, const std::string& reason)
{
    NativeEntryResult result;
    result.verdict = verdict;
    result.reason = reason;
    return result;
}
bool IsRegular(const ApkNativeEntryInput& entry)
{
    // The DOS directory bit is meaningful regardless of the creator OS.
    if ((entry.zipExternalAttributes & 0x10U) != 0) return false;
    const auto creator = entry.zipVersionMadeBy >> 8;
    if (creator == 3 || creator == 19) { // ZIP Unix / OS X encode POSIX file type.
        const auto type = (entry.zipExternalAttributes >> 16) & 0170000U;
        if (type != 0 && type != 0100000U) return false;
    }
    return true; // Unspecified type uses ZIP's ordinary file-entry semantics.
}
}
NativeEntryResult ValidateApkNativeEntry(const ApkNativeEntryInput& entry,
    const NativeAbiProfile& profile, std::set<std::string>& seenNativeNames)
{
    using V = NativeEntryVerdict;
    const auto& name = entry.entryName;
    if (name.empty() || name.size() > 4096 || name.front() == '/' ||
        std::any_of(name.begin(), name.end(), [](unsigned char c) {
            return c < 0x20 || c == 0x7f || c == '\\' || c == ':';
        })) return Result(V::INVALID_NAME, "ZIP entry name is empty, oversized or contains unsafe characters");
    const bool directory = name.back() == '/';
    const std::string canonical = directory ? name.substr(0, name.size() - 1) : name;
    std::vector<std::string> components;
    size_t start = 0;
    while (start <= canonical.size()) {
        const auto end = canonical.find('/', start);
        const auto part = canonical.substr(start, end == std::string::npos ? std::string::npos : end - start);
        if (part.empty() || part == "." || part == ".." || part.size() > 255)
            return Result(V::INVALID_NAME, "ZIP path is not canonical or exceeds component limits");
        components.push_back(part);
        if (end == std::string::npos) break;
        start = end + 1;
    }
    if (components.front() != "lib" || components.size() < 3)
        return Result(V::NOT_NATIVE, "Entry is outside the native library layout");
    const auto& file = components.back();
    if (file.size() <= 3 || file.compare(file.size() - 3, 3, ".so") != 0)
        return Result(V::NOT_NATIVE, "Entry is not a native shared object");
    if (components.size() != 3)
        return Result(V::INVALID_NAME, "Native entry must have exactly one ABI directory");
    if (directory || !IsRegular(entry))
        return Result(V::NON_REGULAR_ENTRY, "Native entry is not a regular ZIP file");
    if (!seenNativeNames.insert(canonical).second)
        return Result(V::DUPLICATE_ENTRY, "Duplicate canonical native entry");
    if (!profile.available)
        return Result(V::PROFILE_UNAVAILABLE, "Runtime ABI profile is unavailable");
    const auto& abi = components[1];
    if (std::find(profile.supportedAbis.begin(), profile.supportedAbis.end(), abi) == profile.supportedAbis.end())
        return Result(V::ABI_UNSUPPORTED, "Native entry ABI is absent from the runtime profile");
    const package_transaction::ElfPrepassInput elf{
        entry.apkSha256, canonical, abi, entry.entrySha256, entry.bytes};
    auto inspected = package_transaction::InspectElf(elf);
    if (!inspected.facts) {
        auto result = Result(V::ELF_REJECTED, inspected.reason);
        result.elfVerdict = inspected.verdict;
        return result;
    }
    auto result = Result(V::VALID_NATIVE, "Native entry name, file kind and actual ELF ABI validated");
    result.canonicalName = canonical;
    result.abi = abi;
    result.fileName = file;
    result.elfVerdict = inspected.verdict;
    result.elfFacts = std::move(inspected.facts);
    return result;
}
}
