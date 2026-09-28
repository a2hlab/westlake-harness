#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C
export SOURCE_DATE_EPOCH=0
export TZ=UTC
export ZERO_AR_DATE=1
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
BUILD_SCRIPT=$SCRIPT_DIR/build_connect_oracle.sh
SOURCE=$SCRIPT_DIR/appspawnx_connect_oracle.c
OUTPUT=${OUTPUT:-$SCRIPT_DIR/out/appspawnx_connect_oracle}
RECEIPT=${RECEIPT:-$SCRIPT_DIR/out/BUILD_GATE.txt}

: "${OH_CC:?OH_CC is required}"
: "${OH_SYSROOT:?OH_SYSROOT is required}"
: "${OH_READELF:?OH_READELF is required}"
: "${OH_SDK_METADATA:?OH_SDK_METADATA is required}"

for executable in "$OH_CC" "$OH_READELF"; do
    [[ -x "$executable" ]] || { echo "required executable is missing: $executable" >&2; exit 64; }
done
[[ -d "$OH_SYSROOT" ]] || { echo "sysroot is missing: $OH_SYSROOT" >&2; exit 65; }
[[ -f "$OH_SDK_METADATA" && ! -L "$OH_SDK_METADATA" ]] || {
    echo "SDK metadata is missing or a symlink: $OH_SDK_METADATA" >&2
    exit 66
}

sha256_file()
{
    shasum -a 256 "$1" | awk '{print $1}'
}

mkdir -p "$SCRIPT_DIR/out" "$(dirname "$OUTPUT")" "$(dirname "$RECEIPT")"
GATE_DIR=$(mktemp -d "$SCRIPT_DIR/out/.verify.XXXXXX")
trap 'rm -rf "$GATE_DIR"' EXIT INT TERM

OUTPUT=$GATE_DIR/oracle-a OH_CC="$OH_CC" OH_SYSROOT="$OH_SYSROOT" bash "$BUILD_SCRIPT"
OUTPUT=$GATE_DIR/oracle-b OH_CC="$OH_CC" OH_SYSROOT="$OH_SYSROOT" bash "$BUILD_SCRIPT"
cmp -s "$GATE_DIR/oracle-a" "$GATE_DIR/oracle-b" || {
    echo "two clean builds differ" >&2
    exit 67
}

"$OH_READELF" -h "$GATE_DIR/oracle-a" > "$GATE_DIR/elf-header.txt"
"$OH_READELF" -l "$GATE_DIR/oracle-a" > "$GATE_DIR/program-headers.txt"
"$OH_READELF" -d "$GATE_DIR/oracle-a" > "$GATE_DIR/dynamic.txt"
"$OH_READELF" -n "$GATE_DIR/oracle-a" > "$GATE_DIR/notes.txt"

grep -Eq 'Class:[[:space:]]+ELF64$' "$GATE_DIR/elf-header.txt"
grep -Eq 'Type:[[:space:]]+DYN ' "$GATE_DIR/elf-header.txt"
grep -Eq 'Machine:[[:space:]]+AArch64$' "$GATE_DIR/elf-header.txt"
grep -Fq '[Requesting program interpreter: /lib/ld-musl-aarch64.so.1]' "$GATE_DIR/program-headers.txt"
grep -Eq 'GNU_STACK[[:space:]].* RW[[:space:]]' "$GATE_DIR/program-headers.txt"
grep -Eq 'GNU_RELRO[[:space:]]' "$GATE_DIR/program-headers.txt"
grep -Fq 'Shared library: [libc.so]' "$GATE_DIR/dynamic.txt"
grep -Eq '\(FLAGS\)[[:space:]]+BIND_NOW' "$GATE_DIR/dynamic.txt"
grep -Eq '\(FLAGS_1\)[[:space:]]+NOW PIE' "$GATE_DIR/dynamic.txt"
grep -Eq 'Build ID: [0-9a-f]{40}$' "$GATE_DIR/notes.txt"
[[ $(grep -c 'Shared library:' "$GATE_DIR/dynamic.txt") -eq 1 ]]
if grep -Eq '\((RPATH|RUNPATH)\)' "$GATE_DIR/dynamic.txt"; then
    echo "RPATH/RUNPATH is forbidden" >&2
    exit 68
fi
if rg -n '\b(send|sendto|sendmsg|write|writev)[[:space:]]*\(' "$SOURCE"; then
    echo "connect-only oracle contains a payload-writing call" >&2
    exit 69
fi

cp "$GATE_DIR/oracle-a" "$OUTPUT"
chmod 0755 "$OUTPUT"

ARTIFACT_SHA=$(sha256_file "$OUTPUT")
BUILD_ID=$(sed -n 's/.*Build ID: \([0-9a-f][0-9a-f]*\)$/\1/p' "$GATE_DIR/notes.txt")
SDK_VERSION=$(sed -n 's/.*"version": "\([^"]*\)".*/\1/p' "$OH_SDK_METADATA")

{
    printf 'status=build_pass\n'
    printf 'device_verified=false\n'
    printf 'artifact=%s\n' "$OUTPUT"
    printf 'artifact_sha256=%s\n' "$ARTIFACT_SHA"
    printf 'build_id=%s\n' "$BUILD_ID"
    printf 'source_sha256=%s\n' "$(sha256_file "$SOURCE")"
    printf 'build_script_sha256=%s\n' "$(sha256_file "$BUILD_SCRIPT")"
    printf 'verifier_sha256=%s\n' "$(sha256_file "$0")"
    printf 'compiler=%s\n' "$OH_CC"
    printf 'compiler_sha256=%s\n' "$(sha256_file "$OH_CC")"
    printf 'readelf=%s\n' "$OH_READELF"
    printf 'readelf_sha256=%s\n' "$(sha256_file "$OH_READELF")"
    printf 'sysroot=%s\n' "$OH_SYSROOT"
    printf 'sdk_version=%s\n' "$SDK_VERSION"
    printf 'sdk_metadata_sha256=%s\n' "$(sha256_file "$OH_SDK_METADATA")"
    printf 'target_runtime=OpenHarmony-6.1.0.31\n'
    printf 'patch_exact_sdk=false\n'
} > "$RECEIPT"

printf 'M02_CONNECT_ORACLE_AARCH64_GATE PASS\n'
cat "$RECEIPT"

