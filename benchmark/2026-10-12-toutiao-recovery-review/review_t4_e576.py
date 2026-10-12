#!/usr/bin/env python3
"""Read one git object; replay only isolated, relocated integration fixtures."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
WORKSPACES = HERE.parents[2]
COMMIT = 'e5763d369cf61e925a2a09f1c7ace8019f818931'
PREFIX = 'benchmark/2026-10-12-toutiao-recovery-integration'
MANIFEST_SHA = '365ac62b5545ed9b45b0d53a64010ff4f2ed3596a2856a9314172dfde98fb370'
BINDING_SHA = 'd352c7681d733a11f759a38039477610d0ead79f6cfb7469cab0f9bf67d536f8'
OUTPUT = HERE / '.artifacts/t4-e576-independent-attempt3'
PACKAGE = OUTPUT / 'workspaces/westlake-harness-t0' / PREFIX


def digest(data):
    return hashlib.sha256(data).hexdigest()


def blob(name):
    return subprocess.run(['git', '-C', str(WORKSPACES / 'westlake-harness-t0'),
                           'show', COMMIT + ':' + PREFIX + '/' + name],
                          check=True, capture_output=True).stdout


def export_release():
    manifest_bytes = blob('release-manifest.json')
    binding_bytes = blob('bindings.json')
    assert digest(manifest_bytes) == MANIFEST_SHA
    assert digest(binding_bytes) == BINDING_SHA
    manifest = json.loads(manifest_bytes)
    bindings = json.loads(binding_bytes)
    names = {row['path'] for row in manifest['files']}
    names.update(['release-manifest.json', 'attempt.draft.json', 'README.md',
                  'service-proposal.disabled.json'])
    names.update(row['copy'] for row in bindings['sources'] if 'copy' in row)
    receipt = []
    for name in sorted(names):
        data = blob(name)
        path = PACKAGE / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        receipt.append({'path': name, 'sha256': digest(data), 'bytes': len(data)})
    for row in manifest['files']:
        assert digest((PACKAGE / row['path']).read_bytes()) == row['sha256']
    for row in bindings['sources']:
        if 'copy' in row:
            data = (PACKAGE / row['copy']).read_bytes()
        else:
            source = WORKSPACES / row['source'].removeprefix('$WORKSPACES/')
            data = source.read_bytes()
            target = OUTPUT / 'workspaces' / row['source'].removeprefix('$WORKSPACES/')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        assert digest(data) == row['sha256']
    (PACKAGE / 'evidence').mkdir(exist_ok=True)
    return {'commit': COMMIT, 'manifest_sha256': MANIFEST_SHA,
            'bindings_sha256': BINDING_SHA, 'files': receipt,
            'source_matches': len(bindings['sources']),
            'package': '$WORKSPACES/westlake-harness-bms/' + str(PACKAGE.relative_to(HERE.parents[1]))}


def load_fixture():
    spec = importlib.util.spec_from_file_location('frozen_t4_fixture', PACKAGE / 'tests/test_integration.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_case(fixture, name):
    mode = name if name not in ('empty_preimage', 'missing_classifier', 'jpeg_unsupported', 'deadline') else ('new_parent' if name == 'deadline' else 'normal')
    original_write = Path.write_text
    original_copy = shutil.copyfile

    class FixtureSocket:
        def __init__(self, *args, **kwargs):
            pass

        def bind(self, path):
            Path(path).write_bytes(b'isolated socket readiness sentinel')

        def close(self):
            pass

    def write_fixture(path, content, *args, **kwargs):
        if path.name == 'bash-env':
            content += '\n[() { if builtin [ "$1" = -S ]; then builtin [ -f "$2" ]; else builtin [ "$@"; fi; }\nexport -f [\n'
        result = original_write(path, content, *args, **kwargs)
        if path.name == 'auth.env':
            if name == 'empty_preimage':
                assert 'PREIMAGE' not in content
            if name == 'missing_classifier':
                (path.parent / 'state/screen-gate').unlink()
        return result

    def copy_fixture(source, target, *args, **kwargs):
        result = original_copy(source, target, *args, **kwargs)
        target = Path(target)
        if Path(source).name == 'record_command.py':
            text = target.read_text()
            hook = '\nclass FixtureSocket:\n def __init__(self,*args,**kwargs): pass\n def bind(self,path): Path(path).write_bytes(b"isolated socket readiness sentinel")\n def close(self): pass\nsocket.socket=FixtureSocket\n'
            target.write_text(text.replace("name, args = Path(sys.argv[0]).name, sys.argv[1:]", hook + '\nname, args = Path(sys.argv[0]).name, sys.argv[1:]'))
        if name == 'jpeg_unsupported' and target.name == 'screen-gate':
            target.write_text('#!/usr/bin/env python3\nimport sys\nprint("unknown");sys.exit(1)\n')
        if name == 'deadline' and target.name == 'timeout':
            target.write_text('#!/usr/bin/env python3\nimport subprocess,sys\ntry:\n result=subprocess.run(sys.argv[2:],timeout=float(sys.argv[1]));sys.exit(result.returncode)\nexcept subprocess.TimeoutExpired:\n sys.exit(124)\n')
        if name == 'deadline' and target.name == 'hidumper':
            text = target.read_text()
            hook = '\nif name == "hidumper":\n import time\n counter=root/"wms-count"\n number=int(counter.read_text())+1 if counter.exists() else 1\n counter.write_text(str(number))\n if number >= 3: time.sleep(17)\n'
            target.write_text(text.replace('if name == \'sha256sum\':', hook + '\nif name == \'sha256sum\':'))
        return result

    with mock.patch.object(Path, 'write_text', write_fixture), \
            mock.patch.object(shutil, 'copyfile', copy_fixture), \
            mock.patch.object(fixture.socket, 'socket', FixtureSocket):
        case = fixture.LaunchTests(methodName='runTest')
        process, calls, state = case.case(mode)
    launches = [row['command'] for row in calls if row['command'] in ('source_app_namespace', 'nsenter', 'host_spawn')]
    return {'case': name, 'exit': process.returncode, 'state': state,
            'launches': launches, 'diagnostics': process.evidence_diagnostics,
            'grading': 'relocated frozen shell; mocked native/identity/frame; not board proof'}


def main():
    assert not OUTPUT.exists(), 'Preserve prior attempt; do not overwrite a replay'
    receipt = export_release()
    fixture = load_fixture()
    print('FROZEN_COMMIT_AND_17_MANIFEST_FILES_MATCH', flush=True)
    cases = []
    names = ['normal', 'unsigned', 'wrong_boot', 'expired', 'wrong_candidate',
             'wrong_auth_sha', 'helper', 'socket', 'missing_jit', 'jit_parent_mismatch',
             'format', 'stale_window', 'empty_preimage', 'missing_classifier',
             'jpeg_unsupported', 'deadline']
    for name in names:
        row = run_case(fixture, name)
        cases.append(row)
        print(json.dumps({key: row[key] for key in ('case', 'exit', 'state', 'launches')}), flush=True)
    result = {'receipt': receipt, 'cases': cases, 'board_access': False,
              'execution_authorized': False, 'ui_signed': False, 'seal_signed': False,
              'socket_fixture': 'sandbox refused AF_UNIX; isolated regular-file sentinel and Bash -S test seam; not real socket proof'}
    (OUTPUT / 'result.json').write_text(json.dumps(result, indent=2))
    print('INDEPENDENT_RESULT_WRITTEN', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
