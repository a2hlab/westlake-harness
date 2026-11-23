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
hdc_reconnect() { timeout 60 $WHDC tconn $T >/dev/null 2>&1; }
# A hung local hdc server still lists the board but times out every shell call (a big file send
# beside other transfers left it at 100% CPU). Restart it when the board does not answer: returns 1.
# A shared board (HDC_SHARED=1) is one other work also uses at the same time: a second agent's launches on this
# board, or another board on this hdc server. A restart ends their hdc sessions, so then the server is left
# running: wait, reconnect, and return 2. The round also never reboots a shared board (launch.sh), and leaves the
# stages in PROTECT_LIST and the zygotes of PROTECT_UIDS alone (below).
hdc_heal() { timeout 20 $WHDC -t $T shell echo ok 2>/dev/null | grep -q ok && return 0
  if [ "${HDC_SHARED:-0}" = 1 ]; then sleep 30; hdc_reconnect; return 2; fi
  timeout 20 $WHDC kill -r >/dev/null 2>&1; sleep 3; hdc_reconnect; return 1; }
# PROTECT_LIST: a file on the board naming stage directories (one per line) that are not this round's, e.g. the
# stages of another agent's running launches. No launch deletes them. When the file is missing on the board,
# nothing is deleted (grep's exit 2 counts as listed). Prints the board-side test for a loop over $d.
protect_test() { [ -n "${PROTECT_LIST:-}" ] && echo "grep -qxF \"\$d\" $PROTECT_LIST; [ \$? = 1 ] || continue;"; }
# PROTECT_UIDS: uids (space-separated) of launches that are not this round's, e.g. apps another agent runs under
# their own host bundles. No zygote with a child under one of them is stopped. Prints a board-side function:
# "spared <zygote>" is true for such a zygote. Empty, no zygote is spared (as before).
spare_fn() { echo "spared() { for c in \$(ps -A -o pid=,ppid= | grep \" \$1\$\" | grep -o '^ *[0-9]*'); do u=\$(ps -o uid= -p \$c | tail -n 1 | grep -o '[0-9]*'); [ -n \"\$u\" ] || continue; case \" ${PROTECT_UIDS:-} \" in *\" \$u \"*) return 0 ;; esac; done; return 1; };"; }
# The board's thread count (/proc/loadavg: running/total), empty when the board does not answer (board_watchdog.sh).
board_threads() { timeout 20 $WHDC -t $T shell 'cat /proc/loadavg' </dev/null 2>/dev/null | tr -d '\r' | cut -d' ' -f4 | cut -d/ -f2; }
# Starts board_watchdog.sh for this script's process group, once per round (WL_WATCHDOG=0 turns it off).
start_watchdog() { [ -n "${WL_WATCHDOG_ON:-}" ] || [ "${WL_WATCHDOG:-1}" = 0 ] && return 0; export WL_WATCHDOG_ON=1
  setsid $DEVICE/board_watchdog.sh "$(ps -o pgid= -p $$ | tr -d ' ')" "$1" </dev/null >/dev/null 2>&1 & }
# Board-side: stop the appspawn-x zygotes, except PROTECT_UIDS' (see spare_fn).
zygote_kill() { echo "$(spare_fn) for z in \$(pidof appspawn-x); do spared \$z && continue; kill \$z; done;"; }
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
  timeout 30 $WHDC -t $T shell "for p in \$(ps -ef | grep '^$u ' | grep -v -e org.westlake.imehost -e org.westlake.playhost | grep -v grep | sed 's/  */ /g' | cut -d' ' -f2); do kill -9 \$p; done; $(zygote_kill) true" >/dev/null 2>&1; }
# Stop what a failed or repeated launch left on the board. The stop after an app's turn needs the child the
# launcher reported: a launcher call that failed after the board had started the app (the WSL interop error
# "UtilAcceptVsock ... failed 110") reported none, and a launch repeated after "board disconnected" reported only
# the second app. In round l8d three such zygotes, two with their app, ran on for hours under the next apps.
# This stops every appspawn-x zygote init has adopted, with the processes it forked and theirs, except the
# zygotes of the Play hosts (a child named com.google.android.gms... or com.android.vending...), which a shared
# round keeps for all its apps. The board is asked rather than the hosts' logs, which a round does not always
# export. All Westlake processes share the host app's uid, so the zygote is what marks a launch's processes.
# Prints "stray <zygote> <pids>" for each; STRAYS_DRY=1 only prints. PROTECT_UIDS' zygotes are not strays.
stop_strays() {
  timeout 40 $WHDC -t $T shell "$(spare_fn) for z in \$(pidof appspawn-x); do [ \"\$(ps -o ppid= -p \$z | tail -n 1 | grep -o '[0-9]*')\" = 1 ] || continue; spared \$z && continue; P=\$(ps -A -o pid=,ppid= | grep \" \$z\$\" | grep -o '^ *[0-9]*'); host=; for p in \$P; do case \"\$(ps -o args= -p \$p | tail -n 1)\" in com.google.android.gms*|com.android.vending*) host=1 ;; esac; done; [ -n \"\$host\" ] && continue; Q=\$(for p in \$P; do ps -A -o pid=,ppid= | grep \" \$p\$\" | grep -o '^ *[0-9]*'; done); echo stray \$z \$P \$Q; ${STRAYS_DRY:+: }kill -9 \$z \$P \$Q; done; true" </dev/null 2>/dev/null | tr -d '\r' | grep '^stray '; }
# launcher arguments for the runtime-library override every launch uses
# WL_RUNTIME_ADD: libraries of the override build the framework stage lacks, added for this launch,
# space-separated. Unset, it is the platform Cronet library (libmainlinecronet.<version>.so, which the
# framework's HttpEngine loads) when the override build has one: that build's natives report the S
# extension level that promises HttpEngine, so every app gets its library. Set empty for none. Needs a
# manifest tools copy with --runtime-library-add.
override_args() { local add=${WL_RUNTIME_ADD-$(ls $V/out/$WL_OVERRIDE/lib 2>/dev/null | grep -E '^libmainlinecronet\..*\.so$')}
  echo "--runtime-library-build $V/out/$WL_OVERRIDE --runtime-library libandroid_native_network_compat.so --runtime-library libwl_missing_natives.so --runtime-library libart.so$(for l in $add; do printf ' --runtime-library-add %s' "$l"; done)"; }
