#!/system/bin/sh
# reconcile_uid.sh (#91 cc-wiki, 2026-10-10) — make the Route B boot slot uid-dynamic.
#
# WHY: OpenHarmony assigns the imehost host app a uid at install time and does NOT preserve it
# across uninstall+reinstall (nor reclaim the original). The Route B donor bundle was built for
# uid 20010053 and pins that uid in THREE kinds of place:
#   1. text: *.sh scripts (run.sh ASX_RUNTIME_OWNER_UID, start-parent.sh source_app_namespace arg,
#      watchdog.sh, preseed_metasec48.sh, prepare_jit50.sh);
#   2. binary: request.bin embeds the uid as TWO little-endian uint32 fields (uid+gid) — ASCII grep
#      cannot see it (proven #91: child kept spawning uid=20010053 -> cross-uid -> alive-but-black);
#   3. ownership: the RT tree.
# This reconciles all three to imehost's ACTUAL installed uid, read from the filesystem. Idempotent:
# re-running with the same uid is a no-op (sed finds nothing; dd rewrites identical bytes).
#
# Board rootfs has NO python/awk/tr/xxd. Uses only: stat, find, grep, sed, dd, printf, od.
set -u
BASE=${TT_BASE:-/data/app/el2/100/base/org.westlake.imehost}
RT=${TT_RT:-$BASE/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d}
F=${TT_F:-/data/local/tmp/operator45/selfheal48}
STAGE=${TT_STAGE:-/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d}
ROOT=${TT_ROOT:-/data/westlake-demo/toutiao}
OLD_UID=${TT_OLD_UID:-20010053}          # uid baked into the Route B donor bundle
REQ_OFFSETS=${TT_REQ_OFFSETS:-312 316}   # LE uint32 uid+gid byte offsets in the pinned request.bin
REQUEST=${TT_REQUEST:-$STAGE/request.bin}

log(){ echo "[TT-UID] $*"; }
fail(){ echo "[TT-UID] FAIL $*" >&2; exit 1; }

# write a little-endian uint32 ($3) at byte offset ($2) of file ($1), in place.
# octal \NNN escapes keep it portable to toybox printf (no \xHH ambiguity next to %x).
write_le_u32(){
  _f=$1; _o=$2; _v=$3
  _b0=$(( _v & 255 )); _b1=$(( (_v / 256) & 255 )); _b2=$(( (_v / 65536) & 255 )); _b3=$(( (_v / 16777216) & 255 ))
  printf "\\$(printf '%03o' "$_b0")\\$(printf '%03o' "$_b1")\\$(printf '%03o' "$_b2")\\$(printf '%03o' "$_b3")" \
    | dd of="$_f" bs=1 seek="$_o" count=4 conv=notrunc 2>/dev/null
}
# read the little-endian uint32 at byte offset ($2) of file ($1) as a decimal (for verify).
read_le_u32(){
  _f=$1; _o=$2
  set -- $(dd if="$_f" bs=1 skip="$_o" count=4 conv=notrunc 2>/dev/null | od -An -tu1)
  [ $# -eq 4 ] || return 1
  echo $(( $1 + $2 * 256 + $3 * 65536 + $4 * 16777216 ))
}

U=$(stat -c %u "$BASE" 2>/dev/null); case "$U" in ''|*[!0-9]*) fail NO_HOST_UID;; esac
log "host uid=$U (donor bundle uid=$OLD_UID)"

# 1) text scripts. Portable in-place edit (no `sed -i`: BSD sed wants a backup-suffix arg, toybox
# does not — temp+cat overwrites content while preserving the file's inode, mode and SELinux label).
for f in $(find "$RT" "$F" "$ROOT/scripts" -name '*.sh' -type f 2>/dev/null); do
  grep -q "$OLD_UID" "$f" 2>/dev/null || continue
  sed "s/$OLD_UID/$U/g" "$f" > "$f.ttuid.tmp" && cat "$f.ttuid.tmp" > "$f" && rm -f "$f.ttuid.tmp" || fail "SED $f"
  log "sed $f"
done

# 2) request.bin binary uid+gid (idempotent dd at the pinned offsets)
[ -f "$REQUEST" ] || fail "NO_REQUEST_BIN $REQUEST"
for off in $REQ_OFFSETS; do
  write_le_u32 "$REQUEST" "$off" "$U" || fail "DD request.bin@$off"
  got=$(read_le_u32 "$REQUEST" "$off"); [ "$got" = "$U" ] || fail "VERIFY request.bin@$off got=$got want=$U"
done
log "request.bin uid patched @ [$REQ_OFFSETS] -> $U (verified)"

# 3) ownership
chown -R "$U:$U" "$RT" 2>/dev/null || fail CHOWN_RT
[ -d "$RT/private-tmp" ] && chown -R "$U:$U" "$RT/private-tmp" 2>/dev/null

# 4) verify no residual donor uid in text (unless the host happens to own exactly OLD_UID)
if [ "$U" != "$OLD_UID" ]; then
  for f in $(find "$RT" "$F" "$ROOT/scripts" -name '*.sh' -type f 2>/dev/null); do
    grep -q "$OLD_UID" "$f" 2>/dev/null && fail "RESIDUAL_OLD_UID $f"
  done
fi
log "reconcile OK (all Route B uid refs -> $U)"
echo "$U"
