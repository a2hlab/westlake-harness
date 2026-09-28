#!/bin/bash
# Pane-state watcher for inner loops without an events.jsonl (e.g. the codex pane): fires once when the pane's
# herdr agent_status leaves "working" after arming, or when the pane disappears. Usage: watch_pane_idle.sh <pane_id>
P=${1:?pane id, e.g. w7:p3}
status() { herdr agent list 2>/dev/null | python3 -c "import json,sys
for a in json.load(sys.stdin)['result']['agents']:
    if a['pane_id']=='$P': print(a['agent_status']); break
else: print('GONE')"; }
seen_working=0
for i in $(seq 1 2880); do
  s=$(status)
  [ "$s" = GONE ] && { echo "PANE-SIGNAL $P gone from herdr"; exit 0; }
  [ "$s" = working ] && seen_working=1
  [ "$seen_working" = 1 ] && [ "$s" != working ] && { echo "PANE-SIGNAL $P $s"; exit 0; }
  sleep 30
done
echo "PANE-TIMEOUT $P still ${s}"
