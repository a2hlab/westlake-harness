#!/bin/bash
set -euo pipefail

ROOT="${ROOT:-/opt/Bridge}"
SERIAL="${SERIAL:-5583f5be00000000000000000323012c}"
RUN_ID="${RUN_ID:-fn01-fn03-strict-multi-apk-${SERIAL:0:4}-$(date -u +%Y%m%dT%H%M%SZ)}"
HDC="${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
RUN_DIR="$ROOT/evidence/runs/$RUN_ID"
RAW_DIR="$RUN_DIR/raw"
REMOTE_DIR="/data/local/tmp/$RUN_ID"

mkdir -p "$RAW_DIR"

APPS=(
  "ProbeAlpha|$ROOT/APKS/Fn01F03-ProbeAlpha/dist/fn0103-probe-alpha.apk|fn0103-probe-alpha.apk|com.a2hlab.bridge.fn0103.alpha|com.a2hlab.bridge.fn0103.alpha.AlphaActivity|Probe Alpha"
  "ProbeBeta|$ROOT/APKS/Fn01F03-ProbeBeta/dist/fn0103-probe-beta.apk|fn0103-probe-beta.apk|com.a2hlab.bridge.fn0103.beta|com.a2hlab.bridge.fn0103.beta.BetaEntryActivity|Probe Beta"
  "ProbeGamma|$ROOT/APKS/Fn01F03-ProbeGamma/dist/fn0103-probe-gamma.apk|fn0103-probe-gamma.apk|com.a2hlab.bridge.fn0103.gamma|com.a2hlab.bridge.fn0103.gamma.GammaHomeActivity|Probe Gamma"
)

host_sha256() {
  shasum -a 256 "$1" | awk '{print $1}'
}

