#!/usr/bin/env python3
"""Write a path-only landing and hashes; never stages, commits or pushes."""
import argparse,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
R=D.parents[2]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',required=True,action='store_true');ap.parse_args()
 excluded={'manifest.json','landing-paths.txt','SHA256SUMS'}
 files=[p for p in D.rglob('*') if p.is_file() and '.private' not in p.relative_to(D).parts and '__pycache__' not in p.parts and p.name not in excluded]
 files.append(R/'tools/spec-checks/tests/commercial_game_loader_triage.rs')
 rows=[{'path':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(files)]
 (D/'manifest.json').write_text(json.dumps({'files':rows,'scope':'STATIC_ONLY_NO_DEVICE_NO_BUILD_NO_RUNTIME_ACCEPTANCE'},indent=2)+'\n')
 listing=sorted([r['path'] for r in rows]+[str((D/n).relative_to(R)) for n in excluded])
 (D/'landing-paths.txt').write_text('\n'.join(listing)+'\n')
 (D/'SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['path']}\n" for r in rows)+f"{hashlib.sha256((D/'manifest.json').read_bytes()).hexdigest()}  {(D/'manifest.json').relative_to(R)}\n")
 print(json.dumps({'payload':len(rows),'landing':len(listing),'manifest_sha256':hashlib.sha256((D/'manifest.json').read_bytes()).hexdigest()}))
if __name__=='__main__':main()
