"""Trusted repository native preflight, including explicitly bound rollback targets."""
import hashlib
import datetime
import tempfile
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repository():
    here = Path(__file__).resolve()
    candidates = list(here.parents)
    if os.environ.get('WESTLAKE_DEPLOY_REPO'):
        candidates.insert(0, Path(os.environ['WESTLAKE_DEPLOY_REPO']).resolve())
    for root in candidates:
        if (root / '.git').exists() and (root / 'scripts/lab/native_predeploy.py').is_file():
            return root
    raise RuntimeError('native gate requires a trusted repository; set WESTLAKE_DEPLOY_REPO')


_EXPERIMENT = None
_EXPERIMENT_SERIAL = None

def configure_experiment(path, serial):
    global _EXPERIMENT, _EXPERIMENT_SERIAL
    _EXPERIMENT = Path(path).resolve() if path else None
    _EXPERIMENT_SERIAL = serial


def experiment_entries(package_sha):
    if _EXPERIMENT is None:
        return [], None
    data = json.loads(_EXPERIMENT.read_text())
    if data.get('schema_version') != 1 or data.get('serial') != _EXPERIMENT_SERIAL:
        raise RuntimeError('native experiment identity mismatch')
    # Restoring the independently approved baseline never depends on experiment expiry.
    if data.get('package_manifest_sha256') != package_sha:
        return [], None
    start = datetime.datetime.fromisoformat(data['issued_at'])
    end = datetime.datetime.fromisoformat(data['expires_at'])
    now = datetime.datetime.now(datetime.timezone.utc)
    if not start.tzinfo or not end.tzinfo or not (0 < (end-start).total_seconds() <= 1800):
        raise RuntimeError('native experiment must have a <=30 minute timezone-aware window')
    if data.get('status') != 'active' or not start <= now < end:
        raise RuntimeError('native experiment expired or revoked')
    rows = data['exceptions']
    if package_sha == '423ea1ff84627c71d445bbfef18766cba9646421bc0d73d94ab07389d1110d16':
        valid = len(rows) == 184 and sum(r['gate'] == 'N1' for r in rows) == 28 and sum(r['gate'] == 'N2' for r in rows) == 156
    elif package_sha in {'a77c7c6cfdc1c0f78a9f32dad2c184dabe049afedc9674774bd578fab1ab67ff', '3dd48299b599c2adebe8cc574649a31d84fabae53b77d5a7df704f4f380b993e'}:
        valid = len(rows) == 185 and sum(r['gate'] == 'N1' for r in rows) == 31 and sum(r['gate'] == 'N2' for r in rows) == 154
    else:
        valid = len(rows) == 57 and all(r['gate'] == 'N2' for r in rows)
    if not valid or any(r['package_manifest_sha256'] != package_sha for r in rows):
        raise RuntimeError('native experiment does not match approved candidate findings')
    return rows, sha(_EXPERIMENT)


def binding(package, root=None):
    package = Path(package).resolve(); root = root or repository()
    sidecar = package / 'native-checks/native-gates.json'
    if not sidecar.is_file():
        raise RuntimeError('native gate inputs missing: ' + str(sidecar))
    manifest = json.loads((package / 'package.json').read_text())
    for name, expected in manifest['files'].items():
        relative = Path(name); path = package / relative
        if relative.is_absolute() or '..' in relative.parts or path.is_symlink() or not path.resolve().is_relative_to(package):
            raise RuntimeError('unsafe native package path')
        if sha(path) != expected: raise RuntimeError('native package file changed: ' + name)
    files = {}
    for path in sorted(sidecar.parent.rglob('*')):
        if path.is_symlink(): raise RuntimeError('native sidecar symlink refused')
        if path.is_file(): files[str(path.relative_to(sidecar.parent))] = sha(path)
    code = {name: sha(root / 'scripts/lab' / name) for name in
            ['native_predeploy.py', 'native_gate_common.py', 'native_initialization_gate.py', 'native_needed_gate.py']}
    for name in ['scan_native_initialization.py', 'rules_native_initialization.py']:
        code[name] = sha(root / 'benchmark/2026-09-29-static-wall-prediction' / name)
    values = {'package': sha(package / 'package.json'), 'inputs': files, 'checker': code,
              'exceptions': sha(root / 'knowledge/gates/native-predeploy-exceptions.json'),
              'experiment': experiment_entries(sha(package / 'package.json'))[1]}
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def check(package, expected_binding=None):
    package = Path(package).resolve(); root = repository()
    before = binding(package, root)
    if expected_binding is not None and before != expected_binding:
        raise RuntimeError('native inputs changed across dispatch')
    reader = os.environ.get('NATIVE_READELF') or shutil.which('llvm-readelf') or shutil.which('readelf')
    if not reader: raise RuntimeError('native gate requires host readelf (NATIVE_READELF)')
    # Never import a checker from candidate/tools.
    scripts = str(root / 'scripts/lab'); sys.path.insert(0, scripts)
    for name in ['native_gate_common', 'native_initialization_gate', 'native_needed_gate', 'native_predeploy']:
        module = sys.modules.get(name)
        if module is not None and Path(module.__file__).resolve().parent != Path(scripts):
            raise RuntimeError('untrusted native checker already imported: ' + name)
    import native_predeploy
    extra, _ = experiment_entries(sha(package / 'package.json'))
    registry = root / 'knowledge/gates/native-predeploy-exceptions.json'
    if extra:
        combined = json.loads(registry.read_text())
        combined['exceptions'].extend(extra)
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json') as temporary:
            json.dump(combined, temporary); temporary.flush()
            report = native_predeploy.check_package(package, package / 'native-checks/native-gates.json', gate='all', exceptions=Path(temporary.name), readelf=reader)
    else:
        report = native_predeploy.check_package(package, package / 'native-checks/native-gates.json', gate='all', exceptions=registry, readelf=reader)
    print(json.dumps({'native_predeploy': report}, sort_keys=True), file=sys.stderr)
    if report['exit_code']:
        raise RuntimeError('native predeploy gate refused: ' + report['status'])
    if binding(package, root) != before:
        raise RuntimeError('native inputs changed during preflight')
    return {'binding': before, 'package': str(package), 'report': report}


def assert_unchanged(ticket):
    if binding(Path(ticket['package'])) != ticket['binding']:
        raise RuntimeError('native inputs changed after preflight')


def restore_target(state_path, serial, generation, target=None):
    if state_path is None:
        raise RuntimeError('rollback requires --rollback-state naming the owned state receipt')
    path = Path(state_path).resolve(); data = json.loads(path.read_text())
    if data.get('serial') != serial or data.get('generation') != generation:
        raise RuntimeError('rollback state identity mismatch')
    if data.get('status') in [None, 'rolled_back']:
        raise RuntimeError('rollback state is not active')
    if target:
        rows = data.get('single_replacements', [])
        if not rows or rows[-1]['target'] != target:
            raise RuntimeError('rollback target is not the last replacement')
        package = Path(rows[-1]['previous_package'])
        digest = rows[-1]['previous_package_sha256']
    else:
        previous = data.get('previous_deployment') or data.get('native_recovery_package')
        if not previous:
            raise RuntimeError('raw underlay rollback lacks native provenance; outer-reviewed recovery needed')
        package = Path(previous['package_path']); digest = previous['package_sha256']
    if sha(package / 'package.json') != digest:
        raise RuntimeError('rollback target package changed')
    return package, {'path': str(path), 'sha256': sha(path), 'boot_id': data['boot_id']}
