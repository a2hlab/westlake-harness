import json
from pathlib import Path
import shutil
import subprocess
import sys

from core import digest, prepared_bytes, encoded

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MASTER = REPO.parent / 'westlake-harness'
sys.path.insert(0, str(MASTER / 'scripts/lab'))
import native_predeploy
import generation_static_checks


def main():
    plan = json.loads((HERE / 'change-plan.json').read_text())
    output = HERE / '.artifacts/preview-gates'
    output.mkdir(parents=True, exist_ok=True)
    before = (MASTER / 'knowledge/gates/native-predeploy-exceptions.json').read_bytes()
    after15 = prepared_bytes(plan['stages'][0]['changes'][0], before, HERE)
    after16 = prepared_bytes(plan['stages'][1]['changes'][0], after15, HERE)
    registry = output / 'staged-native-registry.json'
    registry.write_bytes(after16)
    reader = shutil.which('llvm-readelf') or shutil.which('readelf')
    if not reader:
        candidates = sorted((Path.home() / 'Library').glob('**/llvm-readelf'))
        reader = str(candidates[0]) if candidates else None
    if not reader:
        raise RuntimeError('No local native reader')
    records = []
    for version, folder in [('u15', '2026-10-03-u15-on-u14-base'), ('u16', '2026-10-03-u16-final-assembly')]:
        roots = REPO / 'benchmark' / folder / '.artifacts'
        root = sorted(roots.glob('common-*'))[-1] if version == 'u15' else roots / 'common'
        native = root / 'native'
        report = native_predeploy.check_package(native, native / 'native-checks/native-gates.json', exceptions=registry, readelf=reader)
        native_raw = output / (version + '-native.json')
        native_raw.write_bytes(encoded(report))
        if report['exit_code'] != 0:
            raise RuntimeError('Staged native gate refused: ' + version)
        print(version + ' STAGED N1/N2 exit=' + str(report['exit_code']), flush=True)
        descriptor = json.loads((root / 'bundle.json').read_text())
        baseline_sha = descriptor['static_checks']['baseline_bundle_sha256']
        if version == 'u15':
            baseline_candidates = (REPO / 'benchmark/2026-10-03-u14-on-u13-base/.artifacts').glob('common-*')
        else:
            baseline_candidates = (REPO / 'benchmark/2026-10-03-u15-on-u14-base/.artifacts').glob('common-*')
        baseline = next(path for path in baseline_candidates if digest((path / 'bundle.json').read_bytes()) == baseline_sha)
        policy = json.loads((HERE / f'inputs/static-{version}-after.json').read_text())
        static = generation_static_checks.check(root, baseline, policy)
        static_raw = output / (version + '-static.json')
        static_raw.write_bytes(encoded(static))
        print(version + ' STAGED STATIC status=' + static['status'], flush=True)
        if static['status'] != 'PASS':
            raise RuntimeError('Staged static gate refused: ' + version)
        records.append(dict(version=version, native_exit=report['exit_code'], static_status=static['status'],
            native_report=str(native_raw), native_report_sha256=digest(native_raw.read_bytes()),
            static_report=str(static_raw), static_report_sha256=digest(static_raw.read_bytes()),
            N1_excepted=report['gates']['N1']['excepted'], N2_excepted=report['gates']['N2']['excepted']))
    selftests = []
    for index, command in enumerate(plan['selftests'], 1):
        result = subprocess.run(command, cwd=MASTER, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        raw = output / f'selftest-{index}.txt'
        raw.write_bytes(result.stdout)
        print('SELFTEST ' + command[1] + ' exit=' + str(result.returncode), flush=True)
        if result.returncode:
            sys.stdout.buffer.write(result.stdout)
            raise RuntimeError('Original active-table selftest refused')
        selftests.append(dict(command=command, exit_code=result.returncode, raw=str(raw), raw_sha256=digest(result.stdout),
            scope='Fresh original active-table known answers; actual post-write replay remains outer-only'))
    portable = lambda text: text.replace(str(REPO.parent) + '/', '$WORKSPACES/').replace(str(Path.home()) + '/', '$HOME/')
    summary = encoded(dict(staged_only=True, master_gate_writes=0, records=records, selftests=selftests)).decode()
    (HERE / 'preview-gates.json').write_text(portable(summary))
    evidence = HERE / 'evidence/preview'
    evidence.mkdir(parents=True, exist_ok=True)
    for path in output.glob('selftest-*.txt'):
        (evidence / path.name).write_text(portable(path.read_text(errors='backslashreplace')))


if __name__ == '__main__':
    main()
