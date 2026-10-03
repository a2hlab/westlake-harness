set -e
for round in 1 2 3 4 5 6 7 8; do
 test_children="$(ps -A -o PID,PPID,UID,NAME | awk -v app_uid=20011260 -v parent=30200 'NR>1 && $4=="appspawn-x" && $3!=0 {if ($3!=app_uid || $2!=parent) bad=1; else print $1} END {if(bad) exit 91}')"
 for test_pid in $test_children; do
  test -r /proc/$test_pid/status || continue
  test "$(sed -n 's/^Uid:[[:space:]]*\([0-9]*\).*/\1/p' /proc/$test_pid/status)" = 20011260 || exit 92
  test "$(sed -n 's/^PPid:[[:space:]]*\([0-9]*\).*/\1/p' /proc/$test_pid/status)" = 30200 || exit 93
  echo "OWNED_CHILD $test_pid UID=20011260 PPID=30200"
  kill -9 $test_pid 2>/dev/null || true
 done
 remaining="$(ps -A -o PID,PPID,UID,NAME | awk 'NR>1 && $4=="appspawn-x" && $3!=0 {n++} END{print n+0}')"
 if test "$remaining" = 0; then
  begetctl stop_service appspawn-x
  sleep 1
  ps -A -o PID,PPID,UID,NAME
  exit 0
 fi
 sleep 0.1
done
exit 94
