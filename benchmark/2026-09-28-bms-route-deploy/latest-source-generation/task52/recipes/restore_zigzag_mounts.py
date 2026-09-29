from pathlib import Path
import sys,time,json
R=Path(__file__).resolve().parents[5];sys.path.insert(0,str(R/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
out=Path.home()/'a2hlab/board/b6-task52-installer/reboot-zigzag';out.mkdir(parents=True,exist_ok=False)
tools=R.parent/'westlake-inputs/tools';board=b.Board('5ea34a4500000000000000001123012c',str(tools/'hdc_mac.sh'),'mac '+str(tools/'board_note.sh'),'cx-t0',out/'commands');board.ready()
assert board.boot=='42f125dc-5d9e-405e-91b4-0f9e929c3c5f'
mounts=[]
for l in (R/'bms/src/.work/b6-task52/rollback/shell-mountinfo.txt').read_text().splitlines():
 f=l.split()
 if f[4].startswith('/data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/') and f[3].startswith('/zigzag-apk-lightup/'):mounts.append(('/data'+f[3],f[4]))
assert len(mounts)==5
_,v=board.shell('ps -A -o PID,PPID,UID,NAME');assert not [x for x in b.processes(v) if x['uid']==20010056]
_,info=board.shell('cat /proc/self/mountinfo');assert not any(t in info for s,t in mounts)
local=R.parent/'westlake-bms-suite/var/state/b6-quick/candidates/b5-alias-b6-context/files'
expected={t:b.sha(local/Path(s).name) for s,t in mounts}
for s,t in mounts:
 _,v=board.shell('sha256sum '+s);assert v.split()[0]==expected[t]
for s,t in mounts:board.shell('mount --bind '+s+' '+t)
_,v=board.shell('sha256sum '+' '.join(expected));assert {l.split()[1]:l.split()[0] for l in v.splitlines()}==expected
b.save(out/'result.json',{'mounts':mounts,'hashes':expected,'boot_id':board.boot})
print('restored five exact accepted app native mounts')
