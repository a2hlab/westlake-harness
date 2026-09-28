#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
if [[ $# -gt 1 ]]; then
  echo "usage: $0 [fresh-receipt-dir]" >&2
  exit 64
fi
if [[ $# -eq 1 ]]; then
  REQUEST_DIR=$1
  if [[ -e "$REQUEST_DIR" ]]; then
    echo "fresh-receipt-dir already exists: $REQUEST_DIR" >&2
    exit 73
  fi
  mkdir -p "$REQUEST_DIR"
else
  REQUEST_DIR=$(mktemp -d /tmp/fn01-a11-admission-negative.XXXXXX)
fi
STDOUT="$REQUEST_DIR/stdout"
STDERR="$REQUEST_DIR/stderr"
HDC_MARKER="$REQUEST_DIR/hdc-invocations.txt"
OPERATIONS=(fixture_prepare query resolver launcher token process)
PROBE_MANIFEST_SHA=$(shasum -a 256 \
  "$SCRIPT_DIR/device-probe-manifest.json" | awk '{print $1}')
ARTIFACT_MANIFEST_SHA=$(shasum -a 256 \
  "$SCRIPT_DIR/device-probe-artifact-manifest.json" | awk '{print $1}')
ACTION_ID=$(jq -er '.action_id' "$SCRIPT_DIR/device-probe-manifest.json")
DEPLOY_SET_ID=$(jq -er '.compatible_deploy_set_id' \
  "$SCRIPT_DIR/device-probe-manifest.json")
PROBE_SET_ID=$(jq -er '.probe_set_id' "$SCRIPT_DIR/device-probe-manifest.json")
TARGET_SERIAL=$(jq -er '.target_serial' "$SCRIPT_DIR/device-probe-manifest.json")
ARTIFACT_PATH=$(jq -er \
  '.artifacts[] | select(.role == "target_fence_probe") | .path' \
  "$SCRIPT_DIR/device-probe-artifact-manifest.json")

for operation in "${OPERATIONS[@]}"; do
  jq -n \
    --arg operation "$operation" \
    --arg probeManifest "$PROBE_MANIFEST_SHA" \
    --arg artifactManifest "$ARTIFACT_MANIFEST_SHA" \
    --arg actionId "$ACTION_ID" \
    --arg deploySetId "$DEPLOY_SET_ID" \
    --arg probeSetId "$PROBE_SET_ID" \
    --arg targetSerial "$TARGET_SERIAL" \
    '{
      schema_version: 1,
      action_id: $actionId,
      deploy_set_id: $deploySetId,
      probe_set_id: $probeSetId,
      target_serial: $targetSerial,
      boot_id: "76531440-fe1f-4216-9f9d-af28f4c9af75",
      operation: $operation,
      authority_registry_sha256:
        "0000000000000000000000000000000000000000000000000000000000000000",
      candidate_manifest_sha256:
        "213514e403f095c70733b01d0ef3759fa8498c8c968929e406eceea11c6cd9f3",
      probe_manifest_sha256: $probeManifest,
      artifact_manifest_sha256: $artifactManifest
    }' >"$REQUEST_DIR/$operation.json"
done

if FN01_HDC_INVOCATION_MARKER="$HDC_MARKER" \
  HDC_BIN="$SCRIPT_DIR/forbidden_hdc_test_double.sh" \
  "$SCRIPT_DIR/run_on_device.sh" \
    "$REQUEST_DIR" \
    "$REPO_ROOT/$ARTIFACT_PATH" \
    "/data/local/tmp/fn01-a11-fence-state-bf39173c" \
    "$REQUEST_DIR/device-evidence.jsonl" \
    >"$STDOUT" 2>"$STDERR"; then
  echo "FAIL runner accepted a stale registry request" >&2
  exit 1
fi

grep -q "probe-admission rejected fixture_prepare" "$STDERR"
if [[ -e "$HDC_MARKER" ]] ||
  grep -q "FORBIDDEN_HDC_TEST_DOUBLE_INVOKED" "$STDERR"; then
  echo "FAIL runner attempted hdc after admission denial" >&2
  exit 1
fi
jq -n \
  --arg probe_manifest_sha256 "$PROBE_MANIFEST_SHA" \
  --arg artifact_manifest_sha256 "$ARTIFACT_MANIFEST_SHA" \
  '{
    schema_version: 1,
    case_id: "A11-RUNNER-DENY-BEFORE-HDC",
    request_count: 6,
    first_denied_operation: "fixture_prepare",
    denial: "stale authority registry sha256",
    hdc_invocations: 0,
    probe_manifest_sha256: $probe_manifest_sha256,
    artifact_manifest_sha256: $artifact_manifest_sha256,
    result: "PASS_CANDIDATE",
    formal_verdict: "NOT_ISSUED"
  }' >"$REQUEST_DIR/summary.json"
echo "PASS runner denied before any hdc command"
