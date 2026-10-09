#!/usr/bin/env python3
"""Make an outer-read sheet at each record's real t10/t20, retaining missing tiles.
Recorded image bytes and record.json are never edited.
"""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[3])))
def expand(s):return s.replace('$WORKSPACES',str(WS))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('batch');a=ap.parse_args()
 base=HERE/'plans-v2'/a.batch;plan=json.loads((base/'plan.json').read_text());runner=base/'runner'
 keys=[]
 for shard in plan['shards']:keys.extend(Path(expand(shard['keys_file'])).read_text().split())
 records={}
 for p in runner.glob('0*/*/*/*/record.json'):
  r=json.loads(p.read_text());records[r['key']]=(p,r)
 view=base/'sheet-images';view.mkdir(exist_ok=False);paths=[];mapping=[]
 for key in keys:
  dest=view/(key+'.jpeg');paths.append(str(dest));p,r=records.get(key,(None,{}));seconds=r.get('demo_capture_seconds');item={'key':key,'record':str(p) if p else None,'scheduled_seconds':seconds,'source':None,'reason':'no required capture'}
  for shot in r.get('screenshots',[]):
   if shot.get('scheduled_seconds')!=seconds or not shot.get('captured'):continue
   source=Path(shot['path'])
   if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=shot.get('sha256'):raise SystemExit('image SHA drift: '+key)
   dest.symlink_to(source.resolve());item.update(source=str(source),sha256=shot['sha256'],reason=None);break
  mapping.append(item)
 (base/'sheet-mapping.json').write_text(json.dumps(mapping,indent=2)+'\n')
 with (base/'contact-sheet.txt').open('w') as f:subprocess.run(['bash',str(WS/'westlake-harness/scripts/lab/contact_sheet.sh'),str(base/'contact-sheet.jpeg'),'--cols','6','--width','260',*paths],stdout=f,stderr=subprocess.STDOUT,check=True)
 print(base/'contact-sheet.jpeg')
if __name__=='__main__':main()
