#!/bin/bash
# Read-only inventory of an OH board: what our lab has put on it beyond the factory image, so a clean board
# brought up elsewhere can be diffed against a known-good one (env.md §7). Writes text files only; no board
# writes, no reboots.
#
#   board_inventory.sh <serial> <out dir>
#
# props.txt        build/product properties (proves the same system build, not just the same version label)
# system-files.txt every /system file: size, mtime, path
# system.sha256    sha256 of every /system file (factory mtimes are mixed, so diff hashes, not timestamps;
#                  a bind-mounted file shows its overlay's hash -- see mounts.txt)
# android.sha256   every file under /system/android (framework jars, boot image, runtime libs)
# data-local-tmp.txt / data-local-tmp.sha256   layout of /data/local/tmp (3 levels) and its jar/so/hap/apk files
# mounts.txt       /proc/self/mountinfo (bind overlays such as the runtime JAR)
# bundles.txt      `bm dump -a` (installed bundles, incl. the host HAP and BMS-installed apps)
# misc.txt         selinux mode, appspawn-x process, hilog buffer, screen-off timeout
set -euo pipefail
S=${1:?usage: board_inventory.sh <serial> <out dir>}; OUT=${2:?usage: board_inventory.sh <serial> <out dir>}
HDC=${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}
mkdir -p "$OUT"
sh() { "$HDC" -t "$S" shell "$1" | tr -d '\r'; }

sh 'param get | grep -iE "version|build|product|fullname|sdk|api" | grep -viE "udid|serial|imei" | sort' > "$OUT/props.txt"
sh 'find /system -xdev -type f -exec stat -c "%s %Y %n" {} + 2>/dev/null | sort -k3' > "$OUT/system-files.txt"
sh 'find /system -xdev -type f 2>/dev/null | sort | xargs sha256sum 2>/dev/null' > "$OUT/system.sha256"
sh 'find /system/android -type f 2>/dev/null | sort | xargs sha256sum 2>/dev/null' > "$OUT/android.sha256"
sh 'find /data/local/tmp -maxdepth 3 2>/dev/null | sort' > "$OUT/data-local-tmp.txt"
sh 'find /data/local/tmp -maxdepth 4 -type f \( -name "*.jar" -o -name "*.so" -o -name "*.hap" -o -name "*.apk" \) 2>/dev/null | sort | xargs sha256sum 2>/dev/null' > "$OUT/data-local-tmp.sha256"
sh 'cat /proc/self/mountinfo' > "$OUT/mounts.txt"
sh 'bm dump -a' > "$OUT/bundles.txt"
{ echo "selinux: $(sh getenforce)"; echo "appspawn-x: $(sh 'ps -ef | grep "[a]ppspawn-x"')"
  echo "hilog buffer: $(sh 'hilog -g 2>/dev/null | head -3' | tr '\n' ' ')"
  echo "boot_id: $(sh 'cat /proc/sys/kernel/random/boot_id')"; } > "$OUT/misc.txt"
for f in "$OUT"/*; do printf '%-28s %s lines\n' "$(basename "$f")" "$(wc -l < "$f" | tr -d ' ')"; done
