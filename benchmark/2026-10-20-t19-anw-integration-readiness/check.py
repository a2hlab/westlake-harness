import hashlib,json,re,os
from pathlib import Path
here=Path(__file__).resolve().parent;repo=Path(os.environ.get("T19_SOURCE_REPO",str(here.parents[1]))).resolve()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,x in json.loads((here/'source-index.json').read_text()).items():
 p=repo/name;assert p.is_file() and p.stat().st_size==x['bytes'] and sha(p)==x['sha256'],name
old=repo/'benchmark/2026-10-19-toutiao-video-playback/static/r10-window-contract-review/bridge-unwrap.stdout.txt'
words=lambda p:re.findall(rb'^\s*[0-9a-f]+:\s+([0-9a-f]{8})\s',p.read_bytes(),re.M)
a,b=words(old),words(here/'dca530-unwrap.llvm.txt');assert a==b and len(a)==15
r=json.loads((here/'results.json').read_text());assert r['unwrap']['trusted_pointer_validation'] is False
for x in r['log']['excerpts']:
 p=here/x['path'];assert sha(p)==x['sha256'] and p.stat().st_size==x['bytes'];assert x['source_offset']==r['log']['source_start']+x['selection_offset']
assert r['device_calls']==r['builds']==r['new_REA_runs']==0
print('static input SHA/size, exact 60-byte unwrap equality and excerpt checks passed; live acceptance pending')
