#!/usr/bin/env bash
#
# Non-app-specific, exact-serial device observation harness for the
# generation-bound Surface -> RenderService direct path.
#
# The workload is an external executable with this contract:
#   workload --serial SERIAL --stage \
#     prepare|first-frame|continuous-frame|resize-rotation|surface-loss|recover|rollback
#
# The gate never clears hilog, installs artifacts, or declares a verification
# PASS.  It records direct-path and RenderService observations in a temporary
# directory, always asks the workload to roll back, and reports broker as
# NOT_RUN unless a future separately-authorized experiment supplies it.

set -euo pipefail

readonly REQUIRED_SERIAL="5583f5be00000000000000000323012c"
serial=""
workload=""
check_only=0
run_dir=""
prepared=0

usage()
{
    echo "usage: $0 --serial $REQUIRED_SERIAL [--check-only | --workload EXECUTABLE]" >&2
}

cleanup()
{
    if [[ "$prepared" -eq 1 && -n "$workload" ]]; then
        "$workload" --serial "$serial" --stage rollback >/dev/null 2>&1 || true
    fi
    if [[ -n "$run_dir" && -d "$run_dir" ]]; then
        rm -rf "$run_dir"
    fi
}
trap cleanup EXIT INT TERM

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --serial)
            [[ "$#" -ge 2 ]] || { usage; exit 64; }
            serial="$2"
            shift 2
            ;;
        --workload)
            [[ "$#" -ge 2 ]] || { usage; exit 64; }
            workload="$2"
            shift 2
            ;;
        --check-only)
            check_only=1
            shift
            ;;
        *)
            usage
            exit 64
            ;;
    esac
done

if [[ "$serial" != "$REQUIRED_SERIAL" ]]; then
    echo "REFUSED: exact serial must be $REQUIRED_SERIAL" >&2
    exit 65
fi
if ! command -v hdc >/dev/null 2>&1; then
    echo "BLOCKED: hdc is not available" >&2
    exit 69
fi
if ! hdc list targets 2>/dev/null | tr -d '\r' | awk -v wanted="$serial" '$1 == wanted { found=1 } END { exit !found }'; then
    echo "BLOCKED: physical first-bad is hdc enumeration for $serial" >&2
    exit 69
fi
if [[ "$check_only" -eq 1 ]]; then
    echo "READY: exact target enumerated; no device state changed"
    exit 0
fi
if [[ -z "$workload" || ! -x "$workload" ]]; then
    echo "BLOCKED: --workload must name an executable implementing the stage contract" >&2
    exit 66
fi

run_dir="$(mktemp -d "${TMPDIR:-/tmp}/direct-surface-gate.XXXXXX")"
before_log="$run_dir/hilog.before.txt"
after_log="$run_dir/hilog.after.txt"
log_file="$run_dir/hilog.delta.txt"
hdc -t "$serial" shell hilog -x >"$before_log" 2>&1

"$workload" --serial "$serial" --stage prepare
prepared=1
for stage in first-frame continuous-frame resize-rotation surface-loss recover; do
    "$workload" --serial "$serial" --stage "$stage"
done
sleep 2
hdc -t "$serial" shell hilog -x >"$after_log" 2>&1

# Isolate only newly appended records without clearing the device log buffer.
# If the ring wrapped or the prefix changed, fail closed rather than accepting
# stale markers from a prior generation.
before_count="$(wc -l <"$before_log" | tr -d ' ')"
if [[ "$before_count" -eq 0 ]]; then
    cp "$after_log" "$log_file"
elif head -n "$before_count" "$after_log" | cmp -s - "$before_log"; then
    tail -n "+$((before_count + 1))" "$after_log" >"$log_file"
else
    echo "INCOMPLETE: hilog ring changed during run; cannot isolate current-generation records" >&2
    exit 1
fi

direct_lines="$run_dir/direct.log"
rs_lines="$run_dir/render-service.log"
grep "DIRECT_PATH_MEASURE route=direct" "$log_file" >"$direct_lines" || true
grep -E "RenderService|NotifyUIBufferAvailable|AcquireBuffer|BufferAvailable" \
    "$log_file" >"$rs_lines" || true

queue_count="$(grep -c "event=queue_accepted" "$direct_lines" || true)"
bound_count="$(grep -c "event=bound" "$direct_lines" || true)"
resize_count="$(grep -c "event=geometry_committed" "$direct_lines" || true)"
loss_count="$(grep -c "event=surface_lost" "$direct_lines" || true)"
rs_count="$(wc -l <"$rs_lines" | tr -d ' ')"
recovery_observed="$(awk '
    /event=surface_lost/ { lost=1; next }
    lost && /event=bound/ { rebound=1; next }
    rebound && /event=queue_accepted/ { recovered=1 }
    END { print recovered ? 1 : 0 }
' "$direct_lines")"

printf '%s\n' \
    "route,bound,queued,resize,loss,recovery,render_service_activity,presentation_verdict" \
    "direct,$bound_count,$queue_count,$resize_count,$loss_count,$recovery_observed,$rs_count,NOT_SIGNED" \
    "broker,NOT_RUN,NOT_RUN,NOT_RUN,NOT_RUN,NOT_RUN,NOT_RUN,NOT_RUN"

if [[ "$bound_count" -lt 2 || "$queue_count" -lt 2 ||
      "$resize_count" -lt 1 || "$loss_count" -lt 1 ||
      "$recovery_observed" -ne 1 || "$rs_count" -lt 1 ]]; then
    echo "INCOMPLETE: required direct-path observations are missing; no verdict signed" >&2
    exit 1
fi

echo "OBSERVED: first/continuous queue, resize, loss/recovery, and RenderService activity; no presentation or action verdict signed"
