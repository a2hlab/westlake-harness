#!/bin/bash
# The SOURCE_STACK.md build sequence, run as two waves; each step logs to $LOGS/<step>.log.
set -u
A=/home/dspfac/a2hlab/source-closure/verify
mountpoint -q $A || { sudo mkdir -p $A && sudo mount --bind "$HOME/a2hlab/ws" $A; } || exit 1
M=$HOME/a2hlab/manifest; WS=$A; OUT=$WS/out; LOGS=$HOME/a2hlab/logs/build; mkdir -p "$LOGS"
cd "$M" || exit 1
step() {  # step <name> <command...>: run once, record status
  local name=$1; shift
  if [ -e "$LOGS/$name.ok" ]; then echo "SKIP $name (already built)"; return 0; fi
  echo "START $name $(date +%T)"
  if "$@" > "$LOGS/$name.log" 2>&1; then touch "$LOGS/$name.ok"; echo "OK    $name $(date +%T)"; return 0; fi
  echo "FAIL  $name $(date +%T) (see $LOGS/$name.log)"; return 1
}
# wave 1: independent
step host-tools     python3 tools/rebuild.py --workspace "$WS" --profile host-tools     --out "$OUT/host-tools"     --jobs 6 & p1=$!
step core-java      python3 tools/rebuild.py --workspace "$WS" --profile core-java      --out "$OUT/core-java"                & p2=$!
step native-support python3 tools/rebuild.py --workspace "$WS" --profile native-support --out "$OUT/native-support" --jobs 6 & p3=$!
wait $p1; h=$?; wait $p2; c=$?; wait $p3; n=$?
# wave 2: dependent
[ $c -eq 0 ] && step java-extensions python3 tools/build_java_extensions.py --workspace "$WS" --core-build "$OUT/core-java/java" --out "$OUT/java-extensions"; e=$?
[ $n -eq 0 ] && step art python3 tools/rebuild.py --workspace "$WS" --profile art --native-build "$OUT/native-support/native" --out "$OUT/art" --jobs 12
[ $h -eq 0 ] && [ $c -eq 0 ] && [ $e -eq 0 ] && step core-boot env LD_PRELOAD=$HOME/a2hlab/tools/libmap32bit.so python3 tools/build_core_boot.py --host-build "$OUT/host-tools/host" --core-build "$OUT/core-java/java" --extension-build "$OUT/java-extensions" --out "$OUT/core-boot"
echo "WAVES_DONE $(date +%T)"
