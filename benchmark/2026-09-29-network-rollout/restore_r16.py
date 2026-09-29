#!/usr/bin/env python3
"""Replay the pre-reboot r16 JAR overlay using the verified B11 bind pattern."""
import sys,json,shlex,time
from pathlib import Path
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
S='5cd1e3dd00000000000000000923012c'
P=Path('/Users/zhaoyue/orca/workspaces/vm-copies/r16-runtime-jar/oh-adapter-runtime.jar')
TARGET='/system/android/framework/oh-adapter-runtime.jar'
EXPECTED='6a5d7fcac8c0bd36c0f9c9b65f210f3cff6c90d04b23b21ff3e464476646ad83'
BASELINE='d5000c4e19e74e3ec7a72300ed425fa2c5ba521aa4b04cb6e688e165e6ba5554'
out=Path(__file__).resolve().parent/'5cd/r16-replay';out.mkdir(exist_ok=False)
board=b.Board(S,'/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready();assert b.sha(P)==EXPECTED
parents=[r for r in b.processes(board.shell('ps -A -o PID,PPID,UID,NAME')[1]) if r['name']=='appspawn-x' and r['uid']==0];assert len(parents)==1
pid=parents[0]['pid']
def hashes():
 text=board.shell(f'sha256sum {TARGET} /proc/{pid}/root{TARGET}')[1]
 return {row.split()[-1]:row.split()[0] for row in text.splitlines() if len(row.split())==2}
old=hashes();assert len(old)==2 and set(old.values())=={BASELINE}
remote='/data/local/tmp/b90-r16-replay-'+board.boot
board.shell('mkdir -p '+remote);board.send(P,remote+'/runtime.jar')
assert board.shell('sha256sum '+remote+'/runtime.jar')[1].split()[0]==EXPECTED
board.shell('chmod 0644 '+remote+'/runtime.jar && chcon u:object_r:system_file:s0 '+remote+'/runtime.jar')
receipt={'serial':S,'boot_id':board.boot,'target':TARGET,'baseline_sha256':BASELINE,'deployed_sha256':EXPECTED,'remote_source':remote+'/runtime.jar','status':'pending'};b.save(out/'receipt.json',receipt)
board.shell('mount --bind '+remote+'/runtime.jar '+TARGET)
try:
 actual=hashes();assert len(actual)==2 and set(actual.values())=={EXPECTED}
except Exception:
 board.shell('umount '+TARGET);raise
receipt.update(status='verified_shell_parent',actual=actual);b.save(out/'receipt.json',receipt)
print(json.dumps(receipt,indent=2))
