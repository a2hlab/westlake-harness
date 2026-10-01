"""Assemble exactly 29 Java/image swaps over the signed U7 native package."""
import json,hashlib,subprocess,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];WS=REPO.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
stage=WS/'westlake-generation-u8-staging';base=WS/'westlake-generation-u7-executor-example';out=WS/'westlake-generation-u8-j9-t7e'
assert not out.exists()
for line in (stage/'SHA256SUMS').read_text().splitlines():
 v,n=line.split(None,1);assert sha(stage/n.lstrip('*'))==v,n
assert sha(stage/'oh-adapter-runtime-j9.jar')=='87fd463ddb82e803480a93bd76fc55d4bbb92a2261caa75c6a23cfd0f812c8be'
assert sha(stage/'adapter-mainline-stubs-t7e.jar')=='f3bcc9d7c76cb73487837d7ad92fccba3d595d313ada7403bed99c4f11c2a8c2'
subprocess.run(['/bin/cp','-Rc',str(base),str(out)],check=True);d=json.loads((out/'bundle.json').read_text())
for r in d['boot_group']['members']+[d['runtime_jar']]:
 if r['target'].endswith('oh-adapter-runtime.jar'):source=stage/'oh-adapter-runtime-j9.jar'
 elif r['target'].endswith('.jar'):source=stage/'adapter-mainline-stubs-t7e.jar'
 else:source=stage/'images'/Path(r['target']).name
 shutil.copyfile(source,out/r['source']);r['sha256']=sha(source)
oldreceipt=json.loads((base/'receipts/t7d-build-receipt.json').read_text());inputs=dict(oldreceipt['input_jars']);inputs['adapter-mainline-stubs.jar']=sha(stage/'adapter-mainline-stubs-t7e.jar')
receipt={'status':'unknown','evidence_kind':'retrospective-t7e-input-output-binding-awaiting-original-log','input_jars':inputs,'outputs':{Path(r['target']).name:r['sha256'] for r in d['boot_group']['members'] if not r['target'].endswith('.jar')},'build_command':(HERE/'evidence/t7e-embedded-command.txt').read_text().strip(),'dex2oat_sha256':'ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b','toolchain_identity_sha256':'unknown','build_log_sha256':'unknown','source_receipt':'westlake-harness-t3/benchmark/2026-10-01-j8-jar-donors/build-receipt-t7e.json','staging_sha256sums':sha(stage/'SHA256SUMS')}
save(out/'receipts/t7e-build-receipt.json',receipt);d['paired_build_receipt']={'source':'receipts/t7e-build-receipt.json','sha256':sha(out/'receipts/t7e-build-receipt.json')};d['rollout_ready']=False;d['rollout_blocker']='await complete T7e build provenance and production preflight';save(out/'bundle.json',d)
# Baseline references must describe current U7, not the underlying U5 package JAR/image.
import sys;sys.path.insert(0,str(REPO/'scripts/lab'));import u7_executor as u
old=json.loads((WS/'westlake-generation-u7-executor-example/bundle.json').read_text());_,_,expected=u.bundle.validate(base)
for group,entry in d['reference'].items():
 paths=u.bundle.read_fingerprint(base/entry['source']);text='\n'.join(sorted(f'{expected[p]}  {p}' for p in paths))+'\n';(out/entry['source']).write_text(text);entry['sha256']=sha(out/entry['source'])
save(out/'bundle.json',d);plan=u.prepare(out,WS/'westlake-generation-n4-order-216b68fb')
changed={p:[v,plan['expected'][p]] for p,v in plan['baseline'].items() if plan['expected'][p]!=v}
assert len(plan['expected'])==312;assert all('/system/android/framework/' in p for p in changed);assert len(changed)<=29
save(HERE/'assembly.json',{'package':out.name,'bundle_sha256':sha(out/'bundle.json'),'expected_count':len(plan['expected']),'staged_members':29,'changed':changed,'unchanged_native_manifest':d['native']['manifest']['sha256'],'baseline_fingerprints':u.fingerprints(plan['baseline'],plan['reference_paths']),'target_fingerprints':u.fingerprints(plan['expected'],plan['reference_paths']),'build_receipt':plan['build_receipt'],'device_io':False})
print(json.dumps(json.loads((HERE/'assembly.json').read_text())['target_fingerprints']))
