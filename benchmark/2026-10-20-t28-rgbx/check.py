#!/usr/bin/env python3
"""Read actual receipts and replay the selected real C binary; no device actions."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
os.chdir(P.parents[1]) # receipts recorded commands from the repository root
p=argparse.ArgumentParser();p.add_argument('--suite',choices=['route','regression','failures','concurrency','build'],required=True);a=p.parse_args()
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
h=Path(os.environ['T28_HOST_OUT']);r=json.loads((h/'receipt.json').read_text());assert r['status']=='HOST_ONLY_PASS'
for f,v in r['inputs'].items():assert sha(Path(f))==v,'changed source '+f
for c in r['commands']:
 n=c['name'];assert c['rc']==0 and (h/(n+'.rc')).read_text().strip()=='0';assert (h/(n+'.stdout')).exists() and (h/(n+'.stderr')).exists()
if a.suite=='build':
 b=Path(os.environ['T28_BUILD_OUT']);d=json.loads((b/'receipt.json').read_text());assert d['status']=='OFFLINE_CANDIDATE_NOT_DEPLOYMENT_AUTHORIZED'
 for f,v in d['inputs'].items():assert sha(Path(f))==v['sha256'],'changed build input '+f
 for f,v in d['outputs'].items():assert sha(b/f)==v['sha256'] and (b/f).stat().st_size==v['bytes']
 for c in d['commands']:
  n=c['name'];assert c['rc']==0 and (b/'raw'/(n+'.rc')).read_text().strip()=='0'
 abi=json.loads((b/'abi.json').read_text());assert all(abi[k]==[] for k in ['removed','added','drift','consumer_breaks'])
 assert d['outputs']['baseline.so']['sha256']=='fc58cec5c7a445a28ed0c0e3ec44d486f16f0921afe8ef4b6974bd96ca9574e9'
 print('PASS actual offline build/ABI receipts; human runtime review PENDING')
else:
 cases={'route':['rgbx','rgbx_format0','rgbx_geometry_failure','wrong_caller','wrong_lock','wrong_unlock','wrong_geometry'],'regression':['valid','rgb','unknown'],'failures':['rgbx_bad_format','rgbx_precheck','rgbx_unmap','rgbx_flush']}
 cmds=[[str(h/'test_rgbx')]] if a.suite=='concurrency' else [[str(h/'test_route'),x] for x in cases[a.suite]]
 for cmd in cmds:subprocess.run(cmd,check=True)
