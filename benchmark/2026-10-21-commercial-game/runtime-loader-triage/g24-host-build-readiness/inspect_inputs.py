#!/usr/bin/env python3
"""Local file inspection only. No compiler, device, network, git or build execution."""
import argparse, hashlib, json, os
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workspaces',type=Path,default=Path(os.environ.get('WORKSPACES',Path(__file__).resolve().parents[5])));args=ap.parse_args()
    w=args.workspaces.resolve();main=w/'westlake-harness';bms=w/'westlake-harness-bms';deploy=w/'westlake-harness-bms-deploy'
    card='benchmark/2026-10-02-u13-single-native';n3=deploy/'benchmark/2026-09-30-n3-native'
    out={'method':'read/hash local files only; no build or connection','checks':[]}
    def portable(p):return str(p).replace(str(w),'$WORKSPACES').replace(str(Path.home()),'$HOME')
    def resolve(s,repo=bms):return Path(s.replace('$WORKSPACES',str(w)).replace('$REPO',str(repo)))
    def check(p,expected=None,group='reference'):
        r={'group':group,'path':portable(p),'exists':p.is_file(),'expected_sha256':expected}
        if r['exists']:
            r.update(sha256=sha(p),size=p.stat().st_size)
            r['match']=r['sha256']==expected if expected else None
        out['checks'].append(r);return r
    receipt=json.loads((main/card/'host-build-receipt.json').read_text())
    for group in ('toolchain','reused_inputs','headers'):
        for p,expected in receipt[group].items():
            check(resolve(p),expected,'host_'+group)
            if group=='headers':check(bms/card/'.artifacts/frozen-headers'/expected,expected,'host_frozen_headers')
    for key,v in receipt['artifacts'].items():check(resolve(v['path']),v['sha256'],'host_artifact_'+key)
    out['host_original_commands']=[]
    for c in receipt['commands']:
        out['host_original_commands'].append({k:c[k] for k in ('exit_code','runtime_tee','raw_path','raw_sha256','evidence')})
        check(resolve(c['raw_path']),c['raw_sha256'],'host_original_raw_log')
        check(main/card/c['evidence'],None,'host_archived_log')
    link=receipt['commands'][1]['command'];dirs=[resolve(x[2:]) for x in link if x.startswith('-L')]
    out['host_link_library_resolution']=[]
    for x in link:
        if x.startswith('-l'):
            matches=[p/f'lib{x[2:]}.{ext}' for p in dirs for ext in ('so','a') if (p/f'lib{x[2:]}.{ext}').is_file()]
            out['host_link_library_resolution'].append({'flag':x,'first_existing_candidate':portable(matches[0]) if matches else None,'all_existing_candidates':[portable(p) for p in matches], 'note':'filesystem search-order check only; no linker trace'})
            if matches:check(matches[0],None,'host_unpinned_link_library')
        if x.startswith('-Wl,--version-script='):check(resolve(x.split('=',1)[1]),None,'host_link_version_script')
    native=bms/'benchmark/2026-10-03-u13-effective-rebind/.artifacts/bundle-v4/native'
    pins={'payload/runtime/appspawn-x':'2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e','payload/route/libapp_native_loader.so':'eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c'}
    for p,s in pins.items():check(native/p,s,'u13_payload')
    check(native/'native-checks/n4-host.c','8be12abcb99ccc5f7fbd01f31d04b41a0b47db83d0ceac7f6bfda872b34e7b90','host_source_sidecar')
    check(native/'native-checks/flutter_domain.inc','0117797953a738f248d13f9f8be04e76d6052f1e0f70cf0f0e5c88f16472c15b','anl_source_sidecar')
    for p,s in json.loads((n3/'source-sha256.json').read_text()).items():
        if p.startswith('flutter/') or p in ('src/native_abi.c','src/bionic_stdio_compat.c','src/native_abi.map'):check(n3/p,s,'n3_source')
    for p,s in json.loads((n3/'toolchain-identities.json').read_text()).items():
        if '/b68-generation/' in p:check(Path(p),s,'n3_toolchain_and_libc')
    check(deploy/'bms/src/.work/n3-native/flutter/libapp_native_loader.so',pins['payload/route/libapp_native_loader.so'],'n3_original_output')
    check(w/'westlake-generation-n1-aa57845c/payload/android/lib64/liboh_android_runtime.so',None,'n3_script_precondition_not_anl_link_input')
    for p in sorted((main/card/'sources/baseline/host').glob('*')):check(p,None,'host_baseline_source_snapshot')
    u12=main/'benchmark/2026-10-02-u12-private-zlib'
    u12r=json.loads((u12/'build-receipt.json').read_text())
    for name,expected in u12r['source_files'].items():check(u12/'inputs'/name,expected,'u12_exact_source')
    for name in ('candidate-stock-host.c','resident-compat.h','zlib-route.h'):check(main/card/'sources/baseline/host'/name,u12r['source_files'][name],'u13_baseline_matches_u12')
    refs=[main/'specs/commercial-game-round1/t16-runtime-loader-triage.spec.md',main/card/'host-build-receipt.json',main/card/'build.py',main/card/'host.patch',main/'benchmark/2026-10-02-u12-private-zlib/build-receipt.json',main/'benchmark/2026-10-02-u12-private-zlib/route.patch',main/'benchmark/2026-10-01-u10-bundle/r2-host-build-receipt.json',native/'package.json']
    refs += [n3/p for p in ('build-flutter.sh','build-final-loader.log','build-loader-host.log','source-sha256.json','toolchain-identities.json','results.json','source-origins.json')]
    refs += [deploy/'benchmark/2026-09-30-n4-native'/p for p in ('README.md','package.json','source-sha256.json')]
    refs += [main/'benchmark/2026-10-21-commercial-game/runtime-loader-triage'/p for p in ('g24-atfork-addendum/source-index.json','call-chain-01/source-index.json')]
    for p in refs:check(p,None,'provenance_reference')
    journal=Path.home()/'.local/share/westlake/commercial-game-20261021/g24-window02/journal.json';check(journal,None,'g24_journal')
    j=json.loads(journal.read_text());out['g24_expected']={p:s for p,s in j['plan']['expected'].items() if p.endswith('/appspawn-x') or p.endswith('/libapp_native_loader.so')}
    out['groups']={g:{'count':len(v),'missing':sum(not r['exists'] for r in v),'mismatch':sum(r.get('match') is False for r in v)} for g in sorted({r['group'] for r in out['checks']}) for v in [[r for r in out['checks'] if r['group']==g]]}
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
