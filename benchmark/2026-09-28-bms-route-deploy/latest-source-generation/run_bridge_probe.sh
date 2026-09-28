#!/usr/bin/env bash
set -eu
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
W=$ROOT/bms/src/.work/b6-latest
export BUILD_INNER_INVOKED=1 ADAPTER_ROOT=$W/adapter ADAPTER_OUT_DIR=$W/out BRIDGE_OBJ_DIR=${B6_BRIDGE_OBJ_DIR:-$W/bridge-objects}
export OH_ROOT=$W/oh AOSP_ROOT=/Users/zhaoyue/aosp-r4-incs OH_SDK=$W/sdk FORCE_OH_SDK=1
export OH61_GENERATED_HEADERS=$W/generated
export OH_RESOURCE_MANAGEMENT_ROOT=/Users/zhaoyue/orca/00.Workspace-games-b-80488f37/.bridge-payload/oh-source-inputs/global_resource_management
export R3_SKIA_ROOT=/Users/zhaoyue/orca/00.Workspace-games-b-80488f37/.bridge-payload/oh-source-inputs/third_party_skia/m133
export OH_LIBCXX_INCLUDE=$ROOT/bms/src/.work/product-tls-generation/frozen/toolchain/include/c++/v1
export CPLUS_INCLUDE_PATH=$W/oh/foundation/ability/ability_runtime/interfaces/kits/native/ability/native:/Users/zhaoyue/orca/00.Workspace-games-b-80488f37/.bridge-payload/oh-source-inputs/window_window_manager/utils/include
MIRROR=$W/adapter/sources/oh61-v7-b2133b5b/local_oh_headers/oh_mirror
export CPLUS_INCLUDE_PATH=$CPLUS_INCLUDE_PATH:$MIRROR/foundation/window/window_manager/window_scene:$MIRROR/foundation/systemabilitymgr/samgr/interfaces/innerkits/dynamic_cache/include:$W/oh/foundation/ability/ability_runtime/interfaces/kits/native/appkit/app:$MIRROR/foundation/graphic/graphic_2d/rosen/modules/2d_graphics/src/drawing/engine_adapter:$MIRROR/foundation/graphic/graphic_surface/interfaces/inner_api/sync_fence:$MIRROR/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_base/include/clone:$W/oh/foundation/barrierfree/accessibility/interfaces/innerkits/aafwk/include
export CPLUS_INCLUDE_PATH=$CPLUS_INCLUDE_PATH:$MIRROR/foundation/window/window_manager/utils/include:$W/oh/foundation/barrierfree/accessibility/interfaces/innerkits/common/include:$MIRROR/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_core/include/app_control
export CPLUS_INCLUDE_PATH=$CPLUS_INCLUDE_PATH:$W/oh/base/account/os_account/interfaces/innerkits/osaccount/native/include:$W/oh/base/account/os_account/interfaces/innerkits/common/include:$W/oh/base/account/os_account/interfaces/innerkits/domain_account/native/include
export CPLUS_INCLUDE_PATH=$CPLUS_INCLUDE_PATH:$W/adapter/framework/package-manager/compatibility/include
bash "$W/${B6_BRIDGE_PROBE_SCRIPT:-bridge-first-unit.sh}"
