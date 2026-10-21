#!/usr/bin/env python3
"""Build a small offline review from the retained full review; no device API."""
import argparse,gzip,hashlib,json,shutil
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def main():
 a=argparse.ArgumentParser();a.add_argument('--full-review',type=Path,required=True);a.add_argument('--main',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args();src=args.full_review;out=args.out;out.mkdir(parents=True,exist_ok=True)
 sources={};raw={}
 def copy(rel,dest):
  f=src/rel;t=out/dest;t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,t);sources[dest]={'source':'$G21_FULL_REVIEW/'+rel,'sha256':sha(f),'size':f.stat().st_size}
 for prefix,stage in [('', 'initial'),('restoration-02/','recovery'),('closure-01/','closure')]:
  copy(prefix+'results.json',stage+'/results.json')
  if stage!='closure':copy(prefix+'hash-stages.json',stage+'/hash-stages.json')
 for n in [1384,2293]:
  for suffix in ['.json','.stdout.txt']:
   name=f'command-{n:05d}{suffix}';copy('evidence/apply-device/commands/'+name,'initial/failures/'+name)
 for name in ['boat-before.json']:
  copy('closure-01/'+name,'closure/'+name)
 for folder in ['', 'restoration-02/', 'closure-01/']:
  ix=json.loads((src/folder/'evidence-index.json').read_text())
  for row in ix['files']:
   key=row['original'].removeprefix('$G21_WINDOW/')
   if folder=='' and key=='journal.json':key='journal-after-automatic-rollback.json'
   raw[key]={'sha256':row['original_sha256'],'size':row['size']}
 for rel in ['raw-command-index.json','restoration-02/raw-command-index.json']:
  raw.update(json.loads((src/rel).read_text())['files'])
 for entry in json.loads((src/'closure-01/raw-command-index.json').read_text()).values():raw.update(entry['files'])
 compressed=gzip.compress(json.dumps(raw,sort_keys=True,separators=(',',':')).encode(),mtime=0)
 (out/'original-sha-index.json.gz').write_bytes(compressed)
 labels=[]
 for prefix,side in [('evidence/apply-device/label-recipe-1792583757656176273','initial-candidate'),('evidence/apply-device/label-recipe-1792583897536121279','automatic-rollback-baseline')]:
  d=json.loads((src/prefix/'before.json').read_text());labels.append({'phase':side,'audit':'before','status':d['status'],'paths':d['path_count'],'targets':d['target_count'],'mismatches':len(d['mismatches']),'after_present':False})
 folders=list((src/'restoration-02/evidence/rollback-02-device').glob('label-recipe-*'));assert len(folders)==1
 for name in ['before','after']:
  d=json.loads((folders[0]/(name+'.json')).read_text());labels.append({'phase':'original-journal-recovery','audit':name,'status':d['status'],'paths':d['path_count'],'targets':d['target_count'],'mismatches':len(d['mismatches'])})
 save(out/'label-summary.json',{'audit_paths':295,'recipe_shell_reported_paths':299,'note':'Shell recipe count and audit path count are distinct raw fields; no normalization. Raw files are pinned in original-sha-index.json.gz.','audits':labels})
 refs=[];base=Path('benchmark/2026-10-21-commercial-game/gles-bounded-window/window-01')
 for name,private in [('control.jpeg','post-rollback-02/control.jpeg'),('desktop.jpeg','close-01/desktop.jpeg'),('closure.json','close-01/closure.json'),('window-closed.json','window-closed.json')]:
  f=args.main/base/name;expected=raw[private]['sha256'];assert sha(f)==expected,(str(f),expected)
  refs.append({'repository_path':str(base/name),'sha256':sha(f),'size':f.stat().st_size,'private_alias':'$G21_WINDOW/'+private})
 save(out/'public-evidence-refs.json',{'policy':'Reuse exact main-tree evidence bytes; do not duplicate images. Resolve repository_path relative to main repository root.','files':refs})
 for source,dest in [('post-rollback-02/capture.json','control-capture.json'),('close-01/capture.json','desktop-capture.json'),('close-01/closure.json','closure.json'),('window-closed.json','window-closed.json'),('close-01/power.txt','power.txt')]:
  copy('closure-01/evidence/'+source,'closure/'+dest)
 save(out/'source-index.json',{'aliases':{'$G21_WINDOW':'$HOME/.local/share/westlake/commercial-game-20261021/g21-window-01','$G21_FULL_REVIEW':'retained full review at benchmark/2026-10-21-commercial-game/g21-runtime-peer in the isolated review worktree; not part of this landing'},'copied_sanitized_sources':sources,'original_files':len(raw),'original_index':'original-sha-index.json.gz','full_review_manifest_sha256':sha(src/'manifest.json'),'full_review_initial_manifest_sha256':sha(src/'manifest-initial.json'),'note':'Original journal alias resolves to immutable journal-after-automatic-rollback.json, never the changing journal.json. Large stderr/journals/native exception output are indexed, not copied.'})
 print(json.dumps({'indexed_originals':len(raw),'compressed_index_bytes':len(compressed)}))
if __name__=='__main__':main()
