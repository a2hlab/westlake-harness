#!/usr/bin/env python3
"""Review aids only: target PID exception snippets, no forecast input or verdict."""
import argparse,gzip,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXCEPTION=re.compile(r'(?:Caused by:|(?:java\.lang\.|android\.[\w.]+)(?:[\w$]*Exception|[\w$]*Error)|Fatal signal|dlopen_ns failed|relocating failed: symbol not found.*dso=/data/|Permission denied.*INTERNET)')
NOISE=re.compile(r'IFACE-|class_linker|OH_RegHook|VTLEN|VTBLDIAG')
def main(observations,out):
 rows=json.loads(observations.read_text());out.mkdir(parents=True,exist_ok=True);index=[]
 for key,r in rows.items():
  folder=Path(r['record_path']).parent;log=folder/'hilog.txt'
  if not log.exists():index.append({'app':key,'status':'no-hilog','record':r['record_path']});continue
  lines=log.read_text(errors='replace').splitlines()
  pids={str(x['pid']) for group in r['target_uid_processes'].values() for x in (group or [])}
  # The app-specific capture includes the bridge callback even if the process died before t5.
  callback_pids=set()
  for line in lines:
   m=re.search(r'nativeOnScheduleLaunchApplication ENTRY.*pid=(\d+)',line)
   if m:callback_pids.add(m[1])
  if not pids and len(callback_pids)==1:pids=callback_pids
  snippets=[]
  for n,line in enumerate(lines,1):
   m=re.match(r'\S+\s+\S+\s+(\d+)\s+',line)
   if not m or m[1] not in pids or NOISE.search(line):continue
   if EXCEPTION.search(line):snippets.append({'line':n,'text':line,'next_lines':[{'line':j+1,'text':lines[j]} for j in range(n,min(n+5,len(lines)))]})
  doc={'app':key,'source':str(log),'source_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'pids':sorted(pids),'pid_basis':'UID process snapshots or unique app-specific bridge ENTRY; callback-only attribution must be manually confirmed','snippets':snippets,'verdict':'unassigned; earliest printed exception may be tolerated or downstream, not necessarily causal first wall'}
  dest=out/f'{key}.json.gz';dest.write_bytes(gzip.compress(json.dumps(doc,ensure_ascii=False,indent=2).encode(),mtime=0))
  index.append({'app':key,'status':'extracted' if pids else 'target-pid-unknown','target_pids':sorted(pids),'snippets':len(snippets),'evidence':str(dest),'source':str(log),'source_sha256':doc['source_sha256']})
 (out/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'apps':len(rows),'extracted':sum(x['status']=='extracted' for x in index)}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--observations',type=Path,default=HERE/'observed/observations-pending.json');p.add_argument('--out',type=Path,default=HERE/'observed/exceptions');a=p.parse_args();main(a.observations,a.out)
