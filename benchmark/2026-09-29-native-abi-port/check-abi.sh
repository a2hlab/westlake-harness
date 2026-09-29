#!/usr/bin/env bash
set -euo pipefail
R=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy
E=$R/benchmark/2026-09-29-native-abi-port
W=$R/bms/src/.work/b87-native
SDK=/home/dspfac/a2hlab/source-closure/verify/toolchains/ohos-sdk/native
export LD_LIBRARY_PATH=$SDK/llvm/lib
FLAGS=(--target=aarch64-linux-ohos --sysroot="$SDK/sysroot" -fPIC -shared -Wl,-z,defs -Wl,--allow-shlib-undefined)
"$SDK/llvm/bin/clang-15" "${FLAGS[@]}" "$E/abi-consumer.c" "$W/log-bionic/liblog.so" -o "$W/abi-positive.so"
if "$SDK/llvm/bin/clang-15" "${FLAGS[@]}" "$E/abi-consumer.c" "$W/link/original-liblog.so" -o "$W/abi-negative.so" > "$E/abi-negative.txt" 2>&1; then
 echo 'FAIL original unexpectedly satisfies versioned ABI';exit 1
fi
grep -E '__errno|__sF' "$E/abi-negative.txt" >/dev/null
printf 'PASS: candidate links __errno@LIBC, __sF@LIBC and Android log; original fails.\n'
