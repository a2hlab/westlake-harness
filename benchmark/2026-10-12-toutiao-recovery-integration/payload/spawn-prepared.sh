#!/system/bin/sh
# Installed as NEW_STATE_ROOT/spawn.sh; never replace the old state's script.
set -eu
HERE=$(dirname "$0")
fail(){ printf '[TT-INTEGRATION] REFUSE %s\n' "$*" >&2; exit 2; }
[ "${TT_RECOVERY_EXECUTE:-0}" = 1 ] && [ -n "${TT_INTEGRATION_AUTH:-}" ] || fail UNSIGNED_ENTRY
expected=$(cat "$HERE/authorization.expected.sha256") || fail AUTH_BINDING_MISSING
case "$expected" in ''|NONE|*[!0-9a-f]*) fail UNSIGNED_NEW_ATTEMPT;; esac
[ "${#expected}" = 64 ] || fail AUTH_BINDING_INVALID
[ "$(sha256sum "$TT_INTEGRATION_AUTH" | cut -d' ' -f1)" = "$expected" ] || fail AUTH_SHA_MISMATCH
. "$TT_INTEGRATION_AUTH"
[ "${AUTH_APPROVED_BY:-}" = 'outer(codex)' ] && [ "${AUTH_NEW_ATTEMPT:-}" = yes ] || fail AUTH_NOT_OUTER
[ "$(date +%s)" -lt "${AUTH_EXPIRES_EPOCH:-0}" ] || fail AUTH_EXPIRED
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$AUTH_BOOT" ] || fail BOOT_CHANGED
[ -S "$AUTH_SOCKET" ] || fail SOCKET_NOT_READY
if [ "${AUTH_PARENT_MODE:-}" = new ]; then
 [ -f "$HERE/parent-identity" ] && [ ! -L "$HERE/parent-identity" ] || fail PARENT_IDENTITY_PENDING
 read TT_PARENT_PID TT_PARENT_BIRTH extra < "$HERE/parent-identity" || fail PARENT_IDENTITY_READ_FAILED
 [ -z "$extra" ] || fail PARENT_IDENTITY_MALFORMED
fi
[ -n "${TT_PARENT_PID:-}" ] && [ -n "${TT_PARENT_BIRTH:-}" ] || fail PARENT_IDENTITY_PENDING
# Exact helper/parent checks are in launch-common.sh, copied from frozen R1.
. "$HERE/launch-common.sh"
parent_owned "$TT_PARENT_PID" "$TT_PARENT_BIRTH" || fail PARENT_IDENTITY_CHANGED
verify_parent_window "$TT_PARENT_PID"
[ -f "$AUTH_RUNTIME/prepare_jit50.sh" ] || fail JIT_MISSING
[ "$(sha256sum "$AUTH_RUNTIME/prepare_jit50.sh" | cut -d' ' -f1)" = "$AUTH_JIT_SHA" ] || fail JIT_SHA_CHANGED
private_jit="$PROC/$TT_PARENT_PID/root/data/local/tmp/asx/prepare_jit50.sh"
[ -f "$private_jit" ] || fail JIT_PARENT_VIEW_MISSING
[ "$(sha256sum "$private_jit" | cut -d' ' -f1)" = "$AUTH_JIT_SHA" ] || fail JIT_PARENT_SHA_CHANGED
[ "$(stat -L -c '%d:%i' "$private_jit")" = "$(stat -L -c '%d:%i' "$AUTH_RUNTIME/prepare_jit50.sh")" ] || fail JIT_PARENT_INODE_CHANGED
[ "$(sha256sum "$AUTH_STAGE/host_spawn" | cut -d' ' -f1)" = "$AUTH_HOST_SPAWN_SHA" ] || fail HOST_SPAWN_SHA_CHANGED
[ "$(sha256sum "$AUTH_STAGE/request.bin" | cut -d' ' -f1)" = "$AUTH_REQUEST_SHA" ] || fail REQUEST_SHA_CHANGED
# Preserve the original, proven order: parent namespace -> JIT -> host_spawn.
timeout 8 /bin/nsenter -t "$TT_PARENT_PID" -m -- /system/bin/sh /data/local/tmp/asx/prepare_jit50.sh >&2 || fail JIT_PREPARE_FAILED
parent_owned "$TT_PARENT_PID" "$TT_PARENT_BIRTH" || fail PARENT_CHANGED_AFTER_JIT
verify_parent_window "$TT_PARENT_PID"
exec /system/bin/sh "$HERE/real-spawn.sh"
