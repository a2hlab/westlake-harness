#!/usr/bin/env python3
"""Preserve G28 restoration bytes and verify actual recorded direct/parent hashes."""
import argparse,json,re,subprocess
from pathlib import Path
from inspect_inputs import sha,save
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--workspaces',type=Path,required=True);a=p.parse_args();w=a.workspaces.resolve();c=Path.home()/'.local/share/westlake/commercial-game-20261021';cl=c/'g28-window01/closure';b=json.loads((D/'baseline-319.json').read_text());r=json.loads((cl/'results.json').read_text());parsed={}
def alias(x):return str(x).replace(str(c),'$COMMERCIAL').replace(str(w),'$WORKSPACES')
files=[]
for side in ['direct','parent']:
 observed={}
 for f in sorted(cl.glob(side+'-*.txt')):
  files.append(f)
  for line in f.read_text().splitlines():
   m=re.fullmatch(r'([a-f0-9]{64})\s+(/\S+)',line)
   if m:
    target=m[2].replace('/proc/'+str(r['parent_pid'])+'/root','',1) if side=='parent' else m[2]
    assert target not in observed or observed[target]==m[1];observed[target]=m[1]
 assert observed==b,side;parsed[side]=len(observed)
boat={}
for line in (cl/'boat-sha.txt').read_text().splitlines():
 m=re.fullmatch(r'([a-f0-9]{64})\s+(/\S+)',line)
 if m:boat[m[2]]=m[1]
assert len(boat)==3;files.extend([cl/'boat-sha.txt',cl/'results.json'])
source=w/'westlake-harness-t37-peer/benchmark/2026-10-21-commercial-game/native-route-admission/.private/assembly-01/baseline';dest=D/'.private/recovery-01';assert not dest.exists()
argv=['/bin/cp','-cR',str(source),str(dest)];save(D/'.private/recovery-copy.argv.json',argv)
with (D/'.private/recovery-copy.stdout').open('wb') as o,(D/'.private/recovery-copy.stderr').open('wb') as e:rc=subprocess.run(argv,stdout=o,stderr=e).returncode
(D/'.private/recovery-copy.rc').write_text(str(rc)+'\n');assert rc==0
for n in ['bundle.json','native/package.json','native/native-checks/scan-manifest.json','native/native-checks/native-gates.json']:assert sha(dest/n)==sha(source/n)
save(D/'recovery-binding.json',{'status':'HISTORICAL_G28_RESTORATION_VERIFIED','direct':parsed['direct'],'parent':parsed['parent'],'parent_pid':r['parent_pid'],'parent_birth':r['parent_birth'],'boot':r['boot'],'boat3':boat,'recovery_copy':alias(dest),'bundle_sha256':sha(dest/'bundle.json'),'native_manifest_sha256':sha(dest/'native/package.json'),'fresh_for_G32':False,'source_files':[{'path':alias(f),'sha256':sha(f),'bytes':f.stat().st_size} for f in files]})
print(json.dumps({'direct':parsed['direct'],'parent':parsed['parent'],'boat':len(boat),'copy_rc':rc}))
