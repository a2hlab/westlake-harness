#!/usr/bin/env python3
"""Prepare three packages from boot-matched local ledgers. No board writes/IO."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,subprocess,sys
R=Path(__file__).resolve().parent; REPO=R.parents[1]
OUT=R/'board-packages';OUT.mkdir(exist_ok=True)
STATE=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-state')
SERIALS=[('5ea','5ea34a4500000000000000001123012c','51812b02-ec64-4d36-821c-ffd94531fb45','a0ed5c4fedd952762256a24ab7801deb3ad6e696a0204853ce5000316336d173'),('5cd','5cd1e3dd00000000000000000923012c','a42f2d6c-d29d-40aa-8145-51b4f85d0187','a5cbd8d77ad7cb1592db5d64f9ec1f7ce7da9732fdbe8c4b180c8fa1ea95c2e7'),('61b','61b0657200000000000000000324012c','6fd44228-d33e-4f0e-9bf9-9a34842c72bf','a0ed5c4fedd952762256a24ab7801deb3ad6e696a0204853ce5000316336d173')]
TARGET='/system/android/lib64/liboh_android_runtime.so'
RUNTIME='32dfac830320394d0b62781afcde68537d3b5fff372b5170d7a53baa069013b7'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('graphics_deployer',REPO/'scripts/lab/deploy_generation.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
rows=[]
for prefix,serial,boot,jar in SERIALS:
 ledger=STATE/serial/(boot+'-74d1d6d48210.json');raw=ledger.read_bytes();state=json.loads(raw)
 assert state['boot_id']==boot and state['status']=='active_verified'
 base=Path(state['package_path']);assert sha(base/'package.json')==state['package_sha256']
 old=d.load_package(base)
 out=Path('/Users/zhaoyue/orca/workspaces')/('westlake-runtime-graphics-session-sync-32dfac83-'+prefix)
 if not out.exists():
  subprocess.run([sys.executable,str(R/'prepare_for_base.py'),str(base),str(out)],check=True)
 new=d.load_package(out);source=d.validate_replacement(old,new,TARGET)
 assert new['live_hashes'][TARGET]==RUNTIME
 # Pin the ledger again after copying; a concurrent native change invalidates preparation.
 assert ledger.read_bytes()==raw,'active ledger changed during preparation'
 run=subprocess.run([sys.executable,str(REPO/'scripts/lab/deploy_generation.py'),serial,str(out),'--replace',TARGET,'--dry-run','--lane','claude'],capture_output=True,text=True,check=True)
 dry=json.loads(run.stdout);assert dry['passed'] and dry['device_io'] is False
 (OUT/(prefix+'-dry-run.json')).write_text(run.stdout)
 row={'board':prefix,'serial':serial,'boot_id_readonly_observed':boot,'ledger':str(ledger),'ledger_sha256':hashlib.sha256(raw).hexdigest(),'ledger_status':state['status'],'single_replacement_count':len(state.get('single_replacements',[])),'base':str(base),'base_package_sha256':state['package_sha256'],'package':str(out),'package_sha256':sha(out/'package.json'),'changed_payloads':[k for k in old['files'].keys()|new['files'].keys() if old['files'].get(k)!=new['files'].get(k)],'changed_live_targets':[k for k in old['live_hashes'].keys()|new['live_hashes'].keys() if old['live_hashes'].get(k)!=new['live_hashes'].get(k)],'old_runtime_sha256':old['live_hashes'][TARGET],'new_runtime_sha256':RUNTIME,'jar_readonly_observed':jar,'package_jar_sha256':old['live_hashes']['/system/android/framework/oh-adapter-runtime.jar'],'dry_run':dry,'device_writes':False}
 assert row['changed_payloads']==[source] and row['changed_live_targets']==[TARGET]
 rows.append(row)
(OUT/'results.json').write_text(json.dumps({'prepared_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'device_writes':False,'boot_and_jar_observation':'Read-only hdc cat boot_id + sha256sum before packaging; current JAR must be recaptured at deployment.','boards':rows},indent=2)+'\n')
print(json.dumps([{k:x[k] for k in ['board','package','package_sha256']} for x in rows],indent=2))
