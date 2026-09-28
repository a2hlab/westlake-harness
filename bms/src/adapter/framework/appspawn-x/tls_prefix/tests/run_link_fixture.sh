#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PREFIX_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../../../.." && pwd)
OH_ROOT=${OH_ROOT:-/opt/10.Project/16-WestLake/16.12-HanBing/oh}
OH_PRODUCT_NAME=${OH_PRODUCT_NAME:-wukong100}
OH_OUT="$OH_ROOT/out/$OH_PRODUCT_NAME"
SYSROOT="$OH_OUT/obj/third_party/musl/usr"
MUSL_LIB="$SYSROOT/lib/aarch64-linux-ohos"
LLVM_BIN="$OH_ROOT/prebuilts/clang/ohos/linux-x86_64/llvm/bin"
BC_INCLUDE=$PREFIX_DIR/../bionic_compat/include
CXX=${CXX:-$LLVM_BIN/clang++}
READELF=${READELF:-$LLVM_BIN/llvm-readelf}
WORK=$SCRIPT_DIR/.work/link-fixture.$$

cleanup() {
    rm -rf "$WORK"
    rmdir "$SCRIPT_DIR/.work" 2>/dev/null || :
}
if [ -L "$SCRIPT_DIR/.work" ]; then
    echo "ERROR: refusing symlinked fixture work root: $SCRIPT_DIR/.work" >&2
    exit 2
fi
mkdir -p "$WORK"
WORK=$(CDPATH= cd -- "$WORK" && pwd)
case "$WORK/" in
    "$PROJECT_ROOT/"*) ;;
    *)
        echo "ERROR: fixture output must stay under $PROJECT_ROOT: $WORK" >&2
        exit 2
        ;;
esac
trap cleanup EXIT HUP INT TERM
mkdir -p "$WORK/tmp"
TMPDIR=$WORK/tmp
export TMPDIR

COMPILE_COMMON="--target=aarch64-linux-ohos --sysroot=$SYSROOT -I$SYSROOT/include/aarch64-linux-ohos -include $BC_INCLUDE/libcxx_compat.h -I$BC_INCLUDE -nostdlib++ -std=c++17 -Wall -Wextra -Werror"
BASE_COMMON="$COMPILE_COMMON -B$MUSL_LIB -L$MUSL_LIB"
FIXTURE_TLS_COMMON="$BASE_COMMON -fno-emulated-tls"

# shellcheck disable=SC2086
"$CXX" $FIXTURE_TLS_COMMON -fPIC -shared \
    "$SCRIPT_DIR/tls_after_prefix.cpp" \
    -Wl,-soname,libtls_after_prefix.so \
    -o "$WORK/libtls_after_prefix.so"

# Negative control: this toolchain emits no main PT_TLS when the reservation
# object is omitted, reproducing the layout precondition that lets the first
# host DSO TLS module start at offset zero.
# shellcheck disable=SC2086
"$CXX" $BASE_COMMON \
    "$SCRIPT_DIR/reservation_main.cpp" \
    -L"$WORK" -Wl,--no-as-needed -ltls_after_prefix \
    -Wl,-rpath-link,"$WORK" \
    -o "$WORK/no_reservation_fixture"

# Compile the reservation with the product driver's default emutls policy.
# The explicit ELF TLS section in the source must not depend on a global
# -fno-emulated-tls build switch.
# shellcheck disable=SC2086
"$CXX" $COMPILE_COMMON -fPIC -O2 -D__OHOS__ \
    -c "$PREFIX_DIR/bionic_tls_prefix_reservation.cpp" \
    -o "$WORK/bionic_tls_prefix_reservation.o"

# The reservation object must be linked directly into the executable.  Putting
# it in a DSO would allocate it after earlier host TLS modules and would not own
# Bionic's fixed low slots.
# shellcheck disable=SC2086
"$CXX" $BASE_COMMON \
    "$WORK/bionic_tls_prefix_reservation.o" \
    "$SCRIPT_DIR/reservation_main.cpp" \
    -L"$WORK" -Wl,--no-as-needed -ltls_after_prefix \
    -Wl,-rpath-link,"$WORK" \
    -o "$WORK/reservation_fixture"

# Prove that the SHF_GNU_RETAIN section survives a future dead-section build.
# shellcheck disable=SC2086
"$CXX" $BASE_COMMON -ffunction-sections -fdata-sections \
    "$WORK/bionic_tls_prefix_reservation.o" \
    "$SCRIPT_DIR/reservation_main.cpp" \
    -L"$WORK" -Wl,--no-as-needed -ltls_after_prefix \
    -Wl,-rpath-link,"$WORK" -Wl,--gc-sections \
    -o "$WORK/reservation_fixture_gc"

"$READELF" -lW "$WORK/reservation_fixture" >"$WORK/main.phdr"
"$READELF" -sW "$WORK/reservation_fixture" >"$WORK/main.sym"
"$READELF" -lW "$WORK/reservation_fixture_gc" >"$WORK/main_gc.phdr"
"$READELF" -lW "$WORK/no_reservation_fixture" >"$WORK/main_negative.phdr"
"$READELF" -lW "$WORK/libtls_after_prefix.so" >"$WORK/dso.phdr"
"$READELF" -SW "$WORK/bionic_tls_prefix_reservation.o" >"$WORK/prefix.sections"
"$READELF" -sW "$WORK/bionic_tls_prefix_reservation.o" >"$WORK/prefix.symbols"

sed -n '/TLS/p' "$WORK/main.phdr"
sed -n '/westlake_bionic_tls_slots_2_7_reservation/p' "$WORK/main.sym"
sed -n '/TLS/p' "$WORK/dso.phdr"

grep -Eq 'TLS[[:space:]]+.*0x000000[[:space:]]+0x000030[[:space:]]+R[[:space:]]+0x10' \
    "$WORK/main.phdr"
grep -Eq '[[:space:]]TLS[[:space:]]+.*westlake_bionic_tls_slots_2_7_reservation$' \
    "$WORK/main.sym"
grep -Eq 'TLS[[:space:]]+.*0x000000[[:space:]]+0x000030[[:space:]]+R[[:space:]]+0x10' \
    "$WORK/main_gc.phdr"
grep -Eq 'TLS[[:space:]]+.*0x000008[[:space:]]+0x000008[[:space:]]+R[[:space:]]+0x8' \
    "$WORK/dso.phdr"
grep -Eq '\.tbss\.westlake_bionic_tls_prefix[[:space:]]+NOBITS.*000030.*WATR.*16' \
    "$WORK/prefix.sections"
grep -Eq '[[:space:]]48[[:space:]]+TLS[[:space:]]+GLOBAL[[:space:]]+HIDDEN.*westlake_bionic_tls_slots_2_7_reservation$' \
    "$WORK/prefix.symbols"
if grep -q 'TLS' "$WORK/main_negative.phdr"; then
    echo "ERROR: negative-control executable unexpectedly contains PT_TLS" >&2
    exit 1
fi

echo "PASS main_PT_TLS_memsz=0x30 align=0x10 owns_TP=[0x10,0x40)"
echo "PASS product_default_compile=STT_TLS,size48,align16,SHF_GNU_RETAIN"
echo "PASS main_PT_TLS_survives=--gc-sections"
echo "PASS following_DSO_PT_TLS_memsz=0x8 align=0x8"
echo "PASS negative_control_main_PT_TLS=absent"
echo "NOT_PROVEN slot_semantics=2,3,4,6,7 slots=-1,0,1"
