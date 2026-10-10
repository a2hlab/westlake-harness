#!/usr/bin/env python3
"""Publish the first ten completed Permissive records; no device operations."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
import readout as r

def publish(run,out,count=10):
 paths=[p for p in run.glob('permissive-*/*/*/*/record.json') if r.read(p).get('finished_at')]
 paths.sort(key=lambda p:r.read(p)['finished_at'])
 if len(paths)<count:return False
 paths=paths[:count];out.mkdir(exist_ok=False)
 view=out/'run'/r.SERIAL;view.mkdir(parents=True)
 images=out/'images';images.mkdir();rows=[]
 for p in paths:
  v=r.analyze(p);rows.append(v);(view/v['key']).symlink_to(p.parent.resolve(),target_is_directory=True)
  dest=images/v['key'];dest.mkdir();(dest/'record.json').write_text(json.dumps({'key':v['key']})+'\n')
  shot=v['last_shot']
  if shot:
   tag='t'+str(float(shot['scheduled_seconds'])).removesuffix('.0');src=p.parent/(tag+'.jpeg')
   if src.exists():(dest/'final.jpeg').symlink_to(src.resolve())
 for name in ('runtime-fingerprint.txt','boot-image-fingerprint.txt','plan.json'):
  src=paths[0].parent.parent/name
  if src.exists():(view/name).write_bytes(src.read_bytes())
 facts=subprocess.check_output([sys.executable,str(r.WS/'westlake-harness/scripts/lab/run_facts.py'),str(view.parent)],text=True);(out/'facts.txt').write_text(facts)
 with (out/'sheet-mapping.txt').open('w') as f:subprocess.run([str(r.WS/'westlake-harness/scripts/lab/contact_sheet.sh'),str(out/'contact-sheet.jpeg'),'--run',str(images),'--shot','final'],stdout=f,stderr=subprocess.STDOUT,check=True)
 (out/'counts.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2).replace(str(r.WS),'$WORKSPACES')+'\n')
 table='key CANTOPEN(raw/targetPID) already-existed(raw/targetPackage)\n'+'\n'.join(f"{v['key']} {v['cantopen_log_lines']}/{v['target_cantopen_log_lines']} {v['wms_already_existed_log_lines']}/{v['target_wms_already_existed_log_lines']}" for v in rows)
 (out/'counts.txt').write_text(table+'\n')
 subprocess.run([str(r.WS/'westlake-inputs/tools/board_note.sh'),'progress',str(r.WS/'westlake-harness/.octos/boards/app-lighting.md'),'91','cx-t0','5cd Permissive前10键中间回执，继续采集，不自报亮数。\n'+facts+'\n'+table+'\ncontact sheet='+r.portable(out/'contact-sheet.jpeg')+'；mapping='+r.portable(out/'sheet-mapping.txt')],check=True)
 print(facts+table);return True
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 deadline=time.time()+1800
 while time.time()<deadline:
  if publish(a.run,a.out):break
  time.sleep(10)
 else:raise SystemExit('No ten completed Permissive records within watcher bound')
