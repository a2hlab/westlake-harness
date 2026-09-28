#!/usr/bin/env bash
set -euo pipefail

OH_ROOT=${1:-/opt/build-trees/oh610_lts_source}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT_DIR=${FN01_AUDIT_OUT:-"$SCRIPT_DIR/out"}

mkdir -p "$OUT_DIR"

if [[ ${FN01_AUDIT_CAPTURE:-0} != 1 ]]; then
  set +e
  FN01_AUDIT_CAPTURE=1 "$0" "$OH_ROOT" >"$OUT_DIR/source-audit.log" 2>&1
  audit_status=$?
  set -e
  cat "$OUT_DIR/source-audit.log"
  exit "$audit_status"
fi

files=(
  foundation/systemabilitymgr/safwk/services/safwk/include/system_ability.h
  foundation/systemabilitymgr/safwk/test/mock/common/demo_sa/src/demo_service.cpp
  foundation/systemabilitymgr/samgr/services/samgr/native/source/system_ability_manager_stub.cpp
  foundation/systemabilitymgr/samgr/services/samgr/native/source/system_ability_manager.cpp
  foundation/systemabilitymgr/samgr/interfaces/innerkits/samgr_proxy/include/if_system_ability_manager.h
  foundation/systemabilitymgr/samgr/interfaces/innerkits/samgr_proxy/include/system_ability_definition.h
  base/security/selinux_adapter/sepolicy/ohos_policy/arkXtest/testserver/public/service_contexts
  base/security/selinux_adapter/sepolicy/ohos_policy/arkXtest/testserver/public/test_server.te
  foundation/bundlemanager/bundle_framework/sa_profile/401.json
  foundation/bundlemanager/bundle_framework/services/bundlemgr/src/bundle_permission_mgr.cpp
  foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_core/include/bundle_framework_core_ipc_interface_code.h
  foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_core/src/bundlemgr/bundle_mgr_proxy.cpp
  foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_core/src/bundlemgr/bundle_mgr_host.cpp
  foundation/bundlemanager/bundle_framework/interfaces/inner_api/bundlemgr_extension/src/bms_extension_data_mgr.cpp
  foundation/bundlemanager/bundle_framework/interfaces/inner_api/bundlemgr_extension/include/bundle_mgr_ext_register.h
  foundation/bundlemanager/bundle_framework/interfaces/inner_api/bundlemgr_extension/include/bundle_mgr_ext.h
)

printf 'AUDIT_HOST=%s\n' "$(hostname)"
printf 'AUDIT_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'OH_ROOT=%s\n' "$OH_ROOT"
printf 'OH_MANIFEST_COMMIT=%s\n' \
  "$(git -C "$OH_ROOT/.repo/manifests" rev-parse HEAD)"
for file in "${files[@]}"; do
  sha256sum "$OH_ROOT/$file"
done

printf '%s\n' '--- E1 SA registration anchors ---'
grep -n \
  'REGISTER_SYSTEM_ABILITY_BY_ID\|void DemoService::OnStart\|Publish(this)' \
  "$OH_ROOT/foundation/systemabilitymgr/safwk/test/mock/common/demo_sa/src/demo_service.cpp"
grep -n \
  'AddServiceCheck\|CheckAddOrRemovePermission\|AddSystemAbilityInner' \
  "$OH_ROOT/foundation/systemabilitymgr/samgr/services/samgr/native/source/system_ability_manager_stub.cpp" |
  sed -n '1,20p'
grep -n \
  'AddSystemAbility(int32_t systemAbilityId' \
  "$OH_ROOT/foundation/systemabilitymgr/samgr/services/samgr/native/source/system_ability_manager.cpp" |
  sed -n '1,5p'

printf '%s\n' '--- E1 test SA SELinux anchors ---'
grep -n '^5502' \
  "$OH_ROOT/base/security/selinux_adapter/sepolicy/ohos_policy/arkXtest/testserver/public/service_contexts"
grep -n 'sa_test_server:samgr_class' \
  "$OH_ROOT/base/security/selinux_adapter/sepolicy/ohos_policy/arkXtest/testserver/public/test_server.te"

printf '%s\n' '--- E2 peer identity anchors ---'
grep -n \
  'IPCSkeleton::GetCallingUid()\|IPCSkeleton::GetCallingPid()\|IPCSkeleton::GetCallingTokenID()' \
  "$OH_ROOT/foundation/bundlemanager/bundle_framework/services/bundlemgr/src/bundle_permission_mgr.cpp" |
  sed -n '1,30p'

printf '%s\n' '--- E3 BMS read-only transaction anchors ---'
grep -n \
  'GET_NAME_FOR_UID =\|BundleMgrProxy::GetNameForUid\|HandleGetNameForUid' \
  "$OH_ROOT/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_core/include/bundle_framework_core_ipc_interface_code.h" \
  "$OH_ROOT/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_core/src/bundlemgr/bundle_mgr_proxy.cpp" \
  "$OH_ROOT/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_core/src/bundlemgr/bundle_mgr_host.cpp" |
  sed -n '1,20p'

printf '%s\n' '--- E4 BMS extension anchors ---'
grep -n \
  'BMS_EXTENSION_PATH\|dlopen\|RTLD_NOW\|GetBundleMgrExt' \
  "$OH_ROOT/foundation/bundlemanager/bundle_framework/interfaces/inner_api/bundlemgr_extension/src/bms_extension_data_mgr.cpp" |
  sed -n '1,30p'
grep -n \
  'REGISTER_BUNDLEMGR_EXT\|virtual ErrCode GetBundleInfo\|virtual ErrCode Uninstall\|virtual ErrCode ClearData' \
  "$OH_ROOT/foundation/bundlemanager/bundle_framework/interfaces/inner_api/bundlemgr_extension/include/bundle_mgr_ext_register.h" \
  "$OH_ROOT/foundation/bundlemanager/bundle_framework/interfaces/inner_api/bundlemgr_extension/include/bundle_mgr_ext.h" |
  sed -n '1,30p'

printf '%s\n' '--- BMS component tracked differences ---'
git -C "$OH_ROOT/foundation/bundlemanager/bundle_framework" \
  status --short --untracked-files=no
