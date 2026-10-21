#!/usr/bin/env python3
"""Offline U13 rebind pattern: clone bytes, rebind references, validate with original U7.
No legacy main/stage call; no device API; no build; no approval generation.
"""
import argparse, copy, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
from inspect_inputs import sha, save
HERE=Path(__file__).resolve().parent
BASE_SHA='91272eaf4cdda30b0c079575cd269959c6f6dab9f23a09a0fed567c20478bd28'
BASE_NATIVE='85aef68eafbde98e6ac885264fe36f2f1e357618abf1d455de6ca15c0996cee6'
CANDIDATE='878c7019b1b78c8affbf9808d69fdc8478554273fe5d06d499b6775b7d004f23'
BASELINE='b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7'
def put(src,dst):
    if dst.exists(): dst.chmod(dst.stat().st_mode|0o200)
    dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)
def dump(p,o):
    if p.exists(): p.chmod(p.stat().st_mode|0o200)
    save(p,o)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--workspaces',type=Path,required=True); ap.add_argument('--evidence',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args(); ws=a.workspaces.resolve(); main=ws/'westlake-harness'; out=a.out.resolve()
    sys.path.insert(0,str(main/'scripts/lab')); import u7_executor as u7; import generation_bundle as gb
    base=ws/'westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/.artifacts/bundle-v4'
    assert sha(base/'bundle.json')==BASE_SHA and sha(base/'native/package.json')==BASE_NATIVE
    coverage=json.loads((HERE/'target-coverage.json').read_text()); assert not coverage['missing']
    observed={r['target']:r['observed_sha256'] for r in coverage['rows']}; assert len(observed)==319
    g18=HERE.parent/'gles-loader-candidate/.private/build-01'; cand=g18/'candidate/libnativeloader-candidate.so'; assert sha(cand)==CANDIDATE
    boatplan=main/'benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/minimal-r4/package/plan.disabled.json'; boat=json.loads(boatplan.read_text()); sources={r['sha256']:r for r in boat['members'] if '/sources/' in r['target']}
    assert not out.exists(),'fresh assembly output required'; out.mkdir(parents=True)
    baseline=out/'baseline'; candidate=out/'candidate'; subprocess.run(['/bin/cp','-cR',str(base),str(baseline)],check=True)
    data=json.loads((baseline/'bundle.json').read_text()); m=json.loads((baseline/'native/package.json').read_text()); rows=u7.effective_files(m)
    overlays=[]
    for change in coverage['differences']:
        target=change['target']; digest=change['observed_sha256']; ref=sources[digest]; src=Path(ref['source'].replace('$WORKSPACES',str(ws))); assert sha(src)==digest
        if target==data['runtime_jar']['target']:
            put(src,baseline/data['runtime_jar']['source']); data['runtime_jar']['sha256']=digest
        # Keep native underlay coherent as well as explicit JAR overlay.
        if target in rows:
            name=rows[target]['source']; put(src,baseline/'native'/name); m['files'][name]=digest
            if target in m['live_hashes']: m['live_hashes'][target]=digest
        overlays.append({'target':target,'source':ref['source'],'sha256':digest})
    m['bridge_sha256']=observed['/system/android/lib64/liboh_adapter_bridge.so']; m['rollout_ready']=False; m['rollout_blocker']='G20 current-baseline assembly; no new outer approval'
    for kind,name in [('runtime','runtime'),('boot','boot-image')]:
        dest=baseline/data['reference'][kind]['source'];put(a.evidence/'outer-fingerprint-01/fingerprints'/f'{name}-fingerprint.txt',dest);data['reference'][kind]['sha256']=sha(dest)
    effective=u7.effective_files(m,'native/'); effective.update({r['target']:r for r in data['boot_group']['members']+[data['runtime_jar']]})
    for ref in data['image_gate_reference']['members']:
        current=effective[ref['target']]; assert current['sha256']==observed[ref['target']];put(baseline/current['source'],baseline/ref['source']); ref['sha256']=current['sha256']
    # Retain old signed policy as historical bytes; new active policy has no allowances/signatures.
    dump(baseline/'g20-static-policy.unsigned.json',{'jars':{},'native':{}})
    data['static_checks']={'baseline_bundle_sha256':BASE_SHA,'policy':{'source':'g20-static-policy.unsigned.json','sha256':sha(baseline/'g20-static-policy.unsigned.json')}}
    data['image_gate_reference']['kind']='observed-current-baseline-unsigned';data['image_gate_reference']['baseline_bundle_sha256']=BASE_SHA
    data['rollout_ready']=False;data['rollout_blocker']='G20 unsigned; original static/native/outer admission required'
    def seal(root,b,m):
        dump(root/'native/package.json',m); b['native']['manifest']['sha256']=sha(root/'native/package.json')
        gate=root/'native/native-checks/native-gates.json'; d=json.loads(gate.read_text());d['package_manifest_sha256']=b['native']['manifest']['sha256']
        # Rebind exact artifact references only; do not change namespace or exception policy.
        def bind(v):
            if isinstance(v,dict):
                if 'path' in v and 'sha256' in v:
                    p=root/'native'/v['path']
                    if p.is_file():v['sha256']=sha(p)
                for x in v.values():bind(x)
            elif isinstance(v,list):
                for x in v:bind(x)
        bind(d);dump(gate,d);dump(root/'bundle.json',b)
    seal(baseline,data,m); gb.validate(baseline)
    subprocess.run(['/bin/cp','-cR',str(baseline),str(candidate)],check=True)
    cd=copy.deepcopy(data);cm=copy.deepcopy(m);changed=[]
    for target,row in u7.effective_files(cm).items():
        if Path(target).name=='libnativeloader.so':
            assert row['sha256']==BASELINE;put(cand,candidate/'native'/row['source']);cm['files'][row['source']]=CANDIDATE
            if target in cm['live_hashes']: cm['live_hashes'][target]=CANDIDATE
            changed.append(target)
    assert len(changed)==2
    cd['static_checks']['baseline_bundle_sha256']=sha(baseline/'bundle.json');cd['image_gate_reference']['baseline_bundle_sha256']=sha(baseline/'bundle.json')
    seal(candidate,cd,cm)
    plan=u7.prepare(candidate,baseline/'native'); assert plan['baseline']==observed
    diff=sorted(t for t,h in plan['expected'].items() if plan['baseline'].get(t)!=h);assert diff==sorted(changed)
    assert all(plan['expected'][t]==CANDIDATE for t in diff);assert not plan['additions']; assert not plan['rollout_ready']
    dump(out/'transaction-plan.raw.json',plan)
    def portable(v):
        if isinstance(v,dict):return {k:portable(x) for k,x in v.items()}
        if isinstance(v,list):return [portable(x) for x in v]
        if isinstance(v,str):return v.replace(str(HERE),'$G20').replace(str(ws),'$WORKSPACES')
        return v
    save(HERE/'transaction-plan.json',portable(plan))
    result={'status':'ASSEMBLED_UNSIGNED','device_io':False,'compiled':False,'execution_enabled':False,'observed_boot':coverage['boot'],'baseline_target_count':len(plan['baseline']),'candidate_target_count':len(plan['expected']),'logical_changes':diff,'actual_planned_writes':plan['changes'],'actual_planned_write_count':len(plan['changes']),'unchanged_staged_count':sum(r['sha256']==plan['baseline'][r['target']] for r in plan['changes']),'baseline_bundle_sha256':sha(baseline/'bundle.json'),'baseline_native_sha256':sha(baseline/'native/package.json'),'candidate_bundle_sha256':sha(candidate/'bundle.json'),'candidate_native_sha256':sha(candidate/'native/package.json'),'boat_plan_sha256':sha(boatplan),'overlays':overlays,'build_receipt_status':plan['build_receipt']['status'],'historical_owned_state_created':False,'baseline':str(baseline),'candidate':str(candidate)}
    save(HERE/'assembly.json',portable(result)); print(json.dumps({k:result[k] for k in ['status','baseline_target_count','actual_planned_write_count','unchanged_staged_count','candidate_native_sha256']},sort_keys=True))
if __name__=='__main__':main()
