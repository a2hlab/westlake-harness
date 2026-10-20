#!/usr/bin/env python3
"""Verify actual host logs and source/binary pins; never writes build receipts."""
import argparse,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
CASES=['valid','wrong_caller','wrong_lock','wrong_unlock','wrong_geometry','rgb','unknown','geometry_failure','unmap_failure','flush_failure','alloc_failure','format_refuse','precheck_failure','abort_failure','owner_release_failure']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(v,m):
 if not v:raise ValueError(m)
def check(out,source=HERE):
 out=Path(out);r=json.loads((out/'receipt.json').read_text());require(r['status']=='HOST_ONLY','host status')
 required=['00-frozen','01-compiler','10-core-build','11-core-test','20-route-build']+['21-route-'+x for x in CASES]
 require([x['name'] for x in r['steps']]==required,'exact stages')
 for row in r['steps']:
  n=row['name'];require(row['rc']==0 and (out/(n+'.rc')).read_text().strip()=='0','nonzero '+n)
  require(json.loads((out/(n+'.argv.json')).read_text()),'missing argv')
  require((out/(n+'.stdout')).is_file() and (out/(n+'.stderr')).is_file(),'raw logs missing')
  if n=='11-core-test':require('PASS 34 actual C cases' in (out/(n+'.stdout')).read_text(),'actual core count')
  if n.startswith('21-'):require('PASS ' in (out/(n+'.stdout')).read_text(),'missing actual test result')
 before=json.loads((out/'sources-before.json').read_text());require({x['path']:x['sha256'] for x in before}=={x['path']:x['sha256'] for x in r['sources']},'source drift in build')
 for row in r['sources']:
  p=(source/row['path']).resolve();require(p.is_relative_to(source.resolve()),'source escape');require(sha(p)==row['sha256'],'source drift '+row['path'])
 require({x['name'] for x in r['binaries']}=={'test_yv12','test_route'},'binary list')
 for row in r['binaries']:require(sha(out/row['name'])==row['sha256'],'binary drift')
 return {'status':'PASS_HOST_RECEIPT_ONLY','core_cases':34,'route_scenarios':15,'device_calls':0,'production':'WAIT_T27_SINGLE_AGGREGATION','playback':'UNKNOWN'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--source',type=Path,default=HERE);a=p.parse_args();print(json.dumps(check(a.out,a.source),indent=2))
