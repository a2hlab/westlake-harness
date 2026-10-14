#include "prepass_bundle.h"
#include "sha256.h"
#include <algorithm>
#include <array>
#include <limits>
#include <stdexcept>
#include <string_view>
#include <tuple>

namespace oh_adapter::package_transaction {
namespace {
constexpr uint32_t MAX_TEXT = 65535, MAX_ID = 4096, MAX_SEGMENTS = 4096, MAX_SYMBOLS = 1024 * 1024;
constexpr char MAGIC[8] = {'O', 'H', 'P', 'R', 'E', 'P', 0, 1};
void Require(bool value, const char* reason)
{ if (!value) throw std::runtime_error(reason); }
void Text(const std::string& value, uint32_t limit, bool emptyAllowed = false)
{
    Require((emptyAllowed || !value.empty()) && value.size() <= limit && value.find('\0') == std::string::npos,
        "Prepass text is empty, oversized or contains NUL");
}
bool IsDigest(const std::string& value)
{
    return value.size() == 64 && std::all_of(value.begin(), value.end(), [](char c) {
        return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
    });
}
std::string Hash(const std::string& input)
{
    unsigned char bytes[32]; sha256(reinterpret_cast<const unsigned char*>(input.data()), input.size(), bytes);
    constexpr char hex[] = "0123456789abcdef"; std::string output; output.reserve(64);
    for (auto byte : bytes) { output += hex[byte >> 4]; output += hex[byte & 15]; } return output;
}
void ValidateBinding(const PrepassBinding& b)
{
    Text(b.requestId, MAX_ID); Text(b.packageName, MAX_ID); Text(b.packageGeneration, MAX_ID);
    Require(b.userId >= 0, "Prepass requires an explicit nonnegative user");
    for (const auto* value : {&b.apkDigest, &b.contractDigest, &b.policyDigest, &b.toolDigest,
        &b.topologyDigest, &b.runtimeGenerationSealDigest}) Require(IsDigest(*value), "Prepass binding digest is invalid");
}
auto BindingTuple(const PrepassBinding& b)
{
    return std::tie(b.requestId, b.packageName, b.userId, b.packageGeneration, b.apkDigest,
        b.contractDigest, b.policyDigest, b.toolDigest, b.topologyDigest, b.runtimeGenerationSealDigest);
}
void Validate(const PrepassBundle& b)
{
    ValidateBinding(b);
    Require(b.nativeEntryCount <= PrepassBundleCodec::MAX_NATIVE_ENTRIES && b.elfFacts.size() <= b.nativeEntryCount,
        "Prepass native entry count is invalid");
    switch (b.disposition) {
        case PrepassDisposition::NO_NATIVE_ELF:
            Require(b.nativeEntryCount == 0 && b.elfFacts.empty(), "NO_NATIVE_ELF contradicts native observations"); break;
        case PrepassDisposition::HAS_NATIVE_ELF:
            Require(b.nativeEntryCount > 0 && !b.elfFacts.empty(), "HAS_NATIVE_ELF lacks analyzed observations"); break;
        case PrepassDisposition::NO_MATCHING_ABIS:
            Require(b.nativeEntryCount > 0, "NO_MATCHING_ABIS lacks native observations"); break;
        default: Require(false, "Unknown prepass disposition");
    }
    for (const auto& f : b.elfFacts) {
        Text(f.analyzerVersion, MAX_ID); Text(f.entryName, MAX_ID); Text(f.abi, MAX_ID); Text(f.soname, MAX_TEXT, true);
        Require(f.apkSha256 == b.apkDigest && IsDigest(f.elfSha256), "ELF identity disagrees with prepass APK");
        Require((f.elfClass == 1 || f.elfClass == 2) && f.machine != 0, "ELF scalar schema is invalid");
        Require(!f.loadSegments.empty() && f.loadSegments.size() <= MAX_SEGMENTS, "ELF LOAD count is invalid");
        for (const auto& s : f.loadSegments) {
            Require(s.fileSize <= s.memorySize && s.fileSize <= std::numeric_limits<uint64_t>::max() - s.offset &&
                s.memorySize <= std::numeric_limits<uint64_t>::max() - s.virtualAddress,
                "ELF LOAD range overflows");
        }
        Require(f.neededLibraries.size() <= MAX_SYMBOLS && f.exportedSymbols.size() <= MAX_SYMBOLS &&
            f.requiredSymbols.size() <= MAX_SYMBOLS, "ELF symbol/dependency count exceeds limit");
        for (const auto& v : f.neededLibraries) Text(v, MAX_TEXT);
        for (const auto& v : f.exportedSymbols) Text(v, MAX_TEXT);
        for (const auto& v : f.requiredSymbols) Text(v.name, MAX_TEXT);
    }
}
class Writer {
public:
    std::string payload;
    void Raw(const char* data, size_t count)
    {
        Require(count <= PrepassBundleCodec::MAX_PAYLOAD_BYTES - payload.size(), "Prepass payload exceeds byte limit");
        payload.append(data, count);
    }
    void Number(uint64_t value, size_t width)
    {
        char bytes[8]; for (size_t i = 0; i < width; ++i) bytes[i] = static_cast<char>((value >> (8 * i)) & 255);
        Raw(bytes, width);
    }
    void String(const std::string& value) { Number(value.size(), 4); Raw(value.data(), value.size()); }
    void Strings(const std::vector<std::string>& values)
    { Number(values.size(), 4); for (const auto& value : values) String(value); }
};
void WriteBinding(Writer& w, const PrepassBinding& b)
{
    w.String(b.requestId); w.String(b.packageName); w.Number(static_cast<uint32_t>(b.userId), 4);
    w.String(b.packageGeneration); w.String(b.apkDigest); w.String(b.contractDigest);
    w.String(b.policyDigest); w.String(b.toolDigest); w.String(b.topologyDigest); w.String(b.runtimeGenerationSealDigest);
}
void WriteElf(Writer& w, const ElfPrepassFacts& f)
{
    w.String(f.analyzerVersion); w.String(f.apkSha256); w.String(f.entryName); w.String(f.abi); w.String(f.elfSha256);
    w.Number(f.elfClass, 1); w.Number(f.machine, 2); w.String(f.soname);
    w.Number(f.loadSegments.size(), 4);
    for (const auto& s : f.loadSegments) {
        w.Number(s.offset, 8); w.Number(s.virtualAddress, 8); w.Number(s.fileSize, 8);
        w.Number(s.memorySize, 8); w.Number(s.alignment, 8); w.Number(s.flags, 4);
    }
    w.Strings(f.neededLibraries); w.Strings(f.exportedSymbols); w.Number(f.requiredSymbols.size(), 4);
    for (const auto& s : f.requiredSymbols) { w.String(s.name); w.Number(s.weak ? 1 : 0, 1); }
}
std::string Canonical(const PrepassBundle& bundle)
{
    Validate(bundle);
    std::vector<const ElfPrepassFacts*> sorted;
    for (const auto& f : bundle.elfFacts) sorted.push_back(&f);
    std::sort(sorted.begin(), sorted.end(), [](const auto* a, const auto* b) {
        return std::tie(a->abi, a->entryName) < std::tie(b->abi, b->entryName);
    });
    for (size_t i = 1; i < sorted.size(); ++i) Require(
        std::tie(sorted[i - 1]->abi, sorted[i - 1]->entryName) != std::tie(sorted[i]->abi, sorted[i]->entryName),
        "Duplicate prepass ELF identity");
    Writer w; w.Raw(MAGIC, sizeof(MAGIC)); w.Number(PrepassBundleCodec::SCHEMA_VERSION, 4); w.Number(0, 4);
    WriteBinding(w, bundle); w.Number(static_cast<uint32_t>(bundle.disposition), 4);
    w.Number(bundle.nativeEntryCount, 4); w.Number(sorted.size(), 4);
    for (const auto* f : sorted) WriteElf(w, *f);
    return std::move(w.payload);
}
class Reader {
    std::string_view payload;
    size_t at = 0;
public:
    explicit Reader(const std::string& bytes) : payload(bytes) {}
    std::string_view Raw(size_t length)
    {
        Require(length <= payload.size() - at, "Truncated prepass payload");
        const auto result = payload.substr(at, length); at += length; return result;
    }
    uint64_t Number(size_t width)
    {
        const auto bytes = Raw(width); uint64_t number = 0;
        for (size_t i = 0; i < width; ++i) number |= static_cast<uint64_t>(static_cast<unsigned char>(bytes[i])) << (8 * i);
        return number;
    }
    uint32_t Count(uint32_t maximum, size_t minimumBytes)
    {
        const auto count = Number(4);
        Require(count <= maximum && count <= (payload.size() - at) / minimumBytes, "Prepass count exceeds remaining bytes or limit");
        return static_cast<uint32_t>(count);
    }
    std::string String(uint32_t maximum, bool emptyAllowed = false)
    {
        const auto size = Number(4); Require(size <= maximum, "Prepass text length exceeds limit");
        std::string value(Raw(size)); Text(value, maximum, emptyAllowed); return value;
    }
    std::vector<std::string> Strings()
    {
        std::vector<std::string> values; const auto count = Count(MAX_SYMBOLS, 4); values.reserve(count);
        for (uint32_t i = 0; i < count; ++i) values.push_back(String(MAX_TEXT)); return values;
    }
    bool End() const { return at == payload.size(); }
};
PrepassBinding ReadBinding(Reader& r)
{
    PrepassBinding b; b.requestId = r.String(MAX_ID); b.packageName = r.String(MAX_ID);
    const auto user = r.Number(4); Require(user <= std::numeric_limits<int32_t>::max(), "Invalid prepass user");
    b.userId = static_cast<int32_t>(user); b.packageGeneration = r.String(MAX_ID);
    b.apkDigest = r.String(64); b.contractDigest = r.String(64); b.policyDigest = r.String(64);
    b.toolDigest = r.String(64); b.topologyDigest = r.String(64); b.runtimeGenerationSealDigest = r.String(64);
    return b;
}
ElfPrepassFacts ReadElf(Reader& r)
{
    ElfPrepassFacts f; f.analyzerVersion = r.String(MAX_ID); f.apkSha256 = r.String(64);
    f.entryName = r.String(MAX_ID); f.abi = r.String(MAX_ID); f.elfSha256 = r.String(64);
    f.elfClass = r.Number(1); f.machine = r.Number(2); f.soname = r.String(MAX_TEXT, true);
    const auto segments = r.Count(MAX_SEGMENTS, 44); f.loadSegments.reserve(segments);
    for (uint32_t i = 0; i < segments; ++i) {
        ElfLoadSegment s; s.offset = r.Number(8); s.virtualAddress = r.Number(8); s.fileSize = r.Number(8);
        s.memorySize = r.Number(8); s.alignment = r.Number(8); s.flags = r.Number(4); f.loadSegments.push_back(s);
    }
    f.neededLibraries = r.Strings(); f.exportedSymbols = r.Strings();
    const auto symbols = r.Count(MAX_SYMBOLS, 5); f.requiredSymbols.reserve(symbols);
    for (uint32_t i = 0; i < symbols; ++i) {
        ElfSymbolRequirement s; s.name = r.String(MAX_TEXT); const auto weak = r.Number(1);
        Require(weak <= 1, "Invalid prepass boolean"); s.weak = weak != 0; f.requiredSymbols.push_back(std::move(s));
    }
    return f;
}
void SetError(std::string* error, const std::exception& exception)
{ if (error) *error = exception.what(); }
}
bool PrepassBundleCodec::Encode(const PrepassBundle& bundle, wire::PrepassBundleRecord* output, std::string* error)
{
    if (output) *output = {};
    if (error) error->clear();
    try {
        Require(output != nullptr, "Missing prepass record output");
        wire::PrepassBundleRecord next; next.canonicalPayload = Canonical(bundle);
        next.payloadSha256 = Hash(next.canonicalPayload); next.binding = bundle;
        *output = std::move(next); return true;
    } catch (const std::exception& e) { SetError(error, e); return false; }
}
bool PrepassBundleCodec::Decode(const wire::PrepassBundleRecord& record, PrepassBundle* output, std::string* error)
{
    return DecodePayload(record.canonicalPayload, record.payloadSha256, record.binding, output, error);
}
bool PrepassBundleCodec::DecodePayload(const std::string& payload, const std::string& expectedDigest,
    const PrepassBinding& expectedBinding, PrepassBundle* output, std::string* error)
{
    if (error) error->clear();
    try {
        Require(output != nullptr, "Missing decoded prepass output");
        ValidateBinding(expectedBinding);
        Require(payload.size() <= MAX_PAYLOAD_BYTES && IsDigest(expectedDigest) && Hash(payload) == expectedDigest,
            "Prepass payload size or digest mismatch");
        Reader r(payload);
        Require(r.Raw(sizeof(MAGIC)) == std::string_view(MAGIC, sizeof(MAGIC)), "Invalid prepass magic");
        Require(r.Number(4) == SCHEMA_VERSION && r.Number(4) == 0, "Unknown prepass schema or reserved bits");
        PrepassBundle next; static_cast<PrepassBinding&>(next) = ReadBinding(r);
        Require(BindingTuple(next) == BindingTuple(expectedBinding), "Prepass identity differs from trusted context");
        next.disposition = static_cast<PrepassDisposition>(r.Number(4)); next.nativeEntryCount = r.Number(4);
        const auto count = r.Count(MAX_NATIVE_ENTRIES, 4); next.elfFacts.reserve(count);
        for (uint32_t i = 0; i < count; ++i) next.elfFacts.push_back(ReadElf(r));
        Require(r.End(), "Prepass has trailing bytes");
        Require(Canonical(next) == payload, "Prepass payload is not canonical");
        *output = std::move(next); return true;
    } catch (const std::exception& e) {
        if (output) *output = {};
        SetError(error, e); return false;
    }
}
}
