#include "install_prepass_materializer.h"

#include <cassert>
#include <cstring>
#include <iostream>

#if defined(__linux__) || defined(__OHOS__)
#include <fcntl.h>
#include <unistd.h>
#endif

namespace {

void Copy(char* destination, size_t capacity, const char* source)
{
    assert(std::strlen(source) < capacity);
    std::strcpy(destination, source);
}

PrepassContextWire Context()
{
    PrepassContextWire context{};
    context.abiVersion = PREPASS_CONTEXT_WIRE_ABI;
    context.structSize = sizeof(context);
    context.userId = 10;
    Copy(context.requestId, sizeof(context.requestId), "request-a");
    Copy(context.packageName, sizeof(context.packageName), "org.example.app");
    Copy(context.candidateGeneration, sizeof(context.candidateGeneration), "generation-a");
    constexpr const char* digest =
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    Copy(context.contractSha256Hex, sizeof(context.contractSha256Hex), digest);
    Copy(context.policySha256Hex, sizeof(context.policySha256Hex), digest);
    Copy(context.toolSha256Hex, sizeof(context.toolSha256Hex), digest);
    Copy(context.topologySha256Hex, sizeof(context.topologySha256Hex), digest);
    Copy(context.runtimeGenerationSealSha256Hex,
        sizeof(context.runtimeGenerationSealSha256Hex), digest);
    return context;
}

} // namespace

int main()
{
    const auto context = Context();
    oh_adapter::package_transaction::wire::PrepassBundleRecord record;
    std::string error;
    const std::string apkDigest(64, 'b');
    assert(oh_adapter::BuildInstallPrepass(context, apkDigest, {}, &record, &error));
    assert(record.payloadSha256.size() == 64);

    oh_adapter::package_transaction::PrepassBundle decoded;
    assert(oh_adapter::package_transaction::PrepassBundleCodec::Decode(
        record, &decoded, &error));
    assert(decoded.requestId == "request-a");
    assert(decoded.packageGeneration == "generation-a");
    assert(decoded.topologyDigest == std::string(64, 'a'));
    assert(decoded.disposition ==
        oh_adapter::package_transaction::PrepassDisposition::NO_NATIVE_ELF);
    assert(decoded.elfFacts.empty());

#if defined(__linux__) || defined(__OHOS__)
    int descriptor = -1;
    assert(oh_adapter::WriteCanonicalPrepassFd(record.canonicalPayload, &descriptor));
    assert(descriptor >= 0);
    constexpr int seals = F_SEAL_WRITE | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL;
    assert((fcntl(descriptor, F_GET_SEALS) & seals) == seals);
    std::string readback(record.canonicalPayload.size(), '\0');
    assert(read(descriptor, readback.data(), readback.size()) ==
        static_cast<ssize_t>(readback.size()));
    assert(readback == record.canonicalPayload);
    close(descriptor);
#endif

    std::cout << "INSTALL_PREPASS_MATERIALIZER_HOST_TEST_PASS\n";
}
