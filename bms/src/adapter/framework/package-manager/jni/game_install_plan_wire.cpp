#include "game_install_plan_wire.h"
#include <cstddef>
#include <cstring>

namespace {
static_assert(sizeof(GameInstallPlanV1) == 1208 && sizeof(GameInstallPlanWire) == 1296);
static_assert(offsetof(GameInstallPlanWire, prepassFd) == sizeof(GameInstallPlanV1));
int Header(const GameInstallPlanWire* plan)
{
    if (!plan) return GAME_INSTALL_PLAN_WIRE_BAD_STRUCT_SIZE;
    uint32_t header[2]; std::memcpy(header, plan, sizeof(header));
    if (header[0] != GAME_INSTALL_PLAN_WIRE_ABI) return GAME_INSTALL_PLAN_WIRE_BAD_ABI;
    return header[1] == sizeof(*plan) ? GAME_INSTALL_PLAN_WIRE_OK : GAME_INSTALL_PLAN_WIRE_BAD_STRUCT_SIZE;
}
bool Digest(const char* value)
{
    for (size_t i = 0; i < 64; ++i) if (!((value[i] >= '0' && value[i] <= '9') || (value[i] >= 'a' && value[i] <= 'f'))) return false;
    return value[64] == 0;
}
}
extern "C" int GameInstallPlanWire_Validate(const GameInstallPlanWire* plan)
{
    const int status = Header(plan); if (status != GAME_INSTALL_PLAN_WIRE_OK) return status;
    if (plan->reservedZero != 0) return GAME_INSTALL_PLAN_WIRE_RESERVED_NONZERO;
    for (auto byte : plan->reservedTail) if (byte != 0) return GAME_INSTALL_PLAN_WIRE_RESERVED_NONZERO;
    // Reuse the existing game policy/shape validator without widening its ABI.
    GameInstallPlanV1 legacy; std::memcpy(&legacy, plan, sizeof(legacy));
    legacy.abiVersion = GAME_INSTALL_PLAN_ABI_V1; legacy.structSize = sizeof(legacy);
    if (GameInstallPlanV1_Validate(&legacy) != GAME_INSTALL_PLAN_OK) return GAME_INSTALL_PLAN_WIRE_BAD_LEGACY_FIELDS;
    if (plan->prepassFd < 0) return GAME_INSTALL_PLAN_WIRE_BAD_PREPASS_FD;
    if (plan->prepassByteLength == 0 || plan->prepassByteLength > 64ULL * 1024 * 1024) return GAME_INSTALL_PLAN_WIRE_BAD_PREPASS_LENGTH;
    if (!Digest(plan->prepassSha256Hex)) return GAME_INSTALL_PLAN_WIRE_BAD_PREPASS_DIGEST;
    return GAME_INSTALL_PLAN_WIRE_OK;
}
extern "C" int GameInstallPlanWire_TrySetVersion(GameInstallPlanWire* plan, uint32_t majorBits, uint32_t minorBits)
{
    const int status = Header(plan); if (status != GAME_INSTALL_PLAN_WIRE_OK) return status;
    if (majorBits != 0) return GAME_INSTALL_PLAN_WIRE_VERSION_REQUIRES_V2;
    plan->versionCode = minorBits; return GAME_INSTALL_PLAN_WIRE_OK;
}
