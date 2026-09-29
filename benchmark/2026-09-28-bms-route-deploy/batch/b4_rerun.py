#!/usr/bin/env python3
"""Offline #59 plan validation and v3-shaped aggregation; never operates a board."""
import argparse
import collections
import datetime
import hashlib
import json
from pathlib import Path
import re
import shlex

import bms_batch as b

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text())


def load_plan(path=ROOT/'b4-rerun-shards.json'):
    config = read(path)
    if b.sha(ROOT/'apps.json') != config['manifest_sha256'] or b.sha(ROOT/'bms_batch.py') != config['runner_sha256']:
        raise ValueError('manifest/runner drift: review and repin the plan before use')
    history_path = ROOT/'b4-rerun-history.json'
    if b.sha(history_path) != config['history_sha256']:
        raise ValueError('historical balancing evidence changed')
    history = {x['key']:x for x in read(history_path)['records']}
    apps = b.load_apps(ROOT/'apps.json')
    keys = [a['key'] for a in apps]
    seen = []
    serials = []
    runs = []
    for shard in config['shards']:
        selected = [a['key'] for a in b.load_apps(ROOT/'apps.json', keys=','.join(shard['keys']))]
        if selected != shard['keys'] or len(selected) != 22:
            raise ValueError('shard must preserve manifest order and contain 22 keys')
        if shard['serial'] not in b.SERIALS or not b.KEY.fullmatch(shard['run_id']):
            raise ValueError('invalid shard identity')
        args = shard['runner_args']
        expected = ['--execute', '--serial', shard['serial'], '--lane', shard['lane'],
                    '--run-id', shard['run_id'], '--out', config['run_root'],
                    '--manifest', config['master_batch_directory']+'/apps.json',
                    '--input-root', '/home/zhaoyue/a2hlab/app-inputs',
                    '--keys', ','.join(selected), '--reinstall', '--hilog', '15',
                    '--shots', '5,20', '--focus-check', '--wait', '20']
        if args != expected or shard['command_argv'] != ['orb', '-m', 'a2hlab', 'bash', config['master_batch_directory']+'/run-batch.sh']+args:
            raise ValueError('command and shard configuration differ')
        relative = shard['run_id']+'/'+shard['serial']
        if shard['relative_artifact_directory'] != relative or shard['artifact_directory'] != config['run_root']+'/'+relative:
            raise ValueError('artifact directory identity mismatch')
        families = collections.Counter(history[k]['first_blocker'] if history[k]['category']=='exited-early' else history[k]['category'] for k in selected)
        phases = collections.Counter(history[k]['phase'] for k in selected)
        if dict(families) != shard['historical_family_histogram'] or dict(phases) != shard['phase_histogram']:
            raise ValueError('shard distribution does not match historical evidence')
        seen.extend(selected); serials.append(shard['serial']); runs.append(shard['run_id'])
    if len(serials) != 3 or set(serials) != b.SERIALS or len(set(runs)) != 3 or len(seen) != 66 or sorted(seen) != sorted(keys):
        raise ValueError('three shards must cover all 66 keys exactly once')
    return config, apps


def scoped_path(app_dir, value):
    """Relocate a copied run by its app-directory suffix without reading old VM paths."""
    parts = Path(value).parts
    key = app_dir.name
    matches = [i for i, part in enumerate(parts) if part == key]
    if not matches:
        raise ValueError('evidence path lacks target app directory')
    tail = parts[matches[-1]+1:]
    candidate = app_dir.joinpath(*tail).resolve()
    if not tail or not candidate.is_relative_to(app_dir.resolve()):
        raise ValueError('evidence path escapes target app directory')
    return candidate


def checked_file(app_dir, item):
    path = scoped_path(app_dir, item['path'])
    if not path.is_file() or b.sha(path) != item['sha256']:
        raise ValueError('missing or changed evidence: '+str(path))
    return path


PATTERNS = [
    ('fdsan', r'fdsan_error|attempted to close file descriptor'),
    ('b6-family-context', r'getSharedPreferences'),
    ('b6-activity-attach', r'getApplicationInfo|getTheme|handleConfigurationChanged'),
    ('notification-create', r'Notification.*(?:create|Create)|(?:create|Create).*Notification'),
    ('art-entry', r'nterp|art::interpreter|art_quick_invoke'),
    ('unsatisfied-link', r'UnsatisfiedLinkError'),
    ('class-not-found', r'ClassNotFoundException'),
    ('java-fatal', r'FATAL EXCEPTION|AndroidRuntime.*Exception'),
]
NOISE = ('HDC_LOG', 'MUSL-SIGCHAIN', 'appspawn_kickdog', 'OH_RegHook', 'PARAM_WATCHER')


def bucket(text, fallback):
    return next((name for name, pattern in PATTERNS if re.search(pattern, text)), fallback)


