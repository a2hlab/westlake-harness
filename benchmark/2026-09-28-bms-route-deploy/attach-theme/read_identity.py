from pathlib import Path
import sys,json,hashlib
r=Path(__file__).resolve().parent
sys.path.insert(0,str(r.parent/'batch'));import bms_batch as b
out=Path.home()/'a2hlab/board/b6-identity-5ea-attempt2';out.mkdir(exist_ok=False)
board=b.Board('5ea34a4500000000000000001123012c','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready()
_,p=board.shell('ps -A -o PID,PPID,UID,NAME');(out/'processes.txt').write_text(p)
parents=[x for x in b.processes(p) if x['name']=='appspawn-x' and x['uid']==0];assert len(parents)==1,parents
parent_pid=parents[0]['pid']
children=[x for x in b.processes(p) if x['ppid']==parent_pid and x['uid']==20010055];assert len(children)==1,children
pid=children[0]['pid']
_,maps=board.shell(f'cat /proc/{pid}/maps');(out/'parent-maps.txt').write_text(maps)
art=sorted(set(x.split()[-1] for x in maps.splitlines() if x.split()[-1].endswith('/libart.so')));assert len(art)==1,art
files=['/system/android/framework/arm64/boot-framework.oat','/system/android/framework/framework.jar','/system/android/framework/oh-adapter-runtime.jar',art[0]]
_,hashes=board.shell('sha256sum '+' '.join(f'/proc/{pid}/root'+f for f in files));(out/'hashes.txt').write_text(hashes)
for f in files:
 if f.endswith('.oat') or f.endswith('libart.so'):board.receive(f'/proc/{pid}/root'+f,out/Path(f).name)
oat=(out/'boot-framework.oat').read_bytes();i=oat.index(b'oat\n');version=oat[i+4:i+7].decode()
rec={'serial':board.serial,'boot_id':board.boot,'parent_pid':parent_pid,'child_pid':pid,'oat_version':version,'hashes':hashes,'libart':art[0],'vm_evidence':str(out)}
b.save(r/'identity.json',rec);print(json.dumps(rec,indent=2))
