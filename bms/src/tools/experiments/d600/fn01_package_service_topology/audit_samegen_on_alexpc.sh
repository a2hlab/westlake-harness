#!/usr/bin/env bash
set -euo pipefail

OH_ROOT=${1:-/opt/build-trees/oh610_lts_source}
RUNTIME_ROOT=${2:-"$OH_ROOT/out/wukong100/packages/phone/system"}
RECEIPT=${3:-}
RELEASE_REFERENCE=${4:-/opt/build-trees/_release-reference/dayu600-6.1.0.31_sp7}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT_DIR=${FN01_SAMEGEN_AUDIT_OUT:-"$SCRIPT_DIR/out"}

mkdir -p "$OUT_DIR"
if [[ ${FN01_SAMEGEN_AUDIT_CAPTURE:-0} != 1 ]]; then
  set +e
  FN01_SAMEGEN_AUDIT_CAPTURE=1 "$0" \
    "$OH_ROOT" "$RUNTIME_ROOT" "$RECEIPT" "$RELEASE_REFERENCE" \
    >"$OUT_DIR/samegen-audit.log" 2>&1
  audit_status=$?
  set -e
  cat "$OUT_DIR/samegen-audit.log"
  exit "$audit_status"
fi

if [[ -z "$RECEIPT" || ! -f "$RECEIPT" ]]; then
  echo "RECEIPT_REQUIRED path=$RECEIPT" >&2
  exit 64
fi

printf 'AUDIT_HOST=%s\n' "$(hostname)"
printf 'AUDIT_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'OH_ROOT=%s\n' "$OH_ROOT"
printf 'RUNTIME_ROOT=%s\n' "$RUNTIME_ROOT"
printf 'OH_MANIFEST_COMMIT=%s\n' \
  "$(git -C "$OH_ROOT/.repo/manifests" rev-parse HEAD)"
printf 'RELEASE_MANIFEST_SHA256=%s\n' \
  "$(sha256sum "$RELEASE_REFERENCE/manifest_tag.xml" | awk '{print $1}')"
printf 'RELEASE_TARBALL_SHA256=%s\n' \
  "$(sha256sum "$RELEASE_REFERENCE/release.tar.gz" | awk '{print $1}')"
printf 'RUNTIME_RECEIPT_SHA256=%s\n' \
  "$(sha256sum "$RECEIPT" | awk '{print $1}')"

count=0
while read -r expected_hash device_path extra; do
  if [[ -z "$expected_hash" || "$expected_hash" == \#* ]]; then
    continue
  fi
  if [[ -n "${extra:-}" || "$device_path" != /* ]]; then
    echo "RECEIPT_ROW_INVALID path=$device_path" >&2
    exit 65
  fi
  package_path=$RUNTIME_ROOT$device_path
  actual_hash=$(sha256sum "$package_path" | awk '{print $1}')
  if [[ "$actual_hash" != "$expected_hash" ]]; then
    echo "PACKAGE_HASH_MISMATCH path=$package_path expected=$expected_hash actual=$actual_hash" >&2
    exit 66
  fi
  printf 'PACKAGE_HASH_MATCH path=%s sha256=%s\n' \
    "$package_path" "$actual_hash"
  count=$((count + 1))
done <"$RECEIPT"
if [[ "$count" -ne 6 ]]; then
  echo "RECEIPT_COUNT_INVALID expected=6 actual=$count" >&2
  exit 67
fi

link_libcxx=$OH_ROOT/prebuilts/clang/ohos/linux-x86_64/llvm/lib/aarch64-linux-ohos/libc++.so
package_libcxx=$RUNTIME_ROOT/lib64/chipset-sdk-sp/libc++.so
link_libc=$OH_ROOT/out/wukong100/obj/third_party/musl/usr/lib/aarch64-linux-ohos/libc.so
package_libc=$RUNTIME_ROOT/lib/ld-musl-aarch64.so.1

printf '%s\n' '--- LINK_VS_PACKAGE_IDENTITY ---'
sha256sum "$link_libcxx" "$package_libcxx" "$link_libc" "$package_libc"
file "$link_libcxx" "$package_libcxx" "$link_libc" "$package_libc"
for library in "$link_libcxx" "$package_libcxx" "$link_libc" "$package_libc"; do
  printf 'BUILD_ID path=%s value=' "$library"
  readelf -n "$library" 2>/dev/null |
    sed -n 's/.*Build ID: //p' |
    head -1
done

printf 'SAMEGEN_PACKAGE_RECEIPT_MATCH count=%s\n' "$count"
