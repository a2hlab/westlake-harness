#!/usr/bin/env python3
"""Verify delivered bytes and direct local recipe dependencies; never build."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
def check():
 d=json.loads((ROOT/'sources.lock.json').read_text())
 for r in d['files']:
  p=REPO/r['path'];raw=p.read_bytes()
  assert hashlib.sha256(raw).hexdigest()==r['sha256'],r['path']
  assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==r['git_blob'],r['path']
 for name in ['build_bionic_shim.sh','build_missing_natives.sh']:
  subprocess.run(['bash','-n',str(ROOT/'westlake/tools'/name)],check=True)
 for rel in ['third_party/jni/jni.h','third_party/aaudio/aaudio/AAudio.h','framework/webview-shim/webview_bionic_shim.map','framework/javacore-shim/libwl_missing_natives.map']:
  assert (ROOT/'westlake'/rel).is_file(),rel
 rows=json.loads((ROOT/'api-resolutions.json').read_text())['rows']
 for row in rows:
  for entry in row['source_entry']:
   p=REPO/entry['path']
   # External host source is owned by its separate already landed package.
   if not p.exists():
    import os
    main=Path(os.environ.get('API_SOURCE_MAIN',str(REPO.parent/'westlake-harness')))
    p=main/entry['path']
   assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'],p
   assert entry['symbol'] in p.read_text(),entry['symbol']
 return {'status':'PASS','exact_git_blobs':len(d['files']),'api_mappings':len(rows),'shell_syntax':2,'device_calls':0,'builds':0,'historical_binary_equivalence':False}
if __name__=='__main__':print(json.dumps(check(),indent=2))
