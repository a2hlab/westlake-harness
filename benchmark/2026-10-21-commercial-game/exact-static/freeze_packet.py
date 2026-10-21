#!/usr/bin/env python3
"""Hash the completed local evidence packet; no network, git or target execution."""
import argparse,json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent;REPO=D.parents[2]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def put(p,o):p.write_text(json.dumps(o,indent=2)+'\n')
def main():
 a=argparse.ArgumentParser();a.add_argument('--write',action='store_true',required=True);a.parse_args()
 private=D/'.private/g04-01';raw=[]
 for p in sorted(private.rglob('*')):
  if not p.is_file() or 'module-cache' in p.parts or '__pycache__' in p.parts:continue
  raw.append({'path':p.relative_to(private).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size})
 put(D/'raw-index.json',{'root_alias':'$G04_PRIVATE = exact-static/.private/g04-01','entries':raw,'remote_archive':'NOT_CREATED','excluded':'Disposable compiler module cache; APK/ELF/DEX and full raw dumps are private only.'})
 excluded={'manifest.json','SHA256SUMS','landing-paths.txt'};files=[]
 for p in sorted(D.rglob('*')):
  if not p.is_file() or '.private' in p.parts or '__pycache__' in p.parts or p.name in excluded:continue
  files.append({'path':p.relative_to(D).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size})
 rust=REPO/'tools/spec-checks/tests/commercial_game_exact_static.rs';files.append({'path':rust.relative_to(REPO).as_posix(),'sha256':sha(rust),'bytes':rust.stat().st_size})
 put(D/'manifest.json',{'schema':'commercial-game-g04-manifest-v1','files':files})
 (D/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+(x['path'] if x['path'].startswith('tools/') else str(D.relative_to(REPO)/x['path']))+'\n' for x in files))
 paths=[x['path'] if x['path'].startswith('tools/') else str(D.relative_to(REPO)/x['path']) for x in files]+[str(D.relative_to(REPO)/x) for x in sorted(excluded)]
 (D/'landing-paths.txt').write_text('\n'.join(paths)+'\n')
 print(json.dumps({'payload_files':len(files),'landing_files':len(paths),'manifest_sha256':sha(D/'manifest.json'),'private_entries':len(raw)}))
if __name__=='__main__':main()
