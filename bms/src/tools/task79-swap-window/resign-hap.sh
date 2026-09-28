#!/usr/bin/env bash
# resign-hap.sh — 把任意 OH .hap 重签到**指定板子**的 UDID 上。
#
# 由 harmony/westlake-piercing/ports/dayu600/oh-xcomponent-hap/resign-oh-hap.sh 派生，
# 唯一实质改动：原脚本把 5ce2dcee 的 UDID 写死在源码里，这里改成参数。
#
# 为什么需要它：OH 的 debug 签名 profile **绑死设备 UDID**。给 A 板签的 hap 装到 B 板上
# 会报 `error: Failed to install the HAP because the device is unauthorized`（code 9568423）。
# 换板子 = 必须重签，不是"再试一次"能解决的。
#
# provisioning profile 同时绑 bundleName，所以流程是：读入包的 bundleName ->
# 用它 + 目标 UDID 现做一份 debug profile -> 用 SDK 自带的 OpenHarmony 开发 CA 签
# （板子本来就信这个 CA）-> sign-app -> verify-app。
#
# 用法:
#   UDID=<64位大写十六进制> bash resign-hap.sh <in.hap> [out.hap]
#   TARGET=<hdc序列号> bash resign-hap.sh <in.hap>      # 自动从板子读 UDID
set -euo pipefail

JH="${JH:-/Users/yao/jdk17/jdk-17.0.19+10/Contents/Home}"
LIB="${OH_TOOLLIB:-$HOME/command-line-tools/sdk/default/openharmony/toolchains/lib}"
ST="$LIB/hap-sign-tool.jar"
P12="$LIB/OpenHarmony.p12"
PCERT="$LIB/OpenHarmonyProfileRelease.pem"
# 证书链和 profile 模板沿用 westlake-piercing 那份（公开的 SDK 开发证书，非机密）
SRC="${SIGN_SRC:-/Users/yao/Desktop/code/harmony/westlake-piercing/ports/dayu600/oh-xcomponent-hap/sign}"
APPCHAIN="$SRC/app-cert-chain.pem"
TEMPLATE="$SRC/profile-template.json"
PWD_KS=123456                                     # SDK 自带 keystore 的公开默认口令

IN="${1:?usage: [UDID=... | TARGET=...] resign-hap.sh <in.hap> [out.hap]}"

# UDID：优先环境变量；否则从 TARGET 指定的板子上读
if [ -z "${UDID:-}" ]; then
  [ -n "${TARGET:-}" ] || { echo "需要 UDID=... 或 TARGET=<hdc序列号>"; exit 1; }
  UDID=$(hdc -t "$TARGET" shell bm get -u 2>/dev/null | tr -d '\r' | grep -oE '[0-9A-F]{64}' | head -1)
  [ -n "$UDID" ] || { echo "从板 $TARGET 读 UDID 失败"; exit 1; }
  echo "[0] 板 $TARGET 的 UDID = ${UDID:0:12}…"
fi

NAME="$(basename "$IN" .hap)"
OUT="${2:-$(dirname "$IN")/${NAME}-${UDID:0:8}.hap}"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
JAVA="$JH/bin/java"

for f in "$IN" "$ST" "$PCERT" "$APPCHAIN" "$TEMPLATE" "$P12"; do
  [ -f "$f" ] || { echo "缺文件: $f"; exit 1; }
done

# 1) bundleName —— 打好的 hap 把它放在 pack.info 的 .summary.app.bundleName，不在 module.json5
PI="$(unzip -p "$IN" pack.info 2>/dev/null || true)"
BN="$(printf '%s' "$PI" | grep -oE '"bundleName"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*"([^"]+)"$/\1/' || true)"
[ -n "${BN:-}" ] || BN="$(unzip -p "$IN" module.json 2>/dev/null | grep -oE '"bundleName"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*"([^"]+)"$/\1/' || true)"
BN="${BN:-${BN_OVERRIDE:-}}"
[ -n "$BN" ] || { echo "读不出 bundleName，设 BN_OVERRIDE=<bundle> 重试"; exit 1; }
echo "[1] bundleName = $BN"

# 2) 现做 profile：换 bundleName，换 UDID
sed -e "s/com\.westlake\.glxc/$BN/g" \
    -e "s/E28A04046CD8DC5A2BB7040484CFED32B9478ED4C712D45AA2653F6D6123477B/$UDID/g" \
    "$TEMPLATE" > "$WORK/profile.json"
grep -q "\"$BN\"" "$WORK/profile.json" || { echo "模板改 bundleName 失败"; exit 1; }
grep -q "$UDID" "$WORK/profile.json" || { echo "模板改 UDID 失败——模板里的占位 UDID 变了？"; exit 1; }
echo "[2] profile 已生成 ($BN + ${UDID:0:12}…)"

# 3) sign-profile -> p7b
"$JAVA" -jar "$ST" sign-profile \
  -keyAlias "openharmony application profile release" -signAlg SHA256withECDSA -mode localSign \
  -profileCertFile "$PCERT" -inFile "$WORK/profile.json" \
  -keystoreFile "$P12" -outFile "$WORK/profile.p7b" -keyPwd "$PWD_KS" -keystorePwd "$PWD_KS" >/dev/null
echo "[3] sign-profile OK"

# 4) sign-app
cp "$APPCHAIN" "$WORK/appchain.cer"
"$JAVA" -jar "$ST" sign-app \
  -keyAlias "openharmony application release" -signAlg SHA256withECDSA -mode localSign \
  -appCertFile "$WORK/appchain.cer" -profileFile "$WORK/profile.p7b" \
  -inFile "$IN" -keystoreFile "$P12" -outFile "$OUT" -keyPwd "$PWD_KS" -keystorePwd "$PWD_KS" >/dev/null
echo "[4] sign-app OK -> $OUT"

# 5) verify
if "$JAVA" -jar "$ST" verify-app -inFile "$OUT" -outCertChain "$WORK/vc.cer" -outProfile "$WORK/vp.p7b" 2>&1 | grep -q 'verify codesign success'; then
  echo "[5] verify-app: codesign success"
else
  echo "[5] verify-app 失败"; exit 1
fi

echo
echo "装："
echo "  hdc -t ${TARGET:-<序列号>} shell bm install -p <传上去的路径>"
echo "  hdc -t ${TARGET:-<序列号>} shell aa start -b $BN -m entry -a EntryAbility"
