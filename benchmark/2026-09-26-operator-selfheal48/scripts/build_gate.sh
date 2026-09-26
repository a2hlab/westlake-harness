#!/usr/bin/env bash
set -euo pipefail
TASK=$(cd "$(dirname "$0")/.." && pwd)
SDK=$HOME/a2hlab/ws/toolchains/ohos-sdk/native
OUT=$HOME/a2hlab/board/61b0657200000000000000000324012c/selfheal48
"$SDK/llvm/bin/clang" --target=aarch64-linux-ohos --sysroot="$SDK/sysroot" -O2 -I"$HOME/a2hlab/ws/android-source/libpng" "$TASK/scripts/screen_gate.c" -ldl -o "$OUT/screen-gate"
sha256sum "$OUT/screen-gate"
