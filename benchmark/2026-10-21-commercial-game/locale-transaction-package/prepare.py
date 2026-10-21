#!/usr/bin/env python3
"""G27 clone/rebind pattern with G28 source identities preserved. Offline only."""
import argparse,copy,json,shutil,subprocess,sys
from pathlib import Path
from inspect_inputs import sha,save,BASE
D=Path(__file__).resolve().parent
TARGET='/system/android/lib64/westlake_native/libwestlake_native_abi.so'
STATUS='ACCEPTED_FOR_OFFLINE_UNSIGNED_ASSEMBLY_ONLY'
CAND='4296f8052b6ccc130df83366717903695eba38fcde19c462ee64521414696f0b'
def require_accepted(a,receipt):
 if not a or a.get('status')!=STATUS:raise ValueError('PENDING: explicit outer fixed-candidate acceptance required')
 if a.get('replacement_target')!=TARGET or a.get('keep_public_and_flutter') is not True:raise ValueError('only the user-selected native domain ABI may change')
 if a.get('candidate_sha256')!=CAND or a.get('baseline_sha256')!=BASE:raise ValueError('accepted ABI identity drift')
 pins=a.get('pins',[])
 if len(pins)!=20 or len({x['path'] for x in pins})!=20:raise ValueError('expected exact 20 acceptance pins')
 for pin in pins:
  p=Path(pin['path'])
  if sha(p)!=pin['sha256'] or p.stat().st_size!=pin['bytes']:raise ValueError('acceptance pin drift: '+str(p))
 indexed={str(Path(x['path']).resolve()):x for x in pins}
 if str(receipt.resolve()) not in indexed:raise ValueError('receipt not pinned by outer')
 r=json.loads(receipt.read_text());o=r['outputs']['libwestlake_native_abi.so'];artifact=receipt.parent/'libwestlake_native_abi.so'
 if str(artifact.resolve()) not in indexed or o['sha256']!=CAND or sha(artifact)!=CAND or artifact.stat().st_size!=a['candidate_bytes'] or artifact.stat().st_size!=o['bytes']:raise ValueError('candidate identity drift')
 if not r['commands'] or not all(c['rc']==0 for c in r['commands']):raise ValueError('build did not finish successfully')
 if len(r['inputs'])!=55:raise ValueError('expected 55 build inputs')
 for n,h in r['inputs'].items():
  if sha(Path(n))!=h['sha256']:raise ValueError('G30 source/toolchain input drift: '+n)
 return r,artifact

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--workspaces',type=Path,required=True);ap.add_argument('--acceptance',type=Path);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();w=args.workspaces.resolve();receipt=w/'westlake-harness-t4/benchmark/2026-10-21-commercial-game/locale-abi-candidate/.private/candidate-02/receipt.json'
 acceptance=json.loads(args.acceptance.read_text()) if args.acceptance else None
 # Refusal happens before any staging directory is created.
 try:r,artifact=require_accepted(acceptance,receipt)
 except ValueError as e:print(str(e),file=sys.stderr);return 2
 source=w/'westlake-harness-t37-peer/benchmark/2026-10-21-commercial-game/native-route-admission/.private/assembly-01';out=args.out.resolve()
 assert out.is_relative_to(D/'.private'),'output must remain in this card private directory'
 assert not out.exists(),'fresh output required'
 for pin in json.loads((D/'input-pins.json').read_text()):
  path=Path(pin['path'].replace('$WORKSPACES',str(w)).replace('$HOME',str(Path.home())));assert sha(path)==pin['sha256']
 sys.dont_write_bytecode=True;sys.path.insert(0,str(w/'westlake-harness/scripts/lab'));import u7_executor as u7
 old=u7.prepare(source/'candidate',source/'baseline/native');assert len(old['baseline'])==319 and not old['rollout_ready']
 out.mkdir(parents=True)
 for side in ['baseline','candidate']:subprocess.run(['/bin/cp','-cR',str(source/side),str(out/side)],check=True)
 root=out/'candidate';native=root/'native';m=json.loads((native/'package.json').read_text());rows=u7.effective_files(m);row=rows[TARGET];assert row['sha256']==BASE
 dest=native/row['source'];dest.chmod(dest.stat().st_mode|0o200);shutil.copyfile(artifact,dest);candidate=sha(dest);m['files'][row['source']]=candidate
 if TARGET in m['live_hashes']:m['live_hashes'][TARGET]=candidate
 assert m['rollout_ready'] is False
 def write(p,v):
  if p.exists():p.chmod(p.stat().st_mode|0o200)
  save(p,v)
 write(native/'package.json',m);new_manifest=sha(native/'package.json');meta=native/'native-checks';scan=json.loads((meta/'scan-manifest.json').read_text());before=copy.deepcopy(scan)
 for profile in scan['profiles']:
  ident=profile['identity'];assert sha(native/ident['artifact'])==ident['artifact_sha256'];ident['manifest_sha256']=new_manifest;ident['package']='g32-unsigned-candidate'
 for x in scan['sources'].values():assert sha(meta/x['path'])==x['sha256']
 write(meta/'scan-manifest.json',scan)
 g=json.loads((meta/'native-gates.json').read_text());g['package_manifest_sha256']=new_manifest;g['initialization']['manifest']['sha256']=sha(meta/'scan-manifest.json')
 assert sha(native/g['namespaces']['owner_artifact']['path'])==g['namespaces']['owner_artifact']['sha256'];write(meta/'native-gates.json',g)
 # ABI build provenance is supplemental. N1's namespace/JNI profiles are not invented.
 write(meta/'g30-abi-source-binding.json',{'candidate':{'target':TARGET,'sha256':candidate},'receipt_sha256':sha(receipt),'inputs':r['inputs'],'build_commands':r['commands'],'outer_acceptance_sha256':sha(args.acceptance),'outer_acceptance_status':acceptance['status'],'accepted_evidence_pins':acceptance['pins'],'namespace_profiles_unchanged':True,'signature':None})
 b=json.loads((root/'bundle.json').read_text());b['native']['manifest']['sha256']=new_manifest;b['rollout_ready']=False
 assert b['static_checks']['baseline_bundle_sha256']==sha(out/'baseline/bundle.json')
 write(root/'g32-static-policy.unsigned.json',{'jars':{},'native':{}});b['static_checks']['policy']={'source':'g32-static-policy.unsigned.json','sha256':sha(root/'g32-static-policy.unsigned.json')};write(root/'bundle.json',b)
 plan=u7.prepare(root,out/'baseline/native');assert plan['baseline']==old['baseline'];assert {t for t in plan['expected'] if plan['expected'][t]!=old['expected'][t]}=={TARGET}
 assert plan['expected']['/system/android/lib64/libwestlake_native_abi.so']==BASE and plan['expected']['/system/android/lib64/westlake_flutter/libwestlake_native_abi.so']==BASE
 assert not plan['rollout_ready'] and not plan['additions'];save(out/'transaction-plan.raw.json',plan)
 save(out/'assembly-receipt.json',{'status':'UNSIGNED_NOT_ADMITTED','candidate_sha256':candidate,'targets':len(plan['expected']),'logical_changes':sum(plan['expected'][t]!=plan['baseline'][t] for t in plan['expected']),'planned_writes':len(plan['changes']),'unchanged_writes':sum(x['sha256']==plan['baseline'][x['target']] for x in plan['changes']),'rollout_ready':False,'source_profiles_rebound':len(scan['profiles']),'namespace_config_bytes_changed':False,'old_exceptions_inherited':0})
 print(json.dumps({'status':'UNSIGNED_NOT_ADMITTED','out':str(out),'writes':len(plan['changes'])}));return 0
if __name__=='__main__':sys.exit(main())
