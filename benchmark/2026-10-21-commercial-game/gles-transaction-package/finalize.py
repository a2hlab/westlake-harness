#!/usr/bin/env python3
"""Finalize a portable, unsigned handoff from immutable attempt directories."""
import json,re
from pathlib import Path
from inspect_inputs import sha,save
from export_evidence import portable as localportable
HERE=Path(__file__).resolve().parent;WS=HERE.parents[3]
def portable(s):return re.sub(r'/home/[^/\s\x22\x27]+','$LAB_HOME',localportable(s))
def main():
    index=json.loads((HERE/'evidence-index.json').read_text());seen={r['original'] for r in index}
    locations=[(HERE/'.private/gates-02',HERE/'evidence/gates-02'),(HERE/'.private/commands',HERE/'evidence/assembly-01')]
    for name in ['outer-g20-gates-01','outer-g20-images-01']:
        locations.append((Path.home()/'.local/share/westlake/commercial-game-20261021'/name,HERE/'evidence'/name))
    for srcroot,dstroot in locations:
        for src in sorted(srcroot.rglob('*')):
            if not src.is_file() or portable(str(src)) in seen:continue
            dst=dstroot/src.relative_to(srcroot)
            if dst.suffix in ['.stdout','.stderr'] or dst.name in ['stdout','stderr']:dst=dst.with_name(dst.name+'.txt')
            dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(portable(src.read_text()));index.append({'original':portable(str(src)),'original_sha256':sha(src),'original_size':src.stat().st_size,'sanitized':str(dst.relative_to(HERE)),'sanitized_sha256':sha(dst),'transformation':'literal local path replacement and remote user prefix alias; originals unchanged'})
    save(HERE/'evidence-index.json',index)
    old=json.loads((HERE/'private-package-index.json').read_text());current={};metadata=[]
    for kind in ['baseline','candidate']:
        root=HERE/'.private/assembly-02'/kind;current[kind]={str(p.relative_to(root)):{'sha256':sha(p),'size':p.stat().st_size} for p in sorted(root.rglob('*')) if p.is_file()}
        assert set(old[kind])==set(current[kind])
        changes=[p for p in old[kind] if old[kind][p]!=current[kind][p]]
        assert all(p.startswith('native/native-checks/') for p in changes)
        metadata.append({'package':kind,'changed_from_01':changes,'payload_changed':False})
        for n in ['native/package.json','bundle.json','native/native-checks/native-gates.json','native/native-checks/scan-manifest.json','native/native-checks/u13-m1-compat-shim.cpp','native/native-checks/u10-1-native-policy.h']:
            p=root/n;dest=HERE/'package-metadata-02'/kind/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    save(HERE/'private-package-index-02.json',current);save(HERE/'assembly-02-delta.json',{'from':'assembly-01','to':'assembly-02','metadata':metadata,'execution_enabled':False})
    results=json.loads((HERE/'results.json').read_text());images=json.loads((HERE/'evidence/outer-g20-images-01/report.json').read_text());assert images['image_gates']['G1'] and images['image_gates']['G2']
    report=json.loads((HERE/'.private/gates-02/native-candidate.stdout').read_text());results.update(status='INPUTS_READY_UNSIGNED_NATIVE_REVIEW_REQUIRED',current_assembly='assembly-02',G1=True,G2=True,image_gate_evidence='evidence/outer-g20-images-01/report.json',G2_scope='Exact unchanged images/BCP in assembly-01 and assembly-02; not full preflight acceptance',first_attempt='evidence/gates-01 preserves original G2 missing-tool and N1 INVALID',current_native={'N1_rejected':55,'N2_rejected':104,'errors':report['errors'],'rc':1},exception_proposal='exceptions.unsigned.json',N2_review={'exact_object_rebind':100,'changed_objects':4},N1_new_finding_text_rows=2,blockers=[{'gate':'native N1/N2','needed':'Outer reviews/signs actual assembly-02 package/inputs finding rows; 55 N1 + 104 N2 each package. Do not transplant old signature. See exceptions.unsigned.json.'},{'gate':'outer rollout','needed':'Actual outer admission, original final U7 preflight and rollout_ready decision remain pending; no owned state fabricated.'}]);save(HERE/'results.json',results)
    save(HERE/'documentation.json',{'proposed_digest_line':'G20: U13+Boat r4 current baseline is 319 SHA targets (285 package plus 34 reference-only); GLES two-alias logical change makes U7 stage 32 files/30 same-SHA. Rebinding N1 must use fresh 947 runtime shim and G18 sources; 104 identical N2 findings still contain 4 changed-object review cases. New manifest/inputs require new outer approval; no historical signature transfer.'})
    raw=HERE/'.private/commands';save(raw/'assembly-01.receipt.json',{'argv':['python3','$G20/assemble.py','--workspaces','$WORKSPACES','--evidence','$HOME/.local/share/westlake/commercial-game-20261021/loader-deployment-admission','--out','$G20/.private/assembly-01'],'rc':0,'receipt_note':'Exit code recorded from completed tool invocation; stdout/stderr were redirected before process execution.'})
    save(HERE/'next-commands.json',{'execution_enabled':False,'run_after_outer_native_review':['python3','$G20/run_gates.py','--main','$WORKSPACES/westlake-harness','--assembly','$G20/.private/assembly-02','--out','$G20/.private/gates-final-unique','--only','u7','--oatdump','$WORKSPACES/westlake-harness/scripts/lab/oatdump_remote.sh','--lab-home-from-provenance'],'LAB_HOME_source':'$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/SOURCE.txt; same exact regex as U13 offline_gates.py; never guess server directory','isolated_G2_repeat':False,'device_commands':[]})
    rollback=json.loads((HERE/'rollback-binding.json').read_text())
    rollback['private_baseline']='$G20/.private/assembly-02/baseline'
    rollback['historical_assembly_01']='Preserved, not the current sidecar input'
    comparisons=json.loads((HERE/'exception-comparison.json').read_text())['packages']
    rollback['native_inputs_sha256']={kind:row['inputs_sha256'] for kind,row in comparisons.items()}
    save(HERE/'rollback-binding.json',rollback)
    print('G20 final metadata prepared; unsigned; no device I/O')
if __name__=='__main__':main()
