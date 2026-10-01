"""Relink exact N8 Bionic objects with the real-work LIBC version node."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
INPUTS = REPO.parent / 'westlake-harness-bms-deploy/bms/src/.work'
B68 = INPUTS / 'b68-generation'
FROZEN = B68 / '.work/product-tls-generation/frozen'
SYS = FROZEN / 'sysroot'
POOL = B68 / 'platform-pool/system/lib64'
OBJS = INPUTS / 'n7-native'
CC = Path(os.environ.get('N10_MAC_CLANG', '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/clang'))
OUT = REPO.parent / 'westlake-n10-build'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(OBJS / 'libbionic_compat.so') == '99c51df8020702c4d7166d75738458bf6c57c7752b3aaaf26957e8875e9d7988'
names = ['system_properties', 'malloc_compat', 'fdsan_stubs', 'misc_compat',
         'abort_message_compat', 'liblog_android_supplement', 'sync_builtins',
         'strerror_r_compat', 'dlopen_ext_compat']
objects = [OBJS / (name + '.o') for name in names]
inputs = objects + [POOL / 'platformsdk/libbegetutil.z.so', POOL / 'chipset-sdk-sp/libc++.so']
common = [str(CC), '--target=aarch64-linux-ohos', '--sysroot=' + str(SYS),
          '-B' + str(CC.parent), '-B' + str(SYS / 'lib/aarch64-linux-ohos'),
          '-fuse-ld=lld', '-shared',
          '-Wl,-z,defs,-z,now,-z,relro,--no-undefined,--fatal-warnings,--gc-sections,--build-id=sha1,--hash-style=both',
          '-L' + str(SYS / 'lib/aarch64-linux-ohos'), '-Wl,-soname,libbionic_compat.so']
records = {}
for name, version in [('baseline', REPO / 'benchmark/2026-10-01-n7-native/src/bionic.map'),
                       ('1', HERE / 'src/bionic.map'), ('2', HERE / 'src/bionic.map')]:
    out = OUT / ('bionic-' + name)
    out.mkdir(exist_ok=False)
    command = common + ['-Wl,--version-script=' + str(version)] + [str(p) for p in objects]
    command += ['-Wl,--no-as-needed'] + [str(p) for p in inputs[len(objects):]]
    command += ['-Wl,--as-needed', '-lc', '-ldl', '-lpthread', '-o', str(out / 'libbionic_compat.so')]
    subprocess.run(command, check=True)
    records[name] = {'command': command, 'version_map_sha256': sha(version),
                     'sha256': sha(out / 'libbionic_compat.so')}
assert records['1']['sha256'] == records['2']['sha256']
(HERE / 'bionic-link-receipt.json').write_text(json.dumps({
    'strategy': 'retained N8 objects, no C/C++ source recompilation',
    'reason': 'OrbStack machine and Docker transport unavailable; local DevEco ELF link',
    'compiler': {'sha256': sha(CC), 'version': subprocess.check_output([str(CC), '--version'], text=True)},
    'inputs': {str(p): sha(p) for p in inputs}, 'runs': records}, indent=2) + '\n')
print(records['1']['sha256'])
