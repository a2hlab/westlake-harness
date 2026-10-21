#!/usr/bin/env python3
"""Verify G18 public provenance and, when present, rehash original private outputs."""
import argparse, hashlib, json, sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
BASELINE='b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(c,m):
 if not c:raise ValueError(m)
def check():
 identity=read(HERE/'upstream/source-identity.json');pins=read(HERE/'source-pins.json');changed=[]
 require(not (HERE/'upstream/test_analysis.py').exists(),'historical U13 reference must not be a discoverable G18 test')
 reference=pins['reference_files']['upstream/u13-analysis-tests.reference.txt']
 require(reference['original_path']=='benchmark/2026-10-02-u13-single-native/test_analysis.py' and sha(HERE/'upstream/u13-analysis-tests.reference.txt')==reference['sha256']=='160de163c73cbf3b76aec0618808008dee520d938738377dcb9c91055ada1b50','historical test reference byte drift')
 for name,h in identity['files'].items():
  prefix='sources/candidate/policy/'
  if not name.startswith(prefix):continue
  rel=name[len(prefix):];base=HERE/'sources/baseline'/rel;candidate=HERE/'sources/candidate'/rel
  require(sha(base)==h,'U13 baseline source drift: '+rel)
  if base.read_bytes()!=candidate.read_bytes():changed.append(rel)
 require(set(changed)=={'policy/native_bridge_policy.v1.json','include/nativeloader/native_bridge_policy.h'},'production change scope')
 for group in ['upstream','files']:
  for name,h in pins[group].items():require(sha(HERE/name)==h,'source pin drift: '+name)
 b=read(HERE/'sources/baseline/policy/native_bridge_policy.v1.json');c=read(HERE/'sources/candidate/policy/native_bridge_policy.v1.json')
 require(c['shared_sonames']==b['shared_sonames']+['libGLESv2.so'],'shared must append GLES only')
 c['shared_sonames']=b['shared_sonames'];require(c==b and len(b['system_libraries'])==7,'system/nonshared policy changed')
 base=(HERE/'sources/baseline/include/nativeloader/native_bridge_policy.h').read_text();candidate=(HERE/'sources/candidate/include/nativeloader/native_bridge_policy.h').read_text()
 require(candidate==base.replace('std::array<std::string_view, 7> kBridgeSharedSonames','std::array<std::string_view, 8> kBridgeSharedSonames').replace('    "libstdc++.so",','    "libstdc++.so",\n    "libGLESv2.so",'),'header change not minimal')
 inputs=read(HERE/'input-review.json');require(not inputs['missing_or_drift'] and inputs['counts']['source']==10 and inputs['counts']['old_logs']==15,'input checks incomplete')
 build=read(HERE/'build-01-receipt.json');require(build['status']=='BASELINE_IDENTICAL_CANDIDATE_BUILT','build not accepted')
 require(build['artifacts']['baseline']['sha256']==BASELINE,'full baseline mismatch')
 require(len(build['records'])==11 and all(r['rc']==0 for r in build['records']),'build commands incomplete/failed')
 elf=read(HERE/'elf-review.json');require(elf['status']=='ELF_ARRAYS_AND_TWO_COMPILED_CONSUMERS_VERIFIED','ELF consumption proof absent')
 require(elf['candidate']['shared']['values']==elf['baseline']['shared']['values']+['libGLESv2.so'],'ELF array mismatch')
 require(elf['candidate']['dynamic_abi']==elf['baseline']['dynamic_abi'] and elf['candidate']['needed']==elf['baseline']['needed'],'ABI/NEEDED drift')
 require(elf['candidate']['system']['values']==elf['baseline']['system']['values'],'ELF system policy drift')
 for variant in ['baseline','candidate']:
  require(elf[variant]['sha256']==build['artifacts'][variant]['sha256'],'ELF/artifact binding drift')
  require(set(elf[variant]['compiled_consumers'])=={'CreateClassLoaderNamespace','OpenNativeLibrary'},'missing explicit/implicit compiled consumption')
 tests=read(HERE/'regression.json');require(tests['status']=='PASS' and len(tests['records'])==21,'regression incomplete')
 for r in tests['records']:require(r['rc']==(1 if r['tag'].startswith('negative-') else 0),'unexpected regression result')
 for row in read(HERE/'sanitization.json'):
  require(sha(HERE/row['public'])==row['public_sha256'],'public evidence drift: '+row['public'])
 result=read(HERE/'results.json');require(not result['deployment_performed'] and not result['child_mapping_verified'] and not result['game_frame_verified'],'scope upgrade')
 raw_count=0
 if (HERE/'.private/build-01').exists():
  for row in read(HERE/'raw-index.json'):
   path=HERE/row['path'].removeprefix('$G18/');require(path.is_file() and sha(path)==row['sha256'] and path.stat().st_size==row['bytes'],'private raw drift: '+row['path']);raw_count+=1
  from inspect_elf import Elf
  for variant in ['baseline','candidate']:
   p=HERE/'.private/build-01'/variant/'libnativeloader-candidate.so';require(sha(p)==build['artifacts'][variant]['sha256'],'actual artifact drift')
   require(Elf(p).array('kBridgeSharedSonames')['values']==elf[variant]['shared']['values'],'actual ELF array drift')
 return {'status':'PASS','original_sources':10,'changed_production_files':2,'baseline_full_sha_equal':True,'candidate_sha256':result['candidate']['sha256'],'shared':8,'system':7,'explicit_implicit_consumers':2,'negative_policy_cases':3,'private_raw_rehashed':raw_count,'private_missing_is_not_rebuilt':raw_count==0,'deployment_performed':False}
if __name__=='__main__':print(json.dumps(check(),indent=2))
