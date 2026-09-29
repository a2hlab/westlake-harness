#include "prepass_context_wire.h"
_Static_assert(sizeof(PrepassContextWire) == 856, "context C ABI size");
_Static_assert(_Alignof(PrepassContextWire) == 4, "context C ABI alignment");
_Static_assert(offsetof(PrepassContextWire, userId) == 8, "user offset");
_Static_assert(offsetof(PrepassContextWire, requestId) == 16, "request offset");
_Static_assert(offsetof(PrepassContextWire, packageName) == 144, "package offset");
_Static_assert(offsetof(PrepassContextWire, candidateGeneration) == 400, "generation offset");
_Static_assert(offsetof(PrepassContextWire, contractSha256Hex) == 528, "contract offset");
_Static_assert(offsetof(PrepassContextWire, policySha256Hex) == 593, "policy offset");
_Static_assert(offsetof(PrepassContextWire, toolSha256Hex) == 658, "tool offset");
_Static_assert(offsetof(PrepassContextWire, topologySha256Hex) == 723, "topology offset");
_Static_assert(offsetof(PrepassContextWire, runtimeGenerationSealSha256Hex) == 788, "runtime seal offset");
_Static_assert(offsetof(PrepassContextWire, reservedTail) == 853, "explicit padding");
int prepass_context_c_probe(const PrepassContextWire* context)
{
    int (*validate)(const PrepassContextWire*) = &PrepassContextWire_Validate;
    return validate(context);
}
