#include "install_input_v2.h"
#include "game_install_plan_wire.h"
_Static_assert(sizeof(GameInstallPlanV1) == 1208, "SPC24_V1_LAYOUT");
_Static_assert(sizeof(GameInstallPlanWire) == 1296, "SPC24_LEGACY_WIRE_LAYOUT");
_Static_assert(sizeof(ApkInstallPlanV2) == 21032, "SPC24_V2_LAYOUT");
_Static_assert(sizeof(OhAdapterInstallInputV2) == 21056, "SPC24_INPUT_LAYOUT");
_Static_assert(_Alignof(OhAdapterInstallInputV2) == 8, "SPC24_INPUT_ALIGNMENT");
_Static_assert(offsetof(OhAdapterInstallInputV2, plan) == 24, "SPC24_PLAN_OFFSET");
int install_input_c_probe(const void* bytes, size_t length, int32_t user,
    uint64_t flags, void* output, size_t capacity)
{
    int (*entry)(const void*, size_t, int32_t, uint64_t, void*, size_t) = oh_adapter_acquire_install_input_v2;
    return entry(bytes, length, user, flags, output, capacity);
}
