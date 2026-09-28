#!/bin/bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: $0 RUN_ID SERIAL APK" >&2
  exit 2
fi

RUN_ID="$1"
SERIAL="$2"
APK="$3"
EXPECTED_SERIAL="654b3a6b00000000000000000824012c"
EXPECTED_APK_SHA256="2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd"
EXPECTED_APPSPAWN_SHA256="2e78d89f81b48192c815eea3d982c6e1d9df44897c8356e735cdad47944a3737"
PACKAGE="com.example.helloworld"
MAIN_ACTIVITY="com.example.helloworld.MainActivity"
BRIDGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HDC_BIN="${HDC_BIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
OUT="$BRIDGE_ROOT/evidence/concepts/fn08-fn12-d600-early/$RUN_ID/$SERIAL"
REMOTE_APK="/data/local/tmp/${RUN_ID}-HelloWorld.apk"

case "$RUN_ID" in
  *[!A-Za-z0-9._-]* | "")
    echo "RUN_ID contains unsafe characters: $RUN_ID" >&2
    exit 2
    ;;
esac

[ "$SERIAL" = "$EXPECTED_SERIAL" ]
[ -f "$APK" ]
[ -x "$HDC_BIN" ]
mkdir -p "$OUT"

host_apk_sha256="$(sha256sum "$APK" | awk '{print $1}')"
[ "$host_apk_sha256" = "$EXPECTED_APK_SHA256" ]

dev()
{
  "$HDC_BIN" -t "$SERIAL" shell "$1"
}

boot_before="$(dev "cat /proc/sys/kernel/random/boot_id" | tr -d '\r')"
parent_before="$(dev "pidof appspawn-x || true" | tr -d '\r ')"
appspawn_sha256="$(dev "sha256sum /system/bin/appspawn-x" | awk '{print $1}' | tr -d '\r')"
selinux="$(dev "getenforce" | tr -d '\r')"

{
  echo "boot_id: $boot_before"
  echo "selinux: $selinux"
  echo "appspawn_pid: '$parent_before'"
  echo "host_apk: $APK"
  echo "host_apk_sha256: $host_apk_sha256"
  echo "device_appspawn_sha256: $appspawn_sha256"
  dev "bm dump -n $PACKAGE"
} > "$OUT/install-precheck.txt" 2>&1

[ "$selinux" = "Enforcing" ]
[ -n "$parent_before" ]
[ "$appspawn_sha256" = "$EXPECTED_APPSPAWN_SHA256" ]
if grep -Fq "$PACKAGE:" "$OUT/install-precheck.txt"; then
  {
    echo "experiment: E01-install"
    echo "verdict: BLOCK"
    echo "reason: package already existed before exact new-install stimulus"
    echo "claim_boundary: EXACT_APK_INSTALL_AND_REGISTRY_FACT_ONLY"
  } > "$OUT/INSTALL-VERDICT.yaml"
  exit 1
fi

"$HDC_BIN" -t "$SERIAL" file send "$APK" "$REMOTE_APK" \
  > "$OUT/install-file-send.txt" 2>&1
dev "sha256sum '$REMOTE_APK'; ls -lZ '$REMOTE_APK'" \
  > "$OUT/install-staged-identity.txt" 2>&1
grep -Fq "$EXPECTED_APK_SHA256  $REMOTE_APK" "$OUT/install-staged-identity.txt"

set +e
dev "bm install -p '$REMOTE_APK'" > "$OUT/bm-install.txt" 2>&1
install_rc=$?
set -e

dev "bm dump -n $PACKAGE" > "$OUT/bm-dump-after-install.txt" 2>&1 || true
dev "ls -lZ /data/app/el1/bundle/public/$PACKAGE/android/base.apk; sha256sum /data/app/el1/bundle/public/$PACKAGE/android/base.apk" \
  > "$OUT/installed-apk-identity.txt" 2>&1 || true

boot_after="$(dev "cat /proc/sys/kernel/random/boot_id" | tr -d '\r')"
parent_after="$(dev "pidof appspawn-x || true" | tr -d '\r ')"
dev "hilog -x 2>/dev/null | grep -Ei 'apk|install|bundle|$PACKAGE|appspawn-x' | tail -1600" \
  > "$OUT/install-hilog-tail.txt" 2>&1 || true
dev "rm -f '$REMOTE_APK'" > "$OUT/install-stage-cleanup.txt" 2>&1 || true

verdict="PASS"
reason="exact APK installed and registry/on-disk identity matched"
if [ "$install_rc" -ne 0 ]; then
  verdict="FAIL"
  reason="bm install returned non-zero"
elif ! grep -Fq "$MAIN_ACTIVITY" "$OUT/bm-dump-after-install.txt"; then
  verdict="FAIL"
  reason="bm dump did not expose the expected MainActivity"
elif ! grep -Fq "$EXPECTED_APK_SHA256  /data/app/el1/bundle/public/$PACKAGE/android/base.apk" \
    "$OUT/installed-apk-identity.txt"; then
  verdict="FAIL"
  reason="installed base.apk did not match the exact host APK"
elif [ "$boot_before" != "$boot_after" ]; then
  verdict="BLOCK"
  reason="boot ID changed during install"
elif [ "$parent_before" != "$parent_after" ]; then
  verdict="BLOCK"
  reason="appspawn-x parent identity changed during install"
fi

{
  echo "experiment: E01-install"
  echo "verdict: $verdict"
  echo "risk: R1_REVERSIBLE_PACKAGE_INSTALL"
  echo "device_serial: $SERIAL"
  echo "boot_id_before: $boot_before"
  echo "boot_id_after: $boot_after"
  echo "appspawn_pid_before: '$parent_before'"
  echo "appspawn_pid_after: '$parent_after'"
  echo "apk_sha256: $host_apk_sha256"
  echo "install_rc: $install_rc"
  echo "reason: $reason"
  echo "claim_boundary: EXACT_APK_INSTALL_AND_REGISTRY_FACT_ONLY"
} > "$OUT/INSTALL-VERDICT.yaml"

echo "$verdict: $reason"
test "$verdict" = "PASS"
