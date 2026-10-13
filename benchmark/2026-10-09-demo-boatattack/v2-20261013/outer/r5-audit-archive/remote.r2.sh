#!/system/bin/sh
set -eu
export LC_ALL=C
ROOT=/data/westlake-demo/u13/boat-v2-20261013-r4
ARCHIVE=/data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55
test "$(cat /proc/sys/kernel/random/boot_id)" = 8d0f7543-2352-4d9b-a7ce-e3b5d0ba12a5
test ! -e "$ARCHIVE"; test ! -L "$ARCHIVE"
walk="$ROOT"; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done
test "$(stat -c %d "$ROOT")" = "$(stat -c %d "$(dirname "$ROOT")")"
test "$(sha256sum /system/etc/init/00_westlake_u13_recover-v3.cfg | cut -d" " -f1)" = 7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
set -f
processes=$(ps -A -o PID,PPID,UID,NAME)
printf '%s\n' "$processes" | {
 first=1
 while read -r apid appid auid aname; do
  if [ "$first" = 1 ]; then test "$apid:$appid:$auid" = PID:PPID:UID; first=0; continue; fi
  for number in "$apid" "$appid" "$auid"; do case "$number" in ''|*[!0-9]*) exit 1;; esac; done
  test "$auid" != 20011301
 done
 test "$first" = 0
}
for table in /proc/self/mountinfo /proc/1/mountinfo; do
 while IFS= read -r mountrow; do
  set -- $mountrow
  test "$#" -gt 6
  case "$5" in "$ROOT"|"$ROOT"/*) exit 1;; esac
 done < "$table"
done
actual=$(find /data/westlake-demo/u13/boat-v2-20261013-r4 -print | sort)
test "$actual" = '/data/westlake-demo/u13/boat-v2-20261013-r4
/data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
/data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762
/data/westlake-demo/u13/boat-v2-20261013-r4/sources'
test ! -L /data/westlake-demo/u13/boat-v2-20261013-r4; test -d /data/westlake-demo/u13/boat-v2-20261013-r4
test "$(stat -c %a:%u:%g:%C:%d:%i /data/westlake-demo/u13/boat-v2-20261013-r4)" = 755:0:0:u:object_r:data_file:s0:66352:155995
test ! -L /data/westlake-demo/u13/boat-v2-20261013-r4/sources; test -d /data/westlake-demo/u13/boat-v2-20261013-r4/sources
test "$(stat -c %a:%u:%g:%C:%d:%i /data/westlake-demo/u13/boat-v2-20261013-r4/sources)" = 755:0:0:u:object_r:data_file:s0:66352:155991
test ! -L /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762; test -f /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762)" = 644:0:0:u:object_r:data_file:s0
test "$(sha256sum /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762 | cut -d" " -f1)" = 897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762
inode0=$(stat -c %d:%i /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762)
test ! -L /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1; test -f /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1)" = 644:0:0:u:object_r:data_file:s0
test "$(sha256sum /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1 | cut -d" " -f1)" = 7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
inode1=$(stat -c %d:%i /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1)
# Only mutation: same-parent rename of the fully owned audit tree.
mv "$ROOT" "$ARCHIVE"
test ! -e "$ROOT"; test ! -L "$ROOT"
actual=$(find /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55 -print | sort)
test "$actual" = '/data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55
/data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
/data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762
/data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/sources'
test ! -L /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55; test -d /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55
test "$(stat -c %a:%u:%g:%C:%d:%i /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55)" = 755:0:0:u:object_r:data_file:s0:66352:155995
test ! -L /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/sources; test -d /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/sources
test "$(stat -c %a:%u:%g:%C:%d:%i /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/sources)" = 755:0:0:u:object_r:data_file:s0:66352:155991
test ! -L /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762; test -f /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762)" = 644:0:0:u:object_r:data_file:s0
test "$(sha256sum /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762 | cut -d" " -f1)" = 897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762
test "$(stat -c %d:%i /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762)" = "$inode0"
test ! -L /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1; test -f /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1)" = 644:0:0:u:object_r:data_file:s0
test "$(sha256sum /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1 | cut -d" " -f1)" = 7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
test "$(stat -c %d:%i /data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1)" = "$inode1"
printf '%s\n' '{"status":"ARCHIVED_VERIFIED","source":"/data/westlake-demo/u13/boat-v2-20261013-r4","destination":"/data/westlake-demo/u13/boat-audit-r3-4e4dd9a141864b6c8e0b9ec829a3fd55","boot_id":"8d0f7543-2352-4d9b-a7ce-e3b5d0ba12a5","original_root_absent":true}'
