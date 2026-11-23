#!/bin/bash
# board_watchdog.sh <pgid> <log>  -- stops a round whose board goes into a process storm. Every WATCH_EVERY seconds
# (default 30) it reads the board's thread count (/proc/loadavg: running/total). Past THREAD_LIMIT (default 3500;
# about 1,350 after a boot, 1,800 with the Play hosts up) it writes "thread guard: ..." to <log>, stops the round's
# process group, so nothing retries, and stops the storm on the board. It ends when the round's group is gone.
#
# On 11-22 a spawner that took every message for a spawn request forked a Play services process for each app-id
# query (445 in ten minutes): 6,231 threads, load ~400, SceneBoard restarted, and the board stopped answering a
# few minutes in. Its zygote did not stop on SIGTERM, and a "ps -ef | grep" loop over the board did not finish in
# 90 s. So the stop on the board takes SIGKILL, the zygotes first (no more forks), then the Play hosts by name with
# pkill (one pass over /proc), then the usual kill_children once the board answers again. PROTECT_UIDS' zygotes
# are spared as in kill_children. Started by run_all.sh and round.sh under setsid: outside the group it stops.
. "$(dirname "$0")/config.sh"
G=${1:?pgid}; LOG=${2:?log}; LIMIT=${THREAD_LIMIT:-3500}
while sleep "${WATCH_EVERY:-30}"; do
  pgrep -g "$G" >/dev/null 2>&1 || exit 0
  n=$(board_threads)
  [ -n "$n" ] && [ "$n" -gt "$LIMIT" ] 2>/dev/null || continue
  echo "$(date) thread guard: $n threads on the board (THREAD_LIMIT $LIMIT), a process storm: stopping the round" >> "$LOG"
  kill -TERM -- "-$G" 2>/dev/null
  timeout 150 $WHDC -t $T shell "$(spare_fn) for z in \$(pidof appspawn-x); do spared \$z && continue; kill -9 \$z; done; pkill -9 -f com.google.android.gms; pkill -9 -f com.android.vending; true" </dev/null >/dev/null 2>&1
  sleep 20; kill_children
  echo "$(date) thread guard: board cleaned, $(board_threads) threads" >> "$LOG"
  exit 4
done
