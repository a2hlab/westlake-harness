#!/bin/bash
set -euo pipefail

usage() {
  cat >&2 <<EOF
usage: $0 [--output-root DIR --candidate-id ID] RUN_ID SERIAL [WAIT_SECONDS]

Legacy calls without options keep the historical evidence output directory.
With options, DIR is the exact output directory for this candidate.
EOF
}

die_usage() {
  echo "ERROR: $*" >&2
  usage
  exit 2
}

OUTPUT_ROOT=""
CANDIDATE_ID=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --output-root)
      [ "$#" -ge 2 ] || die_usage "--output-root requires a value"
      OUTPUT_ROOT="$2"
      shift 2
      ;;
    --candidate-id)
      [ "$#" -ge 2 ] || die_usage "--candidate-id requires a value"
      CANDIDATE_ID="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      die_usage "unknown option: $1"
      ;;
    *)
      break
      ;;
  esac
done

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  die_usage "RUN_ID and SERIAL are required"
fi
if { [ -n "$OUTPUT_ROOT" ] && [ -z "$CANDIDATE_ID" ]; } || \
   { [ -z "$OUTPUT_ROOT" ] && [ -n "$CANDIDATE_ID" ]; }; then
  die_usage "--output-root and --candidate-id must be supplied together"
fi

RUN_ID="$1"
SERIAL="$2"
WAIT_SECONDS="${3:-300}"
BRIDGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HDC_BIN="${HDC_BIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"

