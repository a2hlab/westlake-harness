#ifndef OH_ADAPTER_RUNTIME_PATH_DESCRIPTOR_V1_H
#define OH_ADAPTER_RUNTIME_PATH_DESCRIPTOR_V1_H

#include "package_transaction_v1.h"

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace oh_adapter::runtime_path_descriptor {

enum class RuntimePathVerdict {
    READY,
    INVALID_REQUEST,
    UNKNOWN_SCHEMA,
    NOT_AUTHORIZED,
    NOT_SUPPORTED_ARTIFACT_PROFILE,
    NOT_SUPPORTED_USER,
    NOT_SUPPORTED_ABI,
    PACKAGE_NOT_FOUND,
    PACKAGE_NOT_READY,
    STALE_GENERATION,
    DATA_INCONSISTENT,
    PATH_OUTSIDE_PERMITTED_ROOT,
    PATH_READBACK_FAILED,
    DIGEST_MISMATCH,
    ELF_IDENTITY_MISMATCH,
    INTERRUPTED,
};

enum class RuntimePathFaultPoint {
    AFTER_GENERATION_SNAPSHOT,
    AFTER_FILE_READBACK,
    AFTER_ELF_READBACK,
    AFTER_SERIALIZATION,
};

struct RuntimePathRequestV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t expectedGeneration = 0;
    std::optional<std::string> expectedCanonicalDigest;
    std::string abi;
    std::string callerScopeDigest;
    bool callerAuthorized = false;
    bool splitProfileRequested = false;
};

struct NativeLibraryFactV1 {
    std::string path;
    std::string sha256;
};

// This is generation-bound policy/fact input, not a second package truth.
// The canonical base path and digest always come from FilePackageStore.
struct RuntimePathFactsV1 {
    uint32_t schemaVersion = 1;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    std::string artifactSetDigest;
    std::string abi;
    std::vector<std::string> permittedRoots;
    std::vector<std::string> nativeSearchRoots;
    std::vector<NativeLibraryFactV1> nativeLibraries;
};

class RuntimePathFactsProvider {
public:
    virtual ~RuntimePathFactsProvider() = default;
    virtual bool Read(const std::string& packageName, uint32_t userId,
        uint64_t generation, const std::string& abi, RuntimePathFactsV1* facts,
        std::string* error) const = 0;
};

class RuntimePathFaultInjector {
public:
    virtual ~RuntimePathFaultInjector() = default;
    virtual bool InterruptAfter(RuntimePathFaultPoint point) = 0;
};

class NoRuntimePathFaultInjector final : public RuntimePathFaultInjector {
public:
    bool InterruptAfter(RuntimePathFaultPoint) override
    {
        return false;
    }
};

struct RuntimeFileObservationV1 {
    std::string role;
    std::string path;
    uint64_t byteLength = 0;
    std::string sha256;
    std::optional<uint16_t> elfMachine;
};

struct RuntimePathDescriptorV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    std::string artifactSetDigest;
    std::string abi;
    std::string baseCodePath;
    std::string baseCodeSha256;
    std::vector<std::string> splitCodePaths;
    std::vector<std::string> permittedRoots;
    std::vector<std::string> nativeSearchRoots;
    std::vector<NativeLibraryFactV1> nativeLibraries;
};

struct RuntimePathResponseV1 {
    std::string requestId;
    RuntimePathVerdict verdict = RuntimePathVerdict::DATA_INCONSISTENT;
    std::optional<RuntimePathDescriptorV1> descriptor;
    std::vector<RuntimeFileObservationV1> observations;
    bool classLoaderCreated = false;
};

class RuntimePathDescriptorServiceV1 {
public:
    RuntimePathDescriptorServiceV1(
        package_transaction::FilePackageStore* store,
        const RuntimePathFactsProvider* factsProvider,
        RuntimePathFaultInjector* faultInjector);

    RuntimePathResponseV1 Query(const RuntimePathRequestV1& request) const;

private:
    package_transaction::FilePackageStore* store_;
    const RuntimePathFactsProvider* factsProvider_;
    RuntimePathFaultInjector* faultInjector_;
};

// A consumer-side dry run validates the complete immutable descriptor without
// constructing a ClassLoader or loading code.
RuntimePathVerdict ValidateDescriptorForConsumerV1(
    const RuntimePathDescriptorV1& descriptor);

std::string SerializeRuntimePathResponseJsonV1(
    const RuntimePathResponseV1& response);
const char* RuntimePathVerdictName(RuntimePathVerdict verdict);

}  // namespace oh_adapter::runtime_path_descriptor

#endif  // OH_ADAPTER_RUNTIME_PATH_DESCRIPTOR_V1_H
