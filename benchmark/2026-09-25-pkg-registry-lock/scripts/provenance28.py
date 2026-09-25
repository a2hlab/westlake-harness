from board25 import *
import hashlib,shutil
A=pathlib.Path.home()/'a2hlab/ws'; W=A/'westlake-pkg28'; O=A/'out-pkg28'
build=R/'build';build.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
java=json.loads((O/'westlake-java/artifacts.json').read_text())
checks={n:sha(W/n)==v for n,v in java['inputs'].items()}
assert all(checks.values()),checks
subprocess.run(['git','-C',str(W),'merge-base','--is-ancestor','2478a7f','HEAD'],check=True)
for name in ['build.sh','westlake-java.log','framework-runtime.log','framework-boot.log','unit-test.log']:
 shutil.copy2(O/name,build/name)
for name in ['westlake-java','framework-runtime','framework-boot']:
 shutil.copy2(O/name/'artifacts.json',build/(name+'-artifacts.json'))
before=json.loads((R.parent/'touch25/offline-fresh-2/device-report.json').read_text())['source_files']
after=json.loads((R/'offline-fresh-1/device-report.json').read_text())['source_files']
changes=[{'file':k,'before':before.get(k,{}).get('sha256'),'after':after.get(k,{}).get('sha256')} for k in sorted(before.keys()|after.keys()) if before.get(k,{}).get('sha256')!=after.get(k,{}).get('sha256')]
result={'source_inputs':len(checks),'all_source_hashes_match_build':all(checks.values()),'registry_sha256':sha(W/'framework/package-manager/java/SourcePackageRegistry.java'),'base_commit':subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip(),'contains_2478a7f':True,'baseline_runtime_files':len(before),'candidate_runtime_files':len(after),'runtime_changes':changes}
(R/'build-provenance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
