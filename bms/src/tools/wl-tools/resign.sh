#!/usr/bin/env bash
# resign.sh — sign/re-sign an OH .hap for a DAYU600 board. Auto-mints a debug profile for
# whatever bundleName the hap carries + the target board's UDID. Password 123456 = PUBLIC
# SDK default. Cert chain + profile template live in ./sign (rebuilt 2026-07-17).
#
# Board UDIDs (bm get --udid):
#   5583f5be = 3F740326F7978CC8CB62F84376856D13ED1C4B733C763871D300FED31B6560E9  (default)
#   5ce2dcee = E28A04046CD8DC5A2BB7040484CFED32B9478ED4C712D45AA2653F6D6123477B
#   dd011a41 = DC5DF4BE7D032DFEADE1DF35599C6D1303E5A7EE61D230D7369D344F3F82C360
# Override: WL_UDID=<udid> WL_BOARD_TAG=<name> resign.sh <in.hap> [out.hap]
set -euo pipefail
JH="${JH:-/Users/yao/jdk17/jdk-17.0.19+10/Contents/Home}"
LIB="$HOME/command-line-tools/sdk/default/openharmony/toolchains/lib"
ST="$LIB/hap-sign-tool.jar"; P12="$LIB/OpenHarmony.p12"; PCERT="$LIB/OpenHarmonyProfileRelease.pem"
HERE="$(cd "$(dirname "$0")" && pwd)"
APPCHAIN="$HERE/sign/app-cert-chain.pem"
# WL_PROFILE_TEMPLATE lets a caller supply its own profile (e.g. a higher apl +
# allowed-acls for restricted permissions) without mutating the shared default,
# which every other HAP in the repo signs against. Default is unchanged.
TEMPLATE="${WL_PROFILE_TEMPLATE:-$HERE/sign/profile-template.json}"
UDID="${WL_UDID:-3F740326F7978CC8CB62F84376856D13ED1C4B733C763871D300FED31B6560E9}"
TAG="${WL_BOARD_TAG:-5583}"; PWD_KS=123456
IN="${1:?usage: resign.sh <in.hap> [out.hap]}"; NAME="$(basename "$IN" .hap)"
OUT="${2:-$(dirname "$IN")/${NAME}-${TAG}.hap}"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT; JAVA="$JH/bin/java"
PI="$(unzip -p "$IN" pack.info 2>/dev/null || true)"
BN="$(printf '%s' "$PI" | grep -oE '"bundleName"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*"([^"]+)"$/\1/' || true)"
[ -n "${BN:-}" ] || { echo "no bundleName in $IN"; exit 1; }
echo "[1] bundleName=$BN udid=$UDID"
sed -e "s/com\.westlake\.glxc/$BN/g" -e "s/__WL_UDID__/$UDID/g" "$TEMPLATE" > "$WORK/profile.json"
"$JAVA" -jar "$ST" sign-profile -keyAlias "openharmony application profile release" -signAlg SHA256withECDSA -mode localSign \
  -profileCertFile "$PCERT" -inFile "$WORK/profile.json" -keystoreFile "$P12" -outFile "$WORK/profile.p7b" -keyPwd "$PWD_KS" -keystorePwd "$PWD_KS" >/dev/null
echo "[2] profile signed"
cp "$APPCHAIN" "$WORK/appchain.cer"
"$JAVA" -jar "$ST" sign-app -keyAlias "openharmony application release" -signAlg SHA256withECDSA -mode localSign \
  -appCertFile "$WORK/appchain.cer" -profileFile "$WORK/profile.p7b" -inFile "$IN" -keystoreFile "$P12" -outFile "$OUT" -keyPwd "$PWD_KS" -keystorePwd "$PWD_KS" >/dev/null
echo "[3] app signed -> $OUT"
"$JAVA" -jar "$ST" verify-app -inFile "$OUT" -outCertChain "$WORK/vc.cer" -outProfile "$WORK/vp.p7b" 2>&1 | grep -q 'verify codesign success' \
  && echo "[4] verify: codesign success" || { echo "[4] verify FAILED"; exit 1; }
