#!/usr/bin/env python3
"""Fetch SHA-deduplicated read-only ELF snapshot; package bytes may satisfy reads."""
import concurrent.futures, hashlib,json,shutil,subprocess,sys
from pathlib import Path
from collect import HERE,ROOT,hdc
sys.path.insert(0,str(ROOT/'scripts/lab'))
from native_gate_common import Package,sha256
from native_needed_gate import parse_dynamic
import lab_paths
U5=lab_paths.workspaces()/'westlake-generation-n4-order-216b68fb'
N5=lab_paths.workspaces()/'westlake-generation-n5-6d001bb8'
def main():
 rows=json.loads((HERE/'inventory.json').read_text())['rows'];cache=HERE/'elf';cache.mkdir(exist_ok=True)
 known={}
 for p in [U5,N5]:
  for name,digest in json.loads((p/'package.json').read_text())['files'].items():
   if '.so' in name:known[digest]=p/name
 unique={r['sha256']:r for r in rows}
 def fetch(item):
  digest,row=item;dest=cache/digest
  if not dest.exists():
   if digest in known:shutil.copyfile(known[digest],dest)
   else:hdc(['file','recv',row['target'],str(dest)])
  assert sha256(dest)==digest,(row['target'],'SHA mismatch')
  data=dest.read_bytes()[:20]
  if data[:6]!=b'\x7fELF\x02\x01' or int.from_bytes(data[18:20],'little')!=183:return digest,dict(error='not AArch64 ELF')
  p=subprocess.run([shutil.which('llvm-readelf'),'-d','--wide',str(dest)],capture_output=True,text=True,check=True)
  assert not p.stderr.strip(),p.stderr
  return digest,dict(**parse_dynamic(p.stdout),readelf=p.stdout)
 metadata={};failures=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  jobs={pool.submit(fetch,item):item for item in unique.items()}
  for number,f in enumerate(concurrent.futures.as_completed(jobs),1):
   try:k,v=f.result();metadata[k]=v
   except Exception as e:failures.append(dict(record=jobs[f][1],error=str(e)))
   if number%50==0:print(f'{number}/{len(unique)} unique files; errors={len(failures)}',flush=True)
 (HERE/'metadata.json').write_text(json.dumps(dict(files=metadata,failures=failures),indent=2)+'\n')
 (HERE/'snapshot.json').write_text(json.dumps([dict(**r,metadata=metadata.get(r['sha256'])) for r in rows],indent=2)+'\n')
 print(f'complete rows={len(rows)} unique={len(unique)} failures={len(failures)}',flush=True)
 assert not failures
if __name__=='__main__':main()
