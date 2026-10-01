"""Co-build the N11e loader, host plugin and manifest from the pinned N11b recipe."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--workspaces', type=Path, default=os.environ.get('WORKSPACES', REPO.parent))
    args = parser.parse_args()
    workspace = args.workspaces.resolve()
    record = json.loads((REPO/'benchmark/2026-10-01-n11b-early-owner/build-receipt.json').read_text())['candidate']
    recorded_workspace = record['commands'][0][0].split('/westlake-harness-bms-deploy/')[0]
    commands = [[v.replace(recorded_workspace, str(workspace)) for v in c] for c in record['commands']]
    loader_cc, original_link = commands
    seed = Path(original_link[original_link.index('-o')+1]).parent
    plugin = workspace/'westlake-harness-bms-deploy/bms/src/.work/b68-generation/adapter/framework/appspawn-x/security_specialization/stock_child_plugin'
    recorded = [shlex.split(line) for line in (plugin/'out/target/logs/commands.txt').read_text().splitlines()]
    compile_commands = {'sealed_child_provider_loader.c': loader_cc}
    for filename in ['westlake_android_child_plugin.c', 'sealed_provider_manifest.c']:
        compile_commands[filename] = next(command for command in recorded if '-c' in command
                                          and Path(command[command.index('-c')+1]).name == filename)
    for name, expected in record['objects'].items():
        assert sha(seed/name) == expected, 'N11b seed object drift: ' + name
    args.out.mkdir(parents=True, exist_ok=False)
    environment = os.environ.copy()
    # The compiler's runtime is a sibling of bin, independent of source-tree depth.
    environment['LD_LIBRARY_PATH'] = str(Path(loader_cc[0]).parents[1]/'runtime')
    results = {}
    for variant in ['baseline', 'candidate', 'repeat']:
        out = args.out/variant
        out.mkdir()
        for file in seed.glob('*.o'):
            shutil.copyfile(file, out/file.name)
        used = []
        with (out/'build.log').open('w') as log:
            for filename, template in compile_commands.items():
                command = template.copy()
                if variant != 'baseline':
                    command[1:1] = ['-include', str(HERE/'include/sealed_child_provider_loader.h'), '-I'+str(HERE/'include')]
                    command[command.index('-c')+1] = str(HERE/'src'/filename)
                elif filename == 'sealed_child_provider_loader.c':
                    command[command.index('-c')+1] = str(REPO/'benchmark/2026-10-01-n11b-early-owner/src'/filename)
                command[command.index('-o')+1] = str(out/(Path(filename).stem+'.o'))
                subprocess.run(command, env=environment, check=True, stdout=log, stderr=subprocess.STDOUT)
                if variant == 'baseline':
                    name = Path(filename).stem+'.o'
                    assert sha(out/name) == record['objects'][name], 'baseline source/command mismatch: ' + filename
                used.append(command)
            link = [str(out/Path(v).name) if v.endswith('.o') and Path(v).parent == seed else v
                    for v in original_link]
            link[link.index('-o')+1] = str(out/'libwestlake_android_child.z.so')
            subprocess.run(link, env=environment, check=True, stdout=log, stderr=subprocess.STDOUT)
            used.append(link)
        digest = sha(out/'libwestlake_android_child.z.so')
        if variant == 'baseline':
            assert digest == record['sha256'], 'N11b baseline not reproduced'
        if variant == 'repeat':
            assert digest == results['candidate']['sha256'], 'candidate repeat mismatch'
        results[variant] = {'sha256': digest, 'commands': [[v.replace(str(workspace), '$WORKSPACES') for v in c] for c in used],
                            'objects': {p.name: sha(p) for p in out.glob('*.o')}}
        (HERE/'build-receipt.json').write_text(json.dumps(results, indent=2)+'\n')
        print(variant, digest, flush=True)


if __name__ == '__main__':
    main()
