#!/system/bin/sh
set -eu
export LC_ALL=C
ROOT=/data/westlake-demo/u13/boat-v2-20261013-r4
ARCHIVE=/data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a
test "$(cat /proc/sys/kernel/random/boot_id)" = 362f2212-1a42-4c1a-8487-0dddb091c74b
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
/data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.intents
/data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.log
/data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.receipt
/data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
/data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762
/data/westlake-demo/u13/boat-v2-20261013-r4/sources'
test ! -L /data/westlake-demo/u13/boat-v2-20261013-r4; test -d /data/westlake-demo/u13/boat-v2-20261013-r4
test "$(stat -c %a:%u:%g:%C:%d:%i /data/westlake-demo/u13/boat-v2-20261013-r4)" = 755:0:0:u:object_r:data_file:s0:66352:156273
test ! -L /data/westlake-demo/u13/boat-v2-20261013-r4/sources; test -d /data/westlake-demo/u13/boat-v2-20261013-r4/sources
test "$(stat -c %a:%u:%g:%C:%d:%i /data/westlake-demo/u13/boat-v2-20261013-r4/sources)" = 755:0:0:u:object_r:data_file:s0:66352:156291
test ! -L /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762; test -f /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762)" = 644:0:0:u:object_r:data_file:s0
test "$(sha256sum /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762 | cut -d" " -f1)" = 897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762
inode0=$(stat -c %d:%i /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762)
test ! -L /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.log; test -f /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.log
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.log)" = 644:0:0:u:object_r:data_file:s0
test "$(sha256sum /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.log | cut -d" " -f1)" = fdccfae60369a2d9d572b2b52222dae08e6ba6ecc397844ffb6d31fb20ecbb4b
inode1=$(stat -c %d:%i /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.log)
test ! -L /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.intents; test -f /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.intents
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.intents)" = 644:0:0:u:object_r:data_file:s0
test "$(sha256sum /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.intents | cut -d" " -f1)" = d3940793f1d6cab5b97f8aee2757aa54d7f5867c8620ae6a4517db6e8f2c6e9a
inode2=$(stat -c %d:%i /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.intents)
test ! -L /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.receipt; test -f /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.receipt
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.receipt)" = 644:0:0:u:object_r:data_file:s0
test "$(sha256sum /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.receipt | cut -d" " -f1)" = ee336ccd16ccbfb0f873c6a9e128a1c3e985c5c9bf0950e6bcc9bb3641fbc6db
inode3=$(stat -c %d:%i /data/westlake-demo/u13/boat-v2-20261013-r4/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.receipt)
test ! -L /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1; test -f /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1)" = 644:0:0:u:object_r:data_file:s0
test "$(sha256sum /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1 | cut -d" " -f1)" = 7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
inode4=$(stat -c %d:%i /data/westlake-demo/u13/boat-v2-20261013-r4/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1)
# Only mutation: same-parent rename of the fully owned audit tree.
mv "$ROOT" "$ARCHIVE"
test ! -e "$ROOT"; test ! -L "$ROOT"
actual=$(find /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a -print | sort)
test "$actual" = '/data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a
/data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.intents
/data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.log
/data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.receipt
/data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
/data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762
/data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/sources'
test ! -L /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a; test -d /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a
test "$(stat -c %a:%u:%g:%C:%d:%i /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a)" = 755:0:0:u:object_r:data_file:s0:66352:156273
test ! -L /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/sources; test -d /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/sources
test "$(stat -c %a:%u:%g:%C:%d:%i /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/sources)" = 755:0:0:u:object_r:data_file:s0:66352:156291
test ! -L /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762; test -f /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762)" = 644:0:0:u:object_r:data_file:s0
test "$(sha256sum /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762 | cut -d" " -f1)" = 897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762
test "$(stat -c %d:%i /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/cfg-stage-897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762)" = "$inode0"
test ! -L /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.log; test -f /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.log
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.log)" = 644:0:0:u:object_r:data_file:s0
test "$(sha256sum /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.log | cut -d" " -f1)" = fdccfae60369a2d9d572b2b52222dae08e6ba6ecc397844ffb6d31fb20ecbb4b
test "$(stat -c %d:%i /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.log)" = "$inode1"
test ! -L /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.intents; test -f /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.intents
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.intents)" = 644:0:0:u:object_r:data_file:s0
test "$(sha256sum /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.intents | cut -d" " -f1)" = d3940793f1d6cab5b97f8aee2757aa54d7f5867c8620ae6a4517db6e8f2c6e9a
test "$(stat -c %d:%i /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.intents)" = "$inode2"
test ! -L /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.receipt; test -f /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.receipt
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.receipt)" = 644:0:0:u:object_r:data_file:s0
test "$(sha256sum /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.receipt | cut -d" " -f1)" = ee336ccd16ccbfb0f873c6a9e128a1c3e985c5c9bf0950e6bcc9bb3641fbc6db
test "$(stat -c %d:%i /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/boat-0bc46610-55bd-40c7-baf2-b0c0b7c26fe5.receipt)" = "$inode3"
test ! -L /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1; test -f /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
test "$(stat -c %a:%u:%g:%C /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1)" = 644:0:0:u:object_r:data_file:s0
test "$(sha256sum /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1 | cut -d" " -f1)" = 7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
test "$(stat -c %d:%i /data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a/cfg-stage-7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1)" = "$inode4"
printf '%s\n' '{"status":"ARCHIVED_VERIFIED","source":"/data/westlake-demo/u13/boat-v2-20261013-r4","destination":"/data/westlake-demo/u13/boat-audit-r5-return-bc6aaeb061fa4671a8733e5188570d4a","boot_id":"362f2212-1a42-4c1a-8487-0dddb091c74b","original_root_absent":true}'
