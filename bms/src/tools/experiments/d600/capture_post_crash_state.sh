#!/bin/bash
set -euo pipefail

usage() {
  cat >&2 <<EOF
usage: $0 [--output-root DIR --candidate-id ID] RUN_ID SERIAL [WAIT_SECONDS]

Legacy calls without options keep the historical evidence output directory.
With options, DIR must contain the pre-crash index frozen by the reconnect monitor.
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

write_block_receipt() {
  local verdict="$1"
  local error_type="$2"
  {
    echo "schema_version: '1.0'"
    echo "receipt_type: D600_POST_CRASH_INCREMENT"
    echo "verdict: $verdict"
    echo "error_type: $error_type"
    echo "source_candidate_id: $CANDIDATE_ID"
    echo "source_run_id: $RUN_ID"
    echo "device_serial: $SERIAL"
    echo "invocation_mode: $INVOCATION_MODE"
    echo "candidate_marker: .bridge-candidate-marker"
    echo "claim_boundary: POST_RECONNECT_CRASH_ARTIFACT_COLLECTION_ONLY"
  } > "$OUT/CAPTURE-VERDICT.yaml"
}

PRE_INDEX="$OUT/persistent-log-index-before.tsv"
BASELINE_MODE="FROZEN_PRE_CRASH_INDEX"
if [ ! -f "$PRE_INDEX" ]; then
  if [ "$INVOCATION_MODE" = "EXPLICIT_CANDIDATE_ROOT" ]; then
    write_block_receipt "BLOCK_PRE_CRASH_INDEX_MISSING" "PRE_CRASH_INDEX_REQUIRED"
    echo "ERROR: explicit candidate capture requires $PRE_INDEX" >&2
    exit 1
  fi
  # Preserve the legacy standalone call shape. It cannot distinguish old files,
  # so the receipt makes the weaker baseline explicit instead of hiding it.
  : > "$PRE_INDEX"
  BASELINE_MODE="LEGACY_EMPTY_BASELINE_ALL_CURRENT_PATHS_NEW"
fi

start_epoch="$(date +%s)"
deadline_epoch="$((start_epoch + WAIT_SECONDS))"
while ! "$HDC_BIN" list targets | awk -v serial="$SERIAL" '$1 == serial { found=1 } END { exit !found }'; do
  if [ "$(date +%s)" -ge "$deadline_epoch" ]; then
    write_block_receipt "BLOCK_DEVICE_NOT_RECONNECTED" "DEVICE_RECONNECT_TIMEOUT"
    exit 1
  fi
  sleep 1
done

capture_boot="$("$HDC_BIN" -t "$SERIAL" shell \
  "cat /proc/sys/kernel/random/boot_id" | tr -d '\r')"
[ -n "$capture_boot" ] || {
  write_block_receipt "BLOCK_CAPTURE_BOOT_ID_MISSING" "BOOT_ID_REQUIRED"
  exit 1
}

SOURCE_BOOT="UNKNOWN"
if [ -f "$OUT/reconnect-monitor-baseline.txt" ]; then
  SOURCE_BOOT="$(awk -F': ' '$1 == "initial_boot_id" { print $2; exit }' \
    "$OUT/reconnect-monitor-baseline.txt")"
  SOURCE_BOOT="${SOURCE_BOOT:-UNKNOWN}"
fi
if [ "$SOURCE_BOOT" = "UNKNOWN" ]; then
  BOOT_CHANGED="UNKNOWN"
elif [ "$SOURCE_BOOT" = "$capture_boot" ]; then
  BOOT_CHANGED="false"
else
  BOOT_CHANGED="true"
fi

"$HDC_BIN" -t "$SERIAL" shell "
cat /proc/sys/kernel/random/boot_id
cat /proc/uptime
param get const.ohos.fullname
getenforce
uname -a
pidof appspawn-x || true
pidof com.example.helloworld || true
mount | grep ' /system/android ' || true
" > "$OUT/reconnect-identity.txt" 2>&1

"$HDC_BIN" -t "$SERIAL" shell "
ls -laZ /sys/fs/pstore 2>&1
find /sys/fs/pstore -maxdepth 1 -type f -print 2>&1
ls -laZ /data/log/faultlog 2>&1
find /data/log/faultlog -maxdepth 3 -type f -print 2>&1
" > "$OUT/persistent-log-index-detail-after.txt" 2>&1

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

freeze_after_index() {
  local target="$1"
  local temp="${target}.tmp.$$"
  collect_persistent_index > "$temp"
  if [ -e "$target" ]; then
    if ! cmp -s "$temp" "$target"; then
      rm -f "$temp"
      write_block_receipt "BLOCK_POST_CRASH_INDEX_CONFLICT" "CANDIDATE_OUTPUT_REUSE"
      echo "ERROR: post-crash index conflict for candidate $CANDIDATE_ID" >&2
      exit 2
    fi
    rm -f "$temp"
  else
    mv "$temp" "$target"
  fi
}

AFTER_INDEX="$OUT/persistent-log-index-after.tsv"
NEW_INDEX="$OUT/persistent-log-index-new.tsv"
freeze_after_index "$AFTER_INDEX"
LC_ALL=C sort -u "$PRE_INDEX" -o "$PRE_INDEX"
comm -13 "$PRE_INDEX" "$AFTER_INDEX" > "$NEW_INDEX"

"$HDC_BIN" -t "$SERIAL" shell \
  "dmesg | tail -2000" > "$OUT/dmesg-after-reconnect.txt" 2>&1 || true
"$HDC_BIN" -t "$SERIAL" shell \
  "hilog -x | tail -4000" > "$OUT/hilog-after-reconnect.txt" 2>&1 || true

PSTORE_OUT="$OUT/pstore-new"
FAULTLOG_OUT="$OUT/faultlog-new"
RECV_LOG_OUT="$OUT/recv-logs"
mkdir -p "$PSTORE_OUT" "$FAULTLOG_OUT" "$RECV_LOG_OUT"

recv_requested=0
recv_succeeded=0
recv_failed=0
while IFS=$'\t' read -r kind remote_path extra; do
  [ -n "$kind" ] || continue
  [ -n "$remote_path" ] || continue
  [ -z "${extra:-}" ] || {
    echo "WARN: malformed persistent index row: $kind $remote_path $extra" >&2
    recv_failed="$((recv_failed + 1))"
    continue
  }

  case "$kind:$remote_path" in
    pstore:/sys/fs/pstore/*)
      relative_path="${remote_path#/sys/fs/pstore/}"
      local_root="$PSTORE_OUT"
      ;;
    faultlog:/data/log/faultlog/*)
      relative_path="${remote_path#/data/log/faultlog/}"
      local_root="$FAULTLOG_OUT"
      ;;
    *)
      echo "WARN: rejected unexpected persistent path: $kind $remote_path" >&2
      recv_failed="$((recv_failed + 1))"
      continue
      ;;
  esac

  case "$relative_path" in
    ""|/*|..|../*|*/../*|*/..)
      echo "WARN: rejected unsafe persistent path: $remote_path" >&2
      recv_failed="$((recv_failed + 1))"
      continue
      ;;
  esac

  recv_requested="$((recv_requested + 1))"
  local_path="$local_root/$relative_path"
  local_temp="${local_path}.partial.$$"
  mkdir -p "$(dirname "$local_path")"
  safe_log_name="${kind}-${relative_path//\//__}.recv.txt"
  if "$HDC_BIN" -t "$SERIAL" file recv "$remote_path" "$local_temp" \
      > "$RECV_LOG_OUT/$safe_log_name" 2>&1; then
    mv "$local_temp" "$local_path"
    recv_succeeded="$((recv_succeeded + 1))"
  else
    rm -f "$local_temp"
    recv_failed="$((recv_failed + 1))"
  fi
