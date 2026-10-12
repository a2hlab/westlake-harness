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
