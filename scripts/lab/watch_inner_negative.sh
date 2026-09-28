#!/bin/bash
# Negative-signal watcher (OLP restart checklist item 3): first goal transition to blocked, an escalation, or the
# inner loop vanishing from herdr. Only lines written after arming count.
F=~/.octos/instances/${1:-bb400d9c2928af7a}/profiles/kimi/data/events.jsonl; base=-1
for i in $(seq 1 2880); do
  if [ -f "$F" ]; then
    n=$(wc -l < "$F"); [ "$base" -lt 0 ] && base=$n
    if [ "$n" -gt "$base" ]; then
      hit=$(tail -n $((n - base)) "$F" | grep -F -e goal_transition -e escalat | grep -F -e blocked -e escalat | head -3)
      [ -n "$hit" ] && { echo "NEGATIVE-SIGNAL $hit"; exit 0; }; base=$n
    fi
  fi
  herdr agent list 2>/dev/null | grep -q '"agent":"octoscode"' || { echo "NEGATIVE-SIGNAL inner loop gone from herdr"; exit 0; }
  sleep 30
done