done < "$NEW_INDEX"

find "$PSTORE_OUT" "$FAULTLOG_OUT" -type f \
  -exec shasum -a 256 {} \; | LC_ALL=C sort > "$OUT/persistent-artifact-sha256.txt"

count_kind() {
  local kind="$1"
  local index="$2"
  awk -F '\t' -v expected="$kind" '$1 == expected { count++ } END { print count + 0 }' "$index"
}

pstore_before_count="$(count_kind pstore "$PRE_INDEX")"
pstore_after_count="$(count_kind pstore "$AFTER_INDEX")"
pstore_new_count="$(count_kind pstore "$NEW_INDEX")"
faultlog_before_count="$(count_kind faultlog "$PRE_INDEX")"
faultlog_after_count="$(count_kind faultlog "$AFTER_INDEX")"
faultlog_new_count="$(count_kind faultlog "$NEW_INDEX")"
pre_index_sha256="$(shasum -a 256 "$PRE_INDEX" | awk '{print $1}')"
after_index_sha256="$(shasum -a 256 "$AFTER_INDEX" | awk '{print $1}')"
new_index_sha256="$(shasum -a 256 "$NEW_INDEX" | awk '{print $1}')"

if [ "$recv_failed" -gt 0 ]; then
  VERDICT="CAPTURE_PARTIAL"
  ERROR_TYPE="NEW_PERSISTENT_ARTIFACT_RECEIVE_FAILED"
elif [ "$pstore_new_count" -eq 0 ] && [ "$faultlog_new_count" -eq 0 ]; then
  VERDICT="CAPTURED_NO_NEW_PERSISTENT_ARTIFACTS"
  ERROR_TYPE="NONE"
else
  VERDICT="CAPTURED_NEW_PERSISTENT_ARTIFACTS"
  ERROR_TYPE="NONE"
fi

{
  echo "schema_version: '1.0'"
  echo "receipt_type: D600_POST_CRASH_INCREMENT"
  echo "verdict: $VERDICT"
  echo "error_type: $ERROR_TYPE"
  echo "risk: R0_READ_ONLY"
  echo "source_candidate_id: $CANDIDATE_ID"
  echo "source_run_id: $RUN_ID"
  echo "source_candidate_ref: .bridge-candidate-marker"
  echo "device_serial: $SERIAL"
  echo "source_boot_id: $SOURCE_BOOT"
  echo "capture_boot_id: $capture_boot"
  echo "boot_changed: $BOOT_CHANGED"
  echo "baseline_mode: $BASELINE_MODE"
  echo "pre_index: persistent-log-index-before.tsv"
  echo "pre_index_sha256: $pre_index_sha256"
  echo "after_index: persistent-log-index-after.tsv"
  echo "after_index_sha256: $after_index_sha256"
  echo "new_index: persistent-log-index-new.tsv"
  echo "new_index_sha256: $new_index_sha256"
  echo "pstore_before_count: $pstore_before_count"
  echo "pstore_after_count: $pstore_after_count"
  echo "pstore_new_count: $pstore_new_count"
  echo "faultlog_before_count: $faultlog_before_count"
  echo "faultlog_after_count: $faultlog_after_count"
  echo "faultlog_new_count: $faultlog_new_count"
  echo "recv_requested: $recv_requested"
  echo "recv_succeeded: $recv_succeeded"
  echo "recv_failed: $recv_failed"
  echo "claim_boundary: POST_RECONNECT_CRASH_ARTIFACT_COLLECTION_ONLY"
} > "$OUT/CAPTURE-VERDICT.yaml"

if [ "$recv_failed" -gt 0 ]; then
  echo "PARTIAL: $OUT" >&2
  exit 1
fi

echo "CAPTURED: $OUT"