def fatal_evidence(record, app_dir):
    diagnostic = record.get('diagnostics') or {}
    uid = (record.get('bms') or {}).get('uid')
    # New files are not automatically target files: exact recorded UID is required.
    for item in sorted(diagnostic.get('faultlogs', []), key=lambda x: (int(re.search(r'(\d+)$', Path(x['path']).name)[1]) if re.search(r'(\d+)$', Path(x['path']).name) else 0, x['path'])):
        path = checked_file(app_dir, item)
        lines = path.read_text(errors='replace').splitlines()
        fault_uid = next((int(m[1]) for line in lines if (m := re.fullmatch(r'Uid:\s*(\d+)\s*', line))), None)
        if uid is None or fault_uid != uid:
            continue
        for index, line in enumerate(lines, 1):
            if line.startswith('#00 '):
                return {'first_blocker': bucket(line, 'other-native'), 'evidence': line,
                        'path': str(path), 'line': index, 'source': 'faultlog', 'attribution': 'exact BMS UID'}
    if not diagnostic.get('path'):
        return None
    path = checked_file(app_dir, diagnostic)
    lines = path.read_text(errors='replace').splitlines()
    package = record.get('package')
    if not package:
        return None
    pkg_pattern = re.compile(r'(?<![\w.])'+re.escape(package)+r'(?![\w.])')
    pids = set(record.get('observed_pids') or [])
    for shot in record.get('screenshots', []):
        pids.update((shot.get('foreground') or {}).get('observed_pids') or [])
    for line in lines:
        if not any(noise in line for noise in NOISE) and pkg_pattern.search(line):
            match = re.search(r'\bwith pid\s+(\d+)\b', line)
            if match:
                pids.add(int(match[1]))
    for index, line in enumerate(lines, 1):
        if any(noise in line for noise in NOISE):
            continue
        match = re.match(r'\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+(\d+)\s+\d+\s', line)
        attributable = bool(pkg_pattern.search(line)) or (match is not None and int(match[1]) in pids)
        if not attributable:
            continue
        # Avoid ordinary method trace text becoming a fatal claim.
        fatal = re.search(r'FATAL EXCEPTION|UnsatisfiedLinkError|ClassNotFoundException|SIGSEGV|SIGABRT|fdsan_error|attempted to close file descriptor|AndroidRuntime.*Exception', line)
        clean = re.search(r'exit with code:\s*(-?\d+)', line) if pkg_pattern.search(line) else None
        if fatal or clean:
            return {'first_blocker': bucket(line, 'other-native') if fatal else 'clean-exit-'+clean[1],
                    'evidence': line, 'path': str(path), 'line': index, 'source': 'hilog',
                    'attribution': 'exact package or observed/disclosed target PID'}
    return None


def classify(record, app_dir):
    status = record.get('status')
    install = record.get('install')
    fatal = fatal_evidence(record, app_dir)
    blocker = None
    if status == 'batch_interrupted':
        category, why = 'interrupted', record.get('error', 'batch interrupted')
    elif install is None:
        input_error = re.search(r'input|pinned identity|original APK|APK digest', record.get('error', ''), re.I)
        category = 'input-refused' if input_error else 'collection-failed'
        why = record.get('error', 'installation was not reached')
    elif install.get('return_code') or not install.get('success_text'):
        category, why = 'rerun956-install-failed', 'reinstall/install failed; see current install receipt'
    elif status not in ('captured', 'foreground_unconfirmed', 'capture_rejected') or not record.get('clicked') or 'observed_pids' not in record:
        category, why = 'collection-failed', record.get('error', 'no completed post-click process sample')
    elif record['observed_pids']:
        category, why = 'alive-at-sample', 'alive at final current-round observation; not a visual verdict'
    else:
        category, why = 'exited-early', 'no target PID at final current-round observation'
        blocker = fatal['first_blocker'] if fatal else 'unknown'
    return {'category': category, 'category_reason': why, 'first_blocker': blocker,
            'blocker_evidence': fatal['evidence'] if fatal else None,
            'fatal_observation': fatal,
            'alive_with_fatal_evidence': bool(category == 'alive-at-sample' and fatal)}


