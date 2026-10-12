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
ls() { echo label; }
printf OLD > old; cp old target; chmod 550 old target
sha=$(sha256sum old | cut -d' ' -f1)
chmod 750 target; printf FOREIGN > target; chmod 550 target; if restore_old target old "$sha" 550 label 1; then exit 9; fi; test "$(cat target)" = FOREIGN
