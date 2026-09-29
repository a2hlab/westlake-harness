#!/usr/bin/env python3
"""Keep machine tables reproducible and store large text evidence as gzip."""
import gzip,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent

def main():
    import json
    private_keys={r['key'] for r in json.loads((HERE/'v3/classes/cohort.json').read_text())['apps']}
    ignore=HERE/'.gitignore';lines=ignore.read_text().splitlines();count=0
    for p in sorted((HERE/'v3').rglob('*')):
        if not p.is_file() or p.suffix=='.gz' or '__pycache__' in p.parts:continue
        if p.parent.name=='classes' and p.name.removesuffix('.json') in private_keys:continue
        if p.parent.name=='evidence' and p.name.startswith('reachability-') and p.parent.parent.name=='classes':continue
        if p.stat().st_size>1000000:
            raw=p.read_bytes();z=Path(str(p)+'.gz')
            if not z.exists() or gzip.decompress(z.read_bytes())!=raw:z.write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
            item='/'+str(p.relative_to(HERE))
            if item not in lines:lines.append(item)
            count+=1
    ignore.write_text('\n'.join(lines)+'\n')
    manifest=[]
    for p in sorted((HERE/'v3').rglob('*')):
        if not p.is_file() or p.name=='SHA256SUMS' or '__pycache__' in p.parts:continue
        if '/'+str(p.relative_to(HERE)) in lines:continue
        manifest.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(HERE/'v3')))
    (HERE/'v3/SHA256SUMS').write_text('\n'.join(manifest)+'\n');print('gzip text files:',count,'manifest entries:',len(manifest))
if __name__=='__main__':main()
