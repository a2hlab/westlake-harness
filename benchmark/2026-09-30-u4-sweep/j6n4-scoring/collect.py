#!/usr/bin/env python3
"""Collect first U5 attempts offline; extracts are evidence, never automatic verdicts."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts/lab'))
from lab_paths import workspaces

PID = re.compile(r'^\S+ \S+\s+(\d+)\s+(\d+) ')
INTEREST = re.compile(
    r'\[N[234]-OWNER\]|nativeOnScheduleLaunchApplication ENTRY|'
    r'JNI DETECTED|\[CHILD_CK\] J_invokeStaticMain_main_threw|'
    r'ensureBindApplication FAILED|Caused by:|\bUNC[A-Z]*AUGHT|'
    r'\[B8-PM\].*(?:metaData|queryIntentServices)|io.sentry.auto-init|'
    r'\[B8-FETCH\] alarm|SessionToken|\[B8-AMB\].*PlaybackService|'
    r'MUSL-(?:LDSO|FDSAN)|NoSuchMethodError|NoSuchFieldError|'
    r'(?:at |from ).*(?:Vibrator|EglHelper|eglInitialize|eglChooseConfig|FlutterJNI|Sentry|WebView)|'
    r'Fatal signal|FATAL EXCEPTION|ASSERT FAILED|Get(?:Int|Long)Field|'
    r'eglInitialize.*(?:result|return|error)|EGL_NOT_INITIALIZED')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def normalized(line):
    message = re.sub(r'^\S+ \S+\s+\d+\s+\d+\s+[A-Z]\s+[^:]+:\s*', '', line)
    return message.removeprefix('[stderr] ').strip()


def sidecars(record):
    return sorted((item['name'], item['sha256']) for item in record.get('native_sidecars', []))


def collect(base, out):
    predictions = read(HERE.parent / 'j6n4-predictions/criteria.json')['rows']
    binding = read(base / 'inputs.json')
    if binding['prediction_sha256'] != sha((HERE.parent / 'J6N4-PREDICTIONS.csv').read_bytes()):
        raise ValueError('candidate is not bound to the frozen prediction CSV')
    index = {}
    for shard in ('5cd', '5ea', '61b'):
        source = read(base / f'index-{shard}.json')
        for item in source['selected']:
            if item['key'] in index:
                raise ValueError('duplicate selected key')
            index[item['key']] = (shard, source, item)
    if set(index) != {row['key'] for row in predictions}:
        raise ValueError('cohort mismatch')
    if out.exists():
        raise ValueError('choose a new evidence output directory')
    out.mkdir(parents=True)
    for name in ['inputs.json', 'results.json', 'windows.json', 'index-5cd.json', 'index-5ea.json', 'index-61b.json']:
        (out / name).write_bytes((base / name).read_bytes())
    all_rows = []
    for row in predictions:
        key = row['key']
        shard, source, item = index[key]
        record_path = base / item['record']
        data = record_path.read_bytes()
        if sha(data) != item['record_sha256']:
            raise ValueError('record changed: ' + key)
        record = json.loads(data)
        attempts = list((base / 'runs').glob('u5-' + shard + '*/*/' + key + '/record.json'))
        attempted = [(path, read(path)) for path in attempts]
        attempted = [(path, value) for path, value in attempted if value.get('clicked_at')]
        if attempted and min(attempted, key=lambda pair: pair[1]['clicked_at'])[0] != record_path:
            raise ValueError('selected record is not the first timed attempt: ' + key)
        if record.get('clicked_at') and datetime.fromisoformat(binding['planned_at']).timestamp() >= record['clicked_at']:
            raise ValueError('candidate binding not before click: ' + key)
        baseline_path = base.parent / '2026-09-30-u4-sweep' / row['record']
        baseline_data = baseline_path.read_bytes()
        if sha(baseline_data) != row['record_sha256']:
            raise ValueError('U4 record differs from frozen identity: ' + key)
        baseline = json.loads(baseline_data)
        (out / 'records').mkdir(exist_ok=True)
        (out / 'records' / (key + '.json')).write_bytes(data)
        log_path = record_path.parent / 'hilog.txt'
        raw = log_path.read_bytes() if log_path.exists() else b''
        lines = raw.decode(errors='replace').splitlines()
        bindings = [(number, line) for number, line in enumerate(lines, 1)
                    if 'nativeOnScheduleLaunchApplication ENTRY bundle=' + row['package'] + ' ' in line]
        pids = {PID.match(line)[1] for _, line in bindings if PID.match(line)}
        own = [(number, line) for number, line in enumerate(lines, 1)
               if (match := PID.match(line)) and match[1] in pids]
        old = normalized(row['current_wall_evidence'])
        old_hits = [number for number, line in own if normalized(line) == old]
        marker_counts = {marker: sum(marker in line for _, line in own) for marker in (
            '[N2-OWNER] ABI global ready', 'Flutter default-owner namespace configuration failed:',
            'DSN is required.', 'io.sentry.auto-init',
            'projected queryIntentServices androidx.media3.session.MediaSessionService',
            'Failed to resolve SessionToken', 'libmegazord.so: __get_h_errno: symbol not found')}
        selected = {number: line for number, line in own if INTEREST.search(line)
                    and 'OH_RegHook' not in line and '[class_linker.cc:' not in line}
        for number, line in own:
            if number in old_hits:
                selected[number] = line
        excerpts = [{'line': number, 'text': text} for number, text in sorted(selected.items())]
        save(out / 'logs' / (key + '.json'), excerpts)
        shots = [shot for shot in record.get('screenshots', [])
                 if shot.get('scheduled_seconds') == 20 and shot.get('captured')]
        shot = shots[0] if len(shots) == 1 else None
        if shot:
            image_path = record_path.parent / 't20.jpeg'
            if sha(image_path.read_bytes()) != shot['sha256']:
                raise ValueError('t20 changed: ' + key)
            if sha((base / 'evidence/t20' / (key + '.jpeg')).read_bytes()) != shot['sha256']:
                raise ValueError('portable t20 differs: ' + key)
        runtime = record_path.parent.parent / 'runtime-fingerprint.txt'
        boot = record_path.parent.parent / 'boot-image-fingerprint.txt'
        runtime_ok = sha(runtime.read_bytes().strip())[:12] == '73ecf422dba2'
        boot_ok = sha(boot.read_bytes().strip())[:12] == '0876029078e2'
        for fingerprint in (runtime, boot):
            (out / fingerprint.name).write_bytes(fingerprint.read_bytes())
        input_ok = (record['package'] == row['package'] and record['apk_sha256'] == row['apk_sha256']
                    and sidecars(record) == sidecars(baseline)
                    and record.get('launch_activity') == baseline.get('launch_activity'))
        checks = dict(apk_entry_sidecars=input_ok, indexed_boot=record['boot_id'] == source['boot_id'],
                      generation=runtime_ok and boot_ok, target_pid=bool(pids), t20=bool(shot),
                      installed=bool(record.get('install', {}).get('success_text')) if record.get('install') else False)
        valid = all(checks.values())
        all_rows.append(dict(key=key, shard=shard, package=row['package'], apk_sha256=record['apk_sha256'],
            record=item['record'], record_sha256=sha(data), status=record['status'], error=record.get('error'),
            log=str(log_path.relative_to(base)), log_sha256=sha(raw) if raw else None, log_lines=len(lines),
            target_pids=sorted(pids), binding_lines=[number for number, _ in bindings],
            old_exact_lines=old_hits, marker_counts=marker_counts,
            identity_checks=checks, identity_and_capture_valid=valid,
            t20_sha256=shot['sha256'] if shot else None,
            t20_path='evidence/t20/' + key + '.jpeg' if shot else None,
            t20_elapsed_seconds=shot.get('elapsed_seconds') if shot else None,
            input_sha256=record.get('input_sha256'), sidecars=sidecars(record),
            u4_record_sha256=sha(baseline_data), u4_sidecars=sidecars(baseline),
            runtime_sha256=sha(runtime.read_bytes()), boot_sha256=sha(boot.read_bytes()),
            excerpts_sha256=sha((out / 'logs' / (key + '.json')).read_bytes())))
    save(out / 'observations.json', all_rows)
    print(json.dumps({'keys': len(all_rows), 'valid': sum(row['identity_and_capture_valid'] for row in all_rows)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=workspaces() / 'westlake-harness-bms-deploy/benchmark/2026-10-01-u5-sweep')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    collect(args.source, args.out)
