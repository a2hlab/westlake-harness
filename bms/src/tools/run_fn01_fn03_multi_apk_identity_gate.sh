#!/bin/bash
set -euo pipefail

ROOT="${ROOT:-/opt/Bridge}"
SERIAL="${SERIAL:-61b0657200000000000000000324012c}"
RUN_ID="${RUN_ID:-fn01-fn03-multi-apk-probes-$(date -u +%Y%m%dT%H%M%SZ)}"
HDC="${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
RUN_DIR="$ROOT/evidence/runs/$RUN_ID"
RAW_DIR="$RUN_DIR/raw"
REMOTE_DIR="/data/local/tmp/$RUN_ID"

mkdir -p "$RAW_DIR"

APPS=(
  "ProbeAlpha|$ROOT/APKS/Fn01F03-ProbeAlpha/dist/fn0103-probe-alpha.apk|fn0103-probe-alpha.apk|com.a2hlab.bridge.fn0103.alpha|com.a2hlab.bridge.fn0103.alpha.AlphaActivity|Probe Alpha|res/mipmap-mdpi-v4/ic_launcher.png"
  "ProbeBeta|$ROOT/APKS/Fn01F03-ProbeBeta/dist/fn0103-probe-beta.apk|fn0103-probe-beta.apk|com.a2hlab.bridge.fn0103.beta|com.a2hlab.bridge.fn0103.beta.BetaEntryActivity|Probe Beta|res/mipmap-mdpi-v4/ic_launcher.png"
  "ProbeGamma|$ROOT/APKS/Fn01F03-ProbeGamma/dist/fn0103-probe-gamma.apk|fn0103-probe-gamma.apk|com.a2hlab.bridge.fn0103.gamma|com.a2hlab.bridge.fn0103.gamma.GammaHomeActivity|Probe Gamma|res/mipmap-mdpi-v4/ic_launcher.png"
)

host_sha256() {
  shasum -a 256 "$1" | awk '{print $1}'
}

receipt_host() {
  local name="$1"
  shift
  local out="$RAW_DIR/$name.txt"
  {
    echo "receipt_kind=host"
    echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "exact_command=$*"
    echo "combined_output_begin"
    "$@"
    local rc=$?
    echo "combined_output_end"
    echo "host_rc=$rc"
    echo "ended_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    return "$rc"
  } >"$out" 2>&1 || true
}

receipt_hdc_shell() {
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
    return "$rc"
  } >"$out" 2>&1 || true
}

receipt_hdc_send() {
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
    return "$rc"
  } >"$out" 2>&1 || true
}

exact_bundle_found() {
  local file="$1"
  local pkg="$2"
  grep -F "\"bundleName\": \"$pkg\"" "$file" >/dev/null 2>&1
}

exact_activity_found() {
  local file="$1"
  local activity="$2"
  grep -F "$activity" "$file" >/dev/null 2>&1
}

install_success_found() {
  local file="$1"
  grep -F "__REMOTE_RC__=0" "$file" >/dev/null 2>&1 || return 1
  grep -Ei "error:|failed|internal error|code:[0-9]+" "$file" >/dev/null 2>&1 && return 1
  grep -Ei "success|succeed|successfully|install bundle successfully" "$file" >/dev/null 2>&1
}

receipt_host "001-hdc-list-targets" "$HDC" list targets
receipt_hdc_shell "002-version" "param get const.product.software.version"
receipt_hdc_shell "003-selinux" "getenforce"
receipt_hdc_shell "004-boot-id" "cat /proc/sys/kernel/random/boot_id"
receipt_hdc_shell "005-create-stage" "rm -rf $REMOTE_DIR && mkdir -p $REMOTE_DIR/receipts"

cat > "$RUN_DIR/manifest.executed.yaml" <<EOF
schema_version: 1
run_id: $RUN_ID
serial: $SERIAL
remote_dir: $REMOTE_DIR
boundary: Package/Resource
ui_allowed_after_identity_gate: true
cleanup_policy: leave_probe_apks_installed_for_desktop_icon_inspection
apps:
EOF

