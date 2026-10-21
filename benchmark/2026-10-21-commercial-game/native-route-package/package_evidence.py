#!/usr/bin/env python3
"""Create small public evidence from completed original gates; no deployment/build."""
import json,hashlib,re
from pathlib import Path
D=Path(__file__).resolve().parent;W=D.parents[3];C=Path.home()/'.local/share/westlake/commercial-game-20261021';P=D/'.private';MAIN=W/'westlake-harness'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def portable(v):
 if isinstance(v,dict):return {k:portable(x) for k,x in v.items()}
 if isinstance(v,list):return [portable(x) for x in v]
 if isinstance(v,str):return v.replace(str(C),'$COMMERCIAL').replace(str(W),'$WORKSPACES')
 return v
def save(n,v):(D/n).write_text(json.dumps(portable(v),indent=2)+'\n')
baseline=json.loads((D/'baseline-319.json').read_text());parsed={};sources=[]
for p in sorted((C/'g24-window02/closure').glob('baseline-*.txt')):
 sources.append(p)
 for line in p.read_text().splitlines():
  m=re.fullmatch(r'([0-9a-f]{64})\s+(/\S+)',line)
  if m:
   if m[2] in parsed:assert parsed[m[2]]==m[1]
   parsed[m[2]]=m[1]
assert parsed==baseline
boat={}
p=C/'g24-window02/closure/boat3.txt';sources.append(p)
for line in p.read_text().splitlines():
 m=re.fullmatch(r'([0-9a-f]{64})\s+(/\S+)',line)
 if m:boat[m[2]]=m[1]
assert len(boat)==3
save('recovery-binding.json',{'historical_G24_closed_baseline_hashes':319,'actual_readback_matches_all':True,'boat3':boat,'fresh_G27_complete_readback':'outer g27-outer-fingerprint-01/results.json MATCH direct319/parent319; not deployment admission','boot_reference':'a1d869b4-69a2-40a4-937e-4860f5b54239','new_owned_state':False,'baseline_assembly':str(P/'assembly-02/baseline'),'no_current_device_claim':True})
gates={}
for side in ['baseline','candidate']:
 p=P/'gates-native-01'/('native-'+side+'.stdout');d=json.loads(p.read_text());gates['native-'+side]={'rc':int((p.parent/('native-'+side+'.rc')).read_text()),'status':d['status'],'errors':d.get('errors',[]),'N2':{k:d['gates']['N2'][k] for k in ['rejected','excepted','stale']},'package_manifest_sha256':d['package_manifest_sha256'],'inputs_sha256':d['inputs_sha256'],'exceptions_sha256':d['exceptions_sha256']}
 gates['frozen-'+side]={'rc':int((P/('frozen-'+side+'.rc')).read_text()),'stdout':(P/('frozen-'+side+'.stdout')).read_text()}
s=(P/'gates-u7-01/u7-dry-run.stderr').read_text();d=json.loads(s[s.index('{'):]);gates['u7']={'rc':2,'stage':'generation_static_checks','status':d['status'],'changed_native_paths':d['changed_native_paths'],'members':[{'target':x['target'],'status':x['status'],'delta_sha256':x.get('delta_sha256'),'review':x.get('review')} for x in d['members']],'G1':'NOT_REACHED','G2':'NOT_REACHED'}
save('gates.json',gates)
save('host-binding-review.json',{'no_host_constant_found':True,'sites':[{'path':'scripts/lab/u7_executor.py','lines':[464,501],'meaning':'candidate/baseline manifest and native ticket identity bound; explicit expected host digest'},{'path':'scripts/lab/deploy_generation.py','lines':[254,268],'meaning':'original label recipe and supplied live-parent digest check'},{'path':'scripts/lab/native_initialization_gate.py','lines':[20,33],'meaning':'historical profile artifact binding; candidate old host profile is an actual N1 blocker'}],'G20_adapter_limit':'assemble.py fixes CANDIDATE to policy878c and asserts len(changed)==2; G27 uses same cp/rebind and original u7.prepare methods for explicit five targets; no common tools modified','tool_sha256':{n:sha(MAIN/'scripts/lab'/n) for n in ['u7_executor.py','deploy_generation.py','native_initialization_gate.py','generation_bundle.py']}})
metadata=[]
for side in ['baseline','candidate']:
 for rel in ['bundle.json','native/package.json','native/native-checks/native-gates.json']:
  p=P/'assembly-02'/side/rel;metadata.append({'side':side,'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size});sources.append(p)
save('package-index.json',metadata)
raw=[p for p in P.rglob('*') if p.is_file() and 'assembly-' not in str(p.relative_to(P)) and 'rust-target' not in p.parts]
sources+=raw
sources.append(C/'g27-outer-fingerprint-01/results.json')
sources+=[C/'g24-window02/apply.json',C/'g24-window02/closure/runtime-restored.json',MAIN/'specs/commercial-game-round1/t27-native-route-package.spec.md']
sources+=list(MAIN/'scripts/lab'/n for n in ['u7_executor.py','deploy_generation.py','native_initialization_gate.py','generation_bundle.py'])
save('evidence-index.json',[{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(set(sources))])
save('failures.json',{'git_branch':{'argv':['git','switch','-c','analysis/g27-native-route-package'],'rc':128,'stderr':(P/'git-branch.stderr').read_text(),'retries':0},'assembly_01':{'rc':1,'reason':'basename selection caught historical74e6 aliases; cardinality assertion refused before payload mutation; preserved','correction':'explicit route74d1 alias membership; assembly02 fresh, no old paths rewritten'},'gate_refusal_preserved':True})
save('documentation.json',{'proposed_digest_line':'G27: G24 baseline319 includes historical74e6 ANL/policy aliases; select exact system+74d1 targets, never basename-only. Five logical deltas give original U7 35 writes/30 same SHA; start host is manifest-bound but old N1 host profile still refuses new SHA.','shared_docs_modified':False})
print(json.dumps({'status':'PACKAGED','actual_baseline_readback':len(parsed),'raw_index':len(set(sources)),'rollout_ready':False}))
