#!/bin/bash
# Re-run fetch_missing.py until every project of the given locks is READY (max 5 rounds).
# Only a project directory that this fetcher left WITHOUT its completion record is removed.
set -u
manifest=$1; ws=$2; shift 2
tools=$(dirname "$0")
for round in 1 2 3 4 5; do
  left=$(python3 "$tools/audit_fetch.py" "$manifest" "$ws" "$@" | awk '$1=="PARTIAL"{print $2}')
  for p in $left; do
    [ -e "$ws/$p/.git/a2hlab-source.json" ] || rm -rf -- "${ws:?}/$p"
  done
  (cd "$manifest" && python3 "$tools/fetch_missing.py" "$manifest" "$ws" "$@") > "$HOME/a2hlab/logs/fetch-retry-$round.log" 2>&1
  tail -1 "$HOME/a2hlab/logs/fetch-retry-$round.log"
  python3 "$tools/audit_fetch.py" "$manifest" "$ws" "$@" | grep -q -E "PARTIAL|todo" || { echo ALL_READY; exit 0; }
done
exit 1
