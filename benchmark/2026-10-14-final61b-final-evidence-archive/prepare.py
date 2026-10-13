#!/usr/bin/env python3
import datetime,hashlib,json,stat,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
B=Path('benchmark/2026-10-09-demo-boatattack/v2-20261013')
DIRS=[B/'outer/final61b-finalization',B/'outer/final61b-seal-capture-v2',B/'outer/final61b-v2-realization',Path('benchmark/2026-10-14-final61b-full128-outer')]
PEER=Path('benchmark/2026-10-14-final61b-full128-peer')
DOCS=[B/'outer/final61b-v2-seal'/name for name in ['README.md','OPERATIONS.zh.md','RESTORE.zh.md']]
BMS=[B/'static/61b-full128'/f'window-{n:02}-{name}' for n in range(1,9) for name in ['observer.json','closeout.json','facts.txt']]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def enumeration():
 files=[];excluded=[]
 for rel in DIRS:
  p=ROOT/rel;assert stat.S_ISDIR(p.lstat().st_mode)
  for q in sorted(p.rglob('*')):
   m=q.lstat().st_mode
   if stat.S_ISDIR(m):continue
   assert stat.S_ISREG(m),'Unexpected nonregular: '+str(q.relative_to(ROOT))
   files.append(q.relative_to(ROOT))
 for p in sorted((ROOT/PEER).iterdir()):
  m=p.lstat().st_mode
  if stat.S_ISREG(m):files.append(p.relative_to(ROOT))
  elif stat.S_ISDIR(m):excluded.append(str(p.relative_to(ROOT)))
  else:raise RuntimeError('Unexpected nonregular peer top: '+str(p.relative_to(ROOT)))
 for rel in BMS+DOCS:
  assert stat.S_ISREG((ROOT/rel).lstat().st_mode),str(rel);files.append(rel)
 assert len(files)==len(set(files));return sorted(map(str,files)),excluded

def snapshot(paths):
 rows=[]
 for name in paths:
  p=ROOT/name
  cur=ROOT
  for part in Path(name).parts[:-1]:
   cur=cur/part;assert stat.S_ISDIR(cur.lstat().st_mode),'Nonliteral source ancestor: '+name
  s=p.lstat();assert stat.S_ISREG(s.st_mode)
  rows.append({'path':name,'bytes':s.st_size,'sha256':sha(p),'mode':stat.S_IMODE(s.st_mode),'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'inode':s.st_ino})
 return rows

def main():
 assert json.loads((ROOT/B/'outer/final61b-finalization/completion.json').read_text())['source_closed'] is True
 paths,excluded=enumeration()
 fixed={'enumerated_at':datetime.datetime.now().astimezone().isoformat(),'source_root':'$WORKSPACES/westlake-harness','recursive_regular_directories':list(map(str,DIRS)),'peer_top_regular_directory':str(PEER),'excluded_peer_directories':excluded,'bms_selected_count':24,'operation_docs':list(map(str,DOCS)),'file_count':len(paths),'files':paths,'excluded':['active API work','future final signoff','board','active archive index','peer temporary .artifacts view'],'device_calls':0}
 save(HERE/'fixed-sources.json',fixed)
 first=snapshot(paths)
 checks=[]
 argvsets=[['lsof','-n','-P','+D',str(ROOT/d)] for d in DIRS]
 peerfiles=[ROOT/name for name in paths if Path(name).parent==PEER]
 extras=peerfiles+[ROOT/p for p in BMS+DOCS]
 for i in range(0,len(extras),100):argvsets.append(['lsof','-n','-P',*map(str,extras[i:i+100])])
 for i,args in enumerate(argvsets):
  p=subprocess.run(args,capture_output=True,text=True,timeout=60)
  (HERE/f'open-files-{i}.stdout.txt').write_text(p.stdout.replace(str(ROOT.parent),'$WORKSPACES'))
  (HERE/f'open-files-{i}.stderr.txt').write_text(p.stderr.replace(str(ROOT.parent),'$WORKSPACES'))
  assert p.returncode in (0,1) and not p.stderr
  writers=[x for x in p.stdout.splitlines()[1:] if len(x.split())>3 and x.split()[3].endswith(('w','u'))]
  assert not writers,'open source writer; pause archiving'
  checks.append({'check':i,'rc':p.returncode,'writers':0})
 time.sleep(5)
 paths2,excluded2=enumeration();assert paths==paths2 and excluded==excluded2
 assert first==snapshot(paths),'source metadata or SHA changed'
 save(HERE/'source-readiness.json',{'observed_at':datetime.datetime.now().astimezone().isoformat(),'inventory_equal':True,'stable_seconds':5,'open_writer_count':0,'lsof_checks':checks,'fixed_sources_sha256':sha(HERE/'fixed-sources.json'),'snapshot_sha256':hashlib.sha256(json.dumps(first).encode()).hexdigest(),'files':len(paths),'source_bytes':sum(r['bytes'] for r in first),'source_authority':'Parent explicitly closed these exact sources; corrected BMS receipt names are flat window-NN-{observer.json,closeout.json,facts.txt}. No source modifications.'})
 print(json.dumps({'fixed_files':len(paths),'bytes':sum(r['bytes'] for r in first),'source_readiness':'PASS','fixed_sources_sha256':sha(HERE/'fixed-sources.json')}))
if __name__=='__main__':main()
