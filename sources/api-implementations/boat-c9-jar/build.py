#!/usr/bin/env python3
"""Prepare pinned C9 inputs, then execute the unchanged historical producer offline."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--tools', type=Path, required=True)
    p.add_argument('--java', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    for key in ('baseline', 'tools', 'java', 'out'):
        setattr(a, key, getattr(a, key).resolve())
    lock = json.loads((HERE / 'source.lock.json').read_text())
    assert sha(a.baseline) == lock['baseline_sha256'], 'baseline hash mismatch'
    for entry in lock['sources']:
        assert sha(HERE / entry['path']) == entry['sha256'], 'source hash mismatch'
    for entry in lock['tools']:
        assert sha(a.tools / entry['name']) == entry['sha256'], 'tool hash mismatch'
    a.out.mkdir(parents=True, exist_ok=False)
    receipt = {'schema': 'boat-c9-jar-source-build/v1', 'commands': [],
               'producer_sha256': sha(HERE / 'producer.sh'), 'source_lock_sha256': sha(HERE / 'source.lock.json'),
               'java_sha256': sha(a.java), 'historical_logs_recovered': False}

    def run(argv, env=None):
        n = len(receipt['commands'])
        out, err = a.out / f'{n:02}.stdout.txt', a.out / f'{n:02}.stderr.txt'
        with out.open('wb') as stdout, err.open('wb') as stderr:
            proc = subprocess.run([str(x) for x in argv], env=env, stdout=stdout, stderr=stderr)
        normalized = []
        for arg in argv:
            text = str(arg)
            for path, token in [(a.out, '$OUT'), (a.java, '$JAVA'), (a.tools, '$TOOLS'), (HERE, '$SOURCE')]:
                text = text.replace(str(path), token)
            normalized.append(text)
        receipt['commands'].append({'argv': normalized, 'rc': proc.returncode,
                                    'stdout': {'file': out.name, 'sha256': sha(out)},
                                    'stderr': {'file': err.name, 'sha256': sha(err)}})
        assert proc.returncode == 0, 'producer failed; inspect raw logs'

    try:
        run([a.java, '-version'])
        with zipfile.ZipFile(a.baseline) as z:
            (a.out / 'baseline.dex').write_bytes(z.read('classes.dex'))
        cp = ':'.join(str(a.tools / e['name']) for e in lock['tools'] if e['name'] != 'smali-2.5.2.jar')
        run([a.java, '-cp', cp, 'org.jf.baksmali.Main', 'disassemble', a.out / 'baseline.dex',
             '--api', '23', '-o', a.out / 'our/smali'])
        donor = a.out / 'boat/smali/adapter/activity'
        donor.mkdir(parents=True)
        for path in (HERE / 'smali').glob('*.smali'):
            shutil.copy2(path, donor / path.name)
        tools = a.out / 'inputs/westlake-inputs/tools'
        tools.mkdir(parents=True)
        for entry in lock['tools']:
            shutil.copy2(a.tools / entry['name'], tools / entry['name'])
        # Producer removes only c9A/c9B inside this newly created scratch directory.
        env = {**os.environ, 'SC': str(a.out), 'WORKSPACES': str(a.out / 'inputs'),
               'BASE_JAR': str(a.baseline), 'PATH': str(a.java.parent) + os.pathsep + os.environ['PATH']}
        run(['bash', HERE / 'producer.sh'], env)
        output = a.out / 'oh-adapter-runtime.c9only.jar'
        actual = sha(output)
        receipt.update(output_sha256=actual, exact_historical_jar_equal=actual == lock['expected_jar_sha256'])
        assert actual == lock['expected_jar_sha256'], 'historical output hash mismatch'
        receipt.update(status='EXACT_HISTORICAL_JAR_MATCH', rc=0)
    except (AssertionError, OSError, KeyError, zipfile.BadZipFile) as exc:
        receipt.update(status='REJECT', rc=2, error=str(exc))
    (a.out / 'execution.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': receipt['status'], 'rc': receipt['rc']}))
    return receipt['rc']


if __name__ == '__main__':
    raise SystemExit(main())
