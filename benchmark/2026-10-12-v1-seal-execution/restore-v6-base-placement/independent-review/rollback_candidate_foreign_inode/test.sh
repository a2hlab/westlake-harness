set -eu

sha256sum() { shasum -a 256 "$@"; }
stat() { python3 -c 'import os,sys; s=os.stat(sys.argv[2]); print((str(s.st_dev)+":"+str(s.st_ino)) if sys.argv[1]=="%d:%i" else (oct(s.st_mode & 4095)[2:]+":0:0"))' "$2" "$3"; }
ls() { printf '%s\n' 'u:object_r:system_etc_file:s0 u:object_r:data_file:s0'; }
chown() { :; }
chcon() { :; }
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
 restore_old /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-4 "$ROOT/preimage-4" 9abbc98663f5cb860317e75fa2f91af47c1d1824e3bca368018db08b0cfa082c 550 u:object_r:system_etc_file:s0 "$removed_4" || rollback_rc=1
 restore_old /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-3 "$ROOT/preimage-3" e7e5d1fe41f52fa49bca000b82c14cd078f1dc06d268cc71af6a094c38c967d2 550 u:object_r:system_etc_file:s0 "$removed_3" || rollback_rc=1
 if [ -e /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-2 ] || [ -L /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-2 ]; then
  if match_file /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-2 6b7a9d291452573f85e78fc8b12b658c9193a2e7851897aff6640ac8f2f22451 644 u:object_r:data_file:s0 && [ "$(stat -c %d:%i /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-2)" = "$tmp_inode_2" ]; then rm /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-2 || rollback_rc=1
  else echo ROLLBACK_FOREIGN:/var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-2 >&2; rollback_rc=1; fi
 fi
 clean_owned_temp /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-2.v1-migration-tmp "$tmp_inode_2" || rollback_rc=1
 if [ -e /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-1 ] || [ -L /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-1 ]; then
  if match_file /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-1 43491d3aae7dbded7fec2aee38a448087270261a795402c6955db6e7d5de0fae 550 u:object_r:system_etc_file:s0 && [ "$(stat -c %d:%i /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-1)" = "$tmp_inode_1" ]; then rm /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-1 || rollback_rc=1
  else echo ROLLBACK_FOREIGN:/var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-1 >&2; rollback_rc=1; fi
 fi
 clean_owned_temp /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-1.v1-migration-tmp "$tmp_inode_1" || rollback_rc=1
 if [ -e /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-0 ] || [ -L /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-0 ]; then
  if match_file /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-0 7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1 550 u:object_r:system_etc_file:s0 && [ "$(stat -c %d:%i /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-0)" = "$tmp_inode_0" ]; then rm /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-0 || rollback_rc=1
  else echo ROLLBACK_FOREIGN:/var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-0 >&2; rollback_rc=1; fi
 fi
 clean_owned_temp /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-0.v1-migration-tmp "$tmp_inode_0" || rollback_rc=1
 return "$rollback_rc"
}
ROOT=/var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/stage
removed_3=0; removed_4=0
tmp_inode_0=$(stat -c %d:%i /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-0)
tmp_inode_1=$(stat -c %d:%i /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-1)
tmp_inode_2=$(stat -c %d:%i /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-2)
cp /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-0 /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-0.replacement; mv /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-0.replacement /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-0
if rollback; then exit 9; fi
test -e /var/folders/4b/52jp6mr96b75p8tr62l0bz2r0000gn/T/base5-delta-review-0cytaiyr/rollback_candidate_foreign_inode/sandbox/target-0
