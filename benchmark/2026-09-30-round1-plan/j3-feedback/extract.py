#!/usr/bin/env python3
"""Extract app-attributed archived evidence, including nonfatal FDSAN reports."""
import sys,json,re,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=ROOT.parent/'westlake-harness/benchmark/2026-09-30-j3-u3-sweep'
sys.path.insert(0,str(ROOT/'benchmark/2026-09-29-static-wall-prediction'))
import extract_unified_failures as ex
sys.path.insert(0,str(HERE.parent/'shard'))
from merge_facts import record_facts,fingerprint

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
 verdict=json.loads((SOURCE/'results.json').read_text());u2=json.loads((ROOT.parent/'westlake-harness/benchmark/2026-09-30-u2-sweep/results.json').read_text());lit=set(sum(u2['lit_t20'].values(),[]))|set(verdict['returned']);rows=[];facts=[];runs=[]
 ex.TERMINAL=re.compile(ex.TERMINAL.pattern+r'|\[W-ROOM-SURVIVE\] UNCAUGHT.*main=true|DFX_SignalHandler :: signo\((?:6|11)\), si_code\([12]\)')
 for board in ['5ea','61b']:
  run=next((SOURCE/'runs'/('j3-'+board)).iterdir());fp=run/'runtime-fingerprint.txt'
  runs.append(dict(board=board,path=str(run),fingerprint=fingerprint(fp),fingerprint_sha256=sha(fp),facts=(run/'facts.txt').read_text()))
  for rp in sorted(run.glob('*/record.json')):
   r=json.loads(rp.read_text());f=record_facts(rp);facts.append(f);lp=rp.with_name('hilog.txt');ls=lp.read_text(errors='replace').splitlines() if lp.exists() else []
   e=dict(key=r['key'],package=r['package'],record=str(rp),record_sha256=sha(rp),apk_sha256=r.get('apk_sha256'),lit=r['key'] in lit,log=str(lp),log_sha256=sha(lp) if lp.exists() else None,record_error=r.get('error'),clicked=r.get('clicked'),alive_t5=f['alive_t5'],alive_t20=f['alive_t20'])
   e.update(ex.select(ls,r['package']) if ls else dict(stage='prelaunch',pids=[],chain=[],anchor=None));e['first_terminal']=ex.select(ls,r['package'],False) if ls else None
   own=[(n,l) for n,l in enumerate(ls,1) if (m:=ex.PID.match(l)) and m[1] in e['pids']]
   def hits(pat):return [dict(line=n,text=l) for n,l in own if re.search(pat,l)]
   e['events']=hits(r'Caused by:|\[W-ROOM-SURVIVE\] UNCAUGHT|J_invokeStaticMain_main_threw|ensureBindApplication FAILED|ASSERT FAILED|No implementation found|LoadLibrary failed|Error loading shared library|Error relocating|FDSAN|fdsan|System.exit called|finishActivity: OH TerminateAbility|DFX_SignalHandler|\[B8-UEH\] background.*uncaught|\[B8-AMB\] in-process bind failed|Shattered Pixel Dungeon failed|E/flutter|Unhandled Exception|F/flutter')
   e['events']=[x for x in e['events'] if not any(t in x['text'] for t in ['security_component_client_enhance','kotlinx.coroutines.CoroutineStart','libwestlake_html_compat','OH_RegHook','IFACE-','VTLEN-','nativePrimeDefaultTypeface'])]
   e['faultlogs']=[]
   for p in sorted(rp.parent.glob('faultlogs/*')):
    text=p.read_text(errors='replace');pid=re.search(r'^Pid:(\d+)',text,re.M);uid=re.search(r'^Uid:(\d+)',text,re.M)
    e['faultlogs'].append(dict(path=str(p),sha256=sha(p),pid=pid[1] if pid else None,uid=uid[1] if uid else None,attributed=bool(pid and pid[1] in e['pids'] and uid and uid[1]==str((r.get('bms') or {}).get('uid'))),header=[dict(line=n,text=l) for n,l in enumerate(text.splitlines()[:31],1)]))
   rows.append(e)
   if not e['lit']:
    causes=[x for x in e['chain'] if 'Caused by:' in x['text']];cause=causes[-1] if causes else e['anchor']
    print(e['key'],f"alive={e['alive_t5']}/{e['alive_t20']}", 'FAULT='+str(len(e['faultlogs'])),str(cause or r.get('error'))[:480])
 assert len(rows)==len({r['key'] for r in rows})==66 and sum(not r['lit'] for r in rows)==41
 assert all(r['fingerprint']==runs[0]['fingerprint'] for r in runs)
 dump(HERE/'evidence.json',rows);dump(HERE/'record-facts.json',facts);dump(HERE/'run-audit.json',runs)
if __name__=='__main__':main()
