#!/bin/bash
# Host-side device inputs that need no board: runtime data (fonts/ICU), host apps (HAP), development signing.
set -u
A=/home/dspfac/a2hlab/source-closure/verify; O=$A/out
mountpoint -q $A || { sudo mkdir -p $A && sudo mount --bind "$HOME/a2hlab/ws" $A; } || exit 1
M=$HOME/a2hlab/manifest; LOGS=$HOME/a2hlab/logs/build; cd "$M" || exit 1
ok() { for s; do [ -e "$LOGS/$s.ok" ] || return 1; done; }
step() {
  local name=$1; shift
  ok "$name" && { echo "SKIP $name"; return 0; }
  echo "START $name $(date +%T)"
  if "$@" > "$LOGS/$name.log" 2>&1; then touch "$LOGS/$name.ok"; echo "OK    $name $(date +%T)"; else echo "FAIL  $name $(date +%T)"; return 1; fi
}
step runtime-data python3 tools/package_runtime_data.py --workspace $A --fonts --out $O/runtime-data &
step apps python3 tools/rebuild.py --workspace $A --profile apps --out $O/apps --jobs 6
wait
ok apps && step signed-host python3 tools/sign_development_host.py --workspace $A --host-build $O/apps/apps --out $O/signed-host
echo "PHASE3C_DONE $(date +%T)"
