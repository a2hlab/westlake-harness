#!/usr/bin/env python3
"""Local evidence audit only. This module never executes a candidate or device tool."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
WORKSPACES = Path(os.environ.get('WORKSPACES', HERE.parents[2]))
BOOT = 'ac87bbbe-5f9b-496f-8002-43279e072042'
SERIAL = '61b0657200000000000000000324012c'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve(value):
    prefix = '$WORKSPACES/'
    if not value.startswith(prefix) or '..' in Path(value[len(prefix):]).parts:
        raise ValueError('nonportable source path')
    return WORKSPACES / value[len(prefix):]


def verify_sources(entries):
    result = {}
    for entry in entries:
        path = resolve(entry['path'])
        if entry['id'] in result or not path.is_file() or path.is_symlink():
            raise ValueError('missing/duplicate/symlink source: ' + entry['id'])
        if digest(path) != entry['sha256'] or path.stat().st_size != entry['bytes']:
            raise ValueError('source drift: ' + entry['id'])
        result[entry['id']] = path
    return result


def evidence_review(entries=None):
    if entries is None:
        entries = json.loads((HERE / 'sources.json').read_text())
    sources = verify_sources(entries)
    text = {key: path.read_text(errors='backslashreplace') for key, path in sources.items()}
    index = json.loads(text['index'])
    if index['boot_expected'] != BOOT or index['boot_after'] != BOOT or not index['boot_matches']:
        raise ValueError('captured boot mismatch')
    parent = sources['index'].parent
    for item in index['files']:
        if item.get('exists'):
            if digest(parent / item['original']) != item['sha256']:
                raise ValueError('original-index SHA mismatch: ' + item['original'])
        elif item.get('board_path', '').endswith('adapter_child_9548.stderr'):
            if 'No such file or directory' not in (parent / item['presence_evidence']).read_text():
                raise ValueError('missing stderr observation unproved')
    expected_instance = dict(child='9548', parent='9529', birth='25409', started='254', seq='118', mode='fresh')
    instance = dict(line.split('=', 1) for line in text['instance'].splitlines() if '=' in line)
    if instance != expected_instance or text['instance'] != text['instance118'] or text['sequence'].strip() != '118':
        raise ValueError('instance identity drift')
    if f'boot_id={BOOT}' not in text['receipt'] or 'guardian=5936' not in text['receipt']:
        raise ValueError('receipt identity drift')
    required = {'guardian': 'GUARDIAN_PROC_ABSENT', 'state': 'CLEANUP_BLOCKED',
                'snapshot': 'as jpeg failed', 'ui': '438 seq=118 label=unknown',
                'parent': '[WESTLAKE-REAP] child 9548 killed by signal 11',
                'stop': '2026-10-12 09:58', 'events': '454 STOPPED'}
    for key, needle in required.items():
        if needle not in text[key]:
            raise ValueError('evidence assertion missing: ' + key)
    plan = json.loads(text['plan'])
    draft = json.loads(text['draft'])
    if draft['boot_id'] != BOOT or draft['plan_sha256'] != digest(sources['plan']):
        raise ValueError('draft plan binding mismatch')
    if plan['driver_sha256'] != digest(sources['driver']):
        raise ValueError('driver differs from bound plan')
    if plan['toutiao_slot']['placement']['sha256'] != digest(sources['placement']):
        raise ValueError('placement differs from bound plan')
    window = json.loads(text['window'])
    watchdog_lines = text['watchdog'].splitlines()
    overlay_lines = text['overlay'].splitlines()
    def locate(lines, needle):
        return [number for number, line in enumerate(lines, 1) if needle in line]
    return {
        'schema': 'toutiao-recovery-review/v1', 'board_access': False,
        'serial': SERIAL, 'boot_id': BOOT, 'instance': instance,
        'source_count': len(entries), 'source_sha_verified': True,
        'watchdog_sha256': digest(sources['watchdog']), 'overlay_sha256': digest(sources['overlay']),
        'guardian': {'pid': 5936, 'status': 'captured absent', 'receipt_is_liveness': False},
        'keeper': {'pid': 3956, 'role': 'screen keeper, not recovery guardian', 'fresh_liveness': 'unknown'},
        'child': {'pid': 9548, 'birth': 25409, 'route_parent': 9529, 'system_parent': 4792,
                  'status': 'captured signal11 reap; native root unknown'},
        'stop': {'present': True, 'mtime': '2026-10-12 09:58', 'actor': 'unknown'},
        'bootstrap': {'started_uptime': 254, 'last_unknown_uptime': 438,
                      'elapsed': 184, 'stopped_uptime': 454,
                      'inference': '180s bootstrap limit could be reached; cleanup branch/stop actor not proved'},
        'control_risks': [
            {'id': 'R2-01', 'severity': 'blocker', 'object': 'watchdog',
             'lines': locate(watchdog_lines, 'privacy)'), 'risk': 'automatic privacy touch; manual consent not observable'},
            {'id': 'R2-02', 'severity': 'blocker', 'object': 'watchdog',
             'lines': locate(watchdog_lines, 'consented" = 1'), 'risk': 'feed requires scripted consent; manual consent cannot make READY'},
            {'id': 'R2-03', 'severity': 'blocker', 'object': 'watchdog',
             'lines': locate(watchdog_lines, 'bootstrap_timeout'), 'risk': 'snapshot_error/unknown becomes app failure and cleanup'},
            {'id': 'R2-04', 'severity': 'blocker', 'object': 'watchdog',
             'lines': locate(watchdog_lines, 'mv "$RUNTIME/'), 'risk': 'fresh moves user data; repeated fresh can remove previous archive'},
            {'id': 'R2-05', 'severity': 'blocker', 'object': 'overlay',
             'lines': locate(overlay_lines, 'rm -f "$F/stop"'), 'risk': 'blind overlay rerun clears operator stop'},
            {'id': 'R2-06', 'severity': 'pending', 'object': 'guard_source',
             'risk': 'source checks PID/birth/UID/exeSHA/private root; live helper bytes and process scope not freshly captured'},
        ],
        'run_binding': {'plan_sha256': digest(sources['plan']), 'driver_sha256': digest(sources['driver']),
                        'provider_sha256': digest(sources['provider']), 'placement_sha256': digest(sources['placement']),
                        'command_timeout_seconds': plan['command_timeout_seconds'],
                        'provider_default_sign_timeout_seconds': 5400, 'provider_override_or_remaining_budget': 'unknown',
                        'window_document_boot': window['boot_id'], 'window_document_expires_at': window['expires_at'],
                        'window_document_is_current_authorization': False,
                        'same_run_repair_authorized': False, 'acceptance': 'pending; 4/5 is not seal'},
        'stderr': {'expected_capture_path': index['files'][6]['board_path'], 'capture': 'absent',
                   'parent_logged_path': '/data/service/el1/public/appspawnx/adapter_child_9548.stderr',
                   'alternative_path_contents': 'unknown; no board read performed'},
        'unknowns': ['native crash root', 'stop/cleanup actor', 'snapshot permission cause',
                     'live owner guard bytes', 'current driver liveness and deadline', 'candidate SHA/behavior'],
        'candidate': {'status': 'pending', 'reason': 't1 actual candidate not supplied'},
        'execution_enabled': False, 'ui_signed': False, 'seal_signed': False,
    }


def candidate_review(path=None, expected_sha=None):
    if path is None:
        return {'status': 'pending', 'reason': 'actual candidate missing'}
    path = Path(path)
    if not expected_sha or not re.fullmatch('[a-f0-9]{64}', expected_sha):
        return {'status': 'pending', 'reason': 'candidate SHA not independently pinned'}
    if not path.is_file() or path.is_symlink() or digest(path) != expected_sha:
        return {'status': 'blocker', 'reason': 'candidate source missing/symlink/SHA drift'}
    lines = [line for line in path.read_text().splitlines() if not line.lstrip().startswith('#')]
    code = '\n'.join(lines)
    problems = []
    if re.search(r'\buinput\b|\binput\s+tap\b', code):
        problems.append('automatic UI action present')
    if re.search(r'\b(?:mv|rm)\b[^\n]*(?:app-data|webview-t-data|operator-selfheal-(?:original|previous))', code):
        problems.append('data rotation/removal present')
    if re.search(r'\b(?:killall|pkill|pidof)\b', code):
        problems.append('name-based process control present')
    if re.search(r'\bkill\s+(?:-[A-Z0-9]+\s+)?[0-9]+\b', code):
        problems.append('literal PID control without fresh identity present')
    if re.search(r'\brm\b[^\n]*\bstop\b|\brm\b[^\n]*/stop["\s]', code):
        problems.append('stop removal present')
    return {'status': 'blocker' if problems else 'pending', 'sha256': expected_sha,
            'blockers': problems, 'reason': 'static rejection screen only; exact behavior/identity tests and independent manual review still required',
            'offline_accept': False, 'ui_signed': False, 'seal_signed': False}


def checkpoint_review():
    manifest = json.loads((HERE / 'candidate-checkpoint/manifest.json').read_text())
    result = json.loads((HERE / 'evidence/adversarial-result.json').read_text())
    for entry in manifest['files']:
        if digest(HERE / 'candidate-checkpoint' / entry['path']) != entry['sha256']:
            raise ValueError('candidate checkpoint drift')
    if digest(HERE / 'candidate-checkpoint/payload/watchdog.sh') != result['candidate_sha256']:
        raise ValueError('behavior result candidate drift')
    if digest(resolve(result['raw']['path'])) != result['raw']['sha256']:
        raise ValueError('raw behavior receipt drift')
    return result


def accepted_revision_review():
    import io_revision_review
    manifest = io_revision_review.verify_release()
    result = json.loads((HERE / 'evidence/io-9763171a-cases.json').read_text())
    if result['candidate_sha256'] != manifest['expected_watchdog_sha256']:
        raise ValueError('new revision result identity drift')
    raw = json.loads((HERE / 'evidence/io-9763171a-raw-manifest.json').read_text())
    expected_cases = {'owner_write_failure', 'owner_readback_mismatch', 'sequence_write_failure',
                      'instance_write_failure', 'state_write_failure', 'event_log_write_failure',
                      'parent_output_write_failure', 'spawn_output_write_failure', 'pid_reuse',
                      'stop_at_entry', 'stop_during_observation', 'snapshot_error',
                      'manual_consent_feed', 'default_disabled'}
    if {case['case'] for case in result['cases']} != expected_cases or len(result['cases']) != 14:
        raise ValueError('revision safety cases missing/duplicated')
    for case in result['cases']:
        if case['verdict'] != 'pass' or not case['expected_safety_behavior']:
            raise ValueError('new revision has a blocking case')
        for entry in raw[case['case']]['files']:
            if digest(resolve(entry['path'])) != entry['sha256']:
                raise ValueError('new revision raw receipt drift')
    return dict(result, status='offline_accept', deployment_allowed=False,
                full_release_commit='c014f86102f55b51033a0e5032c90ab4af089d09',
                integration_status='pending t4 concrete package', ui_signed=False, seal_signed=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate')
    parser.add_argument('--sha256')
    args = parser.parse_args()
    report = evidence_review()
    report['candidate'] = candidate_review(args.candidate, args.sha256) if args.candidate else accepted_revision_review()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
