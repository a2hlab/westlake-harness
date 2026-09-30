#!/bin/bash
# compile_sigchain_muslcompat.sh — 独立、自包含地把
# aosp_patches/art/sigchainlib/sigchain_muslcompat.cc 编成 aarch64 libsigchain.so。
#
# 背景：memory route3-rssurface-stack-confirmed.md §"执行上一节…sigchain修复实测
# 部署验证"第三节第2/3点指出，本仓库现存 out/aosp_lib/libsigchain.so 其实是
# ARM32/DAYU200 专属流水线(cross_compile_arm32.sh)产物、根本不是从
# sigchain_muslcompat.cc 编的，架构和内容都对不上；而真正匹配的 aarch64 产物当时
# 位于 02.unity.cardwords/adapter 之外（/opt/21.Game/artifacts/shim_sigfwd/diag/），
# 未纳入本仓库自己的可复现构建体系——本脚本补上这个缺口。
#
# 用法：
#   bash build/inner/compile_sigchain_muslcompat.sh              # 生产版（无探针）
#   bash build/inner/compile_sigchain_muslcompat.sh --probe       # 诊断探针版
#       （-DSIGCHAIN_PROBE_LOG=1，见源文件内 #ifdef SIGCHAIN_PROBE_LOG 块）
#
# 与 build/inner/ 其它脚本不同：本脚本不依赖 GZ05 ECS 容器/OH 完整源树——
# sigchain_muslcompat.cc 只用标准 <signal.h>/<fcntl.h> 等，用任意
# aarch64-linux-ohos clang + OH sysroot 即可独立编译，属于铁律1 允许的
# "musl-compat 边界"重编类别，不算碰 libart 源。可以直接运行，不走
# BUILD_INNER_INVOKED guard 分发链。
#
# 工具链默认指向本机已安装的 DevEco Studio 内置 OHOS clang15（自包含 sysroot），
# 可用 OHOS_CLANGXX / OHOS_SYSROOT 环境变量覆盖指向别的等价工具链。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC="$ADAPTER_ROOT/aosp_patches/art/sigchainlib/sigchain_muslcompat.cc"
OUT_DIR="$ADAPTER_ROOT/out/aosp_lib_arm64"

DEFAULT_CLANGXX="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/clang++"
DEFAULT_SYSROOT="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/sysroot"

OHOS_CLANGXX="${OHOS_CLANGXX:-$DEFAULT_CLANGXX}"
OHOS_SYSROOT="${OHOS_SYSROOT:-$DEFAULT_SYSROOT}"

if [ ! -x "$OHOS_CLANGXX" ]; then
    echo "[FATAL] aarch64-linux-ohos clang++ not found at: $OHOS_CLANGXX" >&2
    echo "        override with OHOS_CLANGXX=/path/to/clang++" >&2
    exit 1
fi
if [ ! -d "$OHOS_SYSROOT" ]; then
    echo "[FATAL] OH sysroot not found at: $OHOS_SYSROOT" >&2
    echo "        override with OHOS_SYSROOT=/path/to/sysroot" >&2
    exit 1
fi
if [ ! -f "$SRC" ]; then
    echo "[FATAL] source not found: $SRC" >&2
    exit 1
fi

PROBE=0
OUT_NAME="libsigchain.so"
if [ "${1:-}" == "--probe" ]; then
    PROBE=1
    OUT_NAME="libsigchain_probe.so"
fi

mkdir -p "$OUT_DIR"
OUT_PATH="$OUT_DIR/$OUT_NAME"

EXTRA_DEFS=()
if [ "$PROBE" == "1" ]; then
    EXTRA_DEFS+=(-DSIGCHAIN_PROBE_LOG=1)
fi

echo "[compile_sigchain_muslcompat] clang++  = $OHOS_CLANGXX"
echo "[compile_sigchain_muslcompat] sysroot  = $OHOS_SYSROOT"
echo "[compile_sigchain_muslcompat] source   = $SRC"
echo "[compile_sigchain_muslcompat] probe    = $PROBE (defs: ${EXTRA_DEFS[*]:-<none>})"
echo "[compile_sigchain_muslcompat] out      = $OUT_PATH"

"$OHOS_CLANGXX" \
    --target=aarch64-linux-ohos \
    --sysroot="$OHOS_SYSROOT" \
    -fPIC -shared -O2 -Wall -Wextra \
    ${EXTRA_DEFS[@]+"${EXTRA_DEFS[@]}"} \
    -o "$OUT_PATH" \
    "$SRC"

echo "[compile_sigchain_muslcompat] done."
file "$OUT_PATH" || true
echo "[compile_sigchain_muslcompat] exported symbols:"
nm -D "$OUT_PATH" 2>/dev/null | grep -E ' T | U ' || true
md5sum "$OUT_PATH" 2>/dev/null || md5 "$OUT_PATH"
