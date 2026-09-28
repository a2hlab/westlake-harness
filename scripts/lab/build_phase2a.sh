#!/bin/bash
# SOURCE_STACK.md framework steps with explicit commands, run in the author's workspace path so artifact
# hashes stay comparable with manifest reports. Each step logs to $LOGS/<step>.log and is skipped once ok.
set -u
A=/home/dspfac/a2hlab/source-closure/verify
mountpoint -q $A || { sudo mkdir -p $A && sudo mount --bind "$HOME/a2hlab/ws" $A; } || exit 1
M=$HOME/a2hlab/manifest; LOGS=$HOME/a2hlab/logs/build; mkdir -p "$LOGS"; cd "$M" || exit 1
step() {
  local name=$1; shift
  [ -e "$LOGS/$name.ok" ] && { echo "SKIP $name"; return 0; }
  echo "START $name $(date +%T)"
  if "$@" > "$LOGS/$name.log" 2>&1; then touch "$LOGS/$name.ok"; echo "OK    $name $(date +%T)"; else echo "FAIL  $name $(date +%T)"; return 1; fi
}
step aconfig                unshare -Urn python3 tools/build_aconfig.py --workspace $A --out $A/out/aconfig &
step xsdc                   unshare -Urn python3 tools/build_xsdc.py --workspace $A --out $A/out/xsdc &
step parser-tools           unshare -Urn python3 tools/build_parser_tools.py --workspace $A --out $A/out/parser-tools &
step framework-java-support unshare -Urn python3 tools/build_framework_java_support.py --workspace $A --core-build $A/out/core-java/java --out $A/out/framework-java-support &
wait
echo "PHASE2A_DONE $(date +%T)"
