"""Replay only master-tracked topic files plus the exact landing overlay; no board IO."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[4])
    args = parser.parse_args()
    source = args.source.resolve()
    workspaces = Path(os.environ.get('WORKSPACES', source.parent))
    master = workspaces / 'westlake-harness'
    topic = Path('benchmark/2026-10-03-u14-stage-a-plan')
    output = source / topic / 'window1/landing-repair-1214'
    listing = source / topic / 'window1/r3-config-landing.txt'
    tracked = subprocess.check_output(
        ['git', '-C', str(master), 'ls-files', '--', str(topic)], text=True).splitlines()
    overlay = [line.strip() for line in listing.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith('#')]
    receipts = []
    with tempfile.TemporaryDirectory(prefix='u14-landing-replay-', dir=workspaces) as temp:
        root = Path(temp)
        for rel in tracked:
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.check_output(['git', '-C', str(master), 'show', 'HEAD:' + rel]))
        for rel in overlay:
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / rel, target)
        command = ['python3', '-m', 'unittest', 'discover', '-s', str(root / topic), '-p', 'test*.py']
        for surface, prefix in [('mac', []), ('vm', ['orb', '-m', 'a2hlab', 'env',
                                                       'WORKSPACES=' + str(workspaces)])]:
            result = subprocess.run(prefix + command, cwd=root, capture_output=True, text=True)
            text = result.stdout + result.stderr
            (output / (surface + '-landed-tests.txt')).write_text(text)
            receipts.append({'surface': surface, 'exit_code': result.returncode,
                             'output': str(topic / 'window1/landing-repair-1214' / (surface + '-landed-tests.txt'))})
            print(surface + ':\n' + text, end='', flush=True)
    report = {'master_commit': subprocess.check_output(['git', '-C', str(master), 'rev-parse', 'HEAD'], text=True).strip(),
              'source': 'master git objects + exact r3-config-landing.txt overlay; private fixtures excluded',
              'overlay_files': len(overlay), 'board_access': False, 'tests': receipts}
    (output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    return max(row['exit_code'] for row in receipts)


if __name__ == '__main__':
    raise SystemExit(main())
