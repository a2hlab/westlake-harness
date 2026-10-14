#ifndef OH_ADAPTER_PREPASS_BUNDLE_H
#define OH_ADAPTER_PREPASS_BUNDLE_H
#include "elf_prepass_analyzer.h"
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace oh_adapter::package_transaction {
struct PrepassBinding {
    std::string requestId, packageName, packageGeneration;
    int32_t userId = -1;
    std::string apkDigest, contractDigest, policyDigest, toolDigest;
    std::string topologyDigest, runtimeGenerationSealDigest;
};
enum class PrepassDisposition : uint32_t {
    NO_NATIVE_ELF = 0, HAS_NATIVE_ELF = 1, NO_MATCHING_ABIS = 2,
};
struct PrepassBundle : PrepassBinding {
    PrepassDisposition disposition = PrepassDisposition::NO_NATIVE_ELF;
    uint32_t nativeEntryCount = 0;
    std::vector<ElfPrepassFacts> elfFacts;
};
namespace wire {
struct PrepassBundleRecord {
    // Supplied by the trusted context owner, not recovered from untrusted bytes.
    PrepassBinding binding;
    std::string canonicalPayload, payloadSha256;
};
}
class PrepassBundleCodec {
public:
    static constexpr uint32_t SCHEMA_VERSION = 1;
    static constexpr size_t MAX_PAYLOAD_BYTES = 64 * 1024 * 1024;
    static constexpr uint32_t MAX_NATIVE_ENTRIES = 4096;
    // Canonical ELF order is (ABI, entryName). Within each ELF, ordered loader
    // facts (including DT_NEEDED and PT_LOAD) retain their original order.
    static bool Encode(const PrepassBundle&, wire::PrepassBundleRecord*, std::string* error);
    static bool Decode(const wire::PrepassBundleRecord&, PrepassBundle*, std::string* error);
    // expectedBinding and expectedDigest must come from the trusted request/FD
    // envelope; hashing alone never authenticates an attacker's replacement.
    // expectedBinding may refer to output's base; output is published only after
    // all input is consumed, and is cleared on failure.
    static bool DecodePayload(const std::string& payload, const std::string& expectedDigest,
        const PrepassBinding& expectedBinding, PrepassBundle*, std::string* error);
};
}
#endif
