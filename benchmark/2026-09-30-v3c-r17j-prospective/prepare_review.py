#!/usr/bin/env python3
"""Extract PID-attributed review clues, never infer an outcome from error absence."""
import argparse,json,re
from pathlib import Path
from score import sha
PID=re.compile(r'^\S+ \S+\s+(\d+)\s+\d+ ')
CLUE=re.compile(r'main_threw|FATAL EXCEPTION|Caused by:|Unable to (?:start|resume)|dlopen_ns failed|Error relocating|Error loading shared library|No implementation found|StartAbility returned|nativeOnScheduleLaunchApplication ENTRY|EGL_NO_SURFACE|SIGABRT|SIGSEGV|JNI_OnLoad|\[B8-.*(?:FAIL|fail)|\[B\d+-.*(?:bind OK|bind FAILED)|window.*(?:reject|denied)',re.I)
def extract(record,out):
 r=json.loads(record.read_text());key=r['key'];log=record.parent/'hilog.txt';target=out/(key+'.json')
 if target.exists() and json.loads(target.read_text())['record_sha256']==sha(record):return
 data={'key':key,'record':str(record),'record_sha256':sha(record),'error':r.get('error'),'target_pids':[],'snippets':[]}
 if log.exists():
  data.update(hilog=str(log),hilog_sha256=sha(log));lines=log.read_text(errors='replace').splitlines();pids=set()
  for line in lines:
   if 'nativeOnScheduleLaunchApplication ENTRY bundle='+str(r.get('package'))+' ' in line:
    m=PID.match(line)
    if m:pids.add(m[1])
  data['target_pids']=sorted(pids,key=int)
  indices=set()
  for i,line in enumerate(lines):
   m=PID.match(line)
   if m and m[1] in pids and CLUE.search(line):
    indices.update(range(max(0,i-1),min(len(lines),i+7)))
  data['snippets']=[{'line':i+1,'text':lines[i]} for i in sorted(indices)]
 target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 summary=json.loads((a.run/'summary.json').read_text())
 completed={r['key'] for r in summary['records']}
 for r in sorted(a.run.glob('*/record.json')):
  if r.parent.name in completed:extract(r,a.out)
 print('review extracts:',len(list(a.out.glob('*.json'))))
if __name__=='__main__':main()
