#!/usr/bin/env bash
# Host (Linux) developer test for ApkInstaller::ExtractAndPackResourceHap
# icon-less APK handling. Compiles the REAL jni production sources against
# host shims (hilog, directory_ex) and OH-tree minizip, then runs
# P01/N01/N02 and greps the typed alarm tokens from captured stderr.
# Never issues a formal PASS.
#
# Required env:
#   OH_ROOT     OH source tree providing third_party/zlib/contrib/minizip
#               and the linux-x86_64 clang prebuilt
# Optional env:
#   RESOURCES_HAP_HOST_OUT  output dir (default <repo>/.work/resources-hap-host)
set -euo pipefail
IFS=$'\n\t'
umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
# The adapter root is the directory that CONTAINS framework/package-manager.
# Repo root differs by layout: <repo>/src/adapter locally vs
# <sync>/adapter on the build host — detect via the imports/ dir.
PM_ADAPTER=$(cd "$PACKAGE_DIR/../.." && pwd -P)
if [[ -d "$PM_ADAPTER/../imports" ]]; then
    REPO_ROOT=$(cd "$PM_ADAPTER/.." && pwd -P)
elif [[ -d "$PM_ADAPTER/../../imports" ]]; then
    REPO_ROOT=$(cd "$PM_ADAPTER/../.." && pwd -P)
else
    echo "ERROR: cannot locate repo imports/ dir above $PM_ADAPTER" >&2
    exit 2
fi

: "${OH_ROOT:?OH_ROOT is required (minizip + clang prebuilt)}"
MINIZIP_DIR="$OH_ROOT/third_party/zlib/contrib/minizip"
ZLIB_DIR="$OH_ROOT/third_party/zlib"
CXX="$OH_ROOT/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++"
CC="$OH_ROOT/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang"
G1_APK="$REPO_ROOT/imports/demo-inputs/G1-helloworld/HelloWorld.apk"

for p in "$MINIZIP_DIR/unzip.c" "$MINIZIP_DIR/zip.c" "$MINIZIP_DIR/ioapi.c" \
    "$CXX" "$CC" "$G1_APK"; do
    [[ -e "$p" ]] || { echo "ERROR: missing input: $p" >&2; exit 2; }
done

OUT=${RESOURCES_HAP_HOST_OUT:-$REPO_ROOT/.work/resources-hap-host}
case "$OUT" in
    "$REPO_ROOT"/*) ;;
    *) echo "ERROR: output escaped project: $OUT" >&2; exit 2 ;;
esac
if [[ -L "$OUT" ]]; then
    echo "ERROR: refusing symlinked output: $OUT" >&2; exit 2
fi
rm -rf "$OUT"
mkdir -p "$OUT/fixtures" "$OUT/scratch"

INC=(
    -I"$SCRIPT_DIR/host_shims"
    -I"$PACKAGE_DIR/jni"
    -I"$PM_ADAPTER/third_party/lodepng"
    -I"$MINIZIP_DIR"
    -I"$ZLIB_DIR"
)

"$CC" -std=c11 -O2 -DUSE_FILE32API "${INC[@]}" \
    -c "$MINIZIP_DIR/unzip.c" -o "$OUT/unzip.o"
"$CC" -std=c11 -O2 -DUSE_FILE32API "${INC[@]}" \
    -c "$MINIZIP_DIR/zip.c" -o "$OUT/zip.o"
"$CC" -std=c11 -O2 -DUSE_FILE32API "${INC[@]}" \
    -c "$MINIZIP_DIR/ioapi.c" -o "$OUT/ioapi.o"

"$CXX" -std=c++17 -Wall -Wextra -O2 "${INC[@]}" \
    "$PACKAGE_DIR/jni/apk_installer.cpp" \
    "$PACKAGE_DIR/jni/apk_label_resolver.cpp" \
    "$PACKAGE_DIR/jni/arsc_resolver.cpp" \
    "$PACKAGE_DIR/jni/apk_manifest_parser.cpp" \
    "$PACKAGE_DIR/jni/axml_parser.cpp" \
    "$PACKAGE_DIR/jni/icon_normalize.cpp" \
    "$PM_ADAPTER/third_party/lodepng/lodepng.cpp" \
    "$SCRIPT_DIR/test_resources_hap.cpp" \
    "$OUT/unzip.o" "$OUT/zip.o" "$OUT/ioapi.o" \
    -lz -o "$OUT/test_resources_hap"

python3 "$SCRIPT_DIR/make_resources_hap_fixtures.py" "$G1_APK" "$OUT/fixtures"

LOG="$OUT/run.log"
if ! "$OUT/test_resources_hap" "$OUT/fixtures" "$OUT/scratch" 2>"$LOG"; then
    echo "ERROR: test binary failed" >&2
    cat "$LOG" >&2
    exit 1
fi

# Typed alarm tokens must be loud and present exactly once for the allowed
# icon-less path, and the fail-closed refusal must fire for both tamper cases.
test "$(grep -c 'ICONLESS_APK_TEMPLATE_PLACEHOLDER' "$LOG")" -eq 1
grep -Eq 'ICONLESS_APK_TEMPLATE_PLACEHOLDER.*class=(NOT_DECLARED|DECLARED_MISSING_ALL_BUCKETS)' "$LOG"
test "$(grep -c 'refusing template placeholder' "$LOG")" -eq 2

echo "DEVELOPER_TEST_READY_FOR_HANDOFF module=resources_hap_iconless formal_verdict=NOT_ISSUED evidence=$OUT"
