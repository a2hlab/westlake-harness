#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 <admission-request-dir> <arm64-probe> <remote-state-root> <evidence-jsonl>" >&2
  exit 64
fi

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
REQUEST_DIR=$1
ARTIFACT=$2
REMOTE_STATE_ROOT=$3
EVIDENCE=$4
PROBE_MANIFEST="$SCRIPT_DIR/device-probe-manifest.json"
ARTIFACT_MANIFEST="$SCRIPT_DIR/device-probe-artifact-manifest.json"
ADMISSION="$REPO_ROOT/tools/br-incremental-execution"
HDC_BIN=${HDC_BIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}
OPERATIONS=(fixture_prepare query resolver launcher token process)

fail()
{
  echo "DEVICE_RUNNER_DENY $*" >&2
  exit 65
}

[[ -x "$ADMISSION" ]] || fail "admission CLI is not executable"
[[ -f "$PROBE_MANIFEST" ]] || fail "typed probe manifest missing"
[[ -f "$ARTIFACT_MANIFEST" ]] || fail "typed artifact manifest missing"
[[ -f "$ARTIFACT" ]] || fail "ARM64 probe missing"

ACTION_ID=$(jq -er '.action_id' "$PROBE_MANIFEST")
DEPLOY_SET_ID=$(jq -er '.compatible_deploy_set_id' "$PROBE_MANIFEST")
PROBE_SET_ID=$(jq -er '.probe_set_id' "$PROBE_MANIFEST")
TARGET_SERIAL=$(jq -er '.target_serial' "$PROBE_MANIFEST")
ENTRYPOINT=$(jq -er '.entrypoint_path' "$PROBE_MANIFEST")
EXPECTED_ARTIFACT_SHA=$(jq -er \
  '.artifacts[] | select(.role == "target_fence_probe") | .sha256' \
  "$ARTIFACT_MANIFEST")
PROBE_MANIFEST_SHA=$(shasum -a 256 "$PROBE_MANIFEST" | awk '{print $1}')
ARTIFACT_MANIFEST_SHA=$(shasum -a 256 "$ARTIFACT_MANIFEST" | awk '{print $1}')
ACTUAL_ARTIFACT_SHA=$(shasum -a 256 "$ARTIFACT" | awk '{print $1}')

[[ "$ACTION_ID" == "Fn01.A11" ]] || fail "wrong action"
[[ "$TARGET_SERIAL" =~ ^[A-Za-z0-9._:-]+$ ]] ||
  fail "unsafe target serial"
[[ "$ENTRYPOINT" =~ ^/data/local/tmp/[A-Za-z0-9._/-]+$ ]] ||
  fail "unsafe entrypoint"
[[ "$REMOTE_STATE_ROOT" =~ ^/data/local/tmp/[A-Za-z0-9._/-]+$ ]] ||
  fail "unsafe remote state root"
[[ "$ACTUAL_ARTIFACT_SHA" == "$EXPECTED_ARTIFACT_SHA" ]] ||
  fail "local probe artifact hash mismatch"

admit()
{
  local operation=$1
  local request="$REQUEST_DIR/$operation.json"
  local decision
  [[ -f "$request" ]] || fail "missing exact request for $operation"
  [[ "$(jq -er '.operation' "$request")" == "$operation" ]] ||
    fail "request operation mismatch for $operation"
  [[ "$(jq -er '.action_id' "$request")" == "$ACTION_ID" ]] ||
    fail "request action mismatch for $operation"
  [[ "$(jq -er '.deploy_set_id' "$request")" == "$DEPLOY_SET_ID" ]] ||
    fail "request deploy set mismatch for $operation"
  [[ "$(jq -er '.probe_set_id' "$request")" == "$PROBE_SET_ID" ]] ||
    fail "request probe set mismatch for $operation"
  [[ "$(jq -er '.target_serial' "$request")" == "$TARGET_SERIAL" ]] ||
    fail "request target mismatch for $operation"
  [[ "$(jq -er '.probe_manifest_sha256' "$request")" == "$PROBE_MANIFEST_SHA" ]] ||
    fail "request probe manifest hash mismatch for $operation"
  [[ "$(jq -er '.artifact_manifest_sha256' "$request")" == "$ARTIFACT_MANIFEST_SHA" ]] ||
    fail "request artifact manifest hash mismatch for $operation"
  decision=$("$ADMISSION" probe-admission --request "$request") ||
    fail "probe-admission rejected $operation"
  jq -e '.decision == "ALLOW_REGISTERED_PROBE_OPERATION"' \
    <<<"$decision" >/dev/null ||
    fail "probe-admission returned non-ALLOW for $operation"
}

# Global fail-closed preflight: a denial for any operation occurs before the
# runner is permitted to execute even a read-only hdc command.
for operation in "${OPERATIONS[@]}"; do
  admit "$operation"
done

: >"$EVIDENCE"
for operation in "${OPERATIONS[@]}"; do
  # Re-admit immediately before the corresponding device operation so a
  # registry change cannot inherit an earlier decision.
  admit "$operation"
  request="$REQUEST_DIR/$operation.json"
  expected_boot=$(jq -er '.boot_id' "$request")
  observed_boot=$("$HDC_BIN" -t "$TARGET_SERIAL" shell \
    "cat /proc/sys/kernel/random/boot_id" | tr -d '\r\n')
  [[ "$observed_boot" == "$expected_boot" ]] ||
    fail "live boot mismatch before $operation"

  if [[ "$operation" == "fixture_prepare" ]]; then
    "$HDC_BIN" -t "$TARGET_SERIAL" file send "$ARTIFACT" "$ENTRYPOINT"
    "$HDC_BIN" -t "$TARGET_SERIAL" shell "chmod 700 $ENTRYPOINT"
    remote_sha=$("$HDC_BIN" -t "$TARGET_SERIAL" shell \
      "sha256sum $ENTRYPOINT" | awk '{print $1}' | tr -d '\r\n')
    [[ "$remote_sha" == "$EXPECTED_ARTIFACT_SHA" ]] ||
      fail "deployed probe artifact hash mismatch"
  fi

  "$HDC_BIN" -t "$TARGET_SERIAL" shell \
    "$ENTRYPOINT $REMOTE_STATE_ROOT $operation" | tee -a "$EVIDENCE"
done
