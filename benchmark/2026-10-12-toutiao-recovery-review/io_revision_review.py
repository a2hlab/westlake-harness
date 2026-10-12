#!/usr/bin/env python3
"""Replay immutable R1 commit only in its isolated fake-proc harness."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
RELEASE = HERE / 'io-9763171a'
COMMIT = 'io-revision frozen checkpoint'
EXPECTED_SHA = '9763171a0b6dab1b23b72e454cb2c6256181298bc282e81b6ae8e38fa9577072'


def verify_release():
    manifest = json.loads((RELEASE / 'manifest.json').read_text())
    if manifest['revision'] != COMMIT or manifest['expected_watchdog_sha256'] != EXPECTED_SHA:
        raise ValueError('final release binding drift')
    for entry in manifest['files']:
        if hashlib.sha256((RELEASE / entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('immutable final release drift: ' + entry['path'])
    if hashlib.sha256((RELEASE / 'payload/watchdog.sh').read_bytes()).hexdigest() != EXPECTED_SHA:
        raise ValueError('wrong final candidate')
    return manifest


def run_case(name):
    verify_release()
    spec = importlib.util.spec_from_file_location('r1_final_fixture', RELEASE / 'tests/test_watchdog.py')
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    fixture.WATCH = RELEASE / 'payload/watchdog.sh'
    fixture.TOOL = RELEASE / 'tests/fixture_tool.py'
    original_write = Path.write_text
    inject = {
        'owner_write_failure': '\nmkdir() { command mkdir "$@" || return; case "$1" in */state/lock) command mkdir "$1/owner";; esac; }\nexport -f mkdir\n',
        'owner_readback_mismatch': '\ncat() { case "$1" in "$TT_STATE_ROOT/lock/owner") command printf "999 888 wrong-boot\\n";; *) command cat "$@";; esac; }\nexport -f cat\n',
        'sequence_write_failure': '\nmkdir "$TT_STATE_ROOT/sequence"\n',
        'instance_write_failure': '\nmkdir "$TT_STATE_ROOT/instance.txt"\n',
        'state_write_failure': '\nmkdir "$TT_STATE_ROOT/state"\n',
        'event_log_write_failure': '\nmkdir "$TT_STATE_ROOT/events.log"\n',
        'parent_output_write_failure': '\nmkdir "$TT_STATE_ROOT/parent-start.txt"\n',
        'spawn_output_write_failure': '\nmkdir "$TT_STATE_ROOT/spawn.txt"\n',
    }
    def injected_write(path, content, *args, **kwargs):
        if path.name == 'bash-env':
            content += inject.get(name, '')
        return original_write(path, content, *args, **kwargs)
    model = {'frames': ['feed', 'feed']}
    stop = False
    execute = True
    if name == 'pid_reuse':
        model = {'recycle_after_sleep': True}
    elif name == 'stop_at_entry':
        stop = True
    elif name == 'stop_during_observation':
        model = {'stop_after_sleep': True}
    elif name == 'snapshot_error':
        model = {'frames': ['snapshot_error']}
    elif name == 'manual_consent_feed':
        model = {'frames': ['privacy', 'feed', 'feed']}
    elif name == 'default_disabled':
        execute = False
    artifact_root = HERE / '.artifacts/io-9763171a' / name
    with mock.patch.dict(os.environ, {'R1_TEST_EVIDENCE': str(artifact_root)}), \
            mock.patch.object(Path, 'write_text', injected_write):
        case = fixture.Harness(methodName='runTest')
        process, calls, files = case.run_case(model, polls=3, stop=stop, execute=execute)
    launches = [call['command'] for call in calls if call['command'] in ('parent_tool', 'spawn_tool')]
    current_state = files.get('state/state', '').strip()
    if name in ('owner_write_failure', 'owner_readback_mismatch'):
        refused = process.returncode != 0 and not launches
    elif name in ('sequence_write_failure', 'instance_write_failure', 'state_write_failure', 'event_log_write_failure'):
        refused = process.returncode != 0 and current_state != 'READY'
    elif name == 'parent_output_write_failure':
        refused = process.returncode == 3 and not launches
    elif name == 'spawn_output_write_failure':
        refused = process.returncode == 3 and launches == ['parent_tool']
    elif name == 'pid_reuse':
        refused = process.returncode == 2 and launches.count('spawn_tool') == 1 and current_state == 'OWNER_REFUSED'
    elif name in ('stop_at_entry', 'default_disabled'):
        refused = process.returncode == 2 and not launches
    elif name == 'stop_during_observation':
        refused = process.returncode == 0 and files.get('state/stop') == 'operator marker' and current_state == 'STOPPED'
    elif name == 'snapshot_error':
        refused = process.returncode == 0 and current_state == 'UI_UNVERIFIED' and launches.count('spawn_tool') == 1
    else:
        refused = process.returncode == 0 and current_state == 'READY'
    result = {'case': name, 'commit': COMMIT, 'candidate_sha256': EXPECTED_SHA,
              'candidate_exit': process.returncode, 'state': current_state, 'launches': launches,
              'expected_safety_behavior': refused, 'verdict': 'pass' if refused else 'blocker',
              'stop_preserved': 'operator stop' in files.get('state/stop', '') or files.get('state/stop') == 'operator marker',
              'data_sentinels_verified_by_harness': True, 'no_forbidden_fixture_commands': True,
              'board_access': False, 'raw_cases': '$WORKSPACES/westlake-harness-bms/' + str(artifact_root.relative_to(HERE.parents[1]))}
    return result


def main():
    names = ['owner_write_failure', 'owner_readback_mismatch', 'sequence_write_failure',
             'instance_write_failure', 'state_write_failure', 'event_log_write_failure',
             'parent_output_write_failure', 'spawn_output_write_failure',
             'pid_reuse', 'stop_at_entry', 'stop_during_observation',
             'snapshot_error', 'manual_consent_feed', 'default_disabled']
    cases = [run_case(name) for name in names]
    result = {'commit': COMMIT, 'candidate_sha256': EXPECTED_SHA,
              'verdict': 'blocker' if any(case['verdict'] == 'blocker' for case in cases) else 'offline_accept',
              'cases': cases, 'board_access': False, 'ui_signed': False, 'seal_signed': False}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
