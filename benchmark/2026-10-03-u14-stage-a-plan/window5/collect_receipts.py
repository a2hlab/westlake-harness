"""Read-only facts and continuation accounting; no visual verdicts."""
import json,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;W=H.parents[3];M=W/'westlake-harness'
a=json.loads((H/'accounting.json').read_text());root=H/a['run_id'];summary={}
for board,keys in a['keys'].items():
 runner=root/board/'runner';records=[];facts=[];t20=[]
 for rec in sorted(runner.glob('lit-*/*/*/*/record.json')):
  d=json.loads(rec.read_text())
  row={'key':d['key'],'status':d.get('status'),'record':str(rec),'screenshots':d.get('screenshots',[]),'shard':rec.relative_to(runner).parts[0]};records.append(row)
  out=subprocess.run([sys.executable,str(M/'scripts/lab/run_facts.py'),str(rec.parent.parent)],capture_output=True,text=True,check=True)
  facts.append(str(rec.parent.parent)+'\n'+out.stdout)
  for s in row['screenshots']:
   if s.get('captured') and float(s.get('scheduled_seconds',-1))==20:t20.append(d['key']+'\t'+s['path'])
 measured=sorted({r['key'] for r in records if any(s.get('captured') and float(s.get('scheduled_seconds',-1))==20 for s in r['screenshots'])});unmeasured=sorted(set(keys)-set(measured))
 (H/f'{board}-records.json').write_text(json.dumps(records,indent=2)+'\n');(H/f'{board}-facts-verbatim.txt').write_text('\n'.join(facts));(H/f'{board}-t20-paths.txt').write_text('\n'.join(t20)+'\n');(H/f'{board}-measured.txt').write_text('\n'.join(measured)+'\n');(H/f'{board}-unmeasured.txt').write_text('\n'.join(unmeasured)+'\n')
 counts={k:0 for k in ['selftest_error_count','badtag_count','probe_error_count','unknown_runs']};empty=0
 for p in (runner/'selftest').glob('*.json'):
  d=json.loads(p.read_text())
  if d.get('schema_version')!=2:continue
  if d.get('run_count',0)==0:empty+=1;continue
  for k in counts:counts[k]+=d.get(k,0)
 summary[board]={'records':len(records),'measured_keys':measured,'unmeasured_keys':unmeasured,'selftest':counts,'empty_selftest_reports':empty,'visual_verdict':'pending outer review'}
(H/'continuation-accounting.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
