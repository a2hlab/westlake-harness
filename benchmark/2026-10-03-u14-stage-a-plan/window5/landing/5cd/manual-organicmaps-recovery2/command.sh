(
set -e
aa force-stop app.organicmaps
for round in 1 2 3 4 5 6 7 8; do
 ps -A -o PID,PPID,UID,NAME | while read test_pid test_ppid test_uid test_name; do
  test "$test_name" = appspawn-x || continue
  test "$test_uid" != 0 || continue
  test "$test_uid" = 20011260 || exit 91
  test "$test_ppid" = 30200 || exit 92
  test -r /proc/$test_pid/status || continue
  test "$(sed -n 's/^Uid:[[:space:]]*\([0-9]*\).*/\1/p' /proc/$test_pid/status)" = 20011260 || exit 93
  test "$(sed -n 's/^PPid:[[:space:]]*\([0-9]*\).*/\1/p' /proc/$test_pid/status)" = 30200 || exit 94
  echo "OWNED_CHILD $test_pid UID=20011260 PPID=30200"
  kill -9 $test_pid 2>/dev/null || true
 done
 remaining="$(ps -A -o PID,PPID,UID,NAME | while read test_pid test_ppid test_uid test_name; do test "$test_name" != appspawn-x || test "$test_uid" = 0 || echo "$test_pid"; done)"
 if test -z "$remaining"; then
  begetctl stop_service appspawn-x
  sleep 1
  ps -A -o PID,PPID,UID,NAME
  exit 0
 fi
 sleep 0.1
done
exit 95
)
