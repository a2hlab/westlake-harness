"""Build N8 host/ANL with only the Jitsi owner scope added; strict repeat check."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
INPUT_REPO = REPO.parent / 'westlake-harness-bms-deploy'
B68 = INPUT_REPO / 'bms/src/.work/b68-generation'
FROZEN = B68 / '.work/product-tls-generation/frozen'
TC, SYS = FROZEN / 'toolchain', FROZEN / 'sysroot'
OUT = Path(os.environ.get('N10_BUILD_OUT', str(REPO.parent / 'westlake-n10-build')))
env = dict(os.environ, LD_LIBRARY_PATH=str(TC / 'runtime'))
recipe = json.loads((HERE / 'host-command-input.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
service = INPUT_REPO / 'bms/src/.work/b80-network-groups/candidate-service-1.o'
assert service.is_file()
records = {}
for n in (1, 2):
    out = OUT / ('scoped-' + str(n))
    out.mkdir(exist_ok=False)
    cc = list(recipe['compile'])
    cc[cc.index('-c') + 1] = str(HERE / 'src/host.c')
    cc[cc.index('-o') + 1] = str(out / 'host.o')
    cc += ['-I' + str(INPUT_REPO / 'bms/src/adapter/framework/app-native-loader/src')]
    ld = list(recipe['link'])
    ld[ld.index('-o') + 1] = str(out / 'appspawn-x')
    ld = [str(out / 'host.o') if x.endswith('/host/westlake_stock_host_main.o')
          else str(service) if x.endswith('/host/appspawn_service.o') else x for x in ld]
    common = [str(TC / 'bin/clang-15'), '--target=aarch64-linux-ohos',
              '--sysroot=' + str(SYS), '-B' + str(TC / 'bin'),
              '-isystem', str(SYS / 'include/aarch64-linux-ohos'),
              '-fPIC', '-O2', '-g', '-ffunction-sections', '-fdata-sections',
              '-D__OHOS__', '-D_GNU_SOURCE', '-I' + str(HERE / 'flutter/include')]
    anl_cc = common + ['-std=c11', '-Wall', '-Wextra', '-Werror', '-fvisibility=hidden',
                       '-c', str(HERE / 'flutter/app_native_loader.c'), '-o', str(out / 'anl.o')]
    anl_ld = common[:4] + ['-B' + str(SYS / 'lib/aarch64-linux-ohos'), '-fuse-ld=lld',
              '-shared', '-Wl,-z,defs,-z,now,-z,relro,--no-undefined,--fatal-warnings,--gc-sections,--build-id=sha1,--hash-style=both',
              '-L' + str(SYS / 'lib/aarch64-linux-ohos'), '-Wl,-soname,libapp_native_loader.so',
              '-Wl,--version-script=' + str(HERE / 'flutter/app_native_loader.map'),
              str(out / 'anl.o'), '-lc', '-o', str(out / 'libapp_native_loader.so')]
    commands = [cc, ld, anl_cc, anl_ld]
    for command in commands:
        subprocess.run(command, cwd=B68, env=env, check=True)
    records[str(n)] = {'commands': commands,
                      'outputs': {f: sha(out / f) for f in ['appspawn-x', 'libapp_native_loader.so']},
                      'link_objects': {x: sha(Path(x)) for x in ld if x.endswith('.o')}}
assert records['1']['outputs'] == records['2']['outputs'], 'scoped rebuild differs'
receipt = {'recipe_sha256': sha(HERE / 'host-command-input.json'),
           'sources': {str(p.relative_to(HERE)): sha(p) for p in [HERE / 'src/host.c', HERE / 'flutter/app_native_loader.c', HERE / 'flutter/flutter_domain.inc']},
           'runs': records}
(HERE / 'scoped-build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(records['1']['outputs'])
