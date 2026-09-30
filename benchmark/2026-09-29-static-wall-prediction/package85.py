#!/usr/bin/env python3
import gzip,hashlib
from pathlib import Path
from scan85 import OUT
def main():
    ignore=OUT.parent/'.gitignore';lines=ignore.read_text().splitlines()
    for item in ['/v4-r2/intermediate/']:
        if item not in lines:lines.append(item)
    for p in sorted(OUT.rglob('*')):
        if not p.is_file() or p.suffix=='.gz' or 'intermediate' in p.parts:continue
        if p.stat().st_size>1000000:
            raw=p.read_bytes();z=Path(str(p)+'.gz')
            if not z.exists() or gzip.decompress(z.read_bytes())!=raw:z.write_bytes(gzip.compress(raw,mtime=0))
            line='/'+str(p.relative_to(OUT.parent))
            if line not in lines:lines.append(line)
    ignore.write_text('\n'.join(lines)+'\n');manifest=[]
    for p in sorted(OUT.rglob('*')):
        if not p.is_file() or 'intermediate' in p.parts or p.name=='SHA256SUMS':continue
        if '/'+str(p.relative_to(OUT.parent)) in lines:continue
        manifest.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(OUT)))
    (OUT/'SHA256SUMS').write_text('\n'.join(manifest)+'\n');print('manifest',len(manifest))
if __name__=='__main__':main()
