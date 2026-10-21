#!/usr/bin/env python3
"""Validate G10's recorded evidence without contacting any environment."""
import hashlib
import json
from pathlib import Path


def check(root):
    result = json.loads((root / 'results.json').read_text())
    evidence = {row['id']: row for row in json.loads((root / 'evidence.json').read_text())}
    current = evidence['current-status']['files']
    command = json.loads(current['.json']['text_sanitized'])
    assert command['argv'] == ['orbctl', 'status']
    assert command['rc'] == 1 and not command['timed_out']
    assert command['timeout_seconds'] == 15
    assert 0 <= command['end'] - command['start'] <= 15
    assert current['.stdout']['text_sanitized'].strip() == 'Stopped'
    assert current['.stderr']['text_sanitized'] == ''
    assert result['orb_stack_status'] == 'Stopped'
    assert result['a2hlab_machine_status'] == 'unknown'
    assert result['hw248_archive_sha256'] == 'unknown'
    assert result['hw248_compiler_sha256'] == 'unknown'
    assert result['outer_start_argv'] == ['orbctl', 'start', 'a2hlab']
    for key in ['build_performed', 'start_executed', 'rejected_operations_retried']:
        assert result[key] is False, key
    for key in ['device_operations', 'restart_operations', 'permission_changes']:
        assert result[key] == 0, key
    for tag in ['g09-status-correct-01', 'g09-status-correct-02']:
        files = evidence[tag]['files']
        assert files['.stdout']['text_sanitized'].strip() == 'Stopped'
        assert files['.rc']['text_sanitized'].strip() == '1'
    for tag in ['g09-true-01', 'g09-true-02', 'g09-true-03']:
        assert evidence[tag]['files']['.rc']['text_sanitized'].strip() == '124'
    assert 'Operation not permitted' in evidence['g09-fallback-env']['files']['.stderr']['text_sanitized']
    assert 'Operation not permitted' in evidence['g09-orb-processes']['files']['.json']['text_sanitized']
    inputs = json.loads((root / 'local-inputs.json').read_text())
    assert len(inputs) == result['local_pins_verified'] == 7
    for row in inputs:
        assert row['sha256'] == row['expected_sha256'] and row['matches']
        assert row['bytes'] > 0 and row['end'] >= row['start']
    assert inputs[0]['sha256'] == '61ff2def4508cafa6c1acd30c0c8436a5a760d5869a3520a140a216e39548bb6'
    assert inputs[3]['sha256'] == 'b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913'
    # Public checkouts retain sanitized evidence; lane checkout also checks originals.
    raw_checked = 0
    for row in evidence.values():
        for file in row['files'].values():
            raw = root / file['raw_path']
            if raw.exists():
                data = raw.read_bytes()
                assert hashlib.sha256(data).hexdigest() == file['sha256'], raw
                assert len(data) == file['bytes'], raw
                raw_checked += 1
    print(f'G10 evidence consistent; 7 pins; {raw_checked} original files checked; environment readiness unverified')


if __name__ == '__main__':
    check(Path(__file__).resolve().parent)
