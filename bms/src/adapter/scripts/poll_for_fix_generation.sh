#!/bin/zsh
set -eu

ADAPTER=/opt/Bridge/src/adapter
BASELINE_GENERATION=$ADAPTER/out/helloworld-r18-v7-ams-parent-bound-subwindow-art64-20260725T0050HKT
BASELINE_APPSPAWN_HASH=$(/usr/bin/shasum -a 256 "$BASELINE_GENERATION/bin/appspawn-x" | /usr/bin/awk '{print $1}')
POLL_LOG=$ADAPTER/out/poll_for_fix_generation.log

print "Baseline appspawn-x hash: $BASELINE_APPSPAWN_HASH" | tee -a "$POLL_LOG"

for attempt in {1..120}; do
    # Look for any helloworld-* generation directory newer than the baseline
    # that contains the full runtime closure (exclude evidence-only dirs).
    newest=$(/usr/bin/find "$ADAPTER/out" -maxdepth 1 -type d -name 'helloworld-*' -newer "$BASELINE_GENERATION" 2>/dev/null | while read -r d; do
        if [[ -f "$d/bin/appspawn-x" && -f "$d/systemandroid/lib64/libart.so" && -f "$d/generation.json" ]]; then
            print "$d"
        fi
    done | /usr/bin/sort | /usr/bin/tail -1 || true)
    if [[ -n "$newest" ]]; then
        print "$(date): NEW GENERATION DETECTED: $newest" | tee -a "$POLL_LOG"
        print "$newest"
        exit 0
    fi

    # Also detect if the baseline generation's appspawn-x binary changed (in-place refresh).
    current_hash=$(/usr/bin/shasum -a 256 "$BASELINE_GENERATION/bin/appspawn-x" 2>/dev/null | /usr/bin/awk '{print $1}' || true)
    if [[ "$current_hash" != "$BASELINE_APPSPAWN_HASH" && -n "$current_hash" ]]; then
        print "$(date): BASELINE GENERATION appspawn-x REFRESHED: $current_hash" | tee -a "$POLL_LOG"
        print "$BASELINE_GENERATION"
        exit 0
    fi

    print "$(date): poll $attempt - no new generation yet" | tee -a "$POLL_LOG"
    sleep 30
done

print "$(date): TIMEOUT - no new generation detected within 60 minutes" | tee -a "$POLL_LOG"
exit 1
