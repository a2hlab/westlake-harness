#!/usr/bin/env python3
"""Packaging verification only: no assembly, gate, build, device or signature action."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
WORKSPACES=HERE.parents[4]
def sha(data):return hashlib.sha256(data).hexdigest()
def read(p):return json.loads(p.read_text())
def resolve(s):return Path(s.replace('$WORKSPACES',str(WORKSPACES)).replace('$HOME',str(Path.home())))
def main():
 idx=read(HERE/'retained-originals.json');entries={r['v1_path']:r for r in idx['files']};assert len(entries)==62
 for name,r in entries.items():
  raw=resolve(r['private_copy']).read_bytes();assert sha(raw)==r['sha256'] and len(raw)==r['bytes'],name
  assert sha((HERE.parent/name).read_bytes())==r['sha256'],name
 assert sum(r['stderr_content'] for r in entries.values())==10
 assert not any('stderr' in p.name for p in HERE.iterdir() if p.is_file())
 kept=['results.json','source-rebinding.json','source-matrix.json','target-matrix.json','write-matrix.json','native-review.unsigned.json','static-review.unsigned.json','input-pins.json']
 for name in kept:assert sha((HERE/name).read_bytes())==entries[name]['sha256']
 assert sha((HERE/'admission-report.v1.md').read_bytes())==entries['README.md']['sha256']
 d=read(HERE/'review-matrix.compact.json');fields=set(d['reference_fields']);values=d['definitions']
 for h,v in values.items():assert sha(json.dumps(v,sort_keys=True,separators=(',',':')).encode())==h
 rows=[{(k[:-4] if k.endswith('_ref') and k[:-4] in fields else k):(values[v] if k.endswith('_ref') and k[:-4] in fields else v) for k,v in row.items()} for row in d['rows']]
 raw=(json.dumps(rows,indent=2)+'\n').encode();assert sha(raw)==d['original_sha256']==entries['review-matrix.json']['sha256'];assert len(rows)==318
 native=read(HERE/'native-review.unsigned.json');assert len(native['items'])==318 and all(x['signature'] is None and x['approved_at'] is None for x in native['items'])
 static=read(HERE/'static-review.unsigned.json');assert len(static['items'])==5 and all(x['signature'] is None for x in static['items'])
 sums=HERE/'SHA256SUMS'
 if sums.exists():
  for line in sums.read_text().splitlines():
   h,n=line.split('  ',1);assert sha((HERE/n).read_bytes())==h,n
 print(json.dumps({'status':'PASS','scope':'packaging only','fixed_v1_files_unchanged':62,'stderr_files_indexed_only':10,'matrix_rows_losslessly_restored':318,'unsigned_native_items_unchanged':318,'unsigned_static_rows_unchanged':5,'assembly_modified':False,'gate_runs':0,'builds':0,'device_calls':0,'signatures_supplied':False}))
if __name__=='__main__':main()
