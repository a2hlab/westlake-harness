"""Validate published evidence, not game compatibility. No device/network execution."""
from pathlib import Path
import hashlib,json,os,re
D=Path(__file__).resolve().parent;ROOT=D.parents[2];MAIN=Path(os.environ.get('COMMERCIAL_G02_MAIN',ROOT))
def load(n):return json.loads((D/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 refs=load('source-index.json')
 for r in refs:
  candidates=[ROOT/r['path'],MAIN/r['path']]
  if r.get('snapshot_path'):candidates.append(ROOT/r['snapshot_path'])
  assert any(p.is_file() and sha(p)==r['sha256'] and p.stat().st_size==r['bytes'] for p in candidates),r['path']
 receipts=load('receipts.json')
 for r in receipts:
  for f in r['public']:
   p=D/f['path'];assert sha(p)==f['sha256'] and p.stat().st_size==f['bytes'],p
  assert int((D/'evidence'/(r['id']+'.rc')).read_text())==r['rc']
 for name in ['manifest','xmltree','opensite','llvm-readelf','llvm-nm']:
  assert next(r for r in receipts if r['id']==name)['rc']==0,name
 s=load('smoke.json');text=(D/'evidence/manifest.stdout').read_text()
 assert "name='org.fossify.notes' versionCode='13' versionName='1.7.0'" in text
 assert "minSdkVersion:'26'" in text and "targetSdkVersion:'36'" in text
 assert s['apk_sha256']=='5a56e0e39cc488e1f3b947d3801006d3b7450ec73c67f03195c64c5fd3b6bced'
 assert s['runtime_executed'] is False
 sites=json.loads((D/'evidence/opensite.result.json').read_text());assert len(sites['binaries'])==1
 assert sites['binaries'][0]['sites']==[] and s['direct_open_sites']==0
 elf=(D/'evidence/llvm-readelf.stdout').read_text();assert 'AArch64' in elf and 'ELF64' in elf and 'DYN' in elf
 result=load('results.json');assert set(result['genshin'].values())=={'UNKNOWN'} and result['genshin_runtime']=='NOT_TESTED'
 assert result['device_calls']==result['network_calls']==result['rea_calls']==0
 rows=load('reuse-matrix.json')['rows'];assert len(rows)==11 and all(r['genshin']=='UNKNOWN' for r in rows)
 assert next(r for r in rows if r['item']=='bionic/musl signal adapter')['class'].startswith('public_reusable_candidate')
 assert any('cap/bytesPerFrame' in r['validated_scope'] for r in rows)
 assert any('FEATURE_UNSUPPORTED' in r['validated_scope'] for r in rows)
 print(json.dumps({'source_refs':len(refs),'reuse_rows':len(rows),'actual_smoke_commands':5,'rc':0,'human':'PENDING_REVIEW','genshin':'UNKNOWN'}))
if __name__=='__main__':check()
