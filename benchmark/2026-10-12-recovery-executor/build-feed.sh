#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
D=benchmark/2026-10-12-recovery-executor
SDK=${OH_NATIVE_SDK:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native}
mkdir -p "$D/evidence/classifier-feed-build"
shasum -a 256 "$SDK/llvm/bin/clang-15" "$SDK/llvm/bin/ld.lld" "$SDK/sysroot/usr/lib/aarch64-linux-ohos/libc.so" "$D/src/screen_gate_feed.c" "$D/src/stb_image.h" > "$D/evidence/classifier-feed-build/inputs.sha256"
set +e
"$SDK/llvm/bin/clang-15" --target=aarch64-linux-ohos --sysroot="$SDK/sysroot" -O2 -fno-math-errno "$D/src/screen_gate_feed.c" -o "$D/evidence/classifier-feed-build/screen-gate" -lm > "$D/evidence/classifier-feed-build/stdout.txt" 2> "$D/evidence/classifier-feed-build/stderr.txt"
rc=$?
set -e
printf '%s\n' "$rc" > "$D/evidence/classifier-feed-build/exit.txt"
[ "$rc" = 0 ]
shasum -a 256 "$D/evidence/classifier-feed-build/screen-gate"
if [ -f "$D/payload/screen-gate-feed" ]; then cmp "$D/payload/screen-gate-feed" "$D/evidence/classifier-feed-build/screen-gate"; else cp "$D/evidence/classifier-feed-build/screen-gate" "$D/payload/screen-gate-feed"; fi
