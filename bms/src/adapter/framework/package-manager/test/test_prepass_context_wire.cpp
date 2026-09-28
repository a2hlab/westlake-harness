#include "prepass_context_wire.h"

#include <cassert>
#include <cstring>
#include <iostream>

namespace {

void Copy(char* destination, size_t size, const char* value)
{
    assert(std::strlen(value) < size);
    std::strcpy(destination, value);
}

PrepassContextWire ValidContext()
{
    PrepassContextWire context{};
    context.abiVersion = PREPASS_CONTEXT_WIRE_ABI;
    context.structSize = sizeof(context);
    context.userId = 100;
    Copy(context.requestId, sizeof(context.requestId), "request-42");
    Copy(context.packageName, sizeof(context.packageName), "org.example.game");
    Copy(context.candidateGeneration, sizeof(context.candidateGeneration), "generation-9");
    constexpr const char* digest =
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
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
    auto context = ValidContext();
    assert(PrepassContextWire_Validate(&context) == PREPASS_CONTEXT_WIRE_OK);
    assert(PrepassContextWire_MatchPackageUser(&context,
        "org.example.game", 100) == PREPASS_CONTEXT_WIRE_OK);

    assert(PrepassContextWire_Validate(nullptr) == PREPASS_CONTEXT_WIRE_MISSING);

    auto malformed = context;
    malformed.contractSha256Hex[0] = 'G';
    assert(PrepassContextWire_Validate(&malformed) ==
        PREPASS_CONTEXT_WIRE_BAD_DIGEST);

    auto emptyRequest = context;
    emptyRequest.requestId[0] = '\0';
    assert(PrepassContextWire_Validate(&emptyRequest) ==
        PREPASS_CONTEXT_WIRE_BAD_IDENTITY);

    auto reserved = context;
    reserved.reservedZero = 1;
    assert(PrepassContextWire_Validate(&reserved) ==
        PREPASS_CONTEXT_WIRE_RESERVED_NONZERO);

    assert(PrepassContextWire_MatchPackageUser(&context,
        "org.example.other", 100) == PREPASS_CONTEXT_WIRE_PACKAGE_USER_MISMATCH);
    assert(PrepassContextWire_MatchPackageUser(&context,
        "org.example.game", 101) == PREPASS_CONTEXT_WIRE_PACKAGE_USER_MISMATCH);
    assert(PrepassContextWire_MatchPackageUser(&context,
        nullptr, 100) == PREPASS_CONTEXT_WIRE_PACKAGE_USER_MISMATCH);

    std::cout << "PREPASS_CONTEXT_WIRE_HOST_TEST_PASS\n";
}
