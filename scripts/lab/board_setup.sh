#!/bin/bash
# Bring a freshly flashed OH 6.1.0.31 DAYU600 to the state the launcher expects, then stage the framework:
# clock from the Mac (a fresh board boots at 1970, which breaks TLS), screen held on for 24 h (the default 30 s
# screen-off brings the lock screen back over every app), lock screen dismissed, signed host installed, and
# probe_framework_vm.py run once. Usage: board_setup.sh <serial>   (framework report: ~/a2hlab/board/<serial>/framework-1)
set -eu
S=$1
. "$(dirname "${BASH_SOURCE[0]}")/lab_paths.sh" || exit 1
H=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
dev() { "$H" -t "$S" shell "$1" | LC_ALL=C tr -d '\r'; }

dev "date $(date +%m%d%H%M%Y.%S) >/dev/null; power-shell wakeup >/dev/null; power-shell timeout -o 86400000 >/dev/null"
dev 'uinput -T -m 600 1500 600 300 400' >/dev/null
if ! dev 'bm dump -n org.westlake.imehost' | grep -q '"uid"'; then
  VMH=$(lab_vm_home)   # the VM's ~/a2hlab/ws through OrbStack's Mac view of the VM filesystem
  "$H" -t "$S" install ~/OrbStack/a2hlab"$VMH"/a2hlab/ws/out/signed-host/source-host.hap | tail -1
fi
orb -m a2hlab bash -lc "O=/home/dspfac/a2hlab/source-closure/verify/out; R=~/a2hlab/board/$S; mkdir -p \$R; [ -e \$R/framework-1/device-report.json ] && exit 0
cd ~/a2hlab/manifest && python3 tools/probe_framework_vm.py \
 --appspawn-build \$O/appspawn --core-runtime \$O/native-runtime --native-runtime \$O/native-runtime \
 --core-build \$O/core-java/java --extension-build \$O/java-extensions \
 --framework-build \$O/framework-runtime --boot-build \$O/framework-boot --resources-build \$O/framework-resources \
 --data-build \$O/runtime-data --firmware-abi ~/a2hlab/ws/westlake/native/oh61-firmware-abi.json \
 --hdc $WORKSPACES/westlake-inputs/tools/hdc_mac.sh --serial $S --out \$R/framework-1 >\$R/framework-1.log 2>&1
python3 -c \"import json;r=json.load(open('\$R/framework-1/device-report.json'));print('framework passed=%s files=%d stage=%s'%(r['passed'],len(r['files']),r['stage']))\""
