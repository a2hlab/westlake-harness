#!/system/bin/sh
# Durable startup authority is separate from expiring host placement tickets.
# Loaded only by pinned entry/wrappers, never by an untrusted caller environment.
fail(){ printf '[TT-EXECUTOR] REFUSE %s\n' "$*" >&2; exit 2; }
ROOT=/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012
expected=$(cat "$ROOT/startup.expected.sha256") || fail STARTUP_BINDING_MISSING
case "$expected" in ''|NONE|*[!0-9a-f]*) fail STARTUP_UNSIGNED;; esac
[ "${#expected}" = 64 ] || fail STARTUP_BINDING_BAD
[ -f "$ROOT/startup.env" ] && [ ! -L "$ROOT/startup.env" ] || fail STARTUP_CONFIG_BAD_PATH
[ "$(sha256sum "$ROOT/startup.env" | cut -d' ' -f1)" = "$expected" ] || fail STARTUP_CONFIG_SHA
. "$ROOT/startup.env"
[ "$STARTUP_APPROVED_BY" = 'outer(codex)' ] && [ "$STARTUP_ENABLED" = 1 ] || fail STARTUP_NOT_APPROVED
[ "$STARTUP_SERIAL" = 5cd1e3dd00000000000000000923012c ] || fail STARTUP_SERIAL
AUTH_RUNTIME=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d
AUTH_STAGE=/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d
AUTH_SOCKET=/dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002
AUTH_UID=20011300
[ "$(stat -c %u /data/app/el2/100/base/org.westlake.imehost)" = "$AUTH_UID" ] || fail INSTALLED_HOST_UID_CHANGED
AUTH_BOOT=$(cat /proc/sys/kernel/random/boot_id) || fail KERNEL_BOOT_UNREADABLE
case "$AUTH_BOOT" in ''|*[!0-9a-f-]*) fail KERNEL_BOOT_INVALID;; esac
AUTH_STATE_ROOT="$ROOT/boots/$AUTH_BOOT"
[ ! -e "$ROOT/stop" ] && [ ! -L "$ROOT/stop" ] || fail CANDIDATE_STOP
# A stop in ANY candidate boot attempt persists across future boots.
for stopped in "$ROOT"/boots/*/stop; do [ ! -e "$stopped" ] && [ ! -L "$stopped" ] || fail ATTEMPT_STOP; done
old=/data/local/tmp/operator45/selfheal48/stop
[ ! -e "$old" ] && [ ! -L "$old" ] || fail HISTORICAL_STOP_CHANGED
[ "$(sha256sum "$ROOT/members.tsv" | cut -d' ' -f1)" = "$STARTUP_MEMBERS_SHA" ] || fail MEMBERS_MANIFEST_CHANGED
AUTH_JIT_SHA=$STARTUP_JIT_SHA
AUTH_NAMESPACE_SHA=$STARTUP_NAMESPACE_SHA
AUTH_START_PARENT_SHA=$STARTUP_START_PARENT_SHA
AUTH_HOST_SPAWN_SHA=$STARTUP_HOST_SPAWN_SHA
AUTH_REQUEST_SHA=$STARTUP_REQUEST_SHA
AUTH_PARENT_MODE=new
export PATH=/system/bin:/bin:/system/xbin
