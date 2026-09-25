"""Archive all trial evidence losslessly; keep large logs gzip-compressed."""
import argparse,gzip,hashlib,json,shutil
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);args=ap.parse_args()
dst=Path(__file__).resolve().parent/'device-evidence';dst.mkdir(exist_ok=True)
manifest=[]
for p in sorted(args.source.rglob('*')):
 if not p.is_file() or '__pycache__' in p.parts or p.name in ('launch-inputs.tar','launch-inputs.tar.gz'):continue
 rel=p.relative_to(args.source)
 # Framework manifests suffice; no executable payloads copied.
 data=p.read_bytes();compressed=len(data)>1000000 and p.suffix not in ('.jpeg','.png','.gz')
 target=dst/(str(rel)+('.gz' if compressed else ''));target.parent.mkdir(parents=True,exist_ok=True)
 target.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
 manifest.append(dict(path=str(target.relative_to(dst)),original=str(rel),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),stored_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),gzip=compressed))
(dst.parent/'device-evidence-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(len(manifest),'archived files')
