#!/usr/bin/env bash
# Build the #39 PoC binaries. VM/Mac side only; no device access here.
#   tp_probe_static  - static control, no PT_INTERP, proves NDK/toolchain sanity
#   tp_probe_dyn     - dynamic, PT_INTERP -> /data/local/tmp/bionic39/linker64 (the AOSP14 Bionic linker)
# The dynamic one is the real test: it must be brought up by the Bionic linker64 on the board.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/out"; SRC="$HERE/src"; mkdir -p "$OUT"
NDK="${NDK:-$HOME/Library/Android/sdk/ndk/23.1.7779620}"
T="$NDK/toolchains/llvm/prebuilt/darwin-x86_64"
CC="$T/bin/aarch64-linux-android21-clang"
RE="$T/bin/llvm-readelf"
INTERP="/data/local/tmp/bionic39/linker64"   # where the Bionic linker will live on the board

# 1) static control (its own libc, no interpreter)
"$CC" -static -O2 -Wall -o "$OUT/tp_probe_static" "$SRC/tp_probe.c"
"$CC" -static -O2 -Wall -o "$OUT/hello_static"    "$SRC/hello.c"

# 2) dynamic, interpreter pointed at the on-board Bionic linker
"$CC" -O2 -Wall -fPIE -pie -Wl,--dynamic-linker="$INTERP" -o "$OUT/tp_probe_dyn" "$SRC/tp_probe.c"
"$CC" -O2 -Wall -fPIE -pie -Wl,--dynamic-linker="$INTERP" -o "$OUT/hello_dyn"    "$SRC/hello.c"

echo "== PT_INTERP / NEEDED =="
for b in tp_probe_dyn hello_dyn; do
  echo "-- $b"
  "$RE" -l "$OUT/$b" | grep -A1 INTERP || true
  "$RE" -d "$OUT/$b" | grep NEEDED || true
done
echo "== static (expect no INTERP) =="
"$RE" -l "$OUT/tp_probe_static" | grep INTERP && echo "UNEXPECTED interp in static" || echo "ok: no interp"
echo "== sizes =="; ls -l "$OUT"
