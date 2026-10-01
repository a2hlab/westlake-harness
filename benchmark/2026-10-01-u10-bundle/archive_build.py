"""Persist the host's resolved compile/link inputs and portable replay recipe."""
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
    parser.add_argument('--workspaces', type=Path, default=os.environ.get('WORKSPACES', REPO.parent))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspaces.resolve()
    root = args.root.resolve()
    directory = root / 'build' / 'host-closure'
    directory.mkdir(parents=True, exist_ok=False)
    record = json.loads(args.receipt.read_text())
    commands = [[arg.replace('$WORKSPACES', str(workspace)).replace('$REPO', str(REPO))
                 for arg in command] for command in record['runs'][0]['commands']]
    compiler = Path(commands[0][0])
    sdk = compiler.parents[2]
    assert sha(compiler) == record['compiler_sha256']
    preprocess = commands[0].copy()
    del preprocess[preprocess.index('-o'):preprocess.index('-o') + 2]
    preprocess += ['-M', '-MF', str(directory / 'dependencies.mk')]
    subprocess.run(preprocess, check=True)
    deptext = (directory / 'dependencies.mk').read_text().replace('\\\n', '')
    dependencies = [Path(name) for name in shlex.split(deptext.split(':', 1)[1])]
    link = commands[1].copy()
    link[link.index('-o') + 1] = str(directory / 'trace-host')
    trace = subprocess.run(link + ['-Wl,--trace'], check=True, capture_output=True, text=True)
    (directory / 'link-trace.log').write_text(trace.stdout + trace.stderr)
    assert sha(directory / 'trace-host') == record['runs'][0]['sha256']
    dependencies += [Path(line.strip()) for line in trace.stdout.splitlines()
                     if Path(line.strip()).is_file()]
    dependencies += [Path(arg.split('=', 1)[1]) for command in commands for arg in command
                     if arg.startswith('-Wl,--version-script=')]
    dependencies = sorted(set(dependencies))
    replacements = [(str(sdk), '$ROOT/build/host-closure/inputs/sdk'),
                    (str(workspace), '$ROOT/build/host-closure/inputs/workspaces')]
    rows = []
    for source in dependencies:
        original = str(source)
        target = original
        for before, after in replacements:
            target = target.replace(before, after)
        if not target.startswith('$ROOT/'):
            raise ValueError('unclassified resolved build input: ' + original)
        relative = target[len('$ROOT/'):]
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        rows.append({'file': relative, 'sha256': sha(destination),
                     'original': original.replace(str(workspace), '$WORKSPACES').replace(str(sdk), '$OHOS_SDK')})
    replay = []
    for number, command in enumerate(commands):
        remapped = []
        for arg in command:
            for before, after in replacements:
                arg = arg.replace(before, after)
            remapped.append(arg)
        remapped[0] = '$OHOS_SDK/llvm/bin/clang'
        remapped[remapped.index('-o') + 1] = '$OUT/host.o' if number == 0 else '$OUT/appspawn-x'
        if number == 1:
            remapped = ['$OUT/host.o' if arg == commands[0][commands[0].index('-o') + 1]
                        or arg.endswith('/build/host/host-1.o') else arg for arg in remapped]
        replay.append(remapped)
    receipt = {'schema': 'u10-resolved-host-inputs/v1', 'compiler_sha256': sha(compiler),
               'trace_relink_sha256': sha(directory / 'trace-host'), 'inputs': rows, 'commands': replay,
               'debug_path_note': 'Archived-source relocation may change debug paths; original two builds were byte-identical. Gate relocated rebuilds with ABI/calls before use.'}
    (directory / 'resolved-inputs.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'inputs': len(rows), 'bytes': sum((root / row['file']).stat().st_size for row in rows),
                      'trace_relink_identical': True}))


if __name__ == '__main__':
    main()