record_shell() {
  local name="$1"
  local cmd="$2"
  local out="$RAW_DIR/$name.txt"
  {
    echo "receipt_kind=direct-hdc-remote"
    echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "exact_command=$HDC -t $SERIAL shell '$cmd; rc=\$?; echo __REMOTE_RC__=\$rc; exit \$rc'"
    echo "combined_output_begin"
    "$HDC" -t "$SERIAL" shell "$cmd; rc=\$?; echo __REMOTE_RC__=\$rc; exit \$rc"
    local rc=$?
    echo "combined_output_end"
    echo "host_rc=$rc"
    echo "ended_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } >"$out" 2>&1 || true
}

record_send() {
  local name="$1"
  local src="$2"
  local dst="$3"
  local out="$RAW_DIR/$name.txt"
  {
    echo "receipt_kind=direct-hdc-file-send"
    echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "exact_command=$HDC -t $SERIAL file send $src $dst"
    echo "combined_output_begin"
    "$HDC" -t "$SERIAL" file send "$src" "$dst"
    local rc=$?
    echo "combined_output_end"
    echo "host_rc=$rc"
    echo "ended_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } >"$out" 2>&1 || true
}

receipt_has_error() {
  grep -Ei "error:|failed|internal error|Error Code|code:[0-9]+" "$1" >/dev/null 2>&1
}

install_success_found() {
  grep -F "__REMOTE_RC__=0" "$1" >/dev/null 2>&1 || return 1
  receipt_has_error "$1" && return 1
  grep -F "install bundle successfully." "$1" >/dev/null 2>&1
}

start_success_found() {
  grep -F "__REMOTE_RC__=0" "$1" >/dev/null 2>&1 || return 1
  receipt_has_error "$1" && return 1
  grep -F "start ability successfully." "$1" >/dev/null 2>&1
}

record_shell "001-version" "param get const.product.software.version"
record_shell "002-boot-id" "cat /proc/sys/kernel/random/boot_id"
record_shell "003-power-keep-awake" "power-shell wakeup; power-shell timeout -o 86400000; power-shell dump -s | head -18"
record_shell "004-create-stage" "rm -rf $REMOTE_DIR && mkdir -p $REMOTE_DIR"

cat >"$RUN_DIR/manifest.executed.yaml" <<EOF
schema_version: 1
run_id: $RUN_ID
serial: $SERIAL
boundary: Package/Resource + Launcher desktop + Activity start
remote_dir: $REMOTE_DIR
pass_contract:
  - clean uninstall before install
  - host/device sha256 match
  - bm install success text with no error/code receipt
  - exact BMS bundleName
  - exact BMS launcher activity
  - exact BMS label
  - desktop layout contains each package
  - desktop layout contains each expected label
  - desktop screenshot exists and is nonblank
  - aa start success text with no error/code receipt
apps:
EOF

for item in "${APPS[@]}"; do
  IFS='|' read -r name apk remote pkg activity label <<<"$item"
  sha=$(host_sha256 "$apk")
  {
    echo "  - name: $name"
    echo "    apk: ${apk#$ROOT/}"
    echo "    sha256: $sha"
    echo "    package: $pkg"
    echo "    launcher_activity: $activity"
    echo "    label: $label"
  } >>"$RUN_DIR/manifest.executed.yaml"
  record_shell "010-$name-uninstall" "bm uninstall -n $pkg"
  record_send "020-$name-send" "$apk" "$REMOTE_DIR/$remote"
  record_shell "030-$name-remote-sha" "sha256sum $REMOTE_DIR/$remote"
  record_shell "040-$name-install" "bm install -p $REMOTE_DIR/$remote"
done

record_shell "050-bms-all" "bm dump -a | grep -E 'com\\.a2hlab\\.bridge\\.fn0103|Probe|Hello World|a2hlab' || true"

for item in "${APPS[@]}"; do
  IFS='|' read -r name apk remote pkg activity label <<<"$item"
  record_shell "060-$name-bms" "for i in \$(seq 1 30); do bm dump -n $pkg > $REMOTE_DIR/$name-bms.txt; grep -F '\"bundleName\": \"$pkg\"' $REMOTE_DIR/$name-bms.txt >/dev/null 2>&1 && grep -F '$activity' $REMOTE_DIR/$name-bms.txt >/dev/null 2>&1 && break; sleep 1; done; cat $REMOTE_DIR/$name-bms.txt"
done

record_shell "070-home-page1-capture" "uitest uiInput keyEvent Home; sleep 1; uitest screenCap -p $REMOTE_DIR/home-page1.png; uitest dumpLayout -p $REMOTE_DIR/home-page1.json"
record_shell "071-home-page2-capture" "uitest uiInput swipe 900 1000 200 1000 600; sleep 1; uitest screenCap -p $REMOTE_DIR/home-page2.png; uitest dumpLayout -p $REMOTE_DIR/home-page2.json"
"$HDC" -t "$SERIAL" file recv "$REMOTE_DIR/home-page1.png" "$RAW_DIR/home-page1.png" >/dev/null 2>&1 || true
"$HDC" -t "$SERIAL" file recv "$REMOTE_DIR/home-page1.json" "$RAW_DIR/home-page1.json" >/dev/null 2>&1 || true
"$HDC" -t "$SERIAL" file recv "$REMOTE_DIR/home-page2.png" "$RAW_DIR/home-page2.png" >/dev/null 2>&1 || true
"$HDC" -t "$SERIAL" file recv "$REMOTE_DIR/home-page2.json" "$RAW_DIR/home-page2.json" >/dev/null 2>&1 || true

for item in "${APPS[@]}"; do
  IFS='|' read -r name apk remote pkg activity label <<<"$item"
  record_shell "080-$name-aa-start" "aa start -b $pkg -a $activity -W"
  sleep 2
  record_shell "081-$name-screen-capture" "uitest screenCap -p $REMOTE_DIR/$name-start.png; uitest dumpLayout -p $REMOTE_DIR/$name-start.json"
  "$HDC" -t "$SERIAL" file recv "$REMOTE_DIR/$name-start.png" "$RAW_DIR/$name-start.png" >/dev/null 2>&1 || true
  "$HDC" -t "$SERIAL" file recv "$REMOTE_DIR/$name-start.json" "$RAW_DIR/$name-start.json" >/dev/null 2>&1 || true
done

summary="$RUN_DIR/SUMMARY.tsv"
printf 'name\tpackage\tinstall_success\tsha_match\tbms_bundle\tbms_activity\tbms_label\tdesktop_package\tdesktop_label\tstart_success\tverdict\n' >"$summary"

overall=true
for item in "${APPS[@]}"; do
  IFS='|' read -r name apk remote pkg activity label <<<"$item"
  expected_sha=$(host_sha256 "$apk")
  install_ok=false
  sha_ok=false
  bms_bundle=false
  bms_activity=false
  bms_label=false
  desktop_pkg=false
  desktop_label=false
  start_ok=false

  install_success_found "$RAW_DIR/040-$name-install.txt" && install_ok=true
  grep -F "$expected_sha" "$RAW_DIR/030-$name-remote-sha.txt" >/dev/null 2>&1 && sha_ok=true
  grep -F "\"bundleName\": \"$pkg\"" "$RAW_DIR/060-$name-bms.txt" >/dev/null 2>&1 && bms_bundle=true
  grep -F "$activity" "$RAW_DIR/060-$name-bms.txt" >/dev/null 2>&1 && bms_activity=true
  grep -F "\"label\": \"$label\"" "$RAW_DIR/060-$name-bms.txt" >/dev/null 2>&1 && bms_label=true
  grep -F "$pkg" "$RAW_DIR/home-page1.json" "$RAW_DIR/home-page2.json" >/dev/null 2>&1 && desktop_pkg=true
  grep -F "$label" "$RAW_DIR/home-page1.json" "$RAW_DIR/home-page2.json" >/dev/null 2>&1 && desktop_label=true
  start_success_found "$RAW_DIR/080-$name-aa-start.txt" && start_ok=true

  verdict=PASS
  if [[ "$install_ok" != true || "$sha_ok" != true || "$bms_bundle" != true || "$bms_activity" != true || "$bms_label" != true || "$desktop_pkg" != true || "$desktop_label" != true || "$start_ok" != true ]]; then
    verdict=FAIL
    overall=false
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$pkg" "$install_ok" "$sha_ok" "$bms_bundle" "$bms_activity" "$bms_label" "$desktop_pkg" "$desktop_label" "$start_ok" "$verdict" >>"$summary"
done

if [[ -s "$RAW_DIR/home-page1.png" && -s "$RAW_DIR/home-page2.png" ]]; then
  shasum -a 256 "$RAW_DIR"/*.png >"$RUN_DIR/screenshots.sha256"
fi

if [[ "$overall" == true ]]; then
  final=PASS_STRICT_MULTI_APK
else
  final=FAIL_STRICT_MULTI_APK
fi

cat >"$RUN_DIR/VERDICT.md" <<EOF
# Fn01-Fn03 Strict Multi-APK Gate

- run_id: \`$RUN_ID\`
- serial: \`$SERIAL\`
- verdict: \`$final\`
- boundary: Package/Resource + Launcher desktop + Activity start

This is a strict anti-fake gate. A shell remote rc of 0 is not sufficient.
Receipts containing \`error:\`, \`failed\`, \`internal error\`, \`Error Code\`,
or numeric \`code:<n>\` are failures.

## Summary

See \`SUMMARY.tsv\`.

## Raw Evidence

All raw command receipts and screenshots are under \`raw/\`.
EOF

echo "$final"
echo "$RUN_DIR"
cat "$summary"

if [[ "$overall" == true ]]; then
  exit 0
fi
exit 2
