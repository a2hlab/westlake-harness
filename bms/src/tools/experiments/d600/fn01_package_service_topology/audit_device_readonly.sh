#!/usr/bin/env bash
set -euo pipefail

HDC=${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}
TARGET=${1:-61b0657200000000000000000324012c}
TARGET=$(printf '%s' "$TARGET" | tr '[:upper:]' '[:lower:]')
ALLOW_61B0=61b0657200000000000000000324012c
ALLOW_654B=654b3a6b00000000000000000824012c
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT_DIR=${FN01_DEVICE_AUDIT_OUT:-"$SCRIPT_DIR/out-device-audit"}

if [[ "$TARGET" == 5eab* ]]; then
  echo "REFUSE_5EAB target=$TARGET" >&2
  exit 64
fi
if [[ "$TARGET" != "$ALLOW_61B0" && "$TARGET" != "$ALLOW_654B" ]]; then
  echo "REFUSE_NON_ALLOWLISTED_TARGET target=$TARGET" >&2
  exit 65
fi

mkdir -p "$OUT_DIR"
if [[ ${FN01_DEVICE_AUDIT_CAPTURE:-0} != 1 ]]; then
  set +e
  FN01_DEVICE_AUDIT_CAPTURE=1 "$0" "$TARGET" \
    >"$OUT_DIR/device-audit-$TARGET.log" 2>&1
  audit_status=$?
  set -e
  cat "$OUT_DIR/device-audit-$TARGET.log"
  exit "$audit_status"
fi

printf 'AUDIT_HOST=%s\n' "$(hostname)"
printf 'AUDIT_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'HDC=%s\n' "$HDC"
printf 'TARGET=%s\n' "$TARGET"
target_list=$("$HDC" list targets -v)
printf '%s\n' "$target_list"
if ! printf '%s\n' "$target_list" |
  grep -F "$TARGET" |
  grep -F 'Connected' >/dev/null; then
  echo "TARGET_NOT_CONNECTED target=$TARGET" >&2
  exit 66
fi

device_receipt=$("$HDC" -t "$TARGET" shell '
  echo DEVICE_BINDING
  echo SERIAL
  param get ohos.boot.sn
  echo BOOT_ID
  cat /proc/sys/kernel/random/boot_id
  printf "\n"
  echo SOFTWARE
  param get const.product.software.version
  echo SELINUX_ENFORCE
  cat /sys/fs/selinux/enforce
  printf "\n"
  echo DEVICE_IDENTITY
  id
  cat /proc/self/attr/current
  param get const.product.name
  param get const.product.software.version
  echo PROCESS_BASELINE
  ps -A -o PID,UID,NAME | grep -E "foundation|appspawn-x"
  echo BMS_EXTENSION_PROFILE
  ls -l /system/etc/app/bms-extensions.json 2>&1
  sha256sum /system/etc/app/bms-extensions.json 2>&1
  echo BMS_EXTENSION_LIBRARY
  ls -l /system/lib64/libbundlemgr_extension.z.so 2>&1
  sha256sum /system/lib64/libbundlemgr_extension.z.so 2>&1
  echo BMS_AND_SAMGR_LIBRARIES
  sha256sum \
    /system/lib64/platformsdk/libsamgr_proxy.z.so \
    /system/lib64/platformsdk/libsamgr_common.z.so \
    /system/lib64/platformsdk/libipc_single.z.so \
    /system/lib64/platformsdk/libutils.z.so \
    /system/lib64/chipset-sdk-sp/libc++.so \
    /system/lib/ld-musl-aarch64.so.1 \
    /system/lib64/platformsdk/libappexecfwk_core.z.so 2>&1
  echo PROJECT_PRIVATE_SA_127233_BASELINE
  hidumper -s 127233 2>&1
')
device_receipt=$(printf '%s\n' "$device_receipt" | tr -d '\r')
printf '%s\n' "$device_receipt"

observed_serial=$(
  printf '%s\n' "$device_receipt" |
    awk '/^SERIAL$/{getline; gsub(/[[:space:]]/, ""); print tolower($0); exit}'
)
observed_boot_id=$(
  printf '%s\n' "$device_receipt" |
    awk '/^BOOT_ID$/{getline; gsub(/[[:space:]]/, ""); print tolower($0); exit}'
)
observed_enforce=$(
  printf '%s\n' "$device_receipt" |
    awk '/^SELINUX_ENFORCE$/{getline; gsub(/[[:space:]]/, ""); print; exit}'
)
if [[ "$observed_serial" != "$TARGET" ]]; then
  echo "DEVICE_SERIAL_MISMATCH expected=$TARGET actual=$observed_serial" >&2
  exit 67
fi
if [[ ! "$observed_boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
  echo "DEVICE_BOOT_ID_INVALID value=$observed_boot_id" >&2
  exit 68
fi
if [[ "$observed_enforce" != 1 ]]; then
  echo "SELINUX_NOT_ENFORCING value=$observed_enforce" >&2
  exit 70
fi

expected_rows=(
  "a97fe3dc89365d6e37b44cd130aaf89f3ea30f788f1039301a9bd169d205a107 /system/lib64/platformsdk/libsamgr_proxy.z.so"
  "bb919eb31e6f1b1e58f6578619724fdb1d0d6cf79c1f42a32435b335e3cad51f /system/lib64/platformsdk/libsamgr_common.z.so"
  "f6742ea92c89d4400d69201ec5ac47261dcfeb0945951ecc5ae44041ff6bd4f8 /system/lib64/platformsdk/libipc_single.z.so"
  "66bdf65d494437eae03b4cb4a6f277e65f1832de5d79634d350d01b69e079d1a /system/lib64/platformsdk/libutils.z.so"
  "9466fb0d933689533bdf4b4962907f3e0c0970be278bd6ccf703ffa2aea838a6 /system/lib64/chipset-sdk-sp/libc++.so"
  "fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2 /system/lib/ld-musl-aarch64.so.1"
)
for row in "${expected_rows[@]}"; do
  expected_hash=${row%% *}
  expected_path=${row#* }
  actual_hash=$(
    printf '%s\n' "$device_receipt" |
      awk -v path="$expected_path" '$2 == path {print $1; exit}'
  )
  if [[ "$actual_hash" != "$expected_hash" ]]; then
    echo "RUNTIME_HASH_MISMATCH path=$expected_path expected=$expected_hash actual=${actual_hash:-missing}" >&2
    exit 69
  fi
  printf 'RUNTIME_HASH_MATCH path=%s sha256=%s\n' \
    "$expected_path" "$actual_hash"
done
printf 'DEVICE_AUDIT_MATCH target=%s boot_id=%s runtime_input_count=%s\n' \
  "$TARGET" "$observed_boot_id" "${#expected_rows[@]}"
