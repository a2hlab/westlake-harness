#!/system/bin/sh
# Successor candidate of prepare_jit50.sh; NOT installed or source-pin admitted.
# Run as root in the verified existing RouteB parent's mount namespace.
set -eu
app_uid=20011300
base=/data/data/com.ss.android.article.news
code=$base/code_cache
cache=$code/art-volatile
fail() { printf '[JIT51-REFUSE] %s\n' "$*" >&2; exit 2; }
for p in /data /data/data; do [ -d "$p" ] && [ ! -L "$p" ] || fail ancestor; done
[ "$(stat -c '%u:%g' /data/data)" = "$app_uid:$app_uid" ] || fail data_owner
# Validate all existing explicit directories BEFORE changing any owner.
for p in "$base" "$code" "$cache"; do
 [ ! -L "$p" ] || fail symlink
 if [ -e "$p" ]; then
  [ -d "$p" ] || fail not_directory
  owner=$(stat -c '%u:%g' "$p") || fail stat
  case "$owner" in 0:0|"$app_uid:$app_uid") :;; *) fail foreign_owner;; esac
  [ "$(stat -c %C "$p")" = u:object_r:appdat:s0 ] || fail label
 fi
done
for p in "$base" "$code" "$cache"; do
 if [ ! -e "$p" ]; then mkdir -m 0755 "$p" || fail mkdir; fi
 [ -d "$p" ] && [ ! -L "$p" ] || fail directory_changed
 before=$(stat -c '%d:%i|%u:%g|%a|%C' "$p") || fail stat
 old_owner=$(stat -c '%u:%g' "$p") || fail owner
 case "$old_owner" in 0:0|"$app_uid:$app_uid") :;; *) fail foreign_owner;; esac
 [ "$(stat -c %C "$p")" = u:object_r:appdat:s0 ] || fail label
 IFS='|' read -r inode prior_owner prior_mode prior_label extra <<META_FIELDS
$before
META_FIELDS
 [ -n "$inode" ] && [ -z "$extra" ] || fail metadata_fields
 [ "$(stat -c '%d:%i|%u:%g|%a|%C' "$p")" = "$before" ] || fail preimage_CAS
 chown -h "$app_uid:$app_uid" "$p" || fail chown
 [ "$(stat -c '%d:%i' "$p")" = "$inode" ] && [ ! -L "$p" ] || fail inode_changed
 [ "$(stat -c '%d:%i|%u:%g|%a|%C' "$p")" = "$inode|$app_uid:$app_uid|$prior_mode|$prior_label" ] || fail metadata_readback
 printf '[JIT51-OWNER] path=%s before=%s after=%s\n' "$p" "$before" "$(stat -c '%d:%i|%u:%g|%a|%C' "$p")"
done
chmod 0700 "$cache"
[ "$(stat -c '%u:%g:%a' "$cache")" = "$app_uid:$app_uid:700" ] || fail cache_readback
printf '[JIT51-PREPARE] path=%s identity=%s nonsymlink=1\n' "$cache" "$(stat -c '%u:%g:%a' "$cache")"
ls -ldZ "$cache"
