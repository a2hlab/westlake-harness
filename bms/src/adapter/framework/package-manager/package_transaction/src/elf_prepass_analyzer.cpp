#include "elf_prepass_analyzer.h"
#include "sha256.h"
#include <algorithm>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <utility>

namespace oh_adapter::package_transaction {
namespace {
constexpr uint64_t MAX_SYMBOLS = 1024 * 1024;
struct Failure : std::runtime_error {
    ElfPrepassVerdict verdict;
    Failure(ElfPrepassVerdict value, const std::string& reason)
        : std::runtime_error(reason), verdict(value) {}
};
void Check(bool condition, const char* reason)
{ if (!condition) throw Failure(ElfPrepassVerdict::MALFORMED_ELF, reason); }
bool IsDigest(const std::string& text)
{
    return text.size() == 64 && std::all_of(text.begin(), text.end(), [](char c) {
        return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
    });
}
std::string Digest(const std::vector<uint8_t>& bytes)
{
    unsigned char raw[32];
    sha256(bytes.data(), bytes.size(), raw);
    constexpr char hex[] = "0123456789abcdef";
    std::string out;
    for (unsigned char c : raw) { out.push_back(hex[c >> 4]); out.push_back(hex[c & 15]); }
    return out;
}
bool AbiMatches(const std::string& abi, uint8_t elfClass, uint16_t machine)
{
    if (abi == "armeabi" || abi == "armeabi-v7a") return elfClass == 1 && machine == 40;
    if (abi == "arm64-v8a") return elfClass == 2 && machine == 183;
    if (abi == "x86") return elfClass == 1 && machine == 3;
    if (abi == "x86_64") return elfClass == 2 && machine == 62;
    if (abi == "riscv64") return elfClass == 2 && machine == 243;
    return false;
}
class Reader {
public:
    explicit Reader(const std::vector<uint8_t>& bytes) : bytes_(bytes) {}
    void Range(uint64_t offset, uint64_t size) const
    { Check(offset <= bytes_.size() && size <= bytes_.size() - offset, "ELF file range is out of bounds"); }
    uint64_t Number(uint64_t offset, size_t width) const
    {
        Range(offset, width);
        uint64_t value = 0;
        for (size_t i = 0; i < width; ++i) value |= uint64_t{bytes_[offset + i]} << (8 * i);
        return value;
    }
    std::string String(uint64_t base, uint64_t size, uint64_t index) const
    {
        Range(base, size);
        Check(index < size, "ELF string index is out of bounds");
        uint64_t end = index;
        while (end < size && bytes_[base + end] != 0) ++end;
        Check(end < size, "ELF string is unterminated");
        return std::string(reinterpret_cast<const char*>(bytes_.data() + base + index), end - index);
    }
private:
    const std::vector<uint8_t>& bytes_;
};
uint64_t AddressOffset(const Reader& reader, const ElfPrepassFacts& facts, uint64_t address, uint64_t size)
{
    for (const auto& segment : facts.loadSegments) {
        if (address < segment.virtualAddress) continue;
        const uint64_t delta = address - segment.virtualAddress;
        if (delta <= segment.fileSize && size <= segment.fileSize - delta) {
            reader.Range(segment.offset + delta, size);
            return segment.offset + delta;
        }
    }
    throw Failure(ElfPrepassVerdict::MALFORMED_ELF, "ELF dynamic address is outside file-backed LOAD segments");
}
uint64_t GnuSymbolCount(const Reader& reader, const ElfPrepassFacts& facts,
    uint64_t address, uint64_t wordSize)
{
    const auto header = AddressOffset(reader, facts, address, 16);
    const auto buckets = reader.Number(header, 4);
    const auto firstSymbol = reader.Number(header + 4, 4);
    const auto bloomWords = reader.Number(header + 8, 4);
    Check(buckets > 0 && buckets <= MAX_SYMBOLS && firstSymbol <= MAX_SYMBOLS &&
        bloomWords > 0 && bloomWords <= MAX_SYMBOLS && (bloomWords & (bloomWords - 1)) == 0,
        "ELF GNU hash header is invalid");
    const auto prefix = 16 + wordSize * bloomWords + 4 * buckets;
    const auto table = AddressOffset(reader, facts, address, prefix);
    Check(address <= UINT64_MAX - prefix, "ELF GNU hash address overflow");
    const auto chains = address + prefix;
    uint64_t count = firstSymbol, walked = 0;
    for (uint64_t i = 0; i < buckets; ++i) {
        uint64_t symbol = reader.Number(table + 16 + wordSize * bloomWords + 4 * i, 4);
        if (symbol == 0) continue;
        Check(symbol >= firstSymbol && symbol < MAX_SYMBOLS, "ELF GNU hash bucket is invalid");
        for (;;) {
            Check(symbol < MAX_SYMBOLS && ++walked <= MAX_SYMBOLS, "ELF GNU hash chain exceeds bound");
            const uint64_t delta = 4 * (symbol - firstSymbol);
            Check(chains <= UINT64_MAX - delta, "ELF GNU hash chain address overflow");
            const auto value = reader.Number(AddressOffset(reader, facts, chains + delta, 4), 4);
            count = std::max(count, symbol + 1);
            if ((value & 1) != 0) break;
            ++symbol;
        }
    }
    return count;
}
ElfPrepassFacts Inspect(const ElfPrepassInput& input)
{
    if (!IsDigest(input.apkSha256) || !IsDigest(input.expectedElfSha256) ||
        input.entryName.empty() || input.entryName.size() > 4096 ||
        input.entryName.find('\0') != std::string::npos || input.abi.empty() || input.bytes.size() > 256ULL * 1024 * 1024)
        throw Failure(ElfPrepassVerdict::INVALID_INPUT, "ELF source identity is incomplete or exceeds limits");
    const auto digest = Digest(input.bytes);
    if (digest != input.expectedElfSha256)
        throw Failure(ElfPrepassVerdict::DIGEST_MISMATCH, "ELF bytes differ from verified entry digest");
    Reader reader(input.bytes);
    reader.Range(0, 16);
    Check(reader.Number(0, 4) == 0x464c457f, "ELF magic is invalid");
    const auto elfClass = reader.Number(4, 1);
    Check((elfClass == 1 || elfClass == 2) && reader.Number(6, 1) == 1, "ELF class/version is invalid");
    if (reader.Number(5, 1) != 1)
        throw Failure(ElfPrepassVerdict::ABI_MISMATCH, "Android ABI requires little-endian ELF");
    const bool is64 = elfClass == 2;
    const uint64_t word = is64 ? 8 : 4;
    const auto headerSize = is64 ? 64 : 52;
    reader.Range(0, headerSize);
    Check(reader.Number(16, 2) == 3 && reader.Number(20, 4) == 1, "ELF is not a current shared object");
    const auto machine = reader.Number(18, 2);
    if (!AbiMatches(input.abi, static_cast<uint8_t>(elfClass), static_cast<uint16_t>(machine)))
        throw Failure(ElfPrepassVerdict::ABI_MISMATCH, "ELF class/machine differs from the entry ABI");
    Check(reader.Number(is64 ? 52 : 40, 2) == static_cast<uint64_t>(headerSize), "ELF header size is invalid");
    const auto phoff = reader.Number(is64 ? 32 : 28, word);
    const auto phsize = reader.Number(is64 ? 54 : 42, 2);
    const auto phcount = reader.Number(is64 ? 56 : 44, 2);
    Check(phsize == (is64 ? 56U : 32U) && phcount > 0 && phcount <= 4096, "ELF program header shape is invalid");
    reader.Range(phoff, phsize * phcount);
    ElfPrepassFacts facts;
    facts.analyzerVersion = "elf-prepass-v1";
    facts.apkSha256 = input.apkSha256; facts.entryName = input.entryName; facts.abi = input.abi;
    facts.elfSha256 = digest; facts.elfClass = static_cast<uint8_t>(elfClass); facts.machine = static_cast<uint16_t>(machine);
    std::optional<ElfLoadSegment> dynamic;
    for (uint64_t i = 0; i < phcount; ++i) {
        const auto base = phoff + i * phsize;
        const auto type = reader.Number(base, 4);
        if (type != 1 && type != 2) continue;
        ElfLoadSegment segment;
        segment.offset = reader.Number(base + (is64 ? 8 : 4), word);
        segment.virtualAddress = reader.Number(base + (is64 ? 16 : 8), word);
        segment.fileSize = reader.Number(base + (is64 ? 32 : 16), word);
        segment.memorySize = reader.Number(base + (is64 ? 40 : 20), word);
        segment.alignment = reader.Number(base + (is64 ? 48 : 28), word);
        segment.flags = static_cast<uint32_t>(reader.Number(base + (is64 ? 4 : 24), 4));
        reader.Range(segment.offset, segment.fileSize);
        const auto addressMax = is64 ? UINT64_MAX : UINT32_MAX;
        Check(segment.fileSize <= segment.memorySize && segment.memorySize <= addressMax - segment.virtualAddress,
            "ELF segment memory range is invalid");
        if (type == 1) {
            const auto alignment = segment.alignment;
            Check(alignment <= 1 || ((alignment & (alignment - 1)) == 0 &&
                segment.offset % alignment == segment.virtualAddress % alignment), "ELF LOAD alignment is invalid");
            facts.loadSegments.push_back(segment);
        } else {
            Check(!dynamic.has_value(), "ELF has duplicate DYNAMIC segments");
            dynamic = segment;
        }
    }
    Check(!facts.loadSegments.empty() && dynamic.has_value(), "ELF LOAD/DYNAMIC segment is missing");
    Check(AddressOffset(reader, facts, dynamic->virtualAddress, dynamic->fileSize) == dynamic->offset,
        "ELF DYNAMIC virtual address differs from its file bytes");
    const uint64_t dynEntry = word * 2;
    Check(dynamic->fileSize >= dynEntry && dynamic->fileSize % dynEntry == 0 && dynamic->fileSize / dynEntry <= 4096,
        "ELF DYNAMIC size is invalid");
    std::map<uint64_t, uint64_t> tags;
    std::vector<uint64_t> needed;
    bool terminated = false;
    for (uint64_t offset = 0; offset < dynamic->fileSize; offset += dynEntry) {
        const auto tag = reader.Number(dynamic->offset + offset, word);
        const auto value = reader.Number(dynamic->offset + offset + word, word);
        if (tag == 0) { terminated = true; break; }
        if (tag == 1) { needed.push_back(value); continue; }
        if (tag == 4 || tag == 5 || tag == 6 || tag == 10 || tag == 11 || tag == 14 || tag == 0x6ffffef5) {
            Check(tags.emplace(tag, value).second, "ELF has duplicate singleton dynamic tags");
        }
    }
    Check(terminated && tags.count(5) && tags.count(6) && tags.count(10) && tags.count(11),
        "ELF dynamic symbol/string information is incomplete");
    const auto strsize = tags.at(10);
    Check(strsize > 0, "ELF dynamic string table is empty");
    const auto strbase = AddressOffset(reader, facts, tags.at(5), strsize);
    for (const auto index : needed) {
        auto name = reader.String(strbase, strsize, index);
        Check(!name.empty(), "ELF dependency name is empty");
        facts.neededLibraries.push_back(std::move(name));
    }
    if (tags.count(14)) facts.soname = reader.String(strbase, strsize, tags.at(14));
    std::optional<uint64_t> symbolCount;
    if (tags.count(4)) {
        const auto hash = AddressOffset(reader, facts, tags.at(4), 8);
        const auto buckets = reader.Number(hash, 4), count = reader.Number(hash + 4, 4);
        Check(buckets > 0 && buckets <= MAX_SYMBOLS && count > 0 && count <= MAX_SYMBOLS,
            "ELF SysV hash shape is invalid");
        AddressOffset(reader, facts, tags.at(4), 8 + 4 * (buckets + count));
        symbolCount = count;
    }
    if (tags.count(0x6ffffef5)) {
        const auto count = GnuSymbolCount(reader, facts, tags.at(0x6ffffef5), word);
        Check(!symbolCount || *symbolCount == count, "ELF hash tables disagree on symbol count");
        symbolCount = count;
    }
    Check(symbolCount && *symbolCount > 0 && *symbolCount <= MAX_SYMBOLS, "ELF symbol hash is absent or invalid");
    const uint64_t syment = is64 ? 24 : 16;
    Check(tags.at(11) == syment, "ELF symbol entry size is invalid");
    const auto symbols = AddressOffset(reader, facts, tags.at(6), *symbolCount * syment);
    for (uint64_t i = 0; i < *symbolCount; ++i) {
        const auto base = symbols + i * syment;
        const auto name = reader.String(strbase, strsize, reader.Number(base, 4));
        const auto info = reader.Number(base + (is64 ? 4 : 12), 1);
        const auto visibility = reader.Number(base + (is64 ? 5 : 13), 1) & 3;
        const auto section = reader.Number(base + (is64 ? 6 : 14), 2);
        const auto binding = info >> 4;
        if (name.empty() || (binding != 1 && binding != 2 && binding != 10)) continue;
        if (section == 0) facts.requiredSymbols.push_back({name, binding == 2});
        else if (visibility == 0 || visibility == 3) facts.exportedSymbols.push_back(name);
    }
    std::sort(facts.exportedSymbols.begin(), facts.exportedSymbols.end());
    facts.exportedSymbols.erase(std::unique(facts.exportedSymbols.begin(), facts.exportedSymbols.end()), facts.exportedSymbols.end());
    return facts;
}
ElfPrepassResult Reject(ElfPrepassVerdict verdict, const std::string& reason)
{ return {verdict, reason, {}}; }
}

ElfPrepassResult InspectElf(const ElfPrepassInput& input)
{
    try { return {ElfPrepassVerdict::ANALYZED, "ELF facts inspected from verified entry bytes", Inspect(input)}; }
    catch (const Failure& error) { return Reject(error.verdict, error.what()); }
}
ElfPrepassResult AnalyzeElf(const ElfPrepassInput& input, const std::vector<ElfPrepassFacts>& availableLibraries)
{
    auto result = InspectElf(input);
    if (!result.facts) return result;
    const auto& facts = *result.facts;
    // Resolve a same-ABI dependency group before checking any strong symbol.
    // Queue membership bounds cycles; unrelated available libraries cannot supply symbols.
    std::vector<const ElfPrepassFacts*> group{&facts};
    std::set<const ElfPrepassFacts*> visited{&facts};
    std::set<std::string> exports;
    for (size_t i = 0; i < group.size(); ++i) {
        const auto& library = *group[i];
        exports.insert(library.exportedSymbols.begin(), library.exportedSymbols.end());
        for (const auto& needed : library.neededLibraries) {
            const ElfPrepassFacts* dependency = nullptr;
            if (!facts.soname.empty() && needed == facts.soname) dependency = &facts;
            else {
                const auto found = std::find_if(availableLibraries.begin(), availableLibraries.end(), [&](const auto& candidate) {
                    return candidate.abi == facts.abi && candidate.machine == facts.machine && candidate.elfClass == facts.elfClass &&
                        candidate.soname == needed && IsDigest(candidate.elfSha256) && !candidate.analyzerVersion.empty();
                });
                if (found != availableLibraries.end()) dependency = &*found;
            }
            if (dependency == nullptr)
                return Reject(ElfPrepassVerdict::DEPENDENCY_MISSING, "ELF dependency is unavailable: " + needed);
            if (visited.insert(dependency).second) group.push_back(dependency);
        }
    }
    for (const auto* library : group) {
        for (const auto& required : library->requiredSymbols) {
            if (!required.weak && exports.count(required.name) == 0)
                return Reject(ElfPrepassVerdict::SYMBOL_MISSING, "ELF required symbol is unavailable: " + required.name);
        }
    }
    return result;
}
} // namespace oh_adapter::package_transaction
