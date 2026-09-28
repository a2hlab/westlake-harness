OpenHarmony Source Patches for Android Adapter
===============================================

These patches modify OH ability_rt source to support multi-Ability Mission stacks,
enabling Android apps to maintain their Task/Activity stack behavior on OH.

Changes are minimal and backward-compatible:
  - OH native apps: behavior completely unchanged (single Ability per Mission)
  - Android adapted apps: Mission holds an Ability stack (multiple Activities)

How to apply:
  1. Run build/apply_ohos_patches.sh (strict exact-oracle application)
  2. Rebuild ability_rt module

wukong100 full-product invariant (R45 / OH6.1 LTS):
  - build/ohos/app/app_internal.gni.patch and
    build/config/components/ets_frontend/ets2abc_config.gni.collision_fix.patch
    are HanBing OH7/rk3568 module-only cuts. They are historical inputs, not
    members of the wukong100 full-product Phase-0 manifest.
  - vendor/revoview/wukong100/config.json.patch (in-tree oh_adapter component)
    and foundation/arkui/ui_lite/ext/updater/BUILD.gn.patch (removed official
    graphic_utils_lite dependency) are also retired from that manifest.
  - The canonical wrapper pins all four official full-product files to SHA256:
    app_internal.gni =
    595c739b0741f9fbc1e32990cb1d95bee37bd2fd68daae17e65b726ff44edd1c;
    ets2abc_config.gni =
    28fc4cdcd620fda21c3cb6728d5cfc6a40f0162b93247f2ab86c2c5d4d763867;
    wukong100/config.json =
    45a94f39a529b81577542b02900bbea82dca74d9d8368dd30eb994c9a8b951bd;
    updater/BUILD.gn =
    2a59138648ef7e8771836ea532c7effde7c1fb7387f45bdd74f1bf1cfcc81e13.
  - A generated HAP command must use obj/developtools/.../*_loader_ark.
    Static /developtools/... or ../../../../../developtools paths are a hard
    failure; do not repair them with npm install, copies, or symlinks.

Files modified:
  ability_rt/services/abilitymgr/include/mission/mission.h
    - abilityRecord_ changed to abilityStack_ (vector)
    - Added: PushAbility, PopAbility, GetAbilityStackSize, GetBaseAbilityRecord,
             FindAbilityByName, PopAbilitiesAbove, IsMultiAbilityMode, SetMultiAbilityMode

  ability_rt/services/abilitymgr/src/mission/mission.cpp
    - Implementation of all new methods
    - GetAbilityRecord() returns stack top (backward compatible)
    - Constructor puts initial ability into stack (backward compatible)

  ability_rt/interfaces/inner_api/ability_manager/include/ability_manager_interface.h
    - Added: StartAbilityInMission(Want, missionId) IPC method