def aggregate(config, apps, run_root, partial=False):
    by_key = {a['key']: a for a in apps}
    outputs = {}
    sources = []
    for shard in config['shards']:
        directory = Path(run_root)/shard['relative_artifact_directory']
        summary_path = directory/'summary.json'
        if not summary_path.exists():
            if partial:
                continue
            raise ValueError('missing shard summary: '+str(summary_path))
        run_plan = read(directory/'plan.json')
        if run_plan.get('run_id') != shard['run_id'] or run_plan.get('serial') != shard['serial'] or [a['key'] for a in run_plan['apps']] != shard['keys']:
            raise ValueError('stale/wrong-board run plan')
        required_options = dict(reinstall=True, hilog_seconds=15, shots=[5,20], focus_check=True)
        if run_plan.get('options') != required_options:
            raise ValueError('run options do not match the three-board plan')
        summary = read(summary_path)
        current = summary['records']; current_keys = [r['key'] for r in current]
        missing = summary.get('not_run', [])
        if len(set(current_keys)) != len(current_keys) or set(current_keys)&set(missing) or len(set(missing)) != len(missing) or set(current_keys+missing) != set(shard['keys']):
            raise ValueError('duplicate, foreign or missing key in summary accounting')
        if missing and not partial:
            raise ValueError('incomplete shard; use --allow-partial for an explicitly incomplete v4')
        boots = set()
        for record in current:
            key = record['key']; app = by_key[key]; app_dir = directory/key
            if key in outputs or record.get('serial') != shard['serial'] or record.get('phase') != app['phase']:
                raise ValueError('duplicate key or wrong record identity')
            if record != read(app_dir/'record.json'):
                raise ValueError('summary and per-app record disagree')
            if not record.get('boot_id'):
                raise ValueError('record has no boot identity')
            boots.add(record['boot_id'])
            if record.get('install') is not None and (not isinstance(record.get('package'), str) or not b.IDENT.fullmatch(record['package']) or not isinstance(record.get('apk_sha256'), str) or not b.SHA.fullmatch(record['apk_sha256'])):
                raise ValueError('installed record lacks resolved package/APK identity')
            for field in ('package', 'apk_sha256'):
                if app.get(field) and record.get(field) != app[field]:
                    raise ValueError('record violates manifest '+field)
            for shot in record.get('screenshots', []):
                if shot.get('captured'):
                    checked_file(app_dir, shot)
            outputs[key] = dict(key=key, phase=app['phase'], package=record.get('package'),
                               apk_sha256=record.get('apk_sha256'), serial=shard['serial'],
                               boot_id=record['boot_id'], record_status=record['status'],
                               observed_pids=record.get('observed_pids'),
                               foreground_confirmed=(record.get('foreground') or {}).get('confirmed'),
                               screenshots=record.get('screenshots', []), review='pending_review',
                               record_path=str(app_dir/'record.json'), record_sha256=b.sha(app_dir/'record.json'),
                               **classify(record, app_dir))
        if len(boots) > 1:
            raise ValueError('mixed boot identities within one shard')
        sources.append({'serial': shard['serial'], 'run_id': shard['run_id'], 'summary': str(summary_path), 'sha256': b.sha(summary_path)})
    missing = [a['key'] for a in apps if a['key'] not in outputs]
    if missing and not partial:
        raise ValueError('incomplete round')
    for key in missing:
        app = by_key[key]
        outputs[key] = dict(key=key, phase=app['phase'], package=app.get('package'), apk_sha256=app.get('apk_sha256'),
                            record_status='not_run', category='not-run', category_reason='no current-round record',
                            first_blocker=None, blocker_evidence=None, screenshots=[], review='pending_review')
    records = [outputs[a['key']] for a in apps]
    return {'task': 'B4 three-board rerun v4', 'schema': 'b4-v4 (v3 histogram/record fields retained)',
            'date': datetime.date.today().isoformat(), 'round': config['round'], 'serial': 'three-board',
            'serials': [s['serial'] for s in config['shards']], 'runs': sources, 'total': len(records),
            'complete': not missing, 'missing_keys': missing, 'executed_records': 66-len(missing),
            'category_histogram': dict(collections.Counter(r['category'] for r in records)),
            'exited_early_first_blocker': dict(collections.Counter(r['first_blocker'] for r in records if r['category']=='exited-early')),
            'unknown_keys_remaining': [r['key'] for r in records if r['first_blocker']=='unknown'],
            'visual_verdict': 'pending_review', 'records': records}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'b4-rerun-shards.json')
    sub = parser.add_subparsers(dest='mode', required=True)
    plan = sub.add_parser('plan'); plan.add_argument('--shard', choices=['5ea','5cd','61b'])
    agg = sub.add_parser('aggregate'); agg.add_argument('--run-root', type=Path, required=True)
    agg.add_argument('--out', type=Path, required=True); agg.add_argument('--allow-partial', action='store_true')
    args = parser.parse_args(argv)
    config, apps = load_plan(args.config)
    if args.mode == 'plan':
        for shard in config['shards']:
            if not args.shard or shard['name'] == args.shard:
                print(json.dumps({'shard':shard['name'], 'keys':shard['keys'], 'command':shlex.join(shard['command_argv']), 'artifacts':shard['artifact_directory'], 'execution':'not-requested'},indent=2))
        return 0
    if args.out.exists():
        raise ValueError('refuse overwriting a prior histogram')
    result = aggregate(config, apps, args.run_root, args.allow_partial)
    b.save(args.out, result)
    print(json.dumps({k:result[k] for k in ('complete','executed_records','category_histogram','exited_early_first_blocker','unknown_keys_remaining')},indent=2))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
