#!/usr/bin/env python3
"""Stage pinned WMC baseline inputs and emit argv only; never compile or launch a VM."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
ARCHIVE_SHA = '922e0291a10cc73a1cb6833c19c92c7baab163a7b1a23d92023657b1c40e8fa2'


def need(ok, msg):
    if not ok:
        raise ValueError(msg)


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def dump(p, obj):
    with p.open('x') as f:
        json.dump(obj, f, indent=2)
        f.write('\n')


def safe_name(name):
    p = PurePosixPath(name)
    need(name and not p.is_absolute() and '..' not in p.parts and
         str(p) == name and '\\' not in name, 'unsafe archive/manifest path: ' + name)
    return p


def checked_members(t):
    members = {}
    for m in t:
        safe_name(m.name)
        need(m.name not in members, 'duplicate tar member')
        need(m.isfile() or m.isdir(), 'tar links/special files rejected: ' + m.name)
        members[m.name] = m
    return members


def verify(p, row):
    need(p.is_file() and p.stat().st_size == row['bytes'] and sha(p) == row['sha256'],
         'input mismatch: ' + str(p))


def put(source, dest, row):
    verify(source, row)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() or dest.is_symlink():
        verify(dest, row)
        return
    with source.open('rb') as src, dest.open('xb') as dst:
        shutil.copyfileobj(src, dst)
    shutil.copymode(source, dest)
    verify(dest, row)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, default=HERE.parents[2])
    ap.add_argument('--archive', type=Path)
    ap.add_argument('--sdk', type=Path, required=True)
    ap.add_argument('--sdk-files', type=Path, default=HERE/'.private/sdk-files.json')
    ap.add_argument('--mac-sdk', type=Path, default=Path('/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native'))
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--linux-stage-root', type=Path, help='Same staged tree as visible to future Linux executor; default is exact local OUT')
    a = ap.parse_args()
    for name, expected in json.loads((HERE/'input-pins.json').read_text()).items():
        p = (HERE/name).resolve()
        need(sha(p) == expected, 'metadata pin mismatch: ' + name)
    lock = json.loads((HERE/'sdk-lock.json').read_text())
    need(sha(a.sdk_files) == lock['manifest_sha256'], 'SDK manifest pin')
    sdkrows = json.loads(a.sdk_files.read_text())
    need(len(sdkrows) == lock['entries'], 'SDK manifest count')
    archive = a.archive or a.repo/'benchmark/2026-10-20-t18-build-evidence/source-closure/.private/archive-02/window.tar.gz'
    need(sha(archive) == ARCHIVE_SHA, 'archive SHA mismatch')
    out = a.out.absolute()
    # Never allow output to become a nested part of an input tree.
    for root in (a.sdk, a.repo, a.mac_sdk):
        if root == a.repo:
            continue  # a new private directory inside the worktree is intentional
        need(not out.resolve().is_relative_to(root.resolve()), 'output inside tool input')
    out.mkdir(parents=True, exist_ok=False)
    state = {'status': 'STAGING_INCOMPLETE', 'compile_executions': 0, 'link_executions': 0}
    try:
        inputs = out/'inputs'
        inputs.mkdir()
        records = out/'records'
        records.mkdir()
        deps = json.loads((PARENT/'compile-dependencies.json').read_text())
        links = json.loads((PARENT/'link-inputs.json').read_text())
        wanted = {}
        for r in deps:
            alt = r.get('alternative_snapshot')
            n = r['archive_member'] if r['archive_sha256'] else alt['member']
            wanted[n] = {'sha256': r['archive_sha256'] or alt['sha256'], 'bytes': r['archive_bytes'] if r['archive_sha256'] else alt['bytes']}
        for r in links:
            if 'archive' in r:
                wanted[r['archive']['member']] = r['receipt_pin']
        tools = json.loads((PARENT/'tools.json').read_text())
        with tarfile.open(archive) as t:
            members = checked_members(t)
            for r in tools:
                if r.get('archive_sha256'):
                    m = members[r['archive_member']]
                    wanted[m.name] = {'sha256': r['archive_sha256'], 'bytes': m.size}
            for n in ['artifacts.json','compile-window-manager.log','oh_window_manager_client.o.d']:
                key = 'ORB_WS/out-ability38/native-policy/'+n
                original = next(x for x in json.loads((PARENT/'original-records.json').read_text()) if x.get('archive_member') == key)
                wanted[key] = original
            for n, row in wanted.items():
                m = members[n]
                need(m.isfile() and m.size == row['bytes'], 'member size/type')
                dest = inputs/n
                dest.parent.mkdir(parents=True, exist_ok=True)
                with t.extractfile(m) as src, dest.open('xb') as dst:
                    shutil.copyfileobj(src, dst)
                dest.chmod(m.mode & 0o777 & ~0o022)
                verify(dest, row)
        # Explicit 9-header mapping; preserve both snapshot originals and mapped copies.
        header_map = []
        for r in deps:
            if r.get('alternative_snapshot'):
                alt = r['alternative_snapshot']
                put(inputs/alt['member'], inputs/r['archive_member'], alt)
                header_map.append({'from': alt['member'], 'to': r['archive_member'], 'sha256': alt['sha256']})
        dump(records/'header-mapping.json', header_map)
        # Full fixed SDK: links are accepted only when relative and resolving inside SDK.
        sd = a.sdk.resolve()
        actual = {p.relative_to(a.sdk).as_posix() for p in a.sdk.rglob('*') if p.is_file() or p.is_symlink()}
        need(actual == {r['path'] for r in sdkrows}, 'SDK file set drift')
        sdkdest = inputs/'ORB_WS/toolchains/ohos-sdk/native'
        retained_regular_links = []
        for r in sdkrows:
            safe_name(r['path'])
            src, dst = a.sdk/r['path'], sdkdest/r['path']
            need(src.resolve().is_relative_to(sd), 'SDK symlink escape')
            if 'symlink' in r:
                need(src.is_symlink() and str(src.readlink()) == r['symlink'] and not Path(r['symlink']).is_absolute(), 'SDK link drift/absolute link')
                verify(src, r)
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists() or dst.is_symlink():
                    need(not dst.is_symlink(), 'unexpected staged SDK link collision')
                    verify(dst, r)
                    retained_regular_links.append(r['path'])
                else:
                    dst.symlink_to(r['symlink'])
            else:
                need(not src.is_symlink(), 'SDK file became link')
                put(src, dst, r)
        for r in sdkrows:
            need((sdkdest/r['path']).resolve().is_relative_to(sdkdest.resolve()), 'staged SDK link escape')
            verify(sdkdest/r['path'], r)
        dump(records/'retained-regular-sdk-links.json', retained_regular_links)
        put(a.sdk_files, records/'sdk-files.json', {'sha256': lock['manifest_sha256'], 'bytes': a.sdk_files.stat().st_size})
        dests = {}
        for r in links:
            if 'archive' in r:
                dest = inputs/r['archive']['member']
            else:
                old = r['path'].replace('$REPO', str(a.repo)).replace('$HOME', str(Path.home())).replace('$MAC_SDK', str(a.mac_sdk))
                dest = out/'mac-tools/clang++' if r['argv_index'] == 0 else out/'t29-objects'/Path(old).name
                put(Path(old), dest, r['receipt_pin'])
            verify(dest, r['receipt_pin'])
            dests[r['argv_index']] = str(dest)
        lld = next(r for r in tools if r['path'] == '$MAC_SDK/llvm/bin/ld.lld')
        put(a.mac_sdk/'llvm/bin/ld.lld', out/'mac-tools/ld.lld', lld)
        # Both copied Mach-O tools use @loader_path/../lib; preserve exact SDK dylibs.
        for r in json.loads((HERE/'mac-support.json').read_text()):
            put(a.mac_sdk/r['path'], out/'lib'/Path(r['path']).name, r)
        original = json.loads((PARENT/'recorded-commands.json').read_text())
        link = list(original['link'])
        for i,p in dests.items(): link[i] = p
        link = [x.replace('$ORB_WS', str(inputs/'ORB_WS')) for x in link]
        (out/'build').mkdir()
        link[link.index('-o')+1] = str(out/'build/bridge-original-object.so')
        linux = a.linux_stage_root or out
        root = str(linux/'inputs/ORB_WS')
        comp = [x.replace('$HISTORICAL_ROOT_0', root).replace('$HISTORICAL_ROOT_1', root) for x in original['compile']]
        comp[comp.index('-o')+1] = str(linux/'build/oh_window_manager_client.o')
        comp[comp.index('-MF')+1] = str(linux/'build/oh_window_manager_client.o.d')
        relink = list(link)
        idx = [i for i,x in enumerate(relink) if x.endswith('/out-ability38/native-policy/oh_window_manager_client.o')]
        need(len(idx) == 1, 'exactly one WMC required')
        relink[idx[0]] = str(out/'build/oh_window_manager_client.o')
        relink[relink.index('-o')+1] = str(out/'build/bridge-recompiled-wmc.so')
        for name, argv in [('mac-original-relink',link),('linux-compile',comp),('mac-recompiled-relink',relink)]:
            need(not any('$' in x for x in argv), 'unresolved command alias')
            dump(out/(name+'.argv.json'), argv)
        # Preserve exact original record bytes, including original paths, privately.
        run = a.repo/'benchmark/2026-10-20-t29-window-observation/.private/production-01'
        for name in ['13-bridge-candidate.argv.json','13-bridge-candidate.stdout','13-bridge-candidate.stderr','13-bridge-candidate.rc']:
            src=run/'raw'/name
            row=next(r for r in json.loads((PARENT/'original-records.json').read_text()) if r.get('path','').endswith('/raw/'+name))
            put(src, records/name, row)
        art=inputs/'ORB_WS/out-ability38/native-policy/artifacts.json'
        origcomp=next(x['command'] for x in json.loads(art.read_text())['commands'] if x['label']=='compile-window-manager')
        dump(records/'original-compile.argv.json',origcomp)
        dump(records/'mapping.json',{'linux_stage_root':str(linux),'local_stage_root':str(out),'root0_and_root1':root,'include_order_preserved':True,'sys_types':'-include search operand, unchanged','nine_headers':header_map})
        state.update(status='STAGED_NOT_BUILT', link_inputs_verified=len(links), dep_entries_verified=len(deps), snapshot_headers=len(header_map), sdk_entries_verified=len(sdkrows), sdk_manifest_sha256=lock['manifest_sha256'], archive_sha256=ARCHIVE_SHA)
    except Exception as ex:
        state['error'] = str(ex)
        raise
    finally:
        dump(out/'staging-receipt.json',state)
    print(json.dumps(state,indent=2))

if __name__ == '__main__':
    main()
