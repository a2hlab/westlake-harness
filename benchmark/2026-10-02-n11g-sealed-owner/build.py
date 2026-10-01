"""Reproduce N11f, then co-build the approved N11g callback routing change twice."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE_SOURCE = REPO / 'benchmark/2026-10-01-n11f-owner-callback'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--workspaces', type=Path, default=os.environ.get('WORKSPACES', REPO.parent))
    a = p.parse_args()
    workspace = a.workspaces.resolve()
    record = json.loads((BASE_SOURCE / 'build-receipt.json').read_text())['variants']['candidate']
    commands = [[v.replace('$WORKSPACES', str(workspace)) for v in c] for c in record['commands']]
    link_template = commands[-1]
    seed = Path(link_template[link_template.index('-o') + 1]).parent
    for name, digest in record['objects'].items():
        assert sha(seed / name) == digest, 'N11f link input drift: ' + name
    assert sha(seed / 'libwestlake_android_child.z.so') == record['sha256']
    a.out.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = str(Path(commands[0][0]).parents[1] / 'runtime')
    results = {'compiler_sha256': sha(commands[0][0]), 'baseline_expected': record['sha256'], 'variants': {}}
    for variant in ('baseline', 'candidate', 'repeat'):
        out = a.out / variant
        out.mkdir()
        for f in seed.glob('*.o'):
            shutil.copyfile(f, out / f.name)
        used = []
        with (out / 'build.log').open('w') as log:
            for template in commands[:-1]:
                assert '-c' in template
                command = template.copy()
                if variant != 'baseline':
                    command = [v.replace(str(BASE_SOURCE), str(HERE)) for v in command]
                filename = Path(command[command.index('-c') + 1]).stem + '.o'
                command[command.index('-o') + 1] = str(out / filename)
                subprocess.run(command, env=env, check=True, stdout=log, stderr=subprocess.STDOUT)
                if variant == 'baseline':
                    assert sha(out / filename) == record['objects'][filename], 'N11f object not reproduced: ' + filename
                used.append(command)
            link = [str(out / Path(v).name) if v.endswith('.o') and Path(v).parent == seed else v for v in link_template]
            link[link.index('-o') + 1] = str(out / 'libwestlake_android_child.z.so')
            subprocess.run(link, env=env, check=True, stdout=log, stderr=subprocess.STDOUT)
            used.append(link)
        digest = sha(out / 'libwestlake_android_child.z.so')
        if variant == 'baseline':
            assert digest == record['sha256'], 'N11f binary not reproduced'
        if variant == 'repeat':
            assert digest == results['variants']['candidate']['sha256'], 'N11g repeat not identical'
        results['variants'][variant] = {
            'sha256': digest,
            'commands': [[v.replace(str(workspace), '$WORKSPACES') for v in c] for c in used],
            'objects': {f.name: sha(f) for f in out.glob('*.o')},
        }
        (HERE / 'build-receipt.json').write_text(json.dumps(results, indent=2) + '\n')
        print(variant, digest, flush=True)


if __name__ == '__main__':
    main()
