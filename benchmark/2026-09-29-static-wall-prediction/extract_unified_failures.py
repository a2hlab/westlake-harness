#!/usr/bin/env python3
"""Read PID-attributed startup failures; never equate every error with a wall."""
import json,re,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=Path('/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-unified-r17r-5cd-sweep')
RUN=SOURCE/'runs/unified-r17r-5cd/5cd1e3dd00000000000000000923012c'
OUT=HERE/'unified-r17r-feedback'
PID=re.compile(r'^\S+ \S+\s+(\d+)\s+\d+ ')
TERMINAL=re.compile(r'ensureBindApplication FAILED|J_invokeStaticMain_main_threw|ASSERT FAILED|FATAL EXCEPTION|Fatal signal')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def select(lines,package,include_bind=True):
 pids={m[1] for l in lines if 'nativeOnScheduleLaunchApplication ENTRY bundle='+package+' ' in l and (m:=PID.match(l))}
 own=[(i+1,l) for i,l in enumerate(lines) if (m:=PID.match(l)) and m[1] in pids]
 anchors=[(n,l) for n,l in own if TERMINAL.search(l) and (include_bind or 'ensureBindApplication FAILED' not in l)]
 if not anchors:return {'pids':sorted(pids),'stage':'unknown-no-startup-fatal','anchor':None,'chain':[]}
 n,line=anchors[0];pid=PID.match(line)[1];chain=[]
 for k,l in own:
  if k<n or PID.match(l)[1]!=pid:continue
  if k>n+120:break
  if k>n and ('AppSpawnXInit: initChild failed' in l or TERMINAL.search(l)):break
  if k==n or 'Caused by:' in l or '\tat ' in l or 'Exception' in l or 'Error' in l:chain.append({'line':k,'text':l})
 return {'pids':sorted(pids),'stage':'bind-failed-process-may-survive' if 'ensureBindApplication' in line else 'native-fatal' if 'ASSERT FAILED' in line or 'Fatal signal' in line else 'main-threw','anchor':{'line':n,'text':line},'chain':chain}
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 run=RUN;signature=json.loads((SOURCE/'results.json').read_text());lit=set(signature['lit_t20_by_screenshot']);out=[]
 for p in sorted(run.glob('*/record.json')):
  r=json.loads(p.read_text());f=p.parent/'hilog.txt';d={'key':r['key'],'package':r['package'],'apk_sha256':r.get('apk_sha256'),'lit':r['key'] in lit,'record':str(p),'record_sha256':sha(p),'record_error':r.get('error'),'log':str(f)}
  if f.exists():
   lines=f.read_text(errors='replace').splitlines();d.update(select(lines,r['package']))
   d['first_terminal']=select(lines,r['package'],include_bind=False)
   d['log_sha256']=sha(f)
  else:d.update(pids=[],stage='prelaunch',anchor=None,chain=[],first_terminal=None)
  if d['lit']:d['outcome']='outer-signed-lit; errors not treated as blocking'
  out.append(d)
 (OUT/'first-failures.json').write_text(json.dumps(out,indent=2)+'\n')
 for d in out:
  if d['lit']:continue
  causes=[e for e in d['chain'] if 'Caused by:' in e['text']];last=causes[-1] if causes else d['anchor'];print(d['key'],d['stage'],(str(last['line'])+' '+last['text'].split('[stderr]')[-1][:210]) if last else str(d['record_error']))
if __name__=='__main__':main()
