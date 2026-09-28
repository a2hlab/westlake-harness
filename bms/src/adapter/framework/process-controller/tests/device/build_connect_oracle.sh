#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C
export SOURCE_DATE_EPOCH=0
export TZ=UTC
export ZERO_AR_DATE=1
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
SOURCE=$SCRIPT_DIR/appspawnx_connect_oracle.c
OUTPUT=${OUTPUT:-$SCRIPT_DIR/out/appspawnx_connect_oracle}

: "${OH_CC:?OH_CC must name the reviewed OpenHarmony clang executable}"
: "${OH_SYSROOT:?OH_SYSROOT must name the reviewed OpenHarmony native sysroot}"

[[ -x "$OH_CC" ]] || { echo "OH_CC is not executable: $OH_CC" >&2; exit 64; }
[[ -d "$OH_SYSROOT" ]] || { echo "OH_SYSROOT is not a directory: $OH_SYSROOT" >&2; exit 65; }
[[ -f "$SOURCE" && ! -L "$SOURCE" ]] || { echo "source is missing or a symlink" >&2; exit 66; }

mkdir -p "$(dirname "$OUTPUT")"
"$OH_CC" \
    --target=aarch64-linux-ohos \
    --sysroot="$OH_SYSROOT" \
    -std=c11 -O2 \
    -Wall -Wextra -Werror -pedantic \
    -fPIE -fno-ident -fno-record-gcc-switches \
    -ffunction-sections -fdata-sections \
    -fuse-ld=lld -pie \
    -Wl,--build-id=sha1 \
    -Wl,--gc-sections \
    -Wl,--strip-debug \
    -Wl,-z,now -Wl,-z,relro \
    "$SOURCE" -o "$OUTPUT"

printf 'M02_CONNECT_ORACLE_BUILD output=%s\n' "$OUTPUT"

