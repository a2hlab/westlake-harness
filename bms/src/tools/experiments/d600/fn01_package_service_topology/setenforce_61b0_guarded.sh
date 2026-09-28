#!/usr/bin/env bash
set -euo pipefail

HDC=${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}
ALLOW_TARGET=61b0657200000000000000000324012c
TARGET=${1:-}
TARGET=$(printf '%s' "$TARGET" | tr '[:upper:]' '[:lower:]')
OUT_DIR=${FN01_SETENFORCE_OUT:-"$(pwd)"}

if [[ "$TARGET" == 5eab* ]]; then
  echo "REFUSE_5EAB target=$TARGET" >&2
  exit 64
fi
if [[ "$TARGET" != "$ALLOW_TARGET" ]]; then
  echo "REFUSE_NON_61B0 target=$TARGET" >&2
  exit 65
fi

mkdir -p "$OUT_DIR"
if [[ ${FN01_SETENFORCE_CAPTURE:-0} != 1 ]]; then
  set +e
  FN01_SETENFORCE_CAPTURE=1 "$0" "$TARGET" \
    >"$OUT_DIR/setenforce-$TARGET.log" 2>&1
  operation_status=$?
  set -e
  cat "$OUT_DIR/setenforce-$TARGET.log"
  exit "$operation_status"
fi

read_binding()
{
  "$HDC" -t "$TARGET" shell '
    echo SERIAL
    param get ohos.boot.sn
    echo BOOT_ID
    cat /proc/sys/kernel/random/boot_id
    printf "\n"
    echo SELINUX_ENFORCE
    cat /sys/fs/selinux/enforce
    printf "\n"
  ' | tr -d '\r'
}

parse_field()
{
  local label=$1
  awk -v label="$label" \
    '$0 == label {getline; gsub(/[[:space:]]/, ""); print tolower($0); exit}'
}

target_list=$("$HDC" list targets -v)
printf '%s\n' "$target_list"
if ! printf '%s\n' "$target_list" |
  grep -F "$TARGET" |
  grep -F 'Connected' >/dev/null; then
  echo "TARGET_NOT_CONNECTED target=$TARGET" >&2
  exit 66
fi

printf 'MUTATION_SCOPE=setenforce-1-only\n'
printf 'TARGET=%s\n' "$TARGET"
printf 'STARTED_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%s\n' '--- BEFORE ---'
before=$(read_binding)
printf '%s\n' "$before"
before_serial=$(printf '%s\n' "$before" | parse_field SERIAL)
before_boot=$(printf '%s\n' "$before" | parse_field BOOT_ID)
before_enforce=$(printf '%s\n' "$before" | parse_field SELINUX_ENFORCE)
if [[ "$before_serial" != "$TARGET" ||
      ! "$before_boot" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
  echo "BEFORE_BINDING_INVALID serial=$before_serial boot=$before_boot" >&2
  exit 67
fi

printf '%s\n' '--- MUTATION ---'
printf 'COMMAND=%q -t %q shell %q\n' \
  "$HDC" "$TARGET" "setenforce 1"
set +e
mutation=$(
  "$HDC" -t "$TARGET" shell \
    'setenforce 1; operation_rc=$?; printf "\nSETENFORCE_RC=%s\n" "$operation_rc"; echo SELINUX_ENFORCE_READBACK; cat /sys/fs/selinux/enforce; printf "\n"; exit "$operation_rc"' \
    2>&1
)
hdc_rc=$?
set -e
mutation=$(printf '%s\n' "$mutation" | tr -d '\r')
printf '%s\n' "$mutation"
printf 'HDC_RC=%s\n' "$hdc_rc"
remote_rc=$(
  printf '%s\n' "$mutation" |
    sed -n 's/^SETENFORCE_RC=\([0-9][0-9]*\)$/\1/p' |
    tail -1
)
readback=$(
  printf '%s\n' "$mutation" |
    parse_field SELINUX_ENFORCE_READBACK
)

printf '%s\n' '--- AFTER ---'
after=$(read_binding)
printf '%s\n' "$after"
after_serial=$(printf '%s\n' "$after" | parse_field SERIAL)
after_boot=$(printf '%s\n' "$after" | parse_field BOOT_ID)
after_enforce=$(printf '%s\n' "$after" | parse_field SELINUX_ENFORCE)

if [[ "$hdc_rc" -ne 0 || "$remote_rc" != 0 ]]; then
  echo "SETENFORCE_COMMAND_FAILED hdc_rc=$hdc_rc remote_rc=${remote_rc:-missing}" >&2
  exit 68
fi
if [[ "$after_serial" != "$TARGET" || "$after_boot" != "$before_boot" ]]; then
  echo "POST_MUTATION_BINDING_DRIFT serial=$after_serial before_boot=$before_boot after_boot=$after_boot" >&2
  exit 69
fi
if [[ "$readback" != 1 || "$after_enforce" != 1 ]]; then
  echo "SETENFORCE_READBACK_FAILED mutation=$readback after=$after_enforce" >&2
  exit 70
fi

printf 'SETENFORCE_GUARD_PASS target=%s boot_id=%s before=%s after=%s\n' \
  "$TARGET" "$after_boot" "$before_enforce" "$after_enforce"
