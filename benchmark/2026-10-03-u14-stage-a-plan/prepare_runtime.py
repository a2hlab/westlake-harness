"""Arm reviewed U14 metadata and prove all other bytes unchanged; offline only."""
import json
import os
from pathlib import Path
import subprocess
import sys

H = Path(__file__).resolve().parent
W = H.parents[2]
M = W/'westlake-harness'
sys.path.insert(0, str(M/'scripts/lab'))
import generation_bundle as gb
import u7_executor as u

def path(s):
    return Path(s.replace('$WORKSPACES',str(W)))

def public(p):
    return '$WORKSPACES/'+str(p.relative_to(W))

def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,indent=2)+'\n')

def inventory(p):
    return {str(f.relative_to(p)):gb.sha(f) for f in sorted(p.rglob('*')) if f.is_file() and f.name!='bundle.json'}

def main():
    bindings=json.loads((H/'inputs/bindings.json').read_text())['variants']
    auth=json.loads((M/'benchmark/2026-10-03-u14-stage-a-plan/outer-window-authorization.json').read_text())
    all_proof=[]
    for variant,boards in [('common',['5ea','5cd']),('61b',['61b'])]:
        c=bindings[variant];source=path(c['package'])
        assert gb.sha(source/'bundle.json')==c['bundle_sha256']
        target=W/'westlake-inputs/generations/u14-stageA-20261003'/variant/'armed-bundle'
        target.parent.mkdir(parents=True,exist_ok=True)
        assert not target.exists(),'fresh armed package required'
        subprocess.run(['cp','-cR',str(source),str(target)],check=True)
        before=json.loads((source/'bundle.json').read_text());after=dict(before)
        assert before['rollout_ready'] is False
        after['rollout_ready']=True;after['rollout_blocker']=''
        write(target/'bundle.json',after)
        delta={k:{'before':before.get(k),'after':after.get(k)} for k in set(before)|set(after) if before.get(k)!=after.get(k)}
        assert set(delta)<={'rollout_ready','rollout_blocker'} and delta['rollout_ready']['after'] is True
        files=inventory(source);assert inventory(target)==files
        native=target/'native';assert gb.sha(native/'package.json')==auth['native_manifest_sha256']
        assert gb.sha(native/'native-checks/native-gates.json')==auth['native_inputs_sha256']
        base=path(c['transaction_base']);prepared=u.prepare(target,base/'native')
        identities={};restore={}
        for board in boards:
            p=json.loads((H/f'plan-{board}.json').read_text());serial=p['serial']
            a=auth['per_board'][serial]
            assert c['bundle_sha256']==a['bundle_sha256'] and gb.sha(base/'bundle.json')==a['effective_baseline_bundle_sha256']
            r=json.loads((H/f'inputs/recovery-{board}.json').read_text())
            assert prepared['baseline']==r['expected'],'retained U13 baseline differs'
            refs={k:list(v) for k,v in r['reference_paths'].items()}
            # bms_batch root *.so inventory includes the new ICU compat file.
            refs['runtime']=sorted(set(refs['runtime'])|{p for p in prepared['additions'] if Path(p).parent==Path('/system/android/lib64') and p.endswith('.so')})
            identities[serial]={'expected':prepared['expected'],'reference_paths':refs,
                'fingerprints':u.fingerprints(prepared['expected'],refs),
                'identity_assertions':r['identity_assertions']+len(prepared['additions']),
                'unique_paths':len(prepared['expected'])}
            restore[serial]=r
        folder=H/'window1'/variant
        comp={'package':public(target),'unarmed_package':c['package'],
            'approved_unarmed_bundle_sha256':c['bundle_sha256'],'bundle_sha256':gb.sha(target/'bundle.json'),
            'base_bundle':c['transaction_base'],'base_bundle_sha256':c['transaction_base_sha256'],
            'native_manifest_sha256':auth['native_manifest_sha256'],'native_inputs_sha256':auth['native_inputs_sha256'],
            'candidate_boards':identities,'rollout_ready':True,'execution_enabled':False,
            'smoke_review':'pending outer first-lock approval'}
        write(folder/'composition.json',comp);write(folder/'recovery-u13.json',{'boards':restore})
        proof={'variant':variant,'source':public(source),'armed':public(target),
            'unarmed_sha256':c['bundle_sha256'],'armed_sha256':comp['bundle_sha256'],
            'bundle_field_diff':delta,'other_files_byte_identical':True,'other_files_count':len(files),
            'other_file_sha256':files,'manifest_sha256':auth['native_manifest_sha256'],
            'native_inputs_sha256':auth['native_inputs_sha256'],
            'additions':prepared['additions'],
            'candidate_identity':{k:{n:v[n] for n in ['identity_assertions','unique_paths','fingerprints']} for k,v in identities.items()}}
        write(folder/'arming-proof.json',proof);all_proof.append(proof)
    write(H/'window1/arming-correspondence.json',all_proof)
    print(json.dumps([{k:v for k,v in p.items() if k!='other_file_sha256'} for p in all_proof],indent=2))

if __name__=='__main__':main()
