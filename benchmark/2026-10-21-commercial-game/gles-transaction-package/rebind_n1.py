#!/usr/bin/env python3
"""Fresh sidecar binding from verified old bytes, Boat build and actual G18 build.
Does not change any ELF/JAR payload, namespace policy, registry or approval.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from inspect_inputs import sha,save
from assemble import put,dump
HERE=Path(__file__).resolve().parent;WS=HERE.parents[3];MAIN=WS/'westlake-harness'
def portable(s):return str(s).replace(str(HERE),'$G20').replace(str(WS),'$WORKSPACES')
def resolve(ref):return Path(ref.replace('$WORKSPACES',str(WS)).replace('$REPO',str(MAIN)))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--from-assembly',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();src=a.from_assembly.resolve();out=a.out.resolve();assert not out.exists()
    closure=MAIN/'benchmark/2026-10-10-boat-runtime-port-spec/evidence/linkfix-verification.json';cl=json.loads(closure.read_text());assert sha(closure)=='d4b2b5691bd7f1bd79e6a31697841424c580b21969582f0e4615c579426a7091';fb=cl['fresh_build'];assert fb['status']=='pass'
    pins={portable(closure):sha(closure)}
    for name in ['candidate','baseline','build_log']:
        r=fb[name];p=resolve(r['path']);assert sha(p)==r['sha256'];pins[portable(p)]=sha(p)
    receipt=resolve(cl['fresh_receipt']['path']);assert sha(receipt)==cl['fresh_receipt']['sha256'];pins[portable(receipt)]=sha(receipt)
    assert all(r['exit']==0 for r in fb['steps'])
    for r in fb['steps']:
        for stream in ['stdout','stderr']:
            p=resolve(r[stream]);assert sha(p)==r[stream+'_sha256'];pins[portable(p)]=sha(p)
    cold=resolve(fb['attempt'])/'cold';prep=json.loads((cold/'preparation.json').read_text());pins[portable(cold/'preparation.json')]=sha(cold/'preparation.json')
    for r in prep['generated_scripts']:
        p=Path(r['path'])
        if p.name=='recipe.sh':
            # The pinned build_link_gate replaces precisely one source after prepare().
            driver=resolve(cl['gate_sources']['build_link_gate.py']['path'])
            assert sha(driver)==cl['gate_sources']['build_link_gate.py']['sha256']
            pins[portable(driver)]=sha(driver)
            patched=str(cold.parent/'android_graphics_compat_shim.cpp')
            original=str(WS/'westlake-harness-t3/benchmark/2026-10-02-m1-session-slots/runtime/src/android_graphics_compat_shim.cpp')
            text=p.read_text();assert text.count(patched)==1
            assert hashlib.sha256(text.replace(patched,original).encode()).hexdigest()==r['sha256']
        else: assert sha(p)==r['sha256']
        pins[portable(p)]=sha(p)
    compiled={}
    for name in ['AndroidRuntime','asset_manager','android_graphics_compat_shim','android_graphics_Typeface']:
        dep=cold/'runtime-objects'/f'{name}.d';path=Path(dep.read_text().replace('\\\n',' ').split(':',1)[1].split()[0]);compiled[name]=path;pins[portable(dep)]=sha(dep);pins[portable(path)]=sha(path)
    shim=compiled['android_graphics_compat_shim'];assert sha(shim)==fb['compiled_source_sha256']=='280a36f2000924cecc05feb60ca49d1c2a0fc72a660e02cd7488ad2dedfd2506'
    g18=HERE.parent/'gles-loader-candidate';build=json.loads((g18/'build-01-receipt.json').read_text());assert build['status']=='BASELINE_IDENTICAL_CANDIDATE_BUILT';assert all(r['rc']==0 for r in build['records']);pins[portable(g18/'build-01-receipt.json')]=sha(g18/'build-01-receipt.json')
    sp=json.loads((g18/'source-pins.json').read_text());pins[portable(g18/'source-pins.json')]=sha(g18/'source-pins.json')
    for rel,h in sp['files'].items():assert sha(g18/rel)==h
    subprocess.run(['/bin/cp','-cR',str(src),str(out)],check=True)
    changes=[];profiles=[]
    for kind in ['baseline','candidate']:
        root=out/kind;native=root/'native';meta=native/'native-checks';manifest=json.loads((native/'package.json').read_text());pkgsha=sha(native/'package.json');scan=json.loads((meta/'scan-manifest.json').read_text())
        for name,r in scan['sources'].items():assert sha(meta/r['path'])==r['sha256']
        # The fresh 947 runtime compiled the same recorded source inputs except the pinned compat shim.
        for name,compiled_name in [('n4-order-runtime.cpp','AndroidRuntime'),('u13-asset-manager.cpp','asset_manager'),('android_graphics_Typeface.cpp','android_graphics_Typeface')]:assert sha(meta/scan['sources'][name]['path'])==sha(compiled[compiled_name])
        replacement={'u13-m1-compat-shim.cpp':shim,'u10-1-native-loader.cpp':g18/f'sources/{kind}/src/native_loader.cpp','u13-system-loader.cpp':g18/f'sources/{kind}/src/system_loader.cpp','u10-1-native-policy.h':g18/f'sources/{kind}/include/nativeloader/native_bridge_policy.h'}
        for name,path in replacement.items():
            r=scan['sources'][name];old=r['sha256'];put(path,meta/r['path']);r.update(sha256=sha(path),source_sha256=sha(path),origin=portable(path),first_line=1)
            changes.append({'package':kind,'source':name,'old_sha256':old,'current_sha256':sha(path),'changed':old!=sha(path),'origin':portable(path)})
        for profile in scan['profiles']:
            old=dict(profile['identity']);artifact=old['artifact'];digest=manifest['files'][artifact];assert sha(native/artifact)==digest
            changed=digest!=old['artifact_sha256'];basis='verified identical artifact and unchanged historical source snapshot'
            if artifact.endswith('liboh_android_runtime.so'):
                assert digest==fb['candidate']['sha256'];basis='Boat fresh build: exact ELF, original rc0 logs, recipe/dependency source and changed compat shim pinned'
            elif artifact.endswith('libnativeloader.so'):
                assert digest in ['b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7','878c7019b1b78c8affbf9808d69fdc8478554273fe5d06d499b6775b7d004f23'];basis='G18 actual baseline/candidate build receipt and all ten exact source files'
            else:assert not changed
            profile['identity'].update(package='g20-current-'+kind,manifest_sha256=pkgsha,artifact_sha256=digest)
            profiles.append({'package':kind,'profile':profile['name'],'old_identity':old,'identity':profile['identity'],'basis':basis,'source_files':profile.get('sources',[profile.get('source')])})
        dump(meta/'scan-manifest.json',scan);gate=json.loads((meta/'native-gates.json').read_text());gate['initialization']['manifest']['sha256']=sha(meta/'scan-manifest.json');dump(meta/'native-gates.json',gate)
        assert sha(native/'package.json')==sha(src/kind/'native/package.json');assert sha(root/'bundle.json')==sha(src/kind/'bundle.json')
    save(HERE/'n1-current-source-attestation.json',{'status':'UNSIGNED_SOURCE_BINDING','outer_approved':False,'from_assembly':'assembly-01 (untouched)','to_assembly':'assembly-02','source_changes':changes,'profiles':profiles,'evidence_pins':pins,'scope':'bounded source/DEX initialization scanner; not source-to-binary equivalence; no exceptions transferred','payload_changes':[]})
    print(json.dumps({'status':'N1_CURRENT_SOURCE_BOUND_UNSIGNED','profiles':len(profiles),'sidecar_source_updates':sum(r['changed'] for r in changes),'payload_changes':0}))
if __name__=='__main__':main()
