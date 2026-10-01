"""Replay host r3 with identities read from the immutable U9 deployment package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'benchmark/2026-10-01-u10-bundle'))
from build_host import bind_macros


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--workspaces', type=Path, default=os.environ.get('WORKSPACES', REPO.parent))
    args = parser.parse_args()
    w = args.workspaces.resolve()
    donor = w / 'westlake-harness-bms/benchmark/2026-10-01-u10-native-shims'
    recipe = donor / 'evidence/host-r3/build-receipt.json'
    record = json.loads(recipe.read_text())
    base = w / 'westlake-generation-u9-j10g-238ffc14/native'
    manifest = json.loads((base / 'package.json').read_text())
    child = base / 'payload/runtime/libwestlake_android_child.z.so'
    args.out.mkdir(parents=True, exist_ok=False)
    source = donor / '.artifacts/host-r3/candidate-stock-host.c'
    header = donor / 'host-r3/resident-compat.h'
    assert sha(source) == record['source_sha256']
    assert sha(header) == record['resident_header_sha256']
    assert sha(child) == manifest['files']['payload/runtime/libwestlake_android_child.z.so']
    expand = lambda v: v.replace('$REPO-deploy', str(w / 'westlake-harness-bms-deploy')).replace('$REPO', str(w / 'westlake-harness-bms')).replace('$WORKSPACES', str(w)).replace('$OUT', str(donor / '.artifacts/host-r3'))
    cc = [expand(v) for v in record['commands'][2]]
    ld = [expand(v) for v in record['commands'][3]]
    assert sha(cc[0]) == record['compiler_sha256']
    reader = Path(cc[0]).parent / 'llvm-readelf'
    note = subprocess.check_output([str(reader), '-n', str(child)], text=True)
    build_id = re.search(r'Build ID: ([0-9a-f]+)', note)[1]
    cc = bind_macros(cc, manifest['generation'], sha(child), build_id)
    original_obj = cc[cc.index('-o') + 1]
    expected_objects = {row['sha256'] for row in record['reused_objects']}
    for value in ld:
        if value.endswith('.o') and value != original_obj:
            assert sha(value) in expected_objects, 'reused object drift: ' + value
    runs = []
    for number in [1, 2]:
        compile_command = list(cc)
        obj, target = args.out / f'host-{number}.o', args.out / f'appspawn-x-{number}'
        compile_command[compile_command.index('-o') + 1] = str(obj)
        link_command = [str(obj) if v == original_obj else v for v in ld]
        link_command[link_command.index('-o') + 1] = str(target)
        with (args.out / f'build-{number}.log').open('w') as log:
            for command in [compile_command, link_command]:
                subprocess.run(command, check=True, cwd=w / 'westlake-harness-bms', stdout=log, stderr=subprocess.STDOUT)
        runs.append({'sha256': sha(target), 'commands': [[v.replace(str(w), '$WORKSPACES') for v in command] for command in [compile_command, link_command]]})
    assert runs[0]['sha256'] == runs[1]['sha256'] == record['artifacts']['candidate']
    result = {'schema': 'u10.1-bound-host/v1', 'recipe_sha256': sha(recipe),
              'compiler_sha256': record['compiler_sha256'], 'source_sha256': sha(source),
              'header_sha256': sha(header), 'runtime_generation': manifest['generation'],
              'child_sha256': sha(child), 'child_build_id': build_id,
              'repeat_identical': True, 'matches_r3_component': True,
              'runs': runs, 'reused_objects': record['reused_objects'],
              'generation_reason': 'Actual immutable U9 provider/child ABI generation retained; no new ART/provider generation invented.'}
    (args.out / 'host-build-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['runtime_generation', 'child_sha256', 'child_build_id', 'repeat_identical']}))
    print(runs[0]['sha256'])


if __name__ == '__main__':
    main()
