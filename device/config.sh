# config.sh -- sourced by every script here. Nothing machine-specific is in this repo: set these in
# env.sh (see env.sample.sh) or the environment. Each script stops at once if one it needs is unset.
#
#   WL_SC        source-closure root: verify/ (builds, launcher outputs), workspace/ (manifest,
#                westlake), inputs/ (prep-<app> stages, logs/<tag>/ per-app evidence), logs/
#   HDC          the OpenHarmony device client (Linux build, or Windows hdc.exe under WSL)
#   HDC_TARGET   the board: ip:port for a TCP link, or a USB serial
#   WL_FW        framework deploy under $WL_SC/verify/out (holds device-report.json)
#   WL_SHIM      Bionic shim build under $WL_SC/verify/out
#   WL_OVERRIDE  runtime-library override build under $WL_SC/verify/out
#   WL_GUESTS    guest-package build staged beside each app (microG GmsCore + Companion)
#   WL_PLAY_GUESTS  guest build for the shared Play services process (play/ only)
# Optional:
#   WL_CORPUS    corpus directory: apps.csv (one package per line, in rank order), sources.csv,
#                dl/<package>@<version>.(apk|xapk), <map>/<package>/{scan,gap-map}.json
#                (default $WL_SC/inputs/corpus-hk)
#   WL_MANIFEST_TOOLS  launcher tools (default $WL_SC/workspace/manifest/tools)
#   WL_WESTLAKE_SOURCE westlake tree whose native/ helpers the launcher compiles per launch
#                (source_app_namespace, host_spawn, touchfwd; default $WL_SC/workspace/westlake)
#   ANDROID_BUILD_TOOLS  holds apksigner (default ~/android-sdk/build-tools/34.0.0)
DEVICE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd); HARNESS=$(dirname "$DEVICE")
[ -f "$HARNESS/env.sh" ] && . "$HARNESS/env.sh"
need() { for v in "$@"; do [ -n "${!v:-}" ] || { echo "$(basename "$0"): set $v (see device/config.sh)" >&2; exit 64; }; done; }
need WL_SC HDC HDC_TARGET
IN=$WL_SC/inputs; V=$WL_SC/verify; T=$HDC_TARGET; WHDC=$HDC
# A Windows hdc (the board on USB under WSL) goes through hdc_wsl.sh, which finds an interop socket that works.
case $HDC in *.exe) export HDC_EXE=$HDC; WHDC=$DEVICE/hdc_wsl.sh ;; esac
export WL_SC HDC HDC_TARGET; export WL_CORPUS=${WL_CORPUS:-$IN/corpus-hk}; M=${WL_MANIFEST_TOOLS:-$WL_SC/workspace/manifest/tools}
WS=${WL_WESTLAKE_SOURCE:-$WL_SC/workspace/westlake}
RECV=$IN/.recv; mkdir -p "$RECV" "$IN/logs" "$WL_SC/logs"
# From inside $RECV with a relative name, so a Windows hdc (the board on USB under WSL) works too.
recv_to() { (cd "$RECV" && timeout "${3:-60}" $WHDC -t $T file recv "$1" "$2" >/dev/null 2>&1); }
# child_log <pid> <file> <seconds> [drop]: the board's log of child process <pid> into <file>. An hdc call can
# return nothing at a moment when the link works again a minute later (a round lost two apps' logs that way, and
# with them their other processes' logs, which run_apps.sh finds through the main one), so an empty copy is made
# again, three times in all, the last with twice as long. An empty copy never replaces what <file> holds
# (launch.sh's early copy of the same launch). With drop, the board's copy goes once this copy arrived: the board
# keeps every child's stderr otherwise (it once filled /data). Fails, leaving <file> as it was, when none arrived.
# Each hdc call reads /dev/null: a Windows hdc reads its standard input, in a caller's loop the rest of a list.
child_log() {
  local n part=$2.part
  for n in 1 2 3; do
    [ $n -gt 1 ] && sleep "${CHILD_LOG_PAUSE:-5}"
    timeout $(($3 * (n / 3 + 1))) $WHDC -t $T shell "cat /data/service/el1/public/appspawnx/adapter_child_$1.stderr" </dev/null 2>/dev/null | tr -d '\r' > "$part"
    [ -s "$part" ] && break
  done
  if [ ! -s "$part" ]; then
    rm -f "$part"
    return 1
  fi
  mv -f "$part" "$2"
  [ "${4:-}" = drop ] && timeout 60 $WHDC -t $T shell "rm -f /data/service/el1/public/appspawnx/adapter_child_$1.stderr" </dev/null >/dev/null 2>&1
  return 0
}
hdc_reconnect() { timeout 60 $WHDC tconn $T >/dev/null 2>&1; }
# A hung local hdc server still lists the board but times out every shell call (a big file send
# beside other transfers left it at 100% CPU). Restart it when the board does not answer.
hdc_heal() { timeout 20 $WHDC -t $T shell echo ok 2>/dev/null | grep -q ok && return 0
  timeout 20 $WHDC kill -r >/dev/null 2>&1; sleep 3; hdc_reconnect; return 1; }
