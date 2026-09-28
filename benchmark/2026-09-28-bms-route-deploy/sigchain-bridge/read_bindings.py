"""VM read-only: resolve live libart JUMP_SLOT owners, without altering memory."""
from pathlib import Path
import sys,json,re
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'batch'));import bms_batch as b
out=Path.home()/'a2hlab/board/b6-sigchain-binding-5ea-v3';out.mkdir(exist_ok=False)
board=b.Board('5ea34a4500000000000000001123012c','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready()
_,ps=board.shell('ps -A -o PID,PPID,UID,NAME');rows=[x for x in b.processes(ps) if x['uid']==20010056 and x['ppid']==13161];assert len(rows)==1;pid=rows[0]['pid']
_,maps=board.shell(f'cat /proc/{pid}/maps');(r/'binding-maps.txt').write_text(maps)
entries=[]
for s in maps.splitlines():
 t=s.split()
 if len(t)>=6:
  lo,hi=map(lambda x:int(x,16),t[0].split('-'));entries.append((lo,hi,t[-1],int(t[2],16)))
# Select the executable PT_LOAD, not an unrelated full-file read-only mmap.
# Locked ELF p_offset=0x2c9400, p_vaddr=0x2ca400 (page aligned below).
base=next(lo-0x2ca000 for lo,hi,path,offset in entries if path.endswith('/libart.so') and offset==0x2c9000)
relocs={'AddSpecialSignalHandlerFn':0x94f618,'RemoveSpecialSignalHandlerFn':0x94f628,'sigaction':0x94f7e8,'EnsureFrontOfChain':0x94f850,'SkipAddSignalHandler':0x94fd98}
res={}
for name,off in relocs.items():
 _,data=board.shell(f'dd if=/proc/{pid}/mem bs=1 skip={base+off} count=8 2>/dev/null | od -An -tx8')
 addr=int(data.strip(),16);owners=[p for lo,hi,p,o in entries if lo<=addr<hi];assert len(owners)<=1,(name,data,owners);res[name]={'relocation':hex(off),'bound_address':hex(addr),'owner':owners[0] if owners else None,'raw':data}
_,hashes=board.shell('sha256sum /proc/'+str(pid)+'/root'+next(p for lo,hi,p,o in entries if p.endswith('/libart.so'))+' /proc/'+str(pid)+'/root'+next(p for lo,hi,p,o in entries if p.endswith('/libsigchain.so')))
record={'serial':board.serial,'boot_id':board.boot,'pid':pid,'libart_load_bias':hex(base),'bindings':res,'hashes':hashes,'vm_evidence':str(out)};(r/'bindings.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
