import hashlib,json,subprocess
from pathlib import Path
import lab_paths
d=Path.home()/'a2hlab/static';a=Path('/home/dspfac/a2hlab/source-closure/verify');p=lab_paths.inputs()
def sha(x):return hashlib.sha256(x.read_bytes()).hexdigest()
lock=json.loads((d/'runtime-lock.json').read_text());checks=[]
for group in ['boot_classpath','bridge_libraries','system_libraries']:
 for e in lock[group]:
  paths=[Path(e['path'])] if 'path' in e else list((a/'out').glob('*/'+e['name']))
  matches=[str(x) for x in paths if sha(x)==e['sha256']]
  checks.append({'group':group,'recorded':e['sha256'],'paths_checked':[str(x) for x in paths],'matching_paths':matches,'matches':bool(matches)})
dirs=[a/'toolchains/ohos-sdk/native/sysroot/usr/lib/aarch64-linux-ohos',a/'out/native-imports',a/'out/native-runtime']
libs=[{'path':str(x),'bytes':x.stat().st_size,'sha256':sha(x)} for dr in dirs for x in sorted(dr.glob('*.so'))]
repo=a/'westlake'
r={'runtime_lock_sha256':sha(d/'runtime-lock.json'),'runtime_index_sha256':sha(d/'runtime-index.json'),'runtime_lock_checks':checks,'oh_index_inputs':libs,'westlake_head':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'westlake_status':subprocess.check_output(['git','-C',str(repo),'status','--short'],text=True),'tool_source':'scanner: e3100e1 plus archived operational patch; pipeline/aggregator: analysis/static-100 #5 tracked tools, exact hashes below','pipeline_sha256':sha(p/'tools/static_pipeline.py'),'aggregator_sha256':sha(p/'tools/aggregate_gaps.py')}
(p/'static100-provenance.json').write_text(json.dumps(r,indent=1)+'\n');print('lock checks',len(checks),all(x['matches'] for x in checks),'OH input libraries',len(libs))
