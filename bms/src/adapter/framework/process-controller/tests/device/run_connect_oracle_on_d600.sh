#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C
export TZ=UTC
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
ADAPTER_ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd -P)
HDC=${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}
SERIAL=5eab586000000000000000001123012c
LOCAL=$SCRIPT_DIR/out/appspawnx_connect_oracle
RECEIPT_ROOT=${RECEIPT_ROOT:-$ADAPTER_ROOT/research/atoms/L03/A01/m02-helloworld-cycle-r1/device-runs}

: "${EXPECTED_ARTIFACT_SHA256:?EXPECTED_ARTIFACT_SHA256 is required}"
: "${LEGAL_SERVICE_RECEIPT_SHA256:?LEGAL_SERVICE_RECEIPT_SHA256 is required}"
[[ "${M07_ACK_LEGAL_SERVICE_CANDIDATE:-}" == YES ]] || {
    echo "device gate closed: M07 has not acknowledged a legal service candidate" >&2
    exit 64
}
[[ "$EXPECTED_ARTIFACT_SHA256" =~ ^[0-9a-f]{64}$ ]] || { echo "invalid artifact SHA-256" >&2; exit 65; }
[[ "$LEGAL_SERVICE_RECEIPT_SHA256" =~ ^[0-9a-f]{64}$ ]] || { echo "invalid service receipt SHA-256" >&2; exit 66; }
[[ -x "$HDC" ]] || { echo "hdc is not executable: $HDC" >&2; exit 67; }
[[ -f "$LOCAL" ]] || { echo "probe artifact is missing: $LOCAL" >&2; exit 68; }

sha256_file()
{
    shasum -a 256 "$1" | awk '{print $1}'
}

LOCAL_SHA=$(sha256_file "$LOCAL")
[[ "$LOCAL_SHA" == "$EXPECTED_ARTIFACT_SHA256" ]] || {
    echo "probe hash mismatch: expected=$EXPECTED_ARTIFACT_SHA256 actual=$LOCAL_SHA" >&2
    exit 69
}

RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)-$SERIAL
RUN_DIR=$RECEIPT_ROOT/$RUN_ID
REMOTE=/data/local/tmp/m02_connect_oracle_${EXPECTED_ARTIFACT_SHA256:0:12}
mkdir -p "$RUN_DIR"

hdc_bounded()
{
    local timeout_seconds=$1
    shift
    perl -e 'alarm shift @ARGV; exec @ARGV' "$timeout_seconds" "$HDC" -t "$SERIAL" "$@"
}

cleanup()
{
    hdc_bounded 20 shell "rm -f '$REMOTE'" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

printf '%s\n' \
    "serial=$SERIAL" \
    "artifact=$LOCAL" \
    "artifact_sha256=$LOCAL_SHA" \
    "legal_service_receipt_sha256=$LEGAL_SERVICE_RECEIPT_SHA256" \
    "remote=$REMOTE" > "$RUN_DIR/identity.env"

hdc_bounded 60 file send "$LOCAL" "$REMOTE" > "$RUN_DIR/send.log" 2>&1
REMOTE_SHA=$(hdc_bounded 20 shell "sha256sum '$REMOTE'" | tr -d '\r' | awk '{print $1}')
printf '%s\n' "$REMOTE_SHA" > "$RUN_DIR/remote.sha256"
[[ "$REMOTE_SHA" == "$EXPECTED_ARTIFACT_SHA256" ]] || {
    echo "staged hash mismatch: expected=$EXPECTED_ARTIFACT_SHA256 actual=$REMOTE_SHA" >&2
    exit 70
}
hdc_bounded 20 shell "chmod 0555 '$REMOTE'" > "$RUN_DIR/chmod.log" 2>&1

set +e
RUN_RAW=$(hdc_bounded 20 shell "'$REMOTE'; rc=\$?; printf '\\nM02_REMOTE_EXIT=%d\\n' \"\$rc\"; exit 0" 2>&1)
HDC_EXIT=$?
set -e
printf '%s\n' "$RUN_RAW" | tr -d '\r' | tee "$RUN_DIR/oracle.log"
[[ "$HDC_EXIT" -eq 0 ]] || { echo "hdc execution failed: $HDC_EXIT" >&2; exit 71; }

REMOTE_EXIT=$(printf '%s\n' "$RUN_RAW" | tr -d '\r' | sed -n 's/^M02_REMOTE_EXIT=\([0-9][0-9]*\)$/\1/p' | tail -1)
[[ "$REMOTE_EXIT" =~ ^(0|20|21|22)$ ]] || { echo "invalid remote exit: $REMOTE_EXIT" >&2; exit 72; }
printf 'remote_exit=%s\nreceipt=%s\n' "$REMOTE_EXIT" "$RUN_DIR" | tee "$RUN_DIR/RESULT.txt"
exit "$REMOTE_EXIT"

