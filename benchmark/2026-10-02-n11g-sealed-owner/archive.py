"""Preserve the build sources, seed objects and exact frozen SDK outside .work."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORKSPACES = Path(os.environ.get('WORKSPACES', REPO.parent)).resolve()
DEST = WORKSPACES / 'westlake-inputs/generations/n11g-u9-sealed-owner-v1'
SOURCE = DEST / 'source'
SOURCE.mkdir(exist_ok=False)
for sub in ('src', 'include'):
    shutil.copytree(HERE / sub, SOURCE / sub)
for filename in ('build.py', 'prepare.py', 'n11g-vs-n11f.patch', 'build-receipt.json', 'test_result_channel.py', 'test_callback.py'):
    shutil.copyfile(HERE / filename, SOURCE / filename)
baseline = REPO / 'benchmark/2026-10-01-n11f-owner-callback'
shutil.copytree(baseline / 'src', SOURCE / 'n11f-baseline/src')
shutil.copytree(baseline / 'include', SOURCE / 'n11f-baseline/include')
shutil.copyfile(baseline / 'build-receipt.json', SOURCE / 'n11f-baseline/build-receipt.json')
record = json.loads((baseline / 'build-receipt.json').read_text())['variants']['candidate']
commands = [[v.replace('$WORKSPACES', str(WORKSPACES)) for v in c] for c in record['commands']]
roots = set()
for command in commands:
    for i, value in enumerate(command):
        if value in ('-include', '-isystem'):
            roots.add(Path(command[i + 1]))
        elif value.startswith('-I'):
            roots.add(Path(value[2:]))
        elif value.startswith('--sysroot='):
            roots.add(Path(value.split('=', 1)[1]))
        elif value.startswith('-B'):
            roots.add(Path(value[2:]).parent)
roots.add(Path(commands[0][0]).parents[1])
seed = Path(commands[-1][-1]).parent
roots.add(seed)
roots = sorted(roots, key=lambda p: (len(p.parts), str(p)))
selected = []
for root in roots:
    if not any(root == parent or parent in root.parents for parent in selected):
        selected.append(root)
inputs = DEST / 'frozen-build-inputs'
inputs.mkdir()
mapping = []
for i, root in enumerate(selected):
    target = inputs / ('input-%02d' % i)
    if root.is_dir():
        # APFS clone retains the exact bytes without consuming a second SDK copy.
        subprocess.run(['cp', '-cR', str(root), str(target)], check=True)
    else:
        shutil.copyfile(root, target)
    mapping.append({'origin': str(root).replace(str(WORKSPACES), '$WORKSPACES'),
                    'archived': str(target.relative_to(DEST)), 'directory': root.is_dir()})
plugin = WORKSPACES / 'westlake-harness-bms-deploy/bms/src/.work/b68-generation/adapter/framework/appspawn-x/security_specialization/stock_child_plugin'
shutil.copytree(plugin, SOURCE / 'stock-child-plugin', ignore=shutil.ignore_patterns('out', '.git', '.work'))
inventory = {}
for tree in (SOURCE, inputs):
    for f in tree.rglob('*'):
        if f.is_file():
            inventory[str(f.relative_to(DEST))] = hashlib.sha256(f.read_bytes()).hexdigest()
(DEST / 'source-SHA256SUMS.json').write_text(json.dumps(inventory, indent=2) + '\n')
(DEST / 'input-map.json').write_text(json.dumps(mapping, indent=2) + '\n')
print('archived files', len(inventory), 'input roots', len(mapping))
