#!/usr/bin/env bash
# reproduce-boot61b.sh — 复现 61b 板上现役 9 段 boot 镜像(正规线,2026-09-30)
# 事实来源:板上 /system/android/framework/arm64/boot.oat key-value 区(strings 亲读)
# 用法: 在构建机(host dex2oat64 可用后)直接跑;产物在 <out-dir>/
set -euo pipefail

# ==== 板上 boot.oat 烤入的原始事实(2026-09-30 亲读) ====
# dex2oat-cmdline:
#   /opt/build-trees/aosp-arm64-d600/out/host/linux-x86/bin/dex2oat64 \
#     --android-root=/system --instruction-set=arm64 --base=0x70000000 \
#     --compiler-filter=speed --runtime-arg -Xms64m --runtime-arg -Xmx512m \
#     --runtime-arg -Xverify:none \
#     --image=.../products/arm64/boot.art --oat-file=.../products/arm64/boot.oat ...
# 其余 key-values: compiler-filter=speed, native-debuggable=false, requires-image=true
# BCP 顺序(9 jar,亲读):
BCP=(
  core-oj
  core-libart
  core-icu4j
  okhttp
  bouncycastle
  apache-xml
  adapter-mainline-stubs
  framework
  oh-adapter-framework
)

DEX2OAT="${DEX2OAT:?set DEX2OAT=<host>/bin/dex2oat64}"
JARDIR="${JARDIR:?set JARDIR=<dir with the 9 jars>}"
OUT="${OUT:?set OUT=<out-dir>}"
BASE=0x70000000

mkdir -p "$OUT"
ARGS=(--android-root=/system --instruction-set=arm64 --base=$BASE
      --compiler-filter=speed
      --runtime-arg -Xms64m --runtime-arg -Xmx512m --runtime-arg -Xverify:none
      --image="$OUT/boot.art" --oat-file="$OUT/boot.oat")
for j in "${BCP[@]}"; do
  ARGS+=(--dex-file="$JARDIR/$j.jar" --dex-location="/system/android/framework/$j.jar")
done

echo "== reproducing 9-segment boot image =="
"$DEX2OAT" "${ARGS[@]}"

# 逐段校验:产物 9 段与板上现役逐段比 sha256
BOARD_SN="${BOARD_SN:-61b0657200000000000000000324012c}"
HDC="${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
echo "== sha256 compare (local vs board /system/android/framework/arm64/) =="
for f in boot.art boot.oat boot.vdex; do
  L=$(sha256sum "$OUT/$f" | cut -d' ' -f1)
  B=$("$HDC" -t "$BOARD_SN" shell "sha256sum /system/android/framework/arm64/$f" | cut -d' ' -f1)
  [ "$L" = "$B" ] && echo "MATCH $f $L" || echo "DIFF  $f local=$L board=$B"
done
for j in "${BCP[@]}"; do
  for ext in art oat vdex; do
    F="boot-$j.$ext"
    L=$(sha256sum "$OUT/$F" 2>/dev/null | cut -d' ' -f1 || true)
    B=$("$HDC" -t "$BOARD_SN" shell "sha256sum /system/android/framework/arm64/$F" | cut -d' ' -f1)
    [ "$L" = "$B" ] && echo "MATCH $F $L" || echo "DIFF  $F local=${L:-none} board=$B"
  done
done