# A host bundle's uid on the board (default the window host's, which every app runs under; the Play hosts may run
# under org.westlake.playhost): the uid of its ability process.
host_uid() { timeout 20 $WHDC -t $T shell "ps -ef" 2>/dev/null | tr -d '\r' | awk -v b="${1:-org.westlake.imehost}" '$8==b {print $1; exit}'; }
# A bundle's uid from the bundle manager, whether or not any of its processes runs.
bundle_uid() { timeout 20 $WHDC -t $T shell "bm dump -n $1" 2>/dev/null | tr -d '\r' | grep -m1 -o '"uid": [0-9][0-9]*' | grep -o '[0-9]*$'; }
# Stop every Westlake process but the host app. The board has no awk: grep, sed and cut only.
# The appspawn-x zygotes the processes were forked from run as root, not under the host's uid, and go too.
# A launch that keeps running (KEEP_RUNNING: the Play hosts) leaves its zygote, so after a shared round both
# hosts' zygotes stayed on the board, childless, until the next unshared launch.
kill_children() { local u=${1:-$(host_uid)}; [ -n "$u" ] || return 0
  timeout 30 $WHDC -t $T shell "for p in \$(ps -ef | grep '^$u ' | grep -v -e org.westlake.imehost -e org.westlake.playhost | grep -v grep | sed 's/  */ /g' | cut -d' ' -f2); do kill -9 \$p; done; P=\$(pidof appspawn-x); [ -n \"\$P\" ] && kill \$P; true" >/dev/null 2>&1; }
# Stop what a failed or repeated launch left on the board. The stop after an app's turn needs the child the
# launcher reported: a launcher call that failed after the board had started the app (the WSL interop error
# "UtilAcceptVsock ... failed 110") reported none, and a launch repeated after "board disconnected" reported only
# the second app. In round l8d three such zygotes, two with their app, ran on for hours under the next apps.
# This stops every appspawn-x zygote init has adopted, with the processes it forked and theirs, except the
# zygotes of the Play hosts (a child named com.google.android.gms... or com.android.vending...), which a shared
# round keeps for all its apps. The board is asked rather than the hosts' logs, which a round does not always
# export. All Westlake processes share the host app's uid, so the zygote is what marks a launch's processes.
# Prints "stray <zygote> <pids>" for each; STRAYS_DRY=1 only prints.
stop_strays() {
  timeout 40 $WHDC -t $T shell "for z in \$(pidof appspawn-x); do [ \"\$(ps -o ppid= -p \$z | tail -n 1 | grep -o '[0-9]*')\" = 1 ] || continue; P=\$(ps -A -o pid=,ppid= | grep \" \$z\$\" | grep -o '^ *[0-9]*'); host=; for p in \$P; do case \"\$(ps -o args= -p \$p | tail -n 1)\" in com.google.android.gms*|com.android.vending*) host=1 ;; esac; done; [ -n \"\$host\" ] && continue; Q=\$(for p in \$P; do ps -A -o pid=,ppid= | grep \" \$p\$\" | grep -o '^ *[0-9]*'; done); echo stray \$z \$P \$Q; ${STRAYS_DRY:+: }kill -9 \$z \$P \$Q; done; true" </dev/null 2>/dev/null | tr -d '\r' | grep '^stray '; }
# launcher arguments for the runtime-library override every launch uses
# WL_RUNTIME_ADD: libraries of the override build the framework stage lacks, added for this launch,
# space-separated. Unset, it is the platform Cronet library (libmainlinecronet.<version>.so, which the
# framework's HttpEngine loads) when the override build has one: that build's natives report the S
# extension level that promises HttpEngine, so every app gets its library. Set empty for none. Needs a
# manifest tools copy with --runtime-library-add.
override_args() { local add=${WL_RUNTIME_ADD-$(ls $V/out/$WL_OVERRIDE/lib 2>/dev/null | grep -E '^libmainlinecronet\..*\.so$')}
  echo "--runtime-library-build $V/out/$WL_OVERRIDE --runtime-library libandroid_native_network_compat.so --runtime-library libwl_missing_natives.so --runtime-library libart.so$(for l in $add; do printf ' --runtime-library-add %s' "$l"; done)"; }
