#!/usr/bin/env python3
"""Export explicitly sanitized evidence; originals and private packages remain untouched."""
import json, os
from pathlib import Path
from inspect_inputs import sha, save, fingerprint_raw
HERE=Path(__file__).resolve().parent; WS=HERE.parents[3]; MAIN=WS/'westlake-harness'
def portable(s):
    return s.replace(str(HERE),'$G20').replace(str(WS),'$WORKSPACES').replace(str(Path.home()),'$HOME')
def main():
    evidence=Path.home()/'.local/share/westlake/commercial-game-20261021/loader-deployment-admission'; sources=[]
    for name in ['outer-full-baseline-01','outer-boat-preserve-01']:
        sources.extend((p,HERE/'evidence'/name/p.relative_to(evidence/name)) for p in sorted((evidence/name).rglob('*')) if p.is_file())
    sources.extend((p,HERE/'evidence/gates-01'/p.name) for p in sorted((HERE/'.private/gates-01').iterdir()) if p.is_file())
    sources.extend((p,HERE/'evidence/assembly-01'/p.name) for p in sorted((HERE/'.private/commands').iterdir()) if p.is_file())
    rows=[]
    for src,dst in sources:
        dst=dst.with_name(dst.name+'.txt') if dst.suffix in ['.stderr','.stdout'] else dst
        dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(portable(src.read_text()))
        rows.append({'original':portable(str(src)),'original_sha256':sha(src),'original_size':src.stat().st_size,'sanitized':str(dst.relative_to(HERE)),'sanitized_sha256':sha(dst),'transformation':'literal personal path replacement only; otherwise identical text'})
    save(HERE/'evidence-index.json',rows)
    a=json.loads((HERE/'assembly.json').read_text()); coverage=json.loads((HERE/'target-coverage.json').read_text());boat=evidence/'outer-boat-preserve-01'; hashes=fingerprint_raw(boat/'hashes.stdout');assert '\n__BOAT_PRESERVE_RC__0\n' in (boat/'hashes.stdout').read_text()
    assert all((boat/n).read_text().strip()==coverage['boot'] for n in ['boot-before.stdout','boot-after.stdout'])
    private=[]
    for r in coverage['boat_r4_mounts']:
        if r['in_u7_target_table']:continue
        target=r['target'];source='/data'+r['root'];assert hashes[target]==hashes[source]
        private.append({'target':target,'source':source,'sha256':hashes[target],'candidate_replacement':False,'evidence':'evidence/outer-boat-preserve-01/hashes.stdout.txt'})
    assert len(private)==3;save(HERE/'boat-preserve.json',{'boot':coverage['boot'],'target_count':3,'hash_assertions':6,'rows':private,'u7_target_count':319,'included_in_candidate_replacements':False})
    index={}
    for kind in ['baseline','candidate']:
        root=HERE/'.private/assembly-01'/kind
        index[kind]={str(p.relative_to(root)):{'sha256':sha(p),'size':p.stat().st_size} for p in sorted(root.rglob('*')) if p.is_file()}
        for name in ['bundle.json','native/package.json','native/native-checks/native-gates.json','native/native-checks/scan-manifest.json','g20-static-policy.unsigned.json','reference/runtime.txt','reference/boot-image.txt']:
            src=root/name;dst=HERE/'package-metadata'/kind/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
    save(HERE/'private-package-index.json',index)
    gates=HERE/'.private/gates-01'; records=json.loads((gates/'records.json').read_text()); native={k:json.loads((gates/('native-'+k+'.stdout')).read_text()) for k in ['baseline','candidate']}
    result={'status':'BLOCKED_ORIGINAL_GATES','execution_enabled':False,'device_io':False,'compiled':False,'outer_signed':False,'historical_owned_state_created':False,'baseline_coverage':319,'missing_sha_targets':[],'logical_changed_targets':a['logical_changes'],'actual_planned_writes':32,'same_sha_planned_writes':30,'boat_private_preserved':3,'gates':{Path(r['argv'][1]).name+' '+str(i):{'rc':r['rc'],'argv':[portable(s) for s in r['argv']]} for i,r in enumerate(records)},'blockers':[{'gate':'G2','actual_rc':2,'reason':'Original U7 requires G2 even when its 30 staged boot/JAR members have identical SHA; no oatdump supplied in this offline attempt','needed':'Runnable trusted oatdump binary or independently authorized existing host wrapper; rerun original dry-run with --oatdump. No skip flag/gate change.'},{'gate':'N1','reason':'historical profile does not bind candidate package: host','needed_fields':['baseline/native/native-checks/scan-manifest.json profiles[].identity.manifest_sha256','candidate/native/native-checks/scan-manifest.json profiles[].identity.manifest_sha256','profiles[].identity.artifact and artifact_sha256','profile source provenance; native-gates.json initialization.manifest.sha256'],'note':'Historical inputs preserved; do not relabel old profile evidence as current-source proof without verification.'},{'gate':'N2','rejected_baseline':native['baseline']['gates']['N2']['rejected'],'rejected_candidate':native['candidate']['gates']['N2']['rejected'],'needed_fields':['exact package_manifest_sha256','exact inputs_sha256','actual issue_id/gate rows','real outer approval or existing supported experiment receipt'],'note':'Old U13 exceptions bind old manifest/inputs, not these two newly composed packages.'},{'gate':'outer','reason':'No new outer signature or experiment generated; rollout_ready=false','needed':'Outer admission after original gate obligations resolved'}],'static_gate_limitation':'Original scanner returned PASS for two changed ELF paths with empty open-site/literal sets; does not replace G18 policy-array tests or prove unchanged shared allowlist. G18 explicitly changes shared policy 7 to 8.'}
    save(HERE/'results.json',result)
    save(HERE/'rollback-binding.json',{'execution_enabled':False,'current_boot':coverage['boot'],'baseline_bundle_sha256':a['baseline_bundle_sha256'],'baseline_native_sha256':a['baseline_native_sha256'],'baseline_target_table':'transaction-plan.json baseline (319)','private_baseline':'$G20/.private/assembly-01/baseline','candidate_bundle_sha256':a['candidate_bundle_sha256'],'candidate_native_sha256':a['candidate_native_sha256'],'journal':'NOT_CREATED; actual apply creates a fresh journal after original baseline/hash/mount checks','owned_state':'NOT_REQUIRED_BY_U7_AND_NOT_CREATED','rollback':'original u7_executor.py --rollback --journal <future-real-journal> --serial <held-5ea-serial> --out <fresh-report>; disabled until a real apply journal exists','mount_snapshot':'$HOME/.local/share/westlake/commercial-game-20261021/loader-deployment-admission/outer-readonly-01/mountinfo.stdout','alias_sources':['/data/westlake-demo/u13/sources/seq16','/data/westlake-demo/u13/sources/seq51'],'baseline_loader_sha256':'b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7','boat_preserve':'boat-preserve.json; no candidate writes to those three targets','fresh_apply_required':'Read current boot/hash/mount/lock identity again under outer holder; these offline receipts are not a future write authorization.'})
    pins={}
    names=['scripts/lab/u7_executor.py','scripts/lab/generation_bundle.py','scripts/lab/generation_static_checks.py','scripts/lab/deploy_generation.py','scripts/lab/deployment_native_gate.py','scripts/lab/native_predeploy.py','scripts/lab/native_initialization_gate.py','scripts/lab/native_needed_gate.py','scripts/lab/check_frozen.py','knowledge/gates/native-predeploy-exceptions.json','knowledge/frozen/frozen.json','benchmark/2026-10-03-u13-effective-rebind/prepare.py','benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/minimal-r4/package/plan.disabled.json']
    for n in names:pins['$WORKSPACES/westlake-harness/'+n]=sha(MAIN/n)
    peer=WS/'westlake-harness-t37-peer/benchmark/2026-10-21-commercial-game/loader-deployment-admission'
    for n in ['README.md','source-index.json','admission.json']:pins['$WORKSPACES/westlake-harness-t37-peer/benchmark/2026-10-21-commercial-game/loader-deployment-admission/'+n]=sha(peer/n)
    save(HERE/'tool-source-pins.json',pins)
    print(json.dumps({'exported':len(rows),'baseline_files':len(index['baseline']),'candidate_files':len(index['candidate']),'status':result['status']}))
if __name__=='__main__':main()
