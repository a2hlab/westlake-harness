"""Replay the pinned child compile/link recipe; prove the baseline before the edit."""
import hashlib
import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p/"scripts/lab/u7_executor.py").is_file())
B68 = REPO.parent / 'westlake-harness-bms-deploy/bms/src/.work/b68-generation'
PLUGIN = B68 / 'adapter/framework/appspawn-x/security_specialization/stock_child_plugin'
PASS = PLUGIN / 'out/target/pass1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inputs = json.loads((HERE.parent / '2026-10-01-n10-native/child-inputs.json').read_text())
commands_file = PLUGIN / 'out/target/logs/commands.txt'
assert sha(commands_file) == inputs['original_commands_sha256']
assert sha(PASS / 'libwestlake_android_child.z.so') == inputs['child_baseline']
for name, digest in inputs['objects'].items():
    assert sha(PASS / name) == digest, name
commands = [shlex.split(line) for line in commands_file.read_text().splitlines()]
compile_cmd = next(a for a in commands if '-c' in a and a[a.index('-c') + 1].endswith('/sealed_child_provider_loader.c') and '/pass1/' in a[a.index('-o') + 1])
link_cmd = next(a for a in commands if '-shared' in a and '-o' in a and a[a.index('-o') + 1] == str(PASS / 'libwestlake_android_child.z.so'))
out_root = Path(os.environ.get('N10B_BUILD_OUT', str(REPO.parent / 'westlake-n10b-build')))
env = os.environ.copy()
env['LD_LIBRARY_PATH'] = str(B68 / '.work/product-tls-generation/frozen/toolchain/runtime')
receipts = {}
for variant in ('baseline', 'candidate', 'repeat'):
    out = out_root / ('child-' + variant)
    out.mkdir(parents=True, exist_ok=False)
    for p in PASS.glob('*.o'):
        shutil.copy2(p, out / p.name)
    cc = list(compile_cmd)
    # Baseline retains the original source path and identical arguments.
    if variant != 'baseline':
        cc[cc.index('-c') + 1] = str(HERE / 'src/sealed_child_provider_loader.c')
    cc[cc.index('-o') + 1] = str(out / 'sealed_child_provider_loader.o')
    ld = [str(out / Path(x).name) if x.endswith('.o') and Path(x).parent == PASS else x for x in link_cmd]
    ld[ld.index('-o') + 1] = str(out / 'libwestlake_android_child.z.so')
    for argv in (cc, ld):
        subprocess.run(argv, env=env, check=True)
    binary = out / 'libwestlake_android_child.z.so'
    receipts[variant] = {'sha256': sha(binary), 'commands': [cc, ld],
                         'objects': {p.name: sha(p) for p in out.glob('*.o')}}
    if variant == 'baseline':
        assert sha(binary) == inputs['child_baseline'], 'baseline child rebuild differs'
    if variant == 'repeat':
        assert receipts['candidate']['sha256'] == sha(binary), 'candidate child repeat differs'
(HERE / 'child-build-receipt.json').write_text(json.dumps(receipts, indent=2) + '\n')
print('baseline exact; candidate repeat exact', receipts['candidate']['sha256'])
