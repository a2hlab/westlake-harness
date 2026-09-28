#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MANIFEST=${1:?usage: run_unity_native_bringup_fixture.sh MANIFEST.tsv FIXTURE APP_DIR BRIDGE_DIR IDENTITY_RECEIPT [--java-vm ADDRESS]}
FIXTURE=${2:?missing fixture}
APP_DIR=${3:?missing app dir}
BRIDGE_DIR=${4:?missing bridge dir}
IDENTITY_RECEIPT=${5:?missing generation-private identity receipt}
shift 5

READELF=${OH_READELF:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/llvm-readelf}
SHA256=${SHA256_TOOL:-sha256sum}
RUN_ID=${UNITY_FIXTURE_RUN_ID:-$(date -u '+%Y%m%dT%H%M%SZ')}
EVIDENCE_ROOT=${UNITY_FIXTURE_EVIDENCE_ROOT:-$ROOT/research/atoms/L03/A12/evidence/runs}
OUT=$EVIDENCE_ROOT/$RUN_ID-unity-native-bringup

case "$OUT" in "$ROOT"/*) ;; *) echo "evidence path escapes adapter" >&2; exit 2 ;; esac
test ! -e "$OUT"
mkdir -p "$OUT"
exec > >(tee "$OUT/run.log") 2>&1

test -x "$FIXTURE"
test -d "$APP_DIR"
test -d "$BRIDGE_DIR"
test -f "$MANIFEST"
test -f "$IDENTITY_RECEIPT"
test -x "$READELF"

python3 "$ROOT/scripts/verify_unity_fixture_identity.py" \
  --identity-receipt "$IDENTITY_RECEIPT" \
  --fixture-manifest "$MANIFEST"

declare -A PATHS SHAS BUILDS
while IFS=$'\t' read -r role path sha build_id; do
  case "$role" in ''|'#'*) continue ;; esac
  test -n "$path" && test -n "$sha" && test -n "$build_id"
  test -f "$path"
  actual=$($SHA256 "$path" | awk '{print $1}')
  test "$actual" = "$sha"
  PATHS[$role]=$path
  SHAS[$role]=$sha
  BUILDS[$role]=$build_id
done < "$MANIFEST"

for role in main unity il2cpp app_native_loader native_loader native_helper musl_loader dlns_provider; do
  test -n "${PATHS[$role]:-}"
done
test "${PATHS[main]}" = "$APP_DIR/libmain.so"
test "${PATHS[unity]}" = "$APP_DIR/libunity.so"
test "${PATHS[il2cpp]}" = "$APP_DIR/libil2cpp.so"

for role in main unity il2cpp app_native_loader native_loader native_helper musl_loader dlns_provider; do
  file=${PATHS[$role]}
  "$READELF" -h "$file" | grep -E 'Class:[[:space:]]+ELF64' >/dev/null
  "$READELF" -h "$file" | grep -E 'Machine:[[:space:]]+AArch64' >/dev/null
  actual_build=$($READELF -n "$file" | awk '/Build ID:/{print $3; exit}')
  test -n "$actual_build"
  test "$actual_build" = "${BUILDS[$role]}"
done

"$READELF" -d "${PATHS[unity]}" | grep 'Shared library: \[libmain.so\]' >/dev/null
"$READELF" -d "${PATHS[unity]}" | grep -E '\(INIT_ARRAY\)|\(INIT\)' >/dev/null
"$READELF" -d "${PATHS[il2cpp]}" | grep -E '\(INIT_ARRAY\)|\(INIT\)' >/dev/null
"$READELF" -d "${PATHS[main]}" > "$OUT/libmain.dynamic.txt"
"$READELF" -d "${PATHS[unity]}" > "$OUT/libunity.dynamic.txt"
"$READELF" -d "${PATHS[native_loader]}" > "$OUT/libnativeloader.dynamic.txt"
cp "$MANIFEST" "$OUT/input-manifest.tsv"

if [[ ${UNITY_FIXTURE_PREFLIGHT_ONLY:-0} == 1 ]]; then
  printf 'fixture_rc=not-run\nstatus=candidate_static_preflight_not_proven\n' > "$OUT/result.txt"
  printf 'UNITY_FIXTURE_NOT_PROVEN reason=preflight-only\n'
  (
    cd "$OUT"
    $SHA256 input-manifest.tsv libmain.dynamic.txt libunity.dynamic.txt \
      libnativeloader.dynamic.txt result.txt run.log > EVIDENCE.sha256
  )
  printf 'UNITY_NATIVE_BRINGUP_PREFLIGHT_RECEIPT=%s\n' "$OUT"
  exit 0
fi

PROVIDER_FRAGMENT=$(basename "${PATHS[app_native_loader]}")
set +e
env -i PATH=/system/bin:/bin \
  "$FIXTURE" "$APP_DIR" "$BRIDGE_DIR" "$PROVIDER_FRAGMENT" \
  "${PATHS[main]}" "${PATHS[unity]}" "${PATHS[il2cpp]}" "$@"
rc=$?
set -e
printf 'fixture_rc=%s\n' "$rc" | tee "$OUT/result.txt"
test "$rc" = 0

if (($# == 0)); then
  grep -F 'UNITY_FIXTURE_NOT_PROVEN reason=no-formal-java-vm-receipt' "$OUT/run.log" >/dev/null
  printf 'status=candidate_preflight_not_proven\n' >> "$OUT/result.txt"
else
  test "$1" = --java-vm
  grep -F 'UNITY_FIXTURE_JNI_DISPATCH_GATE_PASS main_jni=1 unity_loaded=1 il2cpp_loaded=1 inner_jni_calls_by_fixture=0' "$OUT/run.log" >/dev/null
  grep -F 'UNITY_FIXTURE_NOT_PROVEN reason=native-entry-marker-not-observed' "$OUT/run.log" >/dev/null
  printf 'status=formal_jni_dispatch_pass_native_entry_not_proven\n' >> "$OUT/result.txt"
fi

(
  cd "$OUT"
  $SHA256 input-manifest.tsv libmain.dynamic.txt libunity.dynamic.txt \
    libnativeloader.dynamic.txt result.txt run.log > EVIDENCE.sha256
)
printf 'UNITY_NATIVE_BRINGUP_RECEIPT=%s\n' "$OUT"
