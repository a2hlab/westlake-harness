#!/usr/bin/env python3
"""Validate unsigned delivery, not deployment admission."""
import argparse,copy,json,sys
from pathlib import Path
from inspect_inputs import sha
from prepare import BASE,CAND,TARGET,require_accepted
D=Path(__file__).resolve().parent;REPO=D.parents[2]
def read(name):return json.loads((D/name).read_text())
def validate(plan,profiles,packages,results):
 assert len(plan['baseline'])==len(plan['expected'])==319
 assert plan['baseline']==read('baseline-319.json')
 assert plan['expected'][TARGET]==CAND and plan['baseline'][TARGET]==BASE
 for t in ['/system/android/lib64/libwestlake_native_abi.so','/system/android/lib64/westlake_flutter/libwestlake_native_abi.so']:
  assert plan['expected'][t]==plan['baseline'][t]==BASE,'non-selected ABI alias drift'
 changes={t for t,v in plan['expected'].items() if v!=plan['baseline'][t]}
 assert changes=={x['target'] for x in read('six-targets.json')}
 assert len(changes)==results['logical_changes']==6
 assert len(plan['changes'])==results['planned_writes']==36
 assert sum(x['sha256']==plan['baseline'][x['target']] for x in plan['changes'])==results['unchanged_writes']==30
 assert not plan['rollout_ready'] and not results['rollout_ready'] and not results['deployable']
 assert results['old_exceptions_inherited']==0
 for side in ['baseline','candidate']:
  assert len(profiles[side])==15
  meta=packages[side]['metadata'];manifest=next(x['sha256'] for x in meta if x['path'].endswith('/native/package.json'))
  for p in profiles[side]:
   i=p['identity'];assert i['manifest_sha256']==manifest,'source profile manifest drift'
   artifact=next(x for x in packages[side]['native_files'] if x['path'].endswith('/native/'+i['artifact']))
   assert i['artifact_sha256']==artifact['sha256'],'source profile artifact drift'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--private',action='store_true');a=ap.parse_args()
 manifest=read('manifest.json');count=0
 for x in manifest['files']:
  p=REPO/x['path'];assert sha(p)==x['sha256'] and p.stat().st_size==x['bytes'],x['path'];count+=1
 plan=read('transaction-plan.json');profiles=read('current-source-profiles.json');packages=read('package-index.json');results=read('results.json');validate(plan,profiles,packages,results)
 findings=read('findings.unsigned.json');gates=read('gates.json')
 assert all(x['signature'] is None and x['approval_inherited'] is False for x in findings['rows'])
 for side in ['baseline','candidate']:
  assert gates[side]['errors']==[]
  for gate in ['N1','N2']:
   rows=[x for x in findings['rows'] if x['side']==side and x['gate']==gate]
   assert len(rows)==gates[side]['gates'][gate]['rejected'] and gates[side]['gates'][gate]['excepted']==0
   assert all(x['package_manifest_sha256']==gates[side]['package_manifest_sha256'] and x['inputs_sha256']==gates[side]['inputs_sha256'] for x in rows)
 assert gates['G1']==gates['G2']=='NOT_REACHED'
 negatives=[]
 try:require_accepted(None,Path('unused'))
 except ValueError:negatives.append('missing outer acceptance refused')
 for name,mutate in [('public alias drift',lambda p,s,r:p['expected'].__setitem__('/system/android/lib64/libwestlake_native_abi.so',CAND)),('profile drift',lambda p,s,r:s['candidate'][0]['identity'].__setitem__('manifest_sha256','0'*64)),('deployment claim',lambda p,s,r:r.__setitem__('rollout_ready',True))]:
  p,s,r=copy.deepcopy((plan,profiles,results));mutate(p,s,r)
  try:validate(p,s,packages,r)
  except AssertionError:negatives.append(name+' refused')
 assert len(negatives)==4
 private_count=0
 if a.private:
  w=REPO.parent
  def expand(n):return Path(n.replace('$WORKSPACES',str(w)).replace('$HOME',str(Path.home())))
  pins=read('evidence-index.json')+read('acceptance-verification.json')['pins']+read('input-pins.json')
  for side in packages.values():pins+=side['metadata']+side['native_files']
  for x in pins:
   p=expand(x['path']);assert sha(p)==x['sha256'],str(p)
   if 'bytes' in x:assert p.stat().st_size==x['bytes']
   private_count+=1
  accept=expand(read('acceptance-verification.json')['acceptance']['path']);assert sha(accept)==read('acceptance-verification.json')['acceptance']['sha256']
  require_accepted(json.loads(accept.read_text()),w/'westlake-harness-t4/benchmark/2026-10-21-commercial-game/locale-abi-candidate/.private/candidate-02/receipt.json')
  sys.dont_write_bytecode=True;sys.path.insert(0,str(w/'westlake-harness/scripts/lab'));import u7_executor as u7
  actual=u7.prepare(D/'.private/assembly-01/candidate',D/'.private/assembly-01/baseline/native');assert actual['expected']==plan['expected'] and actual['baseline']==plan['baseline']
 print(json.dumps({'status':'PASS_UNSIGNED_CONSISTENCY_ONLY','public_pins':count,'private_pins':private_count,'negative_cases':negatives,'rollout_ready':False}))
if __name__=='__main__':main()
