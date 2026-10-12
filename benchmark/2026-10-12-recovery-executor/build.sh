#!/bin/bash
# Local-only frozen classifier rebuild. No Docker/VM/network/device operation.
set -euo pipefail
cd "$(dirname "$0")/../.."
D=benchmark/2026-10-12-recovery-executor
SDK=${OH_NATIVE_SDK:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native}
CC="$SDK/llvm/bin/clang-15"
mkdir -p "$D/evidence/classifier-build"
shasum -a 256 "$CC" "$SDK/llvm/bin/ld.lld" "$SDK/sysroot/usr/lib/aarch64-linux-ohos/libc.so" "$D/src/screen_gate_jpeg.c" "$D/src/stb_image.h" > "$D/evidence/classifier-build/inputs.sha256"
set +e
"$CC" --target=aarch64-linux-ohos --sysroot="$SDK/sysroot" -O2 -fno-math-errno "$D/src/screen_gate_jpeg.c" -o "$D/evidence/classifier-build/screen-gate" -lm > "$D/evidence/classifier-build/stdout.txt" 2> "$D/evidence/classifier-build/stderr.txt"
rc=$?
set -e
printf '%s\n' "$rc" > "$D/evidence/classifier-build/exit.txt"
[ "$rc" = 0 ]
expected=afd0721374ef781552896e966f011966f9ba950b0d2f3fd7eba0a3562424a991
actual=$(shasum -a 256 "$D/evidence/classifier-build/screen-gate" | cut -d' ' -f1)
[ "$actual" = "$expected" ] || { printf 'REBUILD_DRIFT %s\n' "$actual" >&2; exit 2; }
cmp "$D/payload/screen-gate" "$D/evidence/classifier-build/screen-gate"
printf 'byte-identical %s\n' "$actual"
