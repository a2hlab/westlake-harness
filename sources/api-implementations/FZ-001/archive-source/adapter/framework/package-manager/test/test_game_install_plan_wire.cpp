#include "game_install_plan_wire.h"

#include <cassert>
#include <cstring>
#include <iostream>

namespace {
GameInstallPlanWire Valid()
{
    GameInstallPlanWire plan{};
    plan.abiVersion = GAME_INSTALL_PLAN_WIRE_ABI;
    plan.structSize = sizeof(plan);
    plan.apkFd = 41;
    plan.schemeVersion = 2;
    std::strcpy(plan.apkSha256Hex,
        "435f0ebbf99b5f5ae76aecb411da7684052a92ef0b6aee18d50afa6a98210626");
    plan.signerCount = 1;
    std::strcpy(plan.signerSha256Hex[0],
        "5a48f822dafddefd86d3dc68839fcf79e0068db8ac8d1168baa5b96e4147d24d");
    std::strcpy(plan.packageName, "org.example.generic");
    std::strcpy(plan.versionName, "1");
    std::strcpy(plan.launcherActivity, "org.example.generic.Entry");
    std::strcpy(plan.primaryAbi, "arm64-v8a");
    plan.prepassFd = 42;
    plan.prepassByteLength = 1024;
    std::strcpy(plan.prepassSha256Hex,
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
    return plan;
}
}

int main()
{
    auto plan = Valid();
    assert(GameInstallPlanWire_Validate(&plan) == GAME_INSTALL_PLAN_WIRE_OK);
    plan.prepassFd = -1;
    assert(GameInstallPlanWire_Validate(&plan) == GAME_INSTALL_PLAN_WIRE_BAD_PREPASS_FD);
    plan = Valid(); plan.prepassByteLength = 0;
    assert(GameInstallPlanWire_Validate(&plan) == GAME_INSTALL_PLAN_WIRE_BAD_PREPASS_LENGTH);
    plan = Valid(); plan.prepassSha256Hex[0] = 'A';
    assert(GameInstallPlanWire_Validate(&plan) == GAME_INSTALL_PLAN_WIRE_BAD_PREPASS_DIGEST);
    plan = Valid(); plan.reservedZero = 1;
    assert(GameInstallPlanWire_Validate(&plan) == GAME_INSTALL_PLAN_WIRE_RESERVED_NONZERO);
    std::cout << "GAME_INSTALL_PLAN_WIRE_HOST_TEST_PASS\n";
}
