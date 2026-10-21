#!/usr/bin/env python3
"""Offline evidence checker; never executes a deployer, remote wrapper or build."""
import argparse,copy,json
from pathlib import Path
from inspect_inputs import sha
HERE=Path(__file__).resolve().parent
BASE='b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7';CAND='878c7019b1b78c8affbf9808d69fdc8478554273fe5d06d499b6775b7d004f23'
def read(n):return json.loads((HERE/n).read_text())
def invariant(coverage,plan,result):
    assert coverage['missing']==[]
    assert coverage['reference_union_targets']==coverage['observed_targets']==319
    assert all(r['observed_sha256'] and len(r['observed_sha256'])==64 for r in coverage['rows'])
    observed={r['target']:r['observed_sha256'] for r in coverage['rows']};assert plan['baseline']==observed
    diff=[t for t,h in plan['expected'].items() if h!=plan['baseline'].get(t)]
    assert len(diff)==2 and all(Path(t).name=='libnativeloader.so' and plan['expected'][t]==CAND and plan['baseline'][t]==BASE for t in diff)
    assert len(plan['changes'])==32 and sum(r['sha256']==plan['baseline'][r['target']] for r in plan['changes'])==30
    assert not plan['rollout_ready'] and not result['execution_enabled'] and not result['outer_signed'] and not result['device_io']
    assert not result['historical_owned_state_created']
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--private',action='store_true');a=ap.parse_args();c=read('target-coverage.json');p=read('transaction-plan.json');r=read('results.json');invariant(c,p,r)
    assert read('boat-preserve.json')['target_count']==3
    assert all(not x['candidate_replacement'] for x in read('boat-preserve.json')['rows'])
    assert r['G1'] and r['G2'] and r['current_native']=={'N1_rejected':55,'N2_rejected':104,'errors':[],'rc':1}
    assert read('evidence/gates-01/u7-plan.json')['status']=='rejected'
    assert read('evidence/gates-01/native-candidate.stdout.txt')['status']=='INVALID'
    assert read('evidence/gates-02/native-candidate.stdout.txt')['status']=='REJECT'
    cmp=read('exception-comparison.json')
    for kind,data in cmp['packages'].items():
        n2=[x for x in data['rows'] if x['gate']=='N2'];assert len(n2)==104
        assert sum(x['review_class']=='REVIEW_CHANGED_OBJECTS' for x in n2)==4
        exact=[x for x in n2 if x['review_class']=='EXACT_FINDING_AND_OBJECTS_REBIND_REVIEW'];assert len(exact)==100 and all(not x['changed_objects'] for x in exact)
        assert all(x['exact_finding_match'] and x['old_approval_found'] for x in n2)
    proposal=read('exceptions.unsigned.json');assert len(proposal['exceptions'])==318
    assert all(x['approved_by'] is None and x['approved_at'] is None for x in proposal['exceptions'])
    assert len(read('n1-current-source-attestation.json')['profiles'])==30
    for row in read('evidence-index.json'):assert sha(HERE/row['sanitized'])==row['sanitized_sha256']
    negative=0
    for mutate in ['missing','drift','signed','extra','unknown']:
        cc,pp,rr=copy.deepcopy(c),copy.deepcopy(p),copy.deepcopy(r)
        if mutate=='missing':cc['missing']=['/system/missing']
        if mutate=='drift':pp['expected']['/system/bin/appspawn-x']='0'*64
        if mutate=='signed':rr['outer_signed']=True
        if mutate=='extra':pp['changes'].append(pp['changes'][0])
        if mutate=='unknown':cc['rows'][0]['observed_sha256']=None
        try:invariant(cc,pp,rr)
        except AssertionError:negative+=1
        else:raise AssertionError('negative case accepted: '+mutate)
    checked=0
    if a.private:
        for attempt,file in [('assembly-01','private-package-index.json'),('assembly-02','private-package-index-02.json')]:
            for kind,rows in read(file).items():
                root=HERE/'.private'/attempt/kind
                for name,value in rows.items():assert sha(root/name)==value['sha256'];checked+=1
    manifest=HERE/'manifest.json'
    if manifest.exists():
        for name,digest in read('manifest.json')['files'].items():assert sha(HERE.parents[2]/name)==digest
    print(json.dumps({'status':'PASS_OFFLINE_HANDOFF','coverage':319,'logical_changes':2,'planned_writes':32,'unsigned_proposals':318,'negative_cases':negative,'private_files_checked':checked,'device_io':False,'deployable':False}))
if __name__=='__main__':main()
