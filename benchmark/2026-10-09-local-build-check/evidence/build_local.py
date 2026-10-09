#!/usr/bin/env python3
"""只在独立目录本机编译；源工作区以只读方式挂载，不含板操作。"""
import argparse
import difflib
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run-dir', type=Path)
    args = ap.parse_args()
    subprocess.run([sys.executable, str(REPO / 'scripts/lab/check_frozen.py')], check=True)
    ws = lab_paths.workspaces()
    run = args.run_dir or ws / 'westlake-inputs/generations' / (
        'local-build-check-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    run.mkdir(parents=True, exist_ok=False)
    src_repo = ws / 'westlake-harness-bms-deploy'
    n3 = src_repo / 'benchmark/2026-09-30-n3-native'
    frozen = src_repo / 'bms/src/.work/b68-generation/.work/product-tls-generation/frozen'
    tc, sysroot = frozen / 'toolchain', frozen / 'sysroot'
    cc = tc / 'bin/clang-15'
    target = 'aarch64-linux-ohos'
    src = n3 / 'flutter'
    commands = [
        ['uname', '-a'], [str(cc), '--version'],
    ]
    common = [str(cc), '--target=' + target, '--sysroot=' + str(sysroot),
              '-B' + str(tc / 'bin'), '-isystem', str(sysroot / 'include' / target),
              '-fPIC', '-O2', '-g', '-ffunction-sections', '-fdata-sections',
              '-D__OHOS__', '-D_GNU_SOURCE', '-I' + str(src / 'include')]
    link = [str(cc), '--target=' + target, '--sysroot=' + str(sysroot),
            '-B' + str(tc / 'bin'), '-B' + str(sysroot / 'lib' / target),
            '-fuse-ld=lld', '-shared',
            '-Wl,-z,defs,-z,now,-z,relro,--no-undefined,--fatal-warnings,--gc-sections,--build-id=sha1,--hash-style=both',
            '-L' + str(sysroot / 'lib' / target), '-L' + str(run)]
    for label in ('loader-a', 'loader-b'):
        commands += [common + ['-std=c11', '-Wall', '-Wextra', '-Werror', '-fvisibility=hidden',
                               '-c', str(src / 'app_native_loader.c'), '-o', str(run / (label + '.o'))],
                     link + ['-Wl,-soname,libapp_native_loader.so',
                             '-Wl,--version-script=' + str(src / 'app_native_loader.map'),
                             str(run / (label + '.o')), '-lc', '-o', str(run / (label + '.so'))]]

    # 复制部署宿主的已归档源码；与原配方一样复用已哈希的对象文件。
    host_inputs = REPO / 'benchmark/2026-10-03-u15-jitsi-native-domain/inputs'
    shutil.copytree(host_inputs, run / 'host-inputs')
    host_src = (host_inputs / 'candidate-stock-host.c').read_text()
    old = ('    if (wants_bridge) {\n'
           '        result = dlns_inherit(app_namespace, bridge_namespace,\n'
           '                              bridge_shared_sonames);\n')
    new = ('    if (wants_bridge) {\n'
           '        static const char kAospPublicLibs[] =\n'
           '            "libicui18n.so:libGLESv2.so:libGLESv3.so:libjnigraphics.so";\n'
           '        char app_public[2 * PATH_MAX];\n'
           '        int app_public_len = snprintf(app_public, sizeof(app_public), "%s:%s",\n'
           '                                      bridge_shared_sonames, kAospPublicLibs);\n'
           '        if (app_public_len < 0 || (size_t)app_public_len >= sizeof(app_public)) {\n'
           '            return NamespaceResultFence(ENAMETOOLONG);\n'
           '        }\n'
           '        result = dlns_inherit(app_namespace, bridge_namespace, app_public);\n')
    assert host_src.count(old) == 1, '公开库表补丁锚点必须唯一'
    patched = host_src.replace(old, new)
    (run / 'host-base.c').write_text(host_src)
    (run / 'host-public.c').write_text(patched)
    (run / 'host-public.diff').write_text(''.join(difflib.unified_diff(
        host_src.splitlines(True), patched.splitlines(True), fromfile='host-base.c', tofile='host-public.c')))
    receipt = json.loads((REPO / 'benchmark/2026-10-01-u10-bundle/r2-host-build-receipt.json').read_text())
    def expand(v):
        return v.replace('$WORKSPACES', str(ws)).replace('$REPO', str(ws / 'westlake-harness-bms'))
    reused = receipt['reused_objects']
    for row in reused:
        assert sha(expand(row['path'])) == row['sha256'], row['path']
    for label in ('host-base', 'host-public'):
        compile_cmd, link_cmd = [[expand(v) for v in c] for c in receipt['runs'][0]['commands']]
        # 宿主原件用 Mac clang；容器能力检查明确改用 frozen Linux clang。
        compile_cmd[0] = link_cmd[0] = str(cc)
        compile_cmd[1:1] = ['-B' + str(tc / 'bin'), '-I' + str(run / 'host-inputs')]
        link_cmd[1:1] = ['-B' + str(tc / 'bin'), '-B' + str(sysroot / 'lib' / target)]
        old_obj = compile_cmd[compile_cmd.index('-o') + 1]
        compile_cmd[compile_cmd.index('-c') + 1] = str(run / 'host-current.c')
        compile_cmd[compile_cmd.index('-o') + 1] = str(run / (label + '.o'))
        link_cmd = [str(run / (label + '.o')) if v == old_obj else v for v in link_cmd]
        link_cmd[link_cmd.index('-o') + 1] = str(run / label)
        commands += [['cp', str(run / (label + '.c')), str(run / 'host-current.c')], compile_cmd, link_cmd]

    body = ['#!/bin/bash', 'set -euxo pipefail',
            'export LD_LIBRARY_PATH=' + shlex.quote(str(tc / 'runtime'))]
    body += [shlex.join(c) for c in commands]
    body += ['sha256sum ' + ' '.join(shlex.quote(str(run / n)) for n in
              ('loader-a.so', 'loader-b.so', 'host-base', 'host-public'))]
    script = run / 'build.sh'
    script.write_text('\n'.join(body) + '\n')
    docker = ['docker', 'run', '--rm', '--platform', 'linux/amd64',
              '--name', 'cx-build-' + str(os.getpid()),
              '-v', f'{ws}:{ws}:ro', '-v', f'{run}:{run}:rw',
              '-w', str(src_repo), 'a2hlab-build:24.04', 'bash', str(script)]
    start = time.monotonic()
    # 真正的执行时 tee：stdout/stderr 合流，由 tee 持久记录全部原始字节。
    p = subprocess.Popen(docker, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    t = subprocess.Popen(['tee', str(run / 'build.log')], stdin=p.stdout)
    p.stdout.close()
    trc, rc = t.wait(), p.wait()
    manifest = {
        'schema': 1, 'rc': rc, 'tee_rc': trc, 'elapsed_seconds': round(time.monotonic() - start, 3),
        'run_dir': str(run), 'docker_command': docker,
        'image_id': subprocess.check_output(['docker', 'image', 'inspect', 'a2hlab-build:24.04',
                     '--format', '{{.Id}}'], text=True).strip(),
        'reused_objects': reused,
        'inputs': {str(p): sha(p) for p in [cc, tc / 'bin/ld.lld',
            sysroot / 'lib' / target / 'libc.so', src / 'app_native_loader.c',
            src / 'flutter_domain.inc', src / 'app_native_loader.map', n3 / 'build-flutter.sh']},
        'files': {p.name: sha(p) for p in run.iterdir() if p.is_file()},
    }
    shutil.copytree(src, run / 'loader-source-snapshot')
    (run / 'receipt.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('RUN_DIR=' + str(run), 'rc=' + str(rc), 'seconds=' + str(manifest['elapsed_seconds']))
    return rc or trc


if __name__ == '__main__':
    sys.exit(main())
