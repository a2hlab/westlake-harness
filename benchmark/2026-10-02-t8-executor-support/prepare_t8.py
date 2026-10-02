#!/usr/bin/env python3
"""Copy immutable donors into a fresh, unarmed T8/U10.1 candidate.

Keeps the previous rejected candidate intact. Approval and board use are separate.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/lab'))
import generation_bundle as b
import u7_executor as u
import generation_static_checks as static


def save(p,data):p.write_text(json.dumps(data,indent=2)+'\n')


def assemble(out,base,donor,t8,receipt=None):
    out,base,donor,t8=map(lambda p:Path(p).resolve(),(out,base,donor,t8))
    if out.exists():raise ValueError('fresh output directory required')
    bd,bm,_=b.validate(base);dd,dm,_=b.validate(donor)
    old=static.effective(base);donor_rows=static.effective(donor)
    native_changes={p for p,r in donor_rows.items() if old.get(p,{}).get('sha256')!=r['sha256']}
    t8_targets=b.IMAGE_TARGETS|{b.FW+'adapter-mainline-stubs.jar',b.FW+'oh-adapter-framework.jar'}
    if native_changes & t8_targets:raise ValueError('U10.1/T8 members overlap')
    if dd['runtime_jar']['sha256']!='5ae3dd29d45c2270e8a53a9dc4bbeeca8972b9b092f91898a15d605bc1cc0108':
        raise ValueError('this promotion requires the signed U11i runtime JAR')
    # Validate all nine baked inputs before copying, including the seven unchanged JARs.
    for j in b.JARS:
        p=t8/'jars9'/(j+'.jar')
        if j not in ('adapter-mainline-stubs','oh-adapter-framework') and b.sha(p)!=old[b.FW+j+'.jar']['sha256']:
            raise ValueError('unexpected T8 BCP input change: '+j)
    shutil.copytree(donor,out)
    native=out/dd['native']['directory'];manifest=json.loads((native/'package.json').read_text())
    data=json.loads((out/'bundle.json').read_text())
    data['rollout_ready']=False
    for key in ('rollout_approval','window_authorization','rollout_blocker'):data.pop(key,None)
    # Disarm immediately, before any donor bytes are replaced or a later audit can fail.
    save(out/'bundle.json',data)
    for row in data['boot_group']['members']:
        source=t8/('jars9' if row['target'].endswith('.jar') else 'image')/Path(row['target']).name
        dst=out/row['source'];dst.chmod(dst.stat().st_mode|0o200);shutil.copyfile(source,dst);row['sha256']=b.sha(dst)
    # Both BCP swaps are declared in the same stopped-parent boot transaction.
    for j in ('adapter-mainline-stubs','oh-adapter-framework'):
        name=j+'.jar';relative='payload/android/framework/'+name;dst=native/relative
        dst.chmod(dst.stat().st_mode|0o200);shutil.copyfile(t8/'jars9'/name,dst)
        manifest['files'][relative]=b.sha(dst)
        if b.FW+name in manifest['live_hashes']:manifest['live_hashes'][b.FW+name]=b.sha(dst)
        if not any(r['target']==b.FW+name for r in data['boot_group']['members']):
            data['boot_group']['members'].append(dict(source=str(dst.relative_to(out)),target=b.FW+name,sha256=b.sha(dst)))
    manifest.update(variant='U10.1 + T8 effective-BCP candidate; outer review pending',rollout_ready=False)
    manifest.pop('rollout_blocker',None);save(native/'package.json',manifest)
    data['native']['manifest']['sha256']=b.sha(native/'package.json')
    scanpath=native/'native-checks/scan-manifest.json';scan=json.loads(scanpath.read_text())
    for profile in scan['profiles']:
        identity=profile['identity'];identity.update(package=out.name,manifest_sha256=data['native']['manifest']['sha256'],artifact_sha256=manifest['files'][identity['artifact']])
    save(scanpath,scan)
    gatespath=native/'native-checks/native-gates.json';gates=json.loads(gatespath.read_text())
    gates['package_manifest_sha256']=data['native']['manifest']['sha256'];gates['initialization']['manifest']['sha256']=b.sha(scanpath);save(gatespath,gates)
    refs=[]
    for target in sorted(b.IMAGE_TARGETS|b.BCP_TARGETS):
        row=old[target];dst=out/'gate-reference'/Path(target).name;dst.parent.mkdir(exist_ok=True)
        shutil.copyfile(b.member(base,row),dst)
        refs.append(dict(source=str(dst.relative_to(out)),target=target,sha256=b.sha(dst)))
    data['image_gate_reference']=dict(kind='signed-effective-U9',baseline_bundle_sha256=b.sha(base/'bundle.json'),members=refs)
    inputs={j+'.jar':b.sha(t8/'jars9'/(j+'.jar')) for j in b.JARS}
    outputs={Path(p).name:b.sha(t8/'image'/Path(p).name) for p in b.IMAGE_TARGETS}
    provenance=json.loads(Path(receipt).read_text()) if receipt else dict(status='unknown',reason='paired donor build receipt pending')
    if receipt and (provenance.get('input_jars')!=inputs or provenance.get('outputs')!=outputs):raise ValueError('donor paired receipt mismatch')
    provenance.update(input_jars=inputs,outputs=outputs)
    dst=out/'receipts/t8-build-receipt.json';save(dst,provenance)
    data['paired_build_receipt']=dict(source=str(dst.relative_to(out)),sha256=b.sha(dst))
    # U11i class additions were already signed; no drop/reshape whitelist for runtime.
    import deployed_class_diff as classes
    old_runtime=b.member(base,old[b.FW+'oh-adapter-runtime.jar'])
    new_runtime=b.member(out,data['runtime_jar'])
    additions=sorted(classes.classes(new_runtime).keys()-classes.classes(old_runtime).keys())
    policy=dict(jars={b.FW+'oh-adapter-runtime.jar':dict(allow_add=additions,reason='exact signed U11i 5ae3dd29 class additions'),
                      b.FW+'adapter-mainline-stubs.jar':dict(allow_add=['Lcom/android/i18n/phonenumbers/','Lcom/android/org/conscrypt/SSLParametersImpl;'],allow_reshape=['Lcom/android/i18n/phonenumbers/'],reason='T8 real AOSP libphonenumber replaces its stub; SSLParametersImpl presence'),
                      b.FW+'oh-adapter-framework.jar':{}},native={})
    dst=out/'receipts/composition-static-policy.json';save(dst,policy)
    data['static_checks']=dict(baseline_bundle_sha256=b.sha(base/'bundle.json'),policy=dict(source=str(dst.relative_to(out)),sha256=b.sha(dst)))
    save(out/'bundle.json',data)
    plan=u.prepare(out,base/dd['native']['directory'])
    assert all(plan['expected'][b.FW+j+'.jar']==inputs[j+'.jar'] for j in b.JARS)
    assert all(plan['expected'][p]==outputs[Path(p).name] for p in b.IMAGE_TARGETS)
    services=json.loads((ROOT/'benchmark/2026-10-01-installation-chain-identity/current-u9.json').read_text())
    boards={}
    for serial,row in services['boards'].items():
        values=plan['expected']|row['services']
        refs=dict(runtime=sorted(set(plan['reference_paths']['runtime'])|set(row['services'])),boot=plan['reference_paths']['boot'])
        boards[serial]=dict(expected=values,fingerprints=u.fingerprints(values,refs),
                            unique_paths=len(values),identity_assertions=len(plan['expected'])+len(row['services']))
    save(out/'expected-per-board.json',boards)
    return dict(bundle_sha256=b.sha(out/'bundle.json'),native_manifest_sha256=data['native']['manifest']['sha256'],rollout_ready=False,
                boot_group_members=len(data['boot_group']['members']),runtime_jar=data['runtime_jar']['sha256'],
                disjoint_members=True,receipt_status=plan['build_receipt']['status'],static_policy_review='pending',
                expected_fingerprints={s:r['fingerprints'] for s,r in boards.items()},installation_chain_included=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('out','base','donor','t8'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--receipt',type=Path);args=p.parse_args()
    print(json.dumps(assemble(args.out,args.base,args.donor,args.t8,args.receipt),indent=2))


if __name__=='__main__':main()
