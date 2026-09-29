#ifndef OH_ADAPTER_ELF_PREPASS_ANALYZER_H
#define OH_ADAPTER_ELF_PREPASS_ANALYZER_H
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace oh_adapter::package_transaction {
struct ElfPrepassInput {
    std::string apkSha256;
    std::string entryName;
    std::string abi;
    std::string expectedElfSha256;
    std::vector<uint8_t> bytes;
};
struct ElfLoadSegment {
    uint64_t offset = 0, virtualAddress = 0, fileSize = 0, memorySize = 0, alignment = 0;
    uint32_t flags = 0;
};
struct ElfSymbolRequirement { std::string name; bool weak = false; };
struct ElfPrepassFacts {
    std::string analyzerVersion;
    std::string apkSha256, entryName, abi, elfSha256;
    uint8_t elfClass = 0;
    uint16_t machine = 0;
    std::string soname;
    std::vector<ElfLoadSegment> loadSegments;
    std::vector<std::string> neededLibraries;
    std::vector<std::string> exportedSymbols;
    std::vector<ElfSymbolRequirement> requiredSymbols;
};
enum class ElfPrepassVerdict {
    ANALYZED, INVALID_INPUT, DIGEST_MISMATCH, MALFORMED_ELF,
    ABI_MISMATCH, DEPENDENCY_MISSING, SYMBOL_MISSING, INTERNAL_ERROR,
};
struct ElfPrepassResult {
    ElfPrepassVerdict verdict = ElfPrepassVerdict::INTERNAL_ERROR;
    std::string reason;
    std::optional<ElfPrepassFacts> facts;
};
// Inspection reads bytes only. The inventory owner supplies verified APK identity.
// Separate inspection permits collecting a whole same-ABI graph before resolving it.
ElfPrepassResult InspectElf(const ElfPrepassInput& input);
// Available dependency facts come from same-package inspection or the runtime profile.
// Neither function loads a library or performs installation side effects.
ElfPrepassResult AnalyzeElf(const ElfPrepassInput& input,
    const std::vector<ElfPrepassFacts>& availableLibraries);
}
#endif
