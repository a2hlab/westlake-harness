#!/system/bin/sh
set -eu
ROOT=/data/westlake-demo/u13/base-migration-43bc-v3-20261012
BOOT=43bc3915-04bd-42ca-895e-26e8292911fa
test "$(cat /proc/sys/kernel/random/boot_id)" = "$BOOT"
test ! -e /data/westlake-demo/u13/sources-boat
test ! -L /data/westlake-demo/u13/sources-boat
test ! -e /data/westlake-demo/u13/DISABLED
test ! -L /data/westlake-demo/u13/DISABLED
test -d "$ROOT"; test ! -L "$ROOT"
test ! -L /system/etc/init/00_westlake_u13_recover-v3.cfg
test ! -e /system/etc/init/00_westlake_u13_recover-v3.cfg
test ! -L /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-0
test -f /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-0
test "$(sha256sum /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-0 | cut -d' ' -f1)" = 7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
test "$(stat -c %a:%u:%g /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-0)" = 550:0:0
ls -ldnZ /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-0 | grep -F u:object_r:system_etc_file:s0 >/dev/null
test ! -e /system/etc/init/00_westlake_u13_recover-v3.cfg.v1-migration-tmp; test ! -L /system/etc/init/00_westlake_u13_recover-v3.cfg.v1-migration-tmp
test ! -L /system/etc/westlake-u13-recover-v3.sh
test ! -e /system/etc/westlake-u13-recover-v3.sh
test ! -L /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-1
test -f /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-1
test "$(sha256sum /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-1 | cut -d' ' -f1)" = 43491d3aae7dbded7fec2aee38a448087270261a795402c6955db6e7d5de0fae
test "$(stat -c %a:%u:%g /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-1)" = 550:0:0
ls -ldnZ /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-1 | grep -F u:object_r:system_etc_file:s0 >/dev/null
test ! -e /system/etc/westlake-u13-recover-v3.sh.v1-migration-tmp; test ! -L /system/etc/westlake-u13-recover-v3.sh.v1-migration-tmp
test ! -L /data/westlake-demo/u13/selinux-mode
test ! -e /data/westlake-demo/u13/selinux-mode
test ! -L /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-2
test -f /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-2
test "$(sha256sum /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-2 | cut -d' ' -f1)" = 6b7a9d291452573f85e78fc8b12b658c9193a2e7851897aff6640ac8f2f22451
test "$(stat -c %a:%u:%g /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-2)" = 644:0:0
ls -ldnZ /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-2 | grep -F u:object_r:data_file:s0 >/dev/null
test ! -e /data/westlake-demo/u13/selinux-mode.v1-migration-tmp; test ! -L /data/westlake-demo/u13/selinux-mode.v1-migration-tmp
test ! -L /system/etc/init/00_westlake_u13_recover.cfg
test -f /system/etc/init/00_westlake_u13_recover.cfg
test "$(sha256sum /system/etc/init/00_westlake_u13_recover.cfg | cut -d' ' -f1)" = e7e5d1fe41f52fa49bca000b82c14cd078f1dc06d268cc71af6a094c38c967d2
test "$(stat -c %a:%u:%g /system/etc/init/00_westlake_u13_recover.cfg)" = 550:0:0
ls -ldnZ /system/etc/init/00_westlake_u13_recover.cfg | grep -F u:object_r:system_etc_file:s0 >/dev/null
test ! -L /data/westlake-demo/u13/base-migration-43bc-v3-20261012/preimage-3
test -f /data/westlake-demo/u13/base-migration-43bc-v3-20261012/preimage-3
test "$(sha256sum /data/westlake-demo/u13/base-migration-43bc-v3-20261012/preimage-3 | cut -d' ' -f1)" = e7e5d1fe41f52fa49bca000b82c14cd078f1dc06d268cc71af6a094c38c967d2
test "$(stat -c %a:%u:%g /data/westlake-demo/u13/base-migration-43bc-v3-20261012/preimage-3)" = 550:0:0
ls -ldnZ /data/westlake-demo/u13/base-migration-43bc-v3-20261012/preimage-3 | grep -F u:object_r:system_etc_file:s0 >/dev/null
test ! -e /system/etc/init/00_westlake_u13_recover.cfg.v1-migration-tmp; test ! -L /system/etc/init/00_westlake_u13_recover.cfg.v1-migration-tmp
test ! -L /system/etc/westlake-u13-boat-overlay.sh
test -f /system/etc/westlake-u13-boat-overlay.sh
test "$(sha256sum /system/etc/westlake-u13-boat-overlay.sh | cut -d' ' -f1)" = 9abbc98663f5cb860317e75fa2f91af47c1d1824e3bca368018db08b0cfa082c
test "$(stat -c %a:%u:%g /system/etc/westlake-u13-boat-overlay.sh)" = 550:0:0
ls -ldnZ /system/etc/westlake-u13-boat-overlay.sh | grep -F u:object_r:system_etc_file:s0 >/dev/null
test ! -L /data/westlake-demo/u13/base-migration-43bc-v3-20261012/preimage-4
test -f /data/westlake-demo/u13/base-migration-43bc-v3-20261012/preimage-4
test "$(sha256sum /data/westlake-demo/u13/base-migration-43bc-v3-20261012/preimage-4 | cut -d' ' -f1)" = 9abbc98663f5cb860317e75fa2f91af47c1d1824e3bca368018db08b0cfa082c
test "$(stat -c %a:%u:%g /data/westlake-demo/u13/base-migration-43bc-v3-20261012/preimage-4)" = 550:0:0
ls -ldnZ /data/westlake-demo/u13/base-migration-43bc-v3-20261012/preimage-4 | grep -F u:object_r:system_etc_file:s0 >/dev/null
test ! -e /system/etc/westlake-u13-boat-overlay.sh.v1-migration-tmp; test ! -L /system/etc/westlake-u13-boat-overlay.sh.v1-migration-tmp
reseal=0
changed=0
removed_3=0
removed_4=0
tmp_inode_0=
tmp_inode_1=
tmp_inode_2=
root_options() {
 while read -r device point type options rest; do
  if [ "$point" = / ]; then printf '%s\n' "$options"; return 0; fi
 done < /proc/mounts
 return 1
}
match_file() {
 p=$1; sha=$2; mode=$3; label=$4
 [ ! -L "$p" ] && [ -f "$p" ] &&
 [ "$(sha256sum "$p" | cut -d' ' -f1)" = "$sha" ] &&
 [ "$(stat -c %a:%u:%g "$p")" = "$mode:0:0" ] &&
 ls -ldnZ "$p" | grep -F "$label" >/dev/null
}
clean_owned_temp() {
 p=$1; inode=$2
 if [ ! -e "$p" ] && [ ! -L "$p" ]; then return 0; fi
 if [ -n "$inode" ] && [ ! -L "$p" ] && [ -f "$p" ] && [ "$(stat -c %d:%i "$p")" = "$inode" ]; then
  rm "$p"
 else echo "ROLLBACK_TEMP_PRESERVED:$p" >&2; return 1; fi
}
restore_old() {
 t=$1; src=$2; sha=$3; mode=$4; label=$5; removed=$6
 if match_file "$t" "$sha" "$mode" "$label"; then return 0; fi
 if [ -e "$t" ] || [ -L "$t" ] || [ "$removed" != 1 ]; then
  echo "ROLLBACK_FOREIGN_OR_UNOWNED:$t" >&2; return 1
 fi
 tmp="$t.v1-migration-tmp"
 (set -C; : > "$tmp") || return 1
 inode=$(stat -c %d:%i "$tmp") || return 1
 if cp "$src" "$tmp" && chown 0:0 "$tmp" && chmod "$mode" "$tmp" && chcon "$label" "$tmp" && cmp "$src" "$tmp" &&
    [ ! -e "$t" ] && [ ! -L "$t" ] && mv "$tmp" "$t"; then
  match_file "$t" "$sha" "$mode" "$label"
 else clean_owned_temp "$tmp" "$inode"; echo "ROLLBACK_RESTORE_FAILED:$t" >&2; return 1; fi
}
rollback() {
 rollback_rc=0
 restore_old /system/etc/westlake-u13-boat-overlay.sh "$ROOT/preimage-4" 9abbc98663f5cb860317e75fa2f91af47c1d1824e3bca368018db08b0cfa082c 550 u:object_r:system_etc_file:s0 "$removed_4" || rollback_rc=1
 restore_old /system/etc/init/00_westlake_u13_recover.cfg "$ROOT/preimage-3" e7e5d1fe41f52fa49bca000b82c14cd078f1dc06d268cc71af6a094c38c967d2 550 u:object_r:system_etc_file:s0 "$removed_3" || rollback_rc=1
 if [ -e /data/westlake-demo/u13/selinux-mode ] || [ -L /data/westlake-demo/u13/selinux-mode ]; then
  if match_file /data/westlake-demo/u13/selinux-mode 6b7a9d291452573f85e78fc8b12b658c9193a2e7851897aff6640ac8f2f22451 644 u:object_r:data_file:s0 && [ "$(stat -c %d:%i /data/westlake-demo/u13/selinux-mode)" = "$tmp_inode_2" ]; then rm /data/westlake-demo/u13/selinux-mode || rollback_rc=1
  else echo ROLLBACK_FOREIGN:/data/westlake-demo/u13/selinux-mode >&2; rollback_rc=1; fi
 fi
 clean_owned_temp /data/westlake-demo/u13/selinux-mode.v1-migration-tmp "$tmp_inode_2" || rollback_rc=1
 if [ -e /system/etc/westlake-u13-recover-v3.sh ] || [ -L /system/etc/westlake-u13-recover-v3.sh ]; then
  if match_file /system/etc/westlake-u13-recover-v3.sh 43491d3aae7dbded7fec2aee38a448087270261a795402c6955db6e7d5de0fae 550 u:object_r:system_etc_file:s0 && [ "$(stat -c %d:%i /system/etc/westlake-u13-recover-v3.sh)" = "$tmp_inode_1" ]; then rm /system/etc/westlake-u13-recover-v3.sh || rollback_rc=1
  else echo ROLLBACK_FOREIGN:/system/etc/westlake-u13-recover-v3.sh >&2; rollback_rc=1; fi
 fi
 clean_owned_temp /system/etc/westlake-u13-recover-v3.sh.v1-migration-tmp "$tmp_inode_1" || rollback_rc=1
 if [ -e /system/etc/init/00_westlake_u13_recover-v3.cfg ] || [ -L /system/etc/init/00_westlake_u13_recover-v3.cfg ]; then
  if match_file /system/etc/init/00_westlake_u13_recover-v3.cfg 7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1 550 u:object_r:system_etc_file:s0 && [ "$(stat -c %d:%i /system/etc/init/00_westlake_u13_recover-v3.cfg)" = "$tmp_inode_0" ]; then rm /system/etc/init/00_westlake_u13_recover-v3.cfg || rollback_rc=1
  else echo ROLLBACK_FOREIGN:/system/etc/init/00_westlake_u13_recover-v3.cfg >&2; rollback_rc=1; fi
 fi
 clean_owned_temp /system/etc/init/00_westlake_u13_recover-v3.cfg.v1-migration-tmp "$tmp_inode_0" || rollback_rc=1
 return "$rollback_rc"
}
finish() {
 final_rc=$?
 trap - EXIT
 if [ "$final_rc" != 0 ] && [ "$changed" = 1 ]; then rollback || final_rc=97; fi
 if [ "$reseal" = 1 ]; then
  mount -o ro,remount / || final_rc=98
  final_options=$(root_options) || final_rc=98
  case ,${final_options:-}, in *,ro,*) ;; *) final_rc=98;; esac
 fi
 if [ "$final_rc" = 0 ]; then echo BASE_CONTROLS_PLACED_RESEALED_NO_REBOOT; fi
 exit "$final_rc"
}
trap finish EXIT
opts=$(root_options)
case ,$opts, in *,ro,*) reseal=1; mount -o rw,remount /;; *,rw,*) ;; *) exit 90;; esac
changed=1
(set -C; : > /system/etc/init/00_westlake_u13_recover-v3.cfg.v1-migration-tmp)
tmp_inode_0=$(stat -c %d:%i /system/etc/init/00_westlake_u13_recover-v3.cfg.v1-migration-tmp)
cp /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-0 /system/etc/init/00_westlake_u13_recover-v3.cfg.v1-migration-tmp
chown 0:0 /system/etc/init/00_westlake_u13_recover-v3.cfg.v1-migration-tmp
chmod 550 /system/etc/init/00_westlake_u13_recover-v3.cfg.v1-migration-tmp
chcon u:object_r:system_etc_file:s0 /system/etc/init/00_westlake_u13_recover-v3.cfg.v1-migration-tmp
cmp /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-0 /system/etc/init/00_westlake_u13_recover-v3.cfg.v1-migration-tmp
mv /system/etc/init/00_westlake_u13_recover-v3.cfg.v1-migration-tmp /system/etc/init/00_westlake_u13_recover-v3.cfg
(set -C; : > /system/etc/westlake-u13-recover-v3.sh.v1-migration-tmp)
tmp_inode_1=$(stat -c %d:%i /system/etc/westlake-u13-recover-v3.sh.v1-migration-tmp)
cp /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-1 /system/etc/westlake-u13-recover-v3.sh.v1-migration-tmp
chown 0:0 /system/etc/westlake-u13-recover-v3.sh.v1-migration-tmp
chmod 550 /system/etc/westlake-u13-recover-v3.sh.v1-migration-tmp
chcon u:object_r:system_etc_file:s0 /system/etc/westlake-u13-recover-v3.sh.v1-migration-tmp
cmp /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-1 /system/etc/westlake-u13-recover-v3.sh.v1-migration-tmp
mv /system/etc/westlake-u13-recover-v3.sh.v1-migration-tmp /system/etc/westlake-u13-recover-v3.sh
(set -C; : > /data/westlake-demo/u13/selinux-mode.v1-migration-tmp)
tmp_inode_2=$(stat -c %d:%i /data/westlake-demo/u13/selinux-mode.v1-migration-tmp)
cp /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-2 /data/westlake-demo/u13/selinux-mode.v1-migration-tmp
chown 0:0 /data/westlake-demo/u13/selinux-mode.v1-migration-tmp
chmod 644 /data/westlake-demo/u13/selinux-mode.v1-migration-tmp
chcon u:object_r:data_file:s0 /data/westlake-demo/u13/selinux-mode.v1-migration-tmp
cmp /data/westlake-demo/u13/base-migration-43bc-v3-20261012/candidate-2 /data/westlake-demo/u13/selinux-mode.v1-migration-tmp
mv /data/westlake-demo/u13/selinux-mode.v1-migration-tmp /data/westlake-demo/u13/selinux-mode
test ! -L /system/etc/init/00_westlake_u13_recover.cfg
test -f /system/etc/init/00_westlake_u13_recover.cfg
test "$(sha256sum /system/etc/init/00_westlake_u13_recover.cfg | cut -d' ' -f1)" = e7e5d1fe41f52fa49bca000b82c14cd078f1dc06d268cc71af6a094c38c967d2
test "$(stat -c %a:%u:%g /system/etc/init/00_westlake_u13_recover.cfg)" = 550:0:0
ls -ldnZ /system/etc/init/00_westlake_u13_recover.cfg | grep -F u:object_r:system_etc_file:s0 >/dev/null
removed_3=1
rm /system/etc/init/00_westlake_u13_recover.cfg
test ! -L /system/etc/westlake-u13-boat-overlay.sh
test -f /system/etc/westlake-u13-boat-overlay.sh
test "$(sha256sum /system/etc/westlake-u13-boat-overlay.sh | cut -d' ' -f1)" = 9abbc98663f5cb860317e75fa2f91af47c1d1824e3bca368018db08b0cfa082c
test "$(stat -c %a:%u:%g /system/etc/westlake-u13-boat-overlay.sh)" = 550:0:0
ls -ldnZ /system/etc/westlake-u13-boat-overlay.sh | grep -F u:object_r:system_etc_file:s0 >/dev/null
removed_4=1
rm /system/etc/westlake-u13-boat-overlay.sh
test ! -L /system/etc/init/00_westlake_u13_recover-v3.cfg
test -f /system/etc/init/00_westlake_u13_recover-v3.cfg
test "$(sha256sum /system/etc/init/00_westlake_u13_recover-v3.cfg | cut -d' ' -f1)" = 7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1
test "$(stat -c %a:%u:%g /system/etc/init/00_westlake_u13_recover-v3.cfg)" = 550:0:0
ls -ldnZ /system/etc/init/00_westlake_u13_recover-v3.cfg | grep -F u:object_r:system_etc_file:s0 >/dev/null
test ! -L /system/etc/westlake-u13-recover-v3.sh
test -f /system/etc/westlake-u13-recover-v3.sh
test "$(sha256sum /system/etc/westlake-u13-recover-v3.sh | cut -d' ' -f1)" = 43491d3aae7dbded7fec2aee38a448087270261a795402c6955db6e7d5de0fae
test "$(stat -c %a:%u:%g /system/etc/westlake-u13-recover-v3.sh)" = 550:0:0
ls -ldnZ /system/etc/westlake-u13-recover-v3.sh | grep -F u:object_r:system_etc_file:s0 >/dev/null
test ! -L /data/westlake-demo/u13/selinux-mode
test -f /data/westlake-demo/u13/selinux-mode
test "$(sha256sum /data/westlake-demo/u13/selinux-mode | cut -d' ' -f1)" = 6b7a9d291452573f85e78fc8b12b658c9193a2e7851897aff6640ac8f2f22451
test "$(stat -c %a:%u:%g /data/westlake-demo/u13/selinux-mode)" = 644:0:0
ls -ldnZ /data/westlake-demo/u13/selinux-mode | grep -F u:object_r:data_file:s0 >/dev/null
test ! -L /system/etc/init/00_westlake_u13_recover.cfg
test ! -e /system/etc/init/00_westlake_u13_recover.cfg
test ! -L /system/etc/westlake-u13-boat-overlay.sh
test ! -e /system/etc/westlake-u13-boat-overlay.sh
test "$(cat /proc/sys/kernel/random/boot_id)" = "$BOOT"
