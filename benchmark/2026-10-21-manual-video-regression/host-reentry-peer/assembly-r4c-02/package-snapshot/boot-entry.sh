#!/system/bin/sh
# Init condition job -> immutable controls -> a fresh kernel-bound boot attempt.
# Never calls the historical overlay/reconciler, never clears a stop or rotates data.
set -eu
HERE=$(dirname "$0")
. "$HERE/config-common.sh"
[ "$HERE" = "$ROOT" ] || fail BOOT_ENTRY_WRONG_LOCATION
for tool in strings grep wc sha256sum stat readlink timeout nsenter hidumper sed cat cut head dirname; do
 command -v "$tool" >/dev/null || fail "TOOL_MISSING $tool"
done
[ ! -L "$ROOT/boots" ] || fail BOOT_STATE_SYMLINK
mkdir -p "$ROOT/boots" || fail BOOT_STATE_PARENT_CREATE
[ ! -L "$AUTH_STATE_ROOT" ] || fail BOOT_ATTEMPT_SYMLINK
# Existing per-boot attempt is NEVER repaired, overwritten, or reset.
mkdir "$AUTH_STATE_ROOT" || fail BOOT_ATTEMPT_ALREADY_EXISTS
while read checksum member mode; do
 case "$member" in ''|*/*|*[!a-zA-Z0-9._-]*) fail MEMBERS_PATH;; esac
 [ -f "$ROOT/$member" ] && [ ! -L "$ROOT/$member" ] || fail "MEMBER_PATH $member"
 [ "$(sha256sum "$ROOT/$member" | cut -d' ' -f1)" = "$checksum" ] || fail "MEMBER_SHA $member"
 cp "$ROOT/$member" "$AUTH_STATE_ROOT/$member" || fail "BOOT_COPY $member"
 chmod "$mode" "$AUTH_STATE_ROOT/$member" || fail "BOOT_MODE $member"
 chown 0:0 "$AUTH_STATE_ROOT/$member" || fail "BOOT_OWNER $member"
 [ "$(sha256sum "$AUTH_STATE_ROOT/$member" | cut -d' ' -f1)" = "$checksum" ] || fail "BOOT_COPY_SHA $member"
done < "$ROOT/members.tsv"
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$AUTH_BOOT" ] || fail BOOT_CHANGED
printf '[TT-EXECUTOR] autonomous boot=%s new_state=%s historical_stop_retained\n' "$AUTH_BOOT" "$AUTH_STATE_ROOT"
exec /system/bin/sh "$AUTH_STATE_ROOT/entry.sh"
