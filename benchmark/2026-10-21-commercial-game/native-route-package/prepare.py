#!/usr/bin/env python3
"""G20 clone/rebind input pattern, using original main U7 prepare. No devices/builds."""
import argparse,hashlib,json,subprocess,sys,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
HOST='ee5649f2778430e1c997f4bb2d4d4f42f53a46208b4a1b1bbaca185ddf401887'
ANL='640b3c87e2f0f86d31b7defbd8b892515636afa61dcbbab5030d422ec1fb7d86'
POLICY='878c7019b1b78c8affbf9808d69fdc8478554273fe5d06d499b6775b7d004f23'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():p.chmod(p.stat().st_mode|0o200)
 p.write_text(json.dumps(d,indent=2)+'\n')
def clone(src,dst):subprocess.run(['/bin/cp','-cR',str(src),str(dst)],check=True)
def put(src,dst):
 dst.chmod(dst.stat().st_mode|0o200);shutil.copyfile(src,dst)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--main',type=Path,required=True);ap.add_argument('--commercial',type=Path,required=True);ap.add_argument('--g26',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 a.main=a.main.resolve();a.commercial=a.commercial.resolve();a.g26=a.g26.resolve();out=a.out.resolve()
 sys.path.insert(0,str(a.main/'scripts/lab'));import u7_executor as u7
 def portable(x):
  if isinstance(x,dict):return {k:portable(v) for k,v in x.items()}
  if isinstance(x,list):return [portable(v) for v in x]
  if isinstance(x,str):return x.replace(str(a.commercial),'$COMMERCIAL').replace(str(a.main.parent),'$WORKSPACES')
  return x
 origin=a.commercial/'g21-rollout-01';journal=json.loads((a.commercial/'g24-window02/apply.json').read_text());baseline=journal['plan']['baseline'];assert len(baseline)==319
 closure=json.loads((a.commercial/'g24-window02/closure/runtime-restored.json').read_text());assert closure['baseline_all_equal'] and closure['baseline_targets']==319 and closure['boat3_equal']
 hr=a.g26/'.private/host-candidate-01/receipt.json';ar=a.g26/'.private/anl-production-01/receipt.json'
 h=json.loads(hr.read_text())['artifact'];an=json.loads(ar.read_text());an=next(x['artifact'] for x in an['builds'] if x['variant']=='candidate')
 for v,pin in [(h,HOST),(an,ANL)]:assert v['sha256']==pin and sha(v['path'])==pin and Path(v['path']).stat().st_size==v['bytes']
 assert not out.exists(),'fresh assembly required';out.mkdir(parents=True)
 clone(origin/'baseline',out/'baseline');clone(origin/'candidate',out/'candidate')
 first=[]
 for target,digest in baseline.items():
  role='host' if target=='/system/bin/appspawn-x' else ('anl' if target.endswith('/libapp_native_loader.so') else ('policy' if target.endswith('/libnativeloader.so') else None))
  if role and role!='host' and '/route-a/' in target and '/74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac/' not in target:role=None
  if role:first.append({'target':target,'role':role,'baseline_sha256':digest,'candidate_sha256':{'host':HOST,'anl':ANL,'policy':POLICY}[role]})
 assert len(first)==5 and [sum(x['role']==r for x in first) for r in ['host','anl','policy']]==[1,2,2]
 save(HERE/'five-targets.json',first);save(HERE/'baseline-319.json',baseline)
 changed=[]
 for side in ['baseline','candidate']:
  root=out/side;b=json.loads((root/'bundle.json').read_text());m=json.loads((root/'native/package.json').read_text())
  if side=='candidate':
   for t,row in u7.effective_files(m).items():
    entry=next((r for r in first if r['target']==t),None)
    if not entry:continue
    if entry['role'] in ['host','anl']:
     artifact=h if entry['role']=='host' else an;put(Path(artifact['path']),root/'native'/row['source'])
     m['files'][row['source']]=entry['candidate_sha256']
     if t in m['live_hashes']:m['live_hashes'][t]=entry['candidate_sha256']
    assert sha(root/'native'/row['source'])==entry['candidate_sha256'];changed.append(t)
  m['rollout_ready']=False;m['rollout_blocker']='G27 unsigned; G26 independent acceptance, current N1/N2 admission and fresh binding pending'
  save(root/'native/package.json',m);b['native']['manifest']['sha256']=sha(root/'native/package.json')
  gpath=root/'native/native-checks/native-gates.json';g=json.loads(gpath.read_text());g['package_manifest_sha256']=sha(root/'native/package.json')
  # Artifact identity only. Old source profiles/namespace assumptions are not relabelled as approved.
  owner=g['namespaces']['owner_artifact'];owner['sha256']=sha(root/'native'/owner['path']);save(gpath,g)
  b['rollout_ready']=False;b['rollout_blocker']=m['rollout_blocker']
  save(root/'g27-static-policy.unsigned.json',{'jars':{},'native':{}})
  b['static_checks']['policy']={'source':'g27-static-policy.unsigned.json','sha256':sha(root/'g27-static-policy.unsigned.json')}
  if side=='candidate':
   b['static_checks']['baseline_bundle_sha256']=sha(out/'baseline/bundle.json');b['image_gate_reference']['baseline_bundle_sha256']=sha(out/'baseline/bundle.json')
  save(root/'bundle.json',b)
 plan=u7.prepare(out/'candidate',out/'baseline/native');assert plan['baseline']==baseline and len(plan['expected'])==319 and not plan['additions'] and not plan['rollout_ready']
 diff=sorted(t for t,v in plan['expected'].items() if baseline[t]!=v);assert diff==sorted(x['target'] for x in first)
 for x in first:assert plan['expected'][x['target']]==x['candidate_sha256']
 save(out/'transaction-plan.raw.json',plan);save(HERE/'transaction-plan.json',portable(plan))
 inputs=[hr,ar,a.commercial/'g24-window02/apply.json',a.commercial/'g24-window02/closure/runtime-restored.json',a.commercial/'g24-window02/closure/boat3.txt',a.main/'scripts/lab/u7_executor.py',a.main/'scripts/lab/deploy_generation.py',a.main/'benchmark/2026-10-21-commercial-game/gles-transaction-package/assemble.py']
 save(HERE/'source-index.json',[{'path':portable(str(p)),'sha256':sha(p),'bytes':p.stat().st_size} for p in inputs])
 save(HERE/'results.json',{'status':'ASSEMBLED_UNSIGNED_G26_REVIEW_PENDING','assembly':portable(str(out)),'baseline_targets':319,'candidate_targets':319,'logical_changes':5,'planned_writes':len(plan['changes']),'same_sha_writes':sum(baseline[x['target']]==x['sha256'] for x in plan['changes']),'rollout_ready':False,'deployable':False,'g26_independent_accepted':False,'device_calls':0,'builds':0,'owned_state_created':False,'boat3_preserved':True,'baseline_bundle_sha256':sha(out/'baseline/bundle.json'),'candidate_bundle_sha256':sha(out/'candidate/bundle.json'),'baseline_native_sha256':sha(out/'baseline/native/package.json'),'candidate_native_sha256':sha(out/'candidate/native/package.json'),'pending':['G26 final independent acceptance','current N1 source/profile binding and N2 exact unsigned exception review','new outer signatures; no G24 exception reused','fresh read-only baseline and window authorization'],'start_binding':'U7 _bind_start uses explicit candidate/baseline manifest and host; Deployment.start checks supplied digest; no old-host constant found','static_profile_status':'old native profiles retained as historical assumptions for original gate rejection, not approved current G26 source attestation'})
 print(json.dumps({'status':'ASSEMBLED_UNSIGNED','targets':319,'logical_changes':5,'planned_writes':len(plan['changes']),'rollout_ready':False}))
if __name__=='__main__':main()
