"""Hash-validated scan -> oh-resolve -> gap-map, without accessing a device.

Usage: static_pipeline.py corpus.json static-dir [--jobs 4]
An app may override runtime_index with a path to its own runtime snapshot.
Receipts live beside each gap map in pipeline-state.json. Legacy outputs without
receipts are archived and rebuilt. Successful stages of an interrupted run can
be resumed only while their identity and output hashes still match.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import lab_paths

A = Path('/home/dspfac/a2hlab/source-closure/verify')
O = A / 'out'
HARNESS = lab_paths.harness()
TOOL = str(Path.home() / 'a2hlab/harness-venv/bin/westlake-apk-gap')
SDK_LIBS = A / 'toolchains/ohos-sdk/native/sysroot/usr/lib/aarch64-linux-ohos'
LIB_DIRS = [SDK_LIBS, O / 'native-imports', O / 'native-runtime']
SCHEMA = 1


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('w') as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def tool_version():
    """Hash the actual imported implementation, not just an unchanged label."""
    import westlake_gap
    root = Path(westlake_gap.__file__).resolve().parent
    files = {str(p.relative_to(root)): sha256(p) for p in sorted(root.rglob('*'))
             if p.is_file() and p.suffix in {'.py', '.json'}}
    return {'package': importlib.metadata.version('westlake-apk-gap'),
            'implementation_sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
            'pipeline_sha256': sha256(__file__), 'entrypoint_sha256': sha256(TOOL),
            'python': sys.version.split()[0]}


def fingerprint(app, directory, version):
    runtime = Path(app.get('runtime_index', directory / 'runtime-index.json')).resolve()
    lock = read_json(runtime)
    return {'input_path': str(Path(app['input']).resolve()), 'input_sha256': sha256(app['input']),
            'runtime_index': str(runtime), 'runtime_index_sha256': sha256(runtime),
            'runtime_lock_id': lock['runtime_lock_id'], 'tool_version': version,
            'target_abi': 'arm64-v8a',
            'configuration': {'aosp_and_provider_root': str(A), 'harness': str(HARNESS),
                              'library_directories': [str(p) for p in LIB_DIRS], 'tool': TOOL}}


def run(command, log):
    with log.open('w') as out:
        return subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, cwd=HARNESS).returncode


def artifact_valid(stage, path, key, identity, digest):
    try:
        if not digest or sha256(path) != digest:
            return False
        value = read_json(path)
        if stage == 'scan':
            return (value['apk']['sha256'] == identity['input_sha256']
                    and value['runtime_lock_id'] == identity['runtime_lock_id']
                    and value['inventory']['native_resolution']['target_abi'] == identity['target_abi'])
        if stage == 'oh':
            return set(value['apps']) == {key}
        return value['app']['apk_sha256'] == identity['input_sha256'] and isinstance(value['rows'], list)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def archive(directory, key, paths, reason):
    existing = [path for path in paths if path.exists()]
    if not existing:
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    dest = directory / 'history' / key / stamp
    dest.mkdir(parents=True)
    write_json(dest / 'reason.json', {'reason': reason})
    for path in existing:
        shutil.move(str(path), str(dest / path.name))


def one(key, app, directory, version):
    if not key or Path(key).name != key or key in {'.', '..'}:
        return key, 'failed (invalid app key)'
    logs = directory / 'logs'
    scan = directory / 'scans' / f'{key}.json'
    oh = directory / 'oh' / f'{key}.json'
    gap_dir = directory / 'maps' / key
    gap = gap_dir / 'gap-map.json'
    state_path = gap_dir / 'pipeline-state.json'
    outputs = {'scan': scan, 'oh': oh, 'gap-map': gap}
    try:
        identity = fingerprint(app, directory, version)
        try:
            state = read_json(state_path)
        except (OSError, ValueError):
            state = {}
        if not isinstance(state, dict) or state.get('schema') != SCHEMA or state.get('fingerprint') != identity:
            # Give scan and OH distinct names in the archive (both are <key>.json).
            for label, path in [('scan', scan), ('oh', oh), ('map', gap_dir)]:
                archive(directory, key, [path], 'identity changed or receipt missing: ' + label)
            state = {'schema': SCHEMA, 'fingerprint': identity, 'stages': {}}
        elif not isinstance(state.get('stages'), dict):
            state['stages'] = {}
        commands = {
            'scan': [TOOL, 'scan', app['input'], '--runtime', identity['runtime_index'],
                     '--target-abi', 'arm64-v8a', '--out', str(scan)],
            'oh': [TOOL, 'oh-resolve', '--scan', str(scan), '--app-key', key,
                   '--board', 'OH 6.1.0.31 SDK + firmware stubs + westlake main runtime', '--out', str(oh)],
            'gap-map': [TOOL, 'gap-map', '--scan', str(scan), '--apk', app['input'],
                        '--aosp', str(A / 'android-source'), '--westlake', str(A / 'westlake'),
                        '--westlake-label', 'westlake main 22b9453 (source build)',
                        '--manifest-repo', str(Path.home() / 'a2hlab/manifest'),
                        '--oh-resolution', str(oh), '--app-key', key,
                        '--board-libs', str(HARNESS / 'benchmark/2026-09-18-oh-board/oh-board-libraries.txt'),
                        '--runtime-libs', str(O / 'native-runtime'), '--out', str(gap_dir)]}
        for lib in LIB_DIRS:
            commands['oh'] += ['--lib-dir', str(lib)]
        rerun = False
        for stage, path in outputs.items():
            if rerun or not artifact_valid(stage, path, key, identity, state['stages'].get(stage)):
                rerun = True
                # Invalidate this stage and every downstream receipt BEFORE launching.
                stages = list(outputs)
                for downstream in stages[stages.index(stage):]:
                    state['stages'].pop(downstream, None)
                    outputs[downstream].unlink(missing_ok=True)
                write_json(state_path, state)
                log_name = 'gapmap' if stage == 'gap-map' else stage
                if run(commands[stage], logs / f'{key}.{log_name}.log'):
                    path.unlink(missing_ok=True)
                    return key, f'{stage} failed'
                digest = sha256(path)
                if not artifact_valid(stage, path, key, identity, digest):
                    path.unlink(missing_ok=True)
                    return key, f'{stage} failed (invalid output identity/schema)'
                state['stages'][stage] = digest
                write_json(state_path, state)
            if stage == 'scan':
                abi = read_json(scan)['inventory']['native_resolution']['abi_status']
                if abi not in {'target-abi-available', 'no-packaged-native-libraries'}:
                    return key, f'failed (unsupported ABI: {abi})'
        return key, f'ok ({abi}; {"rebuilt" if rerun else "cached"})'
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return key, f'failed ({type(exc).__name__}: {exc})'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus', type=Path)
    parser.add_argument('static_dir', type=Path)
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    directory = args.static_dir.resolve()
    for sub in ('scans', 'oh', 'maps', 'logs'):
        (directory / sub).mkdir(parents=True, exist_ok=True)
    # One writer per output tree; source APKs and runtime snapshots remain read-only.
    import fcntl
    with (directory / '.pipeline.lock').open('a') as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        apps = read_json(args.corpus)['apps']
        version = tool_version()
        failed = False
        with ThreadPoolExecutor(args.jobs) as pool:
            for key, status in pool.map(lambda kv: one(kv[0], kv[1], directory, version), apps.items()):
                print(f'{key:28s} {status}', flush=True)
                failed |= not status.startswith('ok (')
        return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