[[ "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]] || die_usage "invalid RUN_ID: $RUN_ID"
[[ "$SERIAL" =~ ^[A-Za-z0-9._:-]+$ ]] || die_usage "invalid SERIAL: $SERIAL"
[[ "$WAIT_SECONDS" =~ ^[0-9]+$ ]] && [ "$WAIT_SECONDS" -gt 0 ] || \
  die_usage "WAIT_SECONDS must be a positive integer"

if [ -n "$OUTPUT_ROOT" ]; then
  [ "$OUTPUT_ROOT" != "/" ] || die_usage "--output-root cannot be /"
  [[ "$CANDIDATE_ID" =~ ^[A-Za-z0-9._-]+$ ]] || \
    die_usage "invalid candidate ID: $CANDIDATE_ID"
  OUT="$OUTPUT_ROOT"
  INVOCATION_MODE="EXPLICIT_CANDIDATE_ROOT"
else
  CANDIDATE_ID="$RUN_ID"
  OUT="$BRIDGE_ROOT/evidence/concepts/fn08-fn12-d600-early/$RUN_ID/$SERIAL"
  INVOCATION_MODE="LEGACY_COMPATIBLE_ROOT"
fi

mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd -P)"
CANDIDATE_MARKER="$OUT/.bridge-candidate-marker"
EXPECTED_MARKER="BRIDGE_CANDIDATE_MARKER_V1
candidate_id=$CANDIDATE_ID
run_id=$RUN_ID
device_serial=$SERIAL"

if [ -e "$CANDIDATE_MARKER" ]; then
  ACTUAL_MARKER="$(cat "$CANDIDATE_MARKER")"
  if [ "$ACTUAL_MARKER" != "$EXPECTED_MARKER" ]; then
    echo "ERROR: candidate marker conflict at $CANDIDATE_MARKER" >&2
    echo "expected candidate_id=$CANDIDATE_ID run_id=$RUN_ID device_serial=$SERIAL" >&2
    exit 2
  fi
elif ! (set -o noclobber; printf '%s\n' "$EXPECTED_MARKER" > "$CANDIDATE_MARKER") 2>/dev/null; then
  ACTUAL_MARKER="$(cat "$CANDIDATE_MARKER" 2>/dev/null || true)"
  [ "$ACTUAL_MARKER" = "$EXPECTED_MARKER" ] || {
    echo "ERROR: concurrent candidate marker conflict at $CANDIDATE_MARKER" >&2
    exit 2
  }
fi

collect_persistent_index() {
  {
    "$HDC_BIN" -t "$SERIAL" shell \
      "find /sys/fs/pstore -maxdepth 1 -type f -print 2>/dev/null || true" |
      tr -d '\r' |
      awk 'NF { print "pstore\t" $0 }'
    "$HDC_BIN" -t "$SERIAL" shell \
      "find /data/log/faultlog/faultlogger /data/log/faultlog/temp -maxdepth 1 -type f -size -8388608c -print 2>/dev/null || true" |
      tr -d '\r' |
      awk 'NF { print "faultlog\t" $0 }'
  } | LC_ALL=C sort -u
}

freeze_index() {
  local target="$1"
  local temp="${target}.tmp.$$"
  collect_persistent_index > "$temp"
  if [ -e "$target" ]; then
    if ! cmp -s "$temp" "$target"; then
      rm -f "$temp"
      echo "ERROR: pre-crash index conflict for candidate $CANDIDATE_ID: $target" >&2
      exit 2
    fi
    rm -f "$temp"
  else
    mv "$temp" "$target"
  fi
}

initial_boot="$("$HDC_BIN" -t "$SERIAL" shell \
  "cat /proc/sys/kernel/random/boot_id" | tr -d '\r')"
[ -n "$initial_boot" ] || {
  echo "ERROR: device returned an empty boot ID" >&2
  exit 1
}

PRE_INDEX="$OUT/persistent-log-index-before.tsv"
freeze_index "$PRE_INDEX"
PRE_INDEX_SHA256="$(shasum -a 256 "$PRE_INDEX" | awk '{print $1}')"

{
  echo "schema_version: '1.0'"
  echo "receipt_type: D600_RECONNECT_MONITOR_BASELINE"
  echo "source_candidate_id: $CANDIDATE_ID"
  echo "source_run_id: $RUN_ID"
  echo "device_serial: $SERIAL"
  echo "initial_boot_id: $initial_boot"
  echo "wait_seconds: $WAIT_SECONDS"
  echo "invocation_mode: $INVOCATION_MODE"
  echo "candidate_marker: .bridge-candidate-marker"
  echo "pre_index: persistent-log-index-before.tsv"
  echo "pre_index_sha256: $PRE_INDEX_SHA256"
} > "$OUT/reconnect-monitor-baseline.txt"

capture_after_reconnect() {
  "$BRIDGE_ROOT/tools/experiments/d600/capture_post_crash_state.sh" \
    --output-root "$OUT" \
    --candidate-id "$CANDIDATE_ID" \
    "$RUN_ID" "$SERIAL" 60
}

deadline="$(( $(date +%s) + WAIT_SECONDS ))"
saw_disconnect=0
while [ "$(date +%s)" -lt "$deadline" ]; do
  if "$HDC_BIN" list targets | awk -v serial="$SERIAL" \
      '$1 == serial { found=1 } END { exit !found }'; then
    if [ "$saw_disconnect" -eq 1 ]; then
      capture_after_reconnect
      exit 0
    fi
    current_boot="$("$HDC_BIN" -t "$SERIAL" shell \
      "cat /proc/sys/kernel/random/boot_id" 2>/dev/null | tr -d '\r' || true)"
    if [ -n "$current_boot" ] && [ "$current_boot" != "$initial_boot" ]; then
      capture_after_reconnect
      exit 0
    fi
  else
    if [ "$saw_disconnect" -eq 0 ]; then
      {
        echo "schema_version: '1.0'"
        echo "receipt_type: D600_DISCONNECT_OBSERVATION"
        echo "source_candidate_id: $CANDIDATE_ID"
        echo "source_run_id: $RUN_ID"
        echo "device_serial: $SERIAL"
        echo "disconnect_observed_at_epoch: $(date +%s)"
        echo "initial_boot_id: $initial_boot"
      } > "$OUT/disconnect-observed.txt"
    fi
    saw_disconnect=1
  fi
  sleep 0.25
done

{
  echo "schema_version: '1.0'"
  echo "receipt_type: D600_RECONNECT_MONITOR_RESULT"
  echo "verdict: NO_RECONNECT_EVENT_WITHIN_WINDOW"
  echo "source_candidate_id: $CANDIDATE_ID"
  echo "source_run_id: $RUN_ID"
  echo "device_serial: $SERIAL"
  echo "initial_boot_id: $initial_boot"
  echo "saw_disconnect: $saw_disconnect"
  echo "claim_boundary: RECONNECT_MONITOR_ONLY"
} > "$OUT/RECONNECT-MONITOR-VERDICT.yaml"
exit 1
