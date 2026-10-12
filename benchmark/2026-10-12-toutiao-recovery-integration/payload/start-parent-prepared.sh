#!/system/bin/sh
# Installed as NEW_STATE_ROOT/start-parent.sh. R1 acquires/verifies its lock
# before calling this wrapper. Do not prelaunch a parent outside that lock.
set -eu
HERE=$(dirname "$0")
fail(){ printf '[TT-INTEGRATION] REFUSE %s\n' "$*" >&2; exit 2; }
[ "${TT_RECOVERY_EXECUTE:-0}" = 1 ] && [ -n "${TT_INTEGRATION_AUTH:-}" ] || fail UNSIGNED_ENTRY
expected=$(cat "$HERE/authorization.expected.sha256") || fail AUTH_BINDING_MISSING
case "$expected" in ''|NONE|*[!0-9a-f]*) fail UNSIGNED_NEW_ATTEMPT;; esac
[ "${#expected}" = 64 ] || fail AUTH_BINDING_INVALID
[ "$(sha256sum "$TT_INTEGRATION_AUTH" | cut -d' ' -f1)" = "$expected" ] || fail AUTH_SHA_MISMATCH
. "$TT_INTEGRATION_AUTH"
[ "$AUTH_APPROVED_BY" = 'outer(codex)' ] && [ "$AUTH_PARENT_MODE" = new ] || fail WRONG_PARENT_MODE
[ "$(date +%s)" -lt "$AUTH_EXPIRES_EPOCH" ] || fail AUTH_EXPIRED
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$AUTH_BOOT" ] || fail BOOT_CHANGED
[ ! -e "$AUTH_SOCKET" ] || fail EXISTING_SOCKET_NO_TAKEOVER
[ "$(sha256sum "$AUTH_STAGE/source_app_namespace" | cut -d' ' -f1)" = "$AUTH_NAMESPACE_SHA" ] || fail NAMESPACE_SHA_CHANGED
[ "$(sha256sum "$HERE/real-start-parent.sh" | cut -d' ' -f1)" = "$AUTH_START_PARENT_SHA" ] || fail START_PARENT_SHA_CHANGED
. "$HERE/launch-common.sh"
foreground_window_id >/dev/null || fail FOREGROUND_HOST_NOT_READY
# Execute the captured real window-ID update + source_app_namespace entry.
p=$(/system/bin/sh "$HERE/real-start-parent.sh") || fail PARENT_COMMAND_FAILED
case "$p" in ''|*[!0-9]*) fail PARENT_PID_INVALID;; esac
b=''; n=0
while [ -z "$b" ] && [ "$n" -lt 20 ]; do
 b=$(rb_birth "$p") || b=''
 [ -n "$b" ] || sleep .1
 n=$((n+1))
done
[ -n "$b" ] || fail PARENT_NOT_LIVE
n=0
while [ ! -S "$AUTH_SOCKET" ] && [ "$n" -lt 40 ]; do sleep .25; n=$((n+1)); done
[ -S "$AUTH_SOCKET" ] || fail SOCKET_NOT_READY
parent_owned "$p" "$b" || fail PARENT_CHANGED_DURING_WAIT
verify_parent_window "$p"
file="$HERE/parent-identity"
[ ! -L "$file" ] && { [ ! -e "$file" ] || [ -f "$file" ]; } || fail PARENT_IDENTITY_BAD_PATH
printf '%s %s\n' "$p" "$b" > "$file" || fail PARENT_IDENTITY_WRITE_FAILED
[ "$(cat "$file")" = "$p $b" ] || fail PARENT_IDENTITY_READBACK_FAILED
[ "$(wc -c < "$file")" -eq "$(printf '%s %s\n' "$p" "$b" | wc -c)" ] || fail PARENT_IDENTITY_SIZE_MISMATCH
printf '%s\n' "$p"
