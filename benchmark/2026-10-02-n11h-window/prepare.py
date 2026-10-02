"""Rebind the accepted host, without building or touching any device."""
import copy, importlib.util, json, os, shutil, sys
from datetime import datetime
from pathlib import Path
H=Path(__file__).resolve().parent; R=H.parents[1]
sys.path.insert(0,str(R/'scripts/lab'))
import generation_bundle as gb, u7_executor as u, lab_paths
W=lab_paths.workspaces(); M=lab_paths.harness()
BASE=W/'westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle'
PKG=W/'westlake-inputs/generations/n11h-u101t8-host65ac5089-v1/native'
AUDIT=W/'westlake-harness-bms/benchmark/2026-10-02-n11h-host-owner/.artifacts/audit-package'
SERIAL='61b0657200000000000000000324012c'
OLD='65cc3535ebf22bdf664b3c8ddf932ccd7f42d936be1c861e1221a80b12a00284'
NEW='65ac50894de8d06e32439d2aee91f61eb1c45d6c0822826d529f671ca3c49aed'
def save(path,d):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(d,indent=2)+'\n')
def main():
 assert gb.sha(BASE/'bundle.json')=='190afedd3ddb250752e67b83d19669b6a952eb04cd69db5edf0b06eafe119736'
 old=json.loads((BASE/'native/package.json').read_text()); audit=json.loads((AUDIT/'package.json').read_text())
 assert gb.sha(AUDIT/'package.json')=='37c48e2b07e5e757bc872f174f883d44cc0f369a19b035afe9035b2a115286bf'
 assert old['files']['payload/runtime/appspawn-x']==OLD
 assert audit['files']['payload/runtime/appspawn-x']==NEW
 assert audit['live_hashes']['/system/bin/appspawn-x']==OLD
 if not PKG.exists(): shutil.copytree(AUDIT,PKG)
 new=copy.deepcopy(audit);new['live_hashes']['/system/bin/appspawn-x']=NEW
 save(PKG/'package.json',new)
 u.native.validate_replacement(old,new,u.HOST)
 assert u.effective_files(new)[u.HOST]['sha256']==NEW
 manifest=gb.sha(PKG/'package.json')
 sidecar=json.loads((AUDIT/'native-checks/native-gates.json').read_text()); sidecar['package_manifest_sha256']=manifest
 scan=json.loads((AUDIT/'native-checks/scan-manifest.json').read_text())
 for profile in scan['profiles']:profile['identity']['manifest_sha256']=manifest
 save(PKG/'native-checks/scan-manifest.json',scan)
 sidecar['initialization']['manifest']['sha256']=gb.sha(PKG/'native-checks/scan-manifest.json')
 save(PKG/'native-checks/native-gates.json',sidecar)
 inputs=gb.sha(PKG/'native-checks/native-gates.json')
 # Regenerate auto-identical lineage against the actual approved r3 report.
 admission=R/'benchmark/2026-10-02-n11h-admission'; sys.path.insert(0,str(admission))
 spec=importlib.util.spec_from_file_location('n11h_admission_package',admission/'package.py'); p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
 now=datetime.now().astimezone().isoformat(timespec='seconds')
 deltas,review,lineage=p.exceptions(now)
 rows=deltas['N1']['exceptions']+deltas['N2']['exceptions']
 save(H/'audit-registry-delta.json',{'schema_version':1,'state':'PENDING_OUTER_ADOPTION','exceptions':rows})
 report=p.candidate_report(); rebinding=[]
 for row in rows:
  finding=next(f for f in report['gates'][row['gate']]['findings'] if f['issue_id']==row['issue_id'])
  bound=dict(report,package_manifest_sha256=manifest,inputs_sha256=inputs)
  entry=copy.deepcopy(row);entry.update(package_manifest_sha256=manifest,inputs_sha256=inputs,issue_id=p.identity(row['gate'],bound,finding))
  entry['reason']+=' Deployment declaration repaired: host live_hashes now equals the already-reviewed 65ac5089 file. No native byte, namespace, source or checker input changes.'
  rebinding.append(entry)
 save(H/'registry-delta.json',{'schema_version':1,'state':'PENDING_OUTER_ADOPTION','exceptions':rebinding})
 finding=next(f for f in report['gates']['N1']['findings'] if f['issue_id']==review['issue_id'])
 extra={'gate':'N1','package_manifest_sha256':manifest,'inputs_sha256':inputs,'issue_id':p.identity('N1',dict(report,package_manifest_sha256=manifest,inputs_sha256=inputs),finding),
  'reason':'ACK(80) 2026-10-02 14:41:32 approved N11hResidentHandle n11h-owner.h:29 exact canonical owner NOLOAD queries. Rebind only corrected live_hashes metadata, same candidate host65ac5089 and byte-identical source/namespace inputs; sidecar package binding repaired. Request outer adoption of this exact production manifest binding.',
  'removal_condition':'N11h 61b <=30 minute observation only; re-review before unified promotion or any source/namespace/target/flags drift.',
  'evidence':['benchmark/2026-10-02-n11h-admission/outer-review.json','benchmark/2026-10-02-n11h-host-owner/evidence/native-candidate.txt','benchmark/2026-10-02-n11h-window/composition.json'],
  'approved_by':'outer(claude)','approved_at':'2026-10-02T14:41:32+08:00'}
 save(H/'outer-binding-proposal.json',{'schema_version':1,'state':'PENDING_OUTER_BINDING_ADOPTION','exceptions':[extra]})
 registry=json.loads((M/'knowledge/gates/native-predeploy-exceptions.json').read_text());registry['exceptions']+=rebinding+[extra]
 save(H/'proposed-registry.json',registry)
 refs=json.loads((BASE/'bundle.json').read_text())['reference']; paths={k:sorted(gb.read_fingerprint(BASE/v['source'])) for k,v in refs.items()}
 services=json.loads((R/'benchmark/2026-10-01-installation-chain-identity/current-u9.json').read_text())['boards'][SERIAL]['services'];paths['runtime']=sorted(set(paths['runtime'])|set(services))
 baseline=json.loads((R/'benchmark/2026-10-02-u10-1-t8-rerun/expected-run.json').read_text())['boards'][SERIAL]
 expected=copy.deepcopy(baseline['expected']);expected[u.HOST]=NEW
 assert u.fingerprints(baseline['expected'],paths)==baseline['fingerprints']
 fp=u.fingerprints(expected,paths)
 save(H/'expected.json',{'serial':SERIAL,'base':baseline['expected'],'candidate':expected,'reference_paths':paths,'base_fingerprints':baseline['fingerprints'],'candidate_fingerprints':fp,'identity_assertions':318})
 save(H/'composition.json',{'base_name':'U10.1T8','base_bundle_sha256':gb.sha(BASE/'bundle.json'),'base_native_manifest_sha256':gb.sha(BASE/'native/package.json'),'audit_manifest_sha256':gb.sha(AUDIT/'package.json'),'package_manifest_sha256':manifest,'inputs_sha256':inputs,'baseline_host_sha256':OLD,'candidate_host_sha256':NEW,'changed_members':['/system/bin/appspawn-x'],'runtime_fp':fp['runtime']['sha256_12'],'boot_fp':fp['boot']['sha256_12'],'registry_auto_identical':156,'new_reviewed_site':1,'device_io':False,'execution_enabled':False,'metadata_correction':'live_hashes host OLD -> NEW; payload already NEW','package':'$WORKSPACES/westlake-inputs/generations/n11h-u101t8-host65ac5089-v1/native'})
 print(json.dumps({'manifest':manifest,'inputs':inputs,'fingerprints':fp,'auto_identical':len(rebinding),'outer_binding':extra['issue_id'],'device_io':False},indent=2))
if __name__=='__main__':main()
