#!/usr/bin/env bash
# sweep_batch.sh <keys-file> : sweep each app key (one per line), accumulate results + counts.
# Source your 5ea34a45 runtime-candidate config FIRST (export the env vars sweep_app.sh needs), e.g.:
#   source sweep_config.5ea34a45.sh && ./sweep_batch.sh keys.fdroid.txt
set -uo pipefail
KEYS="${1:?usage: sweep_batch.sh <keys-file>}"
HERE="$(cd "$(dirname "$0")" && pwd)"
: "${OUT_ROOT:?source the runtime config first}"
RES="$OUT_ROOT/results.tsv"; : > "$RES"
n=0; lit=0; blocked=0
while IFS= read -r app; do
  [ -z "$app" ] && continue; case "$app" in \#*) continue;; esac
  n=$((n+1)); echo "[$n] $app"
  bash "$HERE/sweep_app.sh" "$app" 2>&1 | tail -3
  v=$(cut -f2 "$OUT_ROOT/$app/verdict.tsv" 2>/dev/null)
  cat "$OUT_ROOT/$app/verdict.tsv" 2>/dev/null >> "$RES"
  [ "$v" = "LIT" ] && lit=$((lit+1)) || blocked=$((blocked+1))
  echo "  running tally: swept=$n LIT=$lit BLOCKED=$blocked"
done < "$KEYS"
echo "=== BATCH DONE: swept=$n LIT=$lit BLOCKED=$blocked  ($(awk "BEGIN{if($n>0)printf \"%.0f\",100*$lit/$n; else print 0}")% lit) ==="
echo "--- LIT ---";     awk -F'\t' '$2=="LIT"{print "  "$1" ("$3")"}' "$RES"
echo "--- BLOCKED by category ---"; awk -F'\t' '$2=="BLOCKED"{print $3}' "$RES" | sort | uniq -c | sort -rn
