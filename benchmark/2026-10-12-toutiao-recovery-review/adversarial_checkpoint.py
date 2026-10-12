#!/usr/bin/env python3
"""Pinned local candidate with the donor's isolated fake proc/commands, never a board."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
CHECKPOINT = HERE / 'candidate-checkpoint'
spec = importlib.util.spec_from_file_location('r1_fixture', CHECKPOINT / 'tests/test_watchdog.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
fixture.WATCH = CHECKPOINT / 'payload/watchdog.sh'
fixture.TOOL = CHECKPOINT / 'tests/fixture_tool.py'
original_write = Path.write_text


def inject_owner_write_failure(path, content, *args, **kwargs):
    if path.name == 'bash-env':
        content += '\nmkdir() { command mkdir "$@" || return; case "$1" in */state/lock) command mkdir "$1/owner";; esac; }\nexport -f mkdir\n'
    return original_write(path, content, *args, **kwargs)


def run_owner_failure():
    manifest = json.loads((CHECKPOINT / 'manifest.json').read_text())
    for entry in manifest['files']:
        if hashlib.sha256((CHECKPOINT / entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('immutable candidate checkpoint drift: ' + entry['path'])
    with mock.patch.dict(os.environ, {'R1_TEST_EVIDENCE': str(HERE / '.artifacts/adversarial-cases')}), \
            mock.patch.object(Path, 'write_text', inject_owner_write_failure):
        case = fixture.Harness(methodName='runTest')
        process, calls, files = case.run_case({'frames': ['feed', 'feed']}, polls=2)
    launches = [call for call in calls if call['command'] in ('parent_tool', 'spawn_tool')]
    result = {'candidate': str(fixture.WATCH.relative_to(HERE)),
              'candidate_sha256': hashlib.sha256(fixture.WATCH.read_bytes()).hexdigest(),
              'fault': 'lock/owner becomes a directory: shell printf owner write fails',
              'candidate_exit': process.returncode, 'launch_commands_after_failure': launches,
              'stderr': process.stderr, 'state': files.get('state/state'),
              'all_commands_are_fixture': True, 'board_access': False,
              'status': 'blocker' if launches or process.returncode == 0 else 'negative case refused'}
    return result


def main():
    print(json.dumps(run_owner_failure(), indent=2))


if __name__ == '__main__':
    main()
