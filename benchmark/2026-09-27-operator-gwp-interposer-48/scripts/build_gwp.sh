#!/usr/bin/env bash
# Build the GWP-ASan-lite page-guard malloc interposer for the board (aarch64 OH musl).
# Header-minimal (self-contained decls) -> compiles against any OH sysroot; -nostdlib, UNDs
# resolve at runtime from the process libc (LD_PRELOAD).
set -euo pipefail
SRC="${1:-$(dirname "$0")/../src/westlake_gwp.c}"
OUT="${2:-$(dirname "$0")/../out/libwestlake_gwp.aarch64-ohos.so}"
NB="${OHOS_NATIVE:-/Users/zhaoyue/command-line-tools/sdk/default/hms/native}"   # BiSheng clang + sysroot
"$NB/BiSheng/bin/clang" --target=aarch64-linux-ohos --sysroot="$NB/sysroot" \
  -O1 -fPIC -shared -Wall -Wextra -nostdlib \
  -Wl,-soname,libwestlake_gwp.so -Wl,--build-id=sha1 -x c "$SRC" -o "$OUT"
echo "built $OUT"; shasum -a 256 "$OUT" 2>/dev/null || sha256sum "$OUT"