for item in "${APPS[@]}"; do
  IFS='|' read -r name apk remote pkg activity label icon <<<"$item"
  test -f "$apk"
  sha=$(host_sha256 "$apk")
  {
    echo "  - name: $name"
    echo "    apk: ${apk#$ROOT/}"
    echo "    sha256: $sha"
    echo "    package: $pkg"
    echo "    launcher_activity: $activity"
    echo "    label: $label"
    echo "    icon: $icon"
  } >> "$RUN_DIR/manifest.executed.yaml"

  receipt_hdc_shell "010-$name-pre-bms" "bm dump -n $pkg > $REMOTE_DIR/receipts/$name-pre-bms.txt; cat $REMOTE_DIR/receipts/$name-pre-bms.txt"
  receipt_hdc_send "020-$name-send" "$apk" "$REMOTE_DIR/$remote"
  receipt_hdc_shell "030-$name-remote-sha" "sha256sum $REMOTE_DIR/$remote"
  receipt_hdc_shell "040-$name-install" "bm install -p $REMOTE_DIR/$remote"
  receipt_hdc_shell "050-$name-after-bms" "for i in \$(seq 1 20); do bm dump -n $pkg > $REMOTE_DIR/receipts/$name-after-bms.txt; grep -F '\"bundleName\": \"$pkg\"' $REMOTE_DIR/receipts/$name-after-bms.txt >/dev/null 2>&1 && grep -F '$activity' $REMOTE_DIR/receipts/$name-after-bms.txt >/dev/null 2>&1 && break; sleep 1; done; cat $REMOTE_DIR/receipts/$name-after-bms.txt"
  "$HDC" -t "$SERIAL" file recv "$REMOTE_DIR/receipts/$name-after-bms.txt" "$RAW_DIR/$name-after-bms-device.txt" >/dev/null 2>&1 || true
done

identity_pass=true
summary="$RUN_DIR/SUMMARY.tsv"
printf 'name\tpackage\tinstall_success\tremote_sha_matches\texact_bundle\texact_activity\tverdict\n' > "$summary"

for item in "${APPS[@]}"; do
  IFS='|' read -r name apk remote pkg activity label icon <<<"$item"
  expected_sha=$(host_sha256 "$apk")
  install_receipt="$RAW_DIR/040-$name-install.txt"
  sha_receipt="$RAW_DIR/030-$name-remote-sha.txt"
  bms_file="$RAW_DIR/$name-after-bms-device.txt"

  install_ok=false
  sha_ok=false
  bundle_ok=false
  activity_ok=false
  verdict=FAIL_INSTALL_OR_QUERY

  install_success_found "$install_receipt" && install_ok=true
  grep -F "$expected_sha" "$sha_receipt" >/dev/null 2>&1 && sha_ok=true
  exact_bundle_found "$bms_file" "$pkg" && bundle_ok=true
  exact_activity_found "$bms_file" "$activity" && activity_ok=true

  if [[ "$install_ok" == true && "$sha_ok" == true && "$bundle_ok" == true && "$activity_ok" == true ]]; then
    verdict=PASS_IDENTITY_GATE
  else
    identity_pass=false
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$pkg" "$install_ok" "$sha_ok" "$bundle_ok" "$activity_ok" "$verdict" >> "$summary"
done

if [[ "$identity_pass" == true ]]; then
  overall=PASS_IDENTITY_GATE
else
  overall=FAIL_IDENTITY_GATE
fi

cat > "$RUN_DIR/VERDICT.md" <<EOF
# Fn01-Fn03 Multi-APK Probe Identity Gate

- run_id: \`$RUN_ID\`
- serial: \`$SERIAL\`
- verdict: \`$overall\`
- cleanup_policy: probe APKs left installed for desktop icon inspection

This verdict is limited to install/query identity. It is not a formal Fn01-Fn03
Action verdict and it is not UI verification.

## Gate

Each APK must satisfy all of:

- host-to-device SHA-256 matches;
- \`bm install -p\` reports success and does not print an error, failure, internal-error, or numeric error-code receipt;
- \`bm dump -n <package>\` contains exact \`"bundleName": "<package>"\`;
- the same BMS dump contains the declared launcher activity.

## Summary

See \`SUMMARY.tsv\`.
EOF

receipt_hdc_shell "090-final-selinux" "getenforce"
receipt_hdc_shell "091-stage-list" "find $REMOTE_DIR -maxdepth 2 -type f | sort"

echo "$overall"
echo "$RUN_DIR"
cat "$summary"

if [[ "$identity_pass" == true ]]; then
  exit 0
fi
exit 2
