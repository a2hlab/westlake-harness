"""VM: read-only hash verification of the route-a signal DSO in a live child."""
from pathlib import Path
import json,sys,hashlib
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'batch'));import bms_batch as b
out=Path.home()/'a2hlab/board/b6-signal-readonly-5ea';out.mkdir(exist_ok=False)
board=b.Board('5ea34a4500000000000000001123012c','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready()
_,ps=board.shell('ps -A -o PID,PPID,UID,NAME');rows=[x for x in b.processes(ps) if x['uid']==20010056 and x['ppid']==13161];assert len(rows)==1
pid=rows[0]['pid'];_,maps=board.shell(f'cat /proc/{pid}/maps');paths=sorted(set(x.split()[-1] for x in maps.splitlines() if x.split()[-1].endswith('/libsigchain.so')));assert len(paths)==1
_,hashes=board.shell('sha256sum /proc/'+str(pid)+'/root'+paths[0]);local=Path('/Users/zhaoyue/orca/workspaces/westlake-bms-suite/.bridge-payload/pr03-74e6-portable/route/libsigchain.so');assert hashes.split()[0]==hashlib.sha256(local.read_bytes()).hexdigest()
(r/'null-check-root/signal-identity.json').write_text(json.dumps({'child_pid':pid,'boot_id':board.boot,'loaded_path':paths[0],'sha256':hashes.split()[0],'matching_local':str(local),'maps':[x for x in maps.splitlines() if any(t in x for t in ['libsigchain.so','libdfx_signalhandler'])],'vm_evidence':str(out)},indent=2)+'\n')
print(hashes)
