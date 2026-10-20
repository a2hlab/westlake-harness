#!/usr/bin/env python3
"""Explicit local manifest writer; defaults to hash verification only."""
import argparse,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
EXCLUDED={'manifest.json','SHA256SUMS','landing-paths.txt'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 paths=sorted(p for p in HERE.rglob('*') if p.is_file() and '.private' not in p.parts and '__pycache__' not in p.parts and p.relative_to(HERE).as_posix() not in EXCLUDED)
 files=[{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in paths]
 if a.write:
  (HERE/'manifest.json').write_text(json.dumps({'token':'t16-window-evidence','files':files},indent=2)+'\n')
  (HERE/'SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['path']+'\n' for r in files))
  (HERE/'landing-paths.txt').write_text(''.join(str(p.relative_to(ROOT))+'\n' for p in sorted(paths+[HERE/n for n in EXCLUDED])))
 else:
  expected=json.loads((HERE/'manifest.json').read_text())['files'];assert files==expected,'payload changed'
 print(json.dumps({'payload_files':len(files),'landing_files':len(files)+3,'manifest_sha256':sha(HERE/'manifest.json'),'device_calls':0}))
if __name__=='__main__':main()
