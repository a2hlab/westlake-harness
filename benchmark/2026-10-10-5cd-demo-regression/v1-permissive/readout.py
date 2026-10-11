#!/usr/bin/env python3
"""Read existing regular captures only; preserve raw facts and t3 UI-review queues."""
import argparse,importlib.util,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2];WS=Path(os.environ.get('WORKSPACES',REPO.parent));T4=REPO/'benchmark/2026-10-09-demo-baseline/t4';SN='5cd1e3dd00000000000000000923012c'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--round',type=Path,required=True);ap.add_argument('--window');ap.add_argument('--out',type=Path,required=True);ap.add_argument('--post',action='store_true');a=ap.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);windows=[a.round/a.window] if a.window else sorted(set(x.parent.parent for x in a.round.glob('**/runner/group-*') if x.is_dir()));records={}
 for w in windows:
  for p in (w/'runner').glob('group-*/*/*/*/record.json'):
   r=json.loads(p.read_text())
   if not r.get('finished_at'):continue
   assert r['key'] not in records,'duplicate regular key';records[r['key']]=p
 view=a.out/'view'/SN;view.mkdir(parents=True)
 for k,p in records.items():(view/k).symlink_to(p.parent.resolve(),target_is_directory=True)
 for name in ['runtime-fingerprint.txt','boot-image-fingerprint.txt']:
  files=[p.parent.parent/name for p in records.values()];values={p.read_bytes() for p in files if p.exists()}
  assert len(values)<=1,'mixed fingerprint';
  if values:(view/name).write_bytes(next(iter(values)))
 plans=[json.loads((p.parent.parent/'plan.json').read_text()) for p in records.values() if (p.parent.parent/'plan.json').is_file()]
 tools={json.dumps(p.get('tool'),sort_keys=True) for p in plans}
 if len(tools)==1 and plans:(view/'plan.json').write_text(json.dumps({'tool':plans[0].get('tool')})+'\n')
 facts=subprocess.check_output([sys.executable,str(WS/'westlake-harness/scripts/lab/run_facts.py'),str(view.parent)],text=True);(a.out/'facts.txt').write_text(facts)
 subprocess.run([sys.executable,str(T4/'regress_vs_signoff.py'),str(view.parent),'--out',str(a.out/'compare'),'--sheet'],check=True)
 images=a.out/'last-shots';images.mkdir()
 for key,p in records.items():
  r=json.loads(p.read_text());shots=[s for s in r.get('screenshots',[]) if s.get('captured')]
  if not shots:continue
  # Scheduled final capture; filenames match the standard record directory.
  candidates=[x for x in p.parent.glob('t*.jpeg')]
  if candidates:
   final=max(candidates,key=lambda x:float(x.stem[1:]) if x.stem[1:].replace('.','',1).isdigit() else -1);(images/(key+'.jpeg')).symlink_to(final.resolve())
 files=sorted(images.glob('*.jpeg'))
 if files:
  with (a.out/'contact-mapping.txt').open('w') as f:subprocess.run(['bash',str(WS/'westlake-harness/scripts/lab/contact_sheet.sh'),str(a.out/'contact-sheet.jpeg'),'--cols','8','--width','240',*[str(x) for x in files]],stdout=f,stderr=subprocess.STDOUT,check=True)
 report=json.loads((a.out/'compare/comparison.json').read_text());summary={'captured_regular_keys':len(records),'semantic_triage':report['semantic_summary'],'suspect_keys':(a.out/'compare/suspect.keys').read_text().split(),'UI_verdict':'pending_outer_review','source_windows':[w.name for w in windows]};(a.out/'readout.json').write_text(json.dumps(summary,indent=2)+'\n')
 if a.post:
  prefix=str(a.out.resolve()).replace(str(WS),'$WORKSPACES');msg='5cd v1宽容预跑 '+(','.join(w.name for w in windows))+' facts原样:\n'+facts+'\ncontact_sheet='+prefix+'/contact-sheet.jpeg；suspect(仅机器筛选，外环判图)='+','.join(summary['suspect_keys'])+'；t3对账='+prefix+'/compare/comparison.json；无自报点亮数。'
  subprocess.run([str(WS/'westlake-inputs/tools/board_note.sh'),'progress',str(WS/'westlake-harness/.octos/boards/app-lighting.md'),'91','cx-t0',msg],check=True)
 print(json.dumps(summary))
if __name__=='__main__':main()
