#!/usr/bin/env python3
"""核验真实产物，生成小证据；不含板写或部署命令。"""
import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def elf_sections(p):
    blob = Path(p).read_bytes()
    assert blob[:6] == b'\x7fELF\x02\x01'
    h = struct.unpack_from('<16sHHIQQQIHHHHHH', blob)
    rows = [struct.unpack_from('<IIQQQQIIQQ', blob, h[6] + i * h[11]) for i in range(h[12])]
    names = blob[rows[h[13]][4]:rows[h[13]][4] + rows[h[13]][5]]
    out = {}
    for row in rows[1:]:
        name = names[row[0]:].split(b'\0')[0].decode()
        payload = b'' if row[1] == 8 else blob[row[4]:row[4] + row[5]]
        out[name] = {'size': row[5], 'flags': row[2], 'offset': row[4],
                     'sha256': hashlib.sha256(payload).hexdigest()}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('run_dir', type=Path)
    a = ap.parse_args()
    run = a.run_dir.resolve()
    ws = lab_paths.workspaces()
    llvm = Path(os.environ.get('OH_LLVM_BIN', '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin'))
    env = dict(os.environ, PATH=str(llvm) + os.pathsep + os.environ['PATH'])
    baseline = ws / 'westlake-inputs/generations/u13-stageA-91272eaf-20261003/armed-bundle/native'
    loader = baseline / 'payload/route/libapp_native_loader.so'
    consumer = baseline / 'payload/runtime/appspawn-x'
    def redact(text):
        return text.replace(str(ws), '$WORKSPACES').replace(str(Path.home()), '$HOME')
    def emit(name, data):
        text = data if isinstance(data, str) else json.dumps(data, indent=2, ensure_ascii=False) + '\n'
        (HERE / name).write_text('\n'.join(line.rstrip() for line in redact(text).splitlines()) + '\n')
    facts = {'loader': {}, 'host': {}, 'boat': {}, 'persisted': {}}
    j = json.loads((run / 'receipt.json').read_text())
    assert j['rc'] == j['tee_rc'] == 0
    facts['persisted'] = {'run_dir': str(run), 'receipt_sha256': sha(run / 'receipt.json'),
                          'log_sha256': sha(run / 'build.log'), 'script_sha256': sha(run / 'build.sh'),
                          'elapsed_seconds': j['elapsed_seconds'], 'image_id': j['image_id'], 'inputs': j['inputs']}
    emit('build-receipt-summary.json', j)
    emit('build-commands.txt', (run / 'build.sh').read_text())
    emit('host-public.diff', (run / 'host-public.diff').read_text())
    for name, old, new, consumers in (
        ('loader', loader, run / 'loader-a.so', [consumer]),
        ('host', run / 'host-base', run / 'host-public', []),
    ):
        cmd = ['python3', str(REPO / 'scripts/lab/abi_diff.py'), '--old', str(old), '--new', str(new),
               '--json', str(run / (name + '-abi.json'))]
        for c in consumers:
            cmd += ['--consumer', str(c)]
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        emit(name + '-abi.txt', r.stdout + r.stderr)
        assert r.returncode == 0, r.stderr
        abi = json.loads((run / (name + '-abi.json')).read_text())
        emit(name + '-abi.json', abi)
        s1, s2 = elf_sections(old), elf_sections(new)
        sections = {k: {'old': s1.get(k), 'new': s2.get(k), 'identical': s1.get(k) == s2.get(k)}
                    for k in sorted(s1.keys() | s2.keys())}
        emit(name + '-sections.json', sections)
        facts[name] = {'old_sha256': sha(old), 'new_sha256': sha(new), 'abi_rc': r.returncode,
                       'identical_sections': sum(v['identical'] for v in sections.values()),
                       'section_count': len(sections)}
        out = subprocess.check_output([str(llvm / 'llvm-readelf'), '-h', '-S', '-d', str(new)], text=True)
        emit(name + '-readelf.txt', out)
    facts['loader']['second_build_sha256'] = sha(run / 'loader-b.so')
    assert facts['loader']['old_sha256'] == facts['loader']['new_sha256'] == facts['loader']['second_build_sha256']
    base_c = (run / 'host-base.c').read_text()
    public_c = (run / 'host-public.c').read_text()
    assert public_c.count('libicui18n.so:libGLESv2.so:libGLESv3.so:libjnigraphics.so') == 1
    source_repo = ws / 'westlake-harness-bms-deploy'
    loader_c = source_repo / 'benchmark/2026-09-30-n3-native/flutter/app_native_loader.c'
    owner = ['原样 loader 只有回调调用，实际命名空间配置函数在宿主。',
             '宿主源码采用本仓库 u15-jitsi/inputs/candidate-stock-host.c，未叠加 jitsi 或 audio 修改。']
    for p, patterns in ((loader_c, ['namespace_host_ops.create_configured_namespaces']),
                        (run / 'host-base.c', ['CreateConfiguredNamespaces', 'create_configured_namespaces =',
                                             'dlns_inherit(app_namespace, bridge_namespace'])):
        lines = p.read_text().splitlines()
        for i, line in enumerate(lines):
            if any(k in line for k in patterns):
                owner += [f'{p}:{i+1}'] + lines[max(0, i-2):i+5]
    emit('namespace-owner.txt', '\n'.join(owner) + '\n')

    boat = Path.home() / 'orca/00.Workspace-games-ad1ab0a7/.bridge-payload/zigzag-candidates/strict-boat-assembled-20260924T074522Z-25403/files/libandroid.so'
    old = baseline / 'payload/android/lib64/libandroid.so'
    b1, b2 = old.read_bytes(), boat.read_bytes()
    assert len(b1) == len(b2)
    diffs = [{'offset': i, 'old': x, 'new': y} for i, (x, y) in enumerate(zip(b1, b2)) if x != y]
    assert len(diffs) == 49 and sha(boat).startswith('adc125f4')
    facts['boat'] = {'source': str(boat), 'sha256': sha(boat), 'base_sha256': sha(old),
                     'base_runtime_sha256': sha(baseline / 'payload/android/lib64/liboh_android_runtime.so'),
                     'size': len(b2), 'differing_bytes': len(diffs), 'compilation_required': False,
                     'targets': ['/system/android/lib64/libandroid.so'],
                     'secondary_target': '/system/android/lib64/liboh_android_runtime.so',
                     'secondary_direct_replacement_verified': False,
                     'secondary_size': (baseline / 'payload/android/lib64/liboh_android_runtime.so').stat().st_size,
                     'secondary_matching_patch_bytes': sum((baseline / 'payload/android/lib64/liboh_android_runtime.so').read_bytes()[d['offset']] == d['old'] for d in diffs)}
    emit('boat-byte-diff.json', diffs)
    # 对现成 CLASSNAME_FIX 同样核验 ABI，判断无需重编并不只依据文件名。
    r = subprocess.run(['python3', str(REPO / 'scripts/lab/abi_diff.py'), '--old', str(old), '--new', str(boat),
                         '--json', str(run / 'boat-abi.json')], capture_output=True, text=True, env=env)
    assert r.returncode == 0
    emit('boat-abi.txt', r.stdout + r.stderr)
    emit('boat-abi.json', json.loads((run / 'boat-abi.json').read_text()))
    r = subprocess.run(['python3', str(REPO / 'scripts/lab/abi_diff.py'),
                         '--old', str(baseline / 'payload/android/lib64/liboh_android_runtime.so'),
                         '--new', str(boat), '--consumer', str(old),
                         '--json', str(run / 'boat-runtime-abi.json')], capture_output=True, text=True, env=env)
    emit('boat-runtime-abi.txt', r.stdout + r.stderr)
    emit('boat-runtime-abi.json', json.loads((run / 'boat-runtime-abi.json').read_text()))
    out = []
    for p in (run / 'host-base', run / 'host-public'):
        s = elf_sections(p)['.rodata']
        data = p.read_bytes()[s['offset']:s['offset'] + s['size']]
        out.append({v.decode('ascii') for v in re.findall(rb'[\x20-\x7e]{4,}', data)})
    emit('host-strings-diff.json', {'added': sorted(out[1]-out[0]), 'removed': sorted(out[0]-out[1])})
    # 保留完整输入树的清单于持久目录；入库只记录清单 SHA 与条目数。
    for name, root in (('toolchain', source_repo / 'bms/src/.work/b68-generation/.work/product-tls-generation/frozen/toolchain'),
                       ('sysroot', source_repo / 'bms/src/.work/b68-generation/.work/product-tls-generation/frozen/sysroot')):
        rows = {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
        path = run / (name + '-files.json')
        path.write_text(json.dumps(rows, indent=2) + '\n')
        facts['persisted'][name + '_tree'] = {'entries': len(rows), 'manifest_sha256': sha(path)}
    emit('facts.json', facts)
    print(json.dumps(facts, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
